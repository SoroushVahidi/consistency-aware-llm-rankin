# Real OpenAI Pairwise Run — scidocs

**This is a REAL OpenAI run — all judgments from live gpt-4o-mini API calls.**

## Configuration

| Param | Value |
|-------|-------|
| Dataset | scidocs |
| Queries | 1 |
| top_k | 5 |
| Model | gpt-4o-mini |
| Provider | openai |
| Mode | **REAL API CALLS** |
| Temperature | 0.0 |

## API Usage

| Metric | Value |
|--------|-------|
| Pairwise comparisons | 10 |
| API calls | 10 |
| Cache hits | 0 |
| Prompt tokens | 3,832 |
| Completion tokens | 20 |
| Wall time | 10.8s |
| Est. cost | $0.0006 |
| Errors | 0 |

## Results

| Method | nDCG@5 | MAP@5 | BEW↓ | PIC↓ |
|--------|---------|---------|------|------|
| llm_pairwise_copeland | **1.0000** | 1.0000 | 1.00 | 1.00 |
| bt_from_llm | **1.0000** | 1.0000 | 1.00 | 1.00 |
| win_rate_from_llm | **1.0000** | 1.0000 | 1.00 | 1.00 |
| markov_from_llm | **1.0000** | 1.0000 | 1.00 | 1.00 |
| tournament_sort_from_llm | **1.0000** | 1.0000 | 1.00 | 1.00 |
| greedy_fas_topological | **1.0000** | 1.0000 | 1.00 | 1.00 |
| greedy_fas_weighted_balance | **1.0000** | 1.0000 | 1.00 | 1.00 |
| greedy_fas_copeland | **1.0000** | 1.0000 | 1.00 | 1.00 |
| hybrid_rrf_repaired_copeland_a03 | **1.0000** | 1.0000 | 1.00 | 1.00 |
| hybrid_rrf_unrepaired_copeland_a03 | **1.0000** | 1.0000 | 1.00 | 1.00 |
| hybrid_rrf_repaired_balance_a03 | **1.0000** | 1.0000 | 1.00 | 1.00 |
| hybrid_rrf_unrepaired_balance_a03 | **1.0000** | 1.0000 | 1.00 | 1.00 |

## Repaired vs Unrepaired

| Component | ΔnDCG | ΔBEW | ΔPIC |
|-----------|-------|------|------|
| copeland | +0.0000 | +0.00 | +0.00 |
| balance | +0.0000 | +0.00 | +0.00 |

## Graph Stats

- Cyclic queries: 1/1 (100.0%)
- Avg FAS edges removed: 1.0

---
*Generated from REAL openai API calls, not mock/synthetic.*
