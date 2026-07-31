"""
run_real_llm_clustered_reanalysis.py
======================================
Repo Stage 3 (2026-07-30): query-clustered re-analysis of the three real-
multi-provider-LLM studies (repair_frontier, extraction_study,
repair_diagnostic). Makes NO external API calls, collects NO new
judgments, adds NO new providers/queries/repair-methods/extractors --
re-derives every number below from data already stored in the repository.

Outputs (see write_all_outputs): analysis_population_manifest.csv,
query_level_aggregates.csv, repair_frontier_clustered_results.csv,
extraction_clustered_results.csv, repair_diagnostic_clustered_results.csv,
multiple_comparison_families.csv, per_query_effects.csv,
reproducibility_manifest.json.

The conclusion-change matrix and the prose protocol/report documents are
written separately (they require human-authored comparison against the
original reports' exact wording, not just numeric recomputation).
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from consistency_ranker.provenance import (  # noqa: E402
    CanonicalOutputExistsError,
    collect_provenance,
    protect_canonical_output,
)
from consistency_ranker.real_llm_reanalysis import (  # noqa: E402
    diagnostic_reanalysis,
    extraction_reanalysis,
    frontier_reanalysis,
    population,
)

SEED = 13
REPS = 10_000


def write_population_manifest(output_dir: Path) -> list[dict]:
    rows = population.build_population_manifest()
    header = [
        "study", "source_file", "unit_key", "independence_cluster", "query_id", "dataset",
        "provider", "model", "construction_variant", "pool_size", "repair_method",
        "extractor", "diagnostic_configuration", "is_cyclic", "incumbent_ndcg",
    ]
    with (output_dir / "analysis_population_manifest.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})
    return rows


def write_query_level_aggregates(output_dir: Path, diag_rows, extr_rows, front_outcomes) -> None:
    header = ["study", "query_id", "dataset", "n_rows", "mean_outcome", "outcome_definition"]
    out_rows = []
    from consistency_ranker.statistical_inference import compute_cluster_means

    diag_deltas = [r["delta"] for r in diag_rows]
    diag_q = [r["query_id"] for r in diag_rows]
    agg = compute_cluster_means(diag_deltas, diag_q)
    ds_by_q = {r["query_id"]: r["dataset"] for r in diag_rows}
    for qid, mean, size in zip(agg.cluster_ids, agg.cluster_means, agg.cluster_sizes):
        out_rows.append(
            {
                "study": "repair_diagnostic", "query_id": qid, "dataset": ds_by_q[qid],
                "n_rows": size, "mean_outcome": mean,
                "outcome_definition": "ndcg_repair - ndcg_preserve",
            }
        )

    for extractor in extraction_reanalysis.FULL_COMPARISON_FAMILY:
        deltas = extraction_reanalysis.per_extractor_deltas(extr_rows, extractor)
        q = [r["query_id"] for r in extr_rows]
        agg = compute_cluster_means(deltas, q)
        ds_by_q2 = {r["query_id"]: r["dataset"] for r in extr_rows}
        for qid, mean, size in zip(agg.cluster_ids, agg.cluster_means, agg.cluster_sizes):
            out_rows.append(
                {
                    "study": f"extraction_study[{extractor}]", "query_id": qid,
                    "dataset": ds_by_q2[qid], "n_rows": size, "mean_outcome": mean,
                    "outcome_definition": f"ndcg[{extractor}] - incumbent_ndcg",
                }
            )

    for label, key in [
        ("repair_frontier[oracle_full_frontier_upper_bound]", "delta_oracle_full_frontier"),
        ("repair_frontier[whole_graph_repair]", "delta_whole_graph_repair"),
        ("repair_frontier[best_alt_extraction]", "delta_best_alt_extraction"),
    ]:
        deltas = [o[key] for o in front_outcomes]
        q = [o["query_id"] for o in front_outcomes]
        agg = compute_cluster_means(deltas, q)
        ds_by_q3 = {o["query_id"]: o["dataset"] for o in front_outcomes}
        for qid, mean, size in zip(agg.cluster_ids, agg.cluster_means, agg.cluster_sizes):
            out_rows.append(
                {"study": label, "query_id": qid, "dataset": ds_by_q3[qid],
                 "n_rows": size, "mean_outcome": mean, "outcome_definition": key}
            )

    with (output_dir / "query_level_aggregates.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)


def write_frontier_results(output_dir: Path, outcomes, clustered) -> None:
    header = [
        "unit_key", "dataset", "query_id", "incumbent_ndcg", "best_ndcg_oracle_full_frontier",
        "best_candidate_id_oracle_full_frontier", "whole_graph_ndcg", "best_alt_extraction_ndcg",
        "delta_oracle_full_frontier", "delta_whole_graph_repair", "delta_best_alt_extraction",
        "n_candidates_evaluated",
    ]
    with (output_dir / "repair_frontier_clustered_results.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for o in outcomes:
            w.writerow({k: o[k] for k in header})
    (output_dir / "repair_frontier_clustered_summary.json").write_text(
        json.dumps(clustered, indent=2, default=str)
    )


def write_extraction_results(output_dir: Path, result) -> None:
    header = [
        "extractor", "n_rows", "n_clusters", "mean_of_cluster_means",
        "cluster_bootstrap_ci_lower", "cluster_bootstrap_ci_upper",
        "cluster_bootstrap_frac_gt_zero",
        "exact_sign_flip_pvalue_raw", "exact_sign_flip_pvalue_holm", "holm_significant_at_0.05",
        "n_query_level_wins", "n_query_level_losses", "n_query_level_ties",
        "direction_consistent_across_queries",
    ]
    with (output_dir / "extraction_clustered_results.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for extractor, d in result["per_extractor"].items():
            row = {"extractor": extractor, **{k: d[k] for k in header if k != "extractor"}}
            w.writerow(row)


def write_diagnostic_results(output_dir: Path, overall, assoc, cv_status) -> None:
    header = [
        "feature", "family", "n_clusters", "pearson_r", "pvalue", "pvalue_holm",
        "holm_significant_at_0.05", "method",
    ]
    with (output_dir / "repair_diagnostic_clustered_results.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for feature, d in assoc["per_feature"].items():
            w.writerow({"feature": feature, **{k: d[k] for k in header if k != "feature"}})
    (output_dir / "repair_diagnostic_overall_delta.json").write_text(
        json.dumps(overall, indent=2, default=str)
    )
    (output_dir / "repair_diagnostic_grouped_cv_status.json").write_text(
        json.dumps(cv_status, indent=2, default=str)
    )


def write_multiple_comparison_families(output_dir: Path, extraction_result, diag_assoc) -> None:
    rows = [
        {
            "family_name": "extraction_study_vs_incumbent",
            "n_tests": extraction_result["family_size"],
            "members": ";".join(extraction_result["family_members"]),
            "correction_method": "Holm (step-down, exact per-cluster sign-flip p-values)",
            "n_significant_before_correction": sum(
                1 for d in extraction_result["per_extractor"].values()
                if d["exact_sign_flip_pvalue_raw"] is not None
                and d["exact_sign_flip_pvalue_raw"] < 0.05
            ),
            "n_significant_after_correction": sum(
                1 for d in extraction_result["per_extractor"].values()
                if d["holm_significant_at_0.05"]
            ),
        },
        {
            "family_name": "repair_diagnostic_feature_associations",
            "n_tests": diag_assoc["n_features"],
            "members": ";".join(diag_assoc["per_feature"].keys()),
            "correction_method": "Holm (step-down, exact/Monte-Carlo "
            "per-cluster permutation p-values)",
            "n_significant_before_correction": sum(
                1 for d in diag_assoc["per_feature"].values()
                if d["pvalue"] is not None and d["pvalue"] < 0.05
            ),
            "n_significant_after_correction": sum(
                1 for d in diag_assoc["per_feature"].values() if d["holm_significant_at_0.05"]
            ),
        },
        {
            "family_name": "repair_frontier_comparisons",
            "n_tests": 3,
            "members": "oracle_full_frontier_upper_bound;whole_graph_repair;best_alt_extraction",
            "correction_method": "None applied (3 conceptually distinct diagnostics reported "
            "separately, not intended as one inferential family per the original study's own "
            "framing -- see canonical_analysis_protocol.md)",
            "n_significant_before_correction": "",
            "n_significant_after_correction": "",
        },
    ]
    header = list(rows[0].keys())
    with (output_dir / "multiple_comparison_families.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_per_query_effects(output_dir: Path, diag_rows, extr_rows, front_outcomes) -> None:
    """One row per (study, comparison, query_id): the complete per-query
    effect table the protocol requires, independent of any CI/test."""
    from consistency_ranker.statistical_inference import compute_cluster_means

    header = ["study", "comparison", "dataset", "query_id", "n_rows", "mean_effect"]
    rows = []

    diag_deltas = [r["delta"] for r in diag_rows]
    diag_q = [r["query_id"] for r in diag_rows]
    ds_by_q = {r["query_id"]: r["dataset"] for r in diag_rows}
    agg = compute_cluster_means(diag_deltas, diag_q)
    for qid, mean, size in zip(agg.cluster_ids, agg.cluster_means, agg.cluster_sizes):
        rows.append({"study": "repair_diagnostic", "comparison": "repair_vs_preserve",
                     "dataset": ds_by_q[qid], "query_id": qid, "n_rows": size, "mean_effect": mean})

    for extractor in extraction_reanalysis.FULL_COMPARISON_FAMILY:
        deltas = extraction_reanalysis.per_extractor_deltas(extr_rows, extractor)
        q = [r["query_id"] for r in extr_rows]
        ds_by_q2 = {r["query_id"]: r["dataset"] for r in extr_rows}
        agg2 = compute_cluster_means(deltas, q)
        for qid, mean, size in zip(agg2.cluster_ids, agg2.cluster_means, agg2.cluster_sizes):
            rows.append({
                "study": "extraction_study", "comparison": f"{extractor}_vs_incumbent",
                "dataset": ds_by_q2[qid], "query_id": qid, "n_rows": size, "mean_effect": mean,
            })

    for label, key in [
        ("oracle_full_frontier_upper_bound", "delta_oracle_full_frontier"),
        ("whole_graph_repair", "delta_whole_graph_repair"),
        ("best_alt_extraction", "delta_best_alt_extraction"),
    ]:
        deltas = [o[key] for o in front_outcomes]
        q = [o["query_id"] for o in front_outcomes]
        ds_by_q3 = {o["query_id"]: o["dataset"] for o in front_outcomes}
        agg3 = compute_cluster_means(deltas, q)
        for qid, mean, size in zip(agg3.cluster_ids, agg3.cluster_means, agg3.cluster_sizes):
            rows.append({
                "study": "repair_frontier", "comparison": label,
                "dataset": ds_by_q3[qid], "query_id": qid, "n_rows": size, "mean_effect": mean,
            })

    with (output_dir / "per_query_effects.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_reproducibility_manifest(output_dir: Path, pop_summary: dict) -> None:
    provenance = collect_provenance(
        generator_script="scripts/run_real_llm_clustered_reanalysis.py",
        seeds={"bootstrap_seed": SEED},
        independence_cluster_count=pop_summary.get("total_unique_queries_overall"),
        input_paths=population.ANALYSIS_INPUT_PATHS,
        config={
            "bootstrap_replicates": REPS,
            "ci_method": "percentile, cluster (block) bootstrap over query_id clusters",
            "paired_test_method": "exact sign-flip permutation (2**n_clusters enumeration) for "
            "mean deltas; exact permutation (n_clusters! enumeration, n<=8) for correlations",
            "multiple_comparison_correction": "Holm step-down",
        },
        output_paths=[
            output_dir / "analysis_population_manifest.csv",
            output_dir / "query_level_aggregates.csv",
            output_dir / "repair_frontier_clustered_results.csv",
            output_dir / "extraction_clustered_results.csv",
            output_dir / "repair_diagnostic_clustered_results.csv",
            output_dir / "multiple_comparison_families.csv",
            output_dir / "per_query_effects.csv",
        ],
        extra={
            "population_summary": pop_summary,
            "no_external_api_calls": True,
            "no_new_judgments_collected": True,
            "no_new_providers_queries_repair_methods_or_extractors_added": True,
        },
    )
    (output_dir / "reproducibility_manifest.json").write_text(
        json.dumps(provenance, indent=2, default=str)
    )


def run(output_dir: Path, *, allow_overwrite: bool = False) -> dict:
    protect_canonical_output(output_dir, allow_overwrite=allow_overwrite)
    output_dir.mkdir(parents=True, exist_ok=True)

    pop_rows = write_population_manifest(output_dir)
    pop_summary = population.population_summary(pop_rows)

    diag_rows = diagnostic_reanalysis.load_rows()
    extr_rows = extraction_reanalysis.load_rows()
    front_outcomes = frontier_reanalysis.reconstruct_per_unit_outcomes()
    front_check = frontier_reanalysis.verify_reconstruction_matches_original(front_outcomes)
    front_clustered = frontier_reanalysis.clustered_analysis(front_outcomes)

    extr_result = extraction_reanalysis.clustered_analysis(extr_rows)
    diag_overall = diagnostic_reanalysis.overall_delta_clustered(diag_rows)
    diag_assoc = diagnostic_reanalysis.feature_associations_clustered(diag_rows)
    diag_cv = diagnostic_reanalysis.grouped_cv_status()

    write_query_level_aggregates(output_dir, diag_rows, extr_rows, front_outcomes)
    write_frontier_results(output_dir, front_outcomes, front_clustered)
    write_extraction_results(output_dir, extr_result)
    write_diagnostic_results(output_dir, diag_overall, diag_assoc, diag_cv)
    write_multiple_comparison_families(output_dir, extr_result, diag_assoc)
    write_per_query_effects(output_dir, diag_rows, extr_rows, front_outcomes)
    write_reproducibility_manifest(output_dir, pop_summary)

    (output_dir / "frontier_reconstruction_verification.json").write_text(
        json.dumps(front_check, indent=2)
    )

    return {
        "n_population_rows": len(pop_rows),
        "population_summary": pop_summary,
        "frontier_reconstruction_check": front_check,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--allow-overwrite", action="store_true",
        help="Permit writing into a non-empty output directory (default: refuse).",
    )
    args = parser.parse_args()
    try:
        result = run(args.output_dir, allow_overwrite=args.allow_overwrite)
    except CanonicalOutputExistsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, indent=2, default=str))
    sys.stdout.flush()
