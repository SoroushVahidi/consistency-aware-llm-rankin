#!/usr/bin/env bash
# JDIQ overnight high-value workflow (~9h budget hard stop).
# No paid APIs. No force-push. No experimental-value fabrication.
# Soft time budget: prefer finishing high-priority phases early.

set -uo pipefail

REPO="/home/soroush/consistency-aware-llm-rankin"
EXPECTED_HEAD="db6edb61b601ca9c5035fd17fcf53c4dd14d0acc"
OUT_DIR="$REPO/reports/jdiq-overnight-20260713-225928"
MS="$REPO/papers/JDIQ_2026/manuscript"
PY="$REPO/.venv/bin/python"
DEADLINE_EPOCH=$(( $(date +%s) + 9*3600 - 900 ))  # 9h minus 15min reserve

status() { echo; echo "==== [$(date -Is)] $* ===="; }
have_time() { [[ $(date +%s) -lt $DEADLINE_EPOCH ]]; }
phase_done() { touch "$OUT_DIR/logs/phase_$1.done"; }
phase_ran() { [[ -f "$OUT_DIR/logs/phase_$1.done" ]]; }

cd "$REPO"
status "START overnight workflow"
git rev-parse HEAD
git status -sb | head -40 | tee "$OUT_DIR/logs/start_git_status.txt"

# Stay on verified commit for analysis identity; allow local manuscript edits later.
if [[ "$(git rev-parse HEAD)" != "$EXPECTED_HEAD" ]]; then
  echo "WARN: HEAD is not the expected verified commit $EXPECTED_HEAD" | tee "$OUT_DIR/logs/head_mismatch.warn"
fi

# ---------------------------------------------------------------------------
# Phase 1 — Fix false "retention sensitivity untested" claim using existing evidence
# ---------------------------------------------------------------------------
if ! phase_ran 01_retention && have_time; then
  status "Phase 1: integrate retention-sensitivity findings"
  if "$PY" "$OUT_DIR/scripts/phase01_retention_integrate.py" | tee "$OUT_DIR/logs/phase01.log"; then phase_done 01_retention; else echo PHASE01_FAILED; fi
fi

# ---------------------------------------------------------------------------
# Phase 2 — CombMNZ exploratory from stored scores (no manuscript add unless decisive)
# ---------------------------------------------------------------------------
if ! phase_ran 02_combmnz && have_time; then
  status "Phase 2: CombMNZ exploratory"
  if "$PY" "$OUT_DIR/scripts/phase02_combmnz_explore.py" | tee "$OUT_DIR/logs/phase02.log"; then phase_done 02_combmnz; else echo PHASE02_FAILED; fi
fi

# ---------------------------------------------------------------------------
# Phase 3 — Scrubbed anonymous artifact package prep + identity audit
# ---------------------------------------------------------------------------
if ! phase_ran 03_artifact && have_time; then
  status "Phase 3: anonymous artifact package preparation"
  if bash "$OUT_DIR/scripts/phase03_prepare_anonymous_artifact.sh" | tee "$OUT_DIR/logs/phase03.log"; then phase_done 03_artifact; else echo PHASE03_FAILED; fi
fi

# ---------------------------------------------------------------------------
# Phase 4 — Presentation / HotpotQA emphasis / consistency polish
# ---------------------------------------------------------------------------
if ! phase_ran 04_polish && have_time; then
  status "Phase 4: presentation and consistency polish"
  if "$PY" "$OUT_DIR/scripts/phase04_polish_manuscript.py" | tee "$OUT_DIR/logs/phase04.log"; then phase_done 04_polish; else echo PHASE04_FAILED; fi
fi

# ---------------------------------------------------------------------------
# Phase 5 — Full validation compile
# ---------------------------------------------------------------------------
if ! phase_ran 05_validate && have_time; then
  status "Phase 5: validate / compile"
  if (
    cd "$MS"
    tectonic -X compile main.tex --keep-logs
    pdfinfo main.pdf | tee "$OUT_DIR/logs/pdfinfo.txt"
    pdftotext main.pdf "$OUT_DIR/logs/main_pdftotext.txt"
    "$PY" "$OUT_DIR/scripts/phase05_validate.py"
  ) | tee "$OUT_DIR/logs/phase05.log"; then phase_done 05_validate; else echo PHASE05_FAILED; fi
fi

# ---------------------------------------------------------------------------
# Phase 6 — Overnight report + optional commit/push of manuscript-only deltas
# ---------------------------------------------------------------------------
if ! phase_ran 06_report && have_time; then
  status "Phase 6: write overnight report and maybe commit"
  if "$PY" "$OUT_DIR/scripts/phase06_finalize.py" | tee "$OUT_DIR/logs/phase06.log"; then phase_done 06_report; else echo PHASE06_FAILED; fi
fi

status "FINISHED overnight workflow"
echo "OUT_DIR=$OUT_DIR"
ls -la "$OUT_DIR" | head -40
