#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path
import statistics


REPO_ROOT = Path("")
TASK1_ROOT = REPO_ROOT / "reports/final_revision_task1_pool_cutoff_20260715"
TASK2_ROOT = REPO_ROOT / "reports/final_revision_task2_statistical_power_20260715"
TABLES = TASK2_ROOT / "tables"
VALIDATION = TASK2_ROOT / "validation"


def load_csv(name: str) -> list[dict[str, str]]:
    with (TABLES / name).open(newline="") as handle:
        return list(csv.DictReader(handle))


def find_row(rows: list[dict[str, str]], **match: str) -> dict[str, str]:
    for row in rows:
        if all(row[key] == value for key, value in match.items()):
            return row
    raise KeyError(f"No row matching {match}")


def main() -> None:
    VALIDATION.mkdir(parents=True, exist_ok=True)

    task1_verification = json.loads(
        (TASK1_ROOT / "validation/pool_cutoff_verification.json").read_text()
    )
    summary = json.loads(
        (TASK2_ROOT / "manifests/task2_analysis_summary.json").read_text()
    )
    interval_rows = load_csv("interval_method_comparison.csv")
    mde_rows = load_csv("mde_per_cell.csv")
    eligibility_rows = load_csv("qrels_reference_eligibility_summary.csv")
    cross_protocol_rows = load_csv("cross_protocol_statistical_tests.csv")
    baseline_rows = load_csv("baseline_claim_audit.csv")

    active_final = [
        row
        for row in mde_rows
        if row["table_kind"] == "final" and row["regime"] == "ms1" and row["metric"] == "ndcg"
    ]
    active_final_abs_means = [abs(float(row["mean_delta"])) for row in active_final]
    active_final_mde = [float(row["mde_normal_holm_active_ms1_power80"]) for row in active_final]
    canonical_active = [
        row
        for row in mde_rows
        if row["table_kind"] == "canonical" and row["regime"] == "ms1" and row["metric"] == "ndcg"
    ]
    canonical_abs_means = [abs(float(row["mean_delta"])) for row in canonical_active]
    canonical_mde = [float(row["mde_normal_holm_active_ms1_power80"]) for row in canonical_active]

    claims = [
        {
            "claim": "Task 1 larger-pool rerun changes top-k membership when P>k.",
            "value": f"{task1_verification['claims']['p_gt_k_membership_change_rate']:.6f}",
            "evidence": "reports/final_revision_task1_pool_cutoff_20260715/validation/pool_cutoff_verification.json",
        },
        {
            "claim": "Task 2 final full and active ms1 families have zero Holm/BH/BY-significant repaired-vs-unrepaired nDCG cells.",
            "value": {
                "full_holm": summary["full_family_holm_significant"],
                "full_bh": summary["full_family_bh_significant"],
                "full_by": summary["full_family_by_significant"],
                "active_holm": summary["active_ms1_holm_significant"],
                "active_bh": summary["active_ms1_bh_significant"],
                "active_by": summary["active_ms1_by_significant"],
            },
            "evidence": "reports/final_revision_task2_statistical_power_20260715/manifests/task2_analysis_summary.json",
        },
        {
            "claim": "Canonical SciDocs ms1 Copeland graph interval sensitivity changes with bootstrap construction but not the multiplicity conclusion.",
            "value": {
                "basic_low": float(find_row(interval_rows, source="canonical", dataset="scidocs", pair_name="copeland_graph")["basic_low"]),
                "bca_low": float(find_row(interval_rows, source="canonical", dataset="scidocs", pair_name="copeland_graph")["bca_low"]),
            },
            "evidence": "reports/final_revision_task2_statistical_power_20260715/tables/interval_method_comparison.csv",
        },
        {
            "claim": "FiQA and BRIGHT canonical pools have no eligible judged different-grade candidate pairs under the final qrels-reference rule.",
            "value": {
                "fiqa_zero_pair_rate": float(find_row(eligibility_rows, dataset="fiqa", config_id="pool20_ndcg20")["fraction_queries_with_zero_eligible_pairs"]),
                "bright_zero_pair_rate": float(find_row(eligibility_rows, dataset="bright", config_id="pool20_ndcg20")["fraction_queries_with_zero_eligible_pairs"]),
            },
            "evidence": "reports/final_revision_task2_statistical_power_20260715/tables/qrels_reference_eligibility_summary.csv",
        },
        {
            "claim": "The active larger-pool ms1 family is underpowered for effects as small as the typical observed mean delta.",
            "value": {
                "median_abs_observed_mean": statistics.median(active_final_abs_means),
                "median_holm80_mde": statistics.median(active_final_mde),
            },
            "evidence": "reports/final_revision_task2_statistical_power_20260715/tables/mde_per_cell.csv",
        },
        {
            "claim": "The original canonical active ms1 design had similar observed means but lower, still nontrivial Holm-adjusted MDE thresholds.",
            "value": {
                "median_abs_observed_mean": statistics.median(canonical_abs_means),
                "median_holm80_mde": statistics.median(canonical_mde),
            },
            "evidence": "reports/final_revision_task2_statistical_power_20260715/tables/mde_per_cell.csv",
        },
        {
            "claim": "Cross-protocol dependence-robust sensitivity does not preserve the lone active-family negative FiQA hit seen under Holm/BH.",
            "value": {
                "holm": float(find_row(cross_protocol_rows, dataset="fiqa", protocol="ablation_raw_fixed", regime="ms1", pair_name="copeland_hybrid")["cross_protocol_active_ms1_family_holm"]),
                "bh": float(find_row(cross_protocol_rows, dataset="fiqa", protocol="ablation_raw_fixed", regime="ms1", pair_name="copeland_hybrid")["cross_protocol_active_ms1_family_bh"]),
                "by": float(find_row(cross_protocol_rows, dataset="fiqa", protocol="ablation_raw_fixed", regime="ms1", pair_name="copeland_hybrid")["cross_protocol_active_ms1_family_by"]),
            },
            "evidence": "reports/final_revision_task2_statistical_power_20260715/tables/cross_protocol_statistical_tests.csv",
        },
        {
            "claim": "Baseline comparisons remain descriptive only.",
            "value": sorted({row["claim_type"] for row in baseline_rows}),
            "evidence": "reports/final_revision_task2_statistical_power_20260715/tables/baseline_claim_audit.csv",
        },
    ]

    markdown_lines = [
        "# Claim-to-Evidence Audit",
        "",
        "| Claim | Value | Evidence |",
        "| --- | --- | --- |",
    ]
    for item in claims:
        markdown_lines.append(
            f"| {item['claim']} | `{json.dumps(item['value'], sort_keys=True)}` | `{item['evidence']}` |"
        )

    (VALIDATION / "claim_to_evidence_audit.md").write_text("\n".join(markdown_lines) + "\n")
    print("\n".join(markdown_lines))


if __name__ == "__main__":
    main()
