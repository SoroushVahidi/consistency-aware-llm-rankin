#!/usr/bin/env python3
"""
validate_repo_clarity.py
=========================
Repository-clarity validator: checks that the GitHub-visible documentation
hierarchy stays internally consistent as the repo evolves, so a future
coding/research agent does not have to re-derive "which document is
authoritative" from scratch.

Checks:
1. Every required canonical document exists.
2. README.md links to every one of them.
3. The two PROJECT_STATUS.md files (root and docs/) cross-reference each
   other -- neither may silently claim sole authority without acknowledging
   the other.
4. Any file containing a "SUPERSEDED" banner also names a replacement
   (contains at least one markdown link).
5. No machine-specific local path in active docs (delegates to
   scripts/check_active_portability.py -- not reimplemented here).
6. No active document claims GitHub Actions is green/passing (it currently
   is not, due to an account billing issue -- see docs/PROJECT_STATUS.md).
7. Every `--tier <value>` mentioned in documentation is one of
   scripts/run_cloud_validation.py's actual argparse choices (catches a doc
   drifting out of sync with the CLI, e.g. a typo'd tier name).

This is a structural/consistency check, not a content-quality check --
it cannot tell you if a document's prose is well-written, only that the
required cross-references and documents exist and agree with each other.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

_REQUIRED_DOCS = [
    "README.md",
    "docs/CONTRIBUTIONS.md",
    "docs/PROJECT_STATUS.md",
    "docs/AGENT_GUIDE.md",
    "docs/ARCHITECTURE.md",
    "docs/EXPERIMENTS.md",
    "docs/claim_evidence_registry.yaml",
    "docs/EXPERIMENT_ARTIFACT_POLICY.md",
]

# Docs README must link to (relative-path substring match against README's
# own text -- good enough to catch "forgot to link this" without a full
# markdown-link parser).
_README_MUST_LINK = [
    "docs/CONTRIBUTIONS.md",
    "docs/PROJECT_STATUS.md",
    "docs/AGENT_GUIDE.md",
    "docs/ARCHITECTURE.md",
    "docs/EXPERIMENTS.md",
    "docs/claim_evidence_registry.yaml",
    "docs/EXPERIMENT_ARTIFACT_POLICY.md",
]

# Active docs scanned for "SUPERSEDED must name a replacement" and
# "GitHub Actions must not be claimed green". Top-level docs/*.md only --
# historical/research/handoff subdirectories are allowed to be pure
# historical narrative without this cross-check.
_ACTIVE_DOC_GLOB_DIRS = ["docs", "."]

_GREEN_CI_PATTERNS = [
    re.compile(r"github actions is (green|passing)", re.IGNORECASE),
    re.compile(r"ci is (green|passing)\b", re.IGNORECASE),
    re.compile(r"ci status:?\s*(green|passing)", re.IGNORECASE),
]


def _read(rel_path: str) -> str | None:
    path = _REPO_ROOT / rel_path
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def _top_level_markdown_files() -> list[Path]:
    files = [p for p in (_REPO_ROOT / "docs").glob("*.md")]
    files.append(_REPO_ROOT / "README.md")
    files.append(_REPO_ROOT / "PROJECT_STATUS.md")
    files.append(_REPO_ROOT / "AGENTS.md")
    files.append(_REPO_ROOT / "CONTRIBUTING.md")
    return [f for f in files if f.exists()]


def check_required_docs_exist() -> list[str]:
    errors = []
    for rel in _REQUIRED_DOCS:
        if not (_REPO_ROOT / rel).exists():
            errors.append(f"required document missing: {rel}")
    return errors


def check_readme_links_to_required_docs() -> list[str]:
    readme = _read("README.md")
    if readme is None:
        return ["README.md not found"]
    errors = []
    for rel in _README_MUST_LINK:
        if rel not in readme:
            errors.append(f"README.md does not reference {rel}")
    return errors


def check_project_status_cross_reference() -> list[str]:
    root_status = _read("PROJECT_STATUS.md")
    docs_status = _read("docs/PROJECT_STATUS.md")
    errors = []
    if root_status is not None and "docs/PROJECT_STATUS.md" not in root_status:
        errors.append(
            "root PROJECT_STATUS.md does not reference docs/PROJECT_STATUS.md -- "
            "the two must cross-reference so neither silently claims sole authority"
        )
    if docs_status is not None and "PROJECT_STATUS.md" not in docs_status.replace(
        "docs/PROJECT_STATUS.md", ""
    ):
        errors.append("docs/PROJECT_STATUS.md does not reference the root PROJECT_STATUS.md")
    return errors


_BANNER_MARKER = re.compile(
    # Only matches a banner that OPENS a blockquote paragraph (preceded by
    # start-of-file or a blank line), not "historical"/"superseded" used
    # as a plain adjective mid-paragraph inside an unrelated blockquote --
    # e.g. this must NOT match "> ... rebuilds the **historical** Q1
    # journal bundle ..." (docs/REPRODUCTION_Q1.md, a real false positive
    # found while building this check).
    r"(?:\A|\n\n)>\s*\*\*(SUPERSEDED|HISTORICAL)\b",
    re.IGNORECASE,
)
_DOC_REFERENCE = re.compile(r"(docs/|reports/|papers/)[\w./-]+\.(md|yaml|yml|csv|json|tex)")


def check_superseded_docs_name_a_replacement() -> list[str]:
    """A superseded/historical banner must name a replacement -- as a real
    markdown link `](` or (this repo's actual convention) a backtick/plain
    reference to another doc/report path within the banner's own paragraph
    (the ~500 chars after the marker, not the whole file, so an unrelated
    doc/report path mentioned elsewhere in the file doesn't count)."""
    errors = []
    for path in _top_level_markdown_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in _BANNER_MARKER.finditer(text):
            paragraph = text[m.start() : m.start() + 600]
            if "](" not in paragraph and not _DOC_REFERENCE.search(paragraph):
                line_no = text.count("\n", 0, m.start()) + 1
                errors.append(
                    f"{path.relative_to(_REPO_ROOT)}:{line_no}: a SUPERSEDED/HISTORICAL "
                    "banner here does not name a replacement document within its own "
                    "paragraph (no markdown link or docs/reports/papers path reference)"
                )
    return errors


def check_no_local_paths_in_active_docs() -> list[str]:
    sys.path.insert(0, str(_REPO_ROOT))
    from scripts import check_active_portability

    findings = check_active_portability.scan_active_files()
    return [
        f"{p.relative_to(_REPO_ROOT)}:{line}: machine-specific path {pattern!r}"
        for p, line, pattern in findings
    ]


_NEGATION_WORDS = ("not", "n't", "never", "no ", "isn't", "is not", "cannot", "can't")


def check_no_ci_green_claims() -> list[str]:
    errors = []
    for path in _top_level_markdown_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in _GREEN_CI_PATTERNS:
            for m in pattern.finditer(text):
                # Look at the ~60 chars immediately before the match for a
                # negation ("do not claim...", "is not currently...") --
                # this repo's convention is to explicitly deny the claim,
                # not assert it.
                context_before = text[max(0, m.start() - 60) : m.start()].lower()
                if any(neg in context_before for neg in _NEGATION_WORDS):
                    continue
                line_no = text.count("\n", 0, m.start()) + 1
                errors.append(
                    f"{path.relative_to(_REPO_ROOT)}:{line_no}: appears to claim "
                    f"GitHub Actions/CI is green/passing ({m.group(0)!r}) -- it is "
                    "not, due to a billing issue; see docs/PROJECT_STATUS.md"
                )
    return errors


def check_cloud_validation_tiers_match_cli() -> list[str]:
    script_path = _REPO_ROOT / "scripts" / "run_cloud_validation.py"
    if not script_path.exists():
        return ["scripts/run_cloud_validation.py not found"]
    source = script_path.read_text(encoding="utf-8")
    m = re.search(r'"--tier",\s*choices=\[(.*?)\]', source)
    if not m:
        return ["could not find --tier argparse choices in run_cloud_validation.py"]
    valid_tiers = {t.strip().strip('"').strip("'") for t in m.group(1).split(",")}

    errors = []
    tier_mention = re.compile(r"--tier[= ]([a-zA-Z0-9_-]+)")
    for path in _top_level_markdown_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for m2 in tier_mention.finditer(text):
            tier = m2.group(1)
            if tier not in valid_tiers:
                line_no = text.count("\n", 0, m2.start()) + 1
                errors.append(
                    f"{path.relative_to(_REPO_ROOT)}:{line_no}: documents '--tier {tier}', "
                    f"not one of run_cloud_validation.py's actual choices {sorted(valid_tiers)}"
                )
    return errors


def main() -> int:
    checks = [
        ("required documents exist", check_required_docs_exist),
        ("README links to required documents", check_readme_links_to_required_docs),
        ("PROJECT_STATUS.md cross-reference", check_project_status_cross_reference),
        ("superseded docs name a replacement", check_superseded_docs_name_a_replacement),
        ("no machine-specific paths in active docs", check_no_local_paths_in_active_docs),
        ("no false GitHub Actions green claims", check_no_ci_green_claims),
        ("cloud-validation --tier values match CLI", check_cloud_validation_tiers_match_cli),
    ]

    all_errors: list[str] = []
    for name, fn in checks:
        errors = fn()
        status = "OK" if not errors else "FAIL"
        print(f"[{status}] {name}")
        for e in errors:
            print(f"    - {e}")
        all_errors.extend(errors)

    if all_errors:
        print(f"\nFAIL: {len(all_errors)} repository-clarity problem(s) found.")
        return 1
    print("\nOK: repository clarity checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
