"""
graph_construction.py
=====================
Build weighted directed preference graphs from pairwise preference data.

The graph representation uses :class:`networkx.DiGraph` (or
:class:`networkx.MultiDiGraph` for multi-edge scenarios).  Each directed edge
``u → v`` carries a ``"weight"`` attribute representing the strength of the
preference for *u* over *v*.

When the same pair (u, v) appears multiple times (e.g. multiple annotators),
the weights are **aggregated** (summed by default).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable

import networkx as nx

from .pairwise_prefs import Preference


def build_graph(
    preferences: list[Preference],
    aggregation: str | Callable[[list[float]], float] = "sum",
) -> nx.DiGraph:
    """Build a weighted directed graph from pairwise preferences.

    Parameters
    ----------
    preferences:
        List of :class:`~consistency_ranker.pairwise_prefs.Preference` triples.
    aggregation:
        How to aggregate weights when the same directed edge appears multiple
        times.  Built-in options: ``"sum"`` (default), ``"mean"``, ``"max"``.
        Alternatively pass any callable ``list[float] → float``.

    Returns
    -------
    networkx.DiGraph
        A directed graph where ``G[u][v]["weight"]`` holds the aggregated
        preference strength for u > v.

    Raises
    ------
    ValueError
        If *aggregation* is an unrecognised string.
    """
    agg_fn = _resolve_aggregation(aggregation)

    # Collect raw weights per directed edge
    edge_weights: dict[tuple[str, str], list[float]] = defaultdict(list)
    for pref in preferences:
        edge_weights[(pref.winner, pref.loser)].append(pref.weight)

    graph = nx.DiGraph()
    for (u, v), weights in edge_weights.items():
        graph.add_edge(u, v, weight=agg_fn(weights))

    return graph


def build_graph_from_dict(
    edge_weight_dict: dict[tuple[str, str], float],
) -> nx.DiGraph:
    """Build a weighted directed graph from an edge-weight dictionary.

    Parameters
    ----------
    edge_weight_dict:
        Mapping ``(winner_id, loser_id) → weight``.

    Returns
    -------
    networkx.DiGraph
    """
    graph = nx.DiGraph()
    for (u, v), w in edge_weight_dict.items():
        graph.add_edge(u, v, weight=w)
    return graph


def graph_summary(graph: nx.DiGraph) -> dict[str, int | float]:
    """Return basic statistics about a preference graph.

    Parameters
    ----------
    graph:
        A directed graph (output of :func:`build_graph`).

    Returns
    -------
    dict
        Keys: ``"n_nodes"``, ``"n_edges"``, ``"is_dag"``,
        ``"total_weight"``, ``"n_sccs"`` (strongly connected components).
    """
    weights = [d.get("weight", 1.0) for _, _, d in graph.edges(data=True)]
    return {
        "n_nodes": graph.number_of_nodes(),
        "n_edges": graph.number_of_edges(),
        "is_dag": nx.is_directed_acyclic_graph(graph),
        "total_weight": sum(weights),
        "n_sccs": nx.number_strongly_connected_components(graph),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_BUILTIN_AGG: dict[str, Callable[[list[float]], float]] = {
    "sum": sum,
    "mean": lambda ws: sum(ws) / len(ws),
    "max": max,
}


def _resolve_aggregation(
    aggregation: str | Callable[[list[float]], float],
) -> Callable[[list[float]], float]:
    if callable(aggregation):
        return aggregation
    if aggregation not in _BUILTIN_AGG:
        raise ValueError(
            f"Unknown aggregation {aggregation!r}. "
            f"Choose from {list(_BUILTIN_AGG)} or pass a callable."
        )
    return _BUILTIN_AGG[aggregation]
