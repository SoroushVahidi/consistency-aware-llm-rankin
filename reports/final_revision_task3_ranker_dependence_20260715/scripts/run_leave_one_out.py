#!/usr/bin/env python3
"""JDIQ Task 3, section 5: leave-one-ranker-out graph/retrieval analysis.

Builds four vote-source variants that share the SAME candidate pool
(the canonical RRF-fused-over-all-three-rankers pool, held fixed so the
ablation isolates "which rankers may vote", not a re-selected candidate
set):

  pair_bm25_tfidf   -- only BM25 and TF-IDF may cast votes
  pair_bm25_minilm  -- only BM25 and MiniLM may cast votes
  pair_tfidf_minilm -- only TF-IDF and MiniLM may cast votes
  all_three         -- all three rankers (the manuscript's existing setup)

Vote-support semantics are named explicitly rather than reusing ms1/ms2,
because "support=2" means something different with 2 voters (unanimity)
than with 3 (majority):

  three-ranker regimes (support out of 3 voters): ms2, ms1, ms1_drop_mutual
  two-ranker regimes   (support out of 2 voters): pair_unanimous, pair_any,
                                                    pair_any_drop_mutual

All variants use minmax_query_ranker calibration with a FIXED numeric
vote-margin threshold of 0.05 (the manuscript's existing
"ablation_minmax_fixed" protocol value) rather than retention-matched
thresholds, so the comparison isolates which rankers vote rather than a
per-subset re-tuned threshold search.
"""

# ruff: noqa: I001 -- import order below is semantically constrained (see comment)
from __future__ import annotations

import json
import time
from collections import defaultdict
from typing import Any

import networkx as nx
import numpy as np

# task3_common must import before full_calibration_utils: it puts the
# latter's directory on sys.path (see task3_common's sys.path bootstrap).
import task3_common as t3
import full_calibration_utils as fcu  # noqa: E402
from consistency_ranker import statistical_inference as stats_inf  # noqa: E402

_align_ranking = fcu._align_ranking
_ndcg_at_k = fcu._ndcg_at_k
_reference_ranking_for_candidates = fcu._reference_ranking_for_candidates
_rrf_prior_scores_for_query = fcu._rrf_prior_scores_for_query
_score_sum_prior_scores = fcu._score_sum_prior_scores

FIXED_VOTE_THRESHOLD = 0.05

VARIANTS: dict[str, tuple[str, ...]] = {
    "all_three": ("bm25", "tfidf", "minilm"),
    "pair_bm25_tfidf": ("bm25", "tfidf"),
    "pair_bm25_minilm": ("bm25", "minilm"),
    "pair_tfidf_minilm": ("tfidf", "minilm"),
}
THREE_RANKER_REGIMES = {
    "ms2": (2, 0.1, False),
    "ms1": (1, 0.0, False),
    "ms1_drop_mutual": (1, 0.0, True),
}
TWO_RANKER_REGIMES = {
    "pair_unanimous": (2, 0.1, False),
    "pair_any": (1, 0.0, False),
    "pair_any_drop_mutual": (1, 0.0, True),
}
# The pre-specified "active" regime per variant kind (mirrors ms1 as the
# manuscript's scientifically active family; see Task 2 final report sec.10).
ACTIVE_REGIME_BY_VARIANT = {
    "all_three": "ms1",
    "pair_bm25_tfidf": "pair_any",
    "pair_bm25_minilm": "pair_any",
    "pair_tfidf_minilm": "pair_any",
}
METRIC_CUTOFF_BY_POOL_LABEL = {
    "canonical": None,
    "task1_larger": 10,
}  # canonical uses P=k (cutoff=pool size)

PAIR_METHODS = ("copeland", "balance")


def _regimes_for_variant(variant: str) -> dict[str, tuple[int, float, bool]]:
    return THREE_RANKER_REGIMES if len(VARIANTS[variant]) == 3 else TWO_RANKER_REGIMES


