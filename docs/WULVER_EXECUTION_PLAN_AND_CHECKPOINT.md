# Wulver Execution Plan And Checkpoint

This note records the fast verification checkpoint before heavier publication and exact-solver work.

## Environment checkpoint

Verified in conda env `feedback-weighted-maximization`:

- Python executable:
  - `/home/sv96/.conda/envs/feedback-weighted-maximization/bin/python`
- Python version:
  - `3.11.14`
- `GRB_LICENSE_FILE`:
  - unset
- `gurobipy` import:
  - success
- tiny Gurobi solve:
  - success
  - status `2`
  - objective `1.0`
- observed Gurobi banner:
  - `Restricted license - for non-production use only - expires 2026-11-23`

Verified publication/dependency stack in the same env:

- `datasets 3.6.0`
- `huggingface_hub 0.36.2`
- `torch 2.5.1`

## Dataset checkpoint

Verified processed dataset artifacts exist for:

- `data/processed/beir/scidocs/{queries,documents,qrels}.jsonl`
- `data/processed/beir/scidocs/pairwise/preferences.jsonl`
- `data/processed/beir/fiqa/{queries,documents,qrels}.jsonl`
- `data/processed/beir/fiqa/pairwise/preferences.jsonl`
- `data/processed/hotpotqa/{queries,documents,qrels}.jsonl`
- `data/processed/hotpotqa/pairwise/preferences.jsonl`
- `data/processed/bright/{queries,documents,qrels}.jsonl`
- `data/processed/bright/pairwise/preferences.jsonl`

Verified load counts in the conda env:

- `scidocs`: `1000` queries, `25657` documents, `29928` qrels
- `fiqa`: `6648` queries, `57638` documents, `17110` qrels
- `hotpotqa`: `7405` queries, `66568` documents, `73642` qrels
- `bright`: `1384` queries, `55643` documents, `1271958` qrels

## Publication-pipeline checkpoint

Current inclusion state before further changes:

- `scripts/run_publication_vote_suite.py`
  - includes `scidocs`
  - includes `hotpotqa`
  - includes `bright` only when `--include-bright` is passed
  - does **not** include `fiqa`
- `scripts/build_paper_evidence_package.py`
  - includes `scidocs`, `hotpotqa`, `bright`
  - does **not** include `fiqa`
- `scripts/summarize_publication_vote_suite.py`
  - includes `scidocs`, `hotpotqa`, `bright`
  - does **not** include `fiqa`

## Exact/ILP checkpoint

- `src/consistency_ranker/mwfas_solver.py`
  - `method="ilp"` is still a stub that raises `NotImplementedError`
- `src/consistency_ranker/exact_fas.py`
  - contains a brute-force exact MWFAS solver for very small graphs

## Highest-value next actions

1. Extend the publication-vote and paper-package scripts so FiQA is handled alongside SciDocs, HotpotQA, and BRIGHT.
2. Run the canonical publication-vote suite in the verified conda env and rebuild the paper evidence package.
3. Audit the exact/ILP path and, if feasible without destabilizing the repo, replace the stubbed `ilp` backend with a real Gurobi-backed exact solver plus a tiny correctness test.
4. Re-run key smoke tests, clean docs/status files, and only then decide whether the repo is coherent enough for commit/push.
