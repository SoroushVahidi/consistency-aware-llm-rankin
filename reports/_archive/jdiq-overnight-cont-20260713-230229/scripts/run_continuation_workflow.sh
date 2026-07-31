#!/usr/bin/env bash
# JDIQ overnight continuation (~remaining ~8h soft budget).
set -uo pipefail

REPO="/home/soroush/consistency-aware-llm-rankin"
OUT_DIR="$REPO/reports/jdiq-overnight-cont-20260713-230229"
MS="$REPO/papers/JDIQ_2026/manuscript"
PY="$REPO/.venv/bin/python"
DEADLINE_EPOCH=$(cat /tmp/jdiq_cont_deadline_epoch.txt 2>/dev/null || echo $(( $(date +%s) + 8*3600 - 900 )))

status() { echo; echo "==== [$(date -Is)] $* ===="; }
have_time() { [[ $(date +%s) -lt $DEADLINE_EPOCH ]]; }
phase_done() { touch "$OUT_DIR/logs/phase_$1.done"; }
phase_ran() { [[ -f "$OUT_DIR/logs/phase_$1.done" ]]; }

cd "$REPO"
status "START overnight continuation"
git rev-parse HEAD
git status -sb | head -50 | tee "$OUT_DIR/logs/start_git_status.txt"

run_phase() {
  local id="$1"; shift
  local title="$1"; shift
  if phase_ran "$id"; then
    echo "Skip $id (already done)"
    return 0
  fi
  if ! have_time; then
    echo "TIME_BUDGET_EXIT before $id"
    return 1
  fi
  status "$title"
  if "$@"; then
    phase_done "$id"
    return 0
  fi
  echo "PHASE_FAILED: $id"
  return 0  # soft-fail
}

run_phase 01_methods "Phase 1: Methods retention consistency" \
  bash -lc "$PY \"$OUT_DIR/scripts/phase01_fix_retention_methods.py\" | tee \"$OUT_DIR/logs/phase01.log\""

run_phase 02_path "Phase 2: remove hardcoded home-path leak" \
  bash -lc "$PY \"$OUT_DIR/scripts/phase02_fix_path_leak.py\" | tee \"$OUT_DIR/logs/phase02.log\""

run_phase 03_combmnz "Phase 3: CombMNZ exploratory (correct qrels)" \
  bash -lc "$PY \"$OUT_DIR/scripts/phase03_combmnz_explore.py\" | tee \"$OUT_DIR/logs/phase03.log\""

# Compile once before packaging so artifact PDF is current after early edits
run_phase 03b_precompile "Phase 3b: precompile after content edits" \
  bash -lc "cd \"$MS\" && tectonic -X compile main.tex --keep-logs | tee \"$OUT_DIR/logs/phase03b_precompile.log\""

run_phase 05_polish "Phase 5: presentation polish" \
  bash -lc "$PY \"$OUT_DIR/scripts/phase05_polish.py\" | tee \"$OUT_DIR/logs/phase05.log\""

# Order: polish -> validate compile -> artifact uses final PDF
run_phase 06_validate "Phase 6: validate / compile" \
  bash -lc "$PY \"$OUT_DIR/scripts/phase06_validate.py\" | tee \"$OUT_DIR/logs/phase06.log\""

run_phase 04_artifact "Phase 4: rebuild anonymous artifact" \
  bash -lc "bash \"$OUT_DIR/scripts/phase04_prepare_anonymous_artifact.sh\" | tee \"$OUT_DIR/logs/phase04.log\""

# Re-validate leak status after artifact
run_phase 06b_reval "Phase 6b: re-check artifact leaks in validation JSON" \
  bash -lc "$PY - <<'PY'
import json
from pathlib import Path
OUT=Path('$OUT_DIR')
vp=OUT/'tables'/'phase06_validation.json'
val=json.loads(vp.read_text()) if vp.exists() else {}
leak=(OUT/'artifact_prep'/'LEAK_FAIL').exists()
fails=list(val.get('fail') or [])
fails=[f for f in fails if f!='artifact_identity_leak']
if leak:
    fails.append('artifact_identity_leak')
val['fail']=fails
val['leak_fail']=leak
vp.write_text(json.dumps(val, indent=2)+'\n')
print(val)
if fails:
    raise SystemExit('REVAL_FAILED')
PY
" | tee "$OUT_DIR/logs/phase06b.log"

run_phase 07_report "Phase 7: report + commit/push if clean" \
  bash -lc "$PY \"$OUT_DIR/scripts/phase07_finalize.py\" | tee \"$OUT_DIR/logs/phase07.log\""

# If time remains, optional deeper consistency scans (non-mutating inventory)
if have_time; then
  status "Optional: residual consistency inventory"
  "$PY" - <<'PY' | tee "$OUT_DIR/logs/optional_inventory.log"
from pathlib import Path
import re
repo=Path('/home/soroush/consistency-aware-llm-rankin')
tex=(repo/'papers/JDIQ_2026/manuscript/main.tex').read_text()
checks={
 'minmax_hyphen_plain': len(re.findall(r'min-max', tex)),
 'minmax_endash': len(re.findall(r'min--max', tex)),
 'tfidf_plain': len(re.findall(r'TF-IDF', tex)),
 'tfidf_endash': len(re.findall(r'TF--IDF', tex)),
 'original_study': 'original study' in tex.lower(),
 'not_yet_performed': 'not yet performed' in tex.lower(),
 'github_author': 'SoroushVahidi' in tex,
 'home_path': '/home/soroush' in tex,
}
print(checks)
Path('/home/soroush/consistency-aware-llm-rankin/reports/jdiq-overnight-cont-20260713-230229/tables/optional_inventory.json').write_text(
    __import__('json').dumps(checks, indent=2)+'\n')
PY
fi

status "FINISHED overnight continuation"
echo "OUT_DIR=$OUT_DIR"
ls -la "$OUT_DIR" | head -40
echo "EXIT_CODE=0"
