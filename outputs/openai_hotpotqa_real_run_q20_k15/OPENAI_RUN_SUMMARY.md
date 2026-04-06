# Real OpenAI Pairwise Run — hotpotqa

**This is a REAL OpenAI run — all judgments from live gpt-4o-mini API calls.**

## Configuration

| Param | Value |
|-------|-------|
| Dataset | hotpotqa |
| Queries | 20 |
| top_k | 15 |
| Model | gpt-4o-mini |
| Provider | openai |
| Mode | **REAL API CALLS** |
| Temperature | 0.0 |

## API Usage

| Metric | Value |
|--------|-------|
| Pairwise comparisons | 900 |
| API calls | 900 |
| Cache hits | 0 |
| Prompt tokens | 314,442 |
| Completion tokens | 1,856 |
| Wall time | 1040.5s |
| Est. cost | $0.0483 |
| Errors | 0 |

## Results

| Method | nDCG@15 | MAP@15 | BEW↓ | PIC↓ |
|--------|---------|---------|------|------|
| llm_pairwise_copeland | 0.9096 | 0.8662 | 3.35 | 3.35 |
| bt_from_llm | 0.9096 | 0.8662 | 3.45 | 3.45 |
| win_rate_from_llm | 0.9096 | 0.8662 | 3.35 | 3.35 |
| markov_from_llm | 0.9174 | 0.8767 | 3.55 | 3.55 |
| tournament_sort_from_llm | **0.9271** | 0.8958 | 2.35 | 2.35 |
| greedy_fas_topological | 0.9061 | 0.8621 | 3.05 | 3.05 |
| greedy_fas_weighted_balance | 0.9076 | 0.8639 | 3.70 | 3.70 |
| greedy_fas_copeland | 0.9076 | 0.8639 | 3.70 | 3.70 |
| hybrid_rrf_repaired_copeland_a03 | 0.9096 | 0.8662 | 3.20 | 3.20 |
| hybrid_rrf_unrepaired_copeland_a03 | 0.9096 | 0.8662 | 3.35 | 3.35 |
| hybrid_rrf_repaired_balance_a03 | 0.9096 | 0.8662 | 3.20 | 3.20 |
| hybrid_rrf_unrepaired_balance_a03 | 0.9096 | 0.8662 | 3.35 | 3.35 |

## Repaired vs Unrepaired

| Component | ΔnDCG | ΔBEW | ΔPIC |
|-----------|-------|------|------|
| copeland | +0.0000 | +0.15 | +0.15 |
| balance | +0.0000 | +0.15 | +0.15 |

## Graph Stats

- Cyclic queries: 16/20 (80.0%)
- Avg FAS edges removed: 4.2

---
*Generated from REAL openai API calls, not mock/synthetic.*
