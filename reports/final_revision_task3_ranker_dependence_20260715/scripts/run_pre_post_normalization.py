#!/usr/bin/env python3
"""JDIQ Task 3, section 6: pre-pool vs post-pool min-max normalization.

post_pool_minmax -- the manuscript's existing behavior: candidate-pool
    restriction happens first, then min-max normalization is computed only
    over the scores of documents retained in that query's candidate pool
    (full_calibration_utils.apply_calibration_to_score_maps).

pre_pool_minmax -- normalization is computed over each ranker's FULL stored
    top-n score list for that query (not the candidate pool), and the
    resulting normalized values are then restricted to the candidate pool.
    Qrels play no role. A document in the candidate pool that a given
    ranker never stored a score for remains missing under both
    constructions (missingness is preserved, not imputed).

Per-ranker stored depths differ (SciDocs/FiQA/BRIGHT top-50, HotpotQA
top-35, per Task 1's verified common complete depths); pre_pool_minmax's
normalization domain for a given (query, ranker) is exactly that ranker's
full stored score list for that query, whatever its length -- i.e. each
ranker is normalized against its own native stored candidate set, not a
shared cross-ranker set.

Threshold-policy choice (declared BEFORE inspecting any retrieval result,
per the task's fairness requirement): reusing one construction's
retention-matched thresholds in the other would bias the comparison
(different score distributions -> different quantile-derived margins).
Both constructions therefore use the SAME independently-defined policy:
per-ranker vote-margin threshold = the median (q=0.5) of that
construction's own pooled pairwise-margin distribution for the given
dataset/regime/pool/construction cell (mirroring the manuscript's existing
pre-registered "independent_minmax_quantile_q0p5" protocol), with no
additional aggregate-weight cut beyond each regime's min_support.
"""

# ruff: noqa: I001 -- import order below is semantically constrained (see comment)
from __future__ import annotations

import json
import time
from collections import defaultdict
from typing import Any

import networkx as nx
import numpy as np

# task3_common must import first: it puts full_calibration_utils's and
# run_pool_cutoff_study's directories on sys.path (see its sys.path bootstrap).
import task3_common as t3
import full_calibration_utils as fcu  # noqa: E402
from consistency_ranker import statistical_inference as stats_inf  # noqa: E402

import run_pool_cutoff_study as t1_study  # noqa: E402  (for _load_score_lists)
import run_leave_one_out as loo  # noqa: E402  (reuse repair/prior/metric helpers)

CONSTRUCTIONS = ("post_pool_minmax", "pre_pool_minmax")
QUANTILE = 0.5
METRIC_CUTOFF_BY_POOL_LABEL = {"canonical": None, "task1_larger": 10}
ACTIVE_REGIME = "ms1"
PAIR_METHODS = ("copeland", "balance")


def _calibrated_scores_for_construction(
    *,
    construction: str,
    raw_scores_by_ranker: dict[str, dict[str, float]],
    full_score_lists_by_ranker: dict[str, dict[str, list[tuple[str, float]]]],
    query_id: str,
    candidate_pool: list[str],
) -> dict[str, dict[str, float]]:
    calibrated: dict[str, dict[str, float]] = {}
    for ranker in t3.RANKERS:
        if construction == "post_pool_minmax":
            score_map = raw_scores_by_ranker.get(ranker, {})
            restricted = {d: score_map[d] for d in candidate_pool if d in score_map}
            calibrated[ranker], _meta = fcu.calibrate_query_ranker_scores(
                restricted, calibration="minmax_query_ranker"
            )
        elif construction == "pre_pool_minmax":
            full_list = full_score_lists_by_ranker.get(ranker, {}).get(query_id, [])
            full_map = dict(full_list)
            normalized_full, _meta = fcu.calibrate_query_ranker_scores(
                full_map, calibration="minmax_query_ranker"
            )
            calibrated[ranker] = {
                d: normalized_full[d] for d in candidate_pool if d in normalized_full
            }
        else:
            raise ValueError(construction)
    return calibrated


def _direction_maps_for_calibrated(
    *,
    raw_scores_by_ranker: dict[str, dict[str, float]],
    calibrated_scores: dict[str, dict[str, float]],
    candidate_pool: list[str],
    vote_thresholds: dict[str, float],
) -> dict[tuple[str, str], dict[tuple[str, str], list[tuple[str, float]]]]:
    direction_maps: dict[tuple[str, str], dict[tuple[str, str], list[tuple[str, float]]]] = (
        defaultdict(lambda: defaultdict(list))
    )
    for ranker in t3.RANKERS:
        direction_map, margin_map = fcu._direction_and_margin_maps(
            ranker,
            raw_scores_by_ranker=raw_scores_by_ranker,
            calibrated_scores=calibrated_scores,
            candidate_pool=candidate_pool,
            calibration="minmax_query_ranker",
        )
        threshold = float(vote_thresholds.get(ranker, 0.0))
        for a, b in t3.unordered_pairs(candidate_pool):
            if a not in direction_map or b not in direction_map:
                continue
            da, db = direction_map[a], direction_map[b]
            if da == db:
                continue
            margin = abs(float(margin_map[a]) - float(margin_map[b]))
            if margin < threshold:
                continue
            winner, loser = (a, b) if da > db else (b, a)
            pair_key = (a, b) if a < b else (b, a)
            direction_maps[pair_key][(winner, loser)].append((ranker, float(margin)))
    return direction_maps


