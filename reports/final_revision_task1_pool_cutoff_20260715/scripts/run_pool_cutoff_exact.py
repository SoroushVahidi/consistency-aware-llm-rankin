#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from networkx import DiGraph

THIS_DIR = Path(__file__).resolve().parent
REPORT_ROOT = THIS_DIR.parent
REPO_ROOT = REPORT_ROOT.parents[1]
SRC_ROOT = REPO_ROOT / "src"
FULL_CAL_SCRIPTS = REPO_ROOT / "reports" / "full_calibrated_core" / "scripts"

for path in (REPO_ROOT, SRC_ROOT, FULL_CAL_SCRIPTS, THIS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import full_calibration_utils as fcu  # noqa: E402
import run_full_calibrated_core as rfc  # noqa: E402
import run_pool_cutoff_study as pcs  # noqa: E402

from consistency_ranker.mwfas_solver import solve  # noqa: E402

OUTPUTS_DIR = REPORT_ROOT / "outputs" / "exact_pool_cutoff"
TABLES_DIR = REPORT_ROOT / "tables"
MANIFESTS_DIR = REPORT_ROOT / "manifests"

TIME_LIMIT_S = 300.0
MIP_GAP = 0.0
REGIME = "ms1"
PRIORITIZED_CONFIGS = {
    "scidocs": (50, 10),
    "fiqa": (50, 10),
    "bright": (50, 10),
    "hotpotqa": (35, 10),
}


class ExactCalibrationEvaluator(fcu.CalibrationEvaluator):
    def __init__(self) -> None:
        super().__init__()
        self.solver_rows: list[dict[str, Any]] = []

    def _apply_repair(
        self,
        graph: DiGraph,
        prior_scores: dict[str, float],
        *,
        top_k: int,
    ) -> tuple[DiGraph, dict[str, Any]]:
        del prior_scores, top_k
        dag, removed_edges, status = solve(
            graph,
            method="scip",
            return_status=True,
            time_limit_s=TIME_LIMIT_S,
            mip_gap=MIP_GAP,
        )
        self.solver_rows.append(
            {
                "status": status.status,
                "proven_optimal": status.proven_optimal,
                "trivial": status.trivial,
                "gap": status.gap,
                "time_s": status.time_s,
                "n_nodes": status.n_nodes,
                "n_vars": status.n_vars,
                "n_constraints": status.n_constraints,
                "objective": status.objective,
                "solver": status.solver,
                "solver_version": status.solver_version,
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
            "solver_trivial": status.trivial,
            "solver_gap": status.gap,
            "solver_time_s": status.time_s,
            "solver_n_nodes": status.n_nodes,
            "solver_n_vars": status.n_vars,
            "solver_n_constraints": status.n_constraints,
            "solver_objective": status.objective,
            "solver_error": status.error,
        }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def run_exact_study() -> dict[str, Any]:
    feasibility = json.loads((MANIFESTS_DIR / "feasibility.json").read_text(encoding="utf-8"))
    evaluator = ExactCalibrationEvaluator()
    pair_rows: list[dict[str, Any]] = []
    solver_rows: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    run_manifest: dict[str, Any] = {
        "started_at": fcu.now_iso(),
        "repo_state": pcs._repo_state(),
        "regime": REGIME,
        "time_limit_s": TIME_LIMIT_S,
        "mip_gap": MIP_GAP,
        "configs": [],
    }

    for dataset, (pool_size, metric_cutoff) in PRIORITIZED_CONFIGS.items():
        common_depth = int(feasibility[dataset]["common_complete_depth_usable"])
        config_id = f"pool{pool_size}_ndcg{metric_cutoff}"
        if pool_size > common_depth:
            exclusions.append(
                {
                    "dataset": dataset,
                    "config_id": config_id,
                    "reason": (
                        f"common complete depth {common_depth} is smaller "
                        f"than requested pool size {pool_size}"
                    ),
                }
            )
            continue

        dataset_inputs = rfc._analysis_dataset_inputs(dataset, pool_size_override=pool_size)
        baseline = fcu.raw_baseline_statistics(dataset_inputs)
        pair_margins, _zero_var = rfc._pair_margin_summary(dataset_inputs, "minmax_query_ranker")
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

        cell_dir = OUTPUTS_DIR / dataset / REGIME / config_id
        cell_dir.mkdir(parents=True, exist_ok=True)
        query_records: list[dict[str, Any]] = []
        query_pair_rows: list[dict[str, Any]] = []

        for item in dataset_inputs["per_query_inputs"]:
            qid = item["query_id"]
            if len(item["candidate_pool"]) < metric_cutoff:
                exclusions.append(
                    {
                        "dataset": dataset,
                        "config_id": config_id,
                        "query_id": qid,
                        "reason": (
                            f"candidate pool size {len(item['candidate_pool'])} is "
                            "smaller than requested "
                            f"metric cutoff {metric_cutoff}"
                        ),
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
                        "reason": "evaluate_query returned None",
                    }
                )
                continue
            coverage = pcs._candidate_coverage(item["candidate_pool"], item["raw_scores_by_ranker"])
            solver_info = evaluator.solver_rows[-1]
            for pair_name, unrepaired_key, repaired_key, pair_family in pcs.PAIR_SPECS:
                comparison = record["pairwise_comparisons"][f"{unrepaired_key}__vs__{repaired_key}"]
                unrepaired = record["method_outputs"][unrepaired_key]
                repaired = record["method_outputs"][repaired_key]
                row = {
                    "dataset": dataset,
                    "regime": REGIME,
                    "config_id": config_id,
                    "pool_size": pool_size,
                    "metric_cutoff": metric_cutoff,
                    "query_id": qid,
                    "pair_name": pair_name,
                    "pair_family": pair_family,
                    "unrepaired_key": unrepaired_key,
                    "repaired_key": repaired_key,
                    "unrepaired_ndcg": float(unrepaired["ndcg_at_k"] or 0.0),
                    "repaired_ndcg": float(repaired["ndcg_at_k"] or 0.0),
                    "delta_ndcg": float(
                        (repaired["ndcg_at_k"] or 0.0) - (unrepaired["ndcg_at_k"] or 0.0)
                    ),
                    "unrepaired_map": float(unrepaired["map_at_k"] or 0.0),
                    "repaired_map": float(repaired["map_at_k"] or 0.0),
                    "delta_map": float(
                        (repaired["map_at_k"] or 0.0) - (unrepaired["map_at_k"] or 0.0)
                    ),
                    "unrepaired_mrr": float(unrepaired["mrr_at_k"] or 0.0),
                    "repaired_mrr": float(repaired["mrr_at_k"] or 0.0),
                    "delta_mrr": float(
                        (repaired["mrr_at_k"] or 0.0) - (unrepaired["mrr_at_k"] or 0.0)
                    ),
                    "graph_is_cyclic": bool(record["graph_stats"]["is_cyclic"]),
                    "repair_applied": bool(record["repair_info"]["repair_applied"]),
                    "solver_status": record["repair_info"]["solver_status"],
                    "solver_proven_optimal": bool(record["repair_info"]["solver_proven_optimal"]),
                    "solver_gap": float(record["repair_info"]["solver_gap"]),
                    "solver_time_s": float(record["repair_info"]["solver_time_s"]),
                    "top_k_membership_changed": bool(comparison["top_k_membership_changed"]),
                    "top_k_order_changed": bool(comparison["top_k_order_changed"]),
                    "differently_graded_judged_pairs_changed": bool(
                        comparison["differently_graded_judged_pairs_changed"]
                    ),
                    "full_ranking_changed": unrepaired["ranking"] != repaired["ranking"],
                    "removed_weight": float(record["repair_info"]["removed_weight"]),
                    "removed_edges_json": json.dumps(record["repair_info"]["removed_edges"]),
                    "bm25_missing_rate": float(coverage["bm25"]["missing_rate"]),
                    "tfidf_missing_rate": float(coverage["tfidf"]["missing_rate"]),
                    "minilm_missing_rate": float(coverage["minilm"]["missing_rate"]),
                }
                pair_rows.append(row)
                query_pair_rows.append(row)

            solver_rows.append(
                {
                    "dataset": dataset,
                    "regime": REGIME,
                    "config_id": config_id,
                    "pool_size": pool_size,
                    "metric_cutoff": metric_cutoff,
                    "query_id": qid,
                    "graph_is_cyclic": bool(record["graph_stats"]["is_cyclic"]),
                    **solver_info,
                }
            )
            query_records.append(
                {
                    "dataset": dataset,
                    "regime": REGIME,
                    "config_id": config_id,
                    "pool_size": pool_size,
                    "metric_cutoff": metric_cutoff,
                    "query_id": qid,
                    "candidate_pool": item["candidate_pool"],
                    "repair_info": record["repair_info"],
                    "solver_info": solver_info,
                    "pairwise_comparisons": record["pairwise_comparisons"],
                    "method_outputs": record["method_outputs"],
                }
            )

        pcs._write_csv(cell_dir / "query_pair_metrics.csv", query_pair_rows)
        _write_jsonl(cell_dir / "query_records.jsonl", query_records)
        _write_json(
            cell_dir / "manifest.json",
            {
                "dataset": dataset,
                "regime": REGIME,
                "config_id": config_id,
                "pool_size": pool_size,
                "metric_cutoff": metric_cutoff,
                "thresholds": {
                    "vote_thresholds": threshold_config.vote_thresholds,
                    "aggregate_threshold": threshold_config.aggregate_threshold,
                    "min_support": threshold_config.min_support,
                    "drop_mutual": threshold_config.postprocess_drop_mutual,
                    "notes": threshold_config.notes,
                },
                "query_count_with_outputs": len(query_records),
            },
        )
        run_manifest["configs"].append(
            {
                "dataset": dataset,
                "config_id": config_id,
                "pool_size": pool_size,
                "metric_cutoff": metric_cutoff,
                "query_count_with_outputs": len(query_records),
            }
        )

    stats_rows = pcs._cell_statistics(pair_rows)
    pcs._write_csv(TABLES_DIR / "pool_cutoff_exact_pair_metrics.csv", pair_rows)
    pcs._write_csv(TABLES_DIR / "pool_cutoff_exact_statistics.csv", stats_rows)
    pcs._write_csv(TABLES_DIR / "pool_cutoff_exact_solver_status.csv", solver_rows)
    pcs._write_csv(TABLES_DIR / "pool_cutoff_exact_exclusions.csv", exclusions)
    run_manifest["completed_at"] = fcu.now_iso()
    _write_json(MANIFESTS_DIR / "exact_study_manifest.json", run_manifest)
    return run_manifest


def main() -> int:
    started = time.time()
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = run_exact_study()
    summary = {
        "started_at": manifest["started_at"],
        "completed_at": manifest["completed_at"],
        "elapsed_seconds": time.time() - started,
        "n_configs": len(manifest["configs"]),
    }
    _write_json(MANIFESTS_DIR / "exact_run_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
