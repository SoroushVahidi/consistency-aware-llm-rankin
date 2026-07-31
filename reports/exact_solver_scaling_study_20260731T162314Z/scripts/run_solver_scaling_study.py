#!/usr/bin/env python3
"""
run_solver_scaling_study.py
============================
Never run before: how far past the production candidate-pool size (n=20,
the max used anywhere in the canonical pipeline) does exact MWFAS solving
stay tractable, and does Gurobi (now available for the first time) scale
meaningfully better than the open-source SCIP backend?

`greedy_fas.py`'s own docstring already *asserts* "the exact ILP back-end
does not scale as well as this heuristic ... prefer greedy for large graphs"
-- but this was never empirically measured beyond n=20 with any exact
solver (SCIP or Gurobi); every synthetic scale-sweep experiment in
`outputs/scale_sweep_n50`, `outputs/scale_sweep_n100` used greedy only.

This script generates synthetic cyclic preference graphs (same generators
as `scripts/run_exact_vs_greedy.py`: `generate_items`/`generate_preferences`/
`build_graph`) at increasing n, and times both:
  - SCIP, via `mwfas_solver.solve(method="scip", time_limit_s=...)` (the
    module's own public, time-limited SCIP path -- no reimplementation).
  - Gurobi, via a local formulation mirroring `mwfas_solver._solve_gurobi`
    exactly (same variables/constraints/objective; see that function's
    source), but with `Params.TimeLimit` set -- the module's own Gurobi
    path does not expose a time limit, so a time-bounded copy is used here
    instead of modifying `mwfas_solver.py`.

Resumable: results are appended incrementally to a CSV; on restart,
already-completed (n_items, seed) rows are skipped. Adaptive: if every
seed at a given n times out for *both* solvers, larger n are not attempted
(the tractability boundary has already been found).
"""
from __future__ import annotations

import csv
import itertools
import sys
import time
from pathlib import Path

import networkx as nx

