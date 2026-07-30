"""
mwfas_solver.py
===============
Solver interface for the Minimum Weighted Feedback Arc Set (MWFAS) problem.

This module provides a unified :func:`solve` entry-point that dispatches to
different back-ends:

- ``"greedy"``  — fast heuristic from :mod:`greedy_fas` (default, always available).
- ``"scip"``    — exact linear-ordering MIP solved with the free, open-source
  SCIP solver via `PySCIPOpt <https://github.com/scipopt/PySCIPOpt>`_. This is
  the canonical exact backend and the one used to produce the exact-vs-greedy
  results reported in the manuscript. Install with
  ``pip install "consistency-ranker[exact]"`` (or ``pip install PySCIPOpt``).
- ``"exact"``   — alias for ``"scip"``.
- ``"ilp"``     — backward-compatible alias for ``"scip"``. Older code and
  scripts in this repository used ``method="ilp"`` to mean "the exact ILP
  solver" back when the only exact backend was Gurobi-based; it now resolves
  to the open-source SCIP backend so that existing call sites keep working
  without requiring a commercial license.
- ``"gurobi"``  — the original commercial-solver backend, kept only as an
  explicitly optional legacy path. It is never selected implicitly, never
  required for installation, testing, or reproduction, and is not exercised
  by any test unless ``gurobipy`` happens to be installed.

All exact back-ends (``scip``/``exact``/``ilp``/``gurobi``) solve the same
linear-ordering MIP:

- one binary variable ``before[u, v]`` per ordered pair of nodes, meaning
  "u is placed before v in the final ordering";
- antisymmetry: ``before[u, v] + before[v, u] == 1`` for every unordered pair;
- transitivity: for every ordered triple (a, b, c), at most two of
  ``before[a, b]``, ``before[b, c]``, ``before[c, a]`` can be 1 (and the
  symmetric triple with the cycle reversed);
- objective: minimize the total weight of edges ``(u, v)`` whose direction is
  reversed by the chosen ordering, i.e. ``sum(weight * before[v, u])`` over
  edges ``(u, v)``. This is exactly the minimum-weight feedback arc set
  objective.
"""

from __future__ import annotations

import copy
import itertools
import time
from dataclasses import dataclass

import networkx as nx

from .greedy_fas import greedy_fas

_SCIP_INSTALL_HINT = (
    'The exact MWFAS solver requires PySCIPOpt (free, open-source; no license '
    'needed). Install it with: pip install "consistency-ranker[exact]" '
    "(or: pip install PySCIPOpt)."
)

_ABS_TOL = 1e-6
_REL_TOL = 1e-6

# The exact PySCIPOpt version every currently-committed exact-repair canonical
# result (reports/exact_open_source_ilp_repair_investigation/,
# reports/final_revision_task4_exact_baseline_fairness_20260715/, and the
# repo's own tracked .venv) was generated with -- recovered 2026-07-30 (repo
# Stage 4) from 3 independent ENVIRONMENT_pip_freeze.txt files plus
# COMMANDS_EXECUTED.md, matching docs/REPRODUCTION_CANONICAL.md's own
# narrative claim exactly. SCIP is a MILP solver; presolve/heuristic/cut
# selection can change across versions in ways that alter which optimal
# solution is returned when multiple exist (though not whether it is
# optimal) -- so canonical reproduction should use exactly this version,
# not merely "some version >= 6.2.1".
CANONICAL_PYSCIPOPT_VERSION = "6.2.1"


class UnsupportedSolverVersionError(RuntimeError):
    """Raised by :func:`verify_canonical_solver_version` when PySCIPOpt is
    missing or does not match :data:`CANONICAL_PYSCIPOPT_VERSION`, and no
    override was requested."""


