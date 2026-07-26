"""Cycle repair with arbitrary edge-removal costs.

Convention: high ``removal_cost`` = expensive to remove = prefer to preserve.
Greedy heuristic removes the cheapest (lowest cost) edge on each found cycle.
"""

from __future__ import annotations

import copy
import itertools
import math
from typing import Any

import networkx as nx


def greedy_fas_with_costs(
    graph: nx.DiGraph,
    *,
    cost_attr: str = "removal_cost",
) -> tuple[nx.DiGraph, list[tuple[str, str, float]], dict[str, Any]]:
    """Like ``greedy_fas`` but minimizes removal *cost* (not raw weight)."""
    dag = copy.deepcopy(graph)
    removed: list[tuple[str, str, float]] = []
    while True:
        try:
            cycle = nx.find_cycle(dag, orientation="original")
        except nx.NetworkXNoCycle:
            break
        cycle_edges = [(u, v) for u, v, *_ in cycle]
        def _cost(e):
            data = dag[e[0]][e[1]]
            return float(data.get(cost_attr, data.get("weight", 1.0)))

        min_edge = min(cycle_edges, key=_cost)
        cost = _cost(min_edge)
        removed.append((min_edge[0], min_edge[1], cost))
        dag.remove_edge(*min_edge)
    meta = {
        "method": "greedy_fas_with_costs",
        "cost_attr": cost_attr,
        "n_removed": len(removed),
        "removed_cost": float(sum(c for _, _, c in removed)),
        "retained_cost": float(
            sum(
                float(d.get(cost_attr, d.get("weight", 1.0)))
                for _, _, d in dag.edges(data=True)
            )
        ),
    }
    return dag, removed, meta


def exact_fas_with_costs(
    graph: nx.DiGraph,
    *,
    cost_attr: str = "removal_cost",
    max_n: int = 9,
) -> tuple[nx.DiGraph, list[tuple[str, str, float]], dict[str, Any]]:
    """Exact linear-ordering FAS under arbitrary edge costs (tiny n)."""
    nodes = list(graph.nodes())
    n = len(nodes)
    if n > max_n:
        raise ValueError(f"exact_fas_with_costs supports n<={max_n}; got n={n}")
    if n < 2 or nx.is_directed_acyclic_graph(graph):
        return copy.deepcopy(graph), [], {
            "method": "exact_fas_with_costs",
            "objective": 0.0,
            "optimal": True,
        }

    edges = [
        (
            u,
            v,
            float(graph[u][v].get(cost_attr, graph[u][v].get("weight", 1.0))),
        )
        for u, v in graph.edges()
    ]
    best_obj = float("inf")
    best_perm: tuple[str, ...] | None = None
    for perm in itertools.permutations(nodes):
        pos = {node: i for i, node in enumerate(perm)}
        obj = sum(c for u, v, c in edges if pos[v] < pos[u])
        if obj < best_obj:
            best_obj = obj
            best_perm = perm

    assert best_perm is not None
    pos = {node: i for i, node in enumerate(best_perm)}
    removed = [(u, v, c) for u, v, c in edges if pos[v] < pos[u]]
    dag = copy.deepcopy(graph)
    for u, v, _ in removed:
        if dag.has_edge(u, v):
            dag.remove_edge(u, v)
    meta = {
        "method": "exact_fas_with_costs",
        "cost_attr": cost_attr,
        "objective": float(best_obj),
        "optimal": True,
        "n_removed": len(removed),
        "removed_cost": float(best_obj),
        "n_permutations": math.factorial(n),
    }
    return dag, removed, meta


def apply_cost_scheme(
    graph: nx.DiGraph,
    *,
    scheme: str,
) -> nx.DiGraph:
    """Set ``removal_cost`` from existing edge attributes.

    Schemes (high = expensive to remove):
      * weight
      * reliability
      * reliability_x_importance
      * weight_x_reliability
      * weight_x_reliability_x_importance
    """
    g = copy.deepcopy(graph)
    for u, v, data in g.edges(data=True):
        w = float(data.get("weight", 1.0))
        r = float(data.get("reliability", 1.0))
        imp = float(data.get("importance", 1.0))
        if scheme == "weight":
            cost = w
        elif scheme == "reliability":
            cost = r
        elif scheme == "reliability_x_importance":
            cost = r * imp
        elif scheme == "weight_x_reliability":
            cost = w * r
        elif scheme == "weight_x_reliability_x_importance":
            cost = w * r * imp
        else:
            raise ValueError(f"Unknown cost scheme {scheme!r}")
        data["removal_cost"] = float(max(cost, 1e-12))
    return g
