#!/usr/bin/env python3
"""JDIQ Task 3, sections 2/3/4/7: coverage & abstention accounting,
pairwise ranker dependence, mutual-pair vote attribution, and ms2
sparsity/acyclicity accounting.

Reuses the canonical primary protocol (minmax_query_ranker calibration +
retention-matched thresholds) from full_calibration_utils.py /
run_full_calibrated_core.py so every count in this script corresponds
exactly to the manuscript's headline pipeline, run once per candidate-pool
size (canonical + Task 1 larger pool) and once per regime (ms2/ms1/
ms1_drop_mutual).
"""

# ruff: noqa: I001 -- import order below is semantically constrained (see comment)
from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from typing import Any

import networkx as nx
import numpy as np
from scipy.stats import kendalltau, pearsonr, spearmanr

# task3_common must import before full_calibration_utils: it puts the
# latter's directory on sys.path (see task3_common's sys.path bootstrap).
import task3_common as t3
import full_calibration_utils as fcu  # noqa: E402

RANKER_PAIRS = (("bm25", "tfidf"), ("bm25", "minilm"), ("tfidf", "minilm"))
TOPK_DEPTHS = (5, 10, 20)
LARGE_DEPTH = {"scidocs": 50, "fiqa": 50, "bright": 50, "hotpotqa": 35}


def _load_raw_score_lists(dataset: str) -> dict[str, dict[str, list[tuple[str, float]]]]:
    """Full stored per-query score lists (not restricted to any candidate
    pool), sorted descending, reusing Task 1's loader so depths/paths match
    exactly what Task 1 already validated."""
    import run_pool_cutoff_study as t1  # noqa: WPS433 (local import: adds sys.path lazily)

    _query_ids, _usable, score_lists = t1._load_score_lists(dataset)
    return score_lists


# ---------------------------------------------------------------------------
# Section 2: coverage and abstention accounting
# ---------------------------------------------------------------------------


