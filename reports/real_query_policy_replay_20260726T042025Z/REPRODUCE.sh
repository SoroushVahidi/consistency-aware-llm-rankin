#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
# Refuse if required canonical SciDocs q50 cache hash differs.
EXPECTED_Q50="61c7f5219161276b8115cbdef69a2db748add82e5ee44511a9fee88697da79de"
CACHE="outputs/openai_scidocs_real_pairwise_q50_k15/judgment_cache/llm_pairwise_judgments.jsonl"
if [[ -n "$EXPECTED_Q50" && -f "$CACHE" ]]; then
  GOT=$(sha256sum "$CACHE" | awk '{print $1}')
  if [[ "$GOT" != "$EXPECTED_Q50" ]]; then
    echo "Cache hash mismatch for $CACHE" >&2
    echo "expected $EXPECTED_Q50 got $GOT" >&2
    exit 2
  fi
fi
OUT="${1:-reports/real_query_policy_replay_$(date -u +%Y%m%dT%H%M%SZ)}"
# Never overwrite this directory.
if [[ -e "$OUT" ]]; then
  echo "Refusing to overwrite existing $OUT" >&2
  exit 3
fi
# No network: rely on the Python network guard inside the runner.
PYTHONPATH=src python scripts/run_real_query_policy_replay.py --output-dir "$OUT"
