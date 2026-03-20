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


def local_adjacent_swap_refinement(
    ranking: list[str],
    graph: nx.DiGraph,
    objective: str = "bew",
    max_iter: int = 1000,
) -> list[str]:
    """Refine a ranking by greedy adjacent-swap hill climbing (local Kemenization-style).

    Inspired by Dwork et al.'s local Kemenization: repeatedly consider adjacent
    swaps and accept if they improve consistency with the preference graph.

    Parameters
    ----------
    ranking:
        Initial ranking (e.g., from RRF).
    graph:
        Weighted directed preference graph.
    objective:
        - "bew": minimize backward edge weight (sum of weights of violated edges)
        - "count": minimize number of backward edges (unit weight per violation)
    max_iter:
        Maximum number of swap passes to prevent infinite loops.

    Returns
    -------
    list[str]
        Refined ranking (copy; original unchanged).
    """
    r = list(ranking)
    n = len(r)
    if n < 2:
        return r

    def _bew(rank: list[str], use_weights: bool = True) -> float:
        pos = {x: i for i, x in enumerate(rank)}
        total = 0.0
        for u, v, data in graph.edges(data=True):
            if pos.get(u) is None or pos.get(v) is None:
                continue
            if pos[v] < pos[u]:  # backward
                total += data.get("weight", 1.0) if use_weights else 1.0
        return total

    use_weights = objective == "bew"
    current = _bew(r, use_weights)

    for _ in range(max_iter):
        improved = False
        for i in range(n - 1):
            a, b = r[i], r[i + 1]
            # Swap: r becomes ... b, a, ...
            r[i], r[i + 1] = b, a
            new_bew = _bew(r, use_weights)
            if new_bew < current:
                current = new_bew
                improved = True
                break
            # Revert
            r[i], r[i + 1] = a, b
        if not improved:
            break
    return r


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
