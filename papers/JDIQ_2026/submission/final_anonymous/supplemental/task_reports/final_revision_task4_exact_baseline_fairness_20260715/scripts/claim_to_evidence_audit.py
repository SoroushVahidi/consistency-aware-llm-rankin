#!/usr/bin/env python3
"""Verify every numeric claim added to main.tex in Task 4 against the CSV/
JSON tables that produced it."""

from __future__ import annotations

import csv
import json
from pathlib import Path

REPO_ROOT = Path("")
TASK4_ROOT = REPO_ROOT / "reports/final_revision_task4_exact_baseline_fairness_20260715"
TABLES = TASK4_ROOT / "tables"
VALIDATION = TASK4_ROOT / "validation"
TOL = 5e-3
TOL_1DP = 0.06
TOL_ROUND = 1.0


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

    # Section 2/3: exact-repaired vs unrepaired
    canonical_stats = load_csv("exact_canonical_family_statistics.csv")
    larger_stats = load_csv("exact_larger_pool_family_statistics.csv")
    check("exact_canonical_family_size", 36, len(canonical_stats), results)
    check(
        "exact_canonical_family_n_significant",
        0,
        sum(1 for r in canonical_stats if r["holm_significant_at_0.05"] == "True"),
        results,
    )
    check("exact_larger_pool_family_size", 56, len(larger_stats), results)
    check(
        "exact_larger_pool_family_n_significant",
        0,
        sum(1 for r in larger_stats if r["holm_significant_at_0.05"] == "True"),
        results,
    )

    solver_rows = load_csv("exact_repaired_vs_unrepaired_solver_status.csv")
    canonical_solver = [r for r in solver_rows if r["family"] == "canonical"]
    check(
        "exact_canonical_all_proven_optimal",
        1.0,
        1.0 if all(r["proven_optimal"] == "True" for r in canonical_solver) else 0.0,
        results,
    )
    times = [float(r["time_s"]) for r in canonical_solver]
    check(
        "exact_canonical_mean_solve_time_ms",
        18.14,
        (sum(times) / len(times)) * 1000,
        results,
        tol=TOL_ROUND,
    )
    check("exact_canonical_max_solve_time_ms", 61.25, max(times) * 1000, results, tol=TOL_ROUND)

    three_way = load_csv("three_way_unrepaired_greedy_exact.csv")
    n_reversals = sum(1 for r in three_way if r["exact_reverses_greedy_sign"] == "True")
    check("three_way_n_cells", 36, len(three_way), results)
    check("three_way_n_sign_reversals", 0, n_reversals, results)

    # Section 4/5: baseline pool fairness
    primary_targeted = load_csv("baseline_targeted_tests_primary_canonical.csv")
    check("primary_targeted_family_size", 8, len(primary_targeted), results)
    check(
        "primary_targeted_n_significant",
        0,
        sum(1 for r in primary_targeted if r["holm_significant_at_0.05"] == "True"),
        results,
    )
    all_pools = load_csv("baseline_targeted_tests_all_pools.csv")
    secondary_significant = [
        r
        for r in all_pools
        if r["family_tag"] == "pool_neutral_round_robin_union"
        and r["holm_significant_at_0.05"] == "True"
    ]
    check("secondary_neutral_pool_n_significant", 1, len(secondary_significant), results)
    if secondary_significant:
        row = secondary_significant[0]
        check(
            "secondary_significant_dataset_is_fiqa",
            1.0,
            1.0 if row["dataset"] == "fiqa" else 0.0,
            results,
        )
        check(
            "secondary_significant_mean_delta",
            0.014,
            float(row["mean_delta"]),
            results,
            tol=TOL_1DP,
        )
        check(
            "secondary_significant_holm_p",
            0.013,
            float(row["holm_adjusted_pvalue"]),
            results,
            tol=TOL_1DP,
        )

    # Table values quoted verbatim in tab:pool-fairness
    canon_by_key = {(r["dataset"], r["baseline_method"]): r for r in primary_targeted}
    table_claims = {
        ("scidocs", "rrf"): (-0.0066, 0.625),
        ("scidocs", "combsum"): (-0.0099, 0.625),
        ("fiqa", "rrf"): (0.0141, 0.058),
        ("fiqa", "combsum"): (0.0135, 0.342),
        ("hotpotqa", "rrf"): (-0.0197, 0.625),
        ("hotpotqa", "combsum"): (0.0045, 0.625),
        ("bright", "rrf"): (0.0137, 0.342),
        ("bright", "combsum"): (0.025, 0.198),
    }
    neutral_by_key = {
        (r["dataset"], r["baseline_method"]): r
        for r in all_pools
        if r["family_tag"] == "pool_neutral_round_robin_union"
    }
    neutral_table_claims = {
        ("scidocs", "rrf"): (-0.0058, 0.863),
        ("scidocs", "combsum"): (-0.0051, 1.000),
        ("fiqa", "rrf"): (0.0082, 0.629),
        ("fiqa", "combsum"): (0.014, 0.013),
        ("hotpotqa", "rrf"): (-0.0103, 1.000),
        ("hotpotqa", "combsum"): (0.0127, 1.000),
        ("bright", "rrf"): (0.0043, 1.000),
        ("bright", "combsum"): (0.0123, 1.000),
    }
    for key, (delta, holm_p) in table_claims.items():
        row = canon_by_key[key]
        check(f"table_canonical_delta{key}", delta, float(row["mean_delta"]), results, tol=TOL_1DP)
        check(
            f"table_canonical_holm{key}",
            holm_p,
            float(row["holm_adjusted_pvalue"]),
            results,
            tol=TOL_1DP,
        )
    for key, (delta, holm_p) in neutral_table_claims.items():
        row = neutral_by_key[key]
        check(f"table_neutral_delta{key}", delta, float(row["mean_delta"]), results, tol=TOL_1DP)
        check(
            f"table_neutral_holm{key}",
            holm_p,
            float(row["holm_adjusted_pvalue"]),
            results,
            tol=TOL_1DP,
        )

    # Section 6: Prior vs RRF
    prior_rrf_summary = load_csv("prior_vs_rrf_summary.csv")
    frac_underlying = [float(r["fraction_underlying_scores_differ"]) for r in prior_rrf_summary]
    frac_tiebreak = [
        float(r["fraction_ranking_differs_only_by_tiebreak"]) for r in prior_rrf_summary
    ]
    check(
        "prior_rrf_underlying_differ_min_pct",
        79,
        min(frac_underlying) * 100,
        results,
        tol=TOL_ROUND,
    )
    check(
        "prior_rrf_underlying_differ_max_pct",
        100,
        max(frac_underlying) * 100,
        results,
        tol=TOL_ROUND,
    )
    check("prior_rrf_tiebreak_only_min_pct", 0, min(frac_tiebreak) * 100, results, tol=TOL_ROUND)
    check("prior_rrf_tiebreak_only_max_pct", 3.8, max(frac_tiebreak) * 100, results, tol=TOL_ROUND)

    manifest = json.loads(
        (TASK4_ROOT / "manifests" / "prior_vs_rrf_audit_run_summary.json").read_text()
    )
    check(
        "prior_rrf_overall_match_fraction_pct",
        3.5,
        manifest["overall_exact_match_fraction"] * 100,
        results,
        tol=TOL_1DP,
    )
    check("prior_rrf_total_exact_matches", 12, manifest["total_exact_ranking_matches"], results)

    all_ok = all(r["match"] for r in results)
    lines = ["# Task 4 Claim-to-Evidence Audit", ""]
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