def verify_canonical_solver_version(*, allow_mismatch: bool = False) -> str:
    """Fail loudly (by default) if PySCIPOpt is absent or not the exact
    version every tracked exact-repair result was generated with.

    Call this at the start of any canonical-reproduction workflow that will
    compare its output against a committed exact-repair report. Pass
    ``allow_mismatch=True`` (documented override) for exploratory use where
    an approximate/newer solver is acceptable and the caller understands the
    result may not byte-match the committed canonical output.

    Returns the installed version string on success.
    """
    try:
        import pyscipopt
    except ImportError as exc:
        if allow_mismatch:
            return "NOT_INSTALLED"
        raise UnsupportedSolverVersionError(
            f"PySCIPOpt is not installed. Canonical exact-repair reproduction requires "
            f"exactly PySCIPOpt=={CANONICAL_PYSCIPOPT_VERSION} (the version every tracked "
            f"exact-repair result was generated with). {_SCIP_INSTALL_HINT} "
            "If you understand the risk and want to proceed with a different/no solver "
            "for exploratory purposes only, pass allow_mismatch=True."
        ) from exc

    installed = getattr(pyscipopt, "__version__", "unknown")
    if installed != CANONICAL_PYSCIPOPT_VERSION and not allow_mismatch:
        raise UnsupportedSolverVersionError(
            f"PySCIPOpt {installed} is installed, but canonical exact-repair reproduction "
            f"requires exactly {CANONICAL_PYSCIPOPT_VERSION} (the version every tracked "
            "exact-repair result was generated with -- a different version may return a "
            "different (still optimal, but not necessarily identical) solution when ties "
            "exist, so outputs may not byte-match the committed canonical results). "
            f"Install the exact version with: "
            f"pip install PySCIPOpt=={CANONICAL_PYSCIPOPT_VERSION}. "
            "Pass allow_mismatch=True to proceed anyway for exploratory use."
        )
    return installed


@dataclass
class SolveStatus:
    """Diagnostics returned by an exact MWFAS solve.

    Attributes
    ----------
    status:
        Raw solver status string (e.g. ``"optimal"``, ``"timelimit"``).
    proven_optimal:
        Whether the solver proved the returned solution is optimal. Callers
        MUST check this before treating ``removed_edges``/``objective`` as
        exact — a timelimit or gap-limit status means the result (if any) is
        only a feasible incumbent, not a proof of optimality.
    trivial:
        True if the graph was empty, single-node, or already acyclic, so the
        solver was never invoked (the answer is trivially "remove nothing").
    gap:
        Relative optimality gap reported by the solver (0.0 once proven optimal).
    time_s:
        Wall-clock solve time in seconds.
    n_nodes, n_vars, n_constraints:
        Problem size. ``n_vars == n_constraints == 0`` for trivial instances.
    objective:
        Total weight of the removed feedback arc set (``nan`` if not solved).
    solver, solver_version:
        Identifies which backend produced this status.
    error:
        Human-readable explanation when ``proven_optimal`` is False.
    """

    status: str
    proven_optimal: bool
    trivial: bool
    gap: float
    time_s: float
    n_nodes: int
    n_vars: int
    n_constraints: int
    objective: float
    solver: str = "pyscipopt/SCIP"
    solver_version: str = ""
    error: str | None = None


def is_scip_available() -> bool:
    """Return True if the free, open-source PySCIPOpt/SCIP backend can be used."""
    try:
        import pyscipopt  # noqa: F401
    except ImportError:
        return False
    return True


def is_gurobi_available() -> bool:
    """Return True if the optional, commercial gurobipy backend can be used."""
    try:
        import gurobipy  # noqa: F401
    except ImportError:
        return False
    return True


def _trivial_result(
    graph: nx.DiGraph, *, solver: str, solver_version: str
) -> tuple[nx.DiGraph, list[tuple[str, str, float]], SolveStatus]:
    return (
        copy.deepcopy(graph),
        [],
        SolveStatus(
            status="optimal",
            proven_optimal=True,
            trivial=True,
            gap=0.0,
            time_s=0.0,
            n_nodes=graph.number_of_nodes(),
            n_vars=0,
            n_constraints=0,
            objective=0.0,
            solver=solver,
            solver_version=solver_version,
        ),
    )


