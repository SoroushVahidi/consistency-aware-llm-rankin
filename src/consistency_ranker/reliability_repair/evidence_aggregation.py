"""Aggregate normalized evidence per unordered pair."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Sequence

from consistency_ranker.reliability_repair.pair_evidence import NormalizedEvidence

DirectionEstimator = Literal[
    "unweighted_majority",
    "valid_majority",
    "provider_balanced",
    "prompt_balanced",
    "orientation_balanced",
    "reliability_weighted",
    "smoothed",
]


@dataclass
class PairAggregate:
    """Aggregated evidence for one unordered pair {doc_i, doc_j}."""

    query_id: str
    canonical_pair_id: str
    doc_i: str
    doc_j: str
    n_total: int = 0
    n_valid_directional: int = 0
    n_plus: int = 0  # z=+1
    n_minus: int = 0  # z=-1
    n_zero: int = 0
    n_tie: int = 0
    n_refusal: int = 0
    n_invalid: int = 0
    n_insufficient: int = 0
    p_hat: float = 0.5
    m: float = 0.0
    d: int = 0  # sign(m); 0 if abstain/tie at aggregate level
    estimator: str = "smoothed"
    features: dict[str, float] = field(default_factory=dict)
    evidence: list[NormalizedEvidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "canonical_pair_id": self.canonical_pair_id,
            "doc_i": self.doc_i,
            "doc_j": self.doc_j,
            "n_total": self.n_total,
            "n_valid_directional": self.n_valid_directional,
            "n_plus": self.n_plus,
            "n_minus": self.n_minus,
            "n_zero": self.n_zero,
            "p_hat": self.p_hat,
            "m": self.m,
            "d": self.d,
            "estimator": self.estimator,
            "features": self.features,
        }


def group_evidence(
    evidence: Iterable[NormalizedEvidence],
) -> dict[str, list[NormalizedEvidence]]:
    by_pair: dict[str, list[NormalizedEvidence]] = defaultdict(list)
    for e in evidence:
        by_pair[e.canonical_pair_id].append(e)
    return dict(by_pair)


def _balanced_counts(
    items: Sequence[NormalizedEvidence],
    key_fn,
) -> tuple[float, float]:
    """Average within groups then average across groups (provider/prompt/orient)."""
    groups: dict[Any, list[NormalizedEvidence]] = defaultdict(list)
    for e in items:
        groups[key_fn(e)].append(e)
    if not groups:
        return 0.0, 0.0
    plus_vals = []
    minus_vals = []
    for grp in groups.values():
        directional = [e for e in grp if e.z != 0]
        if not directional:
            continue
        plus_vals.append(sum(1 for e in directional if e.z == 1) / len(directional))
        minus_vals.append(sum(1 for e in directional if e.z == -1) / len(directional))
    if not plus_vals:
        return 0.0, 0.0
    return sum(plus_vals) / len(plus_vals), sum(minus_vals) / len(minus_vals)


def aggregate_pair(
    evidence: Sequence[NormalizedEvidence],
    *,
    estimator: DirectionEstimator = "smoothed",
    alpha: float = 1.0,
    external_weights: dict[str, float] | None = None,
) -> PairAggregate:
    """Aggregate all judgments for one unordered pair."""
    if not evidence:
        raise ValueError("evidence must be non-empty")
    e0 = evidence[0]
    agg = PairAggregate(
        query_id=e0.query_id,
        canonical_pair_id=e0.canonical_pair_id,
        doc_i=e0.doc_i,
        doc_j=e0.doc_j,
        evidence=list(evidence),
        estimator=estimator,
    )
    agg.n_total = len(evidence)
    for e in evidence:
        if e.z == 1:
            agg.n_plus += 1
            agg.n_valid_directional += 1
        elif e.z == -1:
            agg.n_minus += 1
            agg.n_valid_directional += 1
        else:
            agg.n_zero += 1
            if e.abstention_subtype == "tie":
                agg.n_tie += 1
            elif e.abstention_subtype == "refusal":
                agg.n_refusal += 1
            elif e.abstention_subtype == "insufficient_information":
                agg.n_insufficient += 1
            else:
                agg.n_invalid += 1

    plus = float(agg.n_plus)
    minus = float(agg.n_minus)

    if estimator == "unweighted_majority":
        # Count zeros as non-votes for direction but still in n_total features.
        pass
    elif estimator == "valid_majority":
        pass
    elif estimator == "provider_balanced":
        plus, minus = _balanced_counts(evidence, lambda e: e.provider)
        plus *= max(agg.n_valid_directional, 1)
        minus *= max(agg.n_valid_directional, 1)
    elif estimator == "prompt_balanced":
        plus, minus = _balanced_counts(evidence, lambda e: e.prompt_version)
        plus *= max(agg.n_valid_directional, 1)
        minus *= max(agg.n_valid_directional, 1)
    elif estimator == "orientation_balanced":
        plus, minus = _balanced_counts(evidence, lambda e: e.displayed_orientation)
        plus *= max(agg.n_valid_directional, 1)
        minus *= max(agg.n_valid_directional, 1)
    elif estimator == "reliability_weighted":
        w_plus = 0.0
        w_minus = 0.0
        for e in evidence:
            if e.z == 0:
                continue
            key = e.cache_key or f"{e.provider}:{e.model}:{e.prompt_version}"
            w = 1.0 if external_weights is None else float(external_weights.get(key, 1.0))
            if e.z == 1:
                w_plus += w
            else:
                w_minus += w
        plus, minus = w_plus, w_minus
    elif estimator == "smoothed":
        pass
    else:
        raise ValueError(f"Unknown estimator {estimator!r}")

    if estimator == "smoothed":
        p = (agg.n_plus + alpha) / (agg.n_plus + agg.n_minus + 2 * alpha)
    else:
        denom = plus + minus
        if denom <= 0:
            p = 0.5
        else:
            p = plus / denom
            # mild smoothing for numerical stability in reliability features
            p = (plus + alpha) / (denom + 2 * alpha) if estimator.endswith("majority") else p

    if estimator in {"unweighted_majority", "valid_majority"} and (plus + minus) > 0:
        # Use raw fraction without forcing alpha for direction sign clarity
        p_raw = plus / (plus + minus)
        m = 2 * p_raw - 1
        # still store smoothed p_hat for calibration-friendly features
        agg.p_hat = (agg.n_plus + alpha) / (agg.n_plus + agg.n_minus + 2 * alpha)
        agg.m = m
    else:
        agg.p_hat = p
        agg.m = 2 * p - 1

    if abs(agg.m) < 1e-15:
        agg.d = 0
    else:
        agg.d = 1 if agg.m > 0 else -1

    agg.features = _pair_features(agg, evidence)
    return agg


def aggregate_all(
    evidence: Sequence[NormalizedEvidence],
    *,
    estimator: DirectionEstimator = "smoothed",
    alpha: float = 1.0,
) -> dict[str, PairAggregate]:
    return {
        pid: aggregate_pair(ev, estimator=estimator, alpha=alpha)
        for pid, ev in group_evidence(evidence).items()
    }


def _pair_features(
    agg: PairAggregate,
    evidence: Sequence[NormalizedEvidence],
) -> dict[str, float]:
    n = max(agg.n_total, 1)
    nd = max(agg.n_valid_directional, 1)
    # Orientation agreement among directional judgments
    by_orient: dict[str, list[int]] = defaultdict(list)
    for e in evidence:
        if e.z != 0 and e.displayed_orientation:
            by_orient[str(e.displayed_orientation)].append(int(e.z))
    orient_agree = 1.0
    if "ab" in by_orient and "ba" in by_orient:
        # Agreement if mean signs match
        m_ab = sum(by_orient["ab"]) / len(by_orient["ab"])
        m_ba = sum(by_orient["ba"]) / len(by_orient["ba"])
        orient_agree = 1.0 if (m_ab == 0 and m_ba == 0) or (m_ab * m_ba > 0) else 0.0
        if m_ab == 0 or m_ba == 0:
            orient_agree = 0.5

    # Repeat / prompt / model agreement
    def _group_agree(key_fn) -> float:
        groups = defaultdict(list)
        for e in evidence:
            if e.z == 0:
                continue
            groups[key_fn(e)].append(int(e.z))
        if len(groups) < 2:
            return 1.0 if groups else 0.0
        means = [sum(v) / len(v) for v in groups.values()]
        signs = [0 if abs(m) < 1e-12 else (1 if m > 0 else -1) for m in means]
        return 1.0 if len(set(signs)) == 1 else 0.0

    providers = {e.provider for e in evidence if e.provider}
    prompts = {e.prompt_version for e in evidence if e.prompt_version}
    models = {e.model for e in evidence if e.model}

    # Entropy of directional outcomes
    if agg.n_valid_directional == 0:
        entropy = 1.0
    else:
        p = agg.n_plus / nd
        entropy = _binary_entropy(p)

    prior_margin = 0.0
    if evidence[0].prior_score_i is not None and evidence[0].prior_score_j is not None:
        prior_margin = abs(float(evidence[0].prior_score_i) - float(evidence[0].prior_score_j))
    prior_rank_dist = 0.0
    if evidence[0].prior_rank_i is not None and evidence[0].prior_rank_j is not None:
        prior_rank_dist = abs(int(evidence[0].prior_rank_i) - int(evidence[0].prior_rank_j))

    return {
        "abs_margin": abs(agg.m),
        "n_valid_directional": float(agg.n_valid_directional),
        "valid_fraction": agg.n_valid_directional / n,
        "orientation_agreement": float(orient_agree),
        "repeat_agreement": _group_agree(lambda e: e.repetition_index),
        "prompt_agreement": _group_agree(lambda e: e.prompt_version),
        "model_agreement": _group_agree(lambda e: (e.provider, e.model)),
        "provider_diversity": float(len(providers)),
        "prompt_diversity": float(len(prompts)),
        "model_diversity": float(len(models)),
        "outcome_entropy": float(entropy),
        "tie_rate": agg.n_tie / n,
        "abstention_rate": agg.n_zero / n,
        "refusal_rate": agg.n_refusal / n,
        "invalid_rate": agg.n_invalid / n,
        "prior_score_margin": float(prior_margin),
        "prior_rank_distance": float(prior_rank_dist),
        "single_source": 1.0 if len(models) <= 1 and len(prompts) <= 1 else 0.0,
    }


def _binary_entropy(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return float(-p * math.log(p) - (1 - p) * math.log(1 - p))
