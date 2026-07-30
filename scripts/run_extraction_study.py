"""
run_extraction_study.py
========================
Bounded extraction-vs-repair study: does preference-graph EXTRACTION method
choice (not repair) explain the ranking gains the repair-frontier program
found? Reuses the IDENTICAL 120 real-LLM query-graphs (same graph
construction; only extraction varies) via
scripts/run_repair_frontier_pilot.py's ``load_all_units``/``graphs_for_unit``
-- makes NO new LLM API calls and does not modify any previous report.

Reuses (does not duplicate):
  - consistency_ranker.extraction_study (extractor registry, evaluation,
    grouped-CV selection, predeclared decision rule).
  - scripts/run_repair_frontier_pilot.py's ``load_all_units``/
    ``graphs_for_unit`` (imported as ``frontier_lib``) for the exact same
    graph-construction pipeline used by the repair-frontier program.
  - scripts/run_multi_provider_repair_pilot.py's ``_atomic_write_json``/
    ``_setup_logging`` (imported transitively via ``frontier_lib``).
  - consistency_ranker.repair_selector_mining.checkpoint.FlushWriter for all
    JSONL outputs.

Predeclared decision (see consistency_ranker.extraction_study.decision),
fixed BEFORE inspecting results:
  EXTRACTION_IMPROVES_RANKING / SELECTIVE_EXTRACTION_ONLY /
  ORACLE_ONLY_NOT_DEPLOYABLE / NO_MEANINGFUL_EXTRACTION_GAIN
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

import run_multi_provider_repair_pilot as pilot_lib  # noqa: E402
import run_repair_frontier_pilot as frontier_lib  # noqa: E402

from consistency_ranker.extraction_study import (  # noqa: E402
    EXTRACTORS,
    INCUMBENT_NAME,
    compute_extractor_stats,
    decide,
    evaluate_selection,
    evaluate_unit_graph,
    full_breakdowns,
    oracle_ndcgs,
    outlier_sensitivity,
)
from consistency_ranker.repair_selector_mining.checkpoint import FlushWriter  # noqa: E402

log = logging.getLogger("extraction_study")

_atomic_write_json = pilot_lib._atomic_write_json
_setup_logging = pilot_lib._setup_logging


def _pool_size_for_variant(variant: str) -> int:
    if variant == "pool6_original":
        return 6
    if variant.startswith("pool8"):
        return 8
    if variant.startswith("pool10"):
        return 10
    raise ValueError(f"Unknown variant naming, cannot infer pool size: {variant!r}")


def run_evaluation(output_dir: Path) -> list:
    """Requirement 1/2: evaluate every extractor on the SAME 120 real-LLM
    query graphs the repair-frontier program used, with graph construction
    held fixed (only the extraction step varies)."""
    units = frontier_lib.load_all_units()
    results_writer = FlushWriter(output_dir / "extraction_results.jsonl")
    failures_writer = FlushWriter(output_dir / "failures.jsonl")

    results = []
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
                    result = evaluate_unit_graph(
                        graph,
                        relevance_map,
                        key=key,
                        dataset=unit["dataset"],
                        query_id=unit["query_id"],
                        provider=graph_id,
                        pool_size=pool_size,
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
                if result is None:
                    failures_writer.write(
                        {
                            "unit_key": unit_key,
                            "error_type": "MissingIncumbent",
                            "error_message": "",
                        }
                    )
                    continue
                results.append(result)
                results_writer.write(
                    {
                        "unit_key": unit_key,
                        "dataset": result.dataset,
                        "query_id": result.query_id,
                        "provider": result.provider,
                        "pool_size": result.pool_size,
                        "is_cyclic": result.is_cyclic,
                        "n_nodes": result.n_nodes,
                        "n_edges": result.n_edges,
                        "graph_density": result.graph_density,
                        "ndcg_by_extractor": result.ndcg_by_extractor,
                        "incumbent_ndcg": result.incumbent_ndcg,
                    }
                )
    finally:
        results_writer.close()
        failures_writer.close()
    return results


def compute_all_stats(results: list) -> dict:
    """Requirement 3: mean delta, bootstrap CI, win/tie/loss, downside risk,
    breakdowns by dataset/provider/pool_size/cyclicity, per extractor.
    Requirement 4's outlier-sensitivity check is included per extractor."""
    stats: dict = {}
    for name in EXTRACTORS:
        extractor_stats = compute_extractor_stats(results, name)
        stats[name] = {
            "stats": extractor_stats.to_dict(),
            "breakdowns": full_breakdowns(results, name),
            "outlier_sensitivity": outlier_sensitivity(results, name, drop_top_n=1),
        }
    return stats