def _verify_solution(
    graph: nx.DiGraph,
    dag: nx.DiGraph,
    removed_edges: list[tuple[str, str, float]],
    objective: float,
) -> None:
    """Verify acyclicity, that removed edges/weights came from *graph*, and
    that removed weight matches the solver objective."""
    if not nx.is_directed_acyclic_graph(dag):
        raise AssertionError("BUG: exact MWFAS solver returned a cyclic graph.")
    for u, v, w in removed_edges:
        if not graph.has_edge(u, v):
            raise AssertionError(
                f"BUG: exact MWFAS solver removed edge ({u!r}, {v!r}) that does "
                "not exist in the original graph."
            )
        orig_w = float(graph[u][v].get("weight", 1.0))
        if abs(orig_w - w) > max(_ABS_TOL, _REL_TOL * max(abs(orig_w), 1.0)):
            raise AssertionError(
                f"BUG: exact MWFAS solver reported weight {w!r} for edge "
                f"({u!r}, {v!r}) but the original graph has weight {orig_w!r}."
            )
    removed_weight = float(sum(w for _u, _v, w in removed_edges))
    tol = max(_ABS_TOL, _REL_TOL * max(abs(objective), 1.0))
    if abs(removed_weight - objective) > tol:
        raise AssertionError(
            "BUG: exact MWFAS solver's removed-edge weight "
            f"({removed_weight!r}) does not match the solver objective "
            f"({objective!r}) within tolerance {tol!r}."
        )


def _solve_scip(
    graph: nx.DiGraph,
    *,
    time_limit_s: float = 300.0,
    mip_gap: float = 0.0,
    quiet: bool = True,
) -> tuple[nx.DiGraph, list[tuple[str, str, float]], SolveStatus]:
    """Solve MWFAS exactly with the open-source SCIP solver (via PySCIPOpt).

    Parameters
    ----------
    graph:
        Weighted directed preference graph that may contain cycles.
    time_limit_s:
        Wall-clock time limit passed to SCIP (``limits/time``), default 300s
        per query as used in the manuscript's exact-vs-greedy robustness check.
    mip_gap:
        Relative optimality gap limit passed to SCIP (``limits/gap``). Default
        0.0 requires SCIP to prove optimality exactly (subject to
        floating-point tolerance).
    quiet:
        Suppress SCIP's solver log output.

    Returns
    -------
    dag : networkx.DiGraph
        Acyclic subgraph after removing the feedback arc set (deep copy;
        original graph untouched).
    removed_edges : list[(u, v, weight)]
        Edges removed by the exact solve.
    status : SolveStatus
        Solver status/diagnostics. See :class:`SolveStatus`.
    """
    try:
        import pyscipopt
        from pyscipopt import Model
    except ImportError as exc:
        raise ImportError(_SCIP_INSTALL_HINT) from exc

    solver_version = getattr(pyscipopt, "__version__", "unknown")

    if graph.number_of_nodes() < 2 or nx.is_directed_acyclic_graph(graph):
        return _trivial_result(graph, solver="pyscipopt/SCIP", solver_version=solver_version)

    t0 = time.time()
    nodes = list(graph.nodes())
    edges = [(u, v, float(graph[u][v].get("weight", 1.0))) for u, v in graph.edges()]
    ordered_pairs = [(u, v) for u in nodes for v in nodes if u != v]

    model = Model("mwfas_exact_scip")
    if quiet:
        model.hideOutput()
    model.setParam("limits/time", float(time_limit_s))
    model.setParam("limits/gap", float(mip_gap))

    before = {}
    for u, v in ordered_pairs:
        before[u, v] = model.addVar(name=f"before_{u}_{v}", vtype="B")

    n_constraints = 0
    for i, u in enumerate(nodes):
        for v in nodes[i + 1 :]:
            model.addCons(before[u, v] + before[v, u] == 1, name=f"antisym_{u}_{v}")
            n_constraints += 1

    for a, b, c in itertools.combinations(nodes, 3):
        model.addCons(
            before[a, b] + before[b, c] + before[c, a] <= 2, name=f"trans_abc_{a}_{b}_{c}"
        )
        model.addCons(
            before[a, c] + before[c, b] + before[b, a] <= 2, name=f"trans_acb_{a}_{c}_{b}"
        )
        n_constraints += 2

    model.setObjective(
        pyscipopt.quicksum(weight * before[v, u] for u, v, weight in edges),
        "minimize",
    )

    model.optimize()
    elapsed = time.time() - t0

    scip_status = model.getStatus()
    try:
        gap = float(model.getGap())
    except Exception:
        gap = float("nan")

    proven_optimal = scip_status == "optimal"

    if not proven_optimal:
        return (
            copy.deepcopy(graph),
            [],
            SolveStatus(
                status=scip_status,
                proven_optimal=False,
                trivial=False,
                gap=gap,
                time_s=elapsed,
                n_nodes=graph.number_of_nodes(),
                n_vars=len(ordered_pairs),
                n_constraints=n_constraints,
                objective=float("nan"),
                solver="pyscipopt/SCIP",
                solver_version=solver_version,
                error=f"SCIP did not report proven-optimal status (got {scip_status!r}).",
            ),
        )

    dag = copy.deepcopy(graph)
    removed_edges: list[tuple[str, str, float]] = []
    for u, v, weight in edges:
        val = model.getVal(before[v, u])
        if val > 0.5:
            dag.remove_edge(u, v)
            removed_edges.append((u, v, weight))

    objective = float(model.getObjVal())
    _verify_solution(graph, dag, removed_edges, objective)

    status = SolveStatus(
        status=scip_status,
        proven_optimal=True,
        trivial=False,
        gap=gap,
        time_s=elapsed,
        n_nodes=graph.number_of_nodes(),
        n_vars=len(ordered_pairs),
        n_constraints=n_constraints,
        objective=objective,
        solver="pyscipopt/SCIP",
        solver_version=solver_version,
    )
    return dag, removed_edges, status


