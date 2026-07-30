"""Acceptance modes for repair-frontier candidates.

Every mode compares a candidate against the incumbent's backward-edge-weight
measured on the **original full graph** (not just a touched subgraph), so
whole-graph and SCC-local candidates are comparable on the same scale. The
incumbent ranking is always a valid candidate and is what gets kept when
nothing else passes (abstain).
"""

from __future__ import annotations

import networkx as nx

from consistency_ranker.evaluation import ndcg_at_k
from consistency_ranker.failure_mining.graph_features import backward_edge_weight


def candidate_objective(graph: nx.DiGraph, ranking: list[str]) -> float:
    """Backward-edge-weight of *ranking* against the original full *graph*."""
    return backward_edge_weight(graph, ranking)


def accept_candidate(
    graph: nx.DiGraph,
    incumbent_ranking: list[str],
    candidate_ranking: list[str],
    *,
    mode: str,
    margin: float = 0.0,
    relevance_map: dict[str, int] | None = None,
    ndcg_k: int = 10,
) -> bool:
    """Whether *candidate_ranking* is accepted over *incumbent_ranking*.

    - ``objective_only``: accept iff the candidate's backward-edge-weight
      (on the original graph) is strictly less than the incumbent's.
    - ``conservative``: accept iff the fractional objective improvement
      exceeds *margin* -- a configurable, label-free surrogate.
    - ``oracle_analysis_only``: accept iff candidate nDCG beats incumbent
      nDCG. Uses relevance labels for RETROSPECTIVE ANALYSIS ONLY -- never
      a deployable policy; callers must exclude candidates accepted under
      this mode from anything selection-related.
    """
    if candidate_ranking == incumbent_ranking:
        return True

    if mode == "objective_only":
        incumbent_obj = candidate_objective(graph, incumbent_ranking)
        candidate_obj = candidate_objective(graph, candidate_ranking)
        return candidate_obj < incumbent_obj
    if mode == "conservative":
        incumbent_obj = candidate_objective(graph, incumbent_ranking)
        candidate_obj = candidate_objective(graph, candidate_ranking)
        if incumbent_obj <= 0:
            return False
        improvement_frac = (incumbent_obj - candidate_obj) / incumbent_obj
        return improvement_frac > margin
    if mode == "oracle_analysis_only":
        if relevance_map is None:
            raise ValueError(
                "oracle_analysis_only requires relevance_map (retrospective analysis "
                "only -- never a deployable policy)"
            )
        incumbent_ndcg = ndcg_at_k(incumbent_ranking, relevance_map, k=ndcg_k)
        candidate_ndcg = ndcg_at_k(candidate_ranking, relevance_map, k=ndcg_k)
        return candidate_ndcg > incumbent_ndcg
    raise ValueError(f"Unknown acceptance mode: {mode!r}")


__all__ = ["candidate_objective", "accept_candidate"]
