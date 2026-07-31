#!/usr/bin/env bash
# Overnight repair-selector active mining launcher (detached tmux session).
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MAIN_REPO="${MAIN_REPO:-$(cd -- "${SCRIPT_DIR}/.." && pwd)}"
CAAR_REPO="${CAAR_REPO:-$(cd -- "${MAIN_REPO}/.." && pwd)/$(basename "${MAIN_REPO}")-caar}"
SESSION_NAME="repair_selector_overnight"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
OUTPUT_DIR="${CAAR_REPO}/reports/repair_selector_overnight_${TIMESTAMP}"
WALL_LIMIT="30600"  # 8h30m in seconds

_LAUNCH_ENV="cd ${MAIN_REPO} && source ${VENV_PATH:-${MAIN_REPO}/.venv}/bin/activate"

mkdir -p "${OUTPUT_DIR}"

LAUNCH_CMD="${_LAUNCH_ENV} && timeout --signal=TERM --kill-after=10m ${WALL_LIMIT} python scripts/run_repair_selector_overnight.py \
  --datasets scidocs fiqa hotpotqa bright \
  --max-queries-per-dataset 80 \
  --max-candidates 15 \
  --providers cohere,gemini,azure,cloudrift,fireworks \
  --max-llm-calls 2500 \
  --use-cache \
  --seed 42 \
  --wall-seconds 30600 \
  --batch-size 8 \
  --selector-train-every 25 \
  --output-dir ${OUTPUT_DIR} \
  2>&1 | tee -a ${OUTPUT_DIR}/run.log"

# Kill existing session if present
tmux kill-session -t "${SESSION_NAME}" 2>/dev/null || true

tmux new-session -d -s "${SESSION_NAME}" "bash -lc $(printf '%q' "${LAUNCH_CMD}")"

sleep 1
PID="$(tmux list-panes -t "${SESSION_NAME}" -F '#{pane_pid}' 2>/dev/null | head -1 || true)"

echo "=== Repair selector overnight job launched ==="
echo "tmux session: ${SESSION_NAME}"
echo "attach: tmux attach -t ${SESSION_NAME}"
echo "monitor log: tail -f ${OUTPUT_DIR}/run.log"
echo "output dir: ${OUTPUT_DIR}"
echo "pane pid: ${PID:-unknown}"
echo "launch command: ${LAUNCH_CMD}"
