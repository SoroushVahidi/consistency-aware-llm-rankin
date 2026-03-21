"""
baseline_ranking.py
===================
Simple baseline ranking methods that do not require cycle removal.

Methods
-------
score_sum_ranking:
    Rank items by their total outgoing preference weight ("wins").  This is
    analogous to a sum-of-scores approach and works even on cyclic graphs.

topological_ranking:
    Rank items by a topological sort of the graph.  Only valid on DAGs; raises
    an error if the graph contains cycles.

borda_ranking:
    Rank items by Borda count: each win over another item contributes 1 point.
    Equivalent to score_sum_ranking with uniform weights.

weighted_out_minus_in_ranking:
    Rank items by weighted out-degree minus weighted in-degree.

copeland_ranking:
    Rank items by out-degree minus in-degree (unweighted Copeland score).

priority_topological_ranking:
    Deterministic topological extraction that uses a priority score map for
    tie-breaking among currently available source nodes.

fas_balance_score_prior_alpha_ranking:
    Hybrid post-repair ranking that combines normalized repaired-graph balance
    with normalized original score-sum prior.

fas_balance_score_prior_alpha_beta_ranking:
    Generalized two-parameter hybrid post-repair ranking:
    beta * norm(repaired-balance) + alpha * norm(original score-sum prior).

fas_balance_score_sum_borda_hybrid_ranking:
    Three-term post-repair hybrid:
    beta * norm(repaired-balance)
    + alpha_s * norm(original score-sum prior)
    + alpha_b * norm(original Borda prior).

hybrid_rrf_fas_regularized_ranking:
    Baseline hybrid variant that combines normalized original score prior with
    normalized repaired-graph balance regularizer.
"""

from __future__ import annotations

import networkx as nx


