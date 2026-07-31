"""Guarded topological extraction variants.

Prior-priority remains the headline hard extractor; these variants reduce
anchoring when prior quality is low.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import networkx as nx

from consistency_ranker.baseline_ranking import priority_topological_ranking
from consistency_ranker.dag_linear_extensions import (
    assert_valid_topological_order,
    random_topological_ranking,
)
from consistency_ranker.prior_robust.adaptive_prior import blend_priorities

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState

ExtractionMethod = Literal[
    "prior_priority",
    "confidence_gated",
    "mixed_priority",
    "evidence_only",
    "prior_randomized",
    "multi_prior_consensus",
]


def evidence_priority_scores(state: "AcquisitionState") -> dict[str, float]:
    scores = {d: 0.0 for d in state.candidate_ids}
    for agg in state.aggregates.values():
        if agg.d == 0:
            continue
        w = abs(float(agg.m)) * max(float(agg.n_valid_directional), 1)
        winner = agg.doc_i if agg.d == 1 else agg.doc_j
        loser = agg.doc_j if agg.d == 1 else agg.doc_i
        scores[winner] = scores.get(winner, 0.0) + w
        scores[loser] = scores.get(loser, 0.0) - 0.5 * w
    return scores


def node_acquired_support(state: "AcquisitionState", doc: str) -> float:
    """Total reliability-weighted acquired evidence involving ``doc``."""
    total = 0.0
    for e in state.evidence:
        if e.z == 0:
            continue
        if e.doc_i == doc or e.doc_j == doc:
            total += 1.0
    return total


def confidence_gated_priority(
    state: "AcquisitionState",
    *,
    min_support: float = 1.0,
    lambda_q: float = 0.5,
) -> dict[str, float]:
    """Use prior only for nodes with insufficient independent support."""
    ev = evidence_priority_scores(state)
    out = {}
    for d in state.candidate_ids:
        if node_acquired_support(state, d) >= min_support:
            out[d] = ev.get(d, 0.0)
        else:
            # Blend; low λ when we lack support still uses some prior.
            out[d] = (
                float(lambda_q) * float(state.prior_scores.get(d, 0.0))
                + (1.0 - float(lambda_q)) * ev.get(d, 0.0)
            )
    return out


def extract_ranking(
    state: "AcquisitionState",
    *,
    method: ExtractionMethod = "prior_priority",
    lambda_q: float = 0.5,
    alt_priors: list[dict[str, float]] | None = None,
    seed: int = 0,
) -> list[str]:
    """Extract a valid topological ranking with the requested guard."""
    dag = state.view().dag
    if dag.number_of_nodes() == 0:
        return list(state.prior_ranking())
    if not nx.is_directed_acyclic_graph(dag):
        # Should not happen after repair; fall back to prior order.
        return list(state.prior_ranking())

    if method == "prior_priority":
        ranking = priority_topological_ranking(dag, state.prior_scores)
    elif method == "evidence_only":
        ranking = priority_topological_ranking(dag, evidence_priority_scores(state))
    elif method == "mixed_priority":
        prio = blend_priorities(
            state.prior_scores, evidence_priority_scores(state), lambda_q
        )
        ranking = priority_topological_ranking(dag, prio)
    elif method == "confidence_gated":
        prio = confidence_gated_priority(state, lambda_q=lambda_q)
        ranking = priority_topological_ranking(dag, prio)
    elif method == "prior_randomized":
        ranking = random_topological_ranking(dag, seed=seed)
    elif method == "multi_prior_consensus":
        priors = [state.prior_scores] + list(alt_priors or [])
        # Average ranks across priors as consensus priority.
        from collections import defaultdict

        rank_sum: dict[str, float] = defaultdict(float)
        for p in priors:
            order = sorted(p, key=lambda d: (-float(p.get(d, 0.0)), d))
            for i, d in enumerate(order):
                if d in dag:
                    rank_sum[d] += float(len(order) - i)
        # Missing nodes get 0.
        for d in dag.nodes():
            rank_sum.setdefault(d, 0.0)
        ranking = priority_topological_ranking(dag, dict(rank_sum))
    else:
        raise ValueError(f"Unknown extraction method {method!r}")

    # Ensure all candidates present.
    missing = [d for d in state.prior_ranking() if d not in ranking]
    ranking = ranking + missing
    # Validate on DAG nodes only.
    dag_nodes = [d for d in ranking if d in dag]
    assert_valid_topological_order(dag, dag_nodes)
    return ranking


__all__ = [
    "ExtractionMethod",
    "evidence_priority_scores",
    "confidence_gated_priority",
    "extract_ranking",
]
