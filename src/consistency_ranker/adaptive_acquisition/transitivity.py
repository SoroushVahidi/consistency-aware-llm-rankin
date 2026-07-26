"""Transitivity-aware acquisition: skip pairs strongly implied by the graph.

Inferred relations are kept explicitly distinguishable from observed judgments
(the return value carries ``implied=True`` and a ``confidence`` derived from path
strength). Weak long paths do not count as certain, and path-based inference is
optional and ablatable via ``min_path_reliability`` / ``min_path_count``. A
direct call may still be warranted for a consequential, uncertain implied pair —
the policy, not this module, makes that trade-off.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import networkx as nx

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState
    from consistency_ranker.adaptive_acquisition.ranking_impact import ImpactContext


@dataclass
class ImpliedRelation:
    implied: bool
    direction: int  # +1: doc_i → doc_j, -1: reverse, 0: none
    confidence: float
    path_reliability: float
    path_count: int
    contradicts_direct: bool = False


def _path_reliability(dag: nx.DiGraph, path: list[str]) -> float:
    r = 1.0
    for u, v in zip(path[:-1], path[1:]):
        r *= float(dag[u][v].get("reliability", dag[u][v].get("weight", 1.0)))
    return r


def implied_relation(
    state: "AcquisitionState",
    pair_id: str,
    ctx: "ImpactContext",
    *,
    min_path_reliability: float = 0.4,
    min_path_count: int = 1,
    max_paths: int = 8,
) -> ImpliedRelation:
    """Assess whether ``pair_id`` is implied by a sufficiently reliable path."""
    a, b = state.pair_docs(pair_id)
    dag = ctx.view.dag
    if a not in dag or b not in dag or not nx.is_directed_acyclic_graph(dag):
        return ImpliedRelation(False, 0, 0.0, 0.0, 0)

    direction = 0
    src, dst = a, b
    if nx.has_path(dag, a, b):
        direction = 1
    elif nx.has_path(dag, b, a):
        direction, src, dst = -1, b, a
    else:
        return ImpliedRelation(False, 0, 0.0, 0.0, 0)

    best_rel = 0.0
    count = 0
    for path in nx.all_simple_paths(dag, src, dst, cutoff=dag.number_of_nodes()):
        count += 1
        best_rel = max(best_rel, _path_reliability(dag, path))
        if count >= max_paths:
            break

    # A direct observed edge is not "inference"; direct evidence dominates.
    agg = state.aggregates.get(pair_id)
    contradicts = False
    if agg is not None and agg.d != 0 and direction != 0 and agg.d != direction:
        contradicts = True

    implied = best_rel >= min_path_reliability and count >= min_path_count
    confidence = best_rel if implied else 0.0
    return ImpliedRelation(
        implied=implied and not contradicts,
        direction=direction,
        confidence=float(confidence),
        path_reliability=float(best_rel),
        path_count=int(count),
        contradicts_direct=contradicts,
    )


def is_skippable(
    state: "AcquisitionState",
    pair_id: str,
    ctx: "ImpactContext",
    *,
    min_path_reliability: float = 0.4,
    min_path_count: int = 1,
) -> bool:
    """True when a pair may be skipped because it is reliably implied."""
    rel = implied_relation(
        state,
        pair_id,
        ctx,
        min_path_reliability=min_path_reliability,
        min_path_count=min_path_count,
    )
    return rel.implied


__all__ = ["ImpliedRelation", "implied_relation", "is_skippable"]
