#!/usr/bin/env python3
"""
run_gurobi_vs_scip_cross_validation.py
=======================================
Solver cross-validation: does the commercial Gurobi MWFAS backend
(`mwfas_solver.solve(..., method="gurobi")`) agree with the canonical
open-source SCIP backend (`mwfas_solver.solve(..., method="scip")`) on the
same 1,025 canonical production preference graphs used in
`reports/exact_open_source_ilp_repair_investigation/`?

This is an internal correctness/robustness check only. Per
`papers/JDIQ_2026/manuscript/integrity_audit/EXTERNAL_SOLVER_MANUSCRIPT_DECISION.md`
and the repo's own documentation (README.md, docs/REPRODUCTION_CANONICAL.md),
Gurobi is never used to produce any manuscript result -- this script does not
change that; its only purpose is to independently confirm (with a second,
mature, industrial-grade MIP solver) that the canonical SCIP-based exact
repair results are correct, now that a working Gurobi license is available
for the first time.

Both solver calls go through the actual shipped `consistency_ranker.mwfas_solver`
module (not a re-implementation), so this also re-validates that module's own
SCIP path against the separate ported copy used in
`reports/exact_open_source_ilp_repair_investigation/scripts/exact_ilp_scip.py`.

Nothing here modifies `full_calibration_utils.py`, `mwfas_solver.py`, or any
canonical output. All outputs go under this investigation's own directory.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

THIS_DIR = Path(__file__).resolve().parent
REPORT_ROOT = THIS_DIR.parent
REPO_ROOT = REPORT_ROOT.parents[1]
SRC_ROOT = REPO_ROOT / "src"
FULL_CAL_SCRIPTS = REPO_ROOT / "reports" / "full_calibrated_core" / "scripts"

for p in (REPO_ROOT, SRC_ROOT, FULL_CAL_SCRIPTS, THIS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import full_calibration_utils as fc  # noqa: E402
from consistency_ranker.mwfas_solver import (  # noqa: E402
    is_gurobi_available,
    is_scip_available,
    solve,
    verify_canonical_solver_version,
)

DATASETS = ("bright", "fiqa", "hotpotqa", "scidocs")
REGIMES = ("ms1", "ms1_drop_mutual", "ms2")
PROTOCOL_DIR = "primary_minmax_retention_matched"


class SolverProbeEvaluator(fc.CalibrationEvaluator):
    """Identical to fc.CalibrationEvaluator except the repair step calls the
    given mwfas_solver backend directly and records full solver diagnostics
    (including the removed-edge set, not just counts) for cross-solver
    comparison."""

    def __init__(self, method: str) -> None:
        super().__init__()
        self.method = method
        self.solver_records: list[dict[str, Any]] = []

    def _apply_repair(self, graph, prior_scores, *, top_k: int):
        dag, removed, status = solve(graph, method=self.method, return_status=True)
        self.solver_records.append(
            {
                "n_nodes": status.n_nodes,
                "n_vars": status.n_vars,
                "n_constraints": status.n_constraints,
                "status": status.status,
                "proven_optimal": status.proven_optimal,
                "trivial": status.trivial,
                "gap": status.gap,
                "time_s": status.time_s,
                "objective": status.objective,
                "solver": status.solver,
                "solver_version": status.solver_version,
                "error": status.error,
                "removed_edge_set": sorted(f"{u}->{v}" for u, v, _w in removed),
            }
        )
        removed_weight = float(sum(w for _u, _v, w in removed))
        return dag, {
            "repair_applied": bool(removed),
            "mode": self.method,
            "removed_edges": [(u, v, float(w)) for u, v, w in removed],
            "removed_weight": removed_weight,
            "n_edges_removed": len(removed),
        }


def main() -> int:
    assert is_scip_available(), "PySCIPOpt must be installed for this cross-validation"
    assert is_gurobi_available(), "gurobipy must be installed (and licensed) for this cross-validation"

    scip_version = verify_canonical_solver_version(allow_mismatch=True)
    print(f"[{time.strftime('%H:%M:%S')}] PySCIPOpt version: {scip_version}", flush=True)

    import gurobipy as gp
    print(f"[{time.strftime('%H:%M:%S')}] Gurobi version: {gp.gurobi.version()}", flush=True)

    t_start = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] Loading dataset inputs for {DATASETS} ...", flush=True)
    dataset_inputs = {ds: fc.prepare_dataset_inputs(ds) for ds in DATASETS}
    print(f"[{time.strftime('%H:%M:%S')}] Dataset inputs loaded.", flush=True)

    scip_eval = SolverProbeEvaluator("scip")
    gurobi_eval = SolverProbeEvaluator("gurobi")

    rows: list[dict[str, Any]] = []
    n_done = 0

    for dataset in DATASETS:
        ds_inputs = dataset_inputs[dataset]
        for regime in REGIMES:
            manifest_path = (
                REPO_ROOT
                / "reports/full_calibrated_core/outputs/calibrated_all4/protocol_runs"
                / PROTOCOL_DIR
                / dataset
                / regime
                / "manifest.json"
            )
            manifest = json.loads(manifest_path.read_text())
            th = manifest["thresholds"]
            cfg = fc.ThresholdConfig(
                vote_thresholds={k: float(v) for k, v in th["vote_thresholds"].items()},
                aggregate_threshold=float(th["aggregate_threshold"]),
                min_support=int(th["min_support"]),
                postprocess_drop_mutual=bool(th["drop_mutual"]),
                target_vote_rates=None,
                target_edge_count=None,
                notes=str(th.get("notes", "")),
            )

            for item in ds_inputs["per_query_inputs"]:
                qid = item["query_id"]
                artifacts = fc.build_query_vote_artifacts(
                    query_id=qid,
                    raw_scores_by_ranker=item["raw_scores_by_ranker"],
                    candidate_pool=item["candidate_pool"],
                    calibration="minmax_query_ranker",
                    threshold_config=cfg,
                )
                if not artifacts["rows"]:
                    continue

                common_kwargs = dict(
                    dataset=dataset,
                    query_id=qid,
                    qrels_for_query=ds_inputs["qrels_by_query"].get(qid, []),
                    vote_regime=regime,
                    top_k=int(ds_inputs["spec"].top_k),
                    candidate_pool=item["candidate_pool"],
                    vote_rows=artifacts["rows"],
                    raw_score_maps_by_ranker={
                        rk: list(scores.items()) for rk, scores in item["raw_scores_by_ranker"].items()
                    },
                )
                scip_rec = scip_eval.evaluate_query(**common_kwargs)
                gurobi_rec = gurobi_eval.evaluate_query(**common_kwargs)
                if scip_rec is None or gurobi_rec is None:
                    continue

                n_done += 1
                s = scip_eval.solver_records[-1]
                g = gurobi_eval.solver_records[-1]

                obj_diff = abs(s["objective"] - g["objective"]) if (
                    s["objective"] == s["objective"] and g["objective"] == g["objective"]
                ) else float("nan")  # NaN-safe: NaN != NaN
                same_edge_set = s["removed_edge_set"] == g["removed_edge_set"]

                rows.append(
                    {
                        "dataset": dataset,
                        "regime": regime,
                        "query_id": qid,
                        "n_nodes": s["n_nodes"],
                        "n_vars": s["n_vars"],
                        "n_constraints": s["n_constraints"],
                        "scip_status": s["status"],
                        "scip_proven_optimal": s["proven_optimal"],
                        "scip_objective": s["objective"],
                        "scip_time_s": s["time_s"],
                        "gurobi_status": g["status"],
                        "gurobi_proven_optimal": g["proven_optimal"],
                        "gurobi_objective": g["objective"],
                        "gurobi_time_s": g["time_s"],
                        "gurobi_version": g["solver_version"],
                        "objective_abs_diff": obj_diff,
                        "objective_match": (obj_diff <= 1e-6) if obj_diff == obj_diff else False,
                        "same_removed_edge_set": same_edge_set,
                        "both_proven_optimal": bool(s["proven_optimal"] and g["proven_optimal"]),
                    }
                )
            print(
                f"[{time.strftime('%H:%M:%S')}] {dataset}/{regime}: done. "
                f"cumulative queries processed = {n_done}",
                flush=True,
            )

    print(f"[{time.strftime('%H:%M:%S')}] All queries processed ({n_done} total). Writing outputs ...", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(REPORT_ROOT / "tables" / "gurobi_vs_scip_per_query.csv", index=False)

    n_total = len(df)
    n_obj_mismatch = int((~df["objective_match"]).sum()) if n_total else 0
    n_edge_set_mismatch = int((~df["same_removed_edge_set"]).sum()) if n_total else 0
    n_not_both_optimal = int((~df["both_proven_optimal"]).sum()) if n_total else 0

    summary = {
        "n_queries_total": n_total,
        "n_objective_mismatches": n_obj_mismatch,
        "n_removed_edge_set_mismatches_given_matching_objective": int(
            ((~df["same_removed_edge_set"]) & df["objective_match"]).sum()
        ) if n_total else 0,
        "n_removed_edge_set_mismatches_total": n_edge_set_mismatch,
        "n_not_both_proven_optimal": n_not_both_optimal,
        "scip_total_solve_time_s": float(df["scip_time_s"].sum()) if n_total else 0.0,
        "gurobi_total_solve_time_s": float(df["gurobi_time_s"].sum()) if n_total else 0.0,
        "scip_mean_solve_time_s": float(df["scip_time_s"].mean()) if n_total else 0.0,
        "gurobi_mean_solve_time_s": float(df["gurobi_time_s"].mean()) if n_total else 0.0,
        "scip_max_solve_time_s": float(df["scip_time_s"].max()) if n_total else 0.0,
        "gurobi_max_solve_time_s": float(df["gurobi_time_s"].max()) if n_total else 0.0,
        "gurobi_version": str(df["gurobi_version"].iloc[0]) if n_total else None,
        "pyscipopt_version": scip_version,
        "elapsed_seconds": time.time() - t_start,
    }
    with (REPORT_ROOT / "manifests" / "cross_validation_summary.json").open("w") as fh:
        json.dump(summary, fh, indent=2)

    print(f"[{time.strftime('%H:%M:%S')}] Done. Summary: {json.dumps(summary, indent=2)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
