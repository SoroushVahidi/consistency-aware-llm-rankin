#!/usr/bin/env bash
set -u

SESSION_NAME="method_improvement_audit"
REPO="/home/soroush/consistency-aware-llm-rankin"
WORKSPACE="/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733"
PYTHON_BIN="/home/soroush/modal-venv/bin/python"
ACTIVATE="/home/soroush/modal-venv/bin/activate"
RUNNER="$WORKSPACE/run_method_improvement_audit.py"
STDOUT_LOG="$WORKSPACE/tmux_stdout.log"
STDERR_LOG="$WORKSPACE/tmux_stderr.log"
EXIT_FILE="$WORKSPACE/tmux_exit_status.txt"

mkdir -p "$WORKSPACE"
: > "$STDOUT_LOG"
: > "$STDERR_LOG"

cat > "$WORKSPACE/RUN_MANIFEST.json" <<JSON
{
  "session_name": "$SESSION_NAME",
  "workspace": "$WORKSPACE",
  "repo": "$REPO",
  "launcher_created_at": "$(date '+%Y-%m-%d %H:%M:%S')",
  "stdout_log": "$STDOUT_LOG",
  "stderr_log": "$STDERR_LOG",
  "exit_file": "$EXIT_FILE",
  "status": "launching"
}
JSON

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  echo "Reusing existing tmux session: $SESSION_NAME"
  exit 0
fi

CMD=$(cat <<'EOF'
bash -lc '
  set +e
  cd "/home/soroush/consistency-aware-llm-rankin"
  if [ -f "/home/soroush/modal-venv/bin/activate" ]; then
    source "/home/soroush/modal-venv/bin/activate"
  fi
  export PYTHONPATH="/home/soroush/consistency-aware-llm-rankin/src:${PYTHONPATH:-}"
  "/home/soroush/modal-venv/bin/python" "/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/run_method_improvement_audit.py" >>"/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/tmux_stdout.log" 2>>"/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/tmux_stderr.log"
  status=$?
  printf "%s\n" "$status" > "/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/tmux_exit_status.txt"
  exit "$status"
'
EOF
)

tmux new-session -d -s "$SESSION_NAME" "$CMD"
echo "Started tmux session: $SESSION_NAME"