def _pooled_margins(
    *,
    dataset_inputs: dict[str, Any],
    construction: str,
    full_score_lists_by_ranker: dict[str, dict[str, list[tuple[str, float]]]],
) -> dict[str, list[float]]:
    margins: dict[str, list[float]] = {r: [] for r in t3.RANKERS}
    for item in dataset_inputs["per_query_inputs"]:
        pool = item["candidate_pool"]
        calibrated = _calibrated_scores_for_construction(
            construction=construction,
            raw_scores_by_ranker=item["raw_scores_by_ranker"],
            full_score_lists_by_ranker=full_score_lists_by_ranker,
            query_id=item["query_id"],
            candidate_pool=pool,
        )
        for ranker in t3.RANKERS:
            direction_map, margin_map = fcu._direction_and_margin_maps(
                ranker,
                raw_scores_by_ranker=item["raw_scores_by_ranker"],
                calibrated_scores=calibrated,
                candidate_pool=pool,
                calibration="minmax_query_ranker",
            )
            for a, b in t3.unordered_pairs(pool):
                if a not in direction_map or b not in direction_map:
                    continue
                if direction_map[a] == direction_map[b]:
                    continue
                margins[ranker].append(abs(float(margin_map[a]) - float(margin_map[b])))
    return margins


def run_dataset_pool(dataset: str, pool_label: str, pool_size: int) -> list[dict[str, Any]]:
    dataset_inputs = t3.dataset_inputs_for_pool(dataset, pool_size)
    full_score_lists_by_ranker = t1_study._load_score_lists(dataset)[2]
    metric_cutoff = (
        pool_size
        if METRIC_CUTOFF_BY_POOL_LABEL[pool_label] is None
        else METRIC_CUTOFF_BY_POOL_LABEL[pool_label]
    )
    evaluator = fcu.CalibrationEvaluator()

    records: list[dict[str, Any]] = []
    for construction in CONSTRUCTIONS:
        pooled_margins = _pooled_margins(
            dataset_inputs=dataset_inputs,
            construction=construction,
            full_score_lists_by_ranker=full_score_lists_by_ranker,
        )
        vote_thresholds = {
            r: float(np.quantile(np.asarray(pooled_margins[r], dtype=float), QUANTILE))
            if pooled_margins[r]
            else 0.0
            for r in t3.RANKERS
        }
        for regime in t3.REGIMES:
            min_support, _default_agg, drop_mutual = fcu.base_variant_parameters(regime)
            for item in dataset_inputs["per_query_inputs"]:
                qid = item["query_id"]
                pool = item["candidate_pool"]
                raw_scores = item["raw_scores_by_ranker"]
                calibrated = _calibrated_scores_for_construction(
                    construction=construction,
                    raw_scores_by_ranker=raw_scores,
                    full_score_lists_by_ranker=full_score_lists_by_ranker,
                    query_id=qid,
                    candidate_pool=pool,
                )
                direction_maps = _direction_maps_for_calibrated(
                    raw_scores_by_ranker=raw_scores,
                    calibrated_scores=calibrated,
                    candidate_pool=pool,
                    vote_thresholds=vote_thresholds,
                )
                rows = fcu._vote_rows_from_direction_maps(
                    qid,
                    direction_maps,
                    min_support=min_support,
                    aggregate_threshold=0.0,
                    drop_mutual=drop_mutual,
                )
                prefs = [
                    fcu.Preference(
                        winner=str(r["winner_doc_id"]),
                        loser=str(r["loser_doc_id"]),
                        weight=float(r["weight"]),
                    )
                    for r in rows
                ]
                graph = fcu.build_graph(prefs)
                graph.add_nodes_from(pool)
                if graph.number_of_nodes() < 2:
                    continue

                qrels_for_query = item["qrels_for_query"]
                _ref_ranking, rel_map = loo._reference_ranking_for_candidates(qrels_for_query, pool)
                score_prior_sets = [
                    {qid: list(raw_scores[r].items())} for r in t3.RANKERS if raw_scores.get(r)
                ]
                prior_scores = loo._rrf_prior_scores_for_query(
                    query_id=qid,
                    candidate_nodes=set(pool),
                    score_prior_sets=score_prior_sets,
                    fallback_scores=loo._score_sum_prior_scores(graph),
                )
                repaired_graph, repair_info = evaluator._apply_repair(
                    graph, prior_scores, top_k=metric_cutoff
                )
                repaired_graph.add_nodes_from(pool)

                mutual_pairs = sum(1 for u, v in graph.edges() if graph.has_edge(v, u) and u < v)
                sccs = list(nx.strongly_connected_components(graph))
                largest_scc = max((len(c) for c in sccs), default=0)
                removed_edges = {(u, v) for u, v in graph.edges()} - {
                    (u, v) for u, v in repaired_graph.edges()
                }

                rec: dict[str, Any] = {
                    "dataset": dataset,
                    "pool_label": pool_label,
                    "pool_size": pool_size,
                    "metric_cutoff": metric_cutoff,
                    "construction": construction,
                    "regime": regime,
                    "query_id": qid,
                    "n_edges": graph.number_of_edges(),
                    "density": nx.density(graph) if graph.number_of_nodes() > 1 else 0.0,
                    "mutual_pair_count": mutual_pairs,
                    "is_cyclic": largest_scc > 1,
                    "n_edges_removed": int(repair_info.get("n_edges_removed", 0)),
                    "removed_weight": float(repair_info.get("removed_weight", 0.0)),
                    "removed_edges": sorted(removed_edges),
                }
                for method_name in PAIR_METHODS:
                    raw_ranking = (
                        fcu.copeland_ranking(graph)
                        if method_name == "copeland"
                        else fcu.weighted_out_minus_in_ranking(graph)
                    )
                    rep_ranking = (
                        fcu.copeland_ranking(repaired_graph)
                        if method_name == "copeland"
                        else fcu.weighted_out_minus_in_ranking(repaired_graph)
                    )
                    raw_aligned = fcu._align_ranking(raw_ranking, rel_map)
                    rep_aligned = fcu._align_ranking(rep_ranking, rel_map)
                    rec[f"{method_name}_ndcg_unrepaired"] = fcu._ndcg_at_k(
                        raw_aligned, rel_map, k=metric_cutoff
                    )
                    rec[f"{method_name}_ndcg_repaired"] = fcu._ndcg_at_k(
                        rep_aligned, rel_map, k=metric_cutoff
                    )
                    rec[f"{method_name}_ndcg_delta"] = (
                        rec[f"{method_name}_ndcg_repaired"] - rec[f"{method_name}_ndcg_unrepaired"]
                    )
                    rec[f"{method_name}_ranking_unrepaired"] = raw_ranking
                    rec[f"{method_name}_ranking_repaired"] = rep_ranking
                records.append(rec)
    return records


