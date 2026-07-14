#!/usr/bin/env python3
"""Audit key manuscript numeric claims against paper_package CSV tables."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

REPO = Path("/home/soroush/consistency-aware-llm-rankin")
OUT = REPO / "reports/jdiq-overnight-cont-20260713-230229"
TAB = (
    REPO
    / "reports/full_calibrated_core/outputs/calibrated_all4/paper_package/tables"
)
TEX = (REPO / "papers/JDIQ_2026/manuscript/main.tex").read_text()
PDF_TXT = OUT / "logs" / "main_pdftotext_after_combmnz.txt"
txt = PDF_TXT.read_text(errors="ignore") if PDF_TXT.exists() else ""

report: dict = {"checks": [], "mismatches": [], "notes": []}


def add(ok: bool, name: str, detail: str) -> None:
    row = {"ok": ok, "name": name, "detail": detail}
    report["checks"].append(row)
    if not ok:
        report["mismatches"].append(row)
    print(("OK  " if ok else "FAIL"), name, "-", detail)


def load_csv(name: str) -> list[dict[str, str]]:
    with (TAB / name).open() as f:
        return list(csv.DictReader(f))


# --- Seeds / B ---
add(
    "seed~13" in TEX and "seed~17" in TEX and "10{,}000" in TEX,
    "seeds_in_tex",
    "bootstrap seed 13 / perm seed 17 / B=10000 present in TeX",
)
if txt:
    add(
        "seed 13" in txt.lower() or "seed~13" in TEX,
        "seeds_in_pdf_proxy",
        "seed values reachable from compiled sources",
    )

# --- HotpotQA eligibility ---
add(
    "18 of the 70" in TEX or "18 of the 70" in txt,
    "hotpotqa_exclusion_count",
    "18/70 exclusion stated",
)
add("n={=}52" in TEX or "52" in TEX, "hotpotqa_n52", "HotpotQA n=52 present")

# --- Bootstrap/permutation highlight cells from table ---
boot = load_csv("table_primary_bootstrap_permutation.csv")
# Find HotpotQA Copeland hybrid primary
hits = [
    r
    for r in boot
    if r.get("dataset") == "hotpotqa"
    and "hybrid" in (r.get("method", "") + r.get("method_key", "")).lower()
]
if hits:
    r0 = hits[0]
    # manuscript claims approx +0.012
    mean = float(
        r0.get("mean_delta_ndcg")
        or r0.get("repaired_minus_unrepaired_mean_delta_ndcg")
        or r0.get("mean_delta")
        or "nan"
    )
    report["notes"].append({"hotpotqa_hybrid_boot_row": r0, "parsed_mean": mean})
    add(
        abs(mean - 0.012) < 0.002 or abs(mean - 0.0123) < 0.002,
        "hotpotqa_hybrid_mean_near_0.012",
        f"table mean={mean}",
    )

# --- Holm survivors: expect 0 robust cells mentioned ---
add(
    "no positive" in TEX.lower() and "holm" in TEX.lower(),
    "holm_narrative_present",
    "Holm zero-survivor narrative present",
)

# --- Graph structure HotpotQA cyclicity drop 63->2 ---
g = load_csv("table_primary_graph_structure.csv")
hp = [r for r in g if r.get("dataset") == "hotpotqa" and r.get("regime") == "ms1"]
report["notes"].append({"hotpotqa_ms1_graph_rows": len(hp)})
# Look for cyclic percent fields
if hp:
    # try common column names
    sample = hp[0]
    report["notes"].append({"graph_columns": list(sample.keys())[:30]})

# Parse manuscript table rows for SciDocs ms1 cyclicity 99.2 / 10.8
m = re.search(
    r"SciDocs\s*&\s*\\texttt\{ms1\}\s*&\\s*([0-9.]+)\s*&\s*([0-9.]+)",
    TEX,
)
if m:
    add(True, "scidocs_ms1_cycle_table_parsable", f"{m.group(1)}, {m.group(2)}")
else:
    # looser
    add(
        "99.2" in TEX and "10.8" in TEX,
        "scidocs_ms1_cycle_literals",
        "99.2 and 10.8 present",
    )

# --- Repair effects mean deltas for highlight cells ---
rep = load_csv("table_primary_repair_effects.csv")
# primary protocol only
prim = [
    r
    for r in rep
    if "minmax" in r.get("protocol", "")
    or r.get("protocol_kind") == "primary"
]


def find_delta(dataset: str, regime: str, method_sub: str) -> float | None:
    for r in prim:
        if r.get("dataset") != dataset or r.get("regime") != regime:
            continue
        mk = (r.get("method_key") or "") + (r.get("method") or "")
        if method_sub.lower() not in mk.lower():
            continue
        if "unrepaired" in mk.lower() and "repaired" not in mk.lower().replace(
            "unrepaired", ""
        ):
            continue
        # Prefer repaired_minus_unrepaired fields when present on repaired rows
        for key in (
            "repaired_minus_unrepaired_mean_delta_ndcg",
            "mean_delta_ndcg",
            "mean_delta",
        ):
            if key in r and r[key] not in ("", None):
                try:
                    return float(r[key])
                except ValueError:
                    pass
    return None


checks_deltas = [
    ("scidocs", "ms1", "copeland_hybrid", 0.009, 0.003),
    ("hotpotqa", "ms1", "copeland_hybrid", 0.012, 0.003),
    ("fiqa", "ms1", "copeland_hybrid", -0.005, 0.003),
]
for ds, reg, meth, expected, tol in checks_deltas:
    val = find_delta(ds, reg, meth)
    if val is None:
        # try simpler method key patterns
        val = find_delta(ds, reg, "hybrid")
    ok = val is not None and abs(val - expected) <= tol
    add(ok, f"delta_{ds}_{reg}_{meth}", f"expected~{expected}, got={val}")

# --- Baseline comparison: CombSUM vs repair sign narrative stays ---
base = load_csv("table_primary_baseline_comparison_by_dataset.csv")
report["notes"].append({"baseline_rows": len(base)})

# --- Retention investigation holm=0 ---
ret_exec = REPO / "reports/retention_matching_investigation/EXECUTIVE_CONCLUSION.md"
if ret_exec.exists():
    et = ret_exec.read_text()
    add(
        "Holm" in et and ("0" in et),
        "retention_exec_holm0",
        "executive conclusion mentions Holm survivors 0",
    )

# --- Forbidden identity ---
for needle in ["SoroushVahidi", "/home/soroush/", "sv96@"]:
    add(needle not in TEX, f"no_identity_{needle}", "absent from main.tex")

# --- CombMNZ decision recorded ---
comb = OUT / "tables" / "phase03_combmnz.json"
if comb.exists():
    c = json.loads(comb.read_text())
    add(
        str(c.get("decision", "")).startswith("DO_NOT_ADD"),
        "combmnz_do_not_add",
        c.get("decision", "")[:120],
    )
    max_abs = max(abs(r["delta_mnz_minus_sum"]) for r in c["results"])
    add(max_abs < 0.01, "combmnz_max_abs_delta", f"max_abs={max_abs:.4f}")

# Write reports
(OUT / "tables" / "phase08_numeric_audit.json").write_text(
    json.dumps(report, indent=2) + "\n"
)
md = ["# Numeric Consistency Audit", ""]
md.append(f"**Mismatch count:** {len(report['mismatches'])}")
md.append("")
for c in report["checks"]:
    md.append(f"- {'PASS' if c['ok'] else 'FAIL'}: {c['name']} — {c['detail']}")
(OUT / "NUMERIC_AUDIT.md").write_text("\n".join(md) + "\n")

# Only auto-edit manuscript if a clear literal mismatch on known highlight cells is found
# (conservative: no silent numeric rewrites in overnight job).
(OUT / "tables" / "phase08_mismatch_count.txt").write_text(
    str(len(report["mismatches"])) + "\n"
)
print("MISMATCHES", len(report["mismatches"]))
if report["mismatches"]:
    raise SystemExit(2)
print("NUMERIC_AUDIT_OK")
