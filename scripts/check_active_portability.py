#!/usr/bin/env python
"""
check_active_portability.py
===========================
Fail if active source code, scripts, tests, or navigation documentation embed
machine-specific paths from one contributor's workspace.

Historical generated reports are intentionally out of scope: some immutable
provenance artifacts record the machine path where they were produced, and
rewriting those would falsify history. Active code and docs should instead use
repository-root discovery, command-line arguments, or environment variables.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PROHIBITED_PATTERNS = (
    "/home/soroush",
    "/tmp/claude-1000",
    "/workspace/.venv",
    "/home/soroush/modal-venv",
)

ACTIVE_DIRS = (
    "src",
    "scripts",
    "tests",
    ".github/workflows",
)

ACTIVE_FILES = (
    ".gitignore",
    "AGENTS.md",
    "Makefile",
    "PROJECT_STATUS.md",
    "README.md",
    "pyproject.toml",
    "requirements.txt",
    "docs/ARCHITECTURE.md",
    "docs/ARTIFACT_POLICY.md",
    "docs/COST_ACCURACY_DECISION_ANALYSIS.md",
    "docs/EXPERIMENTS.md",
    "docs/EXPERIMENT_ARTIFACT_POLICY.md",
    "docs/REPOSITORY_LAYOUT.md",
    "docs/REPRODUCTION_CANONICAL.md",
)

TEXT_SUFFIXES = {
    "",
    ".cfg",
    ".csv",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

EXCLUDED_FILES = {
    "scripts/check_active_portability.py",
    "tests/test_active_portability.py",
}


def _candidate_paths() -> list[Path]:
    paths: set[Path] = set()
    for rel in ACTIVE_DIRS:
        base = REPO_ROOT / rel
        if base.exists():
            paths.update(p for p in base.rglob("*") if p.is_file())
    for rel in ACTIVE_FILES:
        path = REPO_ROOT / rel
        if path.exists():
            paths.add(path)
    return sorted(
        path for path in paths if path.relative_to(REPO_ROOT).as_posix() not in EXCLUDED_FILES
    )


def _is_text_path(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def scan_active_files(paths: list[Path] | None = None) -> list[tuple[Path, int, str]]:
    """Return ``(path, line_no, pattern)`` findings for active files."""
    findings: list[tuple[Path, int, str]] = []
    for path in paths or _candidate_paths():
        if not _is_text_path(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            for pattern in PROHIBITED_PATTERNS:
                if pattern in line:
                    findings.append((path, line_no, pattern))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)

    findings = scan_active_files()
    if findings:
        print("FAIL: machine-specific active path(s) found:", file=sys.stderr)
        for path, line_no, pattern in findings:
            rel = path.relative_to(REPO_ROOT)
            print(f"  {rel}:{line_no}: {pattern}", file=sys.stderr)
        print(
            "Use repo-root discovery, an explicit CLI argument, or an environment variable. "
            "Historical report trees can retain original execution paths but should not be "
            "used as portable examples.",
            file=sys.stderr,
        )
        return 1
    print("OK: no machine-specific active paths found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
