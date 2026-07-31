"""Graph construction and cycle/repair metrics from normalized judgments."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

import networkx as nx

from consistency_ranker.baseline_ranking import (
    priority_topological_ranking,
    score_sum_scores,
)
from consistency_ranker.dag_ambiguity import dag_ambiguity_features
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.greedy_fas import greedy_fas, greedy_fas_total_weight
from consistency_ranker.pairwise_prefs import Preference


def records_to_preferences(
    records: Iterable[dict[str, Any]],
    *,
    query_id: str | None = None,
    orientation_consistent_only: bool = False,
) -> list[Preference]:
    """Build Preference list from normalized judgment records for one query."""
    rows = [
        r
        for r in records
        if r.get("valid")
        and r.get("normalized_winner_id") is not None
        and (query_id is None or r.get("query_id") == query_id)
    ]
    if orientation_consistent_only:
        # Keep an edge only if ab and ba agree.
        by_pair: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        for r in rows:
            by_pair[r["canonical_pair_id"]][r["displayed_orientation"]] = r
        filtered = []
        for _pid, orients in by_pair.items():
            if "ab" not in orients or "ba" not in orients:
                continue
            if orients["ab"]["normalized_winner_id"] == orients["ba"]["normalized_winner_id"]:
                filtered.append(orients["ab"])
        rows = filtered

    prefs: list[Preference] = []
    for r in rows:
        winner = str(r["normalized_winner_id"])
        a, b = str(r["doc_a_id"]), str(r["doc_b_id"])
        loser = b if winner == a else a
        prefs.append(Preference(winner=winner, loser=loser, weight=1.0))
    return prefs


def evaluate_preference_graph(prefs: list[Preference]) -> dict[str, Any]:
    """Cycle stats, FAS repair, DAG ambiguity, prior-priority extraction."""
    if not prefs:
        return {
            "n_prefs": 0,
            "n_nodes": 0,
            "n_edges": 0,
            "n_two_cycles": 0,
            "n_sccs": 0,
            "n_nontrivial_sccs": 0,
            "fas_removed_edges": 0,
            "fas_removed_weight": 0.0,
            "retained_edge_fraction": None,
            "originally_acyclic": True,
            "ambiguity": None,
            "ranking": [],
        }
    graph = build_graph(prefs)
    # Two-cycles: mutual edges.
    two_cycles = 0
    for u, v in list(graph.edges()):
        if graph.has_edge(v, u) and u < v:
            two_cycles += 1
    sccs = list(nx.strongly_connected_components(graph))
    n_sccs_nontrivial = sum(1 for c in sccs if len(c) > 1)
    was_dag = nx.is_directed_acyclic_graph(graph)
    if was_dag:
        dag = graph.copy()
        removed = []
        fas_w = 0.0
    else:
        dag, removed = greedy_fas(graph)
        fas_w = greedy_fas_total_weight(removed)
    n_edges = graph.number_of_edges()
    retained = dag.number_of_edges() / n_edges if n_edges else None
    amb = dag_ambiguity_features(dag) if dag.number_of_nodes() else None
    prior = score_sum_scores(graph)
    ranking = priority_topological_ranking(dag, prior) if dag.number_of_nodes() else []
    return {
        "n_prefs": len(prefs),
        "n_nodes": graph.number_of_nodes(),
        "n_edges": n_edges,
        "n_two_cycles": two_cycles,
        "n_sccs": len(sccs),
        "n_nontrivial_sccs": n_sccs_nontrivial,
        "fas_removed_edges": len(removed),
        "fas_removed_weight": fas_w,
        "retained_edge_fraction": retained,
        "originally_acyclic": was_dag,
        "ambiguity": amb,
        "ranking": ranking,
    }
