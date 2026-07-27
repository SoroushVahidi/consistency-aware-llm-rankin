#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
source .venv/bin/activate
export PYTHONPATH=src
# --overwrite-existing is required when regenerating into this frozen directory.
# Prefer writing to a fresh path (e.g. /tmp/ps_verify) when only verifying bit-reproduction.
python scripts/run_policy_selection_experiment.py \
  --output-dir "${1:-reports/policy_selection_20260726T030500Z}" \
  --overwrite-existing
pytest tests/test_policy_selection.py -q
