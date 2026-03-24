# Real OpenAI Pointwise Run — scidocs

**This is a REAL OpenAI run — all scores from live gpt-4o-mini API calls.**

## Configuration

| Param | Value |
|-------|-------|
| Dataset | scidocs |
| Queries | 5 |
| top_k | 15 |
| Model | gpt-4o-mini |
| Provider | openai |
| Mode | **REAL API CALLS** |
| Temperature | 0.3 |

## API Usage

| Metric | Value |
|--------|-------|
| API calls | 75 |
| Cache hits | 0 |
| Prompt tokens | 25,716 |
| Completion tokens | 75 |
| Total tokens | 25,791 |
| Parse failures | 0 |
| Wall time | 37.7s |
| Est. cost | $0.0039 |

## Results

| Method | nDCG@15 | MAP@15 | BEW↓ | PIC↓ |
|--------|---------|---------|------|------|
| llm_pointwise | 0.9540 | 0.8875 | 4.0 | 4.0 |

## Files

- Per-query results: `outputs/openai_robustness_checks/scidocs_pointwise_temp03_q5_k15/pointwise_per_query.csv`
- Summary CSV: `outputs/openai_robustness_checks/scidocs_pointwise_temp03_q5_k15/pointwise_summary.csv`
- Score file: `outputs/openai_robustness_checks/scidocs_pointwise_temp03_q5_k15/pointwise_scores.jsonl`
- Judgment cache: `outputs/openai_robustness_checks/scidocs_pointwise_temp03_q5_k15/judgment_cache`

---
*Generated from REAL OpenAI API calls, not mock/synthetic.*
