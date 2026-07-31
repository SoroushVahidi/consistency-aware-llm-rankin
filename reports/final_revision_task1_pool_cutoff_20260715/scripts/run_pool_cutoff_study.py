#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

THIS_DIR = Path(__file__).resolve().parent
REPORT_ROOT = THIS_DIR.parent
REPO_ROOT = REPORT_ROOT.parents[1]
SRC_ROOT = REPO_ROOT / "src"
FULL_CAL_SCRIPTS = REPO_ROOT / "reports" / "full_calibrated_core" / "scripts"

for path in (REPO_ROOT, SRC_ROOT, FULL_CAL_SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import full_calibration_utils as fcu  # noqa: E402
import run_full_calibrated_core as rfc  # noqa: E402

CANONICAL_MANIFEST = (
    REPO_ROOT
    / "experiments"
    / "method_improvement_audit_20260711_205733"
    / "phase_reports"
    / "canonical_rerun_manifest.json"
)
MANUSCRIPT_TEX = REPO_ROOT / "papers" / "JDIQ_2026" / "manuscript" / "main.tex"
MANUSCRIPT_PDF = REPO_ROOT / "papers" / "JDIQ_2026" / "manuscript" / "main.pdf"
FINAL_ANON_DIR = REPO_ROOT / "papers" / "JDIQ_2026" / "submission" / "final_anonymous"
FINAL_ANON_ZIP = REPO_ROOT / "papers" / "JDIQ_2026" / "submission" / "final_anonymous.zip"

TABLES_DIR = REPORT_ROOT / "tables"
MANIFESTS_DIR = REPORT_ROOT / "manifests"
OUTPUTS_DIR = REPORT_ROOT / "outputs" / "greedy_pool_cutoff"
LOGS_DIR = REPORT_ROOT / "logs"

DATASETS = ("scidocs", "fiqa", "hotpotqa", "bright")
REGIMES = ("ms2", "ms1", "ms1_drop_mutual")
DEPTH_CHECKS = (10, 20, 35, 50, 100, 200)
PRESPECIFIED_GRID = {
    "scidocs": ((20, 5), (20, 10), (20, 20), (50, 5), (50, 10), (50, 20)),
    "fiqa": ((20, 5), (20, 10), (20, 20), (50, 5), (50, 10), (50, 20)),
    "bright": ((20, 5), (20, 10), (20, 20), (50, 5), (50, 10), (50, 20)),
    "hotpotqa": ((10, 5), (35, 5), (35, 10), (35, 20)),
}
PRIMARY_PROTOCOL = "minmax_raw_matched"
PAIR_SPECS = (
    ("copeland_graph", "copeland_graph", "copeland_graph_repaired", "graph"),
    ("balance_graph", "balance_graph", "balance_graph_repaired", "graph"),
    ("markov_graph", "markov_graph", "markov_graph_repaired", "graph"),
    (
        "copeland_hybrid",
        "hybrid_unrepaired_copeland_a0p3_minmax",
        "hybrid_repaired_copeland_a0p3_minmax",
        "hybrid",
    ),
    (
        "balance_hybrid",
        "hybrid_unrepaired_balance_a0p3_minmax",
        "hybrid_repaired_balance_a0p3_minmax",
        "hybrid",
    ),
)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fcu.write_csv(path, rows)


def _git_output(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(REPO_ROOT), *args], text=True).strip()


def _repo_state() -> dict[str, Any]:
    status = subprocess.check_output(["git", "-C", str(REPO_ROOT), "status", "--short"], text=True)
    return {
        "branch": _git_output("branch", "--show-current"),
        "commit": _git_output("rev-parse", "HEAD"),
        "working_tree_clean": not status.strip(),
        "status_short": status.splitlines(),
        "manuscript_pdf_sha256": fcu.sha256_file(MANUSCRIPT_PDF),
        "canonical_manifest": str(CANONICAL_MANIFEST),
        "manuscript_tex": str(MANUSCRIPT_TEX),
        "manuscript_pdf": str(MANUSCRIPT_PDF),
        "final_anonymous_dir": str(FINAL_ANON_DIR),
        "final_anonymous_zip": str(FINAL_ANON_ZIP),
    }


