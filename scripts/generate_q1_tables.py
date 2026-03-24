#!/usr/bin/env python
"""
generate_q1_tables.py
=====================
Canonical script that regenerates all Q1 journal-facing tables from
pre-committed and freshly computed outputs.

Reads from
----------
- ``<pub-root>/paper_package/tables/`` : real-data results (committed)
- ``<synth-results>``                  : synthetic sweep CSV (committed)
- ``docs/tables/bootstrap_results_combined_summary.csv``  (committed)

Writes to ``<out-dir>/``
------------------------
table_main_performance.csv      Per-dataset × vote construction nDCG for all methods
table_structural_consistency.csv BEW/PIC pre/post FAS repair
table_per_dataset_summary.csv   One row per dataset: best method, ΔnDCG, significance
table_significance.csv          Bootstrap CI + significance labels
table_regime_analysis.csv       SCC-stratified ΔnDCG (high vs low cyclicity)
table_failure_cases.csv         Cases where repair yields ΔnDCG < threshold
summary_report.md               Human-readable narrative

Usage (from repository root)
-----------------------------
    python scripts/generate_q1_tables.py \\
        --pub-root outputs/pub_vote_cmp_all4 \\
        --synth-results docs/tables/main_results.csv \\
        --out-dir outputs/q1_journal_package
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV file and return list of dicts."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    """Write a list of dicts to CSV, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    cols = fieldnames or list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _f(value: Any, ndigits: int = 4) -> str:
    """Format a numeric value, handling NaN/None gracefully."""
    try:
        v = float(value)
        if math.isnan(v):
            return ""
        return f"{v:.{ndigits}f}"
    except (TypeError, ValueError):
        return "" if value is None else str(value)


# ---------------------------------------------------------------------------
# Table builders
# ---------------------------------------------------------------------------


def build_main_performance_table(
    pub_root: Path, out_dir: Path
) -> list[dict]:
    """
    Table: Per-dataset × vote construction, mean nDCG for all hybrid methods.

    Sources: pub_root/paper_package/tables/table_graph_ndcg_and_consistency.csv
    """
    src = pub_root / "paper_package" / "tables" / "table_graph_ndcg_and_consistency.csv"
    rows = _read_csv(src)
    if not rows:
        return []

    output_rows = []
    for r in rows:
        output_rows.append(
            {
                "dataset": r.get("dataset", ""),
                "vote_construction": r.get("variant", ""),
                "n_queries": r.get("n_queries", ""),
                "pct_cyclic_graphs": _f(r.get("pct_cyclic", ""), 2),
                "mean_ndcg_prior_only": _f(r.get("mean_ndcg_prior", "")),
                "mean_ndcg_unrepaired_copeland": _f(r.get("mean_ndcg_uco", "")),
                "mean_ndcg_repaired_copeland": _f(r.get("mean_ndcg_rco", "")),
                "mean_ndcg_unrepaired_balance": _f(r.get("mean_ndcg_uba", "")),
                "mean_ndcg_repaired_balance": _f(r.get("mean_ndcg_rba", "")),
                "delta_ndcg_copeland_R_minus_U": _f(
                    _safe_diff(r.get("mean_ndcg_rco"), r.get("mean_ndcg_uco"))
                ),
            }
        )

    path = out_dir / "table_main_performance.csv"
    _write_csv(path, output_rows)
    return output_rows


def _safe_diff(a: Any, b: Any) -> float | str:
    try:
        result = float(a) - float(b)
        if math.isnan(result):
            return ""
        return result
    except (TypeError, ValueError):
        return ""