def main() -> int:
    t0 = time.time()
    all_records: list[dict[str, Any]] = []
    for dataset in t3.DATASETS:
        for pool_label, pool_map in t3.POOLS.items():
            pool_size = pool_map[dataset]
            print(f"[pre/post norm] {dataset} {pool_label} P={pool_size}", flush=True)
            all_records.extend(run_dataset_pool(dataset, pool_label, pool_size))

    # per-query CSV (drop bulky ranking lists for the flat table; keep in JSON)
    flat_rows = [
        {
            k: v
            for k, v in r.items()
            if k
            not in (
                "removed_edges",
                "copeland_ranking_unrepaired",
                "copeland_ranking_repaired",
                "balance_ranking_unrepaired",
                "balance_ranking_repaired",
            )
        }
        for r in all_records
    ]
    t3.write_csv(t3.TABLES_DIR / "pre_post_normalization_per_query.csv", flat_rows)
    t3.write_json(t3.OUTPUTS_DIR / "pre_post_normalization_full_records.json", all_records)

    # structural comparison table
    struct_rows = []
    by_key = defaultdict(list)
    for r in all_records:
        by_key[(r["dataset"], r["pool_label"], r["construction"], r["regime"])].append(r)
    for (dataset, pool_label, construction, regime), rs in sorted(by_key.items()):
        struct_rows.append(
            {
                "dataset": dataset,
                "pool_label": pool_label,
                "construction": construction,
                "regime": regime,
                "n_queries": len(rs),
                "mean_edges": float(np.mean([r["n_edges"] for r in rs])),
                "mean_density": float(np.mean([r["density"] for r in rs])),
                "mean_mutual_pairs": float(np.mean([r["mutual_pair_count"] for r in rs])),
                "cyclic_query_pct": float(np.mean([r["is_cyclic"] for r in rs])),
                "mean_edges_removed": float(np.mean([r["n_edges_removed"] for r in rs])),
            }
        )
    t3.write_csv(t3.TABLES_DIR / "pre_post_normalization_structural_summary.csv", struct_rows)

    # removed-edge overlap between constructions (same dataset/pool/regime/query)
    overlap_rows = []
    by_query = defaultdict(dict)
    for r in all_records:
        key = (r["dataset"], r["pool_label"], r["regime"], r["query_id"])
        by_query[key][r["construction"]] = set(tuple(e) for e in r["removed_edges"])
    for key, cons_map in sorted(by_query.items()):
        if set(CONSTRUCTIONS) - set(cons_map):
            continue
        a, b = cons_map["post_pool_minmax"], cons_map["pre_pool_minmax"]
        jac = fcu.jaccard(a, b)
        dataset, pool_label, regime, qid = key
        overlap_rows.append(
            {
                "dataset": dataset,
                "pool_label": pool_label,
                "regime": regime,
                "query_id": qid,
                "post_pool_removed_count": len(a),
                "pre_pool_removed_count": len(b),
                "removed_edge_jaccard": jac,
            }
        )
    t3.write_csv(t3.TABLES_DIR / "pre_post_normalization_removed_edge_overlap.csv", overlap_rows)

    # retrieval / Holm family (pre-specified: ms1 regime only, both constructions, 2 pair methods)
    retrieval_rows = []
    stat_rows = []
    active_pvalues = []
    by_key2 = defaultdict(list)
    for r in all_records:
        for method in PAIR_METHODS:
            by_key2[(r["dataset"], r["pool_label"], r["construction"], r["regime"], method)].append(
                r[f"{method}_ndcg_delta"]
            )
    for key, deltas in sorted(by_key2.items()):
        dataset, pool_label, construction, regime, method = key
        n = len(deltas)
        helped = sum(1 for d in deltas if d > 1e-12)
        harmed = sum(1 for d in deltas if d < -1e-12)
        retrieval_rows.append(
            {
                "dataset": dataset,
                "pool_label": pool_label,
                "construction": construction,
                "regime": regime,
                "pair_method": method,
                "n_queries": n,
                "mean_delta": float(np.mean(deltas)) if deltas else None,
                "helped_query_count": helped,
                "harmed_query_count": harmed,
                "unchanged_query_count": n - helped - harmed,
            }
        )
        sf = stats_inf.sign_flip_pvalue(deltas)
        stat_rows.append(
            {
                "dataset": dataset,
                "pool_label": pool_label,
                "construction": construction,
                "regime": regime,
                "pair_method": method,
                "n_queries": n,
                "mean_delta": float(np.mean(deltas)) if deltas else None,
                "raw_pvalue": sf.pvalue,
            }
        )
        if regime == ACTIVE_REGIME:
            active_pvalues.append((key, sf.pvalue))
    t3.write_csv(t3.TABLES_DIR / "pre_post_normalization_retrieval_summary.csv", retrieval_rows)
    t3.write_csv(t3.TABLES_DIR / "pre_post_normalization_retrieval_statistics.csv", stat_rows)

    keys, pvals = zip(*active_pvalues) if active_pvalues else ((), ())
    holm = stats_inf.holm_adjust(list(pvals))
    active_rows = []
    for (key, raw_p), holm_p in zip(active_pvalues, holm):
        dataset, pool_label, construction, regime, method = key
        active_rows.append(
            {
                "dataset": dataset,
                "pool_label": pool_label,
                "construction": construction,
                "regime": regime,
                "pair_method": method,
                "raw_pvalue": raw_p,
                "holm_adjusted_pvalue": holm_p,
                "holm_significant_at_0.05": bool(holm_p is not None and holm_p < 0.05),
            }
        )
    t3.write_csv(t3.TABLES_DIR / "pre_post_normalization_active_family_holm.csv", active_rows)

    manifest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "constructions": list(CONSTRUCTIONS),
        "quantile_threshold_policy": (
            f"independently defined per-construction q={QUANTILE} (median) of that "
            "construction's own pooled pairwise-margin distribution; no "
            "aggregate-weight cut beyond min_support"
        ),
        "active_family_definition": (
            "ms1 regime only x 4 datasets x 2 pool labels x 2 constructions x "
            "2 pair methods = 32 cells, Holm-corrected jointly"
        ),
        "active_family_size": len(active_rows),
        "metric_cutoff_policy": (
            "canonical pool: metric_cutoff=pool_size (P=k); task1_larger: metric_cutoff=10"
        ),
        "elapsed_seconds": time.time() - t0,
        "n_records": len(all_records),
    }
    t3.write_json(t3.MANIFESTS_DIR / "pre_post_normalization_run_summary.json", manifest)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
