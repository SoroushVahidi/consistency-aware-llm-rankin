# Real Gemini Pairwise Pilot — SciDocs

**This is a REAL Gemini pilot — all judgments come from live Google Gemini API calls.**

**Label: REAL GEMINI PILOT (2 queries, PARTIAL — API error) — NOT mock/synthetic**

## Experiment Configuration

| Parameter | Value |
|-----------|-------|
| Dataset | scidocs |
| Queries | 2 (sampled from 1000 eligible) |
| Top-k candidates | 20 |
| Seed | 42 |
| Model | gemini-3.1-flash-lite-preview |
| Provider | **gemini** (Google Gemini) |
| LLM mode | **REAL API CALLS** |
| Position debiasing | DISABLED |
| Temperature | 0.0 (deterministic) |
| Prompt template | prompts/pairwise_comparison.txt |

## API Usage

| Metric | Value |
|--------|-------|
| Total pairwise comparisons | 380 |
| API calls | 307 |
| Cache hits | 184 |
| Prompt tokens | 145,247 |
| Completion tokens | 431 |
| Total tokens | 145,678 |
| Wall time | 2897.6s |
| Errors | 1 |
| Rate limit events | 1 |

**Partial run** — stopped at API error: `429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 500, model: gemini-3.1-flash-lite\nPlease retry in 41.596516912s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-3.1-flash-lite'}, 'quotaValue': '500'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '41s'}]}}`

### Rate Limit / Retry Issues

- query 3 [dc344ea8e993584b924522d95febaeb74de2ad30]: rate limit / quota exhausted

## Pilot Comparison Table (nDCG results)

All methods consume the **same real Gemini pairwise judgments**.

| Method | nDCG@20 | MAP@20 | P@20 | R@20 | BEW↓ | PIC↓ |
|--------|---------|---------|-------|-------|------|------|
| llm_pairwise_copeland | **0.9855** | 0.9583 | 0.2250 | 1.0000 | 16.00 | 16.00 |
| bt_from_llm | 0.9810 | 0.9464 | 0.2250 | 1.0000 | 14.50 | 14.50 |
| win_rate_from_llm | **0.9855** | 0.9583 | 0.2250 | 1.0000 | 16.00 | 16.00 |
| markov_from_llm | 0.9524 | 0.9021 | 0.2250 | 1.0000 | 22.00 | 22.00 |
| tournament_sort_from_llm | 0.9779 | 0.9437 | 0.2250 | 1.0000 | 10.50 | 10.50 |
| greedy_fas_topological | 0.8408 | 0.6973 | 0.2250 | 1.0000 | 47.00 | 47.00 |
| greedy_fas_weighted_balance | 0.8447 | 0.7020 | 0.2250 | 1.0000 | 42.50 | 42.50 |
| greedy_fas_copeland | 0.8447 | 0.7020 | 0.2250 | 1.0000 | 42.50 | 42.50 |
| hybrid_rrf_repaired_copeland_a03 | 0.9810 | 0.9464 | 0.2250 | 1.0000 | 19.50 | 19.50 |
| hybrid_rrf_unrepaired_copeland_a03 | **0.9855** | 0.9583 | 0.2250 | 1.0000 | 16.00 | 16.00 |
| hybrid_rrf_repaired_balance_a03 | 0.9810 | 0.9464 | 0.2250 | 1.0000 | 19.50 | 19.50 |
| hybrid_rrf_unrepaired_balance_a03 | **0.9855** | 0.9583 | 0.2250 | 1.0000 | 16.00 | 16.00 |

## Repaired vs Unrepaired Deltas

Positive Δ means repaired is *better* (higher nDCG / lower BEW).

| Component | nDCG Δ | BEW Δ | PIC Δ |
|-----------|--------|-------|-------|
| copeland | -0.0045 | -3.50 | -3.50 |
| balance | -0.0045 | -3.50 | -3.50 |

## Graph Repair Statistics

- Cyclic preference graphs: 2/2 (100.0%)
- Average FAS edges removed: 64.5

## Analysis & Recommendation

**Best method by nDCG@20:** `llm_pairwise_copeland` (0.9855)

### Does repair help or hurt relative to aggregation?

Repair **does not help** on either component in this pilot. Unrepaired aggregation matches or exceeds repaired variants.

## Files

- Per-query results: `outputs/gemini_scidocs_real_pilot/gemini_per_query.csv`
- Summary CSV: `outputs/gemini_scidocs_real_pilot/gemini_summary.csv`
- Raw judgments: `outputs/gemini_scidocs_real_pilot/judgments.jsonl`
- Config: `outputs/gemini_scidocs_real_pilot/config.json`
- Judgment cache: `outputs/gemini_scidocs_real_pilot/judgment_cache`

---
*This report was generated from REAL Google Gemini API calls, not mock/synthetic judgments.*
