#!/bin/bash
#SBATCH --job-name=ma1-scidocs
#SBATCH --partition=debug
#SBATCH --qos=debug
#SBATCH --time=08:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G

# Paths: set METRIC_AWARE_REPO before submit, or submit from repo root (SLURM_SUBMIT_DIR).
# Uncomment #SBATCH --account=YOUR_ACCOUNT if your site requires it.

#SBATCH --output=outputs/slurm/%x-%j.out
#SBATCH --error=outputs/slurm/%x-%j.err

# First metric-aware FAS experiment: SciDocs ms1 votes, small β × focus grid.
# Requires publication-style inputs under outputs/pub_vote_cmp_all4/scidocs (or v2).

set -euo pipefail

REPO="${METRIC_AWARE_REPO:-${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}}"
cd "${REPO}"
mkdir -p "${REPO}/outputs/slurm"

# Conda (Wulver-style) — override or replace with venv:
#   source "${REPO}/.venv/bin/activate"
if [[ -f /apps/easybuild/software/Anaconda3/2023.09-0/etc/profile.d/conda.sh ]]; then
  # shellcheck source=/dev/null
  source /apps/easybuild/software/Anaconda3/2023.09-0/etc/profile.d/conda.sh
  conda activate feedback-weighted-maximization
fi

export PYTHONPATH="${REPO}/src${PYTHONPATH:+:${PYTHONPATH}}"

python scripts/run_metric_aware_first_experiment.py \
  --output-root outputs/metric_aware_first/scidocs_ms1

echo "[sbatch] done."
