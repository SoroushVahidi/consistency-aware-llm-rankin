# Real OpenAI Listwise Run — hotpotqa

**This is a REAL OpenAI run — rankings come from live gpt-4o-mini API calls.**

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
| Window size | 15 |
| Step size | 7 |
| Num passes | 1 |

## API Usage

| Metric | Value |
|--------|-------|
| API calls | 10 |
| Cache hits | 0 |
| Prompt tokens | 11,359 |
| Completion tokens | 386 |
| Total tokens | 11,745 |
| Wall time | 11.5s |
| Est. cost | $0.0019 |
| Parse failures | 0 |

## Results

| Method | nDCG@15 | MAP@15 | BEW↓ | PIC↓ |
|--------|---------|---------|------|------|
| llm_listwise | 0.8987 | 0.8667 | 0.6 | 0.6 |

---
*Generated from REAL openai API calls, not mock/synthetic.*
