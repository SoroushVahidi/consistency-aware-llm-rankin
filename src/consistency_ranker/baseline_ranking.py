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
"""

from __future__ import annotations

import networkx as nx


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
    scores: dict[str, float] = {node: 0.0 for node in graph.nodes()}
    for u, v, data in graph.edges(data=True):
        scores[u] = scores.get(u, 0.0) + data.get("weight", 1.0)
    return sorted(scores, key=lambda n: scores[n], reverse=True)


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


def weighted_balance_ranking(graph: nx.DiGraph) -> list[str]:
    """Rank nodes by weighted out-degree minus weighted in-degree.

    Parameters
    ----------
    graph:
        Weighted directed preference graph.

    Returns
    -------
    list[str]
        Node ids sorted from largest weighted balance to smallest.
    """
    scores: dict[str, float] = {n: 0.0 for n in graph.nodes()}
    for u, v, data in graph.edges(data=True):
        w = data.get("weight", 1.0)
        scores[u] += w
        scores[v] -= w
    return sorted(scores, key=lambda n: (-scores[n], n))


def copeland_ranking(graph: nx.DiGraph) -> list[str]:
    """Rank nodes by Copeland wins-losses score.

    Parameters
    ----------
    graph:
        Directed preference graph.

    Returns
    -------
    list[str]
        Node ids sorted from highest to lowest Copeland score.
    """
    scores: dict[str, int] = {n: 0 for n in graph.nodes()}
    for n in graph.nodes():
        scores[n] = graph.out_degree(n) - graph.in_degree(n)
    return sorted(scores, key=lambda n: (-scores[n], n))


def priority_topological_ranking(
    dag: nx.DiGraph,
    priority_scores: dict[str, float],
) -> list[str]:
    """Topological ranking with deterministic priority tie-breaking.

    Parameters
    ----------
    dag:
        Directed acyclic graph.
    priority_scores:
        Per-node scores used to resolve ties among currently available
        zero-in-degree nodes.

    Returns
    -------
    list[str]
        Node ids in a valid topological order.
    """
    if not nx.is_directed_acyclic_graph(dag):
        raise nx.NetworkXUnfeasible(
            "Priority topological ranking requires a DAG. The graph contains cycles."
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


def hybrid_regularized_ranking(
    dag: nx.DiGraph,
    prior_scores: dict[str, float],
    regularization: float = 0.2,
) -> list[str]:
    """Combine prior scores with repaired-DAG weighted balance scores.

    Parameters
    ----------
    dag:
        Repaired DAG.
    prior_scores:
        Original-graph score prior.
    regularization:
        Weight assigned to the repaired-graph balance component.

    Returns
    -------
    list[str]
        Node ids sorted by the hybrid score.
    """
    if not dag.nodes():
        return []

    balance: dict[str, float] = {n: 0.0 for n in dag.nodes()}
    for u, v, data in dag.edges(data=True):
        w = data.get("weight", 1.0)
        balance[u] += w
        balance[v] -= w

    def _normalize(scores: dict[str, float]) -> dict[str, float]:
        vals = list(scores.values())
        lo, hi = min(vals), max(vals)
        if hi - lo <= 1.0e-12:
            return {k: 0.0 for k in scores}
        return {k: (v - lo) / (hi - lo) for k, v in scores.items()}

    prior_n = _normalize({n: prior_scores.get(n, 0.0) for n in dag.nodes()})
    bal_n = _normalize(balance)
    combo = {
        n: prior_n.get(n, 0.0) + regularization * bal_n.get(n, 0.0)
        for n in dag.nodes()
    }
    return sorted(combo, key=lambda n: (-combo[n], n))


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
    wins: dict[str, int] = {node: 0 for node in graph.nodes()}
    for u in graph.nodes():
        wins[u] = graph.out_degree(u)
    return sorted(wins, key=lambda n: wins[n], reverse=True)
