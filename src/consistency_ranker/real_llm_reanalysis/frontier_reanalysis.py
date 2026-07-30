"""Query-clustered re-analysis of the repair-frontier study.

`reports/repair_frontier_20260729T144742Z/checkpoint/frontier_results.jsonl`
stores each candidate ranking's `global_ranking` but not its nDCG (nDCG was
computed in-memory during the original run and only the resulting
*aggregate* statistics were persisted, in `FINAL_SUMMARY.json`). To get
per-unit deltas for a cluster-aware re-analysis, this module recomputes
per-candidate nDCG@10 from the already-stored `global_ranking` lists using
the exact same function the original pipeline used
(`consistency_ranker.evaluation.ndcg_at_k`) against the exact same relevance
maps (`scripts/run_reviewer_concerns_program._base_queries()`, which reads
already-frozen local qrels -- no new judgments, no API calls). This is a
re-derivation from already-stored data, not a new computation method.

Correctness is checked by comparing the recomputed aggregate
(`mean_incumbent_ndcg`, `mean_best_ndcg`, `mean_headroom`) against the
already-published `FINAL_SUMMARY.json` values -- see
`verify_reconstruction_matches_original()`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

import run_reviewer_concerns_program as program_lib  # noqa: E402

from consistency_ranker.evaluation import ndcg_at_k  # noqa: E402
from consistency_ranker.statistical_inference import (  # noqa: E402
    cluster_bootstrap_mean_interval,
    cluster_exact_sign_flip_pvalue,
    compute_cluster_means,
)

FRONTIER_DIR = _REPO_ROOT / "reports/repair_frontier_20260729T144742Z"
NDCG_K = 10  # matches MAIN_TOPK in scripts/run_repair_frontier_pilot.py


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _relevance_maps() -> dict[tuple[str, str], dict[str, int]]:
    """(dataset, query_id) -> {doc_id: relevance}, from the same frozen
    local qrels the original pipeline used."""
    base_queries = program_lib._base_queries()
    out = {}
    for bq in base_queries:
        qid = bq["query_id"]
        out[(bq["dataset"], qid)] = {
            qr.doc_id: qr.relevance for qr in bq["qrels_by_query"].get(qid, [])
        }
    return out


def reconstruct_per_unit_outcomes() -> list[dict[str, Any]]:
    """One row per unit_key: incumbent_ndcg, best_ndcg (oracle over the full
    candidate frontier), whole_graph_ndcg (best of just the two whole-graph
    repair candidates, if present), and the deltas, all recomputed from
    stored `global_ranking` data."""
    rows = _load_jsonl(FRONTIER_DIR / "checkpoint/frontier_results.jsonl")
    rel_maps = _relevance_maps()

    by_unit: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_unit.setdefault(r["unit_key"], []).append(r)

    whole_graph_ids = {"whole_graph_greedy", "whole_graph_exact"}
    outcomes = []
    for unit_key, candidates in by_unit.items():
        dataset = candidates[0]["dataset"]
        query_id = candidates[0]["query_id"]
        rel_map = rel_maps.get((dataset, query_id), {})
        per_candidate_ndcg = {
            c["candidate_id"]: ndcg_at_k(c["global_ranking"], rel_map, k=NDCG_K) for c in candidates
        }
        incumbent_ndcg = per_candidate_ndcg.get("incumbent")
        if incumbent_ndcg is None:
            continue  # invariant violation -- exclude and let the caller notice n_rows is short
        best_id = max(per_candidate_ndcg, key=lambda cid: per_candidate_ndcg[cid])
        best_ndcg = per_candidate_ndcg[best_id]
        wg_candidates = {cid: v for cid, v in per_candidate_ndcg.items() if cid in whole_graph_ids}
        whole_graph_ndcg = max(wg_candidates.values()) if wg_candidates else incumbent_ndcg
        alt_extraction_candidates = {
            cid: v for cid, v in per_candidate_ndcg.items() if cid.startswith("alt_extraction_")
        }
        best_alt_extraction_ndcg = (
            max(alt_extraction_candidates.values()) if alt_extraction_candidates else incumbent_ndcg
        )
        outcomes.append(
            {
                "unit_key": unit_key,
                "dataset": dataset,
                "query_id": query_id,
                "incumbent_ndcg": incumbent_ndcg,
                "best_ndcg_oracle_full_frontier": best_ndcg,
                "best_candidate_id_oracle_full_frontier": best_id,
                "whole_graph_ndcg": whole_graph_ndcg,
                "best_alt_extraction_ndcg": best_alt_extraction_ndcg,
                "delta_oracle_full_frontier": best_ndcg - incumbent_ndcg,
                "delta_whole_graph_repair": whole_graph_ndcg - incumbent_ndcg,
                "delta_best_alt_extraction": best_alt_extraction_ndcg - incumbent_ndcg,
                "n_candidates_evaluated": len(candidates),
            }
        )
    return outcomes


def verify_reconstruction_matches_original(outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare recomputed aggregates against FINAL_SUMMARY.json's already-
    published numbers -- if these don't match closely, the reconstruction
    has a bug and should not be trusted."""
    published = json.loads((FRONTIER_DIR / "FINAL_SUMMARY.json").read_text())["discovery"]
    n = len(outcomes)
    recomputed_mean_incumbent = sum(o["incumbent_ndcg"] for o in outcomes) / n
    recomputed_mean_best = sum(o["best_ndcg_oracle_full_frontier"] for o in outcomes) / n
    recomputed_mean_headroom = recomputed_mean_best - recomputed_mean_incumbent
    return {
        "n_outcomes_recomputed": len(outcomes),
        "n_outcomes_published": published["n_queries"],
        "published_mean_incumbent_ndcg": published["mean_incumbent_ndcg"],
        "recomputed_mean_incumbent_ndcg": recomputed_mean_incumbent,
        "published_mean_best_ndcg": published["mean_best_ndcg"],
        "recomputed_mean_best_ndcg": recomputed_mean_best,
        "published_mean_headroom": published["mean_headroom"],
        "recomputed_mean_headroom": recomputed_mean_headroom,
        "max_abs_diff": max(
            abs(published["mean_incumbent_ndcg"] - recomputed_mean_incumbent),
            abs(published["mean_best_ndcg"] - recomputed_mean_best),
            abs(published["mean_headroom"] - recomputed_mean_headroom),
        ),
    }


