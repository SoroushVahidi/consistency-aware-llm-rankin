#!/usr/bin/env python3
"""Shared setup for JDIQ final-revision Task 3 (ranker-dependence audit).

Imports the canonical calibration/vote/graph pipeline from
reports/full_calibrated_core/scripts/full_calibration_utils.py and
reports/full_calibrated_core/scripts/run_full_calibrated_core.py so every
Task 3 analysis script reuses the exact same candidate-pool selection,
normalization, vote-construction, and graph-construction code that produced
the manuscript's headline numbers, instead of re-deriving it.
"""

from __future__ import annotations

import json
import subprocess
import sys
from itertools import combinations
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
REPORT_ROOT = THIS_DIR.parent
REPO_ROOT = REPORT_ROOT.parents[1]
SRC_ROOT = REPO_ROOT / "src"
FULL_CAL_SCRIPTS = REPO_ROOT / "reports" / "full_calibrated_core" / "scripts"
TASK1_SCRIPTS = REPO_ROOT / "reports" / "final_revision_task1_pool_cutoff_20260715" / "scripts"

for path in (REPO_ROOT, SRC_ROOT, FULL_CAL_SCRIPTS, TASK1_SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import full_calibration_utils as fcu  # noqa: E402
import run_full_calibrated_core as rfc  # noqa: E402

MANUSCRIPT_TEX = REPO_ROOT / "papers" / "JDIQ_2026" / "manuscript" / "main.tex"
MANUSCRIPT_PDF = REPO_ROOT / "papers" / "JDIQ_2026" / "manuscript" / "main.pdf"

TABLES_DIR = REPORT_ROOT / "tables"
MANIFESTS_DIR = REPORT_ROOT / "manifests"
LOGS_DIR = REPORT_ROOT / "logs"
OUTPUTS_DIR = REPORT_ROOT / "outputs"
VALIDATION_DIR = REPORT_ROOT / "validation"

DATASETS = ("scidocs", "fiqa", "hotpotqa", "bright")
RANKERS = fcu.RANKERS  # ("bm25", "tfidf", "minilm")
REGIMES = fcu.REGIMES  # ("ms2", "ms1", "ms1_drop_mutual")

# Canonical pool = the manuscript's default candidate-pool size per dataset
# (experiments/method_improvement_audit_20260711_205733 manifest spec.top_k).
CANONICAL_POOL = {"scidocs": 20, "fiqa": 20, "hotpotqa": 10, "bright": 20}
# Task 1's targeted larger-pool cells (reports/final_revision_task1_pool_cutoff_20260715).
LARGER_POOL = {"scidocs": 50, "fiqa": 50, "hotpotqa": 35, "bright": 50}
POOLS = {"canonical": CANONICAL_POOL, "task1_larger": LARGER_POOL}

PRIMARY_CALIBRATION = "minmax_query_ranker"
PRIMARY_THRESHOLD_MODE = "retention_matched"


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


def dataset_inputs_for_pool(dataset: str, pool_size: int) -> dict[str, Any]:
    """Usable-query-filtered per-query inputs (candidate pool, raw ranker
    score maps, qrels) for one dataset at one candidate-pool size, using the
    unmodified canonical RRF-union pool-selection policy."""
    return rfc._analysis_dataset_inputs(dataset, pool_size_override=pool_size)


def canonical_threshold_config(
    dataset_inputs: dict[str, Any], regime: str
) -> "fcu.ThresholdConfig":
    """The exact ThresholdConfig the manuscript's primary protocol
    (minmax_query_ranker + retention_matched) uses for one dataset/regime
    cell, derived the same way run_full_calibrated_core.py derives it."""
    raw_stats = fcu.raw_baseline_statistics(dataset_inputs)[regime]
    pair_margins, _zero_var = rfc._pair_margin_summary(dataset_inputs, PRIMARY_CALIBRATION)
    return fcu.choose_threshold_config(
        dataset=dataset_inputs["dataset"],
        regime=regime,
        calibration=PRIMARY_CALIBRATION,
        threshold_mode=PRIMARY_THRESHOLD_MODE,
        baseline_vote_rates=raw_stats["vote_rates"],
        baseline_edge_count=raw_stats["edge_count"],
        calibration_pair_margins=pair_margins,
        per_query_inputs=dataset_inputs["per_query_inputs"],
    )


def unordered_pairs(candidate_pool: list[str]):
    return combinations(candidate_pool, 2)


def n_pairs(pool_size: int) -> int:
    return pool_size * (pool_size - 1) // 2
