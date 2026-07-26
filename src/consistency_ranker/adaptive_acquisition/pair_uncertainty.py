"""Pair-level uncertainty measures for adaptive acquisition.

These quantify *how unsure* we are about a pair's preference direction. They are
deliberately kept separate from expected ranking impact (see ``ranking_impact``):
a pair can be maximally uncertain yet irrelevant to the final top-k ranking.

All measures operate on an aggregated :class:`PairAggregate` (or on a pair with
no evidence, treated as maximally uncertain). Every measure returns a value in
``[0, 1]`` where 1 means "most uncertain".
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from consistency_ranker.reliability_repair.evidence_aggregation import PairAggregate
from consistency_ranker.reliability_repair.pair_evidence import NormalizedEvidence

UncertaintyMethod = str

UNCERTAINTY_METHODS: tuple[str, ...] = (
    "vote",
    "entropy",
    "orientation",
    "repetition",
    "cross_prompt",
    "cross_model",
    "reliability",
    "max",
    "mean",
)


def vote_uncertainty(agg: PairAggregate | None) -> float:
    r"""``U^vote = 1 - |2 p_hat - 1|``. 1 at p=0.5, 0 at p in {0,1}."""
    if agg is None:
        return 1.0
    p = float(agg.p_hat)
    return float(max(0.0, min(1.0, 1.0 - abs(2.0 * p - 1.0))))


def entropy_uncertainty(agg: PairAggregate | None) -> float:
    r"""Binary entropy of ``p_hat`` normalized by ``log 2`` (in ``[0, 1]``)."""
    if agg is None:
        return 1.0
    p = float(agg.p_hat)
    if p <= 0.0 or p >= 1.0:
        return 0.0
    h = -p * math.log(p) - (1.0 - p) * math.log(1.0 - p)
    return float(max(0.0, min(1.0, h / math.log(2))))


def _group_disagreement(
    evidence: list[NormalizedEvidence],
    key_fn,
) -> float:
    """1 - |mean of per-group signed means|, over >=2 non-empty directional groups.

    0 when only one group contributes (no cross-group evidence yet: not
    "uncertain" in the disagreement sense — return 0 so it does not dominate;
    callers combine with vote/entropy for the no-evidence case).
    """
    groups: dict[Any, list[int]] = defaultdict(list)
    for e in evidence:
        if e.z != 0:
            groups[key_fn(e)].append(int(e.z))
    means = [sum(v) / len(v) for v in groups.values() if v]
    if len(means) < 2:
        return 0.0
    grand = sum(means) / len(means)
    # Spread of signed means: max at perfectly split (+1/-1 groups) -> 1.
    return float(max(0.0, min(1.0, 1.0 - abs(grand))))


def orientation_uncertainty(agg: PairAggregate | None) -> float:
    """High when judgments disagree after reversing display order."""
    if agg is None or not agg.evidence:
        return 1.0
    oa = float(agg.features.get("orientation_agreement", 1.0))
    return float(max(0.0, min(1.0, 1.0 - oa)))


def repetition_uncertainty(agg: PairAggregate | None) -> float:
    """High when repeated calls (same everything, different repetition_index) disagree."""
    if agg is None or not agg.evidence:
        return 1.0
    return _group_disagreement(agg.evidence, lambda e: e.repetition_index)


def cross_prompt_uncertainty(agg: PairAggregate | None) -> float:
    """High when prompt variants disagree."""
    if agg is None or not agg.evidence:
        return 1.0
    return _group_disagreement(agg.evidence, lambda e: e.prompt_version)


def cross_model_uncertainty(agg: PairAggregate | None) -> float:
    """High when models / providers disagree."""
    if agg is None or not agg.evidence:
        return 1.0
    return _group_disagreement(agg.evidence, lambda e: (e.provider, e.model))


def reliability_uncertainty(
    agg: PairAggregate | None,
    *,
    prior_support: float = 2.0,
) -> float:
    r"""High when reliability CI is wide / support is thin.

    Uses a Wilson-style half-width proxy on ``p_hat`` with effective support
    ``n = n_valid_directional``. Zero support → 1 (fully uncertain).
    """
    if agg is None:
        return 1.0
    n = float(agg.n_valid_directional)
    if n <= 0:
        return 1.0
    p = float(agg.p_hat)
    # 95% Wilson half-width scaled to [0,1]; shrink by prior_support pseudo-counts.
    z = 1.96
    n_eff = n + prior_support
    denom = 1.0 + z * z / n_eff
    half = (z / denom) * math.sqrt(p * (1 - p) / n_eff + z * z / (4 * n_eff * n_eff))
    return float(max(0.0, min(1.0, 2.0 * half)))


_MEASURES = {
    "vote": vote_uncertainty,
    "entropy": entropy_uncertainty,
    "orientation": orientation_uncertainty,
    "repetition": repetition_uncertainty,
    "cross_prompt": cross_prompt_uncertainty,
    "cross_model": cross_model_uncertainty,
    "reliability": reliability_uncertainty,
}


def all_uncertainties(agg: PairAggregate | None) -> dict[str, float]:
    """Return every base uncertainty measure for a pair."""
    return {name: fn(agg) for name, fn in _MEASURES.items()}


def uncertainty(
    agg: PairAggregate | None,
    *,
    method: UncertaintyMethod = "vote",
    weights: dict[str, float] | None = None,
) -> float:
    """Dispatch a single scalar uncertainty.

    ``method='max'`` / ``'mean'`` combine the base measures; a custom weighted
    combination is used when ``weights`` is provided.
    """
    if weights:
        vals = all_uncertainties(agg)
        num = sum(weights.get(k, 0.0) * v for k, v in vals.items())
        den = sum(abs(w) for w in weights.values()) or 1.0
        return float(max(0.0, min(1.0, num / den)))
    if method in _MEASURES:
        return _MEASURES[method](agg)
    vals = all_uncertainties(agg)
    if method == "max":
        return float(max(vals.values()))
    if method == "mean":
        return float(sum(vals.values()) / len(vals))
    raise ValueError(f"Unknown uncertainty method {method!r}")
