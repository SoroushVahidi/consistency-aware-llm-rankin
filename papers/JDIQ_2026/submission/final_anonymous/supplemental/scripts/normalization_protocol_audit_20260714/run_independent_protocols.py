#!/usr/bin/env python3
"""
run_independent_protocols.py
=============================
Runs the newly-added, independently-defined normalization/threshold
protocols (see PROTOCOL_SPECS in full_calibration_utils's sibling driver,
run_full_calibrated_core.py) across all four datasets and all three vote
regimes, using the exact same canonical pipeline (CalibrationEvaluator,
choose_threshold_config, build_query_vote_artifacts) that produced every
other committed protocol's numbers.

Deliberately does NOT call run_full_calibrated_core.run_full_core(), and
contains no plotting/figure code at all: this task is scoped to not touch
any manuscript figure. It writes:

  - per-query JSONL + manifest.json under
    reports/full_calibrated_core/outputs/calibrated_all4/protocol_runs/
    {protocol}/{dataset}/{regime}/ -- the same directory layout and record
    schema as every existing protocol, so downstream tooling (including
    figure regeneration in a later task) can treat old and new protocols
    identically.
  - cell-level structural/retrieval diagnostic CSVs under
    reports/normalization_protocol_audit_20260714/tables/.

Usage:
    python run_independent_protocols.py [--datasets a,b] [--protocols x,y]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
REPORT_ROOT = SCRIPT_DIR.parent
REPO_ROOT = REPORT_ROOT.parents[1]
FULL_CAL_SCRIPTS = REPO_ROOT / "reports" / "full_calibrated_core" / "scripts"
TABLES_DIR = REPORT_ROOT / "tables"
MANIFESTS_DIR = REPORT_ROOT / "manifests"

for p in (REPO_ROOT, REPO_ROOT / "src", FULL_CAL_SCRIPTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from full_calibration_utils import (  # noqa: E402
    RANKERS,
    CalibrationEvaluator,
    bootstrap_ci,
    build_query_vote_artifacts,
    choose_threshold_config,
    jaccard,
    now_iso,
    paired_permutation_pvalue,
    raw_baseline_statistics,
    sha256_file,
    write_csv,
)
from run_full_calibrated_core import (  # noqa: E402
    DATASETS,
    METHOD_KEYS,
    METHOD_LABELS,
    PAIR_SPECS,
    PRIMARY_PROTOCOL,
    PROTOCOL_SPECS,
    RAW_PROTOCOL,
    REGIMES,
    RUN_OUTPUT_ROOT,
    _analysis_dataset_inputs,
    _config_dir,
    _maybe_float,
    _mutual_pair_weight_share,
    _pair_margin_summary,
    _ranker_weight_summary,
    _repo_context,
    _scc_count_gt1,
    _score_maps_as_tuples,
    _serializable_query_record,
    _support_map_from_rows,
    _write_json,
    _write_jsonl,
)

# The six independently-defined protocols added for this task. q=0.5 is the
# pre-registered primary comparison point; q=0.3/0.7 are the low/high
# selectivity sensitivity grid.
NEW_PROTOCOLS = [
    "independent_minmax_quantile_q0p5",
    "independent_minmax_quantile_q0p3",
    "independent_minmax_quantile_q0p7",
    "independent_rank_percentile_q0p5",
    "independent_rank_percentile_q0p3",
    "independent_rank_percentile_q0p7",
]
# Existing protocols read back in for overlap diagnostics (already-committed
# query_records.jsonl, never modified or re-run by this script).
COMPARISON_PROTOCOLS = [RAW_PROTOCOL, PRIMARY_PROTOCOL]


def _load_existing_removed_edges(
    protocol: str, dataset: str, regime: str
) -> dict[str, set[tuple[str, str]]]:
    """Read an already-committed protocol's per-query removed-edge sets, for
    overlap diagnostics only. Never writes to that protocol's directory."""
    path = RUN_OUTPUT_ROOT / protocol / dataset / regime / "query_records.jsonl"
    out: dict[str, set[tuple[str, str]]] = {}
    if not path.exists():
        return out
    with path.open() as fh:
        for line in fh:
            rec = json.loads(line)
            out[rec["query_id"]] = {tuple(e) for e in rec["removed_edges"]}
    return out