THIS_DIR = Path(__file__).resolve().parent
REPORT_ROOT = THIS_DIR.parent
REPO_ROOT = REPORT_ROOT.parents[1]
SRC_ROOT = REPO_ROOT / "src"
for p in (REPO_ROOT, SRC_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from consistency_ranker.graph_construction import build_graph  # noqa: E402
from consistency_ranker.mwfas_solver import solve as mwfas_solve  # noqa: E402
from consistency_ranker.pairwise_prefs import generate_preferences  # noqa: E402
from consistency_ranker.synthetic_data import generate_items, quality_map  # noqa: E402

N_ITEMS_GRID = [15, 20, 25, 30, 40, 50, 65, 80, 100]
SEEDS = [42, 123]
NOISE = 0.20
WEIGHT_SCHEME = "margin"
TIME_LIMIT_S = 30.0
MIP_GAP = 0.0

RESULTS_CSV = REPORT_ROOT / "tables" / "solver_scaling_per_instance.csv"
FIELDNAMES = [
    "n_items", "seed", "n_nodes", "n_edges", "n_vars", "n_constraints",
    "solver", "status", "proven_optimal", "gap", "time_s", "objective", "error",
]


def _solve_gurobi_time_limited(graph: nx.DiGraph, *, time_limit_s: float, mip_gap: float):
    """Mirrors `mwfas_solver._solve_gurobi`'s formulation exactly (same
    variables/constraints/objective), but with a Params.TimeLimit set, since
    the module's own gurobi path does not expose one. Returns a dict with
    the same fields as `mwfas_solver.SolveStatus` (as a dict, not the
    dataclass, to avoid importing a private symbol)."""
    import gurobipy as gp
    from gurobipy import GRB

    solver_version = str(gp.gurobi.version())

    if graph.number_of_nodes() < 2 or nx.is_directed_acyclic_graph(graph):
        return {
            "status": "optimal", "proven_optimal": True, "gap": 0.0, "time_s": 0.0,
            "n_vars": 0, "n_constraints": 0, "objective": 0.0, "error": None,
        }

    t0 = time.time()
    nodes = list(graph.nodes())
    edges = [(u, v, float(graph[u][v].get("weight", 1.0))) for u, v in graph.edges()]
    ordered_pairs = [(u, v) for u in nodes for v in nodes if u != v]

    model = gp.Model("mwfas_scaling")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = float(time_limit_s)
    model.Params.MIPGap = max(float(mip_gap), 1e-9)

    before = model.addVars(ordered_pairs, vtype=GRB.BINARY, name="before")

    n_constraints = 0
    for i, u in enumerate(nodes):
        for v in nodes[i + 1:]:
            model.addConstr(before[u, v] + before[v, u] == 1)
            n_constraints += 1
    for a, b, c in itertools.combinations(nodes, 3):
        model.addConstr(before[a, b] + before[b, c] + before[c, a] <= 2)
        model.addConstr(before[a, c] + before[c, b] + before[b, a] <= 2)
        n_constraints += 2

    model.setObjective(gp.quicksum(w * before[v, u] for u, v, w in edges), GRB.MINIMIZE)
    model.optimize()
    elapsed = time.time() - t0

    proven_optimal = model.Status == GRB.OPTIMAL
    try:
        gap = float(model.MIPGap) if not proven_optimal else 0.0
    except Exception:
        gap = float("nan")
    try:
        objective = float(model.ObjVal) if model.SolCount > 0 else float("nan")
    except Exception:
        objective = float("nan")

    return {
        "status": str(model.Status), "proven_optimal": proven_optimal, "gap": gap,
        "time_s": elapsed, "n_vars": len(ordered_pairs), "n_constraints": n_constraints,
        "objective": objective,
        "error": None if proven_optimal else f"Gurobi status {model.Status} (not GRB.OPTIMAL)",
        "solver_version": solver_version,
    }


def _load_completed() -> set[tuple[int, int]]:
    if not RESULTS_CSV.exists():
        return set()
    done = set()
    with RESULTS_CSV.open() as fh:
        for row in csv.DictReader(fh):
            done.add((int(row["n_items"]), int(row["seed"])))
    return done


def _append_rows(rows: list[dict]) -> None:
    write_header = not RESULTS_CSV.exists()
    with RESULTS_CSV.open("a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main() -> int:
    RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    completed = _load_completed()
    print(f"[{time.strftime('%H:%M:%S')}] Resuming: {len(completed)} (n_items, seed) pairs already done.", flush=True)

    for n_items in N_ITEMS_GRID:
        any_solver_succeeded_this_n = False
        for seed in SEEDS:
            if (n_items, seed) in completed:
                print(f"[{time.strftime('%H:%M:%S')}] n={n_items} seed={seed}: SKIP (already done)", flush=True)
                any_solver_succeeded_this_n = True  # don't stop early based on stale info; be conservative
                continue

            items = generate_items(n=n_items, seed=seed)
            qmap = quality_map(items)
            prefs = generate_preferences(qmap, noise=NOISE, weight_scheme=WEIGHT_SCHEME, seed=seed)
            graph = build_graph(prefs)
            n_edges = graph.number_of_edges()

            rows = []

            # --- SCIP (via the module's own public, time-limited path) ---
            t0 = time.time()
            try:
                _, _, status = mwfas_solve(
                    graph, method="scip", return_status=True,
                    time_limit_s=TIME_LIMIT_S, mip_gap=MIP_GAP,
                )
                scip_row = {
                    "n_items": n_items, "seed": seed, "n_nodes": graph.number_of_nodes(),
                    "n_edges": n_edges, "n_vars": status.n_vars, "n_constraints": status.n_constraints,
                    "solver": "scip", "status": status.status, "proven_optimal": status.proven_optimal,
                    "gap": status.gap, "time_s": status.time_s, "objective": status.objective,
                    "error": status.error,
                }
            except RuntimeError as exc:
                # solve() raises if not proven_optimal; recover the partial info via a direct call
                scip_row = {
                    "n_items": n_items, "seed": seed, "n_nodes": graph.number_of_nodes(),
                    "n_edges": n_edges, "n_vars": "", "n_constraints": "",
                    "solver": "scip", "status": "timelimit_or_gap", "proven_optimal": False,
                    "gap": "", "time_s": time.time() - t0, "objective": "", "error": str(exc),
                }
            rows.append(scip_row)
            print(f"[{time.strftime('%H:%M:%S')}] n={n_items} seed={seed} SCIP: "
                  f"proven_optimal={scip_row['proven_optimal']} time_s={scip_row['time_s']:.2f}", flush=True)

            # --- Gurobi (time-limited local formulation) ---
            g = _solve_gurobi_time_limited(graph, time_limit_s=TIME_LIMIT_S, mip_gap=MIP_GAP)
            gurobi_row = {
                "n_items": n_items, "seed": seed, "n_nodes": graph.number_of_nodes(),
                "n_edges": n_edges, "n_vars": g["n_vars"], "n_constraints": g["n_constraints"],
                "solver": "gurobi", "status": g["status"], "proven_optimal": g["proven_optimal"],
                "gap": g["gap"], "time_s": g["time_s"], "objective": g["objective"], "error": g["error"],
            }
            rows.append(gurobi_row)
            print(f"[{time.strftime('%H:%M:%S')}] n={n_items} seed={seed} Gurobi: "
                  f"proven_optimal={gurobi_row['proven_optimal']} time_s={gurobi_row['time_s']:.2f}", flush=True)

            _append_rows(rows)
            if scip_row["proven_optimal"] or gurobi_row["proven_optimal"]:
                any_solver_succeeded_this_n = True

        if not any_solver_succeeded_this_n:
            print(
                f"[{time.strftime('%H:%M:%S')}] n={n_items}: BOTH solvers failed to prove optimality "
                f"for every seed within {TIME_LIMIT_S}s -- stopping grid here (tractability boundary found).",
                flush=True,
            )
            break

    print(f"[{time.strftime('%H:%M:%S')}] Scaling study complete. Results: {RESULTS_CSV}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
