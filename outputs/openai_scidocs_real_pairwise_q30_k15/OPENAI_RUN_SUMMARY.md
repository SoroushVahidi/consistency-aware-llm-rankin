# Real OpenAI Pairwise Run — scidocs

**This is a REAL OpenAI run — all judgments from live gpt-4o-mini API calls.**

## Configuration

| Param | Value |
|-------|-------|
| Dataset | scidocs |
| Queries | 30 |
| top_k | 15 |
| Model | gpt-4o-mini |
| Provider | openai |
| Mode | **REAL API CALLS** |
| Temperature | 0.0 |

## API Usage

| Metric | Value |
|--------|-------|
| Pairwise comparisons | 3150 |
| API calls | 1050 |
| Cache hits | 2100 |
| Prompt tokens | 530,278 |
| Completion tokens | 1,050 |
| Wall time | 575.9s |
| Est. cost | $0.0802 |
| Errors | 0 |

## Results

| Method | nDCG@15 | MAP@15 | BEW↓ | PIC↓ |
|--------|---------|---------|------|------|
| llm_pairwise_copeland | 0.9649 | 0.9279 | 4.93 | 4.93 |
| bt_from_llm | **0.9652** | 0.9287 | 5.03 | 5.03 |
| win_rate_from_llm | 0.9649 | 0.9279 | 4.93 | 4.93 |
| markov_from_llm | 0.9647 | 0.9279 | 5.23 | 5.23 |
| tournament_sort_from_llm | 0.9626 | 0.9249 | 4.33 | 4.33 |
| greedy_fas_topological | 0.9562 | 0.9076 | 5.33 | 5.33 |
| greedy_fas_weighted_balance | 0.9562 | 0.9085 | 6.47 | 6.47 |
| greedy_fas_copeland | 0.9562 | 0.9085 | 6.47 | 6.47 |
| hybrid_rrf_repaired_copeland_a03 | 0.9640 | 0.9253 | 4.70 | 4.70 |
| hybrid_rrf_unrepaired_copeland_a03 | 0.9649 | 0.9279 | 4.93 | 4.93 |
| hybrid_rrf_repaired_balance_a03 | 0.9640 | 0.9253 | 4.70 | 4.70 |
| hybrid_rrf_unrepaired_balance_a03 | 0.9649 | 0.9279 | 4.93 | 4.93 |

## Repaired vs Unrepaired

| Component | ΔnDCG | ΔBEW | ΔPIC |
|-----------|-------|------|------|
| copeland | -0.0009 | +0.23 | +0.23 |
| balance | -0.0009 | +0.23 | +0.23 |

## Graph Stats

- Cyclic queries: 29/30 (96.7%)
- Avg FAS edges removed: 7.8

---
*Generated from REAL openai API calls, not mock/synthetic.*