def build_vote_rows_subset(
    *,
    query_id: str,
    raw_scores_by_ranker: dict[str, dict[str, float]],
    candidate_pool: list[str],
    rankers_subset: tuple[str, ...],
    min_support: int,
    aggregate_threshold: float,
    drop_mutual: bool,
) -> list[dict[str, Any]]:
    """Same calibration/direction/margin/threshold/support/drop_mutual logic
    as full_calibration_utils.build_query_vote_artifacts, but iterating over
    an arbitrary ranker subset instead of the fixed module-level RANKERS
    tuple. Reuses the per-ranker helper functions directly so the vote
    semantics can never silently diverge from the canonical pipeline."""
    calibrated: dict[str, dict[str, float]] = {}
    for ranker in rankers_subset:
        score_map = raw_scores_by_ranker.get(ranker, {})
        restricted = {d: score_map[d] for d in candidate_pool if d in score_map}
        calibrated[ranker], _meta = fcu.calibrate_query_ranker_scores(
            restricted, calibration=t3.PRIMARY_CALIBRATION
        )

    direction_maps: dict[tuple[str, str], dict[tuple[str, str], list[tuple[str, float]]]] = (
        defaultdict(lambda: defaultdict(list))
    )
    for ranker in rankers_subset:
        direction_map, margin_map = fcu._direction_and_margin_maps(
            ranker,
            raw_scores_by_ranker=raw_scores_by_ranker,
            calibrated_scores=calibrated,
            candidate_pool=candidate_pool,
            calibration=t3.PRIMARY_CALIBRATION,
        )
        for a, b in t3.unordered_pairs(candidate_pool):
            if a not in direction_map or b not in direction_map:
                continue
            da, db = direction_map[a], direction_map[b]
            if da == db:
                continue
            margin = abs(float(margin_map[a]) - float(margin_map[b]))
            if margin < FIXED_VOTE_THRESHOLD:
                continue
            winner, loser = (a, b) if da > db else (b, a)
            pair_key = (a, b) if a < b else (b, a)
            direction_maps[pair_key][(winner, loser)].append((ranker, float(margin)))

    return fcu._vote_rows_from_direction_maps(
        query_id,
        direction_maps,
        min_support=min_support,
        aggregate_threshold=aggregate_threshold,
        drop_mutual=drop_mutual,
    )