def _solve_gurobi(
    graph: nx.DiGraph,
) -> tuple[nx.DiGraph, list[tuple[str, str, float]], SolveStatus]:
    """Solve MWFAS exactly with a commercial Gurobi mixed-integer program.

    This is an explicitly optional legacy back-end. It is never selected by
    default, never required for installation, testing, or reproduction, and
    solves the identical linear-ordering MIP as :func:`_solve_scip` (see
    module docstring) so its results are directly comparable when a Gurobi
    license happens to be available.
    """
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except ImportError as exc:
        raise ImportError(
            "method='gurobi' requires the commercial gurobipy package and a "
            "Gurobi license. It is an optional legacy backend — use "
            "method='scip' (open-source, no license required) instead."
        ) from exc

    solver_version = str(gp.gurobi.version()) if hasattr(gp, "gurobi") else "unknown"

    if graph.number_of_nodes() < 2 or nx.is_directed_acyclic_graph(graph):
        return _trivial_result(graph, solver="gurobipy/Gurobi", solver_version=solver_version)

    t0 = time.time()
    nodes = list(graph.nodes())
    edges = [(u, v, float(graph[u][v].get("weight", 1.0))) for u, v in graph.edges()]
    ordered_pairs = [(u, v) for u in nodes for v in nodes if u != v]

    model = gp.Model("mwfas_exact")
    model.Params.OutputFlag = 0

    before = model.addVars(ordered_pairs, vtype=GRB.BINARY, name="before")

    n_constraints = 0
    for i, u in enumerate(nodes):
        for v in nodes[i + 1 :]:
            model.addConstr(before[u, v] + before[v, u] == 1, name=f"antisym_{u}_{v}")
            n_constraints += 1

    for a, b, c in itertools.combinations(nodes, 3):
        model.addConstr(
            before[a, b] + before[b, c] + before[c, a] <= 2, name=f"trans_abc_{a}_{b}_{c}"
        )
        model.addConstr(
            before[a, c] + before[c, b] + before[b, a] <= 2, name=f"trans_acb_{a}_{c}_{b}"
        )
        n_constraints += 2

    model.setObjective(
        gp.quicksum(weight * before[v, u] for u, v, weight in edges),
        GRB.MINIMIZE,
    )
    model.optimize()
    elapsed = time.time() - t0

    proven_optimal = model.Status == GRB.OPTIMAL
    if not proven_optimal:
        return (
            copy.deepcopy(graph),
            [],
            SolveStatus(
                status=str(model.Status),
                proven_optimal=False,
                trivial=False,
                gap=float("nan"),
                time_s=elapsed,
                n_nodes=graph.number_of_nodes(),
                n_vars=len(ordered_pairs),
                n_constraints=n_constraints,
                objective=float("nan"),
                solver="gurobipy/Gurobi",
                solver_version=solver_version,
                error=f"Gurobi did not report an optimal status (got {model.Status!r}).",
            ),
        )

    dag = copy.deepcopy(graph)
    removed_edges: list[tuple[str, str, float]] = []
    for u, v, weight in edges:
        if before[v, u].X > 0.5:
            dag.remove_edge(u, v)
            removed_edges.append((u, v, weight))

    objective = float(model.ObjVal)
    _verify_solution(graph, dag, removed_edges, objective)

    status = SolveStatus(
        status="optimal",
        proven_optimal=True,
        trivial=False,
        gap=0.0,
        time_s=elapsed,
        n_nodes=graph.number_of_nodes(),
        n_vars=len(ordered_pairs),
        n_constraints=n_constraints,
        objective=objective,
        solver="gurobipy/Gurobi",
        solver_version=solver_version,
    )
    return dag, removed_edges, status


