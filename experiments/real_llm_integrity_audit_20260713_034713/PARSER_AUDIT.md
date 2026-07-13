# PARSER_AUDIT

## Location

`src/rerankers/llm_pairwise.py::_parse_winner` (identical on origin/main and in
the locally-modified copy that produced the Cohere/Azure corpus -- this
function itself was not touched by the local modifications, only its caller
was instrumented to log prompts/responses). Used, unmodified, by every
provider (OpenAI, Gemini, Cohere, Azure) via the shared `compare_pair()`.

```python
def _parse_winner(response_text: str) -> str:
    """Parse 'A' or 'B' from LLM response."""
    text = response_text.strip().upper()
    if text.startswith("A"):
        return "A"
    if text.startswith("B"):
        return "B"
    if "A" in text and "B" not in text:
        return "A"
    if "B" in text and "A" not in text:
        return "B"
    return "A"
```

## Accepted outputs

- Exact single-character `"A"` or `"B"` (case-insensitive, whitespace-trimmed).
- Any response starting with `"A"` or `"B"` (e.g. `"A, because..."`).
- Any response that mentions exactly one of the two letters anywhere, even if
  it doesn't start with it.

## Ambiguous handling

A response containing **both** `"A"` and `"B"` and not starting with either
falls through all four `if` branches to the final `return "A"`. **This is
silent**: the function's return type is always `"A"`/`"B"`; there is no
sentinel, exception, or flag distinguishing this case from a genuine, clean
`"A"` response.

## Malformed handling

A response containing **neither** letter (empty string, a refusal, a
truncated/garbled completion) hits the same final `return "A"` fallback,
indistinguishable from the ambiguous case above and from a clean `"A"`.

## Default label

**`"A"` in every fallback case.** There is no abstain, no error, no
tie-breaking by any other signal (e.g. re-prompting, majority-of-retries,
random). Confirmed empirically: `parsed_response_audit.csv`'s
`fallback_only` rows (`position_bias_summary.csv`, `scope=fallback_only`) show
`a_rate=1.0` for every provider/dataset group -- this is not a finding about
LLM behavior, it is a direct, mechanical consequence of this line of code, and
is reported here to make sure it is not misread as evidence of the model's
own bias (that evidence is in the `exact_only` rows instead; see
POSITION_BIAS_REPORT.md).

## Retries

`_call_llm` retries on transport/rate-limit errors (`MAX_RETRIES`,
exponential backoff) but never retries on a successfully-returned-but-
unparseable response body -- there is no retry path keyed on parse ambiguity.
Empirically, `llm_call_records.jsonl`'s `retry_count` field is `0` for **all
400** Cohere/Azure records in the v3 corpus (200 each) -- zero transport
retries occurred in this run at all, so this audit's P4 ("retry-success
only") policy is, in this specific corpus, operationally identical to P0 (see
POLICY_SENSITIVITY_REPORT.md).

## The `parse_error` field is dead code

The locally-modified `compare_pair()` (uncommitted; used for the Cohere/Azure
runs) adds:
```python
winner_label = _parse_winner(response_ab)
if winner_label not in ("A", "B"):
    parse_error_ab = f"unparseable response: {response_ab!r}"
```
Because `_parse_winner` **always** returns `"A"` or `"B"` (its final line is
`return "A"`, not `return None` or a raise), this condition can never be
`True`. Confirmed empirically: `parse_error` is `null` in all 12,020
raw-response log rows with preserved text. **The stored data therefore has no
machine-readable signal at all for which parses were ambiguous/malformed vs.
clean** -- recovering that required this audit to re-classify every raw
response's text directly (`classify_response()` in the audit script; see
`parsed_response_audit.csv`).

## The `debias_position=True` combination rule has a structural default-to-first-argument bias

When `config.debias_position` is `True` (the setting used for every Cohere/
Azure call in the v3 corpus -- confirmed via `raw_response_summary.debias_position: true`
in every `llm_call_records.jsonl` row), both the forward (`A=doc_a,B=doc_b`)
and reverse (`A=doc_b,B=doc_a`) prompts are issued, and combined as:

```python
ab_vote = 0 if winner_label == "A" else 1
ba_vote = 1 if winner_ba == "A" else 0
winner_label = "A" if (ab_vote + ba_vote) < 2 else "B"
```

`doc_b` (`id_b`) only wins if **both** directions independently favor it
(`ab_vote + ba_vote == 2`). Any disagreement between the two directions
(`== 1`), or agreement for `doc_a` (`== 0`), resolves to `doc_a`. This means:

- A genuine order-sensitivity disagreement between the forward and reverse
  presentations is **silently resolved in favor of whichever document was
  passed first** (`id_a`, which in `collect_all_pairs()` is simply the
  earlier document in candidate-list order, e.g. by prior retrieval rank) --
  the exact opposite of what "debias" implies.
- This is not a hypothetical edge case: forward/reverse disagreement is
  common in this corpus even among individually clean ("exact") responses --
  Cohere agrees with itself across presentation order only 59-71% of the time
  (Cohen's kappa 0.27-0.45, "fair" to "moderate"); Azure agrees 73-85% of the
  time (kappa 0.47-0.71, "moderate" to "substantial"). See
  FORWARD_REVERSE_REPORT.md.
- The OpenAI primary pairwise pilot uses `debias_position=false` (single
  forward-only call per pair, confirmed via every committed `config.json`),
  so this specific structural bias does not apply to it -- but the plain
  default-to-`"A"`-on-ambiguous-or-malformed-response bias above does.

## Provider differences

The parser itself (`_parse_winner`) is identical across OpenAI, Gemini,
Cohere, and Azure -- there is no provider-specific parsing logic anywhere in
`llm_pairwise.py`. The only provider-relevant configuration differences are
`debias_position` (`false` for the OpenAI primary pilot, `true` for Cohere/
Azure) and which underlying `_call_openai`/`_call_gemini` transport is used.
Response *quality* (ambiguity/malformed rate) does differ materially by
provider -- Cohere's fallback rate is 2-3x Azure's on `bright`/`hotpotqa` and
both are 0% on `fiqa` -- but this is a property of the models' outputs, not
of the parser. See RESPONSE_QUALITY_REPORT.md.

## Coverage caveat for everything downstream of raw text

Of 22,008 total pairwise-direction attempts in the v3 corpus, 12,020 (54.6%)
have preserved raw prompt/response text (`direction` = `"ab"`/`"ba"` in
`llm_prompt_call_log.jsonl`); the remaining 9,988 (45.4%) are within-run cache
hits (`direction = "cached"`) that only ever recorded the already-parsed
winner/loser, never the raw text. **Re-parsing under P1/P2/P3 is therefore
only possible for the 54.6% of pair-directions with preserved text**; cached
pairs are excluded from those policies and counted explicitly
(`pairs_excluded_no_raw_text` in `policy_sensitivity_full.csv`). This is a
real, permanent data-availability ceiling, not a bug in this audit -- if
exact reproducibility of alternate-parse results across the *entire* 200-
record corpus is required, the only path is prospectively re-running with
raw-text logging enabled for every call, cache included (a new experiment,
not a re-parse of stored data).
