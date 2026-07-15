#!/usr/bin/env python3
"""
run_exact_open_ilp_study.py
============================
Phase 4/5 driver for the exact open-source ILP repair investigation.

For every query in the canonical primary-protocol package
(`primary_minmax_retention_matched`, all four datasets, all three vote
regimes), this script:

  1. Rebuilds the exact same pre-repair preference graph the canonical
     pipeline built (same candidate pools, same calibration thresholds,
     same graph construction) via the unmodified `full_calibration_utils`
     module.
  2. Repairs it two ways:
       - "greedy": the canonical NetworkX cycle-peeling heuristic
         (`fc.CalibrationEvaluator`, unmodified).
       - "ilp_scip": the exact open-source SCIP ILP solver added for this
         investigation (`exact_ilp_scip.solve_ilp_scip`), via a thin
         subclass that overrides only the repair step.
  3. Records structural stats (edges/weight removed, post-repair
     acyclicity, pairwise inconsistency) and retrieval metrics
     (nDCG@k, MRR, MAP) for every repaired-graph-dependent method, for
     both repair back-ends.
  4. Writes per-query and aggregated paired-delta tables (ILP - greedy)
     with bootstrap CIs and permutation p-values, mirroring the existing
     `reports/additional_metrics_investigation` methodology.

Nothing here modifies `full_calibration_utils.py`, `mwfas_solver.py`, or any
canonical output under `reports/full_calibrated_core/`. All outputs go under
`reports/exact_open_source_ilp_repair_investigation/`.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
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
from consistency_ranker.evaluation import mrr as mrr_fn  # noqa: E402
from exact_ilp_scip import solve_ilp_scip  # noqa: E402

DATASETS = ("bright", "fiqa", "hotpotqa", "scidocs")
REGIMES = ("ms1", "ms1_drop_mutual", "ms2")
PROTOCOL_DIR = "primary_minmax_retention_matched"
PROTOCOL_KEY = "primary"

PAIR_METHODS = (
    ("copeland", "copeland_graph", "copeland_graph_repaired"),
    ("balance", "balance_graph", "balance_graph_repaired"),
    ("markov", "markov_graph", "markov_graph_repaired"),
    ("copeland_hybrid", "hybrid_unrepaired_copeland_a0p3_minmax", "hybrid_repaired_copeland_a0p3_minmax"),
    ("balance_hybrid", "hybrid_unrepaired_balance_a0p3_minmax", "hybrid_repaired_balance_a0p3_minmax"),
)
REPAIRED_ONLY_METHODS = ("topological_repaired", "priority_topological_repaired")
ILP_TIME_LIMIT_S = 300.0
ILP_MIP_GAP = 0.0


def _map_at_k(ranking: list[str], rel_map: dict[str, int], k: int) -> float:
    if not ranking:
        return 0.0
    k_eff = min(k, len(ranking))
    total_relevant = sum(1 for d in ranking if rel_map.get(d, 0) > 0)
    if total_relevant <= 0:
        return 0.0
    hit = 0
    ap = 0.0
    for i, d in enumerate(ranking[:k_eff], start=1):
        if rel_map.get(d, 0) > 0:
            hit += 1
            ap += hit / i
    denom = min(total_relevant, k_eff)
    return ap / denom if denom > 0 else 0.0


def _mrr_value(ranking: list[str], rel_map: dict[str, int]) -> float:
    relevant = {d for d, g in rel_map.items() if g > 0}
    return float(mrr_fn(ranking, relevant))


def _ndcg_value(ranking: list[str], rel_map: dict[str, int], k: int) -> float:
    from consistency_ranker.evaluation import ndcg_at_k

    return float(ndcg_at_k(ranking, rel_map, k=k))


class ScipIlpCalibrationEvaluator(fc.CalibrationEvaluator):
    """Identical to fc.CalibrationEvaluator except the repair step calls the
    open-source exact SCIP ILP solver instead of the canonical greedy
    heuristic. Every other part of the evaluation pipeline (candidate
    pools, calibration, graph construction, downstream ranking methods,
    metrics) is inherited unchanged."""

    def __init__(self) -> None:
        super().__init__()
        self.solver_records: list[dict[str, Any]] = []

    def _apply_repair(self, graph, prior_scores, *, top_k: int):
        dag, removed, status = solve_ilp_scip(
            graph, time_limit_s=ILP_TIME_LIMIT_S, mip_gap=ILP_MIP_GAP, quiet=True
        )
        self.solver_records.append(
            {
                "n_nodes": status.n_nodes,
                "n_vars": status.n_vars,
                "n_constraints": status.n_constraints,
                "status": status.status,
                "proven_optimal": status.proven_optimal,
                # True iff the graph was empty/single-node/already-acyclic and
                # SCIP was never invoked -- distinguishes trivially-skipped
                # (edgeless/acyclic) graphs from genuine solves, failures, or
                # timeouts (status.status != "optimal").
                "trivial": status.trivial,
                "gap": status.gap,
                "time_s": status.time_s,
                "objective": status.objective,
                "error": status.error,
            }
        )
        removed_weight = float(sum(w for _u, _v, w in removed))
        return dag, {
            "repair_applied": bool(removed),
            "mode": "ilp_scip",
            "removed_edges": [(u, v, float(w)) for u, v, w in removed],
            "removed_weight": removed_weight,
            "n_edges_removed": len(removed),
            "solver_status": status.status,
            "solver_proven_optimal": status.proven_optimal,
            "solver_trivial": status.trivial,
            "solver_gap": status.gap,
            "solver_time_s": status.time_s,
        }


def _bootstrap_ci(values: list[float], reps: int = 10_000, seed: int = 13) -> tuple[float, float, float]:
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return 0.0, 0.0, 0.0
    rng = np.random.default_rng(seed)
    samples = rng.choice(arr, size=(reps, arr.size), replace=True).mean(axis=1)
    lo, hi = np.quantile(samples, [0.025, 0.975])
    return float(lo), float(hi), float(np.mean(samples > 0.0))


def _perm_pvalue(values: list[float], reps: int = 10_000, seed: int = 17) -> float:
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return 1.0
    rng = np.random.default_rng(seed)
    observed = abs(float(arr.mean()))
    flips = rng.choice(np.array([-1.0, 1.0]), size=(reps, arr.size), replace=True)
    samples = np.abs((flips * arr).mean(axis=1))
    return float((np.sum(samples >= observed) + 1) / (reps + 1))


def _holm_bh(pvals: list[float]) -> tuple[list[float], list[float]]:
    m = len(pvals)
    order = np.argsort(pvals)
    holm = [0.0] * m
    bh = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order, start=1):
        running = max(running, min(1.0, (m - rank + 1) * pvals[idx]))
        holm[idx] = running
    prev = 1.0
    for rank, idx in enumerate(order[::-1], start=1):
        adj = min(prev, min(1.0, pvals[idx] * m / (m - rank + 1)))
        bh[idx] = adj
        prev = adj
    return holm, bh


def main() -> int:
    for sub in ("scripts", "logs", "tables", "figures", "outputs", "manifests"):
        (REPORT_ROOT / sub).mkdir(parents=True, exist_ok=True)

    t_start = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] Loading dataset inputs for {DATASETS} ...", flush=True)
    dataset_inputs = {ds: fc.prepare_dataset_inputs(ds) for ds in DATASETS}
    print(f"[{time.strftime('%H:%M:%S')}] Dataset inputs loaded.", flush=True)

    greedy_eval = fc.CalibrationEvaluator()
    ilp_eval = ScipIlpCalibrationEvaluator()

    per_query_rows: list[dict[str, Any]] = []
    structural_rows: list[dict[str, Any]] = []
    paired_metric_rows: list[dict[str, Any]] = []
    solver_status_rows: list[dict[str, Any]] = []
    greedy_records: list[dict[str, Any]] = []
    ilp_records: list[dict[str, Any]] = []

    n_queries_done = 0
    for dataset in DATASETS:
        ds_inputs = dataset_inputs[dataset]
        top_k = int(ds_inputs["spec"].top_k)
        available_cutoffs = [c for c in (5, 10, 20) if c <= top_k]
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
                    top_k=top_k,
                    candidate_pool=item["candidate_pool"],
                    vote_rows=artifacts["rows"],
                    raw_score_maps_by_ranker={rk: list(scores.items()) for rk, scores in item["raw_scores_by_ranker"].items()},
                )
                greedy_rec = greedy_eval.evaluate_query(**common_kwargs)
                ilp_rec = ilp_eval.evaluate_query(**common_kwargs)
                if greedy_rec is None or ilp_rec is None:
                    continue

                greedy_records.append(greedy_rec)
                ilp_records.append(ilp_rec)
                n_queries_done += 1

                solver_status_rows.append(
                    {
                        "dataset": dataset,
                        "regime": regime,
                        "query_id": qid,
                        **ilp_eval.solver_records[-1],
                    }
                )

                # --- structural comparison (greedy vs ilp_scip) ---
                structural_rows.append(
                    {
                        "dataset": dataset,
                        "regime": regime,
                        "query_id": qid,
                        "n_nodes": greedy_rec["graph"].number_of_nodes(),
                        "n_edges_pre_repair": greedy_rec["graph"].number_of_edges(),
                        "is_cyclic_pre_repair": bool(greedy_rec["graph_stats"].get("is_cyclic")),
                        "greedy_n_edges_removed": greedy_rec["repair_info"]["n_edges_removed"],
                        "greedy_weight_removed": greedy_rec["repair_info"]["removed_weight"],
                        "ilp_n_edges_removed": ilp_rec["repair_info"]["n_edges_removed"],
                        "ilp_weight_removed": ilp_rec["repair_info"]["removed_weight"],
                        "ilp_proven_optimal": ilp_rec["repair_info"]["solver_proven_optimal"],
                        "weight_removed_delta_ilp_minus_greedy": (
                            ilp_rec["repair_info"]["removed_weight"] - greedy_rec["repair_info"]["removed_weight"]
                        ),
                        "edges_removed_delta_ilp_minus_greedy": (
                            ilp_rec["repair_info"]["n_edges_removed"] - greedy_rec["repair_info"]["n_edges_removed"]
                        ),
                        "same_edges_removed_set": (
                            {(u, v) for u, v, _w in greedy_rec["repair_info"]["removed_edges"]}
                            == {(u, v) for u, v, _w in ilp_rec["repair_info"]["removed_edges"]}
                        ),
                        "repaired_is_dag_greedy": bool(greedy_rec["repaired_graph_stats"].get("is_dag")),
                        "repaired_is_dag_ilp": bool(ilp_rec["repaired_graph_stats"].get("is_dag")),
                        "bew_post_greedy": greedy_rec["graph_bew_post"],
                        "bew_post_ilp": ilp_rec["graph_bew_post"],
                        "pic_post_greedy": greedy_rec["graph_pic_post"],
                        "pic_post_ilp": ilp_rec["graph_pic_post"],
                    }
                )

                rel_map = greedy_rec["rel_map"]
                assert rel_map == ilp_rec["rel_map"]

                for pair_name, unrepaired_key, repaired_key in PAIR_METHODS:
                    g_out = greedy_rec["method_outputs"]
                    i_out = ilp_rec["method_outputs"]
                    if repaired_key not in g_out or repaired_key not in i_out:
                        continue
                    greedy_ranking = g_out[repaired_key]["ranking"]
                    ilp_ranking = i_out[repaired_key]["ranking"]
                    for cutoff in available_cutoffs:
                        if cutoff > len(greedy_ranking) or cutoff > len(ilp_ranking):
                            continue
                        g_ndcg = _ndcg_value(greedy_ranking, rel_map, cutoff)
                        i_ndcg = _ndcg_value(ilp_ranking, rel_map, cutoff)
                        paired_metric_rows.append(
                            {
                                "dataset": dataset, "regime": regime, "query_id": qid,
                                "pair_name": pair_name, "method_key": repaired_key,
                                "metric": f"nDCG@{cutoff}", "cutoff": cutoff,
                                "greedy": g_ndcg, "ilp_scip": i_ndcg, "delta": i_ndcg - g_ndcg,
                            }
                        )
                    g_mrr, i_mrr = _mrr_value(greedy_ranking, rel_map), _mrr_value(ilp_ranking, rel_map)
                    g_map = _map_at_k(greedy_ranking, rel_map, len(greedy_ranking))
                    i_map = _map_at_k(ilp_ranking, rel_map, len(ilp_ranking))
                    paired_metric_rows.append(
                        {"dataset": dataset, "regime": regime, "query_id": qid, "pair_name": pair_name,
                         "method_key": repaired_key, "metric": "MRR", "cutoff": "",
                         "greedy": g_mrr, "ilp_scip": i_mrr, "delta": i_mrr - g_mrr}
                    )
                    paired_metric_rows.append(
                        {"dataset": dataset, "regime": regime, "query_id": qid, "pair_name": pair_name,
                         "method_key": repaired_key, "metric": "MAP", "cutoff": "",
                         "greedy": g_map, "ilp_scip": i_map, "delta": i_map - g_map}
                    )

                for method_key in REPAIRED_ONLY_METHODS:
                    g_out = greedy_rec["method_outputs"]
                    i_out = ilp_rec["method_outputs"]
                    if method_key not in g_out or method_key not in i_out:
                        continue
                    greedy_ranking = g_out[method_key]["ranking"]
                    ilp_ranking = i_out[method_key]["ranking"]
                    for cutoff in available_cutoffs:
                        if cutoff > len(greedy_ranking) or cutoff > len(ilp_ranking):
                            continue
                        g_ndcg = _ndcg_value(greedy_ranking, rel_map, cutoff)
                        i_ndcg = _ndcg_value(ilp_ranking, rel_map, cutoff)
                        paired_metric_rows.append(
                            {"dataset": dataset, "regime": regime, "query_id": qid, "pair_name": method_key,
                             "method_key": method_key, "metric": f"nDCG@{cutoff}", "cutoff": cutoff,
                             "greedy": g_ndcg, "ilp_scip": i_ndcg, "delta": i_ndcg - g_ndcg}
                        )
                    g_mrr, i_mrr = _mrr_value(greedy_ranking, rel_map), _mrr_value(ilp_ranking, rel_map)
                    g_map = _map_at_k(greedy_ranking, rel_map, len(greedy_ranking))
                    i_map = _map_at_k(ilp_ranking, rel_map, len(ilp_ranking))
                    paired_metric_rows.append(
                        {"dataset": dataset, "regime": regime, "query_id": qid, "pair_name": method_key,
                         "method_key": method_key, "metric": "MRR", "cutoff": "",
                         "greedy": g_mrr, "ilp_scip": i_mrr, "delta": i_mrr - g_mrr}
                    )
                    paired_metric_rows.append(
                        {"dataset": dataset, "regime": regime, "query_id": qid, "pair_name": method_key,
                         "method_key": method_key, "metric": "MAP", "cutoff": "",
                         "greedy": g_map, "ilp_scip": i_map, "delta": i_map - g_map}
                    )

            print(
                f"[{time.strftime('%H:%M:%S')}] {dataset}/{regime}: done. "
                f"cumulative queries processed = {n_queries_done}",
                flush=True,
            )

    print(f"[{time.strftime('%H:%M:%S')}] All queries processed ({n_queries_done} total). Aggregating ...", flush=True)

    # ---- write per-query tables ----
    struct_df = pd.DataFrame(structural_rows)
    struct_df.to_csv(REPORT_ROOT / "tables" / "structural_per_query.csv", index=False)

    solver_df = pd.DataFrame(solver_status_rows)
    solver_df.to_csv(REPORT_ROOT / "tables" / "ilp_solver_status_per_query.csv", index=False)

    paired_df = pd.DataFrame(paired_metric_rows)
    paired_df.to_csv(REPORT_ROOT / "tables" / "retrieval_metric_paired_per_query.csv", index=False)

    # ---- structural summary using the canonical (unmodified) summarizer ----
    struct_summary_greedy = fc.summarize_structural_records(greedy_records)
    struct_summary_ilp = fc.summarize_structural_records(ilp_records)
    pd.DataFrame(
        [
            {"repair_method": "greedy", **struct_summary_greedy},
            {"repair_method": "ilp_scip", **struct_summary_ilp},
        ]
    ).to_csv(REPORT_ROOT / "tables" / "structural_summary_greedy_vs_ilp.csv", index=False)

    # per dataset/regime structural summaries too
    struct_summary_rows = []
    for (dataset, regime), _ in struct_df.groupby(["dataset", "regime"]):
        idxs = [
            i for i, (r) in enumerate(structural_rows)
            if r["dataset"] == dataset and r["regime"] == regime
        ]
        g_sub = [greedy_records[i] for i in idxs]
        i_sub = [ilp_records[i] for i in idxs]
        gs = fc.summarize_structural_records(g_sub)
        is_ = fc.summarize_structural_records(i_sub)
        struct_summary_rows.append({"dataset": dataset, "regime": regime, "repair_method": "greedy", **gs})
        struct_summary_rows.append({"dataset": dataset, "regime": regime, "repair_method": "ilp_scip", **is_})
    pd.DataFrame(struct_summary_rows).to_csv(
        REPORT_ROOT / "tables" / "structural_summary_by_dataset_regime.csv", index=False
    )

    # ---- paired-delta aggregation with bootstrap CI + permutation p-value ----
    agg_rows = []
    for (dataset, regime, pair_name, method_key, metric, cutoff), grp in paired_df.groupby(
        ["dataset", "regime", "pair_name", "method_key", "metric", "cutoff"], dropna=False
    ):
        deltas = grp["delta"].astype(float).to_list()
        arr = np.asarray(deltas)
        lo, hi, frac_gt_zero = _bootstrap_ci(deltas)
        pval = _perm_pvalue(deltas)
        agg_rows.append(
            {
                "dataset": dataset, "regime": regime, "pair_name": pair_name, "method_key": method_key,
                "metric": metric, "cutoff": cutoff, "n_queries": int(arr.size),
                "mean_greedy": float(grp["greedy"].astype(float).mean()),
                "mean_ilp_scip": float(grp["ilp_scip"].astype(float).mean()),
                "mean_delta": float(arr.mean()), "median_delta": float(np.median(arr)),
                "bootstrap_ci_low": lo, "bootstrap_ci_high": hi,
                "bootstrap_fraction_gt_zero": frac_gt_zero,
                "paired_permutation_pvalue": pval,
                "helped_query_count": int(np.sum(arr > 1e-12)),
                "harmed_query_count": int(np.sum(arr < -1e-12)),
                "unchanged_query_count": int(np.sum(np.abs(arr) <= 1e-12)),
            }
        )
    agg_df = pd.DataFrame(agg_rows)
    if not agg_df.empty:
        holm, bh = _holm_bh(agg_df["paired_permutation_pvalue"].astype(float).to_list())
        agg_df["holm_pvalue"] = holm
        agg_df["bh_pvalue"] = bh
    agg_df.to_csv(REPORT_ROOT / "tables" / "retrieval_metric_paired_summary.csv", index=False)

    # ---- also aggregate over primary protocol overall (all datasets/regimes pooled per metric/method) ----
    pooled_rows = []
    for (pair_name, method_key, metric, cutoff), grp in paired_df.groupby(
        ["pair_name", "method_key", "metric", "cutoff"], dropna=False
    ):
        deltas = grp["delta"].astype(float).to_list()
        arr = np.asarray(deltas)
        lo, hi, frac_gt_zero = _bootstrap_ci(deltas)
        pval = _perm_pvalue(deltas)
        pooled_rows.append(
            {
                "pair_name": pair_name, "method_key": method_key, "metric": metric, "cutoff": cutoff,
                "n_queries": int(arr.size),
                "mean_greedy": float(grp["greedy"].astype(float).mean()),
                "mean_ilp_scip": float(grp["ilp_scip"].astype(float).mean()),
                "mean_delta": float(arr.mean()), "median_delta": float(np.median(arr)),
                "bootstrap_ci_low": lo, "bootstrap_ci_high": hi,
                "bootstrap_fraction_gt_zero": frac_gt_zero,
                "paired_permutation_pvalue": pval,
                "helped_query_count": int(np.sum(arr > 1e-12)),
                "harmed_query_count": int(np.sum(arr < -1e-12)),
                "unchanged_query_count": int(np.sum(np.abs(arr) <= 1e-12)),
            }
        )
    pooled_df = pd.DataFrame(pooled_rows)
    if not pooled_df.empty:
        holm, bh = _holm_bh(pooled_df["paired_permutation_pvalue"].astype(float).to_list())
        pooled_df["holm_pvalue"] = holm
        pooled_df["bh_pvalue"] = bh
    pooled_df.to_csv(REPORT_ROOT / "tables" / "retrieval_metric_paired_summary_pooled.csv", index=False)

    # ---- rank-identity check: does ILP ever choose a different DAG than greedy? ----
    n_same_edge_set = int(struct_df["same_edges_removed_set"].sum()) if not struct_df.empty else 0
    n_total = len(struct_df)
    n_different_objective = int(
        (
            struct_df["ilp_weight_removed"] < struct_df["greedy_weight_removed"] - 1e-9
        ).sum()
    ) if not struct_df.empty else 0
    n_not_proven = int((~struct_df["ilp_proven_optimal"]).sum()) if not struct_df.empty else 0

    summary = {
        "n_queries_total": n_total,
        "n_queries_same_removed_edge_set": n_same_edge_set,
        "n_queries_different_removed_edge_set": n_total - n_same_edge_set,
        "n_queries_ilp_strictly_lower_weight_removed": n_different_objective,
        "n_queries_ilp_not_proven_optimal": n_not_proven,
        "elapsed_seconds": time.time() - t_start,
    }
    with (REPORT_ROOT / "manifests" / "study_summary.json").open("w") as fh:
        json.dump(summary, fh, indent=2)

    print(f"[{time.strftime('%H:%M:%S')}] Done. Summary: {json.dumps(summary)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
