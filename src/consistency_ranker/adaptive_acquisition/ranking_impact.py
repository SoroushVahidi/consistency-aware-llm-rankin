"""Estimate how much resolving a pair may change the final top-k ranking.

Impact is kept separate from uncertainty: it answers "would knowing this pair's
direction move the output?" rather than "how unsure are we?". All estimators are
judgment-free (no qrels). Sampling-based estimators reuse the existing
linear-extension sampler; an :class:`ImpactContext` caches the samples so a full
sweep over pairs costs one round of sampling, not one per pair.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import networkx as nx

from consistency_ranker.dag_linear_extensions import sample_linear_extensions

if TYPE_CHECKING:  # avoid import cycle at module load
    from consistency_ranker.adaptive_acquisition.acquisition_state import (
        AcquisitionState,
        StateView,
    )

ImpactMethod = str

IMPACT_METHODS: tuple[str, ...] = (
    "prior_rank_proximity",
    "current_rank_proximity",
    "topk_boundary_proximity",
    "linear_extension_sensitivity",
    "topk_membership_sensitivity",
    "rank_variance_reduction",
    "reachability_impact",
    "repair_impact",
)


@dataclass
class ImpactContext:
    """Per-step cached quantities for impact estimation over all pairs."""

    view: "StateView"
    top_k: int
    n_max_docs: int
    order_prob: dict[tuple[str, str], float] = field(default_factory=dict)
    current_rank: dict[str, int] = field(default_factory=dict)
    prior_rank: dict[str, int] = field(default_factory=dict)
    n_samples: int = 24

    @classmethod
    def build(
        cls,
        state: "AcquisitionState",
        *,
        n_samples: int = 24,
        seed: int = 0,
    ) -> "ImpactContext":
        view = state.view()
        nodes = sorted(state.candidate_ids)
        ctx = cls(
            view=view,
            top_k=state.top_k,
            n_max_docs=len(nodes),
            n_samples=n_samples,
        )
        ctx.current_rank = {d: i + 1 for i, d in enumerate(view.ranking)}
        for d in nodes:
            ctx.current_rank.setdefault(d, len(nodes))
        ctx.prior_rank = {d: i + 1 for i, d in enumerate(state.prior_ranking())}

        dag = view.dag
        if dag.number_of_nodes() >= 2 and nx.is_directed_acyclic_graph(dag):
            samples = sample_linear_extensions(dag, n_samples=n_samples, seed=seed)
            counts: dict[tuple[str, str], int] = {}
            for s in samples:
                pos = {n: i for i, n in enumerate(s)}
                for a, b in itertools.combinations(nodes, 2):
                    if a in pos and b in pos:
                        key = (a, b)
                        if pos[a] < pos[b]:
                            counts[key] = counts.get(key, 0) + 1
            n = max(len(samples), 1)
            for a, b in itertools.combinations(nodes, 2):
                ctx.order_prob[(a, b)] = counts.get((a, b), 0) / n
        return ctx


def _pair_nodes(state: "AcquisitionState", pair_id: str) -> tuple[str, str]:
    return state.pair_docs(pair_id)


def prior_rank_proximity(state: "AcquisitionState", pair_id: str, ctx: ImpactContext) -> float:
    a, b = _pair_nodes(state, pair_id)
    dist = abs(ctx.prior_rank.get(a, ctx.n_max_docs) - ctx.prior_rank.get(b, ctx.n_max_docs))
    return float(1.0 / (1.0 + dist))


def current_rank_proximity(state: "AcquisitionState", pair_id: str, ctx: ImpactContext) -> float:
    a, b = _pair_nodes(state, pair_id)
    dist = abs(ctx.current_rank.get(a, ctx.n_max_docs) - ctx.current_rank.get(b, ctx.n_max_docs))
    return float(1.0 / (1.0 + dist))


def topk_boundary_proximity(state: "AcquisitionState", pair_id: str, ctx: ImpactContext) -> float:
    """High when the pair straddles / sits near the current top-k boundary."""
    a, b = _pair_nodes(state, pair_id)
    k = ctx.top_k
    ra = ctx.current_rank.get(a, ctx.n_max_docs)
    rb = ctx.current_rank.get(b, ctx.n_max_docs)
    in_a, in_b = ra <= k, rb <= k
    if in_a != in_b:
        return 1.0  # straddles the cutoff — maximal boundary relevance
    # proximity of the closer endpoint to the boundary
    d = min(abs(ra - k), abs(rb - k), abs(ra - (k + 1)), abs(rb - (k + 1)))
    return float(1.0 / (1.0 + d))


def linear_extension_sensitivity(
    state: "AcquisitionState", pair_id: str, ctx: ImpactContext
) -> float:
    r"""``P(pi(a)<pi(b)) * (1 - P(...))`` from sampled extensions (max at 0.5)."""
    a, b = _pair_nodes(state, pair_id)
    key = (a, b) if a < b else (b, a)
    p = ctx.order_prob.get(key)
    if p is None:
        return 1.0  # not comparable / no samples → fully variable
    return float(4.0 * p * (1.0 - p))  # scaled so 0.5 → 1.0


def topk_membership_sensitivity(
    state: "AcquisitionState", pair_id: str, ctx: ImpactContext
) -> float:
    r"""``P(a in Tk, b not) + P(b in Tk, a not)`` under sampled membership.

    Independence approximation from per-doc top-k membership probabilities.
    """
    a, b = _pair_nodes(state, pair_id)
    pa = ctx.view.topk_membership_prob.get(a, 0.5)
    pb = ctx.view.topk_membership_prob.get(b, 0.5)
    return float(max(0.0, min(1.0, pa * (1 - pb) + pb * (1 - pa))))


def rank_variance_reduction(
    state: "AcquisitionState", pair_id: str, ctx: ImpactContext
) -> float:
    """Proxy: normalized combined sampled rank std of the two endpoints."""
    a, b = _pair_nodes(state, pair_id)
    stats = ctx.view.doc_stats
    sa = float(stats.get(a, {}).get("rank_std", 0.0)) if stats else 0.0
    sb = float(stats.get(b, {}).get("rank_std", 0.0)) if stats else 0.0
    denom = max(ctx.n_max_docs - 1, 1)
    return float(max(0.0, min(1.0, (sa + sb) / (2.0 * denom) * 2.0)))


def reachability_impact(state: "AcquisitionState", pair_id: str, ctx: ImpactContext) -> float:
    """Fraction of currently-incomparable pairs that a→b (or b→a) would imply.

    Adding a→b implies (ancestors(a) ∪ {a}) × (descendants(b) ∪ {b}). We take the
    larger of the two orientations and normalize by the number of incomparable
    pairs.
    """
    a, b = _pair_nodes(state, pair_id)
    dag = ctx.view.dag
    if a not in dag or b not in dag or not nx.is_directed_acyclic_graph(dag):
        return 1.0
    total_inc = max(len(ctx.view.incomparable_pairs), 1)

    def _implied(u: str, v: str) -> int:
        anc = nx.ancestors(dag, u) | {u}
        desc = nx.descendants(dag, v) | {v}
        cnt = 0
        for x in anc:
            for y in desc:
                if x == y:
                    continue
                # only count currently-incomparable ones
                if y not in nx.descendants(dag, x) and x not in nx.descendants(dag, y):
                    cnt += 1
        return cnt

    best = max(_implied(a, b), _implied(b, a))
    return float(min(1.0, best / total_inc))


def repair_impact(state: "AcquisitionState", pair_id: str, ctx: ImpactContext) -> float:
    """1 if both endpoints share a non-trivial SCC (cycle participation), else scaled."""
    a, b = _pair_nodes(state, pair_id)
    for comp in ctx.view.sccs:
        if len(comp) > 1 and a in comp and b in comp:
            return 1.0
    # partial credit if either endpoint is in some cycle
    in_cycle = any(len(c) > 1 and (a in c or b in c) for c in ctx.view.sccs)
    return 0.5 if in_cycle else 0.0


_IMPACT = {
    "prior_rank_proximity": prior_rank_proximity,
    "current_rank_proximity": current_rank_proximity,
    "topk_boundary_proximity": topk_boundary_proximity,
    "linear_extension_sensitivity": linear_extension_sensitivity,
    "topk_membership_sensitivity": topk_membership_sensitivity,
    "rank_variance_reduction": rank_variance_reduction,
    "reachability_impact": reachability_impact,
    "repair_impact": repair_impact,
}


def all_impacts(
    state: "AcquisitionState", pair_id: str, ctx: ImpactContext
) -> dict[str, float]:
    return {name: fn(state, pair_id, ctx) for name, fn in _IMPACT.items()}


def impact(
    state: "AcquisitionState",
    pair_id: str,
    ctx: ImpactContext,
    *,
    method: ImpactMethod = "topk_membership_sensitivity",
    weights: dict[str, float] | None = None,
) -> float:
    if weights:
        vals = all_impacts(state, pair_id, ctx)
        num = sum(weights.get(k, 0.0) * v for k, v in vals.items())
        den = sum(abs(w) for w in weights.values()) or 1.0
        return float(num / den)
    if method in _IMPACT:
        return _IMPACT[method](state, pair_id, ctx)
    raise ValueError(f"Unknown impact method {method!r}")


__all__ = [
    "ImpactContext",
    "ImpactMethod",
    "IMPACT_METHODS",
    "all_impacts",
    "impact",
]
