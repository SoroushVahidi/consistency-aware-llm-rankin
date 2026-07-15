#!/usr/bin/env python3
"""Verify every numeric claim added to main.tex in Task 3 against the CSV/
JSON tables that produced it. Writes a markdown audit and exits non-zero if
any claim does not match its source table within tolerance."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path("")
TASK3_ROOT = REPO_ROOT / "reports/final_revision_task3_ranker_dependence_20260715"
TABLES = TASK3_ROOT / "tables"
VALIDATION = TASK3_ROOT / "validation"
TOL = 5e-3  # for values quoted to 3 decimal places (tau_b, agreement rates)
TOL_1DP = 0.06  # for values quoted to 1 decimal place (percentages, mean edges)
TOL_ROUND = 1.0  # for values quoted as rounded whole-number "about X" ranges


def load_csv(name: str) -> list[dict[str, str]]:
    with (TABLES / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def find_row(rows: list[dict[str, str]], **match: str) -> dict[str, str]:
    for row in rows:
        if all(row[key] == value for key, value in match.items()):
            return row
    raise KeyError(f"No row matching {match} in table with {len(rows)} rows")


def check(
    label: str, claimed: float, actual: float, results: list[dict[str, object]], tol: float = TOL
) -> None:
    ok = abs(claimed - actual) <= tol
    results.append({"claim": label, "claimed": claimed, "actual": actual, "match": ok, "tol": tol})


def main() -> int:
    VALIDATION.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []

    corr = load_csv("rank_correlation_summary.csv")
    dep_dataset = {(r["dataset"], r["ranker_a"], r["ranker_b"]): r for r in corr}
    tau_claims = {
        ("scidocs", "bm25", "tfidf"): 0.452,
        ("scidocs", "bm25", "minilm"): 0.214,
        ("scidocs", "tfidf", "minilm"): 0.175,
        ("fiqa", "bm25", "tfidf"): 0.312,
        ("fiqa", "bm25", "minilm"): 0.175,
        ("fiqa", "tfidf", "minilm"): 0.187,
        ("hotpotqa", "bm25", "tfidf"): 0.562,
        ("hotpotqa", "bm25", "minilm"): 0.436,
        ("hotpotqa", "tfidf", "minilm"): 0.434,
        ("bright", "bm25", "tfidf"): 0.142,
        ("bright", "bm25", "minilm"): 0.182,
        ("bright", "tfidf", "minilm"): 0.171,
    }
    for (dataset, ra, rb), claimed in tau_claims.items():
        row = dep_dataset[(dataset, ra, rb)]
        check(f"tau_b({dataset},{ra},{rb})", claimed, float(row["mean_kendall_tau_b"]), results)

    directional = load_csv("directional_agreement_margin_correlation.csv")
    dir_canonical = {
        (r["dataset"], r["ranker_a"], r["ranker_b"]): r
        for r in directional
        if r["pool_label"] == "canonical"
    }
    agreement_claims = {
        ("scidocs", "bm25", "tfidf"): 0.720,
        ("fiqa", "bm25", "tfidf"): 0.627,
        ("hotpotqa", "bm25", "tfidf"): 0.817,
        ("bright", "bm25", "tfidf"): 0.573,
        ("bright", "bm25", "minilm"): 0.604,
    }
    for (dataset, ra, rb), claimed in agreement_claims.items():
        row = dir_canonical[(dataset, ra, rb)]
        check(
            f"directional_agreement({dataset},{ra},{rb})",
            claimed,
            float(row["directional_agreement_rate_given_nontied"]),
            results,
        )

    mutual = load_csv("mutual_pair_attribution_summary.csv")
    mutual_canonical = {r["dataset"]: r for r in mutual if r["pool_label"] == "canonical"}
    mutual_claims = {
        "scidocs": (14.8, 78.9),
        "fiqa": (5.9, 89.8),
        "hotpotqa": (26.8, 66.5),
        "bright": (3.8, 91.1),
    }
    for dataset, (lex_pct, single_pct) in mutual_claims.items():
        row = mutual_canonical[dataset]
        check(
            f"mutual_lexical_vs_minilm_pct({dataset})",
            lex_pct,
            float(row["pct_lexical_pair_vs_minilm"]) * 100.0,
            results,
            tol=TOL_1DP,
        )
        check(
            f"mutual_single_vs_single_pct({dataset})",
            single_pct,
            float(row["pct_single_voter_vs_single_voter"]) * 100.0,
            results,
            tol=TOL_1DP,
        )

    loo_holm = load_csv("leave_one_out_active_family_holm.csv")
    n_sig = sum(1 for r in loo_holm if r["holm_significant_at_0.05"] == "True")
    check("leave_one_out_active_family_size", 64, len(loo_holm), results)
    check("leave_one_out_active_family_n_significant", 0, n_sig, results)

    loo_struct = load_csv("leave_one_out_structural_summary.csv")
    loo_by_key = {(r["dataset"], r["pool_label"], r["variant"], r["regime"]): r for r in loo_struct}
    mutual_pair_claims = {
        ("fiqa", "canonical", "pair_bm25_tfidf", "pair_any"): 41.1,
        ("fiqa", "canonical", "pair_bm25_minilm", "pair_any"): 11.9,
        ("fiqa", "canonical", "pair_tfidf_minilm", "pair_any"): 12.6,
        ("hotpotqa", "canonical", "pair_bm25_tfidf", "pair_any"): 3.4,
        ("hotpotqa", "canonical", "pair_bm25_minilm", "pair_any"): 5.3,
        ("hotpotqa", "canonical", "pair_tfidf_minilm", "pair_any"): 6.0,
    }
    for key, claimed in mutual_pair_claims.items():
        row = loo_by_key[key]
        check(
            f"loo_mean_mutual_pairs{key}",
            claimed,
            float(row["mean_mutual_pair_count"]),
            results,
            tol=TOL_1DP,
        )

    ppn_holm = load_csv("pre_post_normalization_active_family_holm.csv")
    n_sig_ppn = sum(1 for r in ppn_holm if r["holm_significant_at_0.05"] == "True")
    check("pre_post_normalization_active_family_size", 32, len(ppn_holm), results)
    check("pre_post_normalization_active_family_n_significant", 0, n_sig_ppn, results)

    ppn_struct = load_csv("pre_post_normalization_structural_summary.csv")
    post_row = find_row(
        ppn_struct,
        dataset="scidocs",
        pool_label="canonical",
        construction="post_pool_minmax",
        regime="ms1",
    )
    pre_row = find_row(
        ppn_struct,
        dataset="scidocs",
        pool_label="canonical",
        construction="pre_pool_minmax",
        regime="ms1",
    )
    check(
        "scidocs_ms1_post_pool_mean_edges",
        153.9,
        float(post_row["mean_edges"]),
        results,
        tol=TOL_1DP,
    )
    check(
        "scidocs_ms1_pre_pool_mean_edges", 154.1, float(pre_row["mean_edges"]), results, tol=TOL_1DP
    )

    # The manuscript's Jaccard claim is about the MEAN removed-edge overlap
    # per (dataset, pool, regime) cell, not the raw per-query values (a
    # single query can legitimately score 0.0 if only one construction
    # removed any edge for it, e.g. one side needed no repair).
    overlap = load_csv("pre_post_normalization_removed_edge_overlap.csv")
    by_cell: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for r in overlap:
        by_cell[(r["dataset"], r["pool_label"], r["regime"])].append(
            float(r["removed_edge_jaccard"])
        )
    cell_means = [sum(vals) / len(vals) for vals in by_cell.values()]
    check("removed_edge_jaccard_cell_mean_min", 0.748, min(cell_means), results, tol=TOL_1DP)
    check("removed_edge_jaccard_cell_mean_max", 1.00, max(cell_means), results, tol=TOL_1DP)

    ms2_summary = load_csv("ms2_sparsity_summary.csv")
    densities = [float(r["mean_density"]) for r in ms2_summary]
    edges = [float(r["mean_n_edges"]) for r in ms2_summary]
    check("ms2_density_min", 0.013, min(densities), results, tol=TOL_1DP)
    check("ms2_density_max", 0.27, max(densities), results, tol=TOL_1DP)
    check("ms2_edges_min", 21, min(edges), results, tol=TOL_ROUND)
    check("ms2_edges_max", 191, max(edges), results, tol=TOL_ROUND)
    total_ms2_queries = sum(int(r["n_queries"]) for r in ms2_summary)
    check("ms2_total_dataset_query_pool_cells", 684, total_ms2_queries, results)
    ms2_per_query = load_csv("ms2_sparsity_per_query.csv")
    max_scc_ms2 = max(int(r["largest_scc"]) for r in ms2_per_query)
    check("ms2_max_observed_scc", 1, max_scc_ms2, results)

    tfidf = load_csv("tfidf_validation_per_query.csv")
    jac_vals = [float(r["topk_jaccard"]) for r in tfidf]
    pearson_vals = [float(r["score_pearson_on_common"]) for r in tfidf]
    agree_vals = [float(r["directional_agreement_rate"]) for r in tfidf]
    check("tfidf_validation_jaccard_min", 1.0, min(jac_vals), results)
    check("tfidf_validation_pearson_min", 0.9999, min(pearson_vals), results)
    check("tfidf_validation_agreement_min", 1.0, min(agree_vals), results)

    coverage = load_csv("coverage_aggregate.csv")
    minilm_canonical = [
        float(r["mean_coverage_fraction"])
        for r in coverage
        if r["pool_label"] == "canonical" and r["ranker"] == "minilm"
    ]
    lexical_canonical = [
        float(r["mean_coverage_fraction"])
        for r in coverage
        if r["pool_label"] == "canonical" and r["ranker"] in ("bm25", "tfidf")
    ]
    check("minilm_coverage_min_pct", 44, min(minilm_canonical) * 100, results, tol=TOL_ROUND)
    check("minilm_coverage_max_pct", 71, max(minilm_canonical) * 100, results, tol=TOL_ROUND)
    check("lexical_coverage_min_pct", 75, min(lexical_canonical) * 100, results, tol=TOL_ROUND)
    check("lexical_coverage_max_pct", 100, max(lexical_canonical) * 100, results, tol=TOL_ROUND)

    all_ok = all(r["match"] for r in results)
    lines = ["# Task 3 Claim-to-Evidence Audit", ""]
    for r in results:
        status = "PASS" if r["match"] else "FAIL"
        lines.append(f"- [{status}] {r['claim']}: claimed={r['claimed']} actual={r['actual']:.6f}")
    lines.append("")
    overall = "ALL CLAIMS VERIFIED" if all_ok else "MISMATCHES FOUND"
    lines.append(f"Overall: {overall} ({len(results)} checks)")
    (VALIDATION / "claim_to_evidence_audit.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    (VALIDATION / "claim_to_evidence_audit.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print("\n".join(lines))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
