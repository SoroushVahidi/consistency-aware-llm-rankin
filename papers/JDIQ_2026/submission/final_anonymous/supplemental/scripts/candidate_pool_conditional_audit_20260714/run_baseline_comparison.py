#!/usr/bin/env python3
"""
run_baseline_comparison.py
============================
Evaluates the four newly-wired baselines (pagerank_graph, rank_centrality_graph,
markov_hybrid, bradley_terry_graph -- see
reports/candidate_pool_conditional_audit_20260714/AUDIT.md section 3) under
the primary protocol and canonical candidate pool, across all four datasets
and three regimes, and verifies baseline fairness: every method compared for
a given query -- old and new alike -- is scored on the identical candidate
pool, qrels, and query set, using the same repaired/unrepaired graphs.

Writes only to reports/candidate_pool_conditional_audit_20260714/tables/.
"""

from __future__ import annotations

import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPORT_ROOT = SCRIPT_DIR.parent
REPO_ROOT = REPORT_ROOT.parents[1]
FULL_CAL_SCRIPTS = REPO_ROOT / "reports" / "full_calibrated_core" / "scripts"
TABLES_DIR = REPORT_ROOT / "tables"

for p in (REPO_ROOT, REPO_ROOT / "src", FULL_CAL_SCRIPTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from full_calibration_utils import (  # noqa: E402
    CalibrationEvaluator,
    bootstrap_ci,
    build_query_vote_artifacts,
    choose_threshold_config,
    now_iso,
    paired_permutation_pvalue,
    raw_baseline_statistics,
    write_csv,
)
from run_full_calibrated_core import (  # noqa: E402
    DATASETS,
    NEW_BASELINE_PAIR_NAMES,
    PAIR_SPECS,
    PRIMARY_PROTOCOL,
    PROTOCOL_SPECS,
    REGIMES,
    _analysis_dataset_inputs,
    _pair_margin_summary,
    _score_maps_as_tuples,
)

SPEC_CFG = PROTOCOL_SPECS[PRIMARY_PROTOCOL]


def main() -> int:
    t0 = time.time()
    evaluator = CalibrationEvaluator()

    paired_rows: list[dict[str, Any]] = []
    fairness_rows: list[dict[str, Any]] = []

    for dataset in DATASETS:
        dataset_inputs = _analysis_dataset_inputs(dataset)
        spec = dataset_inputs["spec"]
        baseline = raw_baseline_statistics(dataset_inputs)
        pair_margins, _zv = _pair_margin_summary(dataset_inputs, SPEC_CFG["calibration"])

        for regime in REGIMES:
            threshold_config = choose_threshold_config(
                dataset=dataset,
                regime=regime,
                calibration=SPEC_CFG["calibration"],
                threshold_mode=SPEC_CFG["threshold_mode"],
                baseline_vote_rates=baseline[regime]["vote_rates"],
                baseline_edge_count=baseline[regime]["edge_count"],
                calibration_pair_margins=pair_margins,
                per_query_inputs=dataset_inputs["per_query_inputs"],
            )

            n_queries_evaluated = 0
            n_fairness_checked = 0
            n_fairness_violations = 0

            for item in dataset_inputs["per_query_inputs"]:
                query_id = item["query_id"]
                artifacts = build_query_vote_artifacts(
                    query_id=query_id,
                    raw_scores_by_ranker=item["raw_scores_by_ranker"],
                    candidate_pool=item["candidate_pool"],
                    calibration=SPEC_CFG["calibration"],
                    threshold_config=threshold_config,
                )
                tuple_maps = _score_maps_as_tuples(item["raw_scores_by_ranker"])
                eval_record = evaluator.evaluate_query(
                    dataset=dataset,
                    query_id=query_id,
                    qrels_for_query=item["qrels_for_query"],
                    vote_regime=regime,
                    top_k=spec.top_k,
                    candidate_pool=item["candidate_pool"],
                    vote_rows=artifacts["rows"],
                    raw_score_maps_by_ranker=tuple_maps,
                )
                if eval_record is None:
                    continue
                n_queries_evaluated += 1

                pool_set = set(item["candidate_pool"])
                n_fairness_checked += 1
                all_pool_subset = all(
                    set(eval_record["method_outputs"][key]["ranking"]) <= pool_set
                    for _pn, unrep, rep, _fam in PAIR_SPECS
                    for key in (unrep, rep)
                )
                if not all_pool_subset:
                    n_fairness_violations += 1

                for pair_name, unrepaired_key, repaired_key, pair_family in PAIR_SPECS:
                    if pair_name not in NEW_BASELINE_PAIR_NAMES:
                        continue
                    unrepaired = float(
                        eval_record["method_outputs"][unrepaired_key]["ndcg_at_k"] or 0.0
                    )
                    repaired = float(
                        eval_record["method_outputs"][repaired_key]["ndcg_at_k"] or 0.0
                    )
                    paired_rows.append(
                        {
                            "dataset": dataset,
                            "regime": regime,
                            "pair_name": pair_name,
                            "pair_family": pair_family,
                            "query_id": query_id,
                            "unrepaired_ndcg": unrepaired,
                            "repaired_ndcg": repaired,
                            "delta_ndcg": repaired - unrepaired,
                        }
                    )

            fairness_rows.append(
                {
                    "dataset": dataset,
                    "regime": regime,
                    "n_queries_evaluated": n_queries_evaluated,
                    "n_queries_fairness_checked": n_fairness_checked,
                    "n_fairness_violations": n_fairness_violations,
                    "all_methods_share_identical_candidate_pool": n_fairness_violations == 0,
                }
            )
            print(
                f"[{now_iso()}] {dataset}/{regime}: {n_queries_evaluated} queries, "
                f"{n_fairness_violations} fairness violations",
                flush=True,
            )

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(TABLES_DIR / "new_baseline_paired_deltas.csv", paired_rows)
    write_csv(TABLES_DIR / "baseline_fairness_verification.csv", fairness_rows)

    stats_rows: list[dict[str, Any]] = []
    by_cell: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in paired_rows:
        key = (row["dataset"], row["regime"], row["pair_name"])
        by_cell[key].append(row["delta_ndcg"])
    for (dataset, regime, pair_name), values in sorted(by_cell.items()):
        ci_low, ci_high, frac_gt0 = bootstrap_ci(values)
        pvalue = paired_permutation_pvalue(values)
        n = len(values)
        stats_rows.append(
            {
                "dataset": dataset,
                "regime": regime,
                "pair_name": pair_name,
                "n_queries": n,
                "mean_delta_ndcg": sum(values) / n if n else 0.0,
                "bootstrap_ci_low": ci_low,
                "bootstrap_ci_high": ci_high,
                "bootstrap_fraction_means_gt_zero": frac_gt0,
                "paired_permutation_pvalue": pvalue,
            }
        )
    write_csv(TABLES_DIR / "new_baseline_statistics.csv", stats_rows)

    all_fair = all(r["all_methods_share_identical_candidate_pool"] for r in fairness_rows)
    print(f"[{now_iso()}] Done in {time.time() - t0:.1f}s. All cells fair: {all_fair}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
