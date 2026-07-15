"""Pre-outcome query scoring for active repair mining."""

from __future__ import annotations

import math
import random
from collections import defaultdict

import networkx as nx

from consistency_ranker.failure_mining.graph_features import extended_graph_stats
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.greedy_fas import greedy_fas, greedy_fas_total_weight
from consistency_ranker.mwfas_solver import is_scip_available, solve
from consistency_ranker.pairwise_prefs import Preference


def _vote_entropy(graph: nx.DiGraph) -> float:
    weights = [float(d.get("weight", 1.0)) for _, _, d in graph.edges(data=True)]
    if not weights:
        return 0.0
    total = sum(weights)
    probs = [w / total for w in weights]
    return -sum(p * math.log(p + 1e-12) for p in probs if p > 0)


def _ranker_disagreement(score_maps: list[dict[str, float]], nodes: set[str]) -> float:
    if len(score_maps) < 2:
        return 0.0
    tops = []
    for smap in score_maps:
        ranked = sorted(
            ((n, smap.get(n, 0.0)) for n in nodes if n in smap),
            key=lambda x: (-x[1], x[0]),
        )
        if ranked:
            tops.append(ranked[0][0])
    if len(tops) < 2:
        return 0.0
    return 1.0 - (max(tops.count(t) for t in set(tops)) / len(tops))


def _greedy_exact_disagreement(graph: nx.DiGraph) -> float:
    """Fraction of edges removed differently by greedy vs exact repair on tiny graphs.

    Returns 0.0 (undecided, not "no disagreement") when the graph is too
    large for exact solving or the open-source SCIP backend is not
    installed. Requires ``pip install "consistency-ranker[exact]"``.
    """
    n = graph.number_of_nodes()
    if n > 12 or nx.is_directed_acyclic_graph(graph) or not is_scip_available():
        return 0.0
    _, greedy_removed = greedy_fas(graph)
    _, exact_removed = solve(graph, method="scip")
    g_set = {(u, v) for u, v, _ in greedy_removed}
    e_set = {(u, v) for u, v, _ in exact_removed}
    union = g_set | e_set
    if not union:
        return 0.0
    return len(g_set ^ e_set) / len(union)


def pre_outcome_features(
    prefs: list[Preference],
    *,
    prior_scores: dict[str, float] | None = None,
    ranker_score_maps: list[dict[str, float]] | None = None,
) -> dict[str, float]:
    """Compute features available before measuring repair NDCG."""
    if not prefs:
        return {}
    graph = build_graph(prefs)
    if graph.number_of_nodes() < 2:
        return {}

    prior_rank = None
    if prior_scores:
        prior_rank = sorted(prior_scores, key=lambda n: (-prior_scores.get(n, 0.0), n))

    stats = extended_graph_stats(graph, prior_scores=prior_scores, ref_ranking=prior_rank)
    n_nodes = max(1, graph.number_of_nodes())
    n_edges = max(1, graph.number_of_edges())
    _, removed = greedy_fas(graph)
    fas_w = greedy_fas_total_weight(removed)

    feats = {
        "is_cyclic": 1.0 if stats.get("is_cyclic") else 0.0,
        "largest_scc_frac": float(stats.get("largest_scc_size", 0)) / n_nodes,
        "n_non_trivial_sccs": float(stats.get("n_non_trivial_sccs", 0)),
        "scc_cycle_burden_frac": float(stats.get("scc_cycle_burden", 0)) / n_nodes,
        "n_mutual_pairs_frac": float(stats.get("n_mutual_pairs", 0)) / n_nodes,
        "graph_density": float(stats.get("graph_density", 0)),
        "vote_entropy": _vote_entropy(graph),
        "fas_removed_weight_frac": fas_w / max(float(stats.get("total_edge_weight", 1.0)), 1e-9),
        "prior_top1_margin": float(stats.get("prior_top1_margin", 0)),
        "prior_entropy": float(stats.get("prior_entropy", 0)),
        "ranker_disagreement": _ranker_disagreement(ranker_score_maps or [], set(graph.nodes())),
        "greedy_exact_disagreement": _greedy_exact_disagreement(graph),
        "n_nodes": float(n_nodes),
        "n_edges": float(n_edges),
    }
    return feats


def mining_priority_score(feats: dict[str, float], *, strategy_weights: dict[str, float] | None = None) -> float:
    """Higher = more likely to show nontrivial repair effect."""
    if not feats:
        return 0.0
    w = strategy_weights or {
        "high_cycle": 0.25,
        "disagreement": 0.20,
        "boundary": 0.15,
        "small_graph": 0.10,
        "repair_instability": 0.15,
        "density": 0.05,
        "random": 0.10,
    }
    high_cycle = feats["is_cyclic"] * feats["largest_scc_frac"] + feats["scc_cycle_burden_frac"]
    disagreement = feats["ranker_disagreement"] + feats.get("vote_entropy", 0) / 5.0
    boundary = 1.0 - abs(feats["prior_top1_margin"] - 0.15) / 0.15
    boundary = max(0.0, min(1.0, boundary))
    small_graph = 1.0 if feats["n_nodes"] <= 12 else 0.3 if feats["n_nodes"] <= 16 else 0.0
    repair_instability = feats["fas_removed_weight_frac"] + feats["greedy_exact_disagreement"]
    density = feats["graph_density"]
    jitter = random.Random(int(feats["n_nodes"] * 1000 + feats["n_edges"])).random()

    return (
        w["high_cycle"] * high_cycle
        + w["disagreement"] * disagreement
        + w["boundary"] * boundary
        + w["small_graph"] * small_graph
        + w["repair_instability"] * repair_instability
        + w["density"] * density
        + w["random"] * jitter
    )


def rank_candidates(candidates: list[dict]) -> list[dict]:
    """Sort candidates by mining priority (descending)."""
    scored = []
    for cand in candidates:
        score = mining_priority_score(cand.get("pre_features", {}))
        scored.append({**cand, "mining_priority": score})
    scored.sort(key=lambda c: (-c["mining_priority"], c["dataset"], c["query_id"]))
    return scored


def diversify_batch(ranked: list[dict], batch_size: int) -> list[dict]:
    """Pick a batch with dataset and feature-space diversity."""
    if batch_size >= len(ranked):
        return ranked
    selected: list[dict] = []
    per_dataset: dict[str, int] = defaultdict(int)
    max_per_ds = max(1, batch_size // 3)
    for cand in ranked:
        if len(selected) >= batch_size:
            break
        ds = cand["dataset"]
        if per_dataset[ds] >= max_per_ds and len({c["dataset"] for c in selected}) < 3:
            continue
        selected.append(cand)
        per_dataset[ds] += 1
    if len(selected) < batch_size:
        for cand in ranked:
            if cand not in selected:
                selected.append(cand)
            if len(selected) >= batch_size:
                break
    return selected
