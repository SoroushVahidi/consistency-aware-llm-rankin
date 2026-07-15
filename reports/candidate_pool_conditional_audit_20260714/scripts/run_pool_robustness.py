#!/usr/bin/env python3
"""
run_pool_robustness.py
=======================
Repeats the primary protocol's repaired-versus-unrepaired analysis
(minmax_query_ranker calibration, retention-matched thresholds -- the same
primary_minmax_retention_matched protocol used throughout the manuscript)
under five candidate-pool policies: the existing canonical RRF-fused pool,
plus four independently-defined alternatives (equal-depth union, neutral
round-robin union, BM25-only, CombSUM-fused union; see
candidate_pool_policies.py). The canonical pool is recomputed fresh here
(not read back from reports/full_calibrated_core/outputs/.../protocol_runs/)
so every pool policy is evaluated identically in the same process, and nothing
under protocol_runs/ is ever written to -- "the original pool must remain
available" is satisfied by construction, not by special-casing.

Writes:
  - per-query JSONL + manifest.json (including the actual candidate_pool
    doc-id list per query, which the canonical pipeline does not persist)
    under reports/full_calibrated_core/outputs/calibrated_all4/pool_runs/
    {pool_id}/{dataset}/{regime}/
  - cell-level diagnostic/overlap/statistics CSVs under
    reports/candidate_pool_conditional_audit_20260714/tables/

Usage:
    python run_pool_robustness.py [--datasets a,b] [--pools x,y]
"""

from __future__ import annotations

import argparse
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

from candidate_pool_policies import POOL_SPECS  # noqa: E402
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
    REGIMES,
    _analysis_dataset_inputs,
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

POOL_OUTPUT_ROOT = (
    REPO_ROOT / "reports" / "full_calibrated_core" / "outputs" / "calibrated_all4" / "pool_runs"
)
CANONICAL_POOL_ID = "rrf_union_topk"
ALL_POOL_IDS = list(POOL_SPECS.keys())
PRIMARY_SPEC_CFG = PROTOCOL_SPECS[PRIMARY_PROTOCOL]


def _pool_dir(pool_id: str, dataset: str, regime: str) -> Path:
    return POOL_OUTPUT_ROOT / pool_id / dataset / regime


def _pairwise_agreement_rate(
    ranking_a: list[str], ranking_b: list[str], common_docs: set[str]
) -> float | None:
    """Fraction of concordant pairwise orderings among ``common_docs`` between
    two full rankings (a Kendall-tau agreement rate, not the -1..1 statistic).
    None if fewer than two common documents."""
    if len(common_docs) < 2:
        return None
    order_a = [d for d in ranking_a if d in common_docs]
    order_b = [d for d in ranking_b if d in common_docs]
    pos_a = {d: i for i, d in enumerate(order_a)}
    pos_b = {d: i for i, d in enumerate(order_b)}
    concordant = 0
    total = 0
    for x, y in combinations(sorted(common_docs), 2):
        total += 1
        sign_a = pos_a[x] < pos_a[y]
        sign_b = pos_b[x] < pos_b[y]
        if sign_a == sign_b:
            concordant += 1
    return concordant / total if total else None


