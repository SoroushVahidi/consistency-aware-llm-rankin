#!/usr/bin/env bash
# Launch inside an explicitly named detached tmux session; never touch other sessions.
set -euo pipefail
umask 077
if [[ $# -lt 2 ]]; then
  echo "Usage: launch.sh PRIVATE_RUN INFERENCE_PYTHON [--resume] [--validation-only]" >&2
  exit 64
fi
run_dir=$(realpath "$1")
inference_python=$(realpath "$2")
shift 2
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
worktree_dir=$(cd -- "$script_dir/../.." && pwd)
cd "$worktree_dir"
export CUDA_VISIBLE_DEVICES=0 CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
export TOKENIZERS_PARALLELISM=false HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export HF_HUB_DISABLE_TELEMETRY=1 HF_HUB_DISABLE_PROGRESS_BARS=1
export PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
launch_id=$(date -u +%Y%m%dT%H%M%SZ)
finish() {
  result=$?
  printf '%s\n' "$result" > "$run_dir/logs/exit-$launch_id.txt"
  printf '%s\n' "$result" > "$run_dir/logs/EXIT_CODE"
}
trap finish EXIT
printf '%s\n' "${TMUX_PANE:-not-tmux}" > "$run_dir/logs/TMUX_PANE"
date -u +%FT%TZ > "$run_dir/logs/start-$launch_id.txt"
timeout --signal=TERM --kill-after=30s 43200 "$inference_python" -u \
  -m experiments.jdsa_prospective_v1.worker --run "$run_dir" "$@" \
  > "$run_dir/logs/worker-$launch_id.log" 2>&1
