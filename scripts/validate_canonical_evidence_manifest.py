"""
validate_canonical_evidence_manifest.py
=========================================
Repo Stage 4 (2026-07-30): validates that every path referenced by the
canonical evidence inventory
(reports/repo_preparation_stage1_20260730T011354Z/canonical_evidence_inventory.csv,
17 rows: CB-01..CB-09 classical backbone, LLM-01..LLM-05 real-LLM studies,
AUD-01..AUD-03 audits, IR-PENDING-01 historical/resolved marker) actually
exists on disk. This is a structural check (do the cited files exist), not a
numeric re-verification (that is what reproduce-ir-audit /
reproduce-real-llm-reanalysis, and the offline validation workflow that
calls them, are for).

`source_data_path`, `generating_script`, and `report_path` are free-text
fields written by a human across several stages of this research thread --
they mix real paths with prose ("(see that report's own scripts
directory)", "would reuse extraction_results.jsonl ..."), semicolon-
separated lists, glob-style wildcards (`*`), and brace-expansion-style
alternatives (`{a,b,c}`). This script extracts every path-shaped token it
can find and checks each one; a field with no path-shaped token at all is
reported as NO_PATH_FOUND (expected/benign for historical or narrative
rows), never silently skipped without a trace.
"""

from __future__ import annotations

import csv
import glob
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

_INVENTORY_PATH = (
    _REPO_ROOT
    / "reports/repo_preparation_stage1_20260730T011354Z/canonical_evidence_inventory.csv"
)

_PATH_PREFIXES = (
    "reports/", "scripts/", "src/", "papers/", "outputs/", "docs/", "data/", "tests/",
)

# Known elliptical aliases used in free-text fields (e.g. "main.tex Sec.4.1"
# instead of the full "papers/JDIQ_2026/manuscript/main.tex") -- these are a
# fixed, small set of well-known references repeated verbatim across the
# inventory, not a guess about an arbitrary bare filename.
_ALIASES = {
    "main.tex": "papers/JDIQ_2026/manuscript/main.tex",
}


def _expand_braces(token: str) -> list[str]:
    match = re.search(r"\{([^}]+)\}", token)
    if not match:
        return [token]
    options = match.group(1).split(",")
    prefix, suffix = token[: match.start()], token[match.end() :]
    return [prefix + opt + suffix for opt in options]


def extract_path_candidates(field: str) -> list[str]:
    """Best-effort extraction of path-shaped tokens from a free-text field."""
    candidates: list[str] = []
    for segment in field.split(";"):
        # Parenthetical asides are prose ("(run_full_core())", "(not yet...)"),
        # never part of a real path in this inventory -- drop them.
        seg = segment.split("(")[0].strip()
        for raw_tok in seg.split():
            tok = raw_tok.strip(",.'\"")
            if tok in _ALIASES:
                candidates.append(_ALIASES[tok])
            elif tok.startswith(_PATH_PREFIXES):
                candidates.extend(_expand_braces(tok))
    return candidates


def path_exists(candidate: str) -> bool:
    if "*" in candidate or "{" in candidate:
        return len(glob.glob(str(_REPO_ROOT / candidate))) > 0
    return (_REPO_ROOT / candidate).exists()


def validate_row(row: dict) -> dict:
    field_results = {}
    for field_name in ("source_data_path", "generating_script", "report_path"):
        candidates = extract_path_candidates(row[field_name])
        if not candidates:
            field_results[field_name] = {"status": "NO_PATH_FOUND", "candidates": []}
            continue
        checked = [{"path": c, "exists": path_exists(c)} for c in candidates]
        all_exist = all(c["exists"] for c in checked)
        field_results[field_name] = {
            "status": "OK" if all_exist else "MISSING",
            "candidates": checked,
        }
    row_ok = all(
        field_results[f]["status"] in ("OK", "NO_PATH_FOUND")
        for f in field_results
    )
    return {
        "result_id": row["result_id"],
        "row_status": "OK" if row_ok else "MISSING_PATHS",
        "fields": field_results,
    }


def run() -> dict:
    if not _INVENTORY_PATH.exists():
        return {
            "overall_status": "FAIL",
            "reason": f"Canonical evidence inventory not found at {_INVENTORY_PATH}",
            "rows": [],
        }

    with _INVENTORY_PATH.open() as f:
        rows = list(csv.DictReader(f))

    results = [validate_row(r) for r in rows]
    n_missing = sum(1 for r in results if r["row_status"] == "MISSING_PATHS")

    return {
        "overall_status": "PASS" if n_missing == 0 else "FAIL",
        "inventory_path": str(_INVENTORY_PATH.relative_to(_REPO_ROOT)),
        "n_rows_checked": len(results),
        "n_rows_with_missing_paths": n_missing,
        "rows": results,
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["overall_status"] == "PASS" else 1)
