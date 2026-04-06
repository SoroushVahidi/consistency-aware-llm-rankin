# Real OpenAI Pairwise Run — scidocs

**This is a REAL OpenAI run — all judgments from live gpt-4o-mini API calls.**

## Configuration

| Param | Value |
|-------|-------|
| Dataset | scidocs |
| Queries | 50 |
| top_k | 15 |
| Model | gpt-4o-mini |
| Provider | openai |
| Mode | **REAL API CALLS** |
| Temperature | 0.0 |

## API Usage

| Metric | Value |
|--------|-------|
| Pairwise comparisons | 5250 |
| API calls | 2100 |
| Cache hits | 3150 |
| Prompt tokens | 1,037,848 |
| Completion tokens | 4,214 |
| Wall time | 2387.1s |
| Est. cost | $0.1582 |
| Errors | 0 |

## Results

| Method | nDCG@15 | MAP@15 | BEW↓ | PIC↓ |
|--------|---------|---------|------|------|
| llm_pairwise_copeland | **0.9749** | 0.9452 | 4.32 | 4.32 |
| bt_from_llm | 0.9746 | 0.9445 | 4.36 | 4.36 |
| win_rate_from_llm | **0.9749** | 0.9452 | 4.32 | 4.32 |
| markov_from_llm | 0.9747 | 0.9448 | 4.96 | 4.96 |
| tournament_sort_from_llm | 0.9728 | 0.9415 | 3.86 | 3.86 |
| greedy_fas_topological | 0.9667 | 0.9257 | 5.12 | 5.12 |
| greedy_fas_weighted_balance | 0.9670 | 0.9271 | 6.04 | 6.04 |
| greedy_fas_copeland | 0.9670 | 0.9271 | 6.04 | 6.04 |
| hybrid_rrf_repaired_copeland_a03 | 0.9739 | 0.9424 | 4.46 | 4.46 |
| hybrid_rrf_unrepaired_copeland_a03 | **0.9749** | 0.9452 | 4.32 | 4.32 |
| hybrid_rrf_repaired_balance_a03 | 0.9739 | 0.9424 | 4.46 | 4.46 |
| hybrid_rrf_unrepaired_balance_a03 | **0.9749** | 0.9452 | 4.32 | 4.32 |

## Repaired vs Unrepaired

| Component | ΔnDCG | ΔBEW | ΔPIC |
|-----------|-------|------|------|
| copeland | -0.0010 | -0.14 | -0.14 |
| balance | -0.0010 | -0.14 | -0.14 |

## Graph Stats

- Cyclic queries: 46/50 (92.0%)
- Avg FAS edges removed: 7.4

---
*Generated from REAL openai API calls, not mock/synthetic.*
