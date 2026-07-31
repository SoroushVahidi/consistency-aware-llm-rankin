#!/usr/bin/env bash
set -euo pipefail

cd /home/soroush/consistency-aware-llm-rankin
./.venv/bin/python reports/final_revision_task1_pool_cutoff_20260715/scripts/run_pool_cutoff_exact.py
