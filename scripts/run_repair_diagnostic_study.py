"""
run_repair_diagnostic_study.py
================================
Bounded diagnostic: are the rare benefits of consistency repair predictable
from observable (pre-repair) graph properties, or are they isolated and
non-deployable? Reuses the IDENTICAL 120 real-LLM query-graphs used by the
repair-frontier and extraction studies -- makes NO new LLM API calls and
does not modify any previous report.

Reuses (does not duplicate):
  - consistency_ranker.repair_diagnostic (outcome classification, pre-/
    post-repair feature extraction, descriptive/associational analysis
    with Holm-adjusted significance, grouped-CV prediction, predeclared
    decision rule).
  - scripts/run_repair_frontier_pilot.py's ``load_all_units``/
    ``graphs_for_unit`` (imported as ``frontier_lib``) for the exact same
    graph-construction pipeline used by both prior studies.
  - scripts/run_extraction_study.py's ``_pool_size_for_variant`` (imported
    as ``extraction_lib``) rather than redefining the same variant-name ->
    pool-size mapping a third time.
  - scripts/run_multi_provider_repair_pilot.py's ``_atomic_write_json``/
    ``_setup_logging`` (imported transitively).
  - consistency_ranker.repair_selector_mining.checkpoint.FlushWriter for
    all JSONL outputs.

Predeclared decision (see consistency_ranker.repair_diagnostic.decision),
fixed BEFORE inspecting results:
  STABLE_REPAIR_REGIME_FOUND / WEAK_DESCRIPTIVE_PATTERN_ONLY /
  ORACLE_ONLY_NOT_PREDICTABLE / NO_IDENTIFIABLE_REPAIR_REGIME
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

import run_extraction_study as extraction_lib  # noqa: E402
import run_multi_provider_repair_pilot as pilot_lib  # noqa: E402
import run_repair_frontier_pilot as frontier_lib  # noqa: E402

from consistency_ranker.repair_diagnostic import (  # noqa: E402
    ALL_FEATURE_NAMES,
    PRE_REPAIR_FEATURE_NAMES,
    QueryGraphDiagnostic,
    baseline_policies,
    best_real_model,
    compute_feature_associations,
    compute_headroom_gate,
    decide,
    evaluate_predictors,
    evaluate_repair_outcome,
    full_stability_report,
    outcome_group_stats,
    outlier_sensitivity,
    overall_delta_ci,
    subgroup_stability,
)
from consistency_ranker.repair_selector_mining.checkpoint import FlushWriter  # noqa: E402

log = logging.getLogger("repair_diagnostic_study")

_atomic_write_json = pilot_lib._atomic_write_json
_setup_logging = pilot_lib._setup_logging
_pool_size_for_variant = extraction_lib._pool_size_for_variant


def run_evaluation(output_dir: Path) -> list[QueryGraphDiagnostic]:
    """Requirement 1/2/3: classify each query-graph's repair outcome and
    compute pre-/post-repair features, on the SAME graphs the repair-
    frontier and extraction studies used."""
    units = frontier_lib.load_all_units()
    results_writer = FlushWriter(output_dir / "diagnostic_results.jsonl")
    failures_writer = FlushWriter(output_dir / "failures.jsonl")

    results: list[QueryGraphDiagnostic] = []
    try:
        for unit in units:
            relevance_map = unit.get("relevance_map") or {}
            if not relevance_map:
                continue
            pool_size = _pool_size_for_variant(unit["variant"])
            for graph_id, graph in frontier_lib.graphs_for_unit(unit).items():
                key = (unit["dataset"], unit["query_id"], unit["source"], unit["variant"], graph_id)
                unit_key = "|".join(str(k) for k in key)
                try:
                    diag = evaluate_repair_outcome(
                        graph,
                        relevance_map,
                        key=key,
                        dataset=unit["dataset"],
                        query_id=unit["query_id"],
                        provider=graph_id,
                        pool_size=pool_size,
                        provider_prefs=unit["provider_prefs"],
                    )
                except Exception as exc:  # noqa: BLE001 - recorded, not silently swallowed
                    failures_writer.write(
                        {
                            "unit_key": unit_key,
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                        }
                    )
                    continue
                results.append(diag)
                results_writer.write(
                    {
                        "unit_key": unit_key,
                        "dataset": diag.dataset,
                        "query_id": diag.query_id,
                        "provider": diag.provider,
                        "pool_size": diag.pool_size,
                        "ndcg_preserve": diag.ndcg_preserve,
                        "ndcg_repair": diag.ndcg_repair,
                        "delta": diag.delta,
                        "outcome": diag.outcome,
                        "pre_repair": diag.pre_repair.to_dict(),
                        "post_repair": diag.post_repair.to_dict(),
                    }
                )
    finally:
        results_writer.close()
        failures_writer.close()
    return results


def write_association_tables(output_dir: Path, results: list[QueryGraphDiagnostic]) -> dict:
    import csv

    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    group_stats = outcome_group_stats(results)
    delta_ci = overall_delta_ci(results)
    associations = compute_feature_associations(results)
    stability = full_stability_report(results, PRE_REPAIR_FEATURE_NAMES)
    outliers = outlier_sensitivity(results)

    assoc_fieldnames = ["feature", "family", "correlation", "pvalue_raw", "pvalue_holm", "n"]
    with (tables_dir / "FEATURE_ASSOCIATIONS.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=assoc_fieldnames)
        writer.writeheader()
        for a in associations:
            writer.writerow(a.to_dict())

    stability_rows = []
    for feature, dims in stability.items():
        for dimension, groups in dims.items():
            for group_value, stats in groups.items():
                stability_rows.append(
                    {
                        "feature": feature,
                        "dimension": dimension,
                        "group_value": group_value,
                        "n": stats.get("n"),
                        "correlation": stats.get("correlation"),
                        "note": stats.get("note"),
                    }
                )
    with (tables_dir / "FEATURE_STABILITY.csv").open("w", newline="", encoding="utf-8") as fh:
        fieldnames = list(stability_rows[0]) if stability_rows else []
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in stability_rows:
            writer.writerow(row)

    return {
        "outcome_group_stats": group_stats,
        "overall_delta_ci": {
            "method": delta_ci.method,
            "lower": delta_ci.lower,
            "upper": delta_ci.upper,
            "reps": delta_ci.reps,
            "seed": delta_ci.seed,
        },
        "feature_associations": [a.to_dict() for a in associations],
        "outlier_sensitivity": outliers,
    }


def run_prediction_and_decision(results: list[QueryGraphDiagnostic]) -> dict:
    headroom, gate = compute_headroom_gate(results)
    baselines = baseline_policies(results)
    oracle_headroom_mean = baselines["oracle_selection"] - baselines["never_repair"]

    predictor_result = evaluate_predictors(results)

    stability_fraction = 0.0
    stability_detail: dict = {}
    if predictor_result.get("status") == "EVALUATED":
        best_name, _ = best_real_model(predictor_result["models"])
        best_model_result = predictor_result["models"][best_name]
        fractions = {}
        for key_name in ("dataset", "provider", "pool_size"):
            stab = subgroup_stability(best_model_result, key_name=key_name)
            fractions[key_name] = stab["fraction_passing"]
            stability_detail[key_name] = stab
        # Conservative: must be stable across ALL major subgroup dimensions,
        # not just one -- take the minimum fraction across dataset/
        # provider/pool_size, not the mean.
        stability_fraction = min(fractions.values()) if fractions else 0.0

    decision_result = decide(
        headroom_gate_decision=gate.decision,
        oracle_headroom_mean=oracle_headroom_mean,
        predictor_status=predictor_result.get("status", "UNSUPPORTED"),
        models=predictor_result.get("models", {}),
        never_repair_ndcg=baselines["never_repair"],
        stability_pass_fraction=stability_fraction,
    )

    return {
        "headroom": headroom,
        "gate": gate,
        "baselines": baselines,
        "oracle_headroom_mean": oracle_headroom_mean,
        "predictor_result": predictor_result,
        "stability_fraction": stability_fraction,
        "stability_detail": stability_detail,
        "decision_result": decision_result,
    }


def write_final_report(
    output_dir: Path,
    n_query_graphs: int,
    runtime_s: float,
    association_summary: dict,
    prediction_summary: dict,
) -> None:
    decision_result = prediction_summary["decision_result"]
    baselines = prediction_summary["baselines"]
    gate = prediction_summary["gate"]
    predictor_result = prediction_summary["predictor_result"]

    summary = {
        "timestamp": time.time(),
        "runtime_s": runtime_s,
        "n_query_graphs": n_query_graphs,
        "outcome_group_stats": association_summary["outcome_group_stats"],
        "overall_delta_ci": association_summary["overall_delta_ci"],
        "outlier_sensitivity": association_summary["outlier_sensitivity"],
        "feature_associations": association_summary["feature_associations"],
        "headroom_gate_decision": gate.decision,
        "headroom_gate_rationale": gate.rationale,
        "baselines": baselines,
        "oracle_headroom_mean": prediction_summary["oracle_headroom_mean"],
        "predictor_result": predictor_result,
        "stability_fraction": prediction_summary["stability_fraction"],
        "stability_detail": prediction_summary["stability_detail"],
        "decision": decision_result.decision,
        "decision_rationale": decision_result.rationale,
        "decision_conditions": decision_result.conditions,
    }
    _atomic_write_json(output_dir / "FINAL_SUMMARY.json", summary)

    top_associations = sorted(
        association_summary["feature_associations"],
        key=lambda a: (a["pvalue_holm"] if a["pvalue_holm"] is not None else 1.0),
    )[:8]
    assoc_lines = [_association_line(a) for a in top_associations]

    lines = [
        "# Repair-Regime Diagnostic Study -- Final Report",
        "",
        f"Runtime: {runtime_s:.1f}s. Query-graphs evaluated: {n_query_graphs} "
        "(identical set used by the repair-frontier and extraction studies).",
        "",
        "## Predeclared decision",
        "",
        f"**{decision_result.decision}**",
        "",
        decision_result.rationale,
        "",
        "### Gate conditions",
        "",
        "```",
        json.dumps(decision_result.conditions, indent=2),
        "```",
        "",
        "## Outcome breakdown",
        "",
        "```",
        json.dumps(association_summary["outcome_group_stats"], indent=2),
        "```",
        "",
        _delta_ci_text(association_summary["overall_delta_ci"]),
        "",
        "## Top pre-/post-repair feature associations (by Holm-adjusted significance)",
        "",
        "```",
        *assoc_lines,
        "```",
        "",
        "See `tables/FEATURE_ASSOCIATIONS.csv` for the full list (all "
        f"{len(ALL_FEATURE_NAMES)} features, pre- and post-repair clearly tagged) and "
        "`tables/FEATURE_STABILITY.csv` for stability across datasets/providers/pool sizes.",
        "",
        "## Outlier sensitivity",
        "",
        f"Mean delta: {association_summary['outlier_sensitivity']['mean_delta_full']:.5f}; "
        f"excluding the single largest delta: "
        f"{association_summary['outlier_sensitivity']['mean_delta_excluding_top_n']}.",
        "",
        "## Oracle headroom gate (never-repair vs. always-repair, 2-action)",
        "",
        f"**{gate.decision}**. {gate.rationale}",
        "",
        f"Baselines (mean nDCG): never_repair={baselines['never_repair']:.6f}, "
        f"always_repair={baselines['always_repair']:.6f}, "
        f"random_selection={baselines['random_selection']:.6f}, "
        f"oracle_selection={baselines['oracle_selection']:.6f}.",
        "",
        "## Grouped-CV prediction from pre-repair features only",
        "",
        _predictor_summary_text(predictor_result),
        "",
        f"Subgroup stability (best model, minimum pass-fraction across dataset/provider/"
        f"pool_size): {prediction_summary['stability_fraction']:.0%}.",
        "",
        "## Are the rare benefits of consistency repair predictable, "
        "or isolated and non-deployable?",
        "",
        _bottom_line_text(decision_result.decision),
        "",
        "## Files in this directory",
        "",
        "- `RUN_CONFIG.json`, `diagnostic_results.jsonl`, `failures.jsonl`",
        "- `tables/FEATURE_ASSOCIATIONS.csv`, `tables/FEATURE_STABILITY.csv`",
        "- `FINAL_SUMMARY.json` (this report's machine-readable twin)",
        "",
    ]
    (output_dir / "FINAL_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def _association_line(a: dict) -> str:
    base = (
        f"- {a['feature']} ({a['family']}): r={a['correlation']:.3f}, "
        f"raw p={a['pvalue_raw']:.4f}"
    )
    if a["pvalue_holm"] is not None:
        return f"{base}, Holm p={a['pvalue_holm']:.4f}"
    return base


def _delta_ci_text(delta_ci: dict) -> str:
    return (
        f"Overall mean-delta bootstrap 95% CI: [{delta_ci['lower']:.5f}, {delta_ci['upper']:.5f}]."
    )


def _predictor_summary_text(predictor_result: dict) -> str:
    if predictor_result.get("status") != "EVALUATED":
        return f"Status: **{predictor_result.get('status')}**. {predictor_result.get('reason', '')}"
    lines = [f"n_rows={predictor_result['n_rows']}, n_groups={predictor_result['n_groups']}", ""]
    for name, m in predictor_result["models"].items():
        policy_ndcg = m.get("policy_mean_ndcg", float("nan"))
        lines.append(
            f"- {name}: balanced_accuracy={m['mean_balanced_accuracy']:.3f} "
            f"({m['n_folds_used']} folds), policy_mean_ndcg={policy_ndcg:.5f}"
        )
    return "\n".join(lines)


def _bottom_line_text(decision: str) -> str:
    if decision == "STABLE_REPAIR_REGIME_FOUND":
        return (
            "Predictable: a simple, pre-repair-feature-only rule reliably identifies when "
            "repair helps, survives grouped validation, and beats never-repairing by a "
            "practically meaningful and stable margin -- this is a deployable regime."
        )
    if decision == "WEAK_DESCRIPTIVE_PATTERN_ONLY":
        return (
            "Neither fully predictable nor fully isolated: a descriptive association between "
            "some pre-repair feature(s) and repair benefit exists, but it does not clear the "
            "full deployability bar (validation margin, policy improvement, subgroup "
            "stability, or practical significance). Not yet actionable."
        )
    if decision == "ORACLE_ONLY_NOT_PREDICTABLE":
        return (
            "Isolated, not deployable: repair genuinely helps on some queries (oracle "
            "headroom is meaningful), but no simple, interpretable, pre-repair-feature-based "
            "rule identifies WHICH queries in advance. The benefit cannot currently be "
            "captured without oracle (post-hoc) knowledge."
        )
    return (
        "Isolated and non-deployable, more fundamentally: there is no meaningful repair "
        "benefit to identify a regime for in the first place on this data -- consistent "
        "with this research thread's other negative results."
    )


def run_config_snapshot() -> dict:
    return {
        "pre_repair_feature_names": PRE_REPAIR_FEATURE_NAMES,
        "meaningful_threshold": 0.01,
        "sources": [str(frontier_lib.POOL6_DIR), str(frontier_lib.REVIEWER_CONCERNS_DIR)],
    }


def run_program(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(output_dir / "RUN_CONFIG.json", run_config_snapshot())

    t0 = time.time()
    results = run_evaluation(output_dir)
    log.info("Evaluated %d query-graphs", len(results))

    association_summary = write_association_tables(output_dir, results)
    prediction_summary = run_prediction_and_decision(results)

    runtime_s = time.time() - t0
    write_final_report(output_dir, len(results), runtime_s, association_summary, prediction_summary)

    return {
        "n_query_graphs": len(results),
        "runtime_s": runtime_s,
        "headroom_gate_decision": prediction_summary["gate"].decision,
        "predictor_status": prediction_summary["predictor_result"].get("status"),
        "decision": prediction_summary["decision_result"].decision,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    run_tag = f"run_{int(time.time())}"
    log_path = _setup_logging(args.output_dir, run_tag)
    log.info("Logging to %s", log_path)

    result = run_program(args.output_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
