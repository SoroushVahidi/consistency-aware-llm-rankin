"""Regression coverage for the 2026-07-31 fresh-checkout reproducibility fix.

Context: a genuinely fresh clone of `main` (not a working directory with
locally-accumulated generated state) previously failed or errored on ~64
tests that silently depended on either (a) prepared BEIR/HotpotQA/BRIGHT
dataset files under `data/processed/` (multi-GB, network-fetched, gitignored
by design), or (b) a `reports/final_revision_task3_ranker_dependence_20260715/`
subdirectory that was accidentally caught by a blanket `reports/final_revision_*/`
.gitignore rule despite being small, source-code-like, and required for
`tests/test_task3_ranker_dependence.py` to even collect.

This module does not re-run those ~64 tests (that would defeat the fix's own
purpose on a machine without prepared datasets); it statically verifies the
guard-rails that keep the default `pytest`/`make test`/`make test-full`/CI run
green on a fresh clone stay in place.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_real_data_marker_is_registered_and_deselected_by_default():
    """pyproject.toml must register the `real_data` marker and deselect it by
    default, or a fresh checkout without prepared datasets will fail again."""
    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    opts = config["tool"]["pytest"]["ini_options"]
    assert "not real_data" in opts["addopts"], (
        "default pytest addopts must deselect the real_data marker so a fresh "
        "checkout without prepared datasets stays green"
    )
    assert any("real_data" in m for m in opts.get("markers", [])), (
        "the real_data marker must be registered (avoids PytestUnknownMarkWarning "
        "and documents the marker's meaning)"
    )


def test_default_collection_deselects_a_nonzero_real_data_set():
    """Sanity check that the marker is actually applied to real tests, not
    just declared: a default (no -m override) collection-only run must report
    a nonzero deselected count. If this drops to zero, either the marker was
    removed from all tests (regression) or something broke deselection."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "deselected" in result.stdout, (
        "expected a nonzero 'N deselected' line in default collection output "
        f"(real_data tests should be excluded by default); got:\n{result.stdout[-2000:]}"
    )


def test_task3_scripts_are_tracked_not_gitignored():
    """tests/test_task3_ranker_dependence.py imports these modules
    unconditionally at module scope; if this directory is ever swept back
    under a blanket reports/final_revision_*/ gitignore rule, a fresh clone
    will silently skip (or, before the 2026-07-31 fix, error-abort collection
    on) this module again. Guard the exact files the module needs."""
    task3_scripts = (
        REPO_ROOT
        / "reports"
        / "final_revision_task3_ranker_dependence_20260715"
        / "scripts"
    )
    required = [
        "run_coverage_and_dependence.py",
        "run_leave_one_out.py",
        "run_pre_post_normalization.py",
        "task3_common.py",
    ]
    for name in required:
        path = task3_scripts / name
        assert path.exists(), f"{path} must exist and be tracked in Git (see .gitignore)"

    result = subprocess.run(
        ["git", "check-ignore", "-q", str(task3_scripts / "task3_common.py")],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    assert result.returncode != 0, (
        "reports/final_revision_task3_ranker_dependence_20260715/scripts/ must NOT "
        "be gitignored -- it is small, source-code-like, and required for "
        "tests/test_task3_ranker_dependence.py to collect on a fresh clone"
    )
