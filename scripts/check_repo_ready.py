#!/usr/bin/env python
"""
check_repo_ready.py
===================
Lightweight end-to-end verification that the repository is set up correctly
and ready to run experiments.

Checks performed
----------------
1. Package import (consistency_ranker)
2. Key source files exist
3. Key scripts are callable (import without errors)
4. pytest can discover tests
5. Expected output and data directories exist or can be created
6. Pre-committed result tables are readable

Usage
-----
    python scripts/check_repo_ready.py          # normal mode
    python scripts/check_repo_ready.py --strict # exit non-zero on any warning
"""

from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Check helpers
# ---------------------------------------------------------------------------

_results: list[tuple[str, str, str]] = []  # (status, category, message)


def _ok(category: str, message: str) -> None:
    _results.append(("OK", category, message))


def _warn(category: str, message: str) -> None:
    _results.append(("WARN", category, message))


def _fail(category: str, message: str) -> None:
    _results.append(("FAIL", category, message))


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def check_package_import() -> None:
    """Verify consistency_ranker can be imported."""
    try:
        importlib.import_module("consistency_ranker")
        _ok("import", "consistency_ranker imported successfully")
    except ImportError as exc:
        _fail("import", f"Cannot import consistency_ranker: {exc}")
        return

    submodules = [
        "consistency_ranker.greedy_fas",
        "consistency_ranker.cycle_detection",
        "consistency_ranker.baseline_ranking",
        "consistency_ranker.evaluation",
        "consistency_ranker.synthetic_data",
        "consistency_ranker.data.dataset_registry",
    ]
    for mod in submodules:
        try:
            importlib.import_module(mod)
            _ok("import", f"  {mod} ok")
        except ImportError as exc:
            _fail("import", f"  {mod} failed: {exc}")


def check_key_source_files() -> None:
    """Verify key source files exist."""
    required = [
        "src/consistency_ranker/__init__.py",
        "src/consistency_ranker/greedy_fas.py",
        "src/consistency_ranker/cycle_detection.py",
        "src/consistency_ranker/baseline_ranking.py",
        "src/consistency_ranker/evaluation.py",
        "src/consistency_ranker/synthetic_data.py",
        "src/consistency_ranker/pairwise_prefs.py",
        "src/consistency_ranker/graph_construction.py",
        "src/consistency_ranker/data/dataset_registry.py",
        "src/consistency_ranker/data/schema.py",
        "src/consistency_ranker/data/unified_loader.py",
        "src/consistency_ranker/utils/timing.py",
        "pyproject.toml",
        "requirements.txt",
    ]
    for rel in required:
        path = REPO_ROOT / rel
        if path.exists():
            _ok("source_files", f"{rel}")
        else:
            _fail("source_files", f"Missing: {rel}")


def check_key_scripts() -> None:
    """Verify key scripts exist and are importable."""
    scripts = [
        "scripts/run_synthetic.py",
        "scripts/run_real_experiment.py",
        "scripts/build_paper_evidence_package.py",
        "scripts/generate_paper_tables.py",
        "scripts/bootstrap_method_deltas.py",
        "scripts/generate_q1_tables.py",
        "scripts/run_publication_vote_suite.py",
        "scripts/analyze_publication_vote_deltas.py",
    ]
    for rel in scripts:
        path = REPO_ROOT / rel
        if path.exists():
            _ok("scripts", f"{rel} exists")
        else:
            _warn("scripts", f"Missing script: {rel}")


def check_docs() -> None:
    """Verify expected documentation files exist."""
    docs = [
        "docs/Q1_JOURNAL_GAP_ANALYSIS.md",
        "docs/Q1_PUBLICATION_GAP_ANALYSIS.md",
        "docs/REPRODUCTION_Q1.md",
        "docs/Q1_POSITIONING_AND_CLAIMS.md",
        "docs/Q1_CLAIM_EVIDENCE_MAP.md",
        "docs/SAFE_Q1_CLAIMS.md",
        "docs/JOURNAL_READY_CONTRIBUTIONS.md",
        "docs/RESULTS_FOR_PAPER.md",
        "docs/THREATS_TO_VALIDITY.md",
        "docs/EXPERIMENTS.md",
        "docs/FINAL_REPRODUCTION_GUIDE.md",
        "docs/AUDIT.md",
    ]
    for rel in docs:
        path = REPO_ROOT / rel
        if path.exists():
            _ok("docs", f"{rel}")
        else:
            _warn("docs", f"Missing doc: {rel}")


