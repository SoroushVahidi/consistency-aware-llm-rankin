#!/usr/bin/env python3
"""Fix Methods section that still claims retention sensitivity is untested."""
from __future__ import annotations

from pathlib import Path

REPO = Path("/home/soroush/consistency-aware-llm-rankin")
MS = REPO / "papers/JDIQ_2026/manuscript/main.tex"
OUT = REPO / "reports/jdiq-overnight-cont-20260713-230229"
REV = REPO / "papers/JDIQ_2026/manuscript/REVISION_SUMMARY.md"

OLD = (
    "procedure is therefore neither a universally optimal threshold-selection\n"
    "method nor a qrels-tuned one, and we do not present it as either. We also do\n"
    "not evaluate how sensitive the reported structural or retrieval conclusions\n"
    "are to matching against a nearby but not exactly raw-ablation-rate-matched\n"
    "retention target; we flag that as a recommended, not yet performed, sensitivity\n"
    "analysis in Section~\\ref{sec:threats}."
)

NEW = (
    "procedure is therefore neither a universally optimal threshold-selection\n"
    "method nor a qrels-tuned one, and we do not present it as either. A sensitivity\n"
    "sweep of nearby retention/threshold policies (Section~\\ref{sec:threats}) shows that\n"
    "graph density, cyclicity, and removed-edge patterns can change, and that some\n"
    "repaired-versus-unrepaired cell signs flip, while no positive cell survives Holm\n"
    "correction under those alternatives. We therefore retain raw-reference retention\n"
    "matching as the primary protocol rather than treating any single nearby target as\n"
    "universally optimal."
)

text = MS.read_text()
if OLD not in text:
    if "recommended, not yet performed, sensitivity" in text:
        raise SystemExit("OLD block not found verbatim; residual untested claim remains")
    print("Methods retention paragraph already updated.")
else:
    MS.write_text(text.replace(OLD, NEW, 1))
    print("Updated Methods retention-sensitivity paragraph.")

# Sync REVISION_SUMMARY leftover risk bullet
rev = REV.read_text()
rev2 = rev.replace(
    "5. Retention-target sensitivity still untested.\n",
    "5. Retention-target sensitivity integrated (structure changes; Holm survivors still 0).\n",
)
rev2 = rev2.replace(
    "- CombMNZ exploratory: n/a\n",
    "- CombMNZ exploratory: see continuation overnight report (computed).\n",
)
if rev2 != rev:
    REV.write_text(rev2)
    print("Updated REVISION_SUMMARY risk list.")

# Also scrub PRE_SUBMISSION outdated guidance if it still praises "not yet performed"
pre = REPO / "papers/JDIQ_2026/manuscript/PRE_SUBMISSION_REVIEW.md"
if pre.exists():
    p = pre.read_text()
    note = (
        "\n\n---\n\n## Overnight status note (2026-07-13)\n\n"
        "Retention-target sensitivity is **no longer** an untested gap: an existing "
        "policy sweep was integrated into Methods/Limitations. Do not reinstate the "
        "\"not yet performed\" phrasing.\n"
    )
    if "Overnight status note (2026-07-13)" not in p:
        pre.write_text(p.rstrip() + note)
        print("Annotated PRE_SUBMISSION_REVIEW.md")

(OUT / "tables" / "phase01_methods_fix.json").write_text(
    '{\n  "methods_updated": true,\n  "residual_untested_phrase": '
    + ("true" if "not yet performed" in MS.read_text() else "false")
    + "\n}\n"
)
print("Phase 1 complete.")