def coverage_and_pair_funnel_for_dataset(
    dataset: str, pool_label: str, pool_size: int
) -> dict[str, Any]:
    dataset_inputs = t3.dataset_inputs_for_pool(dataset, pool_size)
    per_ranker_threshold_cfg = {
        regime: t3.canonical_threshold_config(dataset_inputs, regime) for regime in t3.REGIMES
    }
    # Vote thresholds are identical across regimes (verified empirically);
    # use ms1's as the shared per-ranker vote-margin threshold.
    vote_thresholds = per_ranker_threshold_cfg["ms1"].vote_thresholds

    coverage_rows: list[dict[str, Any]] = []
    funnel_rows: list[dict[str, Any]] = []

    for item in dataset_inputs["per_query_inputs"]:
        qid = item["query_id"]
        pool = item["candidate_pool"]
        n_cand = len(pool)
        n_pair = t3.n_pairs(n_cand)
        raw_scores = item["raw_scores_by_ranker"]

        calibrated_scores, _meta = fcu.apply_calibration_to_score_maps(
            raw_scores, pool, calibration=t3.PRIMARY_CALIBRATION
        )

        # --- per (query, ranker) coverage/abstention ---
        per_ranker_eligible_pairs: dict[str, int] = {}
        per_ranker_tied_pairs: dict[str, int] = {}
        for ranker in t3.RANKERS:
            score_map = raw_scores.get(ranker, {})
            n_scored = sum(1 for d in pool if d in score_map)
            eligible = 0
            tied = 0
            for a, b in t3.unordered_pairs(pool):
                if a in score_map and b in score_map:
                    eligible += 1
                    if score_map[a] == score_map[b]:
                        tied += 1
            per_ranker_eligible_pairs[ranker] = eligible
            per_ranker_tied_pairs[ranker] = tied
            coverage_rows.append(
                {
                    "dataset": dataset,
                    "pool_label": pool_label,
                    "pool_size": pool_size,
                    "query_id": qid,
                    "ranker": ranker,
                    "n_candidates": n_cand,
                    "n_scored": n_scored,
                    "coverage_fraction": n_scored / n_cand if n_cand else None,
                    "n_pairs": n_pair,
                    "eligible_pairs": eligible,
                    "pairwise_eligibility_fraction": (eligible / n_pair) if n_pair else None,
                    "native_ties": tied,
                    "tie_abstention_fraction_of_eligible": (tied / eligible) if eligible else None,
                    "missing_abstention_fraction": ((n_pair - eligible) / n_pair)
                    if n_pair
                    else None,
                    "vote_margin_threshold": vote_thresholds.get(ranker, 0.0),
                }
            )

        # --- direction maps (calibration + vote-threshold stage only) ---
        direction_maps = fcu.direction_maps_for_query(
            raw_scores_by_ranker=raw_scores,
            candidate_pool=pool,
            calibration=t3.PRIMARY_CALIBRATION,
            vote_thresholds=vote_thresholds,
        )
        # retained-vote count per ranker (post threshold, pre support/agg/drop_mutual)
        retained_votes_by_ranker: Counter = Counter()
        for dir_votes in direction_maps.values():
            for recs in dir_votes.values():
                for ranker, _weight in recs:
                    retained_votes_by_ranker[ranker] += 1
        for row in coverage_rows[-3:]:
            ranker = row["ranker"]
            eligible = row["eligible_pairs"]
            tied = row["native_ties"]
            nontied = eligible - tied
            retained = retained_votes_by_ranker.get(ranker, 0)
            row["nontied_eligible_pairs"] = nontied
            row["retained_votes"] = retained
            row["vote_margin_abstention_fraction_of_nontied"] = (
                ((nontied - retained) / nontied) if nontied else None
            )
            row["final_retained_vote_fraction_of_all_pairs"] = (
                (retained / n_pair) if n_pair else None
            )

        pairs_with_any_retained_vote = len(direction_maps)

        # --- per-regime pair funnel: support-qualified -> threshold-qualified -> final edge ---
        regime_funnel: dict[str, dict[str, int]] = {}
        for regime in t3.REGIMES:
            cfg = per_ranker_threshold_cfg[regime]
            support_qualified_pairs = 0
            threshold_qualified_pairs = 0
            final_edge_pairs = 0
            final_directed_edges = 0
            mutual_pairs = 0
            for pair_key, dir_votes in direction_maps.items():
                qualifying_directions = []
                for direction, recs in dir_votes.items():
                    support = len(recs)
                    agg_weight = sum(w for _r, w in recs)
                    if support >= cfg.min_support:
                        support_qualified_pairs += 1  # counted per qualifying direction below guard
                    if support >= cfg.min_support and agg_weight >= cfg.aggregate_threshold:
                        qualifying_directions.append(direction)
                if qualifying_directions:
                    threshold_qualified_pairs += 1
                if cfg.postprocess_drop_mutual and len(qualifying_directions) > 1:
                    continue
                if qualifying_directions:
                    final_edge_pairs += 1
                    final_directed_edges += len(qualifying_directions)
                    if len(qualifying_directions) > 1:
                        mutual_pairs += 1
            regime_funnel[regime] = {
                "support_qualified_pair_direction_events": support_qualified_pairs,
                "threshold_qualified_pairs": threshold_qualified_pairs,
                "final_edge_pairs": final_edge_pairs,
                "final_directed_edges": final_directed_edges,
                "mutual_pairs": mutual_pairs,
            }

        row_out = {
            "dataset": dataset,
            "pool_label": pool_label,
            "pool_size": pool_size,
            "query_id": qid,
            "n_candidates": n_cand,
            "n_pairs": n_pair,
            "pairs_with_any_retained_vote": pairs_with_any_retained_vote,
        }
        for regime, vals in regime_funnel.items():
            for k, v in vals.items():
                row_out[f"{regime}__{k}"] = v
            row_out[f"{regime}__final_retained_edge_fraction_of_pairs"] = (
                vals["final_edge_pairs"] / n_pair if n_pair else None
            )
        funnel_rows.append(row_out)

    return {"coverage_rows": coverage_rows, "funnel_rows": funnel_rows}


# ---------------------------------------------------------------------------
# Section 3: pairwise ranker dependence
# ---------------------------------------------------------------------------


