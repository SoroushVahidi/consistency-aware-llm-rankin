"""Graph-aware acquisition signals.

Two acquisition goals are distinguished:

* **inconsistency reduction** — resolve cycles / contradictory evidence
  (``same_scc``, ``cycle_participation``);
* **ambiguity reduction** — resolve important incomparable pairs in a DAG
  (``incomparable_indicator``, ``frontier_co_membership``, reachability signals).

A good policy needs both; ``structural_relevance`` blends them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState
    from consistency_ranker.adaptive_acquisition.ranking_impact import ImpactContext


def same_scc(state: "AcquisitionState", pair_id: str, ctx: "ImpactContext") -> float:
    a, b = state.pair_docs(pair_id)
    for comp in ctx.view.sccs:
        if len(comp) > 1 and a in comp and b in comp:
            return 1.0
    return 0.0


def cycle_participation(state: "AcquisitionState", pair_id: str, ctx: "ImpactContext") -> float:
    """1 if either endpoint sits in a non-trivial SCC, scaled by its size."""
    a, b = state.pair_docs(pair_id)
    best = 0.0
    n = max(ctx.n_max_docs, 1)
    for comp in ctx.view.sccs:
        if len(comp) > 1 and (a in comp or b in comp):
            best = max(best, len(comp) / n)
    return float(best)


def shortest_directed_path(
    state: "AcquisitionState", pair_id: str, ctx: "ImpactContext"
) -> int | None:
    a, b = state.pair_docs(pair_id)
    dag = ctx.view.dag
    if a not in dag or b not in dag:
        return None
    for u, v in ((a, b), (b, a)):
        if nx.has_path(dag, u, v):
            return int(nx.shortest_path_length(dag, u, v))
    return None


def reachability_asymmetry(
    state: "AcquisitionState", pair_id: str, ctx: "ImpactContext"
) -> float:
    """|desc(a) - desc(b)| normalized — large when endpoints occupy very
    different structural positions (resolving them matters more)."""
    a, b = state.pair_docs(pair_id)
    dag = ctx.view.dag
    if a not in dag or b not in dag or not nx.is_directed_acyclic_graph(dag):
        return 0.0
    da = len(nx.descendants(dag, a))
    db = len(nx.descendants(dag, b))
    n = max(ctx.n_max_docs - 1, 1)
    return float(abs(da - db) / n)


def incomparable_indicator(
    state: "AcquisitionState", pair_id: str, ctx: "ImpactContext"
) -> float:
    a, b = state.pair_docs(pair_id)
    key = (a, b) if a < b else (b, a)
    return 1.0 if key in set(ctx.view.incomparable_pairs) else 0.0


def frontier_co_membership(
    state: "AcquisitionState", pair_id: str, ctx: "ImpactContext"
) -> float:
    """Approx probability the two docs appear as competing sources together.

    Uses the sampled pairwise order probability: near-0.5 means they frequently
    appear as tied/interchangeable in the frontier.
    """
    a, b = state.pair_docs(pair_id)
    key = (a, b) if a < b else (b, a)
    p = ctx.order_prob.get(key)
    if p is None:
        return 1.0
    return float(4.0 * p * (1.0 - p))


def structural_relevance(
    state: "AcquisitionState",
    pair_id: str,
    ctx: "ImpactContext",
    *,
    mode: str = "blend",
) -> float:
    """Scalar structural relevance in ``[0, 1]``.

    * ``mode='inconsistency'`` — cycle-focused (same-SCC / cycle participation).
    * ``mode='ambiguity'`` — incomparability / frontier competition.
    * ``mode='blend'`` (default) — max of the two goals so a pair that helps
      *either* objective scores highly.
    """
    inconsistency = max(
        same_scc(state, pair_id, ctx),
        cycle_participation(state, pair_id, ctx),
    )
    ambiguity = max(
        incomparable_indicator(state, pair_id, ctx),
        frontier_co_membership(state, pair_id, ctx),
    )
    if mode == "inconsistency":
        return float(inconsistency)
    if mode == "ambiguity":
        return float(ambiguity)
    if mode == "blend":
        return float(max(inconsistency, ambiguity))
    raise ValueError(f"Unknown structural mode {mode!r}")


__all__ = [
    "same_scc",
    "cycle_participation",
    "shortest_directed_path",
    "reachability_asymmetry",
    "incomparable_indicator",
    "frontier_co_membership",
    "structural_relevance",
]
