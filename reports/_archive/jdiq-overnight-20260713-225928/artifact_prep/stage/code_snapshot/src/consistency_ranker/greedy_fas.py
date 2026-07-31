"""
greedy_fas.py
=============
Greedy heuristic for the Minimum Weighted Feedback Arc Set (MWFAS) problem.

Strategy
--------
Iteratively find a cycle in the graph and remove the **minimum-weight edge**
from that cycle.  Repeat until the graph is a DAG.

This is a simple O(C · E) heuristic (C = number of cycle-removal iterations,
E = edges per cycle) that gives reasonable results in practice, even though it
does not guarantee the globally optimal solution.

For exact solutions see :mod:`mwfas_solver`.
"""

from __future__ import annotations

import copy

import networkx as nx


def greedy_fas(graph: nx.DiGraph) -> tuple[nx.DiGraph, list[tuple[str, str, float]]]:
    """Remove cycles from *graph* by iteratively deleting minimum-weight edges.

    Parameters
    ----------
    graph:
        Weighted directed preference graph.  The original graph is **not**
        modified.

    Returns
    -------
    dag : networkx.DiGraph
        A copy of *graph* with all cycle-forming edges removed.
    removed_edges : list[(u, v, weight)]
        The edges that were removed, in the order they were removed.

    **Complexity note:** Each iteration finds one cycle with
    ``nx.find_cycle`` (O(n + e)) and removes one edge, so the overall
    cost is O(C · (n + e)) where C is the number of removal iterations
    (at most e).  In the worst case this is O(e · (n + e)).  For dense
    pairwise graphs (e ≈ n²) this can be O(n⁴).  Use a small graph
    (n ≤ 50–100) for interactive experiments; for larger graphs the ILP
    back-end (once implemented) or a more efficient heuristic should be
    preferred.  This stage is typically the **dominant bottleneck** in the
    pipeline for moderately large inputs.

    # TODO: Cache graph copy and incrementally remove edges to avoid
    #       deep-copying the full graph each call.
    """
    dag = copy.deepcopy(graph)
    removed: list[tuple[str, str, float]] = []

    while True:
        try:
            cycle = nx.find_cycle(dag, orientation="original")
        except nx.NetworkXNoCycle:
            break

        # cycle is a list of (u, v, key, direction) or (u, v, direction) tuples
        # networkx.find_cycle returns (u, v, direction) for DiGraph
        cycle_edges = [(u, v) for u, v, *_ in cycle]

        # Find the minimum-weight edge in the cycle
        min_edge = min(
            cycle_edges,
            key=lambda e: dag[e[0]][e[1]].get("weight", 1.0),
        )
        w = dag[min_edge[0]][min_edge[1]].get("weight", 1.0)
        removed.append((min_edge[0], min_edge[1], w))
        dag.remove_edge(*min_edge)

    return dag, removed


def greedy_fas_total_weight(removed_edges: list[tuple[str, str, float]]) -> float:
    """Return the total weight of edges removed by :func:`greedy_fas`.

    Parameters
    ----------
    removed_edges:
        The second return value of :func:`greedy_fas`.

    Returns
    -------
    float
    """
    return sum(w for _, _, w in removed_edges)
