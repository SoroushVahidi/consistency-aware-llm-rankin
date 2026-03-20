"""
cycle_detection.py
==================
Utilities for detecting and characterising cycles in directed preference graphs.

Cycles represent *inconsistencies*: if A > B > C > A it is impossible to
produce a globally consistent linear ranking.  This module provides:

- :func:`has_cycle` — quick Boolean check.
- :func:`find_simple_cycles` — enumerate all simple (elementary) cycles.
- :func:`count_cycles` — scalar count of simple cycles.
- :func:`nodes_in_cycles` — set of nodes that participate in at least one cycle.
- :func:`cycle_edge_set` — set of edges that belong to at least one cycle.
"""

from __future__ import annotations

import networkx as nx


def has_cycle(graph: nx.DiGraph) -> bool:
    """Return ``True`` if *graph* contains at least one directed cycle.

    Parameters
    ----------
    graph:
        A directed graph.

    Returns
    -------
    bool
    """
    return not nx.is_directed_acyclic_graph(graph)


def find_simple_cycles(graph: nx.DiGraph) -> list[list[str]]:
    """Return all simple (elementary) cycles in *graph*.

    Uses Johnson's algorithm (O((n + e)(c + 1)) where *c* is the number of
    cycles).  May be slow for dense graphs with many cycles.

    Parameters
    ----------
    graph:
        A directed graph.

    Returns
    -------
    list[list[str]]
        Each inner list is a cycle expressed as a sequence of node ids.  The
        last node connects back to the first.
    """
    return list(nx.simple_cycles(graph))


def count_cycles(graph: nx.DiGraph) -> int:
    """Return the number of simple cycles in *graph*.

    Parameters
    ----------
    graph:
        A directed graph.

    Returns
    -------
    int
    """
    return sum(1 for _ in nx.simple_cycles(graph))


def nodes_in_cycles(graph: nx.DiGraph) -> set[str]:
    """Return the set of node ids that participate in at least one cycle.

    Parameters
    ----------
    graph:
        A directed graph.

    Returns
    -------
    set[str]
    """
    result: set[str] = set()
    for cycle in nx.simple_cycles(graph):
        result.update(cycle)
    return result


def cycle_edge_set(graph: nx.DiGraph) -> set[tuple[str, str]]:
    """Return the set of directed edges that appear in at least one simple cycle.

    Parameters
    ----------
    graph:
        A directed graph.

    Returns
    -------
    set[(u, v)]
        Each element is a directed edge ``(u, v)``.
    """
    edges: set[tuple[str, str]] = set()
    for cycle in nx.simple_cycles(graph):
        for i in range(len(cycle)):
            u = cycle[i]
            v = cycle[(i + 1) % len(cycle)]
            edges.add((u, v))
    return edges


def cycle_summary(graph: nx.DiGraph) -> dict[str, int]:
    """Return a summary dict of cycle statistics for *graph*.

    Parameters
    ----------
    graph:
        A directed graph.

    Returns
    -------
    dict
        Keys: ``"n_cycles"``, ``"n_nodes_in_cycles"``, ``"n_edges_in_cycles"``.
    """
    cycles = find_simple_cycles(graph)
    node_set: set[str] = set()
    edge_set: set[tuple[str, str]] = set()
    for cycle in cycles:
        node_set.update(cycle)
        for i in range(len(cycle)):
            edge_set.add((cycle[i], cycle[(i + 1) % len(cycle)]))
    return {
        "n_cycles": len(cycles),
        "n_nodes_in_cycles": len(node_set),
        "n_edges_in_cycles": len(edge_set),
    }
