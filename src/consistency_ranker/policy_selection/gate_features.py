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

from consistency_ranker.prior_robust.prior_dependence import evidence_fraction_summary
from consistency_ranker.prior_robust.prior_quality import (
    cross_prior_kendall,
    judgment_prior_agreement,
    prior_score_entropy,
    topk_score_separation,
)

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState

FEATURE_SCHEMA_VERSION = "policy_gate_features_v1"

FeatureStage = Literal["pre", "probe", "online"]

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
ONLINE_FEATURE_NAMES: tuple[str, ...] = (
    "current_prior_credibility",
    "challenger_success_rate",
    "acquisition_gain_proxy",
    "evidence_topk_support",
    "remaining_budget_frac",
    "stability_correctness_warn",
    "shared_bias_score",
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
        if d.get("schema_version") != FEATURE_SCHEMA_VERSION:
            raise ValueError(
                f"Incompatible feature schema {d.get('schema_version')!r}; "
                f"expected {FEATURE_SCHEMA_VERSION!r}"
            )
        return cls(
            schema_version=d["schema_version"],
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
        # one insider, one outsider
        topk_vs_out_n += 1
        # z>0 / p_hat>0.5 ⇒ canonical doc_i preferred.
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
    # Cheap prior-dependence proxy without full Monte Carlo: 1 - evidence fraction.
    ev_frac = float(summary.get("evidence_fraction") or 0.0)
    g_proxy = float(max(0.0, min(1.0, 1.0 - ev_frac)))
    sev_proxy = float(max(0.0, min(1.0, ev_frac)))

    return {
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
        "preliminary_g_prior": g_proxy,
        "evidence_only_stability_proxy": sev_proxy,
        "n_outsiders_defeating_insiders": float(outsiders_beat) / max(k, 1),
        "n_cycles_proxy": float(min(1.0, view.max_scc_size / max(len(state.candidate_ids), 1))),
        "ambiguity_bucket_ord": float(amb_ord),
        "n_probe_acquired": float(summary.get("n_acquired") or 0) / 16.0,
    }


def extract_online_features(
    state: "AcquisitionState",
    *,
    q_hat: float = 0.5,
    challenger_success_rate: float = 0.0,
    acquisition_gain_proxy: float = 0.0,
    shared_bias_score: float = 0.0,
    initial_budget: int | None = None,
) -> dict[str, float]:
    summary = evidence_fraction_summary(state)
    ev_frac = float(summary.get("evidence_fraction") or 0.0)
    init_b = float(initial_budget or max(state.remaining_budget, 1))
    rem = float(state.remaining_budget) / max(init_b, 1.0)
    # Warning: high ordinary stability proxy but thin evidence.
    warn = 1.0 if (ev_frac < 0.25 and q_hat >= 0.55) else 0.0
    # Evidence support for current top-k: fraction of top-k pairs with evidence.
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
    return {
        "current_prior_credibility": float(max(0.0, min(1.0, q_hat))),
        "challenger_success_rate": float(max(0.0, min(1.0, challenger_success_rate))),
        "acquisition_gain_proxy": float(max(0.0, min(1.0, acquisition_gain_proxy))),
        "evidence_topk_support": (support / need) if need else 0.0,
        "remaining_budget_frac": float(max(0.0, min(1.0, rem))),
        "stability_correctness_warn": warn,
        "shared_bias_score": float(max(0.0, min(1.0, shared_bias_score))),
    }


def extract_features(
    state: "AcquisitionState",
    *,
    stage: FeatureStage = "pre",
    alt_priors: list[dict[str, float]] | None = None,
    query_text: str | None = None,
    online_kwargs: dict[str, Any] | None = None,
) -> FeatureBundle:
    """Extract features available at ``stage`` (and earlier stages)."""
    values: dict[str, float] = {}
    availability: dict[str, FeatureStage] = {}
    pre = extract_pre_features(state, alt_priors=alt_priors, query_text=query_text)
    for name, v in pre.items():
        values[name] = float(v)
        availability[name] = "pre"
    if stage in ("probe", "online"):
        probe = extract_probe_features(state, alt_priors=alt_priors)
        for name, v in probe.items():
            values[name] = float(v)
            availability[name] = "probe"
    if stage == "online":
        online = extract_online_features(state, **(online_kwargs or {}))
        for name, v in online.items():
            values[name] = float(v)
            availability[name] = "online"
    return FeatureBundle(
        schema_version=FEATURE_SCHEMA_VERSION,
        stage=stage,
        values=values,
        availability=availability,
        metadata={"n_candidates": len(state.candidate_ids), "top_k": state.top_k},
    )


def feature_names_for_stage(stage: FeatureStage) -> list[str]:
    names = list(PRE_FEATURE_NAMES)
    if stage in ("probe", "online"):
        names.extend(PROBE_FEATURE_NAMES)
    if stage == "online":
        names.extend(ONLINE_FEATURE_NAMES)
    return names


def features_to_vector(
    bundle: FeatureBundle,
    *,
    stage: FeatureStage | None = None,
    names: list[str] | None = None,
) -> list[float]:
    if bundle.schema_version != FEATURE_SCHEMA_VERSION:
        raise ValueError(
            f"Incompatible feature schema {bundle.schema_version!r}; "
            f"expected {FEATURE_SCHEMA_VERSION!r}"
        )
    st = stage or bundle.stage
    use = names or feature_names_for_stage(st)
    return [float(bundle.values.get(n, 0.0)) for n in use]


def assert_no_qrel_keys(bundle: FeatureBundle) -> None:
    forbidden = ("qrel", "relevance", "true_ranking", "label", "ndcg_truth")
    blob = " ".join(bundle.values) + " ".join(map(str, bundle.metadata.keys()))
    for f in forbidden:
        if f in blob.lower():
            raise AssertionError(f"Potential label leakage key involving {f!r}")


__all__ = [
    "FEATURE_SCHEMA_VERSION",
    "FeatureStage",
    "FeatureBundle",
    "PRE_FEATURE_NAMES",
    "PROBE_FEATURE_NAMES",
    "ONLINE_FEATURE_NAMES",
    "extract_features",
    "extract_pre_features",
    "extract_probe_features",
    "extract_online_features",
    "features_to_vector",
    "feature_names_for_stage",
    "assert_no_qrel_keys",
]
