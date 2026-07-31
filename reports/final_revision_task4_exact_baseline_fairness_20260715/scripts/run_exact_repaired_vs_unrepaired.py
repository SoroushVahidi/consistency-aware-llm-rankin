#!/usr/bin/env python3
"""JDIQ Task 4, section 2/3: direct exact-repaired vs unrepaired evaluation.

A. Canonical pool (P=k, primary protocol), all four datasets, ms1, every
   graph-dependent method pair (rfc.PAIR_SPECS, 9 pairs) -- this is new
   work; only the Task 1 larger-pool cells had an exact-vs-unrepaired
   comparison before this task.
B. Task 1 larger-pool cells: reuses the existing
   reports/final_revision_task1_pool_cutoff_20260715 exact tables for
   pool{50,35}_ndcg10 (already solved to proven optimality there) and adds
   a new pool{50,35}_ndcg5 cell (same candidate pools, cheap to add: no new
   SCIP solve is needed per repair since the repaired graph doesn't depend
   on the metric cutoff -- only the ndcg@k readout does -- so the ndcg5
   cells are computed by re-evaluating the already-solved exact-repaired
   graph at a different cutoff, not by re-solving SCIP).

Two separate pre-specified active families (not merged with each other or
with Task 1/2/3 families): "canonical" and "larger_pool".
"""

# ruff: noqa: I001 -- import order below is semantically constrained (see comment)
from __future__ import annotations

import json
import time
from typing import Any

from networkx import DiGraph

# task4_common must import before full_calibration_utils: it puts the
# latter's directory on sys.path (see task4_common's sys.path bootstrap).
import task4_common as t4
import full_calibration_utils as fcu
from consistency_ranker.mwfas_solver import solve

TIME_LIMIT_S = 300.0
MIP_GAP = 0.0
REGIME = "ms1"

# Section 2A: canonical pool (P=k), every dataset.
CANONICAL_CONFIGS = {ds: (t4.CANONICAL_POOL[ds], t4.CANONICAL_POOL[ds]) for ds in t4.DATASETS}

# Section 2B: Task 1's existing larger-pool exact cells (P, k=10) are reused
# from disk; this script additionally solves the new (P, k=5) cells.
LARGER_POOL_NEW_CONFIGS = {
    "scidocs": (50, 5),
    "fiqa": (50, 5),
    "bright": (50, 5),
    "hotpotqa": (35, 5),
}
TASK1_ROOT = t4.REPO_ROOT / "reports" / "final_revision_task1_pool_cutoff_20260715"
TASK1_EXACT_PAIR_METRICS = TASK1_ROOT / "tables" / "pool_cutoff_exact_pair_metrics.csv"


class ExactCalibrationEvaluator(fcu.CalibrationEvaluator):
    def __init__(self) -> None:
        super().__init__()
        self.solver_rows: list[dict[str, Any]] = []

    def _apply_repair(
        self, graph: DiGraph, prior_scores: dict[str, float], *, top_k: int
    ) -> tuple[DiGraph, dict[str, Any]]:
        del prior_scores, top_k
        dag, removed_edges, status = solve(
            graph, method="scip", return_status=True, time_limit_s=TIME_LIMIT_S, mip_gap=MIP_GAP
        )
        self.solver_rows.append(
            {
                "status": status.status,
                "proven_optimal": status.proven_optimal,
                "trivial": status.trivial,
                "gap": status.gap,
                "time_s": status.time_s,
                "n_nodes": status.n_nodes,
                "objective": status.objective,
                "solver": status.solver,
                "error": status.error,
            }
        )
        return dag, {
            "repair_applied": bool(removed_edges),
            "mode": "scip",
            "removed_edges": [(u, v, float(weight)) for u, v, weight in removed_edges],
            "removed_weight": float(sum(weight for _u, _v, weight in removed_edges)),
            "n_edges_removed": len(removed_edges),
            "solver_status": status.status,
            "solver_proven_optimal": status.proven_optimal,
            "solver_gap": status.gap,
            "solver_time_s": status.time_s,
            "solver_n_nodes": status.n_nodes,
            "solver_objective": status.objective,
        }