_EXACT_ALIASES = {"scip", "exact", "ilp"}
_EXACT_BACKENDS = {
    "scip": _solve_scip,
    "exact": _solve_scip,
    "ilp": _solve_scip,
    "gurobi": _solve_gurobi,
}


def solve(
    graph: nx.DiGraph,
    method: str = "greedy",
    *,
    return_status: bool = False,
    time_limit_s: float = 300.0,
    mip_gap: float = 0.0,
):
    """Solve (exactly or approximately) the MWFAS problem on *graph*.

    Parameters
    ----------
    graph:
        Weighted directed preference graph that may contain cycles.
    method:
        Which solver back-end to use.

        - ``"greedy"`` (default): fast greedy heuristic, always available.
        - ``"scip"``: exact solver via the free, open-source SCIP solver
          (PySCIPOpt). Canonical exact backend.
        - ``"exact"``: alias for ``"scip"``.
        - ``"ilp"``: backward-compatible alias for ``"scip"`` (previously
          meant "Gurobi"; see module docstring).
        - ``"gurobi"``: optional legacy backend requiring a commercial
          ``gurobipy`` license. Never selected implicitly.
    return_status:
        Only meaningful for exact methods. If True, also return a
        :class:`SolveStatus` with the solver status, runtime, optimality
        gap, whether optimality was proven, and the objective value.
        Ignored (always a 2-tuple) for ``method="greedy"``.
    time_limit_s:
        Per-solve wall-clock time limit for exact methods (default 300s,
        matching the manuscript's exact-vs-greedy robustness check).
    mip_gap:
        Relative optimality gap required for exact methods (default 0.0 —
        require proven optimality).

    Returns
    -------
    (dag, removed_edges) or (dag, removed_edges, status) :
        ``dag`` is the acyclic subgraph after removing the feedback arc set;
        ``removed_edges`` is a list of ``(u, v, weight)`` tuples;
        ``status`` (only if ``return_status=True`` and method is exact) is a
        :class:`SolveStatus`.

    Raises
    ------
    ValueError
        If *method* is not recognised.
    ImportError
        If an exact method is requested but its solver package is unavailable.
    """
    if method == "greedy":
        return greedy_fas(graph)

    backend = _EXACT_BACKENDS.get(method)
    if backend is None:
        raise ValueError(
            f"Unknown MWFAS method: {method!r}. "
            f"Available methods: 'greedy', {', '.join(sorted(_EXACT_BACKENDS))}."
        )

    if backend is _solve_scip:
        dag, removed_edges, status = backend(graph, time_limit_s=time_limit_s, mip_gap=mip_gap)
    else:
        dag, removed_edges, status = backend(graph)

    if not status.proven_optimal:
        raise RuntimeError(
            f"Exact MWFAS solve did not reach proven optimality: {status.error}"
        )

    if return_status:
        return dag, removed_edges, status
    return dag, removed_edges


def available_methods() -> list[str]:
    """Return the list of currently available MWFAS solver methods.

    ``"greedy"`` is always available. ``"scip"``/``"exact"``/``"ilp"`` are
    available whenever the free, open-source PySCIPOpt package is installed.
    ``"gurobi"`` is available only when the optional commercial gurobipy
    package is installed; it is listed separately and is never required for
    ``"ilp"``/``"exact"``/``"scip"`` to work.

    Returns
    -------
    list[str]
    """
    methods = ["greedy"]
    if is_scip_available():
        methods.extend(["scip", "exact", "ilp"])
    if is_gurobi_available():
        methods.append("gurobi")
    return methods
