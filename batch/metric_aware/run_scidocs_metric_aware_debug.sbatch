#!/bin/bash
#SBATCH --job-name=ma1-scidocs
#SBATCH --output=/mmfs1/home/sv96/consistency-aware-llm-rankin/outputs/slurm/%x-%j.out
#SBATCH --error=/mmfs1/home/sv96/consistency-aware-llm-rankin/outputs/slurm/%x-%j.err
#SBATCH --account=ikoutis
#SBATCH --partition=debug
#SBATCH --qos=debug
#SBATCH --time=08:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G

# First metric-aware FAS experiment: SciDocs ms1 votes, small β × focus grid.
# Requires publication-style inputs under outputs/pub_vote_cmp_all4/scidocs (or v2).
# Adjust REPO / conda env to your Wulver paths if different.

set -euo pipefail

REPO="/mmfs1/home/sv96/consistency-aware-llm-rankin"
mkdir -p "${REPO}/outputs/slurm"

source /apps/easybuild/software/Anaconda3/2023.09-0/etc/profile.d/conda.sh
conda activate feedback-weighted-maximization

cd "${REPO}"

python scripts/run_metric_aware_first_experiment.py \
  --output-root outputs/metric_aware_first/scidocs_ms1

echo "[sbatch] done."
