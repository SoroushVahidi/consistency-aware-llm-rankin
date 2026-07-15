#!/usr/bin/env python3
"""
run_conditional_and_failure_analysis.py
=========================================
Two related analyses, both built on the same per-query classification
(conditional_subsets.classify_query_pair), computed fresh because the
subset/decomposition definitions need each method's full ranking, which the
canonical pipeline's persisted JSONL records never store (only nDCG/MAP/etc
scalars).

1. Conditional analysis (task step 4): for the PRIMARY protocol under the
   CANONICAL candidate pool -- the manuscript's actual repaired-vs-
   unrepaired setting -- report mean/median delta_ndcg and sample size for
   six query subsets (all, has_cycle, repair_active, ranking_changed,
   topk_changed, relevance_order_changed), per dataset/regime/pair.

2. Failure decomposition (task step 5): a five-category, mutually exclusive
   accounting of why repair did or did not produce a measurable metric
   change, computed for:
     (a) every one of the four canonical protocols from the normalization-
         protocol redesign (raw_fixed, minmax_raw_matched, minmax_quantile,
         rank_percentile), under the canonical pool -- "every protocol and
         dataset" as literally requested;
     (b) the primary protocol under every one of the five candidate-pool
         policies -- a direct extension connecting this task's pool-
         robustness work to the failure-decomposition requirement, showing
         how pool choice changes the inactive-repair fractions.

Writes only to reports/candidate_pool_conditional_audit_20260714/tables/.
No manuscript figures are touched.
"""

from __future__ import annotations

import argparse
import sys
import time
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

from candidate_pool_policies import POOL_SPECS  # noqa: E402
from conditional_subsets import (  # noqa: E402
    SUBSET_DEFINITIONS,
    classify_query_pair,
    failure_decomposition_counts,
)
from full_calibration_utils import (  # noqa: E402
    CalibrationEvaluator,
    build_query_vote_artifacts,
    choose_threshold_config,
    now_iso,
    raw_baseline_statistics,
    write_csv,
)
from run_full_calibrated_core import (  # noqa: E402
    DATASETS,
    PAIR_SPECS,
    PRIMARY_PROTOCOL,
    PROTOCOL_SPECS,
    REGIMES,
    _analysis_dataset_inputs,
    _pair_margin_summary,
    _score_maps_as_tuples,
)

CANONICAL_TASK2_PROTOCOLS = [
    "ablation_raw_fixed",
    "primary_minmax_retention_matched",
    "independent_minmax_quantile_q0p5",
    "independent_rank_percentile_q0p5",
]


