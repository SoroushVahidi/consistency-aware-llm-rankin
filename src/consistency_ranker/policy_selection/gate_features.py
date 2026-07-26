"""Observable gate features with explicit availability stages.

Stages
------
* pre  — available before any LLM judgment
* probe — available after a small fixed diagnostic probe budget
* online — updated during acquisition

No feature may depend on qrels or synthetic truth labels.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from consistency_ranker.prior_robust.prior_dependence import (
    evidence_fraction_summary,
    topk_evidence_coverage,
)
from consistency_ranker.prior_robust.prior_quality import (
    cross_prior_kendall,
    judgment_prior_agreement,
    prior_score_entropy,
    topk_score_separation,
)

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState

# Historical Outcome F schema string — must never change meaning or value.
SCHEMA_LEGACY_V1 = "policy_gate_features_v1"
SCHEMA_COVERAGE_V2 = "policy_gate_features_coverage_v2"
# Aliases accepted when requesting a schema; serialized form is the canonical string.
SCHEMA_ALIASES: dict[str, str] = {
    "legacy_v1": SCHEMA_LEGACY_V1,
    "policy_gate_features_v1": SCHEMA_LEGACY_V1,
    "coverage_v2": SCHEMA_COVERAGE_V2,
    "policy_gate_features_coverage_v2": SCHEMA_COVERAGE_V2,
}
KNOWN_FEATURE_SCHEMAS: frozenset[str] = frozenset({SCHEMA_LEGACY_V1, SCHEMA_COVERAGE_V2})
# Default remains legacy so frozen Outcome F / CalibratedModel loaders stay unchanged.
FEATURE_SCHEMA_VERSION = SCHEMA_LEGACY_V1

FeatureStage = Literal["pre", "probe", "online"]
FeatureSchemaVersion = str

# Ordered feature names used by calibrated models. Changing this bumps the schema.
PRE_FEATURE_NAMES: tuple[str, ...] = (
    "prior_score_margin_mean",
    "topk_boundary_separation",
    "normalized_score_entropy",
    "candidate_set_size",
    "cross_prior_kendall",
    "topk_overlap_priors",
    "rank_variance_across_priors",
    "score_dispersion",
    "n_boundary_challengers",
    "query_length_proxy",
)
PROBE_FEATURE_NAMES: tuple[str, ...] = (
    "weighted_agreement",
    "reliable_contradiction_rate",
    "agreement_rate",
    "topk_vs_outsider_win_rate",
    "orientation_consistency",
    "invalid_abstention_rate",
    "preliminary_g_prior",
    "evidence_only_stability_proxy",
    "n_outsiders_defeating_insiders",
    "n_cycles_proxy",
    "ambiguity_bucket_ord",
    "n_probe_acquired",
)
# coverage_v2 replaces the two historically-constant probe slots with unambiguous names.
PROBE_FEATURE_NAMES_V2: tuple[str, ...] = (
    "weighted_agreement",
    "reliable_contradiction_rate",
    "agreement_rate",
    "topk_vs_outsider_win_rate",
    "orientation_consistency",
    "invalid_abstention_rate",
    "preliminary_g_prior_from_coverage",
    "evidence_coverage_fraction",
    "n_outsiders_defeating_insiders",
    "n_cycles_proxy",
    "ambiguity_bucket_ord",
    "n_probe_acquired",
)
ONLINE_FEATURE_NAMES: tuple[str, ...] = (
    "current_prior_credibility",
    "challenger_success_rate",
    "acquisition_gain_proxy",
    "evidence_topk_support",
    "remaining_budget_frac",
    "stability_correctness_warn",
    "shared_bias_score",
)
ONLINE_FEATURE_NAMES_V2: tuple[str, ...] = (
    "current_prior_credibility",
    "challenger_success_rate",
    "acquisition_gain_proxy",
    "evidence_topk_support",
    "remaining_budget_frac",
    "stability_correctness_warn_v2",
    "shared_bias_score",
)


def resolve_feature_schema(schema: str | None) -> str:
    """Map aliases to canonical schema strings; reject unknowns."""
    if schema is None:
        return FEATURE_SCHEMA_VERSION
    key = str(schema).strip()
    if key in SCHEMA_ALIASES:
        return SCHEMA_ALIASES[key]
    if key in KNOWN_FEATURE_SCHEMAS:
        return key
    raise ValueError(
        f"Unknown feature schema {schema!r}; known={sorted(KNOWN_FEATURE_SCHEMAS)} "
        f"aliases={sorted(SCHEMA_ALIASES)}"
    )


def assert_schemas_compatible(left: str, right: str) -> None:
    """Raise unless both sides resolve to the same canonical schema."""
    a = resolve_feature_schema(left)
    b = resolve_feature_schema(right)
    if a != b:
        raise ValueError(
            f"Incompatible feature schemas: {left!r} → {a!r} vs {right!r} → {b!r}. "
            "legacy_v1 models cannot consume coverage_v2 vectors (and vice versa) "
            "without an explicit adapter."
        )


@dataclass
class FeatureBundle:
    schema_version: str
    stage: FeatureStage
    values: dict[str, float]
    availability: dict[str, FeatureStage] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "stage": self.stage,
            "values": dict(self.values),
            "availability": dict(self.availability),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FeatureBundle":
        raw = d.get("schema_version")
        try:
            schema = resolve_feature_schema(
                raw if raw is not None else FEATURE_SCHEMA_VERSION
            )
        except ValueError as exc:
            raise ValueError(
                f"Incompatible feature schema {raw!r}; "
                f"known={sorted(KNOWN_FEATURE_SCHEMAS)}"
            ) from exc
        return cls(
            schema_version=schema,
            stage=d["stage"],
            values=dict(d["values"]),
            availability=dict(d.get("availability") or {}),
            metadata=dict(d.get("metadata") or {}),
        )


def _mean_adjacent_margin(prior: dict[str, float]) -> float:
    ordered = sorted(prior.items(), key=lambda x: (-float(x[1]), x[0]))
    if len(ordered) < 2:
        return 0.0
    spreads = []
    lo, hi = float(ordered[-1][1]), float(ordered[0][1])
    denom = hi - lo if hi > lo else 1.0
    for i in range(len(ordered) - 1):
        spreads.append(abs(float(ordered[i][1]) - float(ordered[i + 1][1])) / denom)
    return float(sum(spreads) / len(spreads))


def _score_dispersion(prior: dict[str, float]) -> float:
    vals = [float(v) for v in prior.values()]
    if len(vals) < 2:
        return 0.0
    mu = sum(vals) / len(vals)
    var = sum((v - mu) ** 2 for v in vals) / len(vals)
    spread = max(vals) - min(vals)
    return float(math.sqrt(var) / spread) if spread > 0 else 0.0


def _topk_overlap(priors: list[dict[str, float]], k: int) -> float:
    if len(priors) < 2:
        return 1.0
    sets = []
    for p in priors:
        ordered = sorted(p, key=lambda d: (-float(p[d]), d))
        sets.append(set(ordered[:k]))
    inter = set.intersection(*sets) if sets else set()
    union = set.union(*sets) if sets else set()
    return float(len(inter) / len(union)) if union else 1.0


def _rank_variance(priors: list[dict[str, float]]) -> float:
    if len(priors) < 2:
        return 0.0
    docs = sorted(priors[0])
    vars_ = []
    for d in docs:
        ranks = []
        for p in priors:
            ordered = sorted(p, key=lambda x: (-float(p[x]), x))
            ranks.append(float(ordered.index(d)) if d in ordered else float(len(ordered)))
        mu = sum(ranks) / len(ranks)
        vars_.append(sum((r - mu) ** 2 for r in ranks) / len(ranks))
    n = max(len(docs) - 1, 1)
    return float(sum(vars_) / len(vars_) / (n * n))


def _n_boundary_challengers(prior: dict[str, float], k: int, window: int = 3) -> float:
    ordered = sorted(prior, key=lambda d: (-float(prior[d]), d))
    if len(ordered) <= k:
        return 0.0
    return float(min(window, len(ordered) - k)) / float(max(window, 1))


def extract_pre_features(
    state: "AcquisitionState",
    *,
    alt_priors: list[dict[str, float]] | None = None,
    query_text: str | None = None,
) -> dict[str, float]:
    prior = state.prior_scores
    k = state.top_k
    alts = list(alt_priors or [])
    all_priors = [prior] + alts if alts else [prior]
    cross = cross_prior_kendall(all_priors) if len(all_priors) > 1 else None
    qlen = float(len(query_text.split())) / 32.0 if query_text else 0.5
    return {
        "prior_score_margin_mean": _mean_adjacent_margin(prior),
        "topk_boundary_separation": topk_score_separation(prior, k),
        "normalized_score_entropy": prior_score_entropy(prior),
        "candidate_set_size": float(len(prior)) / 32.0,
        "cross_prior_kendall": float(cross) if cross is not None else 0.5,
        "topk_overlap_priors": _topk_overlap(all_priors, k),
        "rank_variance_across_priors": _rank_variance(all_priors),
        "score_dispersion": _score_dispersion(prior),
        "n_boundary_challengers": _n_boundary_challengers(prior, k),
        "query_length_proxy": float(max(0.0, min(1.0, qlen))),
    }


def extract_probe_features(
    state: "AcquisitionState",
    *,
    alt_priors: list[dict[str, float]] | None = None,
    schema_version: str | None = None,
) -> dict[str, float]:
    agr = judgment_prior_agreement(state)
    summary = evidence_fraction_summary(state)
    ranking = state.prior_ranking()
    k = state.top_k
    outsiders_beat = 0
    topk_vs_out_wins = 0
    topk_vs_out_n = 0
    for pid in state.all_pair_ids():
        agg = state.aggregates.get(pid)
        if agg is None or not agg.evidence:
            continue
        di, dj = state.pair_docs(pid)
        zi = ranking.index(di) if di in ranking else 99
        zj = ranking.index(dj) if dj in ranking else 99
        if (zi < k) == (zj < k):
            continue
        topk_vs_out_n += 1
        p_hat = float(getattr(agg, "p_hat", 0.5) or 0.5)
        if abs(p_hat - 0.5) < 1e-9:
            votes = sum(1 if e.z > 0 else -1 if e.z < 0 else 0 for e in agg.evidence)
            if votes == 0:
                continue
            pref = di if votes > 0 else dj
        else:
            pref = di if p_hat > 0.5 else dj
        outsider = dj if zi < k else di
        if pref == outsider:
            outsiders_beat += 1
        else:
            topk_vs_out_wins += 1

    orient = []
    invalid = 0
    total_ev = 0
    for agg in state.aggregates.values():
        for e in agg.evidence:
            total_ev += 1
            if getattr(e, "abstained", False) or getattr(e, "invalid", False):
                invalid += 1
        oa = agg.features.get("orientation_agreement")
        if oa is not None:
            orient.append(float(oa))

    view = state.view()
    amb = (view.ambiguity or {}).get("ambiguity_bucket", "low")
    amb_ord = {"low": 0.0, "medium": 0.5, "high": 1.0}.get(str(amb), 0.25)
    schema = resolve_feature_schema(schema_version)

    base = {
        "weighted_agreement": float(agr["weighted_agreement"] or 0.5),
        "reliable_contradiction_rate": float(agr["high_conf_contradiction_rate"] or 0.0),
        "agreement_rate": float(agr["agreement_rate"] or 0.5),
        "topk_vs_outsider_win_rate": (
            topk_vs_out_wins / topk_vs_out_n if topk_vs_out_n else 0.5
        ),
        "orientation_consistency": (
            sum(orient) / len(orient) if orient else 1.0
        ),
        "invalid_abstention_rate": (invalid / total_ev) if total_ev else 0.0,
        "n_outsiders_defeating_insiders": float(outsiders_beat) / max(k, 1),
        "n_cycles_proxy": float(min(1.0, view.max_scc_size / max(len(state.candidate_ids), 1))),
        "ambiguity_bucket_ord": float(amb_ord),
        "n_probe_acquired": float(summary.get("n_acquired") or 0) / 16.0,
    }

    if schema == SCHEMA_LEGACY_V1:
        ev_frac = float(summary.get("evidence_fraction") or 0.0)
        g_proxy = float(max(0.0, min(1.0, 1.0 - ev_frac)))
        sev_proxy = float(max(0.0, min(1.0, ev_frac)))
        base["preliminary_g_prior"] = g_proxy
        base["evidence_only_stability_proxy"] = sev_proxy
        return base

    cov = topk_evidence_coverage(state)
    frac = float(cov.get("fraction_acquired") or 0.0)
    base["preliminary_g_prior_from_coverage"] = float(max(0.0, min(1.0, 1.0 - frac)))
    base["evidence_coverage_fraction"] = float(max(0.0, min(1.0, frac)))
    return base


def extract_online_features(
    state: "AcquisitionState",
    *,
    q_hat: float = 0.5,
    challenger_success_rate: float = 0.0,
    acquisition_gain_proxy: float = 0.0,
    shared_bias_score: float = 0.0,
    initial_budget: int | None = None,
    schema_version: str | None = None,
) -> dict[str, float]:
    summary = evidence_fraction_summary(state)
    schema = resolve_feature_schema(schema_version)
    if schema == SCHEMA_LEGACY_V1:
        # Frozen defective read (always 0.0).
        ev_frac = float(summary.get("evidence_fraction") or 0.0)
    else:
        ev_frac = float(topk_evidence_coverage(state).get("fraction_acquired") or 0.0)
    init_b = float(initial_budget or max(state.remaining_budget, 1))
    rem = float(state.remaining_budget) / max(init_b, 1.0)
    warn = 1.0 if (ev_frac < 0.25 and q_hat >= 0.55) else 0.0
    ranking = state.ranking
    k = state.top_k
    support = 0
    need = 0
    for i in range(min(k, len(ranking))):
        for j in range(i + 1, min(k, len(ranking))):
            need += 1
            pid = state.canonical_pair(ranking[i], ranking[j])
            agg = state.aggregates.get(pid)
            if agg and agg.evidence:
                support += 1
    out = {
        "current_prior_credibility": float(max(0.0, min(1.0, q_hat))),
        "challenger_success_rate": float(max(0.0, min(1.0, challenger_success_rate))),
        "acquisition_gain_proxy": float(max(0.0, min(1.0, acquisition_gain_proxy))),
        "evidence_topk_support": (support / need) if need else 0.0,
        "remaining_budget_frac": float(max(0.0, min(1.0, rem))),
        "shared_bias_score": float(max(0.0, min(1.0, shared_bias_score))),
    }
    if schema == SCHEMA_LEGACY_V1:
        out["stability_correctness_warn"] = warn
    else:
        out["stability_correctness_warn_v2"] = warn
    return out


def extract_features(
    state: "AcquisitionState",
    *,
    stage: FeatureStage = "pre",
    alt_priors: list[dict[str, float]] | None = None,
    query_text: str | None = None,
    online_kwargs: dict[str, Any] | None = None,
    schema_version: str | None = None,
) -> FeatureBundle:
    """Extract features available at ``stage`` (and earlier stages)."""
    schema = resolve_feature_schema(schema_version)
    values: dict[str, float] = {}
    availability: dict[str, FeatureStage] = {}
    pre = extract_pre_features(state, alt_priors=alt_priors, query_text=query_text)
    for name, v in pre.items():
        values[name] = float(v)
        availability[name] = "pre"
    if stage in ("probe", "online"):
        probe = extract_probe_features(
            state, alt_priors=alt_priors, schema_version=schema
        )
        for name, v in probe.items():
            values[name] = float(v)
            availability[name] = "probe"
    if stage == "online":
        okw = dict(online_kwargs or {})
        okw["schema_version"] = schema
        online = extract_online_features(state, **okw)
        for name, v in online.items():
            values[name] = float(v)
            availability[name] = "online"
    return FeatureBundle(
        schema_version=schema,
        stage=stage,
        values=values,
        availability=availability,
        metadata={"n_candidates": len(state.candidate_ids), "top_k": state.top_k},
    )


def feature_names_for_stage(
    stage: FeatureStage,
    *,
    schema_version: str | None = None,
) -> list[str]:
    schema = resolve_feature_schema(schema_version)
    names = list(PRE_FEATURE_NAMES)
    if stage in ("probe", "online"):
        names.extend(
            PROBE_FEATURE_NAMES if schema == SCHEMA_LEGACY_V1 else PROBE_FEATURE_NAMES_V2
        )
    if stage == "online":
        names.extend(
            ONLINE_FEATURE_NAMES if schema == SCHEMA_LEGACY_V1 else ONLINE_FEATURE_NAMES_V2
        )
    return names


def features_to_vector(
    bundle: FeatureBundle,
    *,
    stage: FeatureStage | None = None,
    names: list[str] | None = None,
    expected_schema: str | None = None,
) -> list[float]:
    expected = resolve_feature_schema(expected_schema or bundle.schema_version)
    assert_schemas_compatible(bundle.schema_version, expected)
    st = stage or bundle.stage
    use = names or feature_names_for_stage(st, schema_version=expected)
    return [float(bundle.values.get(n, 0.0)) for n in use]


def assert_no_qrel_keys(bundle: FeatureBundle) -> None:
    forbidden = ("qrel", "relevance", "true_ranking", "label", "ndcg_truth")
    blob = " ".join(bundle.values) + " ".join(map(str, bundle.metadata.keys()))
    for f in forbidden:
        if f in blob.lower():
            raise AssertionError(f"Potential label leakage key involving {f!r}")


__all__ = [
    "FEATURE_SCHEMA_VERSION",
    "SCHEMA_LEGACY_V1",
    "SCHEMA_COVERAGE_V2",
    "SCHEMA_ALIASES",
    "KNOWN_FEATURE_SCHEMAS",
    "FeatureStage",
    "FeatureBundle",
    "PRE_FEATURE_NAMES",
    "PROBE_FEATURE_NAMES",
    "PROBE_FEATURE_NAMES_V2",
    "ONLINE_FEATURE_NAMES",
    "ONLINE_FEATURE_NAMES_V2",
    "resolve_feature_schema",
    "assert_schemas_compatible",
    "extract_features",
    "extract_pre_features",
    "extract_probe_features",
    "extract_online_features",
    "features_to_vector",
    "feature_names_for_stage",
    "assert_no_qrel_keys",
]
