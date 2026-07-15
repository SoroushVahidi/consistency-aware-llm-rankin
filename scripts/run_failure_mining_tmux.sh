#!/usr/bin/env bash
# Failure-mining experiment runner (for tmux session failure_mining)
#
# NOTE (2026-07-09): the original bounded LLM run in reports/failure_mining_llm
# hit a bug in llm_runner.py (rerank_query() called with a nonexistent
# doc_texts= kwarg), so every one of its 1100 LLM calls errored out with zero
# real responses despite valid Cohere/CloudRift/Azure credentials. That bug is
# now fixed (see src/consistency_ranker/failure_mining/llm_runner.py and
# src/rerankers/llm_pairwise.py). reports/failure_mining_llm is left in place
# untouched for provenance; the corrected LLM run below writes to a new
# directory, reports/failure_mining_llm_v2, so its --resume checkpoint isn't
# poisoned by the all-error records. CloudRift is dropped from the provider
# list because its model backend currently returns 503 "no active servers"
# (an account/infra state, not a code bug) and retrying it burns ~30-60s per
# pairwise comparison; re-add it once CloudRift has an active deployment.
set -euo pipefail
cd /home/soroush/consistency-aware-llm-rankin
source .venv/bin/activate

echo "=== Failure mining experiment runner started at $(date -Iseconds) ==="

echo "--- Smoke test (non-LLM) ---"
python scripts/run_failure_mining.py \
  --datasets scidocs \
  --max-queries 3 \
  --max-candidates 10 \
  --providers none \
  --use-cache \
  --resume \
  --output-dir reports/failure_mining_smoke \
  --log-file reports/failure_mining_smoke/run.log

echo "--- Full non-LLM experiment (resume: fills in hotpotqa) ---"
python scripts/run_failure_mining.py \
  --datasets scidocs fiqa hotpotqa bright \
  --max-queries 100 \
  --max-candidates 20 \
  --providers none \
  --use-cache \
  --resume \
  --output-dir reports/failure_mining \
  --log-file reports/failure_mining/run.log

echo "--- LLM smoke test (fixed runner, tiny scale) ---"
python scripts/run_failure_mining.py \
  --datasets scidocs \
  --max-queries 2 \
  --max-candidates 5 \
  --providers cohere,gemini,azure \
  --use-cache \
  --resume \
  --output-dir reports/failure_mining_llm_smoke_v2 \
  --log-file reports/failure_mining_llm_smoke_v2/run.log

echo "--- Bounded LLM experiment (fixed runner; cloudrift excluded, see note above) ---"
python scripts/run_failure_mining.py \
  --datasets scidocs fiqa hotpotqa bright \
  --max-queries 25 \
  --max-candidates 10 \
  --providers cohere,gemini,azure \
  --use-cache \
  --resume \
  --output-dir reports/failure_mining_llm_v2 \
  --log-file reports/failure_mining_llm_v2/run.log

echo "=== All failure mining runs complete at $(date -Iseconds) ==="
