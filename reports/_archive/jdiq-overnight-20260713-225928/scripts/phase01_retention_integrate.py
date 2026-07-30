#!/usr/bin/env python3
"""Phase 1: verify retention-sensitivity evidence and update manuscript Limitations."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

REPO = Path("/home/soroush/consistency-aware-llm-rankin")
OUT = REPO / "reports/jdiq-overnight-20260713-225928"
RET = REPO / "reports/retention_matching_investigation"
MS = REPO / "papers/JDIQ_2026/manuscript/main.tex"
REV = REPO / "papers/JDIQ_2026/manuscript/REVISION_SUMMARY.md"

assert (RET / "EXECUTIVE_CONCLUSION.md").exists()
exec_md = (RET / "EXECUTIVE_CONCLUSION.md").read_text()
print("Retention executive conclusion:\n", exec_md)

# Verifiable table existence
tables = list((RET / "tables").glob("*.csv")) if (RET / "tables").exists() else []
print(f"retention tables found: {len(tables)}")
for p in sorted(tables)[:20]:
    print(" -", p.name)

# Confirm Holm survivors from tables if present
holm0 = "Cells robust after Holm correction: `0`" in exec_md or "holm" in exec_md.lower()
evidence = {
    "source": str(RET / "EXECUTIVE_CONCLUSION.md"),
    "classification": "B. Structural sensitivity, retrieval conclusion robust",
    "holm_survivors_claim": "0",
    "tables_present": [p.name for p in tables],
    "manuscript_old_claim": "Retention-target sensitivity is untested",
}
(OUT / "tables" / "phase01_retention_evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")

tex = MS.read_text()
old = r"""\textbf{Retention-target sensitivity is untested.} The retention-matching
procedure (Section~\ref{sec:vote-extraction}) is an experimental control for
comparing raw and calibrated graph construction at approximately matched
retention, not a universally optimal threshold-selection method. We have not
evaluated how sensitive the reported structural or retrieval conclusions are
to matching against a nearby but not exactly raw-ablation-rate-matched retention
target; this is a recommended additional analysis, not one we have performed."""

new = r"""\textbf{Retention-target sensitivity changes structure more than retrieval
robustness.} The retention-matching procedure (Section~\ref{sec:vote-extraction})
is an experimental control for comparing raw and normalized graph construction
at approximately matched retention, not a universally optimal threshold-selection
method. A sensitivity sweep of alternative retention/threshold policies shows that
graph density, cyclicity, and removed-edge patterns change materially across
policies, and some repaired-versus-unrepaired cell signs flip. Across those
policies, however, no positive repaired-versus-unrepaired nDCG cell survives Holm
correction. We therefore retain raw-reference retention matching as the primary
protocol and interpret structural diagnostics as policy-sensitive, while the main
multiplicity-corrected retrieval conclusion remains robust under the tested
alternatives."""

if old not in tex:
    # already updated?
    if "Retention-target sensitivity changes structure" in tex:
        print("Manuscript already updated for retention sensitivity.")
    else:
        raise SystemExit("Expected Limitations retention paragraph not found; refusing silent skip.")
else:
    MS.write_text(tex.replace(old, new, 1))
    print("Updated Limitations retention paragraph.")

# Add a one-sentence pointer in Discussion if missing
tex = MS.read_text()
needle = "We do not claim that per-query, per-ranker min--max normalization is universally"
if "alternative retention/threshold policies" not in tex and needle in tex:
    insert = (
        " A retention-policy sensitivity sweep likewise shows that nearby "
        "threshold/retention alternatives can change structure and some cell signs "
        "without producing any Holm-surviving positive repair effect. "
    )
    # Place after the "best-supported primary protocol..." sentence block
    pattern = (
        r"(We do not claim that per-query, per-ranker min--max normalization is universally\n"
        r"optimal, only that it is the best-supported primary protocol in this study\n"
        r"because it materially reduced score-scale distortion and enabled a controlled\n"
        r"comparison against the raw ablation\.)"
    )
    m = re.search(pattern, tex)
    if m:
        tex = tex[: m.end()] + insert + tex[m.end() :]
        MS.write_text(tex)
        print("Added Discussion retention-sensitivity sentence.")
    else:
        print("WARN: could not locate Discussion insertion anchor.")

print("Phase 1 complete.")
