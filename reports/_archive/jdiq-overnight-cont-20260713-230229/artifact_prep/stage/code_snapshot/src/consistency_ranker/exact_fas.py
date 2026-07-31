"""
exact_fas.py
============
Exact Minimum Weighted Feedback Arc Set solver for small graphs.

Uses brute-force enumeration of all n! permutations to find the linear
ordering that minimizes total backward-edge weight.  This is the exact
MWFAS solution — the minimum-weight set of edges whose removal makes the
graph a DAG.

**Complexity:** O(n! · e) where e = number of edges.  Only feasible for
very small graphs (n ≤ 10).

    n=6  →     720 permutations
    n=8  →  40 320 permutations
    n=10 → 3 628 800 permutations  (borderline; ~seconds)
"""

from __future__ import annotations

import copy
import itertools
import math

import networkx as nx


def exact_fas(
    graph: nx.DiGraph,
    max_n: int = 10,
) -> tuple[nx.DiGraph, list[tuple[str, str, float]], float]:
    """Find the exact minimum-weight feedback arc set by exhaustive search.

    Enumerates all n! node permutations, treating each as a candidate
    linear ordering.  For a given ordering, every edge pointing "backward"
    (from a later node to an earlier node) is part of the feedback arc set.
    The ordering that minimises total backward-edge weight yields the
    exact MWFAS.

    Parameters
    ----------
    graph:
        Weighted directed preference graph.  Not modified.
    max_n:
        Safety limit — raises ValueError if the graph has more than
        *max_n* nodes (default 10).

    Returns
    -------
    dag : nx.DiGraph
        A copy of *graph* with the exact minimum-weight feedback arcs removed.
    removed_edges : list[(u, v, weight)]
        Edges removed (the exact MWFAS).
    objective : float
        Total weight of removed edges (the optimal MWFAS objective value).
    """
    nodes = list(graph.nodes())
    n = len(nodes)

    if n > max_n:
        raise ValueError(
            f"exact_fas is only feasible for small graphs.  "
            f"Got n={n} > max_n={max_n}.  "
            f"Total permutations would be {math.factorial(n):,}."
        )

    if n < 2 or nx.is_directed_acyclic_graph(graph):
        return copy.deepcopy(graph), [], 0.0

    edges = [
        (u, v, graph[u][v].get("weight", 1.0))
        for u, v in graph.edges()
    ]

    best_objective = float("inf")
    best_perm: tuple[str, ...] | None = None

    for perm in itertools.permutations(nodes):
        pos = {node: i for i, node in enumerate(perm)}
        backward_weight = sum(
            w for u, v, w in edges if pos[u] > pos[v]
        )
        if backward_weight < best_objective:
            best_objective = backward_weight
            best_perm = perm

    assert best_perm is not None
    pos = {node: i for i, node in enumerate(best_perm)}

    removed: list[tuple[str, str, float]] = []
    dag = copy.deepcopy(graph)
    for u, v, w in edges:
        if pos[u] > pos[v]:
            removed.append((u, v, w))
            dag.remove_edge(u, v)

    assert nx.is_directed_acyclic_graph(dag), "BUG: exact_fas produced a cyclic graph"

    return dag, removed, best_objective


def exact_fas_objective(graph: nx.DiGraph) -> float:
    """Return only the optimal MWFAS objective value (total removed weight)."""
    _, _, obj = exact_fas(graph)
    return obj