def _jaccard_overlap_coef(a: set, b: set) -> tuple[float | None, float | None]:
    if not a and not b:
        return 1.0, 1.0
    union = a | b
    inter = a & b
    jac = len(inter) / len(union) if union else None
    denom = min(len(a), len(b))
    ovl = len(inter) / denom if denom else None
    return jac, ovl


def _rbo(list_a: list[str], list_b: list[str], p: float = 0.9) -> float:
    """Rank-biased overlap (Webber, Moffat & Zobel 2010), extrapolated form:
    RBO = (x_l / l) * p^l + ((1 - p) / p) * sum_{d=1}^{l} (x_d / d) * p^d,
    where l is the evaluated depth and x_d is the overlap of the two lists'
    first d items. Identical lists give RBO=1; disjoint lists give RBO=0."""
    s, t = set(), set()
    depth = max(len(list_a), len(list_b))
    if depth == 0:
        return 1.0
    x_d = 0
    weighted_sum = 0.0
    for d in range(1, depth + 1):
        if d <= len(list_a):
            s.add(list_a[d - 1])
        if d <= len(list_b):
            t.add(list_b[d - 1])
        x_d = len(s & t)
        weighted_sum += (x_d / d) * (p**d)
    x_l = x_d
    return float((x_l / depth) * (p**depth) + ((1.0 - p) / p) * weighted_sum)


def ranker_dependence_for_dataset_full_lists(dataset: str) -> dict[str, Any]:
    """Rank correlation (A) and top-k overlap incl. RBO (B) computed on each
    ranker's own full stored score list (not restricted to the small
    candidate pool), so overlap isn't inflated by RRF-fused pool selection."""
    score_lists = _load_raw_score_lists(dataset)
    depths = list(TOPK_DEPTHS) + [LARGE_DEPTH[dataset]]
    query_ids = sorted(
        set(score_lists.get("bm25", {}))
        & set(score_lists.get("tfidf", {}))
        & set(score_lists.get("minilm", {}))
    )

    rows_corr: list[dict[str, Any]] = []
    rows_overlap: list[dict[str, Any]] = []
    for r1, r2 in RANKER_PAIRS:
        for qid in query_ids:
            list1 = score_lists[r1].get(qid, [])
            list2 = score_lists[r2].get(qid, [])
            map1 = dict(list1)
            map2 = dict(list2)
            common = sorted(set(map1) & set(map2))
            if len(common) >= 2:
                v1 = [map1[d] for d in common]
                v2 = [map2[d] for d in common]
                tau, tau_p = kendalltau(v1, v2)
                rho, rho_p = spearmanr(v1, v2)
            else:
                tau = tau_p = rho = rho_p = None
            rows_corr.append(
                {
                    "dataset": dataset,
                    "ranker_a": r1,
                    "ranker_b": r2,
                    "query_id": qid,
                    "n_common_docs": len(common),
                    "kendall_tau_b": tau,
                    "kendall_tau_pvalue": tau_p,
                    "spearman_rho": rho,
                    "spearman_pvalue": rho_p,
                }
            )
            order1 = [d for d, _s in list1]
            order2 = [d for d, _s in list2]
            for depth in depths:
                top1 = set(order1[:depth])
                top2 = set(order2[:depth])
                jac, ovl = _jaccard_overlap_coef(top1, top2)
                rbo = _rbo(order1[:depth], order2[:depth]) if (order1 and order2) else None
                rows_overlap.append(
                    {
                        "dataset": dataset,
                        "ranker_a": r1,
                        "ranker_b": r2,
                        "query_id": qid,
                        "depth": depth,
                        "jaccard": jac,
                        "overlap_coefficient": ovl,
                        "rbo_p0.9": rbo,
                    }
                )
    return {"correlation_rows": rows_corr, "overlap_rows": rows_overlap}


