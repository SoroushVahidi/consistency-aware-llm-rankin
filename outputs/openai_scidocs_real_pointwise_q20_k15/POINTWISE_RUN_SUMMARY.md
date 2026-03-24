# Real OpenAI Pointwise Run — scidocs

**This is a REAL OpenAI run — all scores from live gpt-4o-mini API calls.**

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
| API calls | 300 |
| Cache hits | 0 |
| Prompt tokens | 103,525 |
| Completion tokens | 300 |
| Total tokens | 103,825 |
| Parse failures | 0 |
| Wall time | 175.1s |
| Est. cost | $0.0157 |

## Results

| Method | nDCG@15 | MAP@15 | BEW↓ | PIC↓ |
|--------|---------|---------|------|------|
| llm_pointwise | 0.9081 | 0.8144 | 8.95 | 8.95 |

## Files

- Per-query results: `outputs/openai_scidocs_real_pointwise_q20_k15/pointwise_per_query.csv`
- Summary CSV: `outputs/openai_scidocs_real_pointwise_q20_k15/pointwise_summary.csv`
- Score file: `outputs/openai_scidocs_real_pointwise_q20_k15/pointwise_scores.jsonl`
- Judgment cache: `outputs/openai_scidocs_real_pointwise_q20_k15/judgment_cache`

---
*Generated from REAL OpenAI API calls, not mock/synthetic.*
