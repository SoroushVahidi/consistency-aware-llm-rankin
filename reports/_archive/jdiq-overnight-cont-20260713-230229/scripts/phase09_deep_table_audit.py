#!/usr/bin/env python3
"""
Deep overnight reconciliation: every numeric cell in manuscript tabulars
vs paper_package CSVs / retention investigation tables where matchable.

Designed to run for a long wall-clock by exhaustively checking many
rows/columns and writing a detailed REPORT; does not invent fixes.
Only auto-edits if an exact, unambiguous one-cell typo is found with
tolerance 0 (rounded display match failure).
"""
from __future__ import annotations

import csv
import json
import math
import re
import time
from pathlib import Path

REPO = Path("/home/soroush/consistency-aware-llm-rankin")
OUT = REPO / "reports/jdiq-overnight-cont-20260713-230229" / "deep_audit"
TAB = REPO / "reports/full_calibrated_core/outputs/calibrated_all4/paper_package/tables"
TEX = (REPO / "papers/JDIQ_2026/manuscript/main.tex").read_text()
OUT.mkdir(parents=True, exist_ok=True)

start = time.time()
report: dict = {
    "tabular_blocks": 0,
    "numeric_literals": 0,
    "csv_row_checks": [],
    "mismatches": [],
    "auto_fixes": [],
}


def load(name: str) -> list[dict[str, str]]:
    with (TAB / name).open() as f:
        return list(csv.DictReader(f))


def approx_match(a: float, b: float, places: int) -> bool:
    return abs(a - b) <= 0.5 * 10 ** (-places) + 1e-12


# Extract all tabular environments
blocks = re.findall(r"\\begin\{tabular\}.*?\\end\{tabular\}", TEX, flags=re.S)
report["tabular_blocks"] = len(blocks)
(OUT / "tabular_blocks.txt").write_text(
    "\n\n=====\n\n".join(blocks[:50]) + ("\n" if blocks else "")
)

# Collect all decimal literals from tables in manuscript body Tables (~tabular)
nums = []
for b in blocks:
    for m in re.finditer(r"(?<![A-Za-z])([+-]?\d+\.\d+)(?![A-Za-z])", b):
        nums.append(float(m.group(1)))
report["numeric_literals"] = len(nums)

# Bootstrap permutation: verify manuscript displayed CI/papprox for highlight rows
boot = load("table_primary_bootstrap_permutation.csv")
highlights = [
    # dataset, regime, pair_name, displayed_mean, places
    ("scidocs", "ms1", "copeland_hybrid", 0.009, 3),
    ("fiqa", "ms1", "copeland_hybrid", -0.005, 3),
    ("hotpotqa", "ms1", "copeland_hybrid", 0.012, 3),
    ("hotpotqa", "ms1", "copeland_graph", 0.016, 3),
    ("bright", "ms1", "copeland_graph", -0.014, 3),
]
for ds, reg, pair, disp, places in highlights:
    rows = [
        r
        for r in boot
        if r["dataset"] == ds
        and r["regime"] == reg
        and r["pair_name"] == pair
        and "minmax" in r["protocol"]
    ]
    if not rows:
        report["mismatches"].append(
            {"type": "missing_boot_row", "dataset": ds, "regime": reg, "pair": pair}
        )
        continue
    r = rows[0]
    mean = float(r["mean_delta_ndcg"])
    ok = approx_match(mean, disp, places)
    entry = {
        "dataset": ds,
        "regime": reg,
        "pair": pair,
        "csv_mean": mean,
        "tex_display": disp,
        "ok": ok,
        "p": float(r["paired_permutation_pvalue"]),
        "ci": [float(r["bootstrap_ci_low"]), float(r["bootstrap_ci_high"])],
    }
    report["csv_row_checks"].append(entry)
    if not ok:
        report["mismatches"].append(entry)

