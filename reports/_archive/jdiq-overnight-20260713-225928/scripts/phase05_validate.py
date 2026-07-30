#!/usr/bin/env python3
"""Phase 5: validation checks after compile."""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path("/home/soroush/consistency-aware-llm-rankin")
OUT = REPO / "reports/jdiq-overnight-20260713-225928"
MS = REPO / "papers/JDIQ_2026/manuscript"
pdf_txt = (OUT / "logs" / "main_pdftotext.txt").read_text(errors="ignore")
tex = (MS / "main.tex").read_text()
bib = (MS / "references.bib").read_text()

fail = []
if "??" in pdf_txt:
    fail.append("literal ?? in PDF text")
for bad in [
    "original study",
    "original title",
    "blocking audit",
    "primary_minmax_retention_matched",
    "canonical package",
    "github.com/SoroushVahidi",
]:
    if bad.lower() in pdf_txt.lower():
        fail.append(f"forbidden phrase in PDF: {bad}")

cites = set()
for g in re.findall(r"\\cite[a-zA-Z]*\{([^}]+)\}", tex):
    for k in g.split(","):
        cites.add(k.strip())
missing = [k for k in sorted(cites) if ("{" + k + ",") not in bib]
if missing:
    fail.append(f"missing bib keys: {missing}")

labels = set(re.findall(r"\\label\{([^}]+)\}", tex))
refs = set()
for g in re.findall(r"\\(?:ref|eqref)\{([^}]+)\}", tex):
    for k in g.split(","):
        refs.add(k.strip())
undef = sorted(refs - labels)
if undef:
    fail.append(f"undefined refs: {undef}")

# page count from pdfinfo log if present
pages = None
info = (OUT / "logs" / "pdfinfo.txt").read_text() if (OUT / "logs" / "pdfinfo.txt").exists() else ""
m = re.search(r"Pages:\s+(\d+)", info)
if m:
    pages = int(m.group(1))

report = {
    "pages": pages,
    "fail": fail,
    "cite_count": len(cites),
    "retention_claim_updated": "Retention-target sensitivity changes structure" in tex,
}
(OUT / "tables" / "phase05_validation.json").write_text(__import__("json").dumps(report, indent=2) + "\n")
print(report)
if fail:
    raise SystemExit("VALIDATION FAILED: " + "; ".join(fail))
print("Phase 5 validation OK")
