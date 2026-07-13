# RESPONSE_QUALITY_REPORT

Scope: the 12,020 raw pairwise-direction responses with preserved text in
`reports/failure_mining_llm_v3/llm_prompt_call_log.jsonl` (Cohere and Azure
only -- OpenAI's primary pilot and the Gemini pilot preserve no raw response
text; see PARSER_AUDIT.md's coverage caveat). Categories are defined in
`classify_response()` and reproduced in PARSER_AUDIT.md.

| Provider | Dataset | Total | Exact | Verbose-valid | Contains-only | Ambiguous | Malformed | Empty | Fallback-used | Fallback rate |
|---|---|---|---|---|---|---|---|---|---|---|
| azure | bright | 2050 | 1978 | 3 | 58 | 11 | 0 | 0 | 11 | 0.54% |
| azure | fiqa | 2250 | 2250 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00% |
| azure | hotpotqa | 1710 | 1628 | 0 | 50 | 18 | 14 | 0 | 32 | 1.87% |
| cohere | bright | 2050 | 2024 | 0 | 3 | 0 | 23 | 0 | 23 | 1.12% |
| cohere | fiqa | 2250 | 2250 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00% |
| cohere | hotpotqa | 1710 | 1645 | 0 | 0 | 0 | 65 | 0 | 65 | 3.80% |

**Pooled: 12,020 responses, 131 fallback-triggering (1.09%), 0 empty
responses.** Retry distribution: 0 retries recorded for every one of the 400
Cohere+Azure query-regime records (`retry_count == 0` throughout;
`llm_call_records.jsonl`) -- the transport layer never needed a retry in this
run.

## Reading this table correctly

- **FiQA has zero fallback-triggering responses for both providers.** Both
  models answered every FiQA comparison with an unambiguous `"A"`/`"B"`
  (mostly exact single-character). This is a genuine, dataset-dependent
  quality difference, not a parsing artifact.
- **`bright` and `hotpotqa` are where quality problems concentrate**, and
  Cohere is worse than Azure on both (hotpotqa: 3.80% vs 1.87%; bright: 1.12%
  vs 0.54%).
- **"Malformed" dominates over "ambiguous"** wherever fallback occurs (e.g.
  cohere/hotpotqa: 65 malformed, 0 ambiguous) -- meaning the typical failure
  mode is a response containing *neither* letter (a refusal, an off-format
  completion), not a response hedging between both.
- **Fallback rate alone understates the true impact.** A separate, larger
  source of lost signal is forward/reverse *disagreement* between two
  individually clean responses (not counted here as "fallback" since neither
  response is ambiguous/malformed on its own) -- see FORWARD_REVERSE_REPORT.md
  and the `pairs_excluded_fwd_rev_disagreement` counts in
  `policy_sensitivity_full.csv`, which are typically several times larger
  than the ambiguous/malformed counts above.

Per-response detail (one row per raw response) is in `parsed_response_audit.csv`.