def _load_score_lists(
    dataset: str,
) -> tuple[list[str], list[str], dict[str, dict[str, list[tuple[str, float]]]]]:
    manifest = json.loads(CANONICAL_MANIFEST.read_text(encoding="utf-8"))
    query_ids_path = (
        REPO_ROOT
        / "experiments"
        / "method_improvement_audit_20260711_205733"
        / "inputs"
        / dataset
        / "query_ids.txt"
    )
    query_ids = [
        line.strip()
        for line in query_ids_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    usable_query_ids = rfc._analysis_dataset_inputs(dataset)["analysis_query_ids"]
    score_lists: dict[str, dict[str, list[tuple[str, float]]]] = {}
    for ranker, score_path in manifest["score_files"][dataset].items():
        by_query: dict[str, list[tuple[str, float]]] = defaultdict(list)
        with Path(score_path).open(encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                qid = str(row["query_id"])
                if qid not in query_ids:
                    continue
                by_query[qid].append((str(row["doc_id"]), float(row["score"])))
        for qid, rows in by_query.items():
            rows.sort(key=lambda item: (-item[1], item[0]))
        score_lists[ranker] = dict(by_query)
    return query_ids, usable_query_ids, score_lists


def _pairwise_overlap_mean(sets_by_ranker: dict[str, set[str]], depth: int) -> float | None:
    rankers = sorted(sets_by_ranker)
    overlaps = []
    for idx, left in enumerate(rankers):
        for right in rankers[idx + 1 :]:
            overlaps.append(len(sets_by_ranker[left] & sets_by_ranker[right]) / float(depth))
    if not overlaps:
        return None
    return float(sum(overlaps) / len(overlaps))


def build_feasibility_tables() -> dict[str, Any]:
    ranker_rows: list[dict[str, Any]] = []
    depth_rows: list[dict[str, Any]] = []
    config_rows: list[dict[str, Any]] = []
    feasibility_manifest: dict[str, Any] = {}

    for dataset in DATASETS:
        query_ids, usable_query_ids, score_lists = _load_score_lists(dataset)
        ranker_depths: dict[str, dict[str, int]] = {}
        dataset_blob: dict[str, Any] = {
            "query_count": len(query_ids),
            "usable_query_count": len(usable_query_ids),
            "rankers": {},
            "depths": {},
        }
        for ranker, by_query in score_lists.items():
            depth_map = {qid: len(by_query.get(qid, [])) for qid in query_ids}
            usable_depths = [depth_map.get(qid, 0) for qid in usable_query_ids]
            ranker_depths[ranker] = depth_map
            ranker_rows.append(
                {
                    "dataset": dataset,
                    "ranker": ranker,
                    "query_count": len(query_ids),
                    "usable_query_count": len(usable_query_ids),
                    "min_depth_usable": min(usable_depths) if usable_depths else 0,
                    "max_depth_usable": max(usable_depths) if usable_depths else 0,
                    **{
                        f"queries_ge_{depth}": sum(v >= depth for v in usable_depths)
                        for depth in DEPTH_CHECKS
                    },
                }
            )
            dataset_blob["rankers"][ranker] = ranker_rows[-1]

        common_max_depth = min(
            min(ranker_depths[ranker].get(qid, 0) for qid in usable_query_ids)
            for ranker in score_lists
        )
        for depth in DEPTH_CHECKS:
            common_queries = [
                qid
                for qid in usable_query_ids
                if all(ranker_depths[ranker].get(qid, 0) >= depth for ranker in score_lists)
            ]
            if not common_queries:
                depth_row = {
                    "dataset": dataset,
                    "depth": depth,
                    "usable_queries_with_complete_scores": 0,
                    "mean_union_size": None,
                    "min_union_size": None,
                    "max_union_size": None,
                    "mean_missing_score_rate": None,
                    "mean_pairwise_overlap_at_depth": None,
                }
                depth_rows.append(depth_row)
                dataset_blob["depths"][str(depth)] = depth_row
                continue

            union_sizes = []
            missing_rates = []
            overlap_rates = []
            for qid in common_queries:
                sets_by_ranker = {
                    ranker: {doc_id for doc_id, _score in score_lists[ranker][qid][:depth]}
                    for ranker in score_lists
                }
                union_docs = set().union(*sets_by_ranker.values())
                union_sizes.append(len(union_docs))
                observed = sum(len(docs) for docs in sets_by_ranker.values())
                missing_rates.append(1.0 - observed / float(len(sets_by_ranker) * len(union_docs)))
                overlap = _pairwise_overlap_mean(sets_by_ranker, depth)
                if overlap is not None:
                    overlap_rates.append(overlap)

            depth_row = {
                "dataset": dataset,
                "depth": depth,
                "usable_queries_with_complete_scores": len(common_queries),
                "mean_union_size": float(np.mean(union_sizes)),
                "min_union_size": min(union_sizes),
                "max_union_size": max(union_sizes),
                "mean_missing_score_rate": float(np.mean(missing_rates)),
                "mean_pairwise_overlap_at_depth": float(np.mean(overlap_rates))
                if overlap_rates
                else None,
            }
            depth_rows.append(depth_row)
            dataset_blob["depths"][str(depth)] = depth_row

        for pool_size, metric_cutoff in PRESPECIFIED_GRID[dataset]:
            feasible = common_max_depth >= pool_size
            config_rows.append(
                {
                    "dataset": dataset,
                    "config_id": f"pool{pool_size}_ndcg{metric_cutoff}",
                    "pool_size": pool_size,
                    "metric_cutoff": metric_cutoff,
                    "supported_by_complete_scores": feasible,
                    "documented_reason_if_omitted": ""
                    if feasible
                    else f"common stored depth is only {common_max_depth}",
                }
            )
        dataset_blob["common_complete_depth_usable"] = int(common_max_depth)
        feasibility_manifest[dataset] = dataset_blob

    _write_csv(TABLES_DIR / "score_depth_by_ranker.csv", ranker_rows)
    _write_csv(TABLES_DIR / "score_depth_union_overlap.csv", depth_rows)
    _write_csv(TABLES_DIR / "feasible_config_grid.csv", config_rows)
    _write_json(MANIFESTS_DIR / "feasibility.json", feasibility_manifest)
    return feasibility_manifest


def _candidate_coverage(
    candidate_pool: list[str], raw_scores_by_ranker: dict[str, dict[str, float]]
) -> dict[str, Any]:
    coverage: dict[str, Any] = {}
    pool_size = len(candidate_pool)
    for ranker in fcu.RANKERS:
        score_map = raw_scores_by_ranker.get(ranker, {})
        scored_docs = sum(1 for doc_id in candidate_pool if doc_id in score_map)
        coverage[ranker] = {
            "scored_docs": scored_docs,
            "missing_docs": pool_size - scored_docs,
            "coverage_rate": scored_docs / float(pool_size) if pool_size else 0.0,
            "missing_rate": (pool_size - scored_docs) / float(pool_size) if pool_size else 0.0,
        }
    return coverage


def _delta_quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {
            "q05": None,
            "q25": None,
            "q50": None,
            "q75": None,
            "q95": None,
        }
    arr = np.asarray(values, dtype=float)
    q05, q25, q50, q75, q95 = np.quantile(arr, [0.05, 0.25, 0.50, 0.75, 0.95])
    return {
        "q05": float(q05),
        "q25": float(q25),
        "q50": float(q50),
        "q75": float(q75),
        "q95": float(q95),
    }


def _holms_bh(p_values: list[float]) -> tuple[list[float], list[float]]:
    return rfc._holm_adjust(p_values), rfc._bh_adjust(p_values)


def _influence_summary(group: pd.DataFrame, delta_col: str) -> dict[str, Any]:
    deltas = group[delta_col].astype(float).tolist()
    if not deltas:
        return {
            "top_influence_query_id": None,
            "top_influence_delta": None,
            "mean_without_top_influence": None,
            "median_without_top_influence": None,
        }
    abs_idx = int(np.argmax(np.abs(np.asarray(deltas, dtype=float))))
    top_row = group.iloc[abs_idx]
    remaining = [value for idx, value in enumerate(deltas) if idx != abs_idx]
    return {
        "top_influence_query_id": str(top_row["query_id"]),
        "top_influence_delta": float(deltas[abs_idx]),
        "mean_without_top_influence": float(np.mean(remaining)) if remaining else 0.0,
        "median_without_top_influence": float(np.median(remaining)) if remaining else 0.0,
    }


def _cell_statistics(pair_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(pair_rows)
    stats_rows: list[dict[str, Any]] = []
    if df.empty:
        return stats_rows

    for metric_name, delta_col, unrepaired_col, repaired_col in (
        ("ndcg", "delta_ndcg", "unrepaired_ndcg", "repaired_ndcg"),
        ("map", "delta_map", "unrepaired_map", "repaired_map"),
        ("mrr", "delta_mrr", "unrepaired_mrr", "repaired_mrr"),
    ):
        grouped = df.groupby(
            [
                "dataset",
                "regime",
                "config_id",
                "pool_size",
                "metric_cutoff",
                "pair_name",
                "pair_family",
            ],
            dropna=False,
        )
        for keys, group in grouped:
            deltas = group[delta_col].astype(float).tolist()
            quantiles = _delta_quantiles(deltas)
            helped = sum(value > 1.0e-12 for value in deltas)
            harmed = sum(value < -1.0e-12 for value in deltas)
            unchanged = len(deltas) - helped - harmed
            boot_lo, boot_hi, frac_gt_zero = fcu.bootstrap_ci(deltas)
            perm_p = fcu.paired_permutation_pvalue(deltas)
            influence = _influence_summary(group, delta_col)
            stats_rows.append(
                {
                    "dataset": keys[0],
                    "regime": keys[1],
                    "config_id": keys[2],
                    "pool_size": int(keys[3]),
                    "metric_cutoff": int(keys[4]),
                    "pair_name": keys[5],
                    "pair_family": keys[6],
                    "metric": metric_name,
                    "n_paired_queries": len(deltas),
                    "mean_unrepaired": float(group[unrepaired_col].astype(float).mean()),
                    "mean_repaired": float(group[repaired_col].astype(float).mean()),
                    "mean_delta": float(np.mean(deltas)),
                    "median_delta": float(np.median(deltas)),
                    "std_delta": float(np.std(np.asarray(deltas, dtype=float), ddof=0)),
                    "helped_queries": helped,
                    "harmed_queries": harmed,
                    "unchanged_queries": unchanged,
                    "perm_p_value": perm_p,
                    "bootstrap_ci_low": boot_lo,
                    "bootstrap_ci_high": boot_hi,
                    "bootstrap_fraction_gt_zero": frac_gt_zero,
                    "top_influence_query_id": influence["top_influence_query_id"],
                    "top_influence_delta": influence["top_influence_delta"],
                    "mean_without_top_influence": influence["mean_without_top_influence"],
                    "median_without_top_influence": influence["median_without_top_influence"],
                    "q05_delta": quantiles["q05"],
                    "q25_delta": quantiles["q25"],
                    "q50_delta": quantiles["q50"],
                    "q75_delta": quantiles["q75"],
                    "q95_delta": quantiles["q95"],
                    "holm_full_family": None,
                    "bh_full_family": None,
                    "holm_active_ms1_family": None,
                    "bh_active_ms1_family": None,
                }
            )

    ndcg_rows = [row for row in stats_rows if row["metric"] == "ndcg"]
    if ndcg_rows:
        full_holm, full_bh = _holms_bh([float(row["perm_p_value"]) for row in ndcg_rows])
        for row, holm_value, bh_value in zip(ndcg_rows, full_holm, full_bh, strict=True):
            row["holm_full_family"] = holm_value
            row["bh_full_family"] = bh_value

        active_rows = [row for row in ndcg_rows if row["regime"] == "ms1"]
        active_holm, active_bh = _holms_bh([float(row["perm_p_value"]) for row in active_rows])
        for row, holm_value, bh_value in zip(active_rows, active_holm, active_bh, strict=True):
            row["holm_active_ms1_family"] = holm_value
            row["bh_active_ms1_family"] = bh_value

    return stats_rows


def _structural_summary(pair_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(pair_rows)
    rows: list[dict[str, Any]] = []
    if df.empty:
        return rows
    grouped = df.groupby(
        ["dataset", "regime", "config_id", "pool_size", "metric_cutoff", "pair_name"], dropna=False
    )
    for keys, group in grouped:
        rows.append(
            {
                "dataset": keys[0],
                "regime": keys[1],
                "config_id": keys[2],
                "pool_size": int(keys[3]),
                "metric_cutoff": int(keys[4]),
                "pair_name": keys[5],
                "n_queries": len(group),
                "cycle_rate": float(group["graph_is_cyclic"].astype(float).mean()),
                "repair_applied_rate": float(group["repair_applied"].astype(float).mean()),
                "full_ranking_changed_rate": float(
                    group["full_ranking_changed"].astype(float).mean()
                ),
                "top_k_membership_changed_rate": float(
                    group["top_k_membership_changed"].astype(float).mean()
                ),
                "top_k_order_changed_rate": float(
                    group["top_k_order_changed"].astype(float).mean()
                ),
                "differently_graded_judged_pairs_changed_rate": float(
                    group["differently_graded_judged_pairs_changed"].astype(float).mean()
                ),
                "ndcg_changed_rate": float(
                    (group["delta_ndcg"].astype(float).abs() > 1.0e-12).mean()
                ),
                "mean_removed_weight_fraction": float(
                    group["removed_weight_fraction"].astype(float).mean()
                ),
                "mean_graph_density_pre": float(group["graph_density_pre"].astype(float).mean()),
                "mean_graph_density_post": float(group["graph_density_post"].astype(float).mean()),
                "mean_largest_scc_size_pre": float(
                    group["largest_scc_size_pre"].astype(float).mean()
                ),
                "mean_largest_scc_size_post": float(
                    group["largest_scc_size_post"].astype(float).mean()
                ),
                "mean_total_edge_weight_pre": float(
                    group["total_edge_weight_pre"].astype(float).mean()
                ),
                "mean_total_edge_weight_post": float(
                    group["total_edge_weight_post"].astype(float).mean()
                ),
            }
        )
    return rows


def _method_rows_for_query(
    *,
    dataset: str,
    regime: str,
    config_id: str,
    pool_size: int,
    metric_cutoff: int,
    query_id: str,
    method_outputs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    repaired_methods = {repaired for _pair_name, _unrepaired, repaired, _family in PAIR_SPECS}
    unrepaired_methods = {unrepaired for _pair_name, unrepaired, _repaired, _family in PAIR_SPECS}
    for method_key, payload in method_outputs.items():
        if method_key in repaired_methods:
            repair_state = "repaired"
        elif method_key in unrepaired_methods:
            repair_state = "unrepaired"
        else:
            repair_state = "baseline"
        rows.append(
            {
                "dataset": dataset,
                "regime": regime,
                "config_id": config_id,
                "pool_size": pool_size,
                "metric_cutoff": metric_cutoff,
                "query_id": query_id,
                "method_key": method_key,
                "repair_state": repair_state,
                "ranking_json": json.dumps(payload["ranking"]),
                "top_k_prefix_json": json.dumps(payload["top_k_prefix"]),
                "ndcg_at_k": payload["ndcg_at_k"],
                "map_at_k": payload["map_at_k"],
                "mrr_at_k": payload["mrr_at_k"],
                "precision_at_k": payload["precision_at_k"],
                "recall_at_k": payload["recall_at_k"],
                "pairwise_accuracy": payload["pairwise_accuracy"],
                "kendall_tau": payload["kendall_tau"],
            }
        )
    return rows


def run_greedy_study(feasibility: dict[str, Any]) -> dict[str, Any]:
    evaluator = fcu.CalibrationEvaluator()
    pair_rows: list[dict[str, Any]] = []
    method_rows: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    run_manifest: dict[str, Any] = {
        "started_at": fcu.now_iso(),
        "repo_state": _repo_state(),
        "primary_protocol": PRIMARY_PROTOCOL,
        "regimes": list(REGIMES),
        "grid": {
            dataset: [
                f"pool{pool_size}_ndcg{metric_cutoff}"
                for pool_size, metric_cutoff in PRESPECIFIED_GRID[dataset]
            ]
            for dataset in DATASETS
        },
        "cells": [],
    }

    for dataset in DATASETS:
        common_depth = int(feasibility[dataset]["common_complete_depth_usable"])
        feasible_configs = [
            (pool_size, metric_cutoff)
            for pool_size, metric_cutoff in PRESPECIFIED_GRID[dataset]
            if pool_size <= common_depth
        ]
        for pool_size, metric_cutoff in feasible_configs:
            config_id = f"pool{pool_size}_ndcg{metric_cutoff}"
            dataset_inputs = rfc._analysis_dataset_inputs(dataset, pool_size_override=pool_size)
            baseline = fcu.raw_baseline_statistics(dataset_inputs)
            pair_margins, _zero_var = rfc._pair_margin_summary(
                dataset_inputs, "minmax_query_ranker"
            )
            for regime in REGIMES:
                threshold_config = fcu.choose_threshold_config(
                    dataset=dataset,
                    regime=regime,
                    calibration="minmax_query_ranker",
                    threshold_mode="retention_matched",
                    baseline_vote_rates=baseline[regime]["vote_rates"],
                    baseline_edge_count=baseline[regime]["edge_count"],
                    calibration_pair_margins=pair_margins,
                    per_query_inputs=dataset_inputs["per_query_inputs"],
                )
                cell_dir = OUTPUTS_DIR / dataset / regime / config_id
                cell_dir.mkdir(parents=True, exist_ok=True)
                query_records: list[dict[str, Any]] = []
                query_pair_rows: list[dict[str, Any]] = []
                query_method_rows: list[dict[str, Any]] = []
                for item in dataset_inputs["per_query_inputs"]:
                    qid = item["query_id"]
                    if len(item["candidate_pool"]) < metric_cutoff:
                        exclusions.append(
                            {
                                "dataset": dataset,
                                "regime": regime,
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
                    eval_record = evaluator.evaluate_query(
                        dataset=dataset,
                        query_id=qid,
                        qrels_for_query=item["qrels_for_query"],
                        vote_regime=regime,
                        top_k=metric_cutoff,
                        candidate_pool=item["candidate_pool"],
                        vote_rows=artifacts["rows"],
                        raw_score_maps_by_ranker={
                            ranker: list(score_map.items())
                            for ranker, score_map in item["raw_scores_by_ranker"].items()
                        },
                    )
                    if eval_record is None:
                        exclusions.append(
                            {
                                "dataset": dataset,
                                "regime": regime,
                                "config_id": config_id,
                                "query_id": qid,
                                "reason": "evaluate_query returned None",
                            }
                        )
                        continue

                    coverage = _candidate_coverage(
                        item["candidate_pool"], item["raw_scores_by_ranker"]
                    )
                    pair_payloads: dict[str, Any] = {}
                    for pair_name, unrepaired_key, repaired_key, pair_family in PAIR_SPECS:
                        comparison_key = f"{unrepaired_key}__vs__{repaired_key}"
                        comparison = eval_record["pairwise_comparisons"][comparison_key]
                        unrepaired = eval_record["method_outputs"][unrepaired_key]
                        repaired = eval_record["method_outputs"][repaired_key]
                        row = {
                            "dataset": dataset,
                            "regime": regime,
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
                            "graph_is_cyclic": bool(eval_record["graph_stats"]["is_cyclic"]),
                            "repair_applied": bool(eval_record["repair_info"]["repair_applied"]),
                            "repair_removed_edges_count": int(
                                eval_record["repair_info"]["n_edges_removed"]
                            ),
                            "removed_weight": float(eval_record["repair_info"]["removed_weight"]),
                            "removed_weight_fraction": (
                                float(eval_record["repair_info"]["removed_weight"])
                                / float(eval_record["graph_stats"].get("total_edge_weight", 0.0))
                                if float(eval_record["graph_stats"].get("total_edge_weight", 0.0))
                                > 0
                                else 0.0
                            ),
                            "full_ranking_changed": unrepaired["ranking"] != repaired["ranking"],
                            "top_k_membership_changed": bool(
                                comparison["top_k_membership_changed"]
                            ),
                            "top_k_order_changed": bool(comparison["top_k_order_changed"]),
                            "differently_graded_judged_pairs_changed": bool(
                                comparison["differently_graded_judged_pairs_changed"]
                            ),
                            "relevance_sequence_changed": bool(
                                comparison["relevance_sequence_changed"]
                            ),
                            "candidate_pool_size_realized": len(item["candidate_pool"]),
                            "graph_density_pre": float(eval_record["graph_stats"]["graph_density"]),
                            "graph_density_post": float(
                                eval_record["repaired_graph_stats"]["graph_density"]
                            ),
                            "largest_scc_size_pre": int(
                                eval_record["graph_stats"]["largest_scc_size"]
                            ),
                            "largest_scc_size_post": int(
                                eval_record["repaired_graph_stats"]["largest_scc_size"]
                            ),
                            "total_edge_weight_pre": float(
                                eval_record["graph_stats"]["total_edge_weight"]
                            ),
                            "total_edge_weight_post": float(
                                eval_record["repaired_graph_stats"]["total_edge_weight"]
                            ),
                            "removed_edges_json": json.dumps(
                                eval_record["repair_info"]["removed_edges"]
                            ),
                            "bm25_scored_docs": int(coverage["bm25"]["scored_docs"]),
                            "tfidf_scored_docs": int(coverage["tfidf"]["scored_docs"]),
                            "minilm_scored_docs": int(coverage["minilm"]["scored_docs"]),
                            "bm25_missing_rate": float(coverage["bm25"]["missing_rate"]),
                            "tfidf_missing_rate": float(coverage["tfidf"]["missing_rate"]),
                            "minilm_missing_rate": float(coverage["minilm"]["missing_rate"]),
                        }
                        pair_payloads[pair_name] = {
                            "comparison": comparison,
                            "unrepaired_metrics": unrepaired,
                            "repaired_metrics": repaired,
                        }
                        query_pair_rows.append(row)
                        pair_rows.append(row)

                    query_method_rows.extend(
                        _method_rows_for_query(
                            dataset=dataset,
                            regime=regime,
                            config_id=config_id,
                            pool_size=pool_size,
                            metric_cutoff=metric_cutoff,
                            query_id=qid,
                            method_outputs=eval_record["method_outputs"],
                        )
                    )
                    method_rows.extend(query_method_rows[-len(eval_record["method_outputs"]) :])
                    query_records.append(
                        {
                            "dataset": dataset,
                            "regime": regime,
                            "config_id": config_id,
                            "pool_size": pool_size,
                            "metric_cutoff": metric_cutoff,
                            "query_id": qid,
                            "candidate_pool": item["candidate_pool"],
                            "candidate_coverage": coverage,
                            "graph_stats": eval_record["graph_stats"],
                            "repaired_graph_stats": eval_record["repaired_graph_stats"],
                            "repair_info": eval_record["repair_info"],
                            "pair_results": pair_payloads,
                            "method_outputs": eval_record["method_outputs"],
                        }
                    )

                _write_jsonl(cell_dir / "query_records.jsonl", query_records)
                _write_csv(cell_dir / "query_pair_metrics.csv", query_pair_rows)
                _write_csv(cell_dir / "query_method_metrics.csv", query_method_rows)
                cell_manifest = {
                    "dataset": dataset,
                    "regime": regime,
                    "config_id": config_id,
                    "pool_size": pool_size,
                    "metric_cutoff": metric_cutoff,
                    "query_count_with_outputs": len(query_records),
                    "requested_pool_size": dataset_inputs["requested_pool_size"],
                    "pool_policy_id": dataset_inputs["pool_policy_id"],
                    "usable_query_count": dataset_inputs["usable_query_count"],
                    "excluded_query_ids": dataset_inputs["excluded_query_ids"],
                    "thresholds": {
                        "vote_thresholds": threshold_config.vote_thresholds,
                        "aggregate_threshold": threshold_config.aggregate_threshold,
                        "min_support": threshold_config.min_support,
                        "drop_mutual": threshold_config.postprocess_drop_mutual,
                        "notes": threshold_config.notes,
                    },
                }
                _write_json(cell_dir / "manifest.json", cell_manifest)
                run_manifest["cells"].append(cell_manifest)

    stats_rows = _cell_statistics(pair_rows)
    structural_rows = _structural_summary(pair_rows)
    _write_csv(TABLES_DIR / "pool_cutoff_pair_metrics.csv", pair_rows)
    _write_csv(TABLES_DIR / "pool_cutoff_method_metrics.csv", method_rows)
    _write_csv(TABLES_DIR / "pool_cutoff_statistics.csv", stats_rows)
    _write_csv(TABLES_DIR / "pool_cutoff_structural_summary.csv", structural_rows)
    _write_csv(TABLES_DIR / "pool_cutoff_exclusions.csv", exclusions)
    run_manifest["completed_at"] = fcu.now_iso()
    _write_json(MANIFESTS_DIR / "greedy_study_manifest.json", run_manifest)
    return run_manifest


def main() -> int:
    started = time.time()
    for directory in (TABLES_DIR, MANIFESTS_DIR, OUTPUTS_DIR, LOGS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    feasibility = build_feasibility_tables()
    greedy_manifest = run_greedy_study(feasibility)
    summary = {
        "started_at": greedy_manifest["started_at"],
        "completed_at": greedy_manifest["completed_at"],
        "elapsed_seconds": time.time() - started,
        "datasets": list(DATASETS),
        "regimes": list(REGIMES),
        "feasibility_common_depths": {
            dataset: int(blob["common_complete_depth_usable"])
            for dataset, blob in feasibility.items()
        },
        "n_cells": len(greedy_manifest["cells"]),
    }
    _write_json(MANIFESTS_DIR / "run_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
