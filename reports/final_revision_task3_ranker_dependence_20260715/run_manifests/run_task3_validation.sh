#!/usr/bin/env bash
set -euo pipefail
cd /home/soroush/consistency-aware-llm-rankin

echo "=== Task 3 task-specific tests ==="
./.venv/bin/python -m pytest tests/test_task3_ranker_dependence.py -q

echo "=== Full pytest ==="
./.venv/bin/python -m pytest -q

echo "=== Lint (new Task 3 files) ==="
./.venv/bin/ruff check reports/final_revision_task3_ranker_dependence_20260715/scripts/*.py tests/test_task3_ranker_dependence.py

echo "=== py_compile ==="
./.venv/bin/python -m py_compile reports/final_revision_task3_ranker_dependence_20260715/scripts/*.py tests/test_task3_ranker_dependence.py

echo "=== check_repo_ready ==="
./.venv/bin/python scripts/check_repo_ready.py

echo "=== Claim-to-evidence audit ==="
./.venv/bin/python reports/final_revision_task3_ranker_dependence_20260715/scripts/claim_to_evidence_audit.py

echo "=== LaTeX build ==="
cd papers/JDIQ_2026/manuscript && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

echo "=== ALL VALIDATION STEPS PASSED ==="