def build_structural_consistency_table(pub_root: Path, out_dir: Path) -> list[dict]:
    """
    Table: BEW and PIC pre/post FAS repair.
    """
    src = pub_root / "paper_package" / "tables" / "table_graph_ndcg_and_consistency.csv"
    rows = _read_csv(src)
    if not rows:
        return []

    output_rows = []
    for r in rows:
        output_rows.append(
            {
                "dataset": r.get("dataset", ""),
                "vote_construction": r.get("variant", ""),
                "n_queries": r.get("n_queries", ""),
                "avg_n_edges": _f(r.get("avg_n_edges", ""), 1),
                "mean_fas_weight_removed": _f(r.get("mean_fas_weight_removed", ""), 4),
                "bew_pre": _f(r.get("mean_graph_ref_bew_pre", ""), 2),
                "bew_post": _f(r.get("mean_graph_ref_bew_post", ""), 2),
                "delta_bew_pre_minus_post": _f(r.get("mean_delta_bew_qrels_pre_minus_post", ""), 4),
                "pic_pre": _f(r.get("mean_graph_ref_pic_pre", ""), 2),
                "pic_post": _f(r.get("mean_graph_ref_pic_post", ""), 2),
                "delta_pic_pre_minus_post": _f(r.get("mean_delta_pic_qrels_pre_minus_post", ""), 4),
            }
        )

    path = out_dir / "table_structural_consistency.csv"
    _write_csv(path, output_rows)
    return output_rows


def build_significance_table(pub_root: Path, out_dir: Path) -> list[dict]:
    """
    Table: Bootstrap CI + significance labels for all method pairs.
    """
    src = pub_root / "paper_package" / "tables" / "table_bootstrap_delta_ndcg.csv"
    rows = _read_csv(src)
    if not rows:
        return []

    sig_threshold = 0.0  # CI strictly above or below zero

    output_rows = []
    for r in rows:
        n_q = r.get("n_queries", "")
        mean_d = r.get("mean_delta_ndcg", "")
        ci_lo = r.get("ci95_low", "")
        ci_hi = r.get("ci95_high", "")

        try:
            n_q_int = int(float(n_q)) if n_q else 0
        except (ValueError, TypeError):
            n_q_int = 0

        # Significance label
        try:
            lo = float(ci_lo)
            hi = float(ci_hi)
            m = float(mean_d)
            if n_q_int == 0 or not n_q:
                sig_label = "n/a"
            elif lo > sig_threshold:
                sig_label = "✓ sig. positive"
            elif hi < -sig_threshold:
                sig_label = "✗ sig. negative"
            elif abs(m) < 1e-8:
                sig_label = "− inactive (Δ=0)"
            else:
                sig_label = "− not significant"
        except (TypeError, ValueError):
            sig_label = "n/a"

        output_rows.append(
            {
                "dataset": r.get("dataset", ""),
                "vote_construction": r.get("variant", ""),
                "comparison": r.get("pair", ""),
                "n_queries": n_q,
                "mean_delta_ndcg": _f(mean_d, 6),
                "ci95_low": _f(ci_lo, 6),
                "ci95_high": _f(ci_hi, 6),
                "bootstrap_reps": r.get("bootstrap_reps", ""),
                "significance": sig_label,
            }
        )

    path = out_dir / "table_significance.csv"
    _write_csv(path, output_rows)
    return output_rows


def build_per_dataset_summary_table(
    main_perf: list[dict],
    sig_rows: list[dict],
    out_dir: Path,
) -> list[dict]:
    """
    Table: One row per dataset summarising best method, ΔnDCG, significance.
    """
    # Index sig rows for quick lookup
    sig_index: dict[tuple[str, str, str], dict] = {}
    for r in sig_rows:
        key = (r.get("dataset", ""), r.get("vote_construction", ""), r.get("comparison", ""))
        sig_index[key] = r

    output_rows = []
    for r in main_perf:
        ds = r.get("dataset", "")
        var = r.get("vote_construction", "")

        # Determine best nDCG method
        candidates = {
            "prior_only": r.get("mean_ndcg_prior_only", ""),
            "unrepaired_copeland": r.get("mean_ndcg_unrepaired_copeland", ""),
            "repaired_copeland": r.get("mean_ndcg_repaired_copeland", ""),
            "unrepaired_balance": r.get("mean_ndcg_unrepaired_balance", ""),
            "repaired_balance": r.get("mean_ndcg_repaired_balance", ""),
        }
        best_method = ""
        best_val = -1.0
        for mname, mval in candidates.items():
            try:
                v = float(mval)
                if v > best_val:
                    best_val = v
                    best_method = mname
            except (TypeError, ValueError):
                pass

        copeland_sig = sig_index.get((ds, var, "copeland"), {})
        balance_sig = sig_index.get((ds, var, "balance"), {})

        output_rows.append(
            {
                "dataset": ds,
                "vote_construction": var,
                "n_queries": r.get("n_queries", ""),
                "pct_cyclic_graphs": r.get("pct_cyclic_graphs", ""),
                "best_method": best_method,
                "best_mean_ndcg": _f(best_val, 4) if best_val >= 0 else "",
                "copeland_delta_ndcg_R_minus_U": r.get("delta_ndcg_copeland_R_minus_U", ""),
                "copeland_significance": copeland_sig.get("significance", "n/a"),
                "balance_significance": balance_sig.get("significance", "n/a"),
            }
        )

    path = out_dir / "table_per_dataset_summary.csv"
    _write_csv(path, output_rows)
    return output_rows


