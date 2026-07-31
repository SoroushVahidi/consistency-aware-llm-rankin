"""
validate_report_links.py
==========================
Repo Stage 4 (2026-07-30): validates that every local (non-URL) Markdown
link in a small set of key repository documents actually resolves to a
file that exists on disk. This is a structural link check, not a content
check -- it does not verify the linked file's content is accurate, only
that the path is not broken (e.g. left dangling by a Stage 2 file move
that missed updating one reference).

Checked by default: reports/README.md, README.md,
docs/READ_ME_FIRST_FOR_AI.md, docs/REPOSITORY_LAYOUT.md, docs/EXPERIMENTS.md,
docs/EXPERIMENT_ARTIFACT_POLICY.md, docs/ARCHITECTURE.md,
docs/RELEASE_READINESS.md -- the documents most affected by file moves and
reference rewrites, plus the top-level architecture, artifact-policy, and
release guides. Pass --files to check a different/additional set.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_FILES = [
    "reports/README.md",
    "README.md",
    "AGENTS.md",
    "docs/READ_ME_FIRST_FOR_AI.md",
    "docs/REPOSITORY_LAYOUT.md",
    "docs/EXPERIMENTS.md",
    "docs/EXPERIMENT_ARTIFACT_POLICY.md",
    "docs/ARCHITECTURE.md",
    "docs/RELEASE_READINESS.md",
    "docs/CONTRIBUTIONS.md",
    "docs/PROJECT_STATUS.md",
    "docs/AGENT_GUIDE.md",
    "docs/RELEASE_CHECKLIST.md",
    "docs/MAINTENANCE.md",
    "CONTRIBUTING.md",
]

_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_EXTERNAL_PREFIXES = ("http://", "https://", "mailto:")


def extract_local_links(markdown_text: str) -> list[str]:
    links = []
    for match in _LINK_RE.finditer(markdown_text):
        target = match.group(1).strip()
        if target.startswith(_EXTERNAL_PREFIXES):
            continue
        if target.startswith("#"):
            continue  # in-page anchor only
        links.append(target)
    return links


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(_REPO_ROOT))
    except ValueError:
        return str(path)


def check_file(doc_path: Path) -> dict:
    if not doc_path.exists():
        return {
            "file": _display_path(doc_path),
            "status": "FILE_NOT_FOUND",
            "links": [],
        }

    text = doc_path.read_text(encoding="utf-8")
    links = extract_local_links(text)
    results = []
    for link in links:
        target = link.split("#", 1)[0]  # drop any in-target anchor fragment
        if not target:
            continue  # pure anchor already filtered, but be defensive
        resolved = (doc_path.parent / target).resolve()
        results.append({
            "link": link,
            "resolved_path": str(resolved),
            "exists": resolved.exists(),
        })

    n_broken = sum(1 for r in results if not r["exists"])
    return {
        "file": _display_path(doc_path),
        "status": "OK" if n_broken == 0 else "BROKEN_LINKS",
        "n_links_checked": len(results),
        "n_broken": n_broken,
        "links": [r for r in results if not r["exists"]],
    }


def run(files: list[str]) -> dict:
    file_results = [check_file(_REPO_ROOT / f) for f in files]
    n_bad = sum(1 for r in file_results if r["status"] != "OK")
    return {
        "overall_status": "PASS" if n_bad == 0 else "FAIL",
        "files_checked": files,
        "n_files_with_issues": n_bad,
        "results": file_results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--files", nargs="+", default=DEFAULT_FILES)
    args = parser.parse_args()
    result = run(args.files)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["overall_status"] == "PASS" else 1)