def run_configs(configs: dict[str, tuple[int, int]], *, family_label: str) -> dict[str, Any]:
    evaluator = ExactCalibrationEvaluator()
    pair_rows: list[dict[str, Any]] = []
    solver_rows: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []

    for dataset, (pool_size, metric_cutoff) in configs.items():
        config_id = f"pool{pool_size}_ndcg{metric_cutoff}"
        dataset_inputs = t4.rfc._analysis_dataset_inputs(dataset, pool_size_override=pool_size)
        baseline = fcu.raw_baseline_statistics(dataset_inputs)
        pair_margins, _zero_var = t4.rfc._pair_margin_summary(dataset_inputs, "minmax_query_ranker")
        threshold_config = fcu.choose_threshold_config(
            dataset=dataset,
            regime=REGIME,
            calibration="minmax_query_ranker",
            threshold_mode="retention_matched",
            baseline_vote_rates=baseline[REGIME]["vote_rates"],
            baseline_edge_count=baseline[REGIME]["edge_count"],
            calibration_pair_margins=pair_margins,
            per_query_inputs=dataset_inputs["per_query_inputs"],
        )

        for item in dataset_inputs["per_query_inputs"]:
            qid = item["query_id"]
            if len(item["candidate_pool"]) < metric_cutoff:
                exclusions.append(
                    {
                        "dataset": dataset,
                        "config_id": config_id,
                        "query_id": qid,
                        "reason": "pool<cutoff",
                    }
                )
                continue
            artifacts = fcu.build_query_vote_artifacts(
                query_id=qid,
                raw_scores_by_ranker=item["raw_scores_by_ranker"],
                candidate_pool=item["candidate_pool"],
                calibration="minmax_query_ranker",
                threshold_config=threshold_config,
            )
            record = evaluator.evaluate_query(
                dataset=dataset,
                query_id=qid,
                qrels_for_query=item["qrels_for_query"],
                vote_regime=REGIME,
                top_k=metric_cutoff,
                candidate_pool=item["candidate_pool"],
                vote_rows=artifacts["rows"],
                raw_score_maps_by_ranker={
                    ranker: list(score_map.items())
                    for ranker, score_map in item["raw_scores_by_ranker"].items()
                },
            )
            if record is None:
                exclusions.append(
                    {
                        "dataset": dataset,
                        "config_id": config_id,
                        "query_id": qid,
                        "reason": "evaluate_query None",
                    }
                )
                continue
            solver_info = evaluator.solver_rows[-1]
            for pair_name, unrepaired_key, repaired_key, pair_family in t4.rfc.PAIR_SPECS:
                comparison = record["pairwise_comparisons"].get(
                    f"{unrepaired_key}__vs__{repaired_key}"
                )
                unrepaired = record["method_outputs"][unrepaired_key]
                repaired = record["method_outputs"][repaired_key]
                row = {
                    "family": family_label,
                    "dataset": dataset,
                    "regime": REGIME,
                    "config_id": config_id,
                    "pool_size": pool_size,
                    "metric_cutoff": metric_cutoff,
                    "query_id": qid,
                    "pair_name": pair_name,
                    "pair_family": pair_family,
                    "unrepaired_ndcg": float(unrepaired["ndcg_at_k"] or 0.0),
                    "repaired_ndcg": float(repaired["ndcg_at_k"] or 0.0),
                    "delta_ndcg": float(
                        (repaired["ndcg_at_k"] or 0.0) - (unrepaired["ndcg_at_k"] or 0.0)
                    ),
                    "graph_is_cyclic": bool(record["graph_stats"]["is_cyclic"]),
                    "repair_applied": bool(record["repair_info"]["repair_applied"]),
                    "solver_status": record["repair_info"]["solver_status"],
                    "solver_proven_optimal": bool(record["repair_info"]["solver_proven_optimal"]),
                    "solver_time_s": float(record["repair_info"]["solver_time_s"]),
                    "removed_weight": float(record["repair_info"]["removed_weight"]),
                    "n_edges_removed": int(record["repair_info"]["n_edges_removed"]),
                    "top_k_membership_changed": bool(comparison["top_k_membership_changed"])
                    if comparison
                    else None,
                    "top_k_order_changed": bool(comparison["top_k_order_changed"])
                    if comparison
                    else None,
                    "full_ranking_changed": unrepaired["ranking"] != repaired["ranking"],
                    "reused_from": None,
                }
                pair_rows.append(row)
            solver_rows.append(
                {
                    "family": family_label,
                    "dataset": dataset,
                    "config_id": config_id,
                    "query_id": qid,
                    **solver_info,
                }
            )
    return {"pair_rows": pair_rows, "solver_rows": solver_rows, "exclusions": exclusions}


def load_task1_larger_pool_ndcg10() -> list[dict[str, Any]]:
    """Reuse Task 1's existing exact-vs-unrepaired pool{50,35}_ndcg10 rows
    rather than re-solving them."""
    import csv

    rows: list[dict[str, Any]] = []
    with TASK1_EXACT_PAIR_METRICS.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows.append(
                {
                    "family": "larger_pool",
                    "dataset": row["dataset"],
                    "regime": row["regime"],
                    "config_id": row["config_id"],
                    "pool_size": int(row["pool_size"]),
                    "metric_cutoff": int(row["metric_cutoff"]),
                    "query_id": row["query_id"],
                    "pair_name": row["pair_name"],
                    "pair_family": row["pair_family"],
                    "unrepaired_ndcg": float(row["unrepaired_ndcg"]),
                    "repaired_ndcg": float(row["repaired_ndcg"]),
                    "delta_ndcg": float(row["delta_ndcg"]),
                    "graph_is_cyclic": row["graph_is_cyclic"] == "True",
                    "repair_applied": row["repair_applied"] == "True",
                    "solver_status": row["solver_status"],
                    "solver_proven_optimal": row["solver_proven_optimal"] == "True",
                    "solver_time_s": float(row["solver_time_s"]),
                    "removed_weight": float(row["removed_weight"]),
                    "n_edges_removed": None,
                    "top_k_membership_changed": row["top_k_membership_changed"] == "True",
                    "top_k_order_changed": row["top_k_order_changed"] == "True",
                    "full_ranking_changed": row["full_ranking_changed"] == "True",
                    "reused_from": "task1_pool_cutoff_exact",
                }
            )
    return rows