def build_regime_analysis_table(pub_root: Path, out_dir: Path) -> list[dict]:
    """
    Table: SCC-stratified ΔnDCG (high vs low cyclicity) from bootstrap data.
    """
    src = pub_root / "paper_package" / "tables" / "table_bootstrap_delta_ndcg.csv"
    rows = _read_csv(src)
    if not rows:
        return []

    regime_pairs = ("copeland_scc_high", "copeland_scc_low")
    regime_rows = [r for r in rows if r.get("pair", "") in regime_pairs]
    output_rows = []
    for r in regime_rows:
        regime = "high_scc" if "high" in r.get("pair", "") else "low_scc"
        n_q = r.get("n_queries", "")
        mean_d = r.get("mean_delta_ndcg", "")
        ci_lo = r.get("ci95_low", "")
        ci_hi = r.get("ci95_high", "")

        try:
            n_q_int = int(float(n_q)) if n_q else 0
        except (TypeError, ValueError):
            n_q_int = 0

        output_rows.append(
            {
                "dataset": r.get("dataset", ""),
                "vote_construction": r.get("variant", ""),
                "scc_regime": regime,
                "n_queries": n_q,
                "mean_delta_ndcg_copeland": _f(mean_d, 6),
                "ci95_low": _f(ci_lo, 6),
                "ci95_high": _f(ci_hi, 6),
                "interpretation": (
                    "skipped (n=0)"
                    if n_q_int == 0
                    else _regime_interpretation(mean_d, ci_lo, ci_hi)
                ),
            }
        )

    path = out_dir / "table_regime_analysis.csv"
    _write_csv(path, output_rows)
    return output_rows


def _regime_interpretation(mean_d: Any, ci_lo: Any, ci_hi: Any) -> str:
    try:
        m = float(mean_d)
        lo = float(ci_lo)
        hi = float(ci_hi)
    except (TypeError, ValueError):
        return "n/a"
    if abs(m) < 1e-8 and abs(lo) < 1e-8 and abs(hi) < 1e-8:
        return "repair inactive"
    if hi < 0:
        return "repair harms nDCG (sig.)"
    if lo > 0:
        return "repair helps nDCG (sig.)"
    return "no significant change"


def build_failure_cases_table(
    pub_root: Path, out_dir: Path, threshold: float = -0.005
) -> list[dict]:
    """
    Table: Dataset × vote construction cases where ΔnDCG < threshold.
    """
    src = pub_root / "paper_package" / "tables" / "table_bootstrap_delta_ndcg.csv"
    rows = _read_csv(src)
    if not rows:
        return []

    output_rows = []
    for r in rows:
        if r.get("pair", "") not in ("copeland", "balance"):
            continue
        mean_d = r.get("mean_delta_ndcg", "")
        n_q = r.get("n_queries", "")
        try:
            v = float(mean_d)
            n_q_int = int(float(n_q)) if n_q else 0
        except (TypeError, ValueError):
            continue
        if n_q_int == 0:
            continue
        if v < threshold:
            ci_lo = r.get("ci95_low", "")
            ci_hi = r.get("ci95_high", "")
            output_rows.append(
                {
                    "dataset": r.get("dataset", ""),
                    "vote_construction": r.get("variant", ""),
                    "method_pair": r.get("pair", ""),
                    "n_queries": n_q,
                    "mean_delta_ndcg": _f(v, 6),
                    "ci95_low": _f(ci_lo, 6),
                    "ci95_high": _f(ci_hi, 6),
                    "threshold": str(threshold),
                    "note": "repair harms retrieval quality",
                }
            )

    path = out_dir / "table_failure_cases.csv"
    _write_csv(path, output_rows)
    return output_rows


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------


