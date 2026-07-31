#!/usr/bin/env python3
"""Shared setup for JDIQ final-revision Task 4 (exact repair + baseline
fairness audit). Mirrors task3_common.py's pattern: reuse the canonical
pipeline rather than re-deriving it."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
REPORT_ROOT = THIS_DIR.parent
REPO_ROOT = REPORT_ROOT.parents[1]
SRC_ROOT = REPO_ROOT / "src"
FULL_CAL_SCRIPTS = REPO_ROOT / "reports" / "full_calibrated_core" / "scripts"
TASK1_SCRIPTS = REPO_ROOT / "reports" / "final_revision_task1_pool_cutoff_20260715" / "scripts"
POOL_AUDIT_SCRIPTS = REPO_ROOT / "reports" / "candidate_pool_conditional_audit_20260714" / "scripts"

for path in (REPO_ROOT, SRC_ROOT, FULL_CAL_SCRIPTS, TASK1_SCRIPTS, POOL_AUDIT_SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import full_calibration_utils as fcu  # noqa: E402
import run_full_calibrated_core as rfc  # noqa: E402,F401  (re-exported as t4.rfc for other scripts)

from consistency_ranker import statistical_inference as stats_inf  # noqa: E402

MANUSCRIPT_TEX = REPO_ROOT / "papers" / "JDIQ_2026" / "manuscript" / "main.tex"
MANUSCRIPT_PDF = REPO_ROOT / "papers" / "JDIQ_2026" / "manuscript" / "main.pdf"

TABLES_DIR = REPORT_ROOT / "tables"
MANIFESTS_DIR = REPORT_ROOT / "manifests"
LOGS_DIR = REPORT_ROOT / "logs"
OUTPUTS_DIR = REPORT_ROOT / "outputs"
VALIDATION_DIR = REPORT_ROOT / "validation"

DATASETS = ("scidocs", "fiqa", "hotpotqa", "bright")
RANKERS = fcu.RANKERS
REGIMES = fcu.REGIMES

CANONICAL_POOL = {"scidocs": 20, "fiqa": 20, "hotpotqa": 10, "bright": 20}
LARGER_POOL = {"scidocs": 50, "fiqa": 50, "hotpotqa": 35, "bright": 50}

# Existing per-pool baseline outputs from reports/candidate_pool_conditional_audit_20260714/
POOL_RUNS_ROOT = FULL_CAL_SCRIPTS.parent / "outputs" / "calibrated_all4" / "pool_runs"
POOL_IDS = (
    "rrf_union_topk",
    "neutral_round_robin_union",
    "equal_depth_union",
    "combsum_union_topk",
    "bm25_only",
)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fcu.write_csv(path, rows)


def git_repo_state() -> dict[str, Any]:
    status = subprocess.check_output(["git", "-C", str(REPO_ROOT), "status", "--short"], text=True)
    branch = subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "branch", "--show-current"], text=True
    ).strip()
    commit = subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    return {
        "branch": branch,
        "commit": commit,
        "working_tree_clean": not status.strip(),
        "status_short": status.splitlines(),
        "manuscript_pdf_sha256": fcu.sha256_file(MANUSCRIPT_PDF),
    }


def rich_cell_statistics(deltas: list[float]) -> dict[str, Any]:
    """Task 2's statistical framework (BCa, exact/MC sign-flip, MDE) applied
    to one dataset/regime/pair/metric cell's paired deltas."""
    n = len(deltas)
    if n == 0:
        return {"n_paired_queries": 0}
    mean_delta = sum(deltas) / n
    sf = stats_inf.sign_flip_pvalue(deltas)
    bca = stats_inf.bootstrap_mean_interval(deltas, method="bca")
    helped = sum(1 for d in deltas if d > 1e-12)
    harmed = sum(1 for d in deltas if d < -1e-12)
    unchanged = n - helped - harmed
    sd = (sum((d - mean_delta) ** 2 for d in deltas) / n) ** 0.5
    mde80 = stats_inf.minimum_detectable_effect_normal(n=n, sd=sd, alpha=0.05, power=0.80)
    return {
        "n_paired_queries": n,
        "mean_delta": mean_delta,
        "median_delta": sorted(deltas)[n // 2]
        if n % 2
        else (sorted(deltas)[n // 2 - 1] + sorted(deltas)[n // 2]) / 2,
        "std_delta": sd,
        "helped_queries": helped,
        "harmed_queries": harmed,
        "unchanged_queries": unchanged,
        "sign_flip_pvalue": sf.pvalue,
        "sign_flip_method": sf.method,
        "bca_ci_low": bca.lower,
        "bca_ci_high": bca.upper,
        "bca_frac_gt_zero": bca.frac_gt_zero,
        "mde_normal_alpha05_power80": mde80,
    }