def compute_family_statistics(
    pair_rows: list[dict[str, Any]], family_label: str
) -> list[dict[str, Any]]:
    from collections import defaultdict

    by_key: dict[tuple, list[float]] = defaultdict(list)
    for row in pair_rows:
        if row["family"] != family_label:
            continue
        key = (
            row["dataset"],
            row["regime"],
            row["config_id"],
            row["pair_name"],
            row["pair_family"],
        )
        by_key[key].append(row["delta_ndcg"])

    stats_rows = []
    for key, deltas in sorted(by_key.items()):
        dataset, regime, config_id, pair_name, pair_family = key
        stats = t4.rich_cell_statistics(deltas)
        stats.update(
            {
                "family": family_label,
                "dataset": dataset,
                "regime": regime,
                "config_id": config_id,
                "pair_name": pair_name,
                "pair_family": pair_family,
            }
        )
        stats_rows.append(stats)
    return stats_rows


def holm_correct_family(stats_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pvals = [r["sign_flip_pvalue"] for r in stats_rows]
    holm = t4.stats_inf.holm_adjust(pvals)
    out = []
    for row, holm_p in zip(stats_rows, holm):
        r = dict(row)
        r["holm_adjusted_pvalue"] = holm_p
        r["holm_significant_at_0.05"] = bool(holm_p is not None and holm_p < 0.05)
        out.append(r)
    return out


def main() -> int:
    t0 = time.time()
    all_pair_rows: list[dict[str, Any]] = []
    all_solver_rows: list[dict[str, Any]] = []
    all_exclusions: list[dict[str, Any]] = []

    print("[exact] canonical pool (section 2A, new work)", flush=True)
    canonical_result = run_configs(CANONICAL_CONFIGS, family_label="canonical")
    all_pair_rows.extend(canonical_result["pair_rows"])
    all_solver_rows.extend(canonical_result["solver_rows"])
    all_exclusions.extend(canonical_result["exclusions"])

    print("[exact] larger pool, NEW ndcg5 cells (section 2B extension)", flush=True)
    larger_new_result = run_configs(LARGER_POOL_NEW_CONFIGS, family_label="larger_pool")
    all_pair_rows.extend(larger_new_result["pair_rows"])
    all_solver_rows.extend(larger_new_result["solver_rows"])
    all_exclusions.extend(larger_new_result["exclusions"])

    print("[exact] larger pool, REUSING Task 1's existing ndcg10 cells", flush=True)
    reused_rows = load_task1_larger_pool_ndcg10()
    all_pair_rows.extend(reused_rows)

    t4.write_csv(t4.TABLES_DIR / "exact_repaired_vs_unrepaired_pair_metrics.csv", all_pair_rows)
    t4.write_csv(t4.TABLES_DIR / "exact_repaired_vs_unrepaired_solver_status.csv", all_solver_rows)
    t4.write_csv(t4.TABLES_DIR / "exact_repaired_vs_unrepaired_exclusions.csv", all_exclusions)

    canonical_stats = compute_family_statistics(all_pair_rows, "canonical")
    canonical_stats = holm_correct_family(canonical_stats)
    larger_pool_stats = compute_family_statistics(all_pair_rows, "larger_pool")
    larger_pool_stats = holm_correct_family(larger_pool_stats)

    t4.write_csv(t4.TABLES_DIR / "exact_canonical_family_statistics.csv", canonical_stats)
    t4.write_csv(t4.TABLES_DIR / "exact_larger_pool_family_statistics.csv", larger_pool_stats)

    manifest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "canonical_family_definition": (
            "primary protocol, canonical (P=k) pool, ms1 regime, all 4 datasets, "
            f"all {len(t4.rfc.PAIR_SPECS)} graph-dependent method pairs = "
            f"{len(canonical_stats)} cells, Holm-corrected jointly"
        ),
        "larger_pool_family_definition": (
            "Task 1 larger-pool design, ms1 regime, all 4 datasets, ndcg5 (new) "
            f"and ndcg10 (reused from Task 1) cutoffs, all {len(t4.rfc.PAIR_SPECS)} pairs = "
            f"{len(larger_pool_stats)} cells, Holm-corrected jointly, "
            "SEPARATE from the canonical family"
        ),
        "canonical_family_size": len(canonical_stats),
        "canonical_family_n_significant": sum(
            1 for r in canonical_stats if r["holm_significant_at_0.05"]
        ),
        "larger_pool_family_size": len(larger_pool_stats),
        "larger_pool_family_n_significant": sum(
            1 for r in larger_pool_stats if r["holm_significant_at_0.05"]
        ),
        "reused_task1_rows": len(reused_rows),
        "solver_time_limit_s": TIME_LIMIT_S,
        "mip_gap": MIP_GAP,
        "elapsed_seconds": time.time() - t0,
    }
    t4.write_json(t4.MANIFESTS_DIR / "exact_repaired_vs_unrepaired_run_summary.json", manifest)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
