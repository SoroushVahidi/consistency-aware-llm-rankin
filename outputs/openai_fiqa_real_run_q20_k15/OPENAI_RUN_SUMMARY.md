# Real OpenAI Pairwise Run — fiqa

**This is a REAL OpenAI run — all judgments from live gpt-4o-mini API calls.**

## Configuration

| Param | Value |
|-------|-------|
| Dataset | fiqa |
| Queries | 10 |
| top_k | 15 |
| Model | gpt-4o-mini |
| Provider | openai |
| Mode | **REAL API CALLS** |
| Temperature | 0.0 |

## API Usage

| Metric | Value |
|--------|-------|
| Pairwise comparisons | 46 |
| API calls | 46 |
| Cache hits | 0 |
| Prompt tokens | 22,510 |
| Completion tokens | 92 |
| Wall time | 72.4s |
| Est. cost | $0.0034 |
| Errors | 0 |

## Results

| Method | nDCG@15 | MAP@15 | BEW↓ | PIC↓ |
|--------|---------|---------|------|------|
| llm_pairwise_copeland | **1.0000** | 1.0000 | 0.20 | 0.20 |
| bt_from_llm | **1.0000** | 1.0000 | 0.20 | 0.20 |
| win_rate_from_llm | **1.0000** | 1.0000 | 0.20 | 0.20 |
| markov_from_llm | **1.0000** | 1.0000 | 0.20 | 0.20 |
| tournament_sort_from_llm | **1.0000** | 1.0000 | 0.10 | 0.10 |
| greedy_fas_topological | **1.0000** | 1.0000 | 0.10 | 0.10 |
| greedy_fas_weighted_balance | **1.0000** | 1.0000 | 0.10 | 0.10 |
| greedy_fas_copeland | **1.0000** | 1.0000 | 0.10 | 0.10 |
| hybrid_rrf_repaired_copeland_a03 | **1.0000** | 1.0000 | 0.10 | 0.10 |
| hybrid_rrf_unrepaired_copeland_a03 | **1.0000** | 1.0000 | 0.20 | 0.20 |
| hybrid_rrf_repaired_balance_a03 | **1.0000** | 1.0000 | 0.10 | 0.10 |
| hybrid_rrf_unrepaired_balance_a03 | **1.0000** | 1.0000 | 0.20 | 0.20 |

## Repaired vs Unrepaired

| Component | ΔnDCG | ΔBEW | ΔPIC |
|-----------|-------|------|------|
| copeland | +0.0000 | +0.10 | +0.10 |
| balance | +0.0000 | +0.10 | +0.10 |

## Graph Stats

- Cyclic queries: 1/10 (10.0%)
- Avg FAS edges removed: 0.1

---
*Generated from REAL openai API calls, not mock/synthetic.*
