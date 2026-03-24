# Real OpenAI Pairwise Run — hotpotqa

**This is a REAL OpenAI run — all judgments from live gpt-4o-mini API calls.**

## Configuration

| Param | Value |
|-------|-------|
| Dataset | hotpotqa |
| Queries | 10 |
| top_k | 15 |
| Model | gpt-4o-mini |
| Provider | openai |
| Mode | **REAL API CALLS** |
| Temperature | 0.0 |

## API Usage

| Metric | Value |
|--------|-------|
| Pairwise comparisons | 450 |
| API calls | 450 |
| Cache hits | 0 |
| Prompt tokens | 160,722 |
| Completion tokens | 483 |
| Wall time | 279.0s |
| Est. cost | $0.0244 |
| Errors | 0 |

## Results

| Method | nDCG@15 | MAP@15 | BEW↓ | PIC↓ |
|--------|---------|---------|------|------|
| llm_pairwise_copeland | 0.8929 | 0.8444 | 3.10 | 3.10 |
| bt_from_llm | 0.8859 | 0.8361 | 3.00 | 3.00 |
| win_rate_from_llm | 0.8929 | 0.8444 | 3.10 | 3.10 |
| markov_from_llm | 0.8868 | 0.8375 | 3.70 | 3.70 |
| tournament_sort_from_llm | **0.9008** | 0.8583 | 2.50 | 2.50 |
| greedy_fas_topological | 0.8778 | 0.8267 | 3.80 | 3.80 |
| greedy_fas_weighted_balance | 0.8778 | 0.8267 | 4.30 | 4.30 |
| greedy_fas_copeland | 0.8778 | 0.8267 | 4.30 | 4.30 |
| hybrid_rrf_repaired_copeland_a03 | 0.8859 | 0.8361 | 2.90 | 2.90 |
| hybrid_rrf_unrepaired_copeland_a03 | 0.8929 | 0.8444 | 3.10 | 3.10 |
| hybrid_rrf_repaired_balance_a03 | 0.8859 | 0.8361 | 2.90 | 2.90 |
| hybrid_rrf_unrepaired_balance_a03 | 0.8929 | 0.8444 | 3.10 | 3.10 |

## Repaired vs Unrepaired

| Component | ΔnDCG | ΔBEW | ΔPIC |
|-----------|-------|------|------|
| copeland | -0.0070 | +0.20 | +0.20 |
| balance | -0.0070 | +0.20 | +0.20 |

## Graph Stats

- Cyclic queries: 9/10 (90.0%)
- Avg FAS edges removed: 4.3

---
*Generated from REAL openai API calls, not mock/synthetic.*
