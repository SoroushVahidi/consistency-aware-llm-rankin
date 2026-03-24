# Real OpenAI Listwise Run — scidocs

**This is a REAL OpenAI run — rankings come from live gpt-4o-mini API calls.**

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
| Window size | 15 |
| Step size | 7 |
| Num passes | 1 |

## API Usage

| Metric | Value |
|--------|-------|
| API calls | 5 |
| Cache hits | 0 |
| Prompt tokens | 7,402 |
| Completion tokens | 291 |
| Total tokens | 7,693 |
| Wall time | 10.7s |
| Est. cost | $0.0013 |
| Parse failures | 0 |

## Results

| Method | nDCG@15 | MAP@15 | BEW↓ | PIC↓ |
|--------|---------|---------|------|------|
| llm_listwise | 0.9673 | 0.9253 | 3.0 | 3.0 |

---
*Generated from REAL openai API calls, not mock/synthetic.*