def run_one_pool_cell(
    *,
    evaluator: CalibrationEvaluator,
    dataset: str,
    pool_id: str,
    regime: str,
    repo: dict[str, Any],
    dataset_score_hashes: dict[str, str],
) -> dict[str, Any]:
    pool_spec = POOL_SPECS[pool_id]
    dataset_inputs = _analysis_dataset_inputs(dataset, pool_policy=pool_spec)
    spec = dataset_inputs["spec"]
    baseline = raw_baseline_statistics(dataset_inputs)
    pair_margins, zero_variance = _pair_margin_summary(
        dataset_inputs, PRIMARY_SPEC_CFG["calibration"]
    )
    threshold_config = choose_threshold_config(
        dataset=dataset,
        regime=regime,
        calibration=PRIMARY_SPEC_CFG["calibration"],
        threshold_mode=PRIMARY_SPEC_CFG["threshold_mode"],
        baseline_vote_rates=baseline[regime]["vote_rates"],
        baseline_edge_count=baseline[regime]["edge_count"],
        calibration_pair_margins=pair_margins,
        per_query_inputs=dataset_inputs["per_query_inputs"],
    )

    out_dir = _pool_dir(pool_id, dataset, regime)
    out_dir.mkdir(parents=True, exist_ok=True)

    query_records: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    paired_rows: list[dict[str, Any]] = []
    structural_rows: list[dict[str, Any]] = []
    exclusion_rows: list[dict[str, Any]] = []
    valid_query_ids: list[str] = []
    per_query_state: dict[str, dict[str, Any]] = {}

    for item in dataset_inputs["per_query_inputs"]:
        query_id = item["query_id"]
        artifacts = build_query_vote_artifacts(
            query_id=query_id,
            raw_scores_by_ranker=item["raw_scores_by_ranker"],
            candidate_pool=item["candidate_pool"],
            calibration=PRIMARY_SPEC_CFG["calibration"],
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
                    "pool_id": pool_id,
                    "regime": regime,
                    "exclusion_reason": "no_valid_graph_output",
                }
            )
            continue

        edge_support = _support_map_from_rows(artifacts["rows"])
        record = _serializable_query_record(
            dataset=dataset,
            protocol=PRIMARY_PROTOCOL,
            regime=regime,
            query_id=query_id,
            artifacts=artifacts,
            threshold_config=threshold_config,
            eval_record=eval_record,
            edge_support=edge_support,
            extra_methods={},
        )
        record["pool_id"] = pool_id
        record["candidate_pool"] = list(item["candidate_pool"])
        query_records.append(record)
        valid_query_ids.append(query_id)

        # In-memory only (not persisted to JSONL, to avoid ballooning file
        # size with full rankings): kept for this cell's overlap diagnostics
        # against the canonical pool computed in the same run.
        per_query_state[query_id] = {
            "candidate_pool": set(item["candidate_pool"]),
            "removed_edges": set(eval_record["removed_edges"]),
            "repaired_hybrid_ranking": eval_record["method_outputs"][
                "hybrid_repaired_copeland_a0p3_minmax"
            ]["ranking"],
        }

        for method_key in METHOD_KEYS:
            metric_rows.append(
                {
                    "dataset": dataset,
                    "pool_id": pool_id,
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
                    "pool_id": pool_id,
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
                "pool_id": pool_id,
                "regime": regime,
                "query_id": query_id,
                "candidate_count": len(item["candidate_pool"]),
                "n_nodes": gs.get("n_nodes"),
                "n_edges": gs.get("n_edges"),
                "graph_density": gs.get("graph_density"),
                "total_edge_weight": total_weight,
                "is_cyclic": gs.get("is_cyclic"),
                "n_mutual_pairs": gs.get("n_mutual_pairs"),
                "largest_scc_size": gs.get("largest_scc_size"),
                "n_sccs_gt1": _scc_count_gt1(graph),
                "mutual_pair_weight_share": _mutual_pair_weight_share(graph),
                "is_cyclic_after_mutual_deletion": mrs.get("is_cyclic"),
                "largest_scc_after_mutual_deletion": mrs.get("largest_scc_size"),
                "repaired_is_dag": rgs.get("is_dag"),
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
        "pool_id": pool_id,
        "pool_spec": pool_spec.to_dict(),
        "protocol": PRIMARY_PROTOCOL,
        "protocol_spec": PRIMARY_SPEC_CFG,
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
        "output_files": {
            "query_records": str(out_dir / "query_records.jsonl"),
            "query_method_metrics": str(out_dir / "query_method_metrics.csv"),
        },
    }
    _write_json(out_dir / "manifest.json", manifest)

    return {
        "n_queries": len(valid_query_ids),
        "paired_rows": paired_rows,
        "structural_rows": structural_rows,
        "exclusion_rows": exclusion_rows,
        "per_query_state": per_query_state,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", default=",".join(DATASETS))
    parser.add_argument("--pools", default=",".join(ALL_POOL_IDS))
    args = parser.parse_args()
    datasets = args.datasets.split(",")
    pools = args.pools.split(",")
    for pool_id in pools:
        if pool_id not in POOL_SPECS:
            raise ValueError(f"Unknown pool {pool_id!r}; not in POOL_SPECS")
    if CANONICAL_POOL_ID not in pools:
        pools = [CANONICAL_POOL_ID] + pools

    t0 = time.time()
    repo = _repo_context()
    evaluator = CalibrationEvaluator()

    all_paired_rows: list[dict[str, Any]] = []
    all_structural_rows: list[dict[str, Any]] = []
    all_exclusion_rows: list[dict[str, Any]] = []
    pool_overlap_rows: list[dict[str, Any]] = []
    edge_overlap_rows: list[dict[str, Any]] = []
    ranking_overlap_rows: list[dict[str, Any]] = []

    for dataset in datasets:
        dataset_inputs_for_hashes = _analysis_dataset_inputs(dataset)
        spec = dataset_inputs_for_hashes["spec"]
        dataset_score_hashes = {ranker: sha256_file(spec.score_files[ranker]) for ranker in RANKERS}
        print(f"[{now_iso()}] dataset={dataset}", flush=True)

        for regime in REGIMES:
            cell_states: dict[str, dict[str, dict[str, Any]]] = {}
            for pool_id in pools:
                cell_t0 = time.time()
                result = run_one_pool_cell(
                    evaluator=evaluator,
                    dataset=dataset,
                    pool_id=pool_id,
                    regime=regime,
                    repo=repo,
                    dataset_score_hashes=dataset_score_hashes,
                )
                all_paired_rows.extend(result["paired_rows"])
                all_structural_rows.extend(result["structural_rows"])
                all_exclusion_rows.extend(result["exclusion_rows"])
                cell_states[pool_id] = result["per_query_state"]
                print(
                    f"[{now_iso()}] {dataset}/{pool_id}/{regime}: "
                    f"{result['n_queries']} queries in {time.time() - cell_t0:.1f}s",
                    flush=True,
                )

            canonical_state = cell_states.get(CANONICAL_POOL_ID, {})
            for pool_id in pools:
                if pool_id == CANONICAL_POOL_ID:
                    continue
                alt_state = cell_states[pool_id]
                common_qids = sorted(set(canonical_state) & set(alt_state))
                pool_jaccards = []
                edge_jaccards = []
                ranking_agreements = []
                for qid in common_qids:
                    canon = canonical_state[qid]
                    alt = alt_state[qid]
                    pj = jaccard(canon["candidate_pool"], alt["candidate_pool"])
                    if pj is not None:
                        pool_jaccards.append(pj)
                    ej = jaccard(canon["removed_edges"], alt["removed_edges"])
                    if ej is not None:
                        edge_jaccards.append(ej)
                    common_docs = canon["candidate_pool"] & alt["candidate_pool"]
                    agreement = _pairwise_agreement_rate(
                        canon["repaired_hybrid_ranking"],
                        alt["repaired_hybrid_ranking"],
                        common_docs,
                    )
                    if agreement is not None:
                        ranking_agreements.append(agreement)

                pool_overlap_rows.append(
                    {
                        "dataset": dataset,
                        "regime": regime,
                        "pool_id": pool_id,
                        "compared_against": CANONICAL_POOL_ID,
                        "n_common_queries": len(common_qids),
                        "mean_pool_jaccard": float(np.mean(pool_jaccards))
                        if pool_jaccards
                        else None,
                        "median_pool_jaccard": float(np.median(pool_jaccards))
                        if pool_jaccards
                        else None,
                    }
                )
                edge_overlap_rows.append(
                    {
                        "dataset": dataset,
                        "regime": regime,
                        "pool_id": pool_id,
                        "compared_against": CANONICAL_POOL_ID,
                        "n_common_queries": len(common_qids),
                        "mean_removed_edge_jaccard": float(np.mean(edge_jaccards))
                        if edge_jaccards
                        else None,
                        "median_removed_edge_jaccard": float(np.median(edge_jaccards))
                        if edge_jaccards
                        else None,
                    }
                )
                ranking_overlap_rows.append(
                    {
                        "dataset": dataset,
                        "regime": regime,
                        "pool_id": pool_id,
                        "compared_against": CANONICAL_POOL_ID,
                        "n_common_queries_with_2plus_shared_docs": len(ranking_agreements),
                        "mean_pairwise_rank_agreement": float(np.mean(ranking_agreements))
                        if ranking_agreements
                        else None,
                        "median_pairwise_rank_agreement": float(np.median(ranking_agreements))
                        if ranking_agreements
                        else None,
                    }
                )

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(TABLES_DIR / "pool_robustness_paired_deltas.csv", all_paired_rows)
    write_csv(TABLES_DIR / "pool_robustness_structural_per_query.csv", all_structural_rows)
    write_csv(TABLES_DIR / "pool_robustness_exclusions.csv", all_exclusion_rows)
    write_csv(TABLES_DIR / "pool_overlap_vs_canonical.csv", pool_overlap_rows)
    write_csv(TABLES_DIR / "pool_removed_edge_overlap_vs_canonical.csv", edge_overlap_rows)
    write_csv(TABLES_DIR / "pool_repaired_ranking_overlap_vs_canonical.csv", ranking_overlap_rows)

    # Statistics per pool/dataset/regime/pair: bootstrap CI + paired permutation p-value.
    stats_rows: list[dict[str, Any]] = []
    by_cell: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    for row in all_paired_rows:
        key = (row["pool_id"], row["dataset"], row["regime"], row["pair_name"])
        by_cell[key].append(row["delta_ndcg"])
    for (pool_id, dataset, regime, pair_name), values in sorted(by_cell.items()):
        ci_low, ci_high, frac_gt0 = bootstrap_ci(values)
        pvalue = paired_permutation_pvalue(values)
        n = len(values)
        stats_rows.append(
            {
                "pool_id": pool_id,
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
    write_csv(TABLES_DIR / "pool_robustness_statistics.csv", stats_rows)

    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "generated_at": now_iso(),
        "datasets": datasets,
        "pools": pools,
        "n_paired_rows": len(all_paired_rows),
        "n_structural_rows": len(all_structural_rows),
        "n_exclusion_rows": len(all_exclusion_rows),
        "elapsed_seconds": time.time() - t0,
        "repo": repo,
    }
    _write_json(MANIFESTS_DIR / "run_pool_robustness_summary.json", summary)
    print(f"[{now_iso()}] Done in {summary['elapsed_seconds']:.1f}s.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