def _normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    """Min-max normalize score dict to [0, 1] with safe constant fallback."""
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    if hi - lo <= 1.0e-12:
        return {k: 0.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def score_sum_scores(graph: nx.DiGraph) -> dict[str, float]:
    """Return score-sum values (outgoing weighted wins) per node."""
    scores: dict[str, float] = {node: 0.0 for node in graph.nodes()}
    for u, _, data in graph.edges(data=True):
        scores[u] = scores.get(u, 0.0) + float(data.get("weight", 1.0))
    return scores


def borda_scores(graph: nx.DiGraph) -> dict[str, float]:
    """Return Borda-style score (out-degree wins count) per node."""
    return {node: float(graph.out_degree(node)) for node in graph.nodes()}


def _normalized_weighted_sum(
    *,
    component_scores: dict[str, dict[str, float]],
    component_weights: dict[str, float],
    node_order: list[str],
) -> dict[str, float]:
    """Combine multiple score components after per-component normalization."""
    combo: dict[str, float] = {n: 0.0 for n in node_order}
    for name, raw_scores in component_scores.items():
        w = float(component_weights.get(name, 0.0))
        if w == 0.0:
            continue
        norm_scores = _normalize_scores(raw_scores)
        for n in node_order:
            combo[n] += w * float(norm_scores.get(n, 0.0))
    return combo


def score_sum_ranking(graph: nx.DiGraph) -> list[str]:
    """Rank items by total outgoing edge weight (sum of preference scores).

    Items with higher total outgoing weight are ranked first — they "beat"
    others more strongly.

    Parameters
    ----------
    graph:
        Weighted directed preference graph.

    Returns
    -------
    list[str]
        Node ids sorted from best (highest score) to worst.
    """
    scores = score_sum_scores(graph)
    return sorted(scores, key=lambda n: (-scores[n], n))


def topological_ranking(graph: nx.DiGraph) -> list[str]:
    """Rank items using a topological sort of the graph.

    Parameters
    ----------
    graph:
        A directed **acyclic** graph (DAG).

    Returns
    -------
    list[str]
        Node ids in topological order (sources first).

    Raises
    ------
    networkx.NetworkXUnfeasible
        If *graph* contains a cycle.
    """
    if not nx.is_directed_acyclic_graph(graph):
        raise nx.NetworkXUnfeasible(
            "Topological sort requires a DAG. The graph contains cycles. "
            "Use greedy_fas or mwfas_solver to remove cycles first."
        )
    return list(nx.topological_sort(graph))


def priority_topological_ranking(
    dag: nx.DiGraph,
    priority_scores: dict[str, float],
) -> list[str]:
    """Topological ranking with deterministic priority tie-breaking.

    At each step, choose the currently available source node with highest
    ``priority_scores[node]``; ties fall back to node id for determinism.
    """
    if not nx.is_directed_acyclic_graph(dag):
        raise nx.NetworkXUnfeasible(
            "priority_topological_ranking requires a DAG. "
            "Use greedy_fas or mwfas_solver first."
        )
    in_deg = {n: dag.in_degree(n) for n in dag.nodes()}
    available = [n for n, d in in_deg.items() if d == 0]
    ranking: list[str] = []
    while available:
        best = max(available, key=lambda n: (priority_scores.get(n, 0.0), n))
        available.remove(best)
        ranking.append(best)
        for child in dag.successors(best):
            in_deg[child] -= 1
            if in_deg[child] == 0:
                available.append(child)
    return ranking


def weighted_out_minus_in_ranking(graph: nx.DiGraph) -> list[str]:
    """Rank nodes by weighted out-degree minus weighted in-degree."""
    scores = weighted_out_minus_in_scores(graph)
    return sorted(scores, key=lambda n: (-scores[n], n))


def weighted_out_minus_in_scores(graph: nx.DiGraph) -> dict[str, float]:
    """Return weighted out-minus-in balance scores per node."""
    scores: dict[str, float] = {n: 0.0 for n in graph.nodes()}
    for u, v, data in graph.edges(data=True):
        w = float(data.get("weight", 1.0))
        scores[u] += w
        scores[v] -= w
    return scores


def fas_balance_score_prior_alpha_ranking(
    repaired_graph: nx.DiGraph,
    score_sum_prior_scores: dict[str, float],
    alpha: float = 0.5,
) -> list[str]:
    """Hybrid score = norm(balance_repaired) + alpha * norm(score_sum_prior)."""
    return fas_balance_score_prior_alpha_beta_ranking(
        repaired_graph,
        score_sum_prior_scores,
        alpha=alpha,
        beta=1.0,
    )


def fas_balance_score_prior_alpha_beta_ranking(
    repaired_graph: nx.DiGraph,
    score_sum_prior_scores: dict[str, float],
    alpha: float = 0.5,
    beta: float = 1.0,
) -> list[str]:
    """Hybrid score = beta * norm(balance_repaired) + alpha * norm(score_sum_prior)."""
    if alpha < 0:
        raise ValueError(f"alpha must be non-negative. Got {alpha}.")
    if beta < 0:
        raise ValueError(f"beta must be non-negative. Got {beta}.")
    nodes = list(repaired_graph.nodes())
    combo = _normalized_weighted_sum(
        component_scores={
            "balance": weighted_out_minus_in_scores(repaired_graph),
            "score_sum": {n: float(score_sum_prior_scores.get(n, 0.0)) for n in nodes},
        },
        component_weights={"balance": beta, "score_sum": alpha},
        node_order=nodes,
    )
    return sorted(combo, key=lambda n: (-combo[n], n))


def fas_balance_score_sum_borda_hybrid_ranking(
    repaired_graph: nx.DiGraph,
    score_sum_prior_scores: dict[str, float],
    borda_prior_scores: dict[str, float],
    *,
    alpha_s: float = 1.0,
    alpha_b: float = 1.0,
    beta: float = 0.1,
) -> list[str]:
    """Hybrid score with repaired balance + score-sum prior + Borda prior."""
    if alpha_s < 0:
        raise ValueError(f"alpha_s must be non-negative. Got {alpha_s}.")
    if alpha_b < 0:
        raise ValueError(f"alpha_b must be non-negative. Got {alpha_b}.")
    if beta < 0:
        raise ValueError(f"beta must be non-negative. Got {beta}.")
    nodes = list(repaired_graph.nodes())
    combo = _normalized_weighted_sum(
        component_scores={
            "balance": weighted_out_minus_in_scores(repaired_graph),
            "score_sum": {n: float(score_sum_prior_scores.get(n, 0.0)) for n in nodes},
            "borda": {n: float(borda_prior_scores.get(n, 0.0)) for n in nodes},
        },
        component_weights={"balance": beta, "score_sum": alpha_s, "borda": alpha_b},
        node_order=nodes,
    )
    return sorted(combo, key=lambda n: (-combo[n], n))


def hybrid_rrf_fas_regularized_ranking(
    repaired_graph: nx.DiGraph,
    score_sum_prior_scores: dict[str, float],
    fas_regularization: float = 0.2,
) -> list[str]:
    """Hybrid score = norm(score_sum_prior) + lambda * norm(balance_repaired)."""
    if fas_regularization < 0:
        raise ValueError(
            f"fas_regularization must be non-negative. Got {fas_regularization}."
        )
    balance_raw = weighted_out_minus_in_scores(repaired_graph)
    prior_raw = {n: float(score_sum_prior_scores.get(n, 0.0)) for n in repaired_graph.nodes()}
    bal_n = _normalize_scores(balance_raw)
    prior_n = _normalize_scores(prior_raw)
    combo = {
        n: prior_n.get(n, 0.0) + fas_regularization * bal_n.get(n, 0.0)
        for n in repaired_graph.nodes()
    }
    return sorted(combo, key=lambda n: (-combo[n], n))


def copeland_ranking(graph: nx.DiGraph) -> list[str]:
    """Rank by Copeland wins-losses score (out-degree minus in-degree)."""
    scores = {n: graph.out_degree(n) - graph.in_degree(n) for n in graph.nodes()}
    return sorted(scores, key=lambda n: (-scores[n], n))


def pagerank_ranking(
    graph: nx.DiGraph,
    alpha: float = 0.85,
    max_iter: int = 100,
    tol: float = 1.0e-6,
) -> list[str]:
    """Rank items using a weighted PageRank-style centrality score.

    Items that are beaten by many other highly-ranked items accumulate a
    higher "authority" score.  The graph is **reversed** before computing
    PageRank so that an edge ``u → v`` (meaning "u beats v") translates to
    *authority flowing from u to v* — i.e. being beaten by a strong
    competitor increases your authority.

    In practice, nodes with many high-weight incoming edges (i.e. beaten by
    strong competitors) receive high scores.  To produce a *preference*
    ranking (best first), the scores are sorted in **descending** order.

    Parameters
    ----------
    graph:
        Weighted directed preference graph.  Edge weights are used.
    alpha:
        PageRank damping factor.  Default is 0.85.
    max_iter:
        Maximum number of power-iteration steps.
    tol:
        Convergence tolerance for power iteration.

    Returns
    -------
    list[str]
        Node ids sorted from highest to lowest PageRank score.

    Notes
    -----
    PageRank on the reversed graph is O((n + e) · iter) where *iter* is the
    number of power-iteration steps until convergence.  For sparse preference
    graphs this is fast (typically < 50 iterations).

    # TODO: If called repeatedly on the same graph, cache the PageRank vector
    #       since it is deterministic for a fixed graph + alpha.
    """
    # Work on the transposed graph so that winning over a strong node raises
    # your score (incoming edges in the reversed graph = "winning" edges here).
    reversed_graph = graph.reverse(copy=True)
    scores = nx.pagerank(
        reversed_graph,
        alpha=alpha,
        weight="weight",
        max_iter=max_iter,
        tol=tol,
    )
    return sorted(scores, key=lambda n: scores[n], reverse=True)


def borda_ranking(graph: nx.DiGraph) -> list[str]:
    """Rank items by Borda count (number of items each node beats).

    Parameters
    ----------
    graph:
        A directed preference graph (weights ignored; only edge presence counts).

    Returns
    -------
    list[str]
        Node ids sorted from most wins to fewest.
    """
    wins = borda_scores(graph)
    return sorted(wins, key=lambda n: (-wins[n], n))