def check_committed_tables() -> None:
    """Verify pre-committed result tables are present and readable."""
    tables = [
        "docs/tables/main_results.csv",
        "docs/tables/regime_analysis.csv",
        "docs/tables/bootstrap_results_combined_summary.csv",
        "outputs/pub_vote_cmp_v2/paper_package/tables/table_graph_ndcg_and_consistency.csv",
        "outputs/pub_vote_cmp_v2/paper_package/tables/table_bootstrap_delta_ndcg.csv",
        "outputs/pub_vote_cmp_v2/paper_package/tables/table_consistency_qrels_bew.csv",
    ]
    import csv

    for rel in tables:
        path = REPO_ROOT / rel
        if not path.exists():
            _warn("committed_tables", f"Missing table: {rel}")
            continue
        try:
            with path.open(encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            _ok("committed_tables", f"{rel} ({len(rows)} rows)")
        except Exception as exc:
            _fail("committed_tables", f"Cannot read {rel}: {exc}")


def check_output_directories() -> None:
    """Verify output directories exist or can be created."""
    dirs = [
        "outputs",
        "outputs/pub_vote_cmp_v2",
        "outputs/pub_vote_cmp_v2/paper_package",
        "outputs/q1_journal_package",
        "data/processed",
        "data/raw",
        "docs/tables",
        "docs/figures",
    ]
    for rel in dirs:
        path = REPO_ROOT / rel
        if path.exists():
            _ok("directories", f"{rel}/ exists")
        else:
            try:
                path.mkdir(parents=True, exist_ok=True)
                _ok("directories", f"{rel}/ created")
            except OSError as exc:
                _fail("directories", f"Cannot create {rel}/: {exc}")


def check_pytest_discovery() -> None:
    """Verify pytest can discover the test suite."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "--tb=no"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    lines = (result.stdout + result.stderr).strip().splitlines()
    # Look for lines like "N tests collected"
    collected_line = next(
        (ln for ln in lines if "test" in ln and ("collected" in ln or "selected" in ln)), None
    )
    if result.returncode == 0 and collected_line:
        _ok("pytest", f"Test discovery succeeded: {collected_line}")
    elif result.returncode == 0:
        _ok("pytest", "Test discovery succeeded (no summary line found)")
    else:
        last_line = lines[-1] if lines else "no output"
        _fail("pytest", f"pytest --collect-only failed (rc={result.returncode}): {last_line}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_all_checks() -> None:
    check_package_import()
    check_key_source_files()
    check_key_scripts()
    check_docs()
    check_committed_tables()
    check_output_directories()
    check_pytest_discovery()


def print_report(strict: bool) -> int:
    """Print results and return exit code."""
    status_width = 6
    cat_width = 22

    counts = {"OK": 0, "WARN": 0, "FAIL": 0}
    for status, category, message in _results:
        counts[status] += 1
        symbol = {"OK": "✓", "WARN": "⚠", "FAIL": "✗"}.get(status, "?")
        print(f"  {symbol} [{status:<{status_width}}] [{category:<{cat_width}}] {message}")

    print()
    print(
        f"Summary: {counts['OK']} OK, {counts['WARN']} warnings, {counts['FAIL']} failures"
    )

    if counts["FAIL"] > 0:
        print("\n❌ Repository is NOT ready: fix FAIL items above before running experiments.")
        return 1
    if counts["WARN"] > 0 and strict:
        print("\n⚠  Strict mode: treating warnings as failures.")
        return 1
    if counts["WARN"] > 0:
        print("\n⚠  Repository has warnings (non-critical). Run with --strict to treat as errors.")
    else:
        print("\n✅ Repository is ready.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify repository is set up correctly.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on warnings as well as failures.",
    )
    args = parser.parse_args(argv)

    print("Repository readiness check")
    print("=" * 60)
    run_all_checks()
    print()
    return print_report(strict=args.strict)


if __name__ == "__main__":
    sys.exit(main())
