# PARSER_AUDIT

## Pairwise parser

Source: `src/rerankers/llm_pairwise.py::_parse_winner`

- Accepted outputs:
  - Any response whose uppercased, stripped text starts with `A` parses to `A`.
  - Any response whose uppercased, stripped text starts with `B` parses to `B`.
  - Otherwise, any text containing `A` but not `B` parses to `A`.
  - Otherwise, any text containing `B` but not `A` parses to `B`.
- Malformed handling:
  - Any remaining response defaults to `A`.
- Ambiguous handling:
  - Ambiguous or nonconforming outputs are not rejected; they collapse into the default `A` path.
- Retries:
  - OpenAI: up to four retries with exponential backoff on transient errors.
  - Gemini: up to eight total retry attempts (`MAX_RETRIES + 4`) for transient rate limits.
- Default label:
  - `A`.
- Fallback behavior:
  - Silent parser fallback to `A`; no dedicated audit field records when this occurred.
- Provider differences:
  - Provider-specific retry logic differs, but parsing logic is shared.

## Pointwise parser

Source: `src/rerankers/llm_pointwise.py::_parse_score`

- Accepted outputs:
  - First 1- or 2-digit integer in the response.
- Malformed handling:
  - In non-strict mode, absence of an integer falls back to score `5.0`.
- Ambiguous handling:
  - The parser does not separately record ambiguity; any first integer is accepted.
- Default / fallback:
  - `5.0` if no integer is found and strict parsing is disabled.

## Listwise parser

Source: `src/rerankers/llm_listwise.py::_parse_ranking`

- Accepted outputs:
  - Any response containing digits; the parser extracts all integers, filters to valid indices, removes duplicates, and appends any missing indices in their original order.
- Malformed handling:
  - In non-strict mode, responses with no digits would collapse to the original order after the "append missing indices" step.
- Ambiguous handling:
  - Extra prose is tolerated if the response still contains parseable integers.

## Provenance gap

- Pairwise committed caches preserve only final `winner` / `loser` records, not raw response text.
- Pointwise committed caches preserve only parsed numeric scores, not raw response text.
- Listwise committed caches preserve raw `response_text`.
- Because pairwise raw responses are absent, ambiguous-response counts, fallback-to-`A` counts, exact-vs-verbose breakdowns, and alternative reparsing policies P1–P4 are **not reproducible from the current committed artifact set**.
