"""Extended graph statistics for failure-mining forensic records."""

from __future__ import annotations

import math
from collections import defaultdict

import networkx as nx

from consistency_ranker.qrels_reference import (
    qrels_backward_edge_weight,
    qrels_pairwise_inconsistency,
)


def _edge_list(graph: nx.DiGraph) -> list[dict]:
    edges: list[dict] = []
    for u, v, data in graph.edges(data=True):
        edges.append(
            {
                "source": u,
                "target": v,
                "weight": float(data.get("weight", 1.0)),
                "margin": float(data.get("margin", data.get("weight", 1.0))),
                "voter": str(data.get("voter", data.get("source_ranker", ""))),
            }
        )
    return edges


def _mutual_pair_count(graph: nx.DiGraph) -> int:
    directed = {(u, v) for u, v in graph.edges()}
    count = 0
    seen: set[frozenset[str]] = set()
    for u, v in directed:
        key = frozenset({u, v})
        if key in seen:
            continue
        if (v, u) in directed:
            count += 1
            seen.add(key)
    return count


def _prior_dominance_stats(
    graph: nx.DiGraph,
    prior_scores: dict[str, float],
) -> dict[str, float]:
    if not prior_scores:
        return {"prior_top1_margin": 0.0, "prior_entropy": 0.0, "prior_gini": 0.0}
    vals = [float(prior_scores.get(n, 0.0)) for n in graph.nodes()]
    if not vals:
        return {"prior_top1_margin": 0.0, "prior_entropy": 0.0, "prior_gini": 0.0}
    sorted_vals = sorted(vals, reverse=True)
    top1 = sorted_vals[0]
    top2 = sorted_vals[1] if len(sorted_vals) > 1 else 0.0
    lo, hi = min(vals), max(vals)
    norm = {n: (prior_scores.get(n, 0.0) - lo) / (hi - lo + 1e-12) for n in graph.nodes()}
    probs = [v / (sum(norm.values()) + 1e-12) for v in norm.values()]
    entropy = -sum(p * math.log(p + 1e-12) for p in probs if p > 0)
    mean_v = sum(vals) / len(vals)
    gini_num = sum(abs(a - b) for a in vals for b in vals)
    gini = gini_num / (2 * len(vals) ** 2 * (mean_v + 1e-12)) if vals else 0.0
    return {
        "prior_top1_margin": float(top1 - top2),
        "prior_entropy": float(entropy),
        "prior_gini": float(gini),
    }


def _margin_stats(graph: nx.DiGraph) -> dict[str, float]:
    weights = [float(d.get("weight", 1.0)) for _, _, d in graph.edges(data=True)]
    if not weights:
        return {"edge_weight_mean": 0.0, "edge_weight_std": 0.0, "edge_weight_max": 0.0}
    mean_w = sum(weights) / len(weights)
    var = sum((w - mean_w) ** 2 for w in weights) / len(weights)
    return {
        "edge_weight_mean": mean_w,
        "edge_weight_std": math.sqrt(var),
        "edge_weight_max": max(weights),
    }


def _scc_membership(graph: nx.DiGraph) -> dict[str, int]:
    membership: dict[str, int] = {}
    for idx, comp in enumerate(nx.strongly_connected_components(graph)):
        for node in comp:
            membership[node] = idx
    return membership


def backward_edge_weight(graph: nx.DiGraph, ranking: list[str]) -> float:
    pos = {node: i for i, node in enumerate(ranking)}
    total = 0.0
    for u, v, data in graph.edges(data=True):
        u_pos = pos.get(u)
        v_pos = pos.get(v)
        if u_pos is not None and v_pos is not None and v_pos < u_pos:
            total += float(data.get("weight", 1.0))
    return total


def extended_graph_stats(
    graph: nx.DiGraph,
    *,
    prior_scores: dict[str, float] | None = None,
    ref_ranking: list[str] | None = None,
    reference_judged_rel_map: dict[str, int] | None = None,
) -> dict:
    """Collect graph features used for failure correlation analysis."""
    summary_base = {
        "n_nodes": graph.number_of_nodes(),
        "n_edges": graph.number_of_edges(),
        "graph_density": nx.density(graph) if graph.number_of_nodes() > 1 else 0.0,
        "is_dag": nx.is_directed_acyclic_graph(graph),
        "is_cyclic": not nx.is_directed_acyclic_graph(graph),
    }
    sccs = list(nx.strongly_connected_components(graph))
    n_sccs = len(sccs)
    largest_scc = max((len(s) for s in sccs), default=0)
    weights = [float(d.get("weight", 1.0)) for _, _, d in graph.edges(data=True)]
    total_weight = sum(weights)

    pic_pre = None
    bew_pre = None
    if reference_judged_rel_map is not None:
        pic_pre = qrels_pairwise_inconsistency(graph, reference_judged_rel_map)
        bew_pre = qrels_backward_edge_weight(graph, reference_judged_rel_map)
    elif ref_ranking:
        pos = {node: i for i, node in enumerate(ref_ranking)}
        pic_pre = 0
        bew_pre = 0.0
        for u, v, data in graph.edges(data=True):
            u_pos = pos.get(u)
            v_pos = pos.get(v)
            if u_pos is not None and v_pos is not None and v_pos < u_pos:
                pic_pre += 1
                bew_pre += float(data.get("weight", 1.0))

    voter_counts: dict[str, int] = defaultdict(int)
    for _, _, data in graph.edges(data=True):
        voter = str(data.get("voter", data.get("source_ranker", "unknown")))
        voter_counts[voter] += 1

    out = {
        **summary_base,
        "n_sccs": n_sccs,
        "largest_scc_size": largest_scc,
        "n_non_trivial_sccs": sum(1 for s in sccs if len(s) > 1),
        "scc_cycle_burden": sum(len(s) for s in sccs if len(s) > 1),
        "scc_membership": _scc_membership(graph),
        "n_mutual_pairs": _mutual_pair_count(graph),
        "total_edge_weight": total_weight,
        "pairwise_inconsistency_pre_repair": pic_pre,
        "backward_edge_weight_pre_repair": bew_pre,
        "preference_edges": _edge_list(graph),
        "voter_edge_counts": dict(voter_counts),
        **_margin_stats(graph),
    }
    if prior_scores:
        out.update(_prior_dominance_stats(graph, prior_scores))
    return out
