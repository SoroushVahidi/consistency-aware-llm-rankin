#!/usr/bin/env bash
#SBATCH --account=ikoutis
#SBATCH --partition=debug_gpu
#SBATCH --qos=debug
#SBATCH --gres=gpu:a100_40g:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=14G
#SBATCH --time=07:45:00
#SBATCH --no-requeue
#SBATCH --job-name=jdsa-prospective-v2
#SBATCH --output=logs/slurm-%j.out
#SBATCH --error=logs/slurm-%j.err
#SBATCH --signal=B:TERM@60
set -euo pipefail
umask 077
run_dir=${SLURM_SUBMIT_DIR:?}
inference_python=${PROSPECTIVE_PYTHON:?}
dependencies=${PROSPECTIVE_DEPENDENCIES:?}
cd "$run_dir/worktree"
export PYTHONPATH="$dependencies:$PWD/src"
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
export CUBLAS_WORKSPACE_CONFIG=:4096:8 TOKENIZERS_PARALLELISM=false
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_DISABLE_PROGRESS_BARS=1 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
# Preserve Slurm's CUDA_VISIBLE_DEVICES; never select a physical GPU manually.
finish() {
  result=$?
  printf '%s\n' "$result" > "$run_dir/logs/job-$SLURM_JOB_ID.EXIT_CODE"
  printf '%s\n' "$result" > "$run_dir/logs/EXIT_CODE"
  date -u +%FT%TZ > "$run_dir/logs/job-$SLURM_JOB_ID.FINISHED_UTC"
}
trap finish EXIT
printf '%s\n' "$SLURM_JOB_ID" > "$run_dir/logs/SLURM_JOB_ID"
date -u +%FT%TZ > "$run_dir/logs/job-$SLURM_JOB_ID.STARTED_UTC"
timeout --signal=TERM --kill-after=30s 28200 "$inference_python" -u \
  -m experiments.jdsa_prospective_v1.worker --run "$run_dir" "$@" \
  > "$run_dir/logs/worker-$SLURM_JOB_ID.log" 2>&1