def clustered_analysis(outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    """The actual re-analysis: query-clustered CIs and exact paired tests
    for each of the three delta definitions, in place of the original
    row-level `bootstrap_mean_interval` over all 120 units."""
    query_ids = [o["query_id"] for o in outcomes]
    results = {}
    for label, key in [
        ("oracle_full_frontier_upper_bound", "delta_oracle_full_frontier"),
        ("whole_graph_repair", "delta_whole_graph_repair"),
        ("best_alt_extraction", "delta_best_alt_extraction"),
    ]:
        deltas = [o[key] for o in outcomes]
        agg = compute_cluster_means(deltas, query_ids)
        ci = cluster_bootstrap_mean_interval(deltas, query_ids, seed=13)
        sign = cluster_exact_sign_flip_pvalue(deltas, query_ids)
        results[label] = {
            "n_rows": len(deltas),
            "n_clusters": agg.n_clusters,
            "cluster_ids": agg.cluster_ids,
            "cluster_means": agg.cluster_means,
            "mean_of_cluster_means": agg.overall_mean,
            "cluster_bootstrap_ci_lower": ci.lower,
            "cluster_bootstrap_ci_upper": ci.upper,
            "cluster_bootstrap_frac_gt_zero": ci.frac_gt_zero,
            "exact_sign_flip_pvalue": sign.pvalue,
            "exact_sign_flip_n_patterns": sign.reps,
            "is_upper_bound_diagnostic_not_deployable": label == "oracle_full_frontier_upper_bound",
        }
    return results
