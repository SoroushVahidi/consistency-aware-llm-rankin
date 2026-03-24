# Real OpenAI Pairwise Run — scidocs

**This is a REAL OpenAI run — all judgments from live gpt-4o-mini API calls.**

## Configuration

| Param | Value |
|-------|-------|
| Dataset | scidocs |
| Queries | 20 |
| top_k | 15 |
| Model | gpt-4o-mini |
| Provider | openai |
| Mode | **REAL API CALLS** |
| Temperature | 0.0 |

## API Usage

| Metric | Value |
|--------|-------|
| Pairwise comparisons | 2100 |
| API calls | 2100 |
| Cache hits | 0 |
| Prompt tokens | 968,975 |
| Completion tokens | 2,103 |
| Wall time | 1219.0s |
| Est. cost | $0.1466 |
| Errors | 0 |

## Results

| Method | nDCG@15 | MAP@15 | BEW↓ | PIC↓ |
|--------|---------|---------|------|------|
| llm_pairwise_copeland | 0.9566 | 0.9141 | 4.60 | 4.60 |
| bt_from_llm | 0.9566 | 0.9141 | 4.80 | 4.80 |
| win_rate_from_llm | 0.9566 | 0.9141 | 4.60 | 4.60 |
| markov_from_llm | **0.9574** | 0.9171 | 4.85 | 4.85 |
| tournament_sort_from_llm | 0.9533 | 0.9100 | 4.25 | 4.25 |
| greedy_fas_topological | 0.9474 | 0.8936 | 5.25 | 5.25 |
| greedy_fas_weighted_balance | 0.9464 | 0.8924 | 6.40 | 6.40 |
| greedy_fas_copeland | 0.9464 | 0.8924 | 6.40 | 6.40 |
| hybrid_rrf_repaired_copeland_a03 | 0.9563 | 0.9132 | 4.45 | 4.45 |
| hybrid_rrf_unrepaired_copeland_a03 | 0.9566 | 0.9141 | 4.60 | 4.60 |
| hybrid_rrf_repaired_balance_a03 | 0.9563 | 0.9132 | 4.45 | 4.45 |
| hybrid_rrf_unrepaired_balance_a03 | 0.9566 | 0.9141 | 4.60 | 4.60 |

## Repaired vs Unrepaired

| Component | ΔnDCG | ΔBEW | ΔPIC |
|-----------|-------|------|------|
| copeland | -0.0003 | +0.15 | +0.15 |
| balance | -0.0003 | +0.15 | +0.15 |

## Graph Stats

- Cyclic queries: 19/20 (95.0%)
- Avg FAS edges removed: 7.2

---
*Generated from REAL openai API calls, not mock/synthetic.*
