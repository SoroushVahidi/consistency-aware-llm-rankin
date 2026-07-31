"""Edge importance factors (separate from reliability)."""

from __future__ import annotations

import math
from typing import Literal

from consistency_ranker.reliability_repair.evidence_aggregation import PairAggregate

ImportanceMethod = Literal[
    "uniform",
    "prior_position",
    "topk_boundary",
    "structural_placeholder",
]


def importance_uniform(_agg: PairAggregate, **_kwargs) -> float:
    return 1.0


def importance_prior_position(
    agg: PairAggregate,
    *,
    prior_ranks: dict[str, int] | None = None,
) -> float:
    """Higher importance when either endpoint is near the top of the prior."""
    ranks = prior_ranks or {}
    r_i = ranks.get(agg.doc_i) or agg.evidence[0].prior_rank_i or 100
    r_j = ranks.get(agg.doc_j) or agg.evidence[0].prior_rank_j or 100
    return float(1.0 / math.log2(1.0 + min(int(r_i), int(r_j))))


def importance_topk_boundary(
    agg: PairAggregate,
    *,
    prior_ranks: dict[str, int] | None = None,
    k: int = 10,
) -> float:
    """Boost pairs that straddle or sit near the top-k boundary."""
    ranks = prior_ranks or {}
    r_i = int(ranks.get(agg.doc_i) or agg.evidence[0].prior_rank_i or 10**9)
    r_j = int(ranks.get(agg.doc_j) or agg.evidence[0].prior_rank_j or 10**9)
    base = importance_prior_position(agg, prior_ranks=prior_ranks)
    # Both above k: medium; one in one out: high; both below: low
    in_i, in_j = r_i <= k, r_j <= k
    if in_i != in_j:
        return float(base * 2.0)
    if in_i and in_j:
        return float(base * 1.5)
    return float(base * 0.5)


def importance_structural_placeholder(
    agg: PairAggregate,
    *,
    cycle_participation: dict[str, float] | None = None,
) -> float:
    """Optional structural boost from precomputed cycle participation."""
    cp = cycle_participation or {}
    return float(1.0 + cp.get(agg.canonical_pair_id, 0.0))


def estimate_importance(
    agg: PairAggregate,
    method: ImportanceMethod = "uniform",
    **kwargs,
) -> float:
    if method == "uniform":
        return importance_uniform(agg)
    if method == "prior_position":
        return importance_prior_position(
            agg, prior_ranks=kwargs.get("prior_ranks")
        )
    if method == "topk_boundary":
        return importance_topk_boundary(
            agg,
            prior_ranks=kwargs.get("prior_ranks"),
            k=int(kwargs.get("k", 10)),
        )
    if method == "structural_placeholder":
        return importance_structural_placeholder(
            agg, cycle_participation=kwargs.get("cycle_participation")
        )
    raise ValueError(f"Unknown importance method {method!r}")