def _eligible_pair_counts(
    raw_scores_by_ranker: dict[str, dict[str, float]], candidate_pool: list[str]
) -> dict[str, int]:
    """Number of candidate pairs, per ranker, for which both documents are
    scored and the native scores differ -- the same "possible" denominator
    used by raw_baseline_statistics, independent of calibration or
    thresholding. This is the pairwise-comparison count eligible to receive
    a vote from that ranker at all."""
    counts: dict[str, int] = {}
    for ranker in RANKERS:
        score_map = raw_scores_by_ranker.get(ranker, {})
        n = 0
        for a, b in combinations(candidate_pool, 2):
            if a in score_map and b in score_map and score_map[a] != score_map[b]:
                n += 1
        counts[ranker] = n
    return counts


def run_one_cell(
    *,
    evaluator: CalibrationEvaluator,
    dataset: str,
    dataset_inputs: dict[str, Any],
    protocol: str,
    regime: str,
    repo: dict[str, Any],
    dataset_score_hashes: dict[str, str],
) -> dict[str, Any]:
    spec_cfg = PROTOCOL_SPECS[protocol]
    spec = dataset_inputs["spec"]
    baseline = raw_baseline_statistics(dataset_inputs)
    pair_margins, zero_variance = _pair_margin_summary(dataset_inputs, spec_cfg["calibration"])
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

    out_dir = _config_dir(protocol, dataset, regime)
    out_dir.mkdir(parents=True, exist_ok=True)

    query_records: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    paired_rows: list[dict[str, Any]] = []
    structural_rows: list[dict[str, Any]] = []
    ranker_rows: list[dict[str, Any]] = []
    exclusion_rows: list[dict[str, Any]] = []
    valid_query_ids: list[str] = []

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
            exclusion_rows.append(
                {
                    "dataset": dataset,
                    "query_id": query_id,
                    "protocol": protocol,
                    "regime": regime,
                    "exclusion_reason": "no_valid_graph_output",
                }
            )
            continue

        eligible_counts = _eligible_pair_counts(
            item["raw_scores_by_ranker"], item["candidate_pool"]
        )
        for ranker in RANKERS:
            n_eligible = eligible_counts[ranker]
            n_nontied = len(artifacts["pair_margins_by_ranker"].get(ranker, []))
            n_retained = int(artifacts["retained_vote_counts"].get(ranker, 0))
            ranker_rows.append(
                {
                    "dataset": dataset,
                    "protocol": protocol,
                    "protocol_label": spec_cfg["label"],
                    "protocol_kind": spec_cfg["kind"],
                    "regime": regime,
                    "query_id": query_id,
                    "ranker": ranker,
                    "n_eligible_pairs": n_eligible,
                    "n_nontied_margins": n_nontied,
                    "n_retained_votes": n_retained,
                    "retained_vote_rate_of_eligible": (n_retained / n_eligible)
                    if n_eligible > 0
                    else None,
                    "retained_vote_rate_of_nontied": (n_retained / n_nontied)
                    if n_nontied > 0
                    else None,
                    "vote_threshold": threshold_config.vote_thresholds.get(ranker, 0.0),
                }
            )

        edge_support = _support_map_from_rows(artifacts["rows"])
        query_records.append(
            _serializable_query_record(
                dataset=dataset,
                protocol=protocol,
                regime=regime,
                query_id=query_id,
                artifacts=artifacts,
                threshold_config=threshold_config,
                eval_record=eval_record,
                edge_support=edge_support,
                extra_methods={},
            )
        )
        valid_query_ids.append(query_id)

        for method_key in METHOD_KEYS:
            metric_rows.append(
                {
                    "dataset": dataset,
                    "protocol": protocol,
                    "protocol_label": spec_cfg["label"],
                    "regime": regime,
                    "query_id": query_id,
                    "method_key": method_key,
                    "method": METHOD_LABELS[method_key],
                    "ndcg_at_k": _maybe_float(
                        eval_record["method_outputs"][method_key]["ndcg_at_k"]
                    ),
                }
            )

        for pair_name, unrepaired_key, repaired_key, pair_family in PAIR_SPECS:
            unrepaired = float(eval_record["method_outputs"][unrepaired_key]["ndcg_at_k"] or 0.0)
            repaired = float(eval_record["method_outputs"][repaired_key]["ndcg_at_k"] or 0.0)
            paired_rows.append(
                {
                    "dataset": dataset,
                    "protocol": protocol,
                    "protocol_label": spec_cfg["label"],
                    "protocol_kind": spec_cfg["kind"],
                    "regime": regime,
                    "pair_name": pair_name,
                    "pair_family": pair_family,
                    "query_id": query_id,
                    "unrepaired_ndcg": unrepaired,
                    "repaired_ndcg": repaired,
                    "delta_ndcg": repaired - unrepaired,
                }
            )

        gs = eval_record["graph_stats"]
        rgs = eval_record["repaired_graph_stats"]
        mrs = eval_record["mutual_removed_stats"]
        graph = eval_record["graph"]
        total_weight = float(gs.get("total_edge_weight", 0.0) or 0.0)
        structural_rows.append(
            {
                "dataset": dataset,
                "protocol": protocol,
                "protocol_label": spec_cfg["label"],
                "protocol_kind": spec_cfg["kind"],
                "regime": regime,
                "query_id": query_id,
                "n_nodes": gs.get("n_nodes"),
                "n_edges": gs.get("n_edges"),
                "graph_density": gs.get("graph_density"),
                "total_edge_weight": total_weight,
                "is_cyclic": gs.get("is_cyclic"),
                "n_mutual_pairs": gs.get("n_mutual_pairs"),
                "largest_scc_size": gs.get("largest_scc_size"),
                "n_sccs_gt1": _scc_count_gt1(graph),
                "mutual_pair_weight_share": _mutual_pair_weight_share(graph),
                # After deleting direct mutual-pair edges (both directions
                # retained for the same pair): isolates whether cyclicity is
                # direct bidirectional contradiction or longer-cycle
                # nontransitivity, matching the manuscript's mutual-pair /
                # nontrivial-cycle decomposition (Sec. "Mutual Pairs Versus
                # Residual Nontrivial Cyclicity").
                "is_cyclic_after_mutual_deletion": mrs.get("is_cyclic"),
                "largest_scc_after_mutual_deletion": mrs.get("largest_scc_size"),
                "repaired_is_dag": rgs.get("is_dag"),
                "repaired_largest_scc_size": rgs.get("largest_scc_size"),
                "n_edges_removed": len(eval_record["removed_edges"]),
                "removed_weight": sum(
                    float(graph[u][v].get("weight", 1.0))
                    for u, v in eval_record["removed_edges"]
                    if graph.has_edge(u, v)
                ),
                "normalized_fas_weight_removed": (
                    sum(
                        float(graph[u][v].get("weight", 1.0))
                        for u, v in eval_record["removed_edges"]
                        if graph.has_edge(u, v)
                    )
                    / total_weight
                    if total_weight > 0
                    else 0.0
                ),
                "ranker_weight_summary": _ranker_weight_summary(edge_support),
            }
        )

    _write_jsonl(out_dir / "query_records.jsonl", query_records)
    write_csv(out_dir / "query_method_metrics.csv", metric_rows)
    manifest = {
        "generated_at": now_iso(),
        "branch": repo["branch"],
        "head": repo["head"],
        "dataset": dataset,
        "protocol": protocol,
        "protocol_spec": spec_cfg,
        "regime": regime,
        "qrels_hash": dataset_inputs.get("qrels_hash", "unavailable"),
        "query_ids": valid_query_ids,
        "excluded_query_ids": [row["query_id"] for row in exclusion_rows],
        "seed": 13,
        "source_score_hashes": dataset_score_hashes,
        "thresholds": {
            "vote_thresholds": threshold_config.vote_thresholds,
            "aggregate_threshold": threshold_config.aggregate_threshold,
            "min_support": threshold_config.min_support,
            "drop_mutual": threshold_config.postprocess_drop_mutual,
            "notes": threshold_config.notes,
        },
        "generation_script": str(Path(__file__).resolve()),
        "output_files": {
            "query_records": str(out_dir / "query_records.jsonl"),
            "query_method_metrics": str(out_dir / "query_method_metrics.csv"),
        },
    }
    _write_json(out_dir / "manifest.json", manifest)

    return {
        "paired_rows": paired_rows,
        "structural_rows": structural_rows,
        "ranker_rows": ranker_rows,
        "exclusion_rows": exclusion_rows,
        "n_queries": len(valid_query_ids),
        "query_ids": valid_query_ids,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", default=",".join(DATASETS))
    parser.add_argument("--protocols", default=",".join(NEW_PROTOCOLS))
    args = parser.parse_args()
    datasets = args.datasets.split(",")
    protocols = args.protocols.split(",")
    for protocol in protocols:
        if protocol not in PROTOCOL_SPECS:
            raise ValueError(f"Unknown protocol {protocol!r}; not in PROTOCOL_SPECS")

    t0 = time.time()
    repo = _repo_context()
    evaluator = CalibrationEvaluator()

    all_paired_rows: list[dict[str, Any]] = []
    all_structural_rows: list[dict[str, Any]] = []
    all_ranker_rows: list[dict[str, Any]] = []
    all_exclusion_rows: list[dict[str, Any]] = []
    overlap_rows: list[dict[str, Any]] = []

    for dataset in datasets:
        dataset_inputs = _analysis_dataset_inputs(dataset)
        spec = dataset_inputs["spec"]
        dataset_score_hashes = {ranker: sha256_file(spec.score_files[ranker]) for ranker in RANKERS}
        n_usable = dataset_inputs["usable_query_count"]
        print(
            f"[{now_iso()}] dataset={dataset} usable_queries={n_usable}",
            flush=True,
        )

        for protocol in protocols:
            for regime in REGIMES:
                cell_t0 = time.time()
                result = run_one_cell(
                    evaluator=evaluator,
                    dataset=dataset,
                    dataset_inputs=dataset_inputs,
                    protocol=protocol,
                    regime=regime,
                    repo=repo,
                    dataset_score_hashes=dataset_score_hashes,
                )
                all_paired_rows.extend(result["paired_rows"])
                all_structural_rows.extend(result["structural_rows"])
                all_ranker_rows.extend(result["ranker_rows"])
                all_exclusion_rows.extend(result["exclusion_rows"])
                print(
                    f"[{now_iso()}] {dataset}/{protocol}/{regime}: "
                    f"{result['n_queries']} queries in {time.time() - cell_t0:.1f}s",
                    flush=True,
                )

                # Overlap diagnostics vs raw_fixed and minmax_raw_matched
                # (read-only; never writes into those protocols' directories).
                new_removed = _load_existing_removed_edges(protocol, dataset, regime)
                for comp_protocol in COMPARISON_PROTOCOLS:
                    comp_removed = _load_existing_removed_edges(comp_protocol, dataset, regime)
                    common_ids = sorted(set(new_removed) & set(comp_removed))
                    jaccards = [jaccard(new_removed[qid], comp_removed[qid]) for qid in common_ids]
                    jaccards = [j for j in jaccards if j is not None]
                    overlap_rows.append(
                        {
                            "dataset": dataset,
                            "protocol": protocol,
                            "regime": regime,
                            "compared_against": comp_protocol,
                            "n_common_queries": len(common_ids),
                            "mean_removed_edge_jaccard": float(np.mean(jaccards))
                            if jaccards
                            else None,
                            "median_removed_edge_jaccard": float(np.median(jaccards))
                            if jaccards
                            else None,
                        }
                    )

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(TABLES_DIR / "independent_protocol_paired_deltas.csv", all_paired_rows)
    write_csv(TABLES_DIR / "independent_protocol_structural_per_query.csv", all_structural_rows)
    write_csv(TABLES_DIR / "independent_protocol_ranker_diagnostics_per_query.csv", all_ranker_rows)
    write_csv(TABLES_DIR / "independent_protocol_exclusions.csv", all_exclusion_rows)
    write_csv(TABLES_DIR / "independent_protocol_removed_edge_overlap.csv", overlap_rows)

    # Cell-level (dataset/protocol/regime/ranker) aggregation of the
    # per-query ranker diagnostics: mean retained-vote rate, mutual-pair
    # prevalence, and cyclicity prevalence before/after mutual-pair deletion.
    diag_rows: list[dict[str, Any]] = []
    by_diag_cell: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in all_structural_rows:
        by_diag_cell[(row["dataset"], row["protocol"], row["regime"])].append(row)
    ranker_by_cell: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in all_ranker_rows:
        ranker_by_cell[(row["dataset"], row["protocol"], row["regime"], row["ranker"])].append(row)
    for (dataset, protocol, regime), rows in sorted(by_diag_cell.items()):
        n = len(rows)
        cyclic_before = sum(1 for r in rows if r["is_cyclic"])
        cyclic_after = sum(1 for r in rows if r["is_cyclic_after_mutual_deletion"])
        mutual_prevalence = sum(1 for r in rows if (r["n_mutual_pairs"] or 0) > 0)
        cell = {
            "dataset": dataset,
            "protocol": protocol,
            "protocol_label": PROTOCOL_SPECS[protocol]["label"],
            "protocol_kind": PROTOCOL_SPECS[protocol]["kind"],
            "regime": regime,
            "n_queries": n,
            "cyclic_query_pct": 100.0 * cyclic_before / n if n else None,
            "cyclic_query_pct_after_mutual_deletion": 100.0 * cyclic_after / n if n else None,
            "mutual_pair_query_prevalence_pct": 100.0 * mutual_prevalence / n if n else None,
            "mean_graph_density": float(
                np.mean([r["graph_density"] for r in rows if r["graph_density"] is not None])
            )
            if rows
            else None,
            "mean_largest_scc_size": float(
                np.mean([r["largest_scc_size"] for r in rows if r["largest_scc_size"] is not None])
            )
            if rows
            else None,
            "mean_largest_scc_after_mutual_deletion": float(
                np.mean(
                    [
                        r["largest_scc_after_mutual_deletion"]
                        for r in rows
                        if r["largest_scc_after_mutual_deletion"] is not None
                    ]
                )
            )
            if rows
            else None,
            "mean_normalized_fas_weight_removed": float(
                np.mean([r["normalized_fas_weight_removed"] for r in rows])
            )
            if rows
            else None,
        }
        for ranker in RANKERS:
            rrows = ranker_by_cell.get((dataset, protocol, regime, ranker), [])
            total_eligible = sum(r["n_eligible_pairs"] for r in rrows)
            total_retained = sum(r["n_retained_votes"] for r in rrows)
            cell[f"{ranker}_retained_vote_rate_of_eligible"] = (
                (total_retained / total_eligible) if total_eligible else None
            )
        bm25_conditional_shares = [
            r["ranker_weight_summary"].get("bm25_share_conditional")
            for r in rows
            if r.get("ranker_weight_summary", {}).get("bm25_share_conditional") is not None
        ]
        cell["bm25_conditional_weight_share_mean"] = (
            float(np.mean(bm25_conditional_shares)) if bm25_conditional_shares else None
        )
        diag_rows.append(cell)
    write_csv(TABLES_DIR / "independent_protocol_diagnostics_summary.csv", diag_rows)

    # Cell-level statistics (bootstrap CI, paired permutation) per
    # dataset/protocol/regime/pair, matching the schema style of the
    # existing full_calibrated_core tables.
    stats_rows: list[dict[str, Any]] = []
    by_cell: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    for row in all_paired_rows:
        key = (row["dataset"], row["protocol"], row["regime"], row["pair_name"])
        by_cell[key].append(row["delta_ndcg"])
    for (dataset, protocol, regime, pair_name), deltas in sorted(by_cell.items()):
        lo, hi, frac_gt_zero = bootstrap_ci(deltas)
        pval = paired_permutation_pvalue(deltas)
        arr = np.asarray(deltas, dtype=float)
        stats_rows.append(
            {
                "dataset": dataset,
                "protocol": protocol,
                "protocol_label": PROTOCOL_SPECS[protocol]["label"],
                "protocol_kind": PROTOCOL_SPECS[protocol]["kind"],
                "regime": regime,
                "pair_name": pair_name,
                "n_queries": len(deltas),
                "mean_delta_ndcg": float(arr.mean()) if len(arr) else None,
                "median_delta_ndcg": float(np.median(arr)) if len(arr) else None,
                "bootstrap_ci_low": lo,
                "bootstrap_ci_high": hi,
                "bootstrap_fraction_means_gt_zero": frac_gt_zero,
                "paired_permutation_pvalue": pval,
                "helped_query_count": int(np.sum(arr > 1e-12)),
                "harmed_query_count": int(np.sum(arr < -1e-12)),
                "unchanged_query_count": int(np.sum(np.abs(arr) <= 1e-12)),
            }
        )
    write_csv(TABLES_DIR / "independent_protocol_statistics.csv", stats_rows)

    summary = {
        "generated_at": now_iso(),
        "datasets": datasets,
        "protocols": protocols,
        "n_paired_rows": len(all_paired_rows),
        "n_structural_rows": len(all_structural_rows),
        "n_stats_cells": len(stats_rows),
        "elapsed_seconds": time.time() - t0,
        "repo": repo,
    }
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(MANIFESTS_DIR / "run_independent_protocols_summary.json", summary)
    summary_preview = json.dumps(summary, default=str)[:400]
    print(
        f"[{now_iso()}] Done in {summary['elapsed_seconds']:.1f}s. Summary: {summary_preview}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