def _evaluate_cell(
    evaluator: CalibrationEvaluator,
    *,
    dataset: str,
    regime: str,
    protocol: str,
    pool_id: str | None,
) -> list[dict[str, Any]]:
    """Returns a list of per-query eval_record dicts (with query_id and
    top_k attached) for one (protocol, pool, dataset, regime) cell."""
    spec_cfg = PROTOCOL_SPECS[protocol]
    pool_spec = POOL_SPECS[pool_id] if pool_id is not None else None
    dataset_inputs = _analysis_dataset_inputs(dataset, pool_policy=pool_spec)
    spec = dataset_inputs["spec"]
    baseline = raw_baseline_statistics(dataset_inputs)
    pair_margins, _zv = _pair_margin_summary(dataset_inputs, spec_cfg["calibration"])
    threshold_config = choose_threshold_config(
        dataset=dataset,
        regime=regime,
        calibration=spec_cfg["calibration"],
        threshold_mode=spec_cfg["threshold_mode"],
        baseline_vote_rates=baseline[regime]["vote_rates"],
        baseline_edge_count=baseline[regime]["edge_count"],
        calibration_pair_margins=pair_margins,
        per_query_inputs=dataset_inputs["per_query_inputs"],
    )

    out: list[dict[str, Any]] = []
    for item in dataset_inputs["per_query_inputs"]:
        query_id = item["query_id"]
        artifacts = build_query_vote_artifacts(
            query_id=query_id,
            raw_scores_by_ranker=item["raw_scores_by_ranker"],
            candidate_pool=item["candidate_pool"],
            calibration=spec_cfg["calibration"],
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
        eval_record["query_id"] = query_id
        eval_record["top_k"] = spec.top_k
        out.append(eval_record)
    return out


def run_conditional_analysis(
    evaluator: CalibrationEvaluator, datasets: list[str]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dataset in datasets:
        for regime in REGIMES:
            records = _evaluate_cell(
                evaluator, dataset=dataset, regime=regime, protocol=PRIMARY_PROTOCOL, pool_id=None
            )
            for pair_name, unrepaired_key, repaired_key, pair_family in PAIR_SPECS:
                per_query = []
                for rec in records:
                    flags = classify_query_pair(
                        rec,
                        unrepaired_key=unrepaired_key,
                        repaired_key=repaired_key,
                        top_k=rec["top_k"],
                    )
                    unrep_ndcg = float(rec["method_outputs"][unrepaired_key]["ndcg_at_k"] or 0.0)
                    rep_ndcg = float(rec["method_outputs"][repaired_key]["ndcg_at_k"] or 0.0)
                    per_query.append({"flags": flags, "delta_ndcg": rep_ndcg - unrep_ndcg})

                for subset_name in SUBSET_DEFINITIONS:
                    if subset_name == "all":
                        subset_rows = per_query
                    else:
                        subset_rows = [r for r in per_query if r["flags"][subset_name]]
                    n = len(subset_rows)
                    deltas = [r["delta_ndcg"] for r in subset_rows]
                    mean_delta = sum(deltas) / n if n else None
                    rows.append(
                        {
                            "dataset": dataset,
                            "regime": regime,
                            "pair_name": pair_name,
                            "pair_family": pair_family,
                            "subset": subset_name,
                            "subset_definition": SUBSET_DEFINITIONS[subset_name],
                            "n_queries": n,
                            "n_queries_total_in_cell": len(per_query),
                            "mean_delta_ndcg": mean_delta,
                        }
                    )
    return rows


def run_failure_decomposition_by_protocol(
    evaluator: CalibrationEvaluator, datasets: list[str]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for protocol in CANONICAL_TASK2_PROTOCOLS:
        for dataset in datasets:
            for regime in REGIMES:
                records = _evaluate_cell(
                    evaluator, dataset=dataset, regime=regime, protocol=protocol, pool_id=None
                )
                for pair_name, unrepaired_key, repaired_key, pair_family in PAIR_SPECS:
                    flags_list = [
                        classify_query_pair(
                            rec,
                            unrepaired_key=unrepaired_key,
                            repaired_key=repaired_key,
                            top_k=rec["top_k"],
                        )
                        for rec in records
                    ]
                    counts = failure_decomposition_counts(flags_list)
                    rows.append(
                        {
                            "axis": "protocol",
                            "protocol": protocol,
                            "protocol_label": PROTOCOL_SPECS[protocol]["label"],
                            "pool_id": "rrf_union_topk",
                            "dataset": dataset,
                            "regime": regime,
                            "pair_name": pair_name,
                            "pair_family": pair_family,
                            **counts,
                        }
                    )
    return rows


def run_failure_decomposition_by_pool(
    evaluator: CalibrationEvaluator, datasets: list[str]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pool_id in POOL_SPECS:
        for dataset in datasets:
            for regime in REGIMES:
                records = _evaluate_cell(
                    evaluator,
                    dataset=dataset,
                    regime=regime,
                    protocol=PRIMARY_PROTOCOL,
                    pool_id=pool_id,
                )
                for pair_name, unrepaired_key, repaired_key, pair_family in PAIR_SPECS:
                    flags_list = [
                        classify_query_pair(
                            rec,
                            unrepaired_key=unrepaired_key,
                            repaired_key=repaired_key,
                            top_k=rec["top_k"],
                        )
                        for rec in records
                    ]
                    counts = failure_decomposition_counts(flags_list)
                    rows.append(
                        {
                            "axis": "pool",
                            "protocol": PRIMARY_PROTOCOL,
                            "protocol_label": PROTOCOL_SPECS[PRIMARY_PROTOCOL]["label"],
                            "pool_id": pool_id,
                            "dataset": dataset,
                            "regime": regime,
                            "pair_name": pair_name,
                            "pair_family": pair_family,
                            **counts,
                        }
                    )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", default=",".join(DATASETS))
    args = parser.parse_args()
    datasets = args.datasets.split(",")

    t0 = time.time()
    evaluator = CalibrationEvaluator()

    print(f"[{now_iso()}] conditional analysis (primary protocol x canonical pool)...", flush=True)
    conditional_rows = run_conditional_analysis(evaluator, datasets)

    print(f"[{now_iso()}] failure decomposition by protocol...", flush=True)
    failure_by_protocol_rows = run_failure_decomposition_by_protocol(evaluator, datasets)

    print(f"[{now_iso()}] failure decomposition by pool...", flush=True)
    failure_by_pool_rows = run_failure_decomposition_by_pool(evaluator, datasets)

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(TABLES_DIR / "conditional_analysis_primary_protocol.csv", conditional_rows)
    write_csv(TABLES_DIR / "failure_decomposition_by_protocol.csv", failure_by_protocol_rows)
    write_csv(TABLES_DIR / "failure_decomposition_by_pool.csv", failure_by_pool_rows)

    print(f"[{now_iso()}] Done in {time.time() - t0:.1f}s.", flush=True)
    print(
        f"  conditional_analysis rows={len(conditional_rows)} "
        f"failure_by_protocol rows={len(failure_by_protocol_rows)} "
        f"failure_by_pool rows={len(failure_by_pool_rows)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