def write_extractor_tables(output_dir: Path, stats_by_extractor: dict) -> None:
    import csv

    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    for name, entry in stats_by_extractor.items():
        s = entry["stats"]
        summary_rows.append(
            {
                "extractor": name,
                "n": s["n"],
                "mean_delta": s["mean_delta"],
                "headroom_ci_lower": s["headroom_ci"]["lower"],
                "headroom_ci_upper": s["headroom_ci"]["upper"],
                "n_win": s["n_win"],
                "n_tie": s["n_tie"],
                "n_loss": s["n_loss"],
                "downside_q05": s["downside_q05"],
            }
        )
    with (tables_dir / "EXTRACTOR_SUMMARY.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary_rows[0]) if summary_rows else [])
        writer.writeheader()
        for row in summary_rows:
            writer.writerow(row)

    breakdown_rows = []
    for name, entry in stats_by_extractor.items():
        for dimension, groups in entry["breakdowns"].items():
            for group_value, group_stats in groups.items():
                breakdown_rows.append(
                    {
                        "extractor": name,
                        "dimension": dimension,
                        "group_value": group_value,
                        "n": group_stats["n"],
                        "mean_delta": group_stats["mean_delta"],
                        "headroom_ci_lower": group_stats["headroom_ci"]["lower"],
                        "headroom_ci_upper": group_stats["headroom_ci"]["upper"],
                        "n_win": group_stats["n_win"],
                        "n_tie": group_stats["n_tie"],
                        "n_loss": group_stats["n_loss"],
                    }
                )
    with (tables_dir / "BREAKDOWN_TABLES.csv").open("w", newline="", encoding="utf-8") as fh:
        fieldnames = list(breakdown_rows[0]) if breakdown_rows else []
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in breakdown_rows:
            writer.writerow(row)


def _selection_comparison_text(comparison: dict) -> str:
    best = comparison["always_best_single_extractor"]
    return (
        f"Comparison (mean nDCG): always_incumbent={comparison['always_incumbent']:.6f}, "
        f"always_best_single_extractor ({best['name']})={best['mean_ndcg']:.6f}, "
        f"oracle_extractor_selection={comparison['oracle_extractor_selection']:.6f}."
    )


def _method_localization_text(stats_by_extractor: dict) -> str:
    """Requirement 4: is the gain from one consistently superior extractor,
    dataset/provider-specific behavior, cyclic graphs, prior fusion, or
    isolated outliers?"""
    non_incumbent = {n: s for n, s in stats_by_extractor.items() if n != INCUMBENT_NAME}
    ranked = sorted(non_incumbent.items(), key=lambda kv: -kv[1]["stats"]["mean_delta"])
    lines = ["Extractors ranked by mean delta vs. incumbent:"]
    for name, entry in ranked:
        s = entry["stats"]
        out = entry["outlier_sensitivity"]
        frac_from_top = out.get("fraction_of_mean_from_top_n")
        frac_text = (
            f", {frac_from_top:.1%} of its mean from the single largest delta"
            if frac_from_top
            else ""
        )
        wtl = f"{s['n_win']}/{s['n_tie']}/{s['n_loss']}"
        ci = f"[{s['headroom_ci']['lower']:.5f}, {s['headroom_ci']['upper']:.5f}]"
        lines.append(
            f"- {name}: mean_delta={s['mean_delta']:.5f} (CI {ci}), win/tie/loss={wtl}, "
            f"downside_q05={s['downside_q05']:.5f}{frac_text}"
        )
    return "\n".join(lines)


def write_final_report(output_dir: Path, program_result: dict) -> None:
    decision_result = program_result["decision_result"]
    stats_by_extractor = program_result["stats_by_extractor"]
    selection = program_result["selection"]

    summary = {
        "timestamp": time.time(),
        "runtime_s": program_result["runtime_s"],
        "n_query_graphs": program_result["n_query_graphs"],
        "best_fixed_extractor": program_result["best_fixed_name"],
        "best_fixed_stats": stats_by_extractor[program_result["best_fixed_name"]]["stats"],
        "oracle_mean_ndcg": program_result["oracle_mean"],
        "incumbent_mean_ndcg": program_result["incumbent_mean"],
        "oracle_mean_delta": program_result["oracle_mean_delta"],
        "selection": selection,
        "decision": decision_result.decision,
        "decision_rationale": decision_result.rationale,
        "stats_by_extractor": {n: e["stats"] for n, e in stats_by_extractor.items()},
    }
    _atomic_write_json(output_dir / "FINAL_SUMMARY.json", summary)

    lines = [
        "# Extraction-vs-Repair Study -- Final Report",
        "",
        f"Runtime: {program_result['runtime_s']:.1f}s. Query-graphs evaluated: "
        f"{program_result['n_query_graphs']} (identical set used by the repair-frontier program).",
        "",
        "## Predeclared decision",
        "",
        f"**{decision_result.decision}**",
        "",
        decision_result.rationale,
        "",
        "## Per-extractor results (mean delta vs. incumbent, bootstrap 95% CI, "
        "win/tie/loss, downside risk)",
        "",
        "```",
        _method_localization_text(stats_by_extractor),
        "```",
        "",
        "## Is the gain from one consistently superior extractor, or "
        "dataset/provider-specific, cyclic-only, prior-fusion, or outlier-driven?",
        "",
        "See `tables/BREAKDOWN_TABLES.csv` for the full by-dataset/by-provider/by-pool_size/"
        "by-cyclicity breakdown per extractor, and the per-extractor "
        "`fraction_of_mean_from_top_n` figure above for outlier sensitivity "
        "(drops the single largest positive delta and recomputes the mean).",
        "",
        "## Selective vs. deployable selection",
        "",
        f"Selection status: **{selection['status']}**. {selection['reason']}",
        "",
        _selection_comparison_text(selection["comparison"]),
        "",
        "## Should extraction, not repair, become the paper's central contribution?",
        "",
        _central_contribution_text(decision_result.decision, program_result),
        "",
        "## Files in this directory",
        "",
        "- `RUN_CONFIG.json`, `extraction_results.jsonl`, `failures.jsonl`",
        "- `tables/EXTRACTOR_SUMMARY.csv`, `tables/BREAKDOWN_TABLES.csv`",
        "- `FINAL_SUMMARY.json` (this report's machine-readable twin)",
        "",
    ]
    (output_dir / "FINAL_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def _central_contribution_text(decision: str, program_result: dict) -> str:
    best_name = program_result["best_fixed_name"]
    best_delta = program_result["stats_by_extractor"][best_name]["stats"]["mean_delta"]
    if decision == "EXTRACTION_IMPROVES_RANKING":
        return (
            f"Yes, provisionally: switching the extraction method to '{best_name}' "
            f"(mean delta {best_delta:.5f}) is a simple, fixed, deployable change with no "
            "per-query selection or repair machinery required. This is a stronger and "
            "simpler claim than anything the repair program produced, and is the "
            "recommended candidate for the paper's central contribution -- subject to "
            "replication at larger scale (this study, like the repair-frontier program, "
            "runs on the same n=120 real-LLM query-graph sample)."
        )
    if decision == "SELECTIVE_EXTRACTION_ONLY":
        return (
            "Partially: no single fixed extractor is reliably better, but a deployable "
            "per-query selector beats the incumbent and the oracle has real headroom. "
            "Extraction is a more promising direction than repair, but the paper's "
            "contribution would need to center on the SELECTOR, not a single extractor "
            "swap -- a more complex (though still simpler than repair) story."
        )
    if decision == "ORACLE_ONLY_NOT_DEPLOYABLE":
        return (
            "No: oracle-level headroom exists across extractors, but nothing deployable "
            "(fixed rule or learned selector) currently realizes it. Extraction is not "
            "yet a defensible central contribution on this evidence -- it would need a "
            "better selector or additional features, not just a different ranking of "
            "candidate extractors."
        )
    return (
        "No: neither a fixed extractor, a selector, nor the oracle shows a meaningful "
        "gain on this data. The repair-frontier program's apparent 'extraction, not "
        "repair' signal does not survive a systematic, bootstrap-CI'd comparison across "
        "the full extractor family -- extraction should NOT become the paper's central "
        "contribution based on this evidence."
    )


def run_program(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(
        output_dir / "RUN_CONFIG.json",
        {
            "extractors": list(EXTRACTORS),
            "incumbent_name": INCUMBENT_NAME,
            "meaningful_threshold": 0.01,
            "sources": [str(frontier_lib.POOL6_DIR), str(frontier_lib.REVIEWER_CONCERNS_DIR)],
        },
    )

    t0 = time.time()
    results = run_evaluation(output_dir)
    log.info("Evaluated %d query-graphs across %d extractors", len(results), len(EXTRACTORS))

    stats_by_extractor = compute_all_stats(results)
    write_extractor_tables(output_dir, stats_by_extractor)

    non_incumbent_names = [n for n in EXTRACTORS if n != INCUMBENT_NAME]
    best_fixed_name = max(
        non_incumbent_names, key=lambda n: stats_by_extractor[n]["stats"]["mean_delta"]
    )
    best_stats = stats_by_extractor[best_fixed_name]["stats"]

    selection = evaluate_selection(results)
    oracle_mean = float(np.mean(oracle_ndcgs(results))) if results else 0.0
    incumbent_mean = float(np.mean([r.incumbent_ndcg for r in results])) if results else 0.0
    oracle_mean_delta = oracle_mean - incumbent_mean

    decision_result = decide(
        best_fixed_name=best_fixed_name,
        best_fixed_mean_delta=best_stats["mean_delta"],
        best_fixed_headroom_ci_lower=best_stats["headroom_ci"]["lower"],
        best_fixed_downside_q05=best_stats["downside_q05"],
        selection_status=selection["status"],
        oracle_mean_delta=oracle_mean_delta,
    )

    runtime_s = time.time() - t0
    program_result = {
        "runtime_s": runtime_s,
        "n_query_graphs": len(results),
        "stats_by_extractor": stats_by_extractor,
        "best_fixed_name": best_fixed_name,
        "selection": selection,
        "oracle_mean": oracle_mean,
        "incumbent_mean": incumbent_mean,
        "oracle_mean_delta": oracle_mean_delta,
        "decision_result": decision_result,
    }
    write_final_report(output_dir, program_result)

    return {
        "n_query_graphs": len(results),
        "runtime_s": runtime_s,
        "best_fixed_extractor": best_fixed_name,
        "best_fixed_mean_delta": best_stats["mean_delta"],
        "selection_status": selection["status"],
        "decision": decision_result.decision,
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
