#!/usr/bin/env python3
"""Remove identity-revealing absolute home path from processor.py."""
from __future__ import annotations

from pathlib import Path

REPO = Path("/home/soroush/consistency-aware-llm-rankin")
PATH = REPO / "src/consistency_ranker/repair_selector_mining/processor.py"
OUT = REPO / "reports/jdiq-overnight-cont-20260713-230229"

text = PATH.read_text()
old = '            caar_solver = Path("/home/soroush/consistency-aware-llm-rankin-caar/src/consistency_ranker/mwfas_solver.py")\n'
new = (
    "            # Optional sibling checkout; avoid hardcoded home-directory identity leaks.\n"
    "            repo_root = Path(__file__).resolve().parents[3]\n"
    "            caar_solver = (\n"
    '                repo_root.parent\n'
    '                / "consistency-aware-llm-rankin-caar"\n'
    '                / "src"\n'
    '                / "consistency_ranker"\n'
    '                / "mwfas_solver.py"\n'
    "            )\n"
)
if "/home/soroush/" not in text:
    print("No /home/soroush/ leak in processor.py")
elif old not in text:
    raise SystemExit("Expected hardcoded path not found; refuse to guess")
else:
    PATH.write_text(text.replace(old, new, 1))
    print("Replaced hardcoded home path with sibling-relative Path.")

# Repo-wide src leak check
hits = []
for p in (REPO / "src").rglob("*.py"):
    t = p.read_text(errors="ignore")
    if "/home/soroush/" in t:
        hits.append(str(p.relative_to(REPO)))
(OUT / "tables" / "phase02_src_leaks.json").write_text(
    __import__("json").dumps({"src_home_path_leaks": hits}, indent=2) + "\n"
)
print("src leaks remaining:", hits)
print("Phase 2 complete.")