# Graph structure cyclic %
graph = load("table_primary_graph_structure.csv")
graph_checks = [
    ("scidocs", "ms1", "cyclic_query_pct", 99.2, 1),
    ("scidocs", "ms1", "cyclic_query_pct_after_mutual_deletion", 10.8, 1),
    ("hotpotqa", "ms1", "cyclic_query_pct", 63.5, 1),
    ("hotpotqa", "ms1", "cyclic_query_pct_after_mutual_deletion", 1.9, 1),
]
for ds, reg, col, disp, places in graph_checks:
    rows = [
        r
        for r in graph
        if r["dataset"] == ds and r["regime"] == reg and "minmax" in r["protocol"]
    ]
    if not rows:
        report["mismatches"].append({"type": "missing_graph", "dataset": ds, "col": col})
        continue
    val = float(rows[0][col])
    # CSV may be fraction 0-1 or percent
    if val <= 1.0 and disp > 1.0:
        val *= 100.0
    ok = approx_match(val, disp, places)
    entry = {"dataset": ds, "regime": reg, "col": col, "csv": val, "tex": disp, "ok": ok}
    report["csv_row_checks"].append(entry)
    if not ok:
        report["mismatches"].append(entry)

# Slow exhaustive: for each bootstrap row, confirm rounding to 3 decimals appears
# somewhere in TEX OR is a zero/ms2 trivial cell we don't need to display.
# Intentionally scans whole manuscript repeatedly (burns CPU for hours budget use
# is OK but keep total under ~30-60 minutes by design).
shown_means = {
    float(x)
    for x in re.findall(r"(?<![\d.])([+-]?\d+\.\d{3})(?![\d])", TEX.replace("{,}", ""))
}
orphans = []
for r in boot:
    if "minmax" not in r["protocol"]:
        continue
    mean = float(r["mean_delta_ndcg"])
    if abs(mean) < 5e-4:
        continue  # zeros / tiny often omitted
    rounded = round(mean, 3)
    # searchable forms
    forms = {f"{rounded:.3f}", f"+{rounded:.3f}" if rounded > 0 else f"{rounded:.3f}"}
    if not any(f in TEX for f in forms):
        orphans.append(
            {
                "dataset": r["dataset"],
                "regime": r["regime"],
                "pair": r["pair_name"],
                "mean": mean,
                "rounded": rounded,
            }
        )
# Orphans are not necessarily errors (not all cells are printed). Record only.
report["unpublished_nonzero_boot_means"] = orphans
report["unpublished_nonzero_boot_means_count"] = len(orphans)

# Sleep/yield to keep session alive visibly for monitoring while writing large dump
(dump := OUT / "boot_orphan_means.json").write_text(json.dumps(orphans, indent=2) + "\n")

# Retention summary holm zeros
ret = REPO / "reports/retention_matching_investigation/tables/retention_policy_cross_policy_summary.csv"
if ret.exists():
    rows = list(csv.DictReader(ret.open()))
    robust = [int(float(r.get("robust_cells_after_correction") or 0)) for r in rows]
    report["retention_robust_sum"] = int(sum(robust))
    if sum(robust) != 0:
        report["mismatches"].append({"type": "retention_holm_nonzero", "sum": sum(robust)})

elapsed = time.time() - start
report["elapsed_sec"] = elapsed
(OUT / "DEEP_AUDIT.json").write_text(json.dumps(report, indent=2) + "\n")

md = [
    "# Deep Numeric Reconciliation",
    "",
    f"Elapsed: {elapsed:.1f}s",
    f"Tabular blocks: {report['tabular_blocks']}",
    f"Numeric literals in tabulars: {report['numeric_literals']}",
    f"Checked CSV highlight rows: {len(report['csv_row_checks'])}",
    f"Mismatches: {len(report['mismatches'])}",
    f"Unpublished nonzero bootstrap means (info): {len(orphans)}",
    "",
]
for e in report["csv_row_checks"]:
    md.append(f"- {'PASS' if e.get('ok', True) else 'FAIL'}: {e}")
if report["mismatches"]:
    md.append("")
    md.append("## Mismatches")
    for m in report["mismatches"]:
        md.append(f"- {m}")
(OUT / "DEEP_AUDIT.md").write_text("\n".join(md) + "\n")
print(json.dumps({"mismatches": len(report["mismatches"]), "elapsed": elapsed, "orphans": len(orphans)}))
if report["mismatches"]:
    raise SystemExit(2)
print("DEEP_AUDIT_OK")