def directional_agreement_and_margin_correlation(
    dataset: str, pool_label: str, pool_size: int
) -> list[dict[str, Any]]:
    """Directional agreement (C) and margin correlation (D) computed on
    candidate-pool pairs jointly scored by both rankers, in both raw and
    normalized (minmax_query_ranker) score space."""
    dataset_inputs = t3.dataset_inputs_for_pool(dataset, pool_size)
    rows: list[dict[str, Any]] = []
    for r1, r2 in RANKER_PAIRS:
        agree = disagree = tie_either = 0
        raw_margin1: list[float] = []
        raw_margin2: list[float] = []
        raw_signed1: list[float] = []
        raw_signed2: list[float] = []
        norm_margin1: list[float] = []
        norm_margin2: list[float] = []
        norm_signed1: list[float] = []
        norm_signed2: list[float] = []
        for item in dataset_inputs["per_query_inputs"]:
            pool = item["candidate_pool"]
            raw_scores = item["raw_scores_by_ranker"]
            calibrated, _meta = fcu.apply_calibration_to_score_maps(
                raw_scores, pool, calibration=t3.PRIMARY_CALIBRATION
            )
            m1, m2 = raw_scores.get(r1, {}), raw_scores.get(r2, {})
            c1, c2 = calibrated.get(r1, {}), calibrated.get(r2, {})
            for a, b in t3.unordered_pairs(pool):
                if a not in m1 or b not in m1 or a not in m2 or b not in m2:
                    continue
                d1_raw = m1[a] - m1[b]
                d2_raw = m2[a] - m2[b]
                tie1 = m1[a] == m1[b]
                tie2 = m2[a] == m2[b]
                if tie1 or tie2:
                    tie_either += 1
                else:
                    if (d1_raw > 0) == (d2_raw > 0):
                        agree += 1
                    else:
                        disagree += 1
                raw_margin1.append(abs(d1_raw))
                raw_margin2.append(abs(d2_raw))
                raw_signed1.append(d1_raw)
                raw_signed2.append(d2_raw)
                if a in c1 and b in c1 and a in c2 and b in c2:
                    d1n = c1[a] - c1[b]
                    d2n = c2[a] - c2[b]
                    norm_margin1.append(abs(d1n))
                    norm_margin2.append(abs(d2n))
                    norm_signed1.append(d1n)
                    norm_signed2.append(d2n)

        def _safe_pearson(x: list[float], y: list[float]) -> float | None:
            if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
                return None
            return float(pearsonr(x, y)[0])

        nontied_total = agree + disagree
        rows.append(
            {
                "dataset": dataset,
                "pool_label": pool_label,
                "pool_size": pool_size,
                "ranker_a": r1,
                "ranker_b": r2,
                "jointly_scored_pairs": agree + disagree + tie_either,
                "nontied_pairs": nontied_total,
                "agree_pairs": agree,
                "disagree_pairs": disagree,
                "tie_in_either_pairs": tie_either,
                "directional_agreement_rate_given_nontied": (agree / nontied_total)
                if nontied_total
                else None,
                "raw_abs_margin_correlation": _safe_pearson(raw_margin1, raw_margin2),
                "raw_signed_margin_correlation": _safe_pearson(raw_signed1, raw_signed2),
                "normalized_abs_margin_correlation": _safe_pearson(norm_margin1, norm_margin2),
                "normalized_signed_margin_correlation": _safe_pearson(norm_signed1, norm_signed2),
                "note": "raw cross-ranker score/margin correlations are on different native scales "
                "(BM25 unbounded lexical score, custom cosine TF-IDF in [0,1], MiniLM "
                "cosine similarity in [-1,1]); treat raw-space correlations as "
                "scale-sensitive diagnostics, not as directly comparable effect sizes -- "
                "the normalized-space values are the scale-controlled comparison.",
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Section 4: mutual-pair vote attribution
# ---------------------------------------------------------------------------


def _classify_configuration(dir1_rankers: set[str], dir2_rankers: set[str]) -> str:
    lexical = {"bm25", "tfidf"}
    pair_sorted = tuple(
        sorted(
            [frozenset(dir1_rankers), frozenset(dir2_rankers)], key=lambda s: (len(s), sorted(s))
        )
    )
    a, b = pair_sorted
    if {a, b} == {frozenset(lexical), frozenset({"minilm"})}:
        return "lexical_pair_vs_minilm"
    if len(a) == 1 and len(b) == 1:
        return "single_voter_vs_single_voter"
    if len(a) == 1 and len(b) == 2:
        return "single_voter_vs_two_voter"
    if len(a) == 2 and len(b) == 2:
        return "two_voter_vs_two_voter"
    return "other"


def mutual_pair_attribution_for_dataset(
    dataset: str, pool_label: str, pool_size: int
) -> list[dict[str, Any]]:
    dataset_inputs = t3.dataset_inputs_for_pool(dataset, pool_size)
    threshold_cfg_ms1 = t3.canonical_threshold_config(dataset_inputs, "ms1")
    vote_thresholds = threshold_cfg_ms1.vote_thresholds
    min_support, agg_threshold, _drop = fcu.base_variant_parameters("ms1")

    rows: list[dict[str, Any]] = []
    for item in dataset_inputs["per_query_inputs"]:
        qid = item["query_id"]
        pool = item["candidate_pool"]
        raw_scores = item["raw_scores_by_ranker"]
        direction_maps = fcu.direction_maps_for_query(
            raw_scores_by_ranker=raw_scores,
            candidate_pool=pool,
            calibration=t3.PRIMARY_CALIBRATION,
            vote_thresholds=vote_thresholds,
        )
        for pair_key, dir_votes in direction_maps.items():
            qualifying = {}
            for direction, recs in dir_votes.items():
                support = len(recs)
                agg_weight = sum(w for _r, w in recs)
                if support >= min_support and agg_weight >= agg_threshold:
                    qualifying[direction] = {r for r, _w in recs}
            if len(qualifying) <= 1:
                continue  # not a mutual (contested) pair under ms1
            directions = list(qualifying.items())
            (_dir1, rankers1), (_dir2, rankers2) = directions[0], directions[1]
            config = _classify_configuration(rankers1, rankers2)
            rows.append(
                {
                    "dataset": dataset,
                    "pool_label": pool_label,
                    "pool_size": pool_size,
                    "query_id": qid,
                    "pair": f"{pair_key[0]}|{pair_key[1]}",
                    "direction_1_rankers": "+".join(sorted(rankers1)),
                    "direction_2_rankers": "+".join(sorted(rankers2)),
                    "configuration": config,
                }
            )
    return rows


# ---------------------------------------------------------------------------
# Section 7: ms2 density / sparsity accounting
# ---------------------------------------------------------------------------


def ms2_sparsity_for_dataset(dataset: str, pool_label: str, pool_size: int) -> dict[str, Any]:
    dataset_inputs = t3.dataset_inputs_for_pool(dataset, pool_size)
    threshold_cfg = t3.canonical_threshold_config(dataset_inputs, "ms2")
    per_query_rows: list[dict[str, Any]] = []
    for item in dataset_inputs["per_query_inputs"]:
        qid = item["query_id"]
        pool = item["candidate_pool"]
        artifacts = fcu.build_query_vote_artifacts(
            query_id=qid,
            raw_scores_by_ranker=item["raw_scores_by_ranker"],
            candidate_pool=pool,
            calibration=t3.PRIMARY_CALIBRATION,
            threshold_config=threshold_cfg,
        )
        prefs = [
            fcu.Preference(
                winner=str(r["winner_doc_id"]),
                loser=str(r["loser_doc_id"]),
                weight=float(r["weight"]),
            )
            for r in artifacts["rows"]
        ]
        graph = fcu.build_graph(prefs)
        graph.add_nodes_from(pool)
        n_nodes = graph.number_of_nodes()
        n_edges = graph.number_of_edges()
        density = nx.density(graph) if n_nodes > 1 else 0.0
        undirected = graph.to_undirected()
        wccs = list(nx.connected_components(undirected))
        largest_wcc = max((len(c) for c in wccs), default=0)
        sccs = list(nx.strongly_connected_components(graph))
        largest_scc = max((len(c) for c in sccs), default=0)
        support_by_edge = defaultdict(int)
        for r in artifacts["rows"]:
            support_by_edge[(r["winner_doc_id"], r["loser_doc_id"])] += 1
        agree_all3 = sum(1 for v in support_by_edge.values() if v >= 3)
        agree_2 = sum(1 for v in support_by_edge.values() if v == 2)
        per_query_rows.append(
            {
                "dataset": dataset,
                "pool_label": pool_label,
                "pool_size": pool_size,
                "query_id": qid,
                "n_nodes": n_nodes,
                "n_edges": n_edges,
                "density": density,
                "n_weak_components": len(wccs),
                "largest_weak_component": largest_wcc,
                "largest_scc": largest_scc,
                "is_cyclic": largest_scc > 1,
                "edges_all3_agree": agree_all3,
                "edges_exactly2_agree": agree_2,
            }
        )
    n = len(per_query_rows)

    def frac_le(threshold: int) -> float:
        return sum(1 for r in per_query_rows if r["n_edges"] <= threshold) / n if n else None

    summary = {
        "dataset": dataset,
        "pool_label": pool_label,
        "pool_size": pool_size,
        "n_queries": n,
        "mean_n_nodes": float(np.mean([r["n_nodes"] for r in per_query_rows])) if n else None,
        "mean_n_edges": float(np.mean([r["n_edges"] for r in per_query_rows])) if n else None,
        "mean_density": float(np.mean([r["density"] for r in per_query_rows])) if n else None,
        "fraction_edgeless": frac_le(0),
        "fraction_le_1_edge": frac_le(1),
        "fraction_le_5_edges": frac_le(5),
        "fraction_le_10_edges": frac_le(10),
        "mean_n_weak_components": float(np.mean([r["n_weak_components"] for r in per_query_rows]))
        if n
        else None,
        "mean_largest_weak_component": float(
            np.mean([r["largest_weak_component"] for r in per_query_rows])
        )
        if n
        else None,
        "mean_largest_scc": float(np.mean([r["largest_scc"] for r in per_query_rows]))
        if n
        else None,
        "fraction_cyclic_queries": float(np.mean([r["is_cyclic"] for r in per_query_rows]))
        if n
        else None,
        "total_edges_all3_agree": sum(r["edges_all3_agree"] for r in per_query_rows),
        "total_edges_exactly2_agree": sum(r["edges_exactly2_agree"] for r in per_query_rows),
    }
    return {"per_query": per_query_rows, "summary": summary}


def main() -> int:
    t0 = time.time()
    t3.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    t3.MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)

    all_coverage_rows: list[dict[str, Any]] = []
    all_funnel_rows: list[dict[str, Any]] = []
    all_corr_rows: list[dict[str, Any]] = []
    all_overlap_rows: list[dict[str, Any]] = []
    all_directional_rows: list[dict[str, Any]] = []
    all_mutual_rows: list[dict[str, Any]] = []
    ms2_per_query_rows: list[dict[str, Any]] = []
    ms2_summary_rows: list[dict[str, Any]] = []

    for dataset in t3.DATASETS:
        print(f"[dependence] full-list rank correlation & overlap: {dataset}", flush=True)
        dep = ranker_dependence_for_dataset_full_lists(dataset)
        all_corr_rows.extend(dep["correlation_rows"])
        all_overlap_rows.extend(dep["overlap_rows"])

        for pool_label, pool_map in t3.POOLS.items():
            pool_size = pool_map[dataset]
            print(f"[coverage/funnel] {dataset} {pool_label} (P={pool_size})", flush=True)
            cov = coverage_and_pair_funnel_for_dataset(dataset, pool_label, pool_size)
            all_coverage_rows.extend(cov["coverage_rows"])
            all_funnel_rows.extend(cov["funnel_rows"])

            print(f"[directional agreement] {dataset} {pool_label}", flush=True)
            all_directional_rows.extend(
                directional_agreement_and_margin_correlation(dataset, pool_label, pool_size)
            )

            print(f"[mutual-pair attribution] {dataset} {pool_label}", flush=True)
            all_mutual_rows.extend(
                mutual_pair_attribution_for_dataset(dataset, pool_label, pool_size)
            )

            print(f"[ms2 sparsity] {dataset} {pool_label}", flush=True)
            ms2 = ms2_sparsity_for_dataset(dataset, pool_label, pool_size)
            ms2_per_query_rows.extend(ms2["per_query"])
            ms2_summary_rows.append(ms2["summary"])

    t3.write_csv(t3.TABLES_DIR / "coverage_per_query.csv", all_coverage_rows)
    t3.write_csv(t3.TABLES_DIR / "pair_funnel_per_query.csv", all_funnel_rows)
    t3.write_csv(t3.TABLES_DIR / "rank_correlation_per_query.csv", all_corr_rows)
    t3.write_csv(t3.TABLES_DIR / "topk_overlap_per_query.csv", all_overlap_rows)
    t3.write_csv(
        t3.TABLES_DIR / "directional_agreement_margin_correlation.csv", all_directional_rows
    )
    t3.write_csv(t3.TABLES_DIR / "mutual_pair_attribution_raw.csv", all_mutual_rows)
    t3.write_csv(t3.TABLES_DIR / "ms2_sparsity_per_query.csv", ms2_per_query_rows)
    t3.write_csv(t3.TABLES_DIR / "ms2_sparsity_summary.csv", ms2_summary_rows)

    # --- aggregate coverage ---
    agg_rows = []
    by_key = defaultdict(list)
    for r in all_coverage_rows:
        by_key[(r["dataset"], r["pool_label"], r["ranker"])].append(r)
    for (dataset, pool_label, ranker), rows in sorted(by_key.items()):
        agg_rows.append(
            {
                "dataset": dataset,
                "pool_label": pool_label,
                "ranker": ranker,
                "n_queries": len(rows),
                "mean_coverage_fraction": float(np.mean([r["coverage_fraction"] for r in rows])),
                "mean_pairwise_eligibility_fraction": float(
                    np.mean([r["pairwise_eligibility_fraction"] for r in rows])
                ),
                "mean_tie_abstention_fraction_of_eligible": float(
                    np.mean([r["tie_abstention_fraction_of_eligible"] or 0.0 for r in rows])
                ),
                "mean_missing_abstention_fraction": float(
                    np.mean([r["missing_abstention_fraction"] for r in rows])
                ),
                "mean_vote_margin_abstention_fraction_of_nontied": float(
                    np.mean([r["vote_margin_abstention_fraction_of_nontied"] or 0.0 for r in rows])
                ),
                "mean_final_retained_vote_fraction_of_all_pairs": float(
                    np.mean([r["final_retained_vote_fraction_of_all_pairs"] for r in rows])
                ),
                "total_eligible_pairs": sum(r["eligible_pairs"] for r in rows),
                "total_native_ties": sum(r["native_ties"] for r in rows),
                "total_retained_votes": sum(r["retained_votes"] for r in rows),
            }
        )
    t3.write_csv(t3.TABLES_DIR / "coverage_aggregate.csv", agg_rows)

    # --- aggregate pair funnel ---
    funnel_agg = []
    by_key2 = defaultdict(list)
    for r in all_funnel_rows:
        by_key2[(r["dataset"], r["pool_label"])].append(r)
    for (dataset, pool_label), rows in sorted(by_key2.items()):
        entry = {"dataset": dataset, "pool_label": pool_label, "n_queries": len(rows)}
        for regime in t3.REGIMES:
            entry[f"{regime}_mean_final_retained_edge_fraction"] = float(
                np.mean([r[f"{regime}__final_retained_edge_fraction_of_pairs"] for r in rows])
            )
            entry[f"{regime}_total_final_edge_pairs"] = sum(
                r[f"{regime}__final_edge_pairs"] for r in rows
            )
            entry[f"{regime}_total_mutual_pairs"] = sum(r[f"{regime}__mutual_pairs"] for r in rows)
        funnel_agg.append(entry)
    t3.write_csv(t3.TABLES_DIR / "pair_funnel_aggregate.csv", funnel_agg)

    # --- aggregate rank correlation (macro summary per ranker pair per dataset) ---
    corr_agg = []
    by_key3 = defaultdict(list)
    for r in all_corr_rows:
        by_key3[(r["dataset"], r["ranker_a"], r["ranker_b"])].append(r)
    for (dataset, ra, rb), rows in sorted(by_key3.items()):
        taus = [r["kendall_tau_b"] for r in rows if r["kendall_tau_b"] is not None]
        rhos = [r["spearman_rho"] for r in rows if r["spearman_rho"] is not None]
        corr_agg.append(
            {
                "dataset": dataset,
                "ranker_a": ra,
                "ranker_b": rb,
                "n_queries_with_valid_corr": len(taus),
                "mean_kendall_tau_b": float(np.mean(taus)) if taus else None,
                "median_kendall_tau_b": float(np.median(taus)) if taus else None,
                "mean_spearman_rho": float(np.mean(rhos)) if rhos else None,
                "median_spearman_rho": float(np.median(rhos)) if rhos else None,
            }
        )
    t3.write_csv(t3.TABLES_DIR / "rank_correlation_summary.csv", corr_agg)

    # --- aggregate top-k overlap ---
    overlap_agg = []
    by_key4 = defaultdict(list)
    for r in all_overlap_rows:
        by_key4[(r["dataset"], r["ranker_a"], r["ranker_b"], r["depth"])].append(r)
    for (dataset, ra, rb, depth), rows in sorted(by_key4.items()):
        overlap_agg.append(
            {
                "dataset": dataset,
                "ranker_a": ra,
                "ranker_b": rb,
                "depth": depth,
                "n_queries": len(rows),
                "mean_jaccard": float(
                    np.mean([r["jaccard"] for r in rows if r["jaccard"] is not None])
                ),
                "mean_overlap_coefficient": float(
                    np.mean(
                        [
                            r["overlap_coefficient"]
                            for r in rows
                            if r["overlap_coefficient"] is not None
                        ]
                    )
                ),
                "mean_rbo_p0.9": float(
                    np.mean([r["rbo_p0.9"] for r in rows if r["rbo_p0.9"] is not None])
                ),
            }
        )
    t3.write_csv(t3.TABLES_DIR / "topk_overlap_summary.csv", overlap_agg)

    # --- mutual pair attribution summary ---
    mutual_agg = []
    by_key5 = defaultdict(list)
    for r in all_mutual_rows:
        by_key5[(r["dataset"], r["pool_label"])].append(r)
    for (dataset, pool_label), rows in sorted(by_key5.items()):
        total = len(rows)
        cfg_counts = Counter(r["configuration"] for r in rows)
        entry = {"dataset": dataset, "pool_label": pool_label, "total_mutual_pairs": total}
        for cfg, count in cfg_counts.items():
            entry[f"count_{cfg}"] = count
            entry[f"pct_{cfg}"] = (count / total) if total else None
        mutual_agg.append(entry)
    t3.write_csv(t3.TABLES_DIR / "mutual_pair_attribution_summary.csv", mutual_agg)

    manifest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "datasets": list(t3.DATASETS),
        "pools": {k: v for k, v in t3.POOLS.items()},
        "regimes": list(t3.REGIMES),
        "rankers": list(t3.RANKERS),
        "topk_depths_used": list(TOPK_DEPTHS) + ["dataset-specific-large-depth (see LARGE_DEPTH)"],
        "large_depth_by_dataset": LARGE_DEPTH,
        "elapsed_seconds": time.time() - t0,
        "tables_written": [
            "coverage_per_query.csv",
            "coverage_aggregate.csv",
            "pair_funnel_per_query.csv",
            "pair_funnel_aggregate.csv",
            "rank_correlation_per_query.csv",
            "rank_correlation_summary.csv",
            "topk_overlap_per_query.csv",
            "topk_overlap_summary.csv",
            "directional_agreement_margin_correlation.csv",
            "mutual_pair_attribution_raw.csv",
            "mutual_pair_attribution_summary.csv",
            "ms2_sparsity_per_query.csv",
            "ms2_sparsity_summary.csv",
        ],
    }
    t3.write_json(t3.MANIFESTS_DIR / "coverage_and_dependence_run_summary.json", manifest)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
