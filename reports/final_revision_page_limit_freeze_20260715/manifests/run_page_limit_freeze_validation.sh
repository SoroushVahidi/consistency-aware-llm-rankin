#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "=== 1. Full pytest suite ==="
./.venv/bin/python -m pytest -q

echo
echo "=== 2. Relevant skipped-test audit ==="
./.venv/bin/python -m pytest -q -rs

echo
echo "=== 3. Repo readiness ==="
./.venv/bin/python scripts/check_repo_ready.py

echo
echo "=== 4. Lint touched code ==="
./.venv/bin/ruff check \
  scripts/run_real_experiment.py \
  src/consistency_ranker/failure_mining/graph_features.py \
  src/consistency_ranker/failure_mining/query_processor.py \
  src/consistency_ranker/qrels_reference.py \
  src/consistency_ranker/statistical_inference.py \
  tests/test_conditional_subsets.py \
  tests/test_pool_cutoff_evaluation.py \
  tests/test_qrels_reference.py \
  tests/test_real_experiment_modes.py \
  tests/test_statistical_inference.py \
  tests/test_task3_ranker_dependence.py \
  tests/test_task4_exact_baseline_fairness.py \
  reports/full_calibrated_core/scripts/conditional_subsets.py \
  reports/full_calibrated_core/scripts/full_calibration_utils.py \
  reports/full_calibrated_core/scripts/run_full_calibrated_core.py \
  papers/JDIQ_2026/submission/scripts/build_final_anonymous.py \
  reports/final_revision_page_limit_freeze_20260715/scripts/page_limit_freeze_audit.py

echo
echo "=== 5. py_compile on touched/task-critical Python ==="
./.venv/bin/python -m py_compile \
  scripts/run_real_experiment.py \
  src/consistency_ranker/failure_mining/graph_features.py \
  src/consistency_ranker/failure_mining/query_processor.py \
  src/consistency_ranker/qrels_reference.py \
  src/consistency_ranker/statistical_inference.py \
  reports/full_calibrated_core/scripts/conditional_subsets.py \
  reports/full_calibrated_core/scripts/full_calibration_utils.py \
  reports/full_calibrated_core/scripts/run_full_calibrated_core.py \
  papers/JDIQ_2026/submission/scripts/build_final_anonymous.py \
  reports/final_revision_page_limit_freeze_20260715/scripts/page_limit_freeze_audit.py

echo
echo "=== 6. Main manuscript build ==="
cd papers/JDIQ_2026/manuscript
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
pdfinfo main.pdf | grep '^Pages:'

echo
echo "=== 7. Supplement build ==="
latexmk -pdf -interaction=nonstopmode -halt-on-error supplement.tex
pdfinfo supplement.pdf | grep '^Pages:'
cd "$REPO_ROOT"

echo
echo "=== 8. Rebuild freeze manifest and anonymous artifact ==="
./.venv/bin/python papers/JDIQ_2026/submission/scripts/build_freeze_manifest.py
./.venv/bin/python papers/JDIQ_2026/submission/scripts/build_final_anonymous.py

echo
echo "=== 9. Citation/reference log scan ==="
if [[ -f papers/JDIQ_2026/manuscript/main.log || -f papers/JDIQ_2026/manuscript/supplement.log ]]; then
  ! rg -n "undefined references|undefined citation|Citation .* undefined|Reference .* undefined" \
    papers/JDIQ_2026/manuscript/main.log \
    papers/JDIQ_2026/manuscript/supplement.log
else
  echo "log files not retained; relying on rendered-PDF broken-reference scan and audit script"
fi

echo
echo "=== 10. Broken-reference glyph scan ==="
pdftotext papers/JDIQ_2026/manuscript/main.pdf - 2>/dev/null | grep -n "⁇\\|??" && echo "BROKEN REF FOUND" || echo "clean (no matches)"
pdftotext papers/JDIQ_2026/manuscript/supplement.pdf - 2>/dev/null | grep -n "⁇\\|??" && echo "BROKEN REF FOUND" || echo "clean (no matches)"

echo
echo "=== 11. Page-freeze claim/equation/reference audit ==="
./.venv/bin/python reports/final_revision_page_limit_freeze_20260715/scripts/page_limit_freeze_audit.py

echo
echo "=== 12. Artifact identity, secret, absolute-path, and ZIP integrity scans ==="
grep -rniE "vahidi|sv96@njit\\.edu|koutis|/home/soroush|njit\\.edu" papers/JDIQ_2026/submission/final_anonymous/ 2>/dev/null && echo "LEAK FOUND" || echo "clean (no matches)"
grep -rniE "api[_-]?key\\s*[:=]|secret[_-]?key\\s*[:=]|password\\s*[:=]|BEGIN (RSA|OPENSSH|PGP)|AKIA[0-9A-Z]{16}|sk-[a-zA-Z0-9]{20,}" papers/JDIQ_2026/submission/final_anonymous/ 2>/dev/null && echo "SECRET FOUND" || echo "clean (no matches)"
unzip -t papers/JDIQ_2026/submission/final_anonymous.zip | tail -3

echo
echo "=== 13. ZIP extraction test ==="
rm -rf /tmp/jdiq_page_limit_zip_extract
unzip -q papers/JDIQ_2026/submission/final_anonymous.zip -d /tmp/jdiq_page_limit_zip_extract
diff -rq papers/JDIQ_2026/submission/final_anonymous /tmp/jdiq_page_limit_zip_extract/final_anonymous

echo
echo "=== Page-limit freeze validation complete ==="
