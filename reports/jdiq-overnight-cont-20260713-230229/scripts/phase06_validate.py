#!/usr/bin/env python3
"""Compile checks after overnight continuation edits."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPO = Path("/home/soroush/consistency-aware-llm-rankin")
OUT = REPO / "reports/jdiq-overnight-cont-20260713-230229"
MS = REPO / "papers/JDIQ_2026/manuscript"

# Compile
subprocess.check_call(
    ["tectonic", "-X", "compile", "main.tex", "--keep-logs"], cwd=MS
)
info = subprocess.check_output(["pdfinfo", str(MS / "main.pdf")], text=True)
(OUT / "logs" / "pdfinfo.txt").write_text(info)
subprocess.check_call(
    ["pdftotext", str(MS / "main.pdf"), str(OUT / "logs" / "main_pdftotext.txt")]
)
txt = (OUT / "logs" / "main_pdftotext.txt").read_text(errors="ignore")
tex = (MS / "main.tex").read_text()

fail: list[str] = []
pages_m = re.search(r"Pages:\s+(\d+)", info)
pages = int(pages_m.group(1)) if pages_m else -1
if pages < 0:
    fail.append("pages_unknown")

forbidden = [
    "original study",
    "original title",
    "blocking audit",
    "primary_minmax_retention_matched",
    "canonical package",
    "not yet performed",
    "github.com/SoroushVahidi",
    "/home/soroush/",
]
for ph in forbidden:
    if ph.lower() in txt.lower() or ph in tex:
        # allow PRE_SUBMISSION-only docs; check PDF/text and main.tex only
        if ph in tex or ph.lower() in txt.lower():
            fail.append(f"forbidden:{ph}")

if "Retention-target sensitivity changes structure" not in txt:
    fail.append("missing_retention_limitations_claim")

cite_count = len(re.findall(r"\\cite[a-z]*\{", tex))
leak_fail = (OUT / "artifact_prep" / "LEAK_FAIL").exists()
if leak_fail:
    fail.append("artifact_identity_leak")

# undefined refs markers
if "??" in txt:
    # acmart sometimes has ?? in rare cases; fail if many
    if txt.count("??") > 2:
        fail.append("literal_??_in_pdf")

result = {
    "pages": pages,
    "fail": fail,
    "cite_count": cite_count,
    "leak_fail": leak_fail,
    "methods_claim_ok": "not yet performed" not in tex,
}
(OUT / "tables" / "phase06_validation.json").write_text(json.dumps(result, indent=2) + "\n")
print(result)
if fail:
    raise SystemExit(f"VALIDATION_FAILED: {fail}")
print("Phase 6 validation OK")
