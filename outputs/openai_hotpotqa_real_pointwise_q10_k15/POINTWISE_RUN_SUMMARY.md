# Real OpenAI Pointwise Run — hotpotqa

**This is a REAL OpenAI run — all scores from live gpt-4o-mini API calls.**

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
| API calls | 100 |
| Cache hits | 0 |
| Prompt tokens | 29,518 |
| Completion tokens | 100 |
| Total tokens | 29,618 |
| Parse failures | 0 |
| Wall time | 66.4s |
| Est. cost | $0.0045 |

## Results

| Method | nDCG@15 | MAP@15 | BEW↓ | PIC↓ |
|--------|---------|---------|------|------|
| llm_pointwise | 0.8262 | 0.7542 | 1.2 | 1.2 |

## Files

- Per-query results: `outputs/openai_hotpotqa_real_pointwise_q10_k15/pointwise_per_query.csv`
- Summary CSV: `outputs/openai_hotpotqa_real_pointwise_q10_k15/pointwise_summary.csv`
- Score file: `outputs/openai_hotpotqa_real_pointwise_q10_k15/pointwise_scores.jsonl`
- Judgment cache: `outputs/openai_hotpotqa_real_pointwise_q10_k15/judgment_cache`

---
*Generated from REAL OpenAI API calls, not mock/synthetic.*
