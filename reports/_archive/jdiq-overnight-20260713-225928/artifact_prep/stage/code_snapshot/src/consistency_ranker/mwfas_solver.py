"""
mwfas_solver.py
===============
Solver interface for the Minimum Weighted Feedback Arc Set (MWFAS) problem.

This module provides a unified :func:`solve` entry-point that dispatches to
different back-ends:

- ``"greedy"``  — fast heuristic from :mod:`greedy_fas` (default).
- ``"ilp"``     — exact ILP formulation backed by ``gurobipy``.
"""

from __future__ import annotations

import copy
import itertools

import networkx as nx

from .greedy_fas import greedy_fas


def _solve_ilp(
    graph: nx.DiGraph,
) -> tuple[nx.DiGraph, list[tuple[str, str, float]]]:
    """Solve MWFAS exactly with a Gurobi mixed-integer program.

    The model uses one integer position variable per node and one binary
    removal variable per edge.  An edge can remain only if its tail is placed
    before its head in the final ordering; otherwise the solver must remove it.
    Minimizing removed edge weight is equivalent to the minimum-weight feedback
    arc set objective.
    """
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except ImportError as exc:
        raise ImportError(
            "The ILP MWFAS solver requires gurobipy. "
            "Install Gurobi's Python package and ensure the solver license is available."
        ) from exc

    if graph.number_of_nodes() < 2 or nx.is_directed_acyclic_graph(graph):
        return copy.deepcopy(graph), []

    nodes = list(graph.nodes())
    edges = [(u, v, float(graph[u][v].get("weight", 1.0))) for u, v in graph.edges()]
    ordered_pairs = [(u, v) for u in nodes for v in nodes if u != v]

    model = gp.Model("mwfas_exact")
    model.Params.OutputFlag = 0

    before = model.addVars(
        ordered_pairs,
        vtype=GRB.BINARY,
        name="before",
    )

    for i, u in enumerate(nodes):
        for v in nodes[i + 1:]:
            model.addConstr(before[u, v] + before[v, u] == 1, name=f"antisym_{u}_{v}")

    for a, b, c in itertools.combinations(nodes, 3):
        model.addConstr(
            before[a, b] + before[b, c] + before[c, a] <= 2,
            name=f"trans_abc_{a}_{b}_{c}",
        )
        model.addConstr(
            before[a, c] + before[c, b] + before[b, a] <= 2,
            name=f"trans_acb_{a}_{c}_{b}",
        )

    model.setObjective(
        gp.quicksum(weight * before[v, u] for u, v, weight in edges),
        GRB.MINIMIZE,
    )
    model.optimize()

    if model.Status != GRB.OPTIMAL:
        raise RuntimeError(
            f"Gurobi failed to solve the ILP optimally. Solver status: {model.Status}."
        )

    dag = copy.deepcopy(graph)
    removed_edges: list[tuple[str, str, float]] = []
    for u, v, weight in edges:
        if before[v, u].X > 0.5:
            dag.remove_edge(u, v)
            removed_edges.append((u, v, weight))

    if not nx.is_directed_acyclic_graph(dag):
        raise AssertionError("BUG: ILP MWFAS solver returned a cyclic graph.")

    return dag, removed_edges


def solve(
    graph: nx.DiGraph,
    method: str = "greedy",
) -> tuple[nx.DiGraph, list[tuple[str, str, float]]]:
    """Solve (approximately) the MWFAS problem on *graph*.

    Parameters
    ----------
    graph:
        Weighted directed preference graph that may contain cycles.
    method:
        Which solver back-end to use.

        - ``"greedy"``: fast greedy heuristic (always available).
        - ``"ilp"``: exact ILP solver (requires ``gurobipy``).

    Returns
    -------
    dag : networkx.DiGraph
        Acyclic subgraph after removing the feedback arc set.
    removed_edges : list[(u, v, weight)]
        Edges that were removed.

    Raises
    ------
    ValueError
        If *method* is not recognised.
    ImportError
        If *method* is ``"ilp"`` but ``gurobipy`` is unavailable.
    """
    if method == "greedy":
        return greedy_fas(graph)
    elif method == "ilp":
        return _solve_ilp(graph)
    else:
        raise ValueError(
            f"Unknown MWFAS method: {method!r}. "
            "Available methods: 'greedy', 'ilp'."
        )


def available_methods() -> list[str]:
    """Return the list of currently available MWFAS solver methods.

    Returns
    -------
    list[str]
    """
    methods = ["greedy"]
    try:
        import gurobipy  # noqa: F401

        methods.append("ilp")
    except ImportError:
        pass
    return methods