def evaluate_variant_regime_query(
    *,
    dataset: str,
    query_id: str,
    item: dict[str, Any],
    rankers_subset: tuple[str, ...],
    min_support: int,
    aggregate_threshold: float,
    drop_mutual: bool,
    metric_cutoff: int,
    evaluator: "fcu.CalibrationEvaluator",
) -> dict[str, Any] | None:
    candidate_pool = item["candidate_pool"]
    raw_scores_by_ranker = item["raw_scores_by_ranker"]
    rows = build_vote_rows_subset(
        query_id=query_id,
        raw_scores_by_ranker=raw_scores_by_ranker,
        candidate_pool=candidate_pool,
        rankers_subset=rankers_subset,
        min_support=min_support,
        aggregate_threshold=aggregate_threshold,
        drop_mutual=drop_mutual,
    )
    prefs = [
        fcu.Preference(
            winner=str(r["winner_doc_id"]), loser=str(r["loser_doc_id"]), weight=float(r["weight"])
        )
        for r in rows
    ]
    graph = fcu.build_graph(prefs)
    graph.add_nodes_from(candidate_pool)
    if graph.number_of_nodes() < 2:
        return None

    qrels_for_query = item["qrels_for_query"]
    _ref_ranking, rel_map = _reference_ranking_for_candidates(qrels_for_query, candidate_pool)
    score_prior_sets = [
        {query_id: list(raw_scores_by_ranker[r].items())}
        for r in rankers_subset
        if raw_scores_by_ranker.get(r)
    ]
    prior_scores = _rrf_prior_scores_for_query(
        query_id=query_id,
        candidate_nodes=set(candidate_pool),
        score_prior_sets=score_prior_sets,
        fallback_scores=_score_sum_prior_scores(graph),
    )
    repaired_graph, repair_info = evaluator._apply_repair(graph, prior_scores, top_k=metric_cutoff)
    repaired_graph.add_nodes_from(candidate_pool)

    undirected = graph.to_undirected()
    n_triangles = int(sum(nx.triangles(undirected).values()) / 3)
    mutual_pairs = sum(1 for u, v in graph.edges() if graph.has_edge(v, u) and u < v)
    sccs = list(nx.strongly_connected_components(graph))
    largest_scc = max((len(c) for c in sccs), default=0)
    sccs_after = list(nx.strongly_connected_components(repaired_graph))
    largest_scc_after = max((len(c) for c in sccs_after), default=0)

    out: dict[str, Any] = {
        "dataset": dataset,
        "query_id": query_id,
        "n_nodes": graph.number_of_nodes(),
        "n_edges": graph.number_of_edges(),
        "density": nx.density(graph) if graph.number_of_nodes() > 1 else 0.0,
        "mutual_pair_count": mutual_pairs,
        "triangle_count": n_triangles,
        "is_cyclic": largest_scc > 1,
        "largest_scc": largest_scc,
        "is_cyclic_after_repair": largest_scc_after > 1,
        "largest_scc_after_repair": largest_scc_after,
        "n_edges_removed": int(repair_info.get("n_edges_removed", 0)),
        "removed_weight": float(repair_info.get("removed_weight", 0.0)),
        "repair_active": bool(repair_info.get("n_edges_removed", 0) > 0),
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
        raw_aligned = _align_ranking(raw_ranking, rel_map)
        rep_aligned = _align_ranking(rep_ranking, rel_map)
        out[f"{method_name}_ndcg_unrepaired"] = _ndcg_at_k(raw_aligned, rel_map, k=metric_cutoff)
        out[f"{method_name}_ndcg_repaired"] = _ndcg_at_k(rep_aligned, rel_map, k=metric_cutoff)
        out[f"{method_name}_ndcg_delta"] = (
            out[f"{method_name}_ndcg_repaired"] - out[f"{method_name}_ndcg_unrepaired"]
        )
    return out


def run_all() -> dict[str, Any]:
    per_query_records: list[dict[str, Any]] = []
    for dataset in t3.DATASETS:
        for pool_label, pool_map in t3.POOLS.items():
            pool_size = pool_map[dataset]
            metric_cutoff = (
                pool_size
                if METRIC_CUTOFF_BY_POOL_LABEL[pool_label] is None
                else METRIC_CUTOFF_BY_POOL_LABEL[pool_label]
            )
            dataset_inputs = t3.dataset_inputs_for_pool(dataset, pool_size)
            evaluator = fcu.CalibrationEvaluator()
            print(
                f"[leave-one-out] {dataset} {pool_label} P={pool_size} k={metric_cutoff}",
                flush=True,
            )
            for variant, rankers_subset in VARIANTS.items():
                for regime, (min_support, agg_threshold, drop_mutual) in _regimes_for_variant(
                    variant
                ).items():
                    for item in dataset_inputs["per_query_inputs"]:
                        rec = evaluate_variant_regime_query(
                            dataset=dataset,
                            query_id=item["query_id"],
                            item=item,
                            rankers_subset=rankers_subset,
                            min_support=min_support,
                            aggregate_threshold=agg_threshold,
                            drop_mutual=drop_mutual,
                            metric_cutoff=metric_cutoff,
                            evaluator=evaluator,
                        )
                        if rec is None:
                            continue
                        rec.update(
                            {
                                "pool_label": pool_label,
                                "pool_size": pool_size,
                                "metric_cutoff": metric_cutoff,
                                "variant": variant,
                                "rankers": "+".join(rankers_subset),
                                "regime": regime,
                            }
                        )
                        per_query_records.append(rec)
    return {"per_query_records": per_query_records}


def _structural_summary(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = defaultdict(list)
    for r in records:
        by_key[(r["dataset"], r["pool_label"], r["variant"], r["regime"])].append(r)
    rows = []
    for (dataset, pool_label, variant, regime), rs in sorted(by_key.items()):
        n = len(rs)
        rows.append(
            {
                "dataset": dataset,
                "pool_label": pool_label,
                "variant": variant,
                "regime": regime,
                "n_queries": n,
                "mean_edge_count": float(np.mean([r["n_edges"] for r in rs])),
                "mean_density": float(np.mean([r["density"] for r in rs])),
                "mean_mutual_pair_count": float(np.mean([r["mutual_pair_count"] for r in rs])),
                "pct_queries_with_mutual_pair": float(
                    np.mean([r["mutual_pair_count"] > 0 for r in rs])
                ),
                "mean_triangle_count": float(np.mean([r["triangle_count"] for r in rs])),
                "cyclic_query_pct": float(np.mean([r["is_cyclic"] for r in rs])),
                "cyclic_query_pct_after_repair": float(
                    np.mean([r["is_cyclic_after_repair"] for r in rs])
                ),
                "mean_largest_scc": float(np.mean([r["largest_scc"] for r in rs])),
                "mean_largest_scc_after_repair": float(
                    np.mean([r["largest_scc_after_repair"] for r in rs])
                ),
                "repair_active_fraction": float(np.mean([r["repair_active"] for r in rs])),
                "mean_edges_removed": float(np.mean([r["n_edges_removed"] for r in rs])),
                "mean_weight_removed": float(np.mean([r["removed_weight"] for r in rs])),
            }
        )
    return rows


def _retrieval_summary_and_stats(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    by_key = defaultdict(list)
    for r in records:
        for method in PAIR_METHODS:
            by_key[(r["dataset"], r["pool_label"], r["variant"], r["regime"], method)].append(
                r[f"{method}_ndcg_delta"]
            )
    summary_rows = []
    stat_rows = []
    active_family_pvalues: list[tuple[tuple, float | None]] = []
    for key, deltas in sorted(by_key.items()):
        dataset, pool_label, variant, regime, method = key
        n = len(deltas)
        helped = sum(1 for d in deltas if d > 1e-12)
        harmed = sum(1 for d in deltas if d < -1e-12)
        unchanged = n - helped - harmed
        summary_rows.append(
            {
                "dataset": dataset,
                "pool_label": pool_label,
                "variant": variant,
                "regime": regime,
                "pair_method": method,
                "n_queries": n,
                "mean_delta": float(np.mean(deltas)) if deltas else None,
                "helped_query_count": helped,
                "harmed_query_count": harmed,
                "unchanged_query_count": unchanged,
            }
        )
        sf = stats_inf.sign_flip_pvalue(deltas)
        stat_rows.append(
            {
                "dataset": dataset,
                "pool_label": pool_label,
                "variant": variant,
                "regime": regime,
                "pair_method": method,
                "n_queries": n,
                "mean_delta": float(np.mean(deltas)) if deltas else None,
                "raw_pvalue": sf.pvalue,
                "test_kind": sf.method,
            }
        )
        if regime == ACTIVE_REGIME_BY_VARIANT.get(variant):
            active_family_pvalues.append((key, sf.pvalue))

    # pre-specified single active-family Holm correction (see manifest)
    keys, pvals = zip(*active_family_pvalues) if active_family_pvalues else ((), ())
    holm = stats_inf.holm_adjust(list(pvals))
    active_rows = []
    for (key, raw_p), holm_p in zip(active_family_pvalues, holm):
        dataset, pool_label, variant, regime, method = key
        active_rows.append(
            {
                "dataset": dataset,
                "pool_label": pool_label,
                "variant": variant,
                "regime": regime,
                "pair_method": method,
                "raw_pvalue": raw_p,
                "holm_adjusted_pvalue": holm_p,
                "holm_significant_at_0.05": bool(holm_p is not None and holm_p < 0.05),
            }
        )
    return summary_rows, stat_rows, active_rows


def main() -> int:
    t0 = time.time()
    result = run_all()
    records = result["per_query_records"]
    t3.write_json(t3.OUTPUTS_DIR / "leave_one_out_per_query_records.json", records)

    structural = _structural_summary(records)
    t3.write_csv(t3.TABLES_DIR / "leave_one_out_structural_summary.csv", structural)

    retrieval_summary, stat_rows, active_family = _retrieval_summary_and_stats(records)
    t3.write_csv(t3.TABLES_DIR / "leave_one_out_retrieval_summary.csv", retrieval_summary)
    t3.write_csv(t3.TABLES_DIR / "leave_one_out_retrieval_statistics.csv", stat_rows)
    t3.write_csv(t3.TABLES_DIR / "leave_one_out_active_family_holm.csv", active_family)

    manifest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "variants": {k: list(v) for k, v in VARIANTS.items()},
        "three_ranker_regimes": THREE_RANKER_REGIMES,
        "two_ranker_regimes": TWO_RANKER_REGIMES,
        "active_regime_by_variant": ACTIVE_REGIME_BY_VARIANT,
        "active_family_size": len(active_family),
        "active_family_definition": (
            "one pre-specified family: for each of the 4 variants (all_three, pair_bm25_tfidf, "
            "pair_bm25_minilm, pair_tfidf_minilm), the variant's own 'active' permissive regime "
            "(ms1 for all_three, pair_any for two-ranker variants) x 4 datasets x 2 pool labels x "
            "2 pair methods (copeland, balance) = 64 cells, Holm-corrected jointly."
        ),
        "fixed_vote_threshold": FIXED_VOTE_THRESHOLD,
        "calibration": t3.PRIMARY_CALIBRATION,
        "metric_cutoff_policy": (
            "canonical pool: metric_cutoff = pool_size (P=k); task1_larger pool: "
            "metric_cutoff=10 (matches Task 1's targeted exact-study P>k cells)"
        ),
        "candidate_pool_policy": (
            "held fixed at the canonical RRF-fused-over-all-three-rankers pool for "
            "every variant, so only the vote source is ablated"
        ),
        "n_per_query_records": len(records),
        "elapsed_seconds": time.time() - t0,
    }
    t3.write_json(t3.MANIFESTS_DIR / "leave_one_out_run_summary.json", manifest)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
