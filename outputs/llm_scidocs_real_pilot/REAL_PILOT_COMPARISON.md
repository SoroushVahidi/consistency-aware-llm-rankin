# Real LLM Pairwise Pilot Comparison — SciDocs

**Status: BLOCKED — OpenAI API quota exhausted**

## What Happened

The experiment infrastructure is fully built and tested, but the OpenAI API key
injected into this environment (`sk-proj-4L…`) returns:

```
Error code: 429 — insufficient_quota
"You exceeded your current quota, please check your plan and billing details."
```

This is a **hard billing limit**, not a transient rate limit. No model works
(tested gpt-4o-mini, gpt-3.5-turbo, gpt-5.4-nano).

## How to Run

Once the API key has billing credits, run:

```bash
source /workspace/.venv/bin/activate
python scripts/run_llm_scidocs_real_pilot.py
```

The script is fully resumable via disk-backed caching — if it gets interrupted,
re-running will pick up where it left off.

## What the Script Will Do

| Step | Description |
|------|-------------|
| 1 | Load SciDocs (1000 queries, 25657 docs, 29928 qrels) |
| 2 | Sample 30 queries (seed=42, deterministic) |
| 3 | Build top-20 candidate pools per query |
| 4 | Collect real LLM pairwise judgments with position debiasing |
| 5 | Evaluate 12 aggregation methods on the same real judgments |
| 6 | Write per-query CSV, summary CSV, judgments JSONL |
| 7 | Generate this comparison report with nDCG results |

## Budget Estimate

| Parameter | Value |
|-----------|-------|
| Queries | 30 |
| Candidates per query | 20 |
| Pairs per query | 190 (= 20×19/2) |
| API calls per pair | 2 (position debiasing: A→B + B→A) |
| Total API calls | **11,400** |
| Model | gpt-4o-mini |
| Est. cost | ~$0.10–$0.30 (gpt-4o-mini pricing) |

## Methods to Be Compared

All methods consume the **same** real LLM pairwise judgments:

| Category | Methods |
|----------|---------|
| LLM Pairwise Baseline | `llm_pairwise_copeland` |
| Tournament Aggregation | `bt_from_llm`, `win_rate_from_llm`, `markov_from_llm`, `tournament_sort_from_llm` |
| FAS-Repaired Graph | `greedy_fas_topological`, `greedy_fas_weighted_balance`, `greedy_fas_copeland` |
| Hybrid Repaired | `hybrid_rrf_repaired_copeland_a03`, `hybrid_rrf_repaired_balance_a03` |
| Hybrid Unrepaired | `hybrid_rrf_unrepaired_copeland_a03`, `hybrid_rrf_unrepaired_balance_a03` |

## Infrastructure Changes Made

### PHASE 1 — Pipeline hardening (`src/rerankers/llm_pairwise.py`)
- Real OpenAI API calls by default (mock only with explicit `dry_run=True`)
- Retry with exponential backoff (4 retries, 2/4/8/16s)
- Immediate fail on hard quota exhaustion (no pointless retries)
- `LLMCallStats` dataclass tracks real token counts from API responses
- Query-aware cache keys for proper resumability
- `stats` parameter flows through `compare_pair` → `collect_all_pairs`

### PHASE 2–6 — Real pilot script (`scripts/run_llm_scidocs_real_pilot.py`)
- Graceful error handling: partial results if some queries succeed
- Honest labeling of partial vs complete runs
- Cost estimation from real token counts
- Full evaluation pipeline (12 methods) on real judgments
- Markdown report with API usage, nDCG table, repair deltas, recommendation

## To Resolve

Add billing credits to the OpenAI account at:
https://platform.openai.com/settings/organization/billing

Or add a funded `OPENAI_API_KEY` to Cursor Cloud Agent secrets at:
https://cursor.com → Dashboard → Cloud Agents → Secrets
