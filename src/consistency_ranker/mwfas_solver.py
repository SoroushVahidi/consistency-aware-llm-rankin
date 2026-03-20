"""
mwfas_solver.py
===============
Solver interface for the Minimum Weighted Feedback Arc Set (MWFAS) problem.

This module provides a unified :func:`solve` entry-point that dispatches to
different back-ends:

- ``"greedy"``  — fast heuristic from :mod:`greedy_fas` (default).
- ``"ilp"``     — exact ILP formulation (requires ``pulp``; raises
                  :class:`ImportError` if not installed).

The ILP back-end is a *stub* placeholder for future work.  It raises
:class:`NotImplementedError` until a full ILP formulation is integrated.
"""

from __future__ import annotations

import networkx as nx

from .greedy_fas import greedy_fas


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
        - ``"ilp"``: exact ILP solver (requires ``pulp``; not yet implemented).

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
    NotImplementedError
        If *method* is ``"ilp"`` (not yet implemented).
    """
    if method == "greedy":
        return greedy_fas(graph)
    elif method == "ilp":
        raise NotImplementedError(
            "The ILP solver back-end is not yet implemented. "
            "Install 'pulp' and implement the ILP formulation in mwfas_solver.py. "
            "See TODO.md for details."
        )
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
        import pulp  # noqa: F401

        methods.append("ilp")
    except ImportError:
        pass
    return methods
