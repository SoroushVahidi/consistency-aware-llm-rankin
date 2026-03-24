# Real OpenAI Listwise Run — scidocs

**This is a REAL OpenAI run — rankings come from live gpt-4o-mini API calls.**

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
| Window size | 15 |
| Step size | 7 |
| Num passes | 1 |

## API Usage

| Metric | Value |
|--------|-------|
| API calls | 20 |
| Cache hits | 0 |
| Prompt tokens | 29,365 |
| Completion tokens | 1,168 |
| Total tokens | 30,533 |
| Wall time | 35.0s |
| Est. cost | $0.0051 |
| Parse failures | 0 |

## Results

| Method | nDCG@15 | MAP@15 | BEW↓ | PIC↓ |
|--------|---------|---------|------|------|
| llm_listwise | 0.9537 | 0.919 | 2.75 | 2.75 |

---
*Generated from REAL openai API calls, not mock/synthetic.*