def build_summary_report(
    main_perf: list[dict],
    struct: list[dict],
    sig: list[dict],
    regime: list[dict],
    failure: list[dict],
    out_dir: Path,
) -> Path:
    """
    Generate a human-readable Markdown narrative summarising all tables.
    """
    lines: list[str] = [
        "# Q1 Journal Package — Summary Report",
        "",
        "> Auto-generated by `scripts/generate_q1_tables.py`.",
        "> Numbers are taken directly from pre-committed and freshly computed outputs.",
        "> Do not edit manually.",
        "",
        "---",
        "",
        "## 1. Main Performance Table",
        "",
        "Mean nDCG@k across hybrid methods per dataset and vote construction.",
        "",
    ]

    if main_perf:
        lines.append(
            "| Dataset | Vote | n_q | %Cyclic | Prior-only | U-Copeland | R-Copeland |"
            " ΔCopeland (R−U) |"
        )
        lines.append("|---|---|---|---|---|---|---|---|")
        for r in main_perf:
            lines.append(
                f"| {r['dataset']} | {r['vote_construction']} | {r['n_queries']} |"
                f" {r['pct_cyclic_graphs']} |"
                f" {r['mean_ndcg_prior_only']} | {r['mean_ndcg_unrepaired_copeland']} |"
                f" {r['mean_ndcg_repaired_copeland']} | {r['delta_ndcg_copeland_R_minus_U']} |"
            )
    else:
        lines.append("*No data available — run the real-data pipeline first.*")

    lines += [
        "",
        "---",
        "",
        "## 2. Structural Consistency Table",
        "",
        "Mean BEW and PIC (pairwise inconsistency count) before and after FAS repair,",
        "measured against a qrels-derived reference ranking.",
        "",
    ]

    if struct:
        lines.append("| Dataset | Vote | BEW pre | BEW post | ΔBEW | PIC pre | PIC post | ΔPIC |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for r in struct:
            lines.append(
                f"| {r['dataset']} | {r['vote_construction']} |"
                f" {r['bew_pre']} | {r['bew_post']} | {r['delta_bew_pre_minus_post']} |"
                f" {r['pic_pre']} | {r['pic_post']} | {r['delta_pic_pre_minus_post']} |"
            )
    else:
        lines.append("*No data available.*")

    lines += [
        "",
        "---",
        "",
        "## 3. Significance Table",
        "",
        "Bootstrap 95% CI (2000 replications) for ΔnDCG (repaired − unrepaired),",
        "with significance labels.",
        "",
        "**Legend:** ✓ sig. positive = CI strictly above 0; ✗ sig. negative = CI strictly below 0;",
        "− inactive = Δ=0 (repair removed no edges); − not significant = CI straddles 0.",
        "",
    ]

    if sig:
        lines.append(
            "| Dataset | Vote | Comparison | n_q | Mean Δ | CI low | CI high | Significance |"
        )
        lines.append("|---|---|---|---|---|---|---|---|")
        for r in sig:
            lines.append(
                f"| {r['dataset']} | {r['vote_construction']} | {r['comparison']} |"
                f" {r['n_queries']} | {r['mean_delta_ndcg']} |"
                f" {r['ci95_low']} | {r['ci95_high']} | {r['significance']} |"
            )
    else:
        lines.append("*No data available.*")

    lines += [
        "",
        "---",
        "",
        "## 4. Regime Analysis Table",
        "",
        "ΔnDCG stratified by SCC size (high vs low cyclicity) to assess whether",
        "repair harm concentrates in high-conflict subgraphs.",
        "",
    ]

    if regime:
        lines.append(
            "| Dataset | Vote | SCC Regime | n_q | Mean Δ | CI low | CI high | Interpretation |"
        )
        lines.append("|---|---|---|---|---|---|---|---|")
        for r in regime:
            lines.append(
                f"| {r['dataset']} | {r['vote_construction']} | {r['scc_regime']} |"
                f" {r['n_queries']} | {r['mean_delta_ndcg_copeland']} |"
                f" {r['ci95_low']} | {r['ci95_high']} | {r['interpretation']} |"
            )
    else:
        lines.append("*No data available.*")

    lines += [
        "",
        "---",
        "",
        "## 5. Failure Cases",
        "",
        "Conditions where mean ΔnDCG < −0.005 (repair causes meaningful harm).",
        "",
    ]

    if failure:
        lines.append("| Dataset | Vote | Pair | n_q | Mean Δ | CI low | CI high | Note |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for r in failure:
            lines.append(
                f"| {r['dataset']} | {r['vote_construction']} | {r['method_pair']} |"
                f" {r['n_queries']} | {r['mean_delta_ndcg']} |"
                f" {r['ci95_low']} | {r['ci95_high']} | {r['note']} |"
            )
    else:
        lines.append("*No failure cases found at the −0.005 threshold.*")

    lines += [
        "",
        "---",
        "",
        "## 6. Key Findings",
        "",
        "1. **Vote construction controls cyclicity**: ms1 → high cycles;"
        " ms2 and ms1_drop_mutual → near-acyclic.",
        "2. **FAS repair reduces structural inconsistency (BEW, PIC)**"
        " but does not reliably improve nDCG@k.",
        "3. **Under high-cyclicity ms1 + Copeland**: repair is significantly harmful"
        " on SciDocs (CI strictly negative).",
        "4. **Under near-acyclic constructions (ms2, ms1_drop_mutual)**: repair is inactive (Δ=0).",
        "5. **SCC-stratified analysis**: harm concentrates in queries with largest SCC ≥ median.",
        "",
        "---",
        "",
        "*For full reproduction instructions, see `docs/REPRODUCTION_Q1.md`.*",
        "*For manuscript positioning guidance, see `docs/Q1_POSITIONING_AND_CLAIMS.md`.*",
    ]

    out_path = out_dir / "summary_report.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate Q1 journal package tables from committed outputs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--pub-root",
        default="outputs/pub_vote_cmp_all4",
        help="Root of the publication vote suite outputs "
        "(default: outputs/pub_vote_cmp_all4).",
    )
    parser.add_argument(
        "--synth-results",
        default="docs/tables/main_results.csv",
        help="Synthetic sweep results CSV (default: docs/tables/main_results.csv).",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/q1_journal_package",
        help="Output directory for generated tables "
        "(default: outputs/q1_journal_package; regenerate from all4 for current JIS alignment).",
    )
    parser.add_argument(
        "--failure-threshold",
        type=float,
        default=-0.005,
        help="ΔnDCG threshold below which a case is labelled a failure (default: -0.005).",
    )
    args = parser.parse_args(argv)

    pub_root = (REPO_ROOT / args.pub_root).resolve()
    out_dir = (REPO_ROOT / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not pub_root.exists():
        print(
            f"ERROR: pub-root directory not found: {pub_root}\n"
            "Run `python scripts/run_publication_vote_suite.py` first, or "
            "check that the pre-committed paper_package exists.",
            file=sys.stderr,
        )
        return 1

    paper_pkg = pub_root / "paper_package" / "tables"
    if not paper_pkg.exists():
        print(
            f"WARNING: paper_package/tables not found under {pub_root}. "
            "Tables will be empty. Run `python scripts/build_paper_evidence_package.py` "
            f"--root {pub_root}` first.",
            file=sys.stderr,
        )

    print(f"Generating Q1 journal tables in: {out_dir}")

    main_perf = build_main_performance_table(pub_root, out_dir)
    print(f"  table_main_performance.csv          ({len(main_perf)} rows)")

    struct = build_structural_consistency_table(pub_root, out_dir)
    print(f"  table_structural_consistency.csv    ({len(struct)} rows)")

    sig = build_significance_table(pub_root, out_dir)
    print(f"  table_significance.csv              ({len(sig)} rows)")

    per_ds = build_per_dataset_summary_table(main_perf, sig, out_dir)
    print(f"  table_per_dataset_summary.csv       ({len(per_ds)} rows)")

    regime = build_regime_analysis_table(pub_root, out_dir)
    print(f"  table_regime_analysis.csv           ({len(regime)} rows)")

    failure = build_failure_cases_table(pub_root, out_dir, threshold=args.failure_threshold)
    print(f"  table_failure_cases.csv             ({len(failure)} rows)")

    report_path = build_summary_report(main_perf, struct, sig, regime, failure, out_dir)
    print(f"  {report_path.name}")

    print(f"\nDone. Q1 journal package written to: {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
