"""Query-clustered re-analysis of the extraction-method comparison study.

Unlike `repair_frontier`, `extraction_study`'s own
`extraction_results.jsonl` already stores every extractor's nDCG per row
(`ndcg_by_extractor`) alongside `incumbent_ndcg` -- no reconstruction is
needed, only the clustered inference the original analysis omitted.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from consistency_ranker.statistical_inference import (
    cluster_bootstrap_mean_interval,
    cluster_exact_sign_flip_pvalue,
    compute_cluster_means,
    holm_adjust,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
EXTRACTION_DIR = _REPO_ROOT / "reports/extraction_study_20260729T151610Z"

INCUMBENT_KEY = "incumbent"  # == "copeland" per extractors.py; the primary comparator
NON_INCUMBENT_EXTRACTORS = [
    "borda",
    "pagerank",
    "rank_centrality",
    "balance_score",
    "hodge_rank",
    "fas_balance_prior_fusion",
    "hybrid_rrf_prior_fusion",
]
# "copeland" is numerically identical to "incumbent" (verified: FINAL_REPORT.md
# reports mean_delta=0.00000 for copeland, win/tie/loss=0/120/0) -- included as
# the 8th member of the declared comparison family per the task brief
# ("Holm correction across the full extractor comparison family" / "eight
# extractors"), even though it is a trivial null-by-construction comparison.
FULL_COMPARISON_FAMILY = NON_INCUMBENT_EXTRACTORS + ["copeland"]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_rows() -> list[dict[str, Any]]:
    return _load_jsonl(EXTRACTION_DIR / "extraction_results.jsonl")


def per_extractor_deltas(rows: list[dict[str, Any]], extractor: str) -> list[float]:
    return [r["ndcg_by_extractor"][extractor] - r["incumbent_ndcg"] for r in rows]


def clustered_analysis(rows: list[dict[str, Any]]) -> dict[str, Any]:
    query_ids = [r["query_id"] for r in rows]
    per_extractor: dict[str, Any] = {}
    for extractor in FULL_COMPARISON_FAMILY:
        deltas = per_extractor_deltas(rows, extractor)
        agg = compute_cluster_means(deltas, query_ids)
        ci = cluster_bootstrap_mean_interval(deltas, query_ids, seed=13)
        sign = cluster_exact_sign_flip_pvalue(deltas, query_ids)
        n_query_wins = sum(1 for m in agg.cluster_means if m > 0)
        n_query_losses = sum(1 for m in agg.cluster_means if m < 0)
        n_query_ties = agg.n_clusters - n_query_wins - n_query_losses
        per_extractor[extractor] = {
            "n_rows": len(deltas),
            "n_clusters": agg.n_clusters,
            "cluster_ids": agg.cluster_ids,
            "cluster_means": agg.cluster_means,
            "mean_of_cluster_means": agg.overall_mean,
            "cluster_bootstrap_ci_lower": ci.lower,
            "cluster_bootstrap_ci_upper": ci.upper,
            "cluster_bootstrap_frac_gt_zero": ci.frac_gt_zero,
            "exact_sign_flip_pvalue_raw": sign.pvalue,
            "n_query_level_wins": n_query_wins,
            "n_query_level_losses": n_query_losses,
            "n_query_level_ties": n_query_ties,
            "direction_consistent_across_queries": n_query_wins == agg.n_clusters
            or n_query_losses == agg.n_clusters,
        }

    # Holm correction across the FULL declared family (8 extractors), using
    # the exact cluster-level sign-flip p-value for each -- not the
    # row-level p-value the original analysis implicitly relied on (it
    # reported bootstrap CIs per extractor but never combined them into one
    # corrected family at all).
    raw_pvalues = [per_extractor[e]["exact_sign_flip_pvalue_raw"] for e in FULL_COMPARISON_FAMILY]
    holm_pvalues = holm_adjust(raw_pvalues)
    for extractor, holm_p in zip(FULL_COMPARISON_FAMILY, holm_pvalues):
        per_extractor[extractor]["exact_sign_flip_pvalue_holm"] = holm_p
        per_extractor[extractor]["holm_significant_at_0.05"] = (
            holm_p is not None and holm_p < 0.05
        )

    return {
        "incumbent_comparator": INCUMBENT_KEY,
        "family_members": FULL_COMPARISON_FAMILY,
        "family_size": len(FULL_COMPARISON_FAMILY),
        "per_extractor": per_extractor,
    }
