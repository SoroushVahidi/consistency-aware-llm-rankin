"""Per-query-graph repair outcome: does whole-graph greedy MWFAS repair
improve, harm, or leave nDCG unchanged?

"Repair" here means the same whole-graph greedy MWFAS repair used
throughout this research thread as the canonical baseline (the original
multi-provider pilot, the reviewer-concerns program, and the repair-
frontier program's ``whole_graph_greedy`` candidate) -- recomputed directly
from the SAME already-materialized graphs (built via
``run_repair_frontier_pilot.load_all_units``/``graphs_for_unit``, zero new
API calls) rather than parsed from a prior report's output files, so this
module has no file-format coupling to either finished study.

Reuses :func:`consistency_ranker.mwfas_solver.solve`,
:func:`consistency_ranker.baseline_ranking.copeland_ranking`, and
:func:`consistency_ranker.evaluation.ndcg_at_k`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import networkx as nx

from consistency_ranker.baseline_ranking import copeland_ranking
from consistency_ranker.evaluation import ndcg_at_k
from consistency_ranker.mwfas_solver import solve as mwfas_solve
from consistency_ranker.pairwise_prefs import Preference

from .features import (
    PostRepairFeatures,
    PreRepairFeatures,
    compute_post_repair_features,
    compute_pre_repair_features,
)

Outcome = Literal["improves", "harms", "no_change"]
_TIE_TOL = 1e-12


@dataclass(frozen=True)
class QueryGraphDiagnostic:
    key: tuple
    dataset: str
    query_id: str
    provider: str
    pool_size: int
    ndcg_preserve: float
    ndcg_repair: float
    delta: float
    outcome: Outcome
    pre_repair: PreRepairFeatures
    post_repair: PostRepairFeatures


def _classify(delta: float) -> Outcome:
    if delta > _TIE_TOL:
        return "improves"
    if delta < -_TIE_TOL:
        return "harms"
    return "no_change"


def evaluate_repair_outcome(
    graph: nx.DiGraph,
    relevance_map: dict[str, int],
    *,
    key: tuple,
    dataset: str,
    query_id: str,
    provider: str,
    pool_size: int,
    provider_prefs: dict[str, list[Preference]] | None = None,
    ndcg_k: int = 10,
) -> QueryGraphDiagnostic:
    incumbent_ranking = copeland_ranking(graph)
    dag, removed = mwfas_solve(graph, method="greedy")
    repaired_ranking = copeland_ranking(dag)

    ndcg_preserve = ndcg_at_k(incumbent_ranking, relevance_map, k=ndcg_k)
    ndcg_repair = ndcg_at_k(repaired_ranking, relevance_map, k=ndcg_k)
    delta = ndcg_repair - ndcg_preserve

    total_weight = sum(float(d.get("weight", 1.0)) for _, _, d in graph.edges(data=True))
    pre = compute_pre_repair_features(
        graph, pool_size=pool_size, provider_prefs=provider_prefs, topk=ndcg_k
    )
    post = compute_post_repair_features(total_weight, removed)

    return QueryGraphDiagnostic(
        key=key,
        dataset=dataset,
        query_id=query_id,
        provider=provider,
        pool_size=pool_size,
        ndcg_preserve=ndcg_preserve,
        ndcg_repair=ndcg_repair,
        delta=delta,
        outcome=_classify(delta),
        pre_repair=pre,
        post_repair=post,
    )


__all__ = ["Outcome", "QueryGraphDiagnostic", "evaluate_repair_outcome"]
