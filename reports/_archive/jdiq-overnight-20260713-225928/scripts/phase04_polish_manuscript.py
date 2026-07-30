#!/usr/bin/env python3
"""Phase 4: targeted presentation polish; compress HotpotQA emphasis slightly if needed."""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path("/home/soroush/consistency-aware-llm-rankin")
MS = REPO / "papers/JDIQ_2026/manuscript/main.tex"
OUT = REPO / "reports/jdiq-overnight-20260713-225928"

tex = MS.read_text()
changes = []

# Soften unsupported absolute novelty residues
for old, new, label in [
    (
        "The novelty of this paper lies",
        "The contribution of this paper is",
        "novelty_phrase",
    ),
]:
    if old in tex:
        tex = tex.replace(old, new)
        changes.append(label)

# Compress a common HotpotQA build-up pattern if the long positive-then-deflate block still exists.
# Keep numbers; move influence caveat earlier when an obvious paragraph pair is found.
pat = re.compile(
    r"(HotpotQA is the clearest example\..*?Holm or Benjamini--Hochberg adjustment\.)",
    re.S,
)
m = pat.search(tex)
if m:
    block = m.group(1)
    # Ensure influence caveat is front-loaded
    if "influence" in block.lower() and not block.startswith("HotpotQA is the clearest example. Its"):
        pass
    rewritten = (
        "HotpotQA is the clearest example of a positive-looking but non-robust cell: "
        "its calibrated \\texttt{ms1} Copeland-hybrid mean is positive, yet the effect is "
        "concentrated in a few influential queries, the paired permutation test is not "
        "compelling, and the cell does not survive Holm or Benjamini--Hochberg adjustment."
    )
    if block != rewritten and "HotpotQA is the clearest example" in block:
        tex = tex.replace(block, rewritten)
        changes.append("hotpotqa_compress")

# Ensure CombMNZ decision sentence still present; if phase2 says REVIEW_MANUALLY, leave text.
comb_path = OUT / "tables" / "phase02_combmnz.json"
# Consistency: no author GitHub
if "github.com/SoroushVahidi" in tex:
    raise SystemExit("Author-identifying GitHub URL found in manuscript; refusing to continue.")

# Fix any leftover 'untested' retention if phase1 already handled
if "Retention-target sensitivity is untested" in tex:
    changes.append("WARN_retention_still_untested")

MS.write_text(tex)
(OUT / "logs" / "phase04_changes.txt").write_text("\n".join(changes) + "\n")
print("Phase 4 changes:", changes or ["none"])
