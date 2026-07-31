#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/home/soroush/consistency-aware-llm-rankin"
PYTHON_BIN="$REPO_ROOT/.venv/bin/python"

timestamp() {
  date +"%Y-%m-%dT%H:%M:%S%z"
}

echo "[$(timestamp)] full pytest"
cd "$REPO_ROOT"
"$PYTHON_BIN" -m pytest -q

echo "[$(timestamp)] repo readiness"
"$PYTHON_BIN" scripts/check_repo_ready.py

echo "[$(timestamp)] ruff on touched code"
"$PYTHON_BIN" -m ruff check \
  reports/final_revision_task1_pool_cutoff_20260715/scripts \
  tests/test_pool_cutoff_evaluation.py
"$PYTHON_BIN" -m ruff check --select F,E9 \
  reports/full_calibrated_core/scripts/full_calibration_utils.py \
  reports/full_calibrated_core/scripts/run_full_calibrated_core.py
"$PYTHON_BIN" -m py_compile \
  reports/full_calibrated_core/scripts/full_calibration_utils.py \
  reports/full_calibrated_core/scripts/run_full_calibrated_core.py \
  reports/final_revision_task1_pool_cutoff_20260715/scripts/*.py \
  tests/test_pool_cutoff_evaluation.py

echo "[$(timestamp)] task1 output verification"
"$PYTHON_BIN" reports/final_revision_task1_pool_cutoff_20260715/scripts/verify_pool_cutoff_outputs.py

echo "[$(timestamp)] manuscript build"
cd "$REPO_ROOT/papers/JDIQ_2026/manuscript"
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

echo "[$(timestamp)] manuscript checksum"
sha256sum main.pdf
