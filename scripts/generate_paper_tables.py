#!/usr/bin/env python
"""
Generate manuscript-ready evidence tables under reports/paper_tables.

This script is intentionally conservative: it only aggregates from existing
artifacts in this repository and never fabricates missing values.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    cols = fieldnames or list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)


def _to_float(value: Any) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f):
        return None
    return f


def _fmt(value: float | None, ndigits: int = 6) -> str:
    if value is None:
        return ""
    return f"{value:.{ndigits}f}"


def _effect_label(
    mean_delta: float | None,
    ci_low: float | None,
    ci_high: float | None,
    n_q: int,
) -> str:
    if n_q <= 0:
        return "no_data"
    if mean_delta is None or ci_low is None or ci_high is None:
        return "incomplete"
    if ci_low > 0.0:
        return "significant_gain"
    if ci_high < 0.0:
        return "significant_harm"
    if (
        abs(mean_delta) <= 1.0e-10
        and abs(ci_low) <= 1.0e-10
        and abs(ci_high) <= 1.0e-10
    ):
        return "inactive"
    return "no_significant_change"


def build_repair_effects_table(q1_dir: Path) -> list[dict[str, str]]:
    sig_rows = _read_csv(q1_dir / "table_significance.csv")
    out: list[dict[str, str]] = []
    for row in sig_rows:
        comparison = row.get("comparison", "")
        if comparison not in {"copeland", "balance"}:
            continue
        mean_delta = _to_float(row.get("mean_delta_ndcg"))
        ci_low = _to_float(row.get("ci95_low"))
        ci_high = _to_float(row.get("ci95_high"))
        n_q = int(float(row.get("n_queries", "0") or 0))
        out.append(
            {
                "dataset": row.get("dataset", ""),
                "vote_construction": row.get("vote_construction", ""),
                "comparison": comparison,
                "n_queries": str(n_q),
                "mean_delta_ndcg": _fmt(mean_delta),
                "ci95_low": _fmt(ci_low),
                "ci95_high": _fmt(ci_high),
                "effect_label": _effect_label(mean_delta, ci_low, ci_high, n_q),
            }
        )
    out.sort(key=lambda r: (r["dataset"], r["vote_construction"], r["comparison"]))
    return out


def build_proxy_baseline_table(real_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for summary_path in sorted(real_dir.glob("*/*/*_summary.csv")):
        source = summary_path.parent.name
        dataset = summary_path.parent.parent.name
        summary_rows = _read_csv(summary_path)
        for row in summary_rows:
            rows.append(
                {
                    "dataset": dataset,
                    "preference_source": source,
                    "method": row.get("method", ""),
                    "n_queries": row.get("n_queries", ""),
                    "ndcg_mean": row.get("ndcg_mean", ""),
                    "map_mean": row.get("map_mean", ""),
                    "pairwise_accuracy_mean": row.get("pairwise_accuracy_mean", ""),
                    "tau_mean": row.get("tau_mean", ""),
                    "runtime_mean_s": row.get("runtime_mean_s", ""),
                    "cyclic_pct": row.get("cyclic_pct", ""),
                    "fas_removed_weight_mean": row.get("fas_removed_weight_mean", ""),
                }
            )
    rows.sort(key=lambda r: (r["dataset"], r["preference_source"], r["method"]))
    return rows


def build_synthetic_multiseed_stability(synthetic_dir: Path) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str], list[float]] = {}
    for result_path in sorted(synthetic_dir.glob("*multiseed*/seed_*/synthetic_results.json")):
        run_family = result_path.parents[1].name
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        tau_map = payload.get("evaluation", {}).get("kendall_tau", {})
        for method, tau in tau_map.items():
            tau_val = _to_float(tau)
            if tau_val is None:
                continue
            grouped.setdefault((run_family, method), []).append(tau_val)

    rows: list[dict[str, str]] = []
    for (run_family, method), values in sorted(grouped.items()):
        mean_v = statistics.mean(values)
        std_v = statistics.stdev(values) if len(values) > 1 else 0.0
        rows.append(
            {
                "run_family": run_family,
                "method": method,
                "n_seeds": str(len(values)),
                "kendall_tau_mean": _fmt(mean_v),
                "kendall_tau_std": _fmt(std_v),
                "kendall_tau_min": _fmt(min(values)),
                "kendall_tau_max": _fmt(max(values)),
            }
        )
    return rows


def build_synthetic_noise_table(synthetic_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    noise_result_paths = list(sorted(synthetic_dir.glob("noise_sweep_n*/synthetic_results.json")))
    noise_result_paths += list(
        sorted(synthetic_dir.glob("noise_sweep_variant_followup/noise_*/synthetic_results.json"))
    )
    for result_path in noise_result_paths:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        cfg = payload.get("config", {})
        tau_map = payload.get("evaluation", {}).get("kendall_tau", {})
        noise = _to_float(cfg.get("noise"))
        for method, tau in tau_map.items():
            tau_val = _to_float(tau)
            if tau_val is None or noise is None:
                continue
            rows.append(
                {
                    "source_dir": str(result_path.parent.relative_to(synthetic_dir)),
                    "noise": _fmt(noise, ndigits=3),
                    "method": method,
                    "kendall_tau": _fmt(tau_val),
                }
            )
    rows.sort(key=lambda r: (float(r["noise"]), r["source_dir"], r["method"]))
    return rows


def build_failure_context_table(q1_dir: Path) -> list[dict[str, str]]:
    failures = _read_csv(q1_dir / "table_failure_cases.csv")
    main_perf = _read_csv(q1_dir / "table_main_performance.csv")
    structural = _read_csv(q1_dir / "table_structural_consistency.csv")

    perf_idx = {(r.get("dataset"), r.get("vote_construction")): r for r in main_perf}
    struct_idx = {(r.get("dataset"), r.get("vote_construction")): r for r in structural}

    out: list[dict[str, str]] = []
    for row in failures:
        key = (row.get("dataset"), row.get("vote_construction"))
        perf = perf_idx.get(key, {})
        struct = struct_idx.get(key, {})
        out.append(
            {
                "dataset": row.get("dataset", ""),
                "vote_construction": row.get("vote_construction", ""),
                "method_pair": row.get("method_pair", ""),
                "n_queries": row.get("n_queries", ""),
                "mean_delta_ndcg": row.get("mean_delta_ndcg", ""),
                "ci95_low": row.get("ci95_low", ""),
                "ci95_high": row.get("ci95_high", ""),
                "pct_cyclic_graphs": perf.get("pct_cyclic_graphs", ""),
                "mean_fas_weight_removed": struct.get("mean_fas_weight_removed", ""),
                "delta_bew_pre_minus_post": struct.get("delta_bew_pre_minus_post", ""),
                "delta_pic_pre_minus_post": struct.get("delta_pic_pre_minus_post", ""),
            }
        )
    return out


def build_artifact_inventory(
    q1_dir: Path,
    paper_pkg_dir: Path,
    real_dir: Path,
) -> list[dict[str, str]]:
    tracked_paths = [
        q1_dir / "table_main_performance.csv",
        q1_dir / "table_significance.csv",
        q1_dir / "table_structural_consistency.csv",
        q1_dir / "table_failure_cases.csv",
        q1_dir / "summary_report.md",
        paper_pkg_dir / "tables" / "table_graph_ndcg_and_consistency.csv",
        paper_pkg_dir / "tables" / "table_bootstrap_delta_ndcg.csv",
        paper_pkg_dir / "tables" / "table_consistency_qrels_bew.csv",
        paper_pkg_dir / "MANUSCRIPT_SUMMARY.md",
        real_dir / "PROVENANCE.md",
    ]

    rows: list[dict[str, str]] = []
    for path in tracked_paths:
        exists = path.exists()
        row_count = ""
        if exists and path.suffix.lower() == ".csv":
            row_count = str(len(_read_csv(path)))
        try:
            display_path = str(path.relative_to(REPO_ROOT))
        except ValueError:
            display_path = str(path)
        rows.append(
            {
                "path": display_path,
                "exists": "yes" if exists else "no",
                "row_count_if_csv": row_count,
            }
        )
    return rows


def write_readme(out_dir: Path) -> None:
    readme = out_dir / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# paper_tables",
                "",
                "Machine-readable manuscript-support tables generated by",
                "`scripts/generate_paper_tables.py`.",
                "",
                "Tables in this directory are derived only from committed repository artifacts.",
                "If a source artifact is missing, the corresponding table may be empty.",
            ]
        ),
        encoding="utf-8",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate manuscript-ready evidence tables from committed outputs."
    )
    parser.add_argument(
        "--q1-dir",
        type=Path,
        default=Path("outputs/q1_journal_package"),
        help=(
            "Directory containing aggregated Q1 tables. "
            "For JIS manuscript use, regenerate this directory from "
            "outputs/pub_vote_cmp_all4 before running this script "
            "(default: outputs/q1_journal_package)."
        ),
    )
    parser.add_argument(
        "--paper-package-dir",
        type=Path,
        default=Path("outputs/pub_vote_cmp_all4/paper_package"),
        help=(
            "Publication paper_package directory to inventory/reference "
            "(default: outputs/pub_vote_cmp_all4/paper_package)."
        ),
    )
    parser.add_argument(
        "--real-dir",
        type=Path,
        default=Path("outputs/real_full"),
        help="Directory for real-data non-vote-suite summaries (default: outputs/real_full).",
    )
    parser.add_argument(
        "--synthetic-dir",
        type=Path,
        default=Path("outputs"),
        help="Root directory containing synthetic result families (default: outputs).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("reports/paper_tables"),
        help="Output directory for generated manuscript-support tables (default: reports/paper_tables).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    q1_dir = (REPO_ROOT / args.q1_dir).resolve()
    paper_pkg_dir = (REPO_ROOT / args.paper_package_dir).resolve()
    real_dir = (REPO_ROOT / args.real_dir).resolve()
    synthetic_dir = (REPO_ROOT / args.synthetic_dir).resolve()
    out_dir = (REPO_ROOT / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    table_repair = build_repair_effects_table(q1_dir)
    _write_csv(out_dir / "table_01_repair_effects.csv", table_repair)

    table_proxy = build_proxy_baseline_table(real_dir)
    _write_csv(out_dir / "table_02_proxy_baseline_leaderboard.csv", table_proxy)

    table_multiseed = build_synthetic_multiseed_stability(synthetic_dir)
    _write_csv(out_dir / "table_03_synthetic_multiseed_stability.csv", table_multiseed)

    table_noise = build_synthetic_noise_table(synthetic_dir)
    _write_csv(out_dir / "table_04_synthetic_noise_sweep.csv", table_noise)

    table_failure = build_failure_context_table(q1_dir)
    _write_csv(out_dir / "table_05_failure_context.csv", table_failure)

    table_inventory = build_artifact_inventory(q1_dir, paper_pkg_dir, real_dir)
    _write_csv(out_dir / "table_06_artifact_inventory.csv", table_inventory)

    write_readme(out_dir)

    print(f"[generate_paper_tables] out_dir={out_dir}")
    print(f"[generate_paper_tables] table_01_repair_effects.csv rows={len(table_repair)}")
    print(
        "[generate_paper_tables] table_02_proxy_baseline_leaderboard.csv "
        f"rows={len(table_proxy)}"
    )
    print(
        "[generate_paper_tables] table_03_synthetic_multiseed_stability.csv "
        f"rows={len(table_multiseed)}"
    )
    print(
        "[generate_paper_tables] table_04_synthetic_noise_sweep.csv "
        f"rows={len(table_noise)}"
    )
    print(f"[generate_paper_tables] table_05_failure_context.csv rows={len(table_failure)}")
    print(f"[generate_paper_tables] table_06_artifact_inventory.csv rows={len(table_inventory)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

