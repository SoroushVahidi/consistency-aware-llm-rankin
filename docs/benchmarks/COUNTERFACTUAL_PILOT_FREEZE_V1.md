# Counterfactual Pilot Freeze v1

Status: **frozen design** — not executed.
Safety branch tip when authored: `backup/pre-counterfactual-pilot-freeze-20260727`
Related: `docs/benchmarks/REAL_COUNTERFACTUAL_BENCHMARK_SPEC.md`
Config: `configs/counterfactual_micro_pilot_v1.json`

Any model replacement requires **panel version v2** and a new freeze document.

## Provider panel (`counterfactual_provider_panel_v1`)

| Provider | Model or deployment | Intended role |
|---|---|---|
| Azure | `gpt-4.1-mini` | closed-model production-style judge |
| Cohere | `command-r-plus-08-2024` | independent Command-family judge |
| Fireworks | `accounts/fireworks/models/gpt-oss-120b` | open-weight or hosted low-cost judge |
| Vertex/Gemini | `gemini-2.5-flash` | independent Gemini-family judge |

For every member, record separately:

- provider;
- endpoint or deployment (sanitized in published artifacts);
- underlying model family;
- exact configured model identifier;
- model version **only if exposed** (often opaque).

Four providers do **not** automatically imply four fully independent model
families. Exact backend revisions may be opaque.

Observed capability-audit notes (connectivity only):

| Provider | Structured output | Token reporting | Latency reporting | Temperature | Max out tokens | Backend revision visible |
|---|---|---|---|---|---|---|
| Azure | yes | yes | yes | 0.0 | 128 | no |
| Cohere | yes | yes | yes | 0.0 | 128 | no |
| Fireworks | yes | yes | yes | 0.0 | 128 | no |
| Gemini | yes | yes | yes | 0.0 | 128 | no |

Seed behavior: client may accept a seed; **determinism is not claimed**.

## Scientific roles

- **qrels** = retrieval-evaluation truth (post-hoc only).
- Each LLM = noisy pairwise judge.
- Azure = production-style reference path, **not** ground truth.
- Fireworks = economical open/hosted path.
- Cohere and Vertex = independent judge families.
- Provider-native rerankers = separate listwise baselines, **not** pairwise judges.

## Frozen pairwise prompt

- Path: `prompts/counterfactual_pairwise_judge_v1.txt`
- Version: `counterfactual_pairwise_judge_v1`
- SHA-256: `6e8038363393bb3e6c70edb61619107a29253fda60b35295c040c3925661fcf0`

Semantic decisions:

- Same substantive instructions for every provider.
- Allows A / B / TIE / ABSTAIN.
- Ties are narrow (essentially equal usefulness).
- Abstention for insufficient/malformed/incomparable evidence.
- No chain-of-thought; structured schema only.
- No qrels, ranks, retriever IDs, prior scores, or selection methods.
- Provider wrapper syntax stays outside the semantic prompt.

## Frozen response schema

- Path: `schemas/counterfactual_pairwise_judgment_v1.json`
- Version: `counterfactual_pairwise_judgment_v1`
- SHA-256: `f8332b7eadcbe92e1c4aed5299a0e3b1214c6d53a68aff3c826fe86147366de7`

```json
{
  "schema_version": "counterfactual_pairwise_judgment_v1",
  "preference": "A | B | TIE | ABSTAIN",
  "confidence": 0.0,
  "evidence_strength": "weak | moderate | strong",
  "reason_code": "direct_relevance | partial_answer | unsupported | ambiguous | other"
}
```

Clarifications:

- `confidence` is provider self-report; **not** assumed calibrated.
- Preserve raw provider-specific signals separately when available.
- Do not compare raw confidence across providers without validation.
- `reason_code` is categorical, not chain-of-thought.

## Presentation order

For unordered pair `{d_i, d_j}`:

- `ab`: A=`d_i`, B=`d_j`
- `ba`: A=`d_j`, B=`d_i`

Stored outcomes must include document identity, presentation order, displayed
label, and normalized document-level preference. Never infer document identity
from the returned letter alone. Position consistency = agreement after mapping
both responses to document IDs.

## Adaptive repeats

Default: one presentation per initially selected pair.

Add a second AB (or swapped-order) call only for:

- position-inconsistent pairs;
- ties or abstentions;
- low-confidence outcomes;
- cross-provider disagreement;
- pairs near the evaluation cutoff;
- pairs whose outcome changes top-k membership.

## Micro-pilot configuration

| Knob | Value |
|---|---|
| Datasets | SciDocs, FiQA, HotpotQA, BRIGHT |
| Queries | 2 per dataset (8 total); IDs frozen in config |
| Pool size \(P\) | 10 |
| Eval cutoff \(k\) | 5 (\(P > k\)) |
| Providers | frozen panel v1 |
| Policies | production UHT, factorial UHT, HYBRID, ROBUST_COMBINED, random pair, prior-only |
| Design | fixed-policy logged shell; **no** full 45-pair×provider matrix |
| Initial pairs/query | 8 |
| Initial calls | \(8 \times 4 \times 8 = 256\) |
| Follow-up reserve | 128 |
| Hard max live calls | **384** |
| Execute now | **false** |

Frozen query IDs (lexicographic first two with positive qrel + query text):

- SciDocs: `01273bd34dacfe9ef887b320f36934d2f9fa9b34`, `012e396b02aa584cb74a65ae14af355e7c897858`
- FiQA: `0`, `1`
- HotpotQA: `5a70eee85542994082a3e3f0`, `5a70f0a75542994082a3e403`
- BRIGHT: `aops:aops_1959_IMO_Problems/Problem_1`, `aops:aops_1971_AHSME_Problems/Problem_26`

## Query-selection caveat

The micro-pilot chooses the lexicographically first two eligible query IDs per
dataset, where "eligible" means: usable query text is present and the query
has at least one positive qrel. This rule is an **operational micro-pilot
eligibility filter only**, not a sampling design:

- It conditions solely on pre-execution qrels *availability* (does this query
  have any judged positive at all?) and text *evaluability* (can a prompt be
  rendered?) — it does not condition on qrel *values*, relevance grades, rank
  positions, or any policy/provider behavior.
- It is **not** a representative-sampling claim. Lexicographically-first
  queries are not a random, stratified, or otherwise representative sample of
  each dataset's query distribution, and no such claim should be inferred from
  micro-pilot results.
- No policy outcome or provider response influenced this selection: query IDs
  are frozen in `configs/counterfactual_micro_pilot_v1.json` before any
  provider call is made, and `query_selection.select_lexicographic_queries`
  reads only `qrels_path`/`queries_path` — it never receives acquisition,
  policy, or provider state.
- Qrels are consulted **only before collection**, solely to establish
  evaluability (does the query have at least one positive judgment?). Qrels
  must never be consulted *during* policy execution or acquisition, and must
  never influence which candidates are pooled or which pairs are selected.
- A later scientific (non-pilot) benchmark **must** replace this eligibility
  filter with a prespecified representative or stratified sampling protocol
  over the full query population, defined and frozen before any query IDs are
  chosen, and versioned separately from this micro-pilot.

## Candidate-pool freeze

- Freeze pools before pairwise calls.
- Identical candidate IDs for all policies/providers in a cell.
- Qrels must not influence pool construction or acquisition.
- Record candidate-pool hashes.
- Prefer the existing canonical multi-ranker pool when available.

## Candidate-pool protocol (implementation)

`candidate_pool.pool_protocol_version = lexical_prior_pool_v1`
(`consistency_ranker.counterfactual_benchmark.pool_builder.POOL_PROTOCOL_VERSION`).

No canonical multi-ranker/RRF fusion pool exists anywhere in this repository
for SciDocs, FiQA, HotpotQA, or BRIGHT (verified by search before this
protocol was implemented). `lexical_prior_pool_v1` is a deterministic
fallback:

- **Retrieval/scoring method**: two independent, qrels-blind lexical priors
  over the full document corpus -- a primary token-overlap-count prior
  (`|query ∩ doc| / sqrt(|doc|)`) and a secondary plain-Jaccard prior
  (`|query ∩ doc| / |query ∪ doc|`). Both are scored over the same
  title+text composition that gets rendered (see rendering policy below).
- **Tie-breaking rule**: ties in the primary prior break by ascending doc id
  (`sorted(primary, key=lambda d: (-primary[d], d))`), so pool construction
  is fully deterministic for fixed corpus content.
- **Ordered candidate IDs, pool size, source data, hash**: recorded per
  query in `candidate_pools.jsonl` as `candidate_ids` (ordered),
  `len(candidate_ids)`, the dataset's `documents_path`, and `pool_hash`
  (sha256 of the ordered candidate-id list).
- **Implementation version**: `pool_protocol_version` on every
  `CandidatePoolRecord`; the collector's freeze verification refuses to run
  if a config's declared `pool_protocol_version` disagrees with the
  implemented one.

**This pool protocol is valid for the operational micro-pilot only.** It is
**not** automatically identical to a canonical multi-ranker/RRF pool a later
scientific benchmark might use, and scientific conclusions drawn from this
micro-pilot apply specifically to results collected under this pool
protocol. Changing the pool protocol requires either a new benchmark version
or an explicit pool-robustness audit comparing outcomes under both
protocols. This task does not implement a new multi-ranker retrieval
pipeline.

## Document rendering and truncation protocol

`candidate_pool.rendering_policy_version = title_plus_prefix_truncate_v1`
(`consistency_ranker.counterfactual_benchmark.pool_builder.RENDERING_POLICY_VERSION`).

Rendering is deterministic and byte-for-byte identical across providers and
across AB/BA orientation swaps (the same excerpt string is reused; only its
position in the prompt changes):

1. Compose the full document as `f"{title}\n\n{text}"` when a non-empty
   `title` field is present, else just `text`.
2. Truncate the composed text to `candidate_pool.max_candidate_chars`
   (currently 1200) via a plain Python string prefix slice. String slicing
   operates on Unicode code points, so a multi-byte UTF-8 character is never
   split mid-sequence.

`max_candidate_chars = 1200` exists because at least one real BRIGHT
document exceeds 9,000,000 characters; without a truncation cap a single
candidate could blow any per-request token budget. Titles are present (and
non-empty) for SciDocs and HotpotQA documents in this corpus, and absent
(empty string) for FiQA and BRIGHT documents -- both cases are exercised by
real data, not just synthetic fixtures.

For every rendered candidate, `candidate_pools.jsonl` records a
`RenderedDocumentRecord` under `rendering_metadata[doc_id]`:

- `document_id`
- `full_document_sha256` -- hash of the complete composed (title+text)
  document, so a truncated excerpt can always be traced back to, without
  ever storing, the full original content;
- `rendered_excerpt_sha256` -- hash of exactly what was (or would be) sent
  to a provider;
- `original_character_count`, `rendered_character_count`;
- `truncated` (bool);
- `truncation_policy` (`rendering_policy_version`, above);
- `title_included` (bool).

The full, untruncated document text is never written to any manifest,
ledger, or trajectory record -- only the bounded excerpt (`truncated_texts`)
and the two hashes above.

**Rendering policy is itself an experimental factor.** A later benchmark
should compare at least one alternative rendering policy (for example, a
different truncation length, a summary-based excerpt, or a different
title-handling rule) before broad scientific claims are made about
judgment quality.

## Token and character caps (derived from rendered fixtures)

The call-count cap (256 initial / 128 reserve / 384 hard max) is authoritative
regardless of token estimates. Token caps below are additional defense in
depth, derived by rendering the real frozen prompt against the actual frozen
query text and real per-dataset document lengths (script-measured, not
invented):

| Quantity | Observed | Derivation |
|---|---|---|
| Prompt template overhead (fixed text, no query/candidates) | 1,344 chars | Direct render of `prompts/counterfactual_pairwise_judge_v1.txt` with empty fields |
| Max real frozen query length | 661 chars | BRIGHT `aops:...Problem_26` |
| Per-dataset document length (p50 / p95 / p99) | scidocs 1034/1980/3566; fiqa 522/2097/3703; hotpotqa 502/1161/1712; bright 1146/3107/19969 (chars) | Full corpus scan of each dataset's `documents.jsonl` |
| Max real document length observed (uncapped, any dataset) | 9,182,738 chars | One BRIGHT document; this is why an explicit `max_candidate_chars` truncation is required — without it, a single candidate could exceed any reasonable per-request token budget |

Frozen `candidate_pool.max_candidate_chars = 1200` (matches the existing
`multi_provider_eval.manifest.build_pilot_manifest` truncation convention).
With that truncation and a conservative 3-chars-per-token ratio (chosen to
over-, not under-, estimate tokens across four different provider
tokenizers):

- Worst-case rendered request: 1,344 (template) + 661 (longest real query) +
  2 × 1,200 (truncated candidates) = 4,405 chars ≈ 1,468 tokens.
- `max_input_tokens_per_request = 2000` (rounded up from ~1,468 with margin).
- `max_output_tokens_per_request = 128` (already frozen in
  `generation_defaults.max_output_tokens`).
- `max_total_input_tokens = 800000` (384 × 2000, rounded up from 768,000).
- `max_total_output_tokens = 60000` (384 × 128 = 49,152, rounded up with
  margin).

These replace the original placeholder ceilings (2,000,000 input /
200,000 output), which were valid but far looser than the 384-call budget
requires. The hard call cap remains the primary safety mechanism; the token
caps exist to catch a malformed or unexpectedly large request before it is
sent, not to substitute for the call cap.

## Trajectory schema

Step fields and terminal fields are defined in
`src/consistency_ranker/counterfactual_pilot/trajectory.py`.

Oracle / qrels metrics appear only on terminal records after execution.

## Operational success vs scientific claims

Operational success: all eight queries load; pools valid and matched; qrels
unavailable to runtime policies; no duplicate request hashes; resume skips
completed calls; responses normalize or fail explicitly; caps hold; terminal
qrels evaluation present; missing cells have explicit reasons.

Scientific claims **not** allowed from the micro-pilot alone: provider/policy
superiority, oracle gap, noninferiority, production readiness.

## Code entry points

- Panel: `consistency_ranker.counterfactual_pilot.panel`
- Schema: `consistency_ranker.counterfactual_pilot.schema`
- Presentation: `consistency_ranker.counterfactual_pilot.presentation`
- Trajectory: `consistency_ranker.counterfactual_pilot.trajectory`
- Prompt: `consistency_ranker.counterfactual_pilot.prompt`
- Query selection: `consistency_ranker.counterfactual_pilot.query_selection`

## v2 addendum: pool-quality and Gemini normalization fix (2026-07-27)

`counterfactual_collector_canary_v1_20260727T145126Z` (the first bounded
4-call canary) surfaced two defects, diagnosed and fixed without touching
the frozen v1 artifacts above:

**1. Content-sufficiency defect in `lexical_prior_pool_v1`.** The primary
prior (`token_overlap / sqrt(doc_token_count)`) has no lower bound on
`doc_token_count`, so a near-empty document can outscore substantive ones
purely through the denominator. Measured directly: the canary's SciDocs
query (`01273bd34dacfe9ef887b320f36934d2f9fa9b34`) had a pool that was
10/10 title-only documents (empty `text` field, only a title survives
composition), and a second frozen SciDocs query was 7/10 title-only —
versus 0/10 for every frozen fiqa/hotpotqa/bright query. Only 1.34% of the
SciDocs corpus has an empty `text` field; the formula, not the corpus, is
what concentrates the pool. All three providers that parsed successfully
in the canary returned `ABSTAIN`/`reason_code=unsupported` — a correct
response to genuinely insufficient content, not a bug in those providers.

Tested (qrels-blind, operational properties only, across all 8 frozen
queries / 80 candidates) against raw token-overlap, plain Jaccard, an RRF
fusion of the two v1 priors, an approximate BM25, and a bounded-denominator
variant of the v1 formula. Raw overlap swings to the opposite failure
(selects a document exceeding 1.8M characters in one BRIGHT query).
Jaccard and RRF-of-the-two-v1-priors are equally or more biased toward
short/empty documents (23.8% and 22.5% title-only, vs. v1's 21.2%) — fusing
two similarly-biased signals does not fix the bias. The bounded-denominator
variant (`overlap / sqrt(max(doc_token_count, 25))`) dropped title-only
share to 1.2% and candidates below 100 rendered characters to 1.2%, with no
new dependency and no rendering-policy change.

**Fix — `lexical_prior_pool_v2`** (`pool_builder.build_candidate_pool_v2`):
a bounded-denominator primary prior plus an explicit, pre-scoring
document-validity gate (`document_validity_v2`): nonempty body text,
≥15 alphabetic tokens, ≥100 substantive characters (thresholds are the
1st-percentile nonempty-body length across all four frozen datasets,
rounded down slightly — hotpotqa was the tightest corpus at 15
tokens/103 chars). Excluded documents are recorded with the valid
candidate that replaced their slot (`CandidatePoolRecord.exclusion_records`).
`pair_selection.select_shared_pairs_v2` re-checks every pool candidate
against the same rule before selecting pairs (defense in depth; a v2 pool
should never contain an invalid candidate by construction). Rendering
(`title_plus_prefix_truncate_v1`, 1,200-char cap) is unchanged — the audit
found no independent rendering defect.

`counterfactual_micro_pilot_v2` / `counterfactual_collector_canary_v2`
change only `candidate_pool.pool_protocol_version`; frozen queries, prompt,
judgment schema, and provider panel are identical to v1.
`config.verify_frozen_contract` maps each `benchmark_version` to its
required `pool_protocol_version` (`BENCHMARK_VERSION_POOL_PROTOCOL`) and
refuses any config that combines them incorrectly.

**2. Vertex AI (`gemini-2.5-flash`) `parse_failure`.** `collector.py` parsed
every provider's raw response with a bare `json.loads(...)`. Azure and
Fireworks are both reached through an OpenAI-compatible chat-completions
endpoint and returned bare JSON for this prompt in both canaries. Cohere is
also reached through an OpenAI-compatible endpoint (Cohere's own
"compatibility" API, `https://api.cohere.ai/compatibility/v1`) and returned
bare JSON in canary v1 -- but see finding 3 below: its reliability is **not**
established, and canary v2 shows it can fail. `provider: vertex`
(`model_family: gemini`, `model_id: gemini-2.5-flash`, `access_path: Google
Vertex AI`) is reached through the native `google-genai` SDK path with no
`response_mime_type`/`response_schema` set, and is documented to wrap
structured output in a markdown code fence by default. The canary retains
only a sha256 of each raw response (never the bytes, by design), so the
exact captured text could not be recovered for direct inspection -- the
diagnosis rests on the code-path asymmetry above, not a captured payload.

**Fix** — `counterfactual_pilot.schema.extract_json_payload`: unwraps a
response *only* when the entire stripped response is a single well-formed
` ```json ... ``` ` (or unlabeled ` ``` ... ``` `) fence; any other shape
(prose around the fence, an unclosed fence, multiple blocks) is returned
unchanged, so the caller's existing strict `json.loads` +
`validate_judgment` still reject it exactly as before. `NormalizedJudgment`
records `wrapper_extraction_used` so it's always visible whether a cell
needed unwrapping. Confirmed live in `counterfactual_collector_canary_v2`
(see that report's `normalized_judgments.jsonl`): Vertex AI's real response
required unwrapping (`wrapper_extraction_used: true`) and then validated
successfully. Azure and Fireworks succeeded without wrapper extraction
(`wrapper_extraction_used: false`).

**3. Cohere normalization failure in canary v2 (unresolved).** In that same
`counterfactual_collector_canary_v2` run, Cohere (`command-r-plus-08-2024`,
reached through Cohere's OpenAI-compatible "compatibility" endpoint)
completed inference but failed normalization (`parse_status: parse_failed`,
`error_category: parse_failure`; see `normalized_judgments.jsonl` and
`request_ledger.jsonl` in that report). This is new -- the same provider,
same access path, and an equivalent short-content pair succeeded in canary
v1. Only a sha256 of the raw response was retained by design, so the exact
returned text was not available for inspection at the time this addendum
was first written, and the cause was not yet established.

**Canary v2 does not yet validate all four providers end-to-end.** It
validates: (a) the `lexical_prior_pool_v2` content-sufficiency fix on the
exact previously-failing query, and (b) the Vertex AI/Gemini fenced-JSON
fix. It does **not** validate Cohere normalization, which failed in this
same run for an as-yet-undiagnosed reason.

**4. Cohere normalization diagnosis (bounded live diagnostic, one Cohere
call).** Reconstructing canary v2's exact failing Cohere request
byte-for-byte (same query, pool, pair, presentation order, prompt, and
judgment schema; request_hash
`8075b96f1a6c8271d8e4fd56a272a2dcc412656599fc04440fef63447fa6f494`) and
reissuing it with response-shape introspection reproduced the *identical*
`raw_response_sha256` as the original canary-v2 failure -- fully
deterministic, not transient. The response was well-formed, unwrapped bare
JSON (`finish_reason: "stop"`, no markdown fence -- not a Vertex AI/Gemini-
style wrapping defect): Cohere put a `reason_code` value (`"unsupported"`)
into the `evidence_strength` field, which `validate_judgment` correctly
rejected. This is **malformed model output**, not a parser defect. A first
attempted fix (`response_format: {"type": "json_object"}`, JSON-syntax
enforcement only) produced the byte-identical response with the fix in
place, proving JSON-syntax enforcement alone does not address
schema-semantic errors.

**5. Compatibility-path schema-constrained confirmation also failed.** A
follow-up attempt sent Cohere's documented schema-constrained
`response_format` (`{"type": "json_object", "schema": <frozen schema>}`,
Cohere's compatibility-API convention) through the same OpenAI-compatible
endpoint. The confirmation call (request_hash
`a8d368d37bcc918a3684805e0869ce52fe53c39781419b4d44ec19ff57ee3df9`) still
returned a **byte-identical** `raw_response_sha256` to both prior calls --
strong evidence the compatibility endpoint was not enforcing the supplied
schema at all for this model, not merely producing different-but-still-
invalid output under stricter constraints. This implementation was
archived, not merged, at `archive/cohere-compat-schema-failed-20260727`
(commit `0646fde88a3d529ce4ebd4a4c2d5b6d3b21074a2`) -- it did not resolve
the failure and must not be presented as a working fix.

**6. Native Cohere ClientV2 transport (implemented, live confirmation
pending).** Because two calls through the OpenAI-compatibility endpoint
failed identically regardless of `response_format`, a genuinely different
transport was implemented: Cohere's own native Chat API v2
(`cohere.ClientV2(...).chat(...)`), which uses a different wire protocol
and a different `response_format` convention (`JsonObjectResponseFormatV2`,
whose schema field is named `json_schema`, not `schema`). Implementation:
`consistency_ranker.counterfactual_benchmark.cohere_native` (module
`cohere_native.py`), protocol identity `cohere_native_v2_json_schema_v1`
(constant `COHERE_NATIVE_V2_JSON_SCHEMA_PROTOCOL_VERSION`), never imports
`openai` and never references the compatibility endpoint. It loads the
frozen schema verbatim via the same `counterfactual_pilot.schema.load_json_schema()`
every other validation path uses, and fails closed (raises
`CohereNativeConfigError`) if asked to run against a different model ID or
a schema that does not match the frozen artifact. Content extraction is
strict: only `type: "text"` content blocks are ever treated as judgment
JSON; `thinking`, `citations`, and `tool_calls` blocks are recorded for
shape visibility but never concatenated into or parsed as judgment content.

**This transport is deliberately not wired into `dispatch.call_provider`
or the frozen `counterfactual_provider_panel_v1`.** Wiring it into the
collector's live-call path would silently change two existing collector
tests that inject a generic fake across all four providers uniformly, and
would risk an unintended real network call in test runs (the native path's
own client-construction activates when no fake is injected). It remains a
standalone, explicitly-invoked experimental path until independently
validated by a live confirmation call and a deliberate integration
decision.

**7. Native ClientV2 confirmation result: request rejected before any
judgment content was produced.** The bounded live confirmation call
(request_hash `d6ba44eb9fc254a2bdd9cbae2c3005f56e4c849f6b35788998031fb88c8338fe`
-- same query/pair/orientation/prompt as findings 4-6, distinct identity
via `transport_family=cohere_native_v2` +
`structured_output_protocol=cohere_native_v2_json_schema_v1`, confirmed
different from both archived compatibility-path hashes) returned a 400
Bad Request from Cohere's native API (`error_category: malformed_request`)
before generating any content -- unlike the compatibility-path failures,
this is not a judgment-validity failure at all; the native endpoint
rejected the request outright. The initial diagnostic capture
(`str(exc)[:500]`) truncated the exception to HTTP response headers only,
losing the actual rejection reason (Cohere's `ApiError.__str__` renders
headers before body); this has been fixed in `cohere_native.py`
(`_sanitized_error_message`, prioritizing `.body`/`.status_code`,
regression-tested) for any future attempt, but the fix could not be
re-verified live within this session's one-call ceiling. **Root cause is
therefore not established**: it may be an incompatible JSON Schema shape
(e.g. `$schema`/`$id`/`title`/`description` keys the compatibility
endpoint accepted but the native `json_schema` validator may not), a
message-format issue, or something else entirely.

**8. Deterministic Cohere-compatible schema projection implemented.**
Verified via a direct wire-serialization probe (SDK 6.1.0, `ClientV2.chat`)
that the native endpoint's `response_format` uses wire key `json_schema`
(not the compatibility endpoint's `schema`) -- ruling out a field-naming
mismatch as the cause of finding 7's 400. Enumerating the canonical
schema's JSON Schema keywords recursively found `minimum`/`maximum` on
`confidence` as the only keywords matching Cohere's documented list of
unsupported structured-output constraints (`$schema`/`$id`/`title`/
`description` are schema-identity metadata, not generation-time
constraints, and are not documented as unsupported).
`cohere_schema_projection.py` builds a deterministic, fully-recorded
projection of the canonical schema: `minimum`/`maximum` removed (recorded
as `{json_pointer, keyword, reason}` for each), everything else (enums,
`const`, `required`, `additionalProperties`, descriptions) preserved
verbatim. It fails closed (`UnclassifiedSchemaKeywordError`) on any
keyword not explicitly reviewed and classified as supported or
unsupported. The **canonical schema is never modified** --
`schemas/counterfactual_pairwise_judgment_v1.json` and its sha256
`f8332b7eadcbe92e1c4aed5299a0e3b1214c6d53a68aff3c826fe86147366de7` are
unchanged and re-verified at projection time; local
`validate_judgment` continues to enforce the full canonical contract,
including `confidence` in `[0, 1]`, regardless of what was sent to the
provider. `cohere_native.py` now sends the *projected* schema on the wire
while using the *canonical* schema for the fail-closed model/schema
identity check and for all local validation after the fact. Request
identity now includes `schema_projection_protocol:
cohere_native_v2_schema_projection_v1` plus both the canonical and
provider-schema hashes, so this request cannot collide with any prior
attempt's cache entry.

**9. Schema-projection confirmation result: `minimum`/`maximum` were not
the (sole) cause.** The bounded confirmation call (request_hash
`41f1de66736d8bb70410eefe0a59ad378b68fbc87c44bc00078fb71a5d19b302`; wire
schema confirmed free of `minimum`/`maximum` before sending) was rejected
again -- but this time the now-fixed error capture recovered the *actual*
API rejection reason for the first time:

```text
status_code=400 body={'id': '...', 'message':
  "invalid request: response_format validation: invalid 'json_schema'
   provided: unknown field '$id' in `object` type"}
```

Cohere's native `json_schema` validator rejects the schema-identity
keyword `$id` (present in the canonical schema as
`"$id": "counterfactual_pairwise_judgment_v1"`), which was preserved by
the projection (it was classified as passthrough metadata, not a
generation-time constraint, and finding 8 explicitly declined to strip
undocumented metadata keywords without evidence). **That evidence now
exists.** `$schema` is architecturally identical (same category of
schema-identity metadata) and is a reasonable suspect for the same
rejection, though unconfirmed -- only `$id` was named in the returned
error. No further call was made to test this, per the one-call ceiling.
A hash-provenance bug was also found and fixed during this pass: an
earlier version of `cohere_native.py` recorded a locally re-serialized
hash for `canonical_schema_sha256` instead of the well-known raw-file-bytes
value (`f8332b7e...`) used everywhere else in the repo -- fixed and
regression-tested; the persisted confirmation record for this specific
call predates the fix and shows the old (inconsistent but harmless)
value.

**10. `$id` removal implemented (protocol v2); `$schema` deliberately left
untouched.** `cohere_schema_projection.py`'s removal registry now has two
distinct categories: `UNSUPPORTED_CONSTRAINT_KEYWORDS`
(`minimum`/`maximum`, unchanged from v1) and the new
`UNSUPPORTED_SCHEMA_IDENTITY_METADATA_KEYWORDS` (`$id` only, added because
of finding 9's recovered evidence). `$schema` stays in the passthrough set
-- it is the same category of metadata and a reasonable suspect, but no
live rejection has named it, and stripping it now would be an unreviewed
guess, exactly what this module's fail-closed design exists to prevent.
This is a transformation-semantics change (not just a config tweak), and a
live call was already persisted under the old identity, so the projection
protocol was incremented:
`cohere_native_v2_schema_projection_v1` &rarr;
`cohere_native_v2_schema_projection_v2`
(`SCHEMA_PROJECTION_PROTOCOL_VERSION_V1` is kept as a named historical
reference, not deleted). New projection sha256:
`02870598a56c19838cb8eb8ca8ba5f9b864594cbf54e421e9d8ec8b548904917`.
Canonical schema sha256 unchanged and re-verified:
`f8332b7eadcbe92e1c4aed5299a0e3b1214c6d53a68aff3c826fe86147366de7`. The
resulting request identity was independently recomputed and confirmed
distinct from all four prior Cohere request hashes (json-object-only,
compat-schema, native-unprojected, and native-v1-projection) --
`be312ecf7ba089348ffa2e0a93d1e0f2155940f6721175d63f9de14e26aa6c78`.
53 offline tests pass (12 new/updated for this pass), full suite
1010 passed / 22 skipped / 0 failed, ruff/mypy/compileall clean.

**11. v2 ($id-removed) confirmation result: `$id` removal was necessary
but not sufficient -- a third, different field is now named.** The
bounded confirmation call (request_hash
`be312ecf7ba089348ffa2e0a93d1e0f2155940f6721175d63f9de14e26aa6c78`; wire
schema confirmed free of `$id`/`minimum`/`maximum` before sending) was
rejected a third time, but the error moved to a new field entirely:

```text
status_code=400 body={'id': '...', 'message':
  "invalid request: response_format validation: invalid 'json_schema'
   provided: error at 'properties.schema_version': missing required
   field 'type'"}
```

The canonical schema's `schema_version` property is
`{"const": "counterfactual_pairwise_judgment_v1"}` with no `type` key --
valid JSON Schema (a `const` value unambiguously implies its own type),
but Cohere's native `json_schema` validator requires `type` to be given
explicitly alongside `const`. Evidence persisted at
`reports/cohere_native_v2_schema_projection_v2_confirmation_20260728T010224Z/`
(sanitized, no headers/credentials).

**12. Missing `type` companion added (protocol v3).**
`cohere_schema_projection.py` now has a third, distinct transformation
category alongside the two removal categories: an *addition*. When a
property schema declares `const` without `type`, the projection adds
`type`, mechanically inferred from the Python type of the `const` value
itself (never a guess about Cohere's requirements -- it is a JSON-Schema-
faithful completion of information already implied by the existing,
reviewed `const` keyword). Today this fires only on
`schema_version` (`type: "string"` added). Recorded via a new
`AddedTypeAnnotation` provenance type, symmetric to `RemovedConstraint`
but for additions; `build_cohere_schema_projection` now returns a 4-tuple
`(projected, hash, removed, added)`. `$schema` remains untouched -- no
live rejection has named it. Protocol incremented again (a live call was
already persisted under v2's identity):
`cohere_native_v2_schema_projection_v2` &rarr;
`cohere_native_v2_schema_projection_v3`
(`SCHEMA_PROJECTION_PROTOCOL_VERSION_V1` and `..._V2` both kept as named
historical references). New projection sha256:
`d001a8a52fb72f5a0798e7468411348eed16516104ba00c7ba69aeb8bdcdba26`.
Canonical schema sha256 unchanged and re-verified:
`f8332b7eadcbe92e1c4aed5299a0e3b1214c6d53a68aff3c826fe86147366de7`. 59
offline tests pass for the two Cohere modules (9 new/updated for this
pass), ruff/mypy clean.

**13. v3 confirmation result: SUCCESS.** The fourth bounded confirmation
call (request_hash
`f062ea286398b73316c1dcbbc6a9868ab698491d47a6cd0d8041a43718d1e829`; wire
schema confirmed to have `$id`/`minimum`/`maximum` removed and
`schema_version.type` added before sending) was accepted by Cohere's
native `json_schema` validator: `finish_reason: "COMPLETE"`, 46 completion
tokens, 732 billable tokens total, latency 2.44s. The returned content
(`{"schema_version": "counterfactual_pairwise_judgment_v1", "preference":
"ABSTAIN", "confidence": 0.0, ...}`) parsed as JSON and **passed the full
canonical `validate_judgment` unchanged** -- the same strict schema used
for every other provider, not a relaxed or provider-specific check.
Evidence persisted at
`reports/cohere_native_v2_schema_projection_v3_confirmation_20260728T011703Z/`
(sanitized, no headers/credentials).

This is the first successful native Cohere structured-output judgment in
this investigation. It establishes that the *schema/transport* now works
end-to-end for `command-r-plus-08-2024`; it does **not** establish
judgment quality (a single ABSTAIN at temperature 0 on one pair is a
connectivity/schema signal, not a quality signal), and the native
transport is still **not wired into `dispatch.call_provider`/the frozen
collector** -- see the wiring plan below, which is a plan only, not yet
implemented.

**Status: COHERE NATIVE -- SCHEMA/TRANSPORT CONFIRMED WORKING (v3
projection); NOT YET WIRED INTO THE FROZEN COLLECTOR; NO FOUR-PROVIDER
CANARY RUN UNDER THIS PATH YET.** Do not claim Cohere is production-ready
for the frozen panel until the native transport is wired into the
collector (a deliberate, separate, reviewed change) and a clean
four-provider canary passes under it. Local schema validation remains
authoritative and unchanged throughout; nothing was repaired or coerced.
The bounded micro-pilot remains blocked until a clean canary passes.

## Native Cohere collector-wiring plan (not implemented)

This section is a plan only -- no collector/dispatch code has been
changed to route Cohere through the native transport. It exists so the
next authorized implementation pass has a concrete, reviewed starting
point rather than needing to re-derive one.

**Why this is nontrivial, not a one-line change:**

- `dispatch.call_provider(provider, model_id, prompt, temperature,
  max_tokens, call_fn=None)` is a single function serving all four
  providers through one shared code path: it calls
  `multi_provider_eval.providers._build_pairwise_config(provider, ...)`,
  which resolves each provider to an OpenAI-compatible `PairwiseConfig`
  (`family`, `base_url`, `api_key`, etc.) via `_provider_call_config`, then
  issues the call through the shared `call_fn`/`_call_llm` path. Cohere's
  entry in that config resolves to the OpenAI-compatibility base URL --
  the same path already confirmed broken (finding 5-7).
  `cohere_native.call_cohere_native` has a deliberately different
  signature (`chat_fn` instead of `call_fn`, a `judgment_schema`
  parameter, `NativeDispatchResult` instead of `DispatchResult`) and a
  different fail-closed model/schema identity check, and does not go
  through `_build_pairwise_config` at all. It returns a dataclass whose
  fields overlap enough with `DispatchResult` (`raw_text`↔`raw_response`,
  `prompt_tokens`, `completion_tokens`, `latency_seconds`,
  `error_category`, `error_message`) to make a thin adapter feasible, but
  it cannot be dropped into `call_provider`'s existing code path
  unchanged.
- `collector._resolve_live` calls `call_provider(...)` uniformly for every
  provider and reads a `DispatchResult`-shaped return. Routing Cohere to a
  structurally different function/return type means either (a) a
  provider-keyed dispatch table inside `_resolve_live` that special-cases
  `cohere` to call `call_cohere_native` and adapts `NativeDispatchResult`
  into whatever shape `_resolve_live` expects next (parsing/validation
  fields), or (b) making `call_cohere_native`'s result shape
  interface-compatible with `call_provider`'s and routing inside
  `dispatch.py` itself. Which is preferable is a design decision, not
  determined by this investigation.
- Request-hash/cache identity: the collector's existing request hash
  formula (used for `request.request_hash` / cache keys) was NOT built
  with `schema_projection_protocol` / `provider_schema_projection_hash` as
  fields -- those only exist in this investigation's standalone identity
  dict (`_native_identity_hash` in the test file / the ad hoc confirmation
  scripts). Wiring Cohere in means either extending the collector's
  production request-hash formula to include these fields for every
  provider (a schema/cache-format change affecting all 4 providers'
  request hashes, i.e. a new benchmark/collector protocol version) or
  finding another way to keep Cohere's cache entries distinguishable
  without changing the shared formula. This needs an explicit decision,
  not a silent default.
- Existing collector-level tests inject one generic fake `call_fn` across
  all 4 providers uniformly (see
  `test_other_providers_dispatch_still_use_openai_compatible_path` and
  similar collector tests) -- these assume every provider takes the same
  code path today. Wiring Cohere differently requires either updating
  those tests' assumptions or adding Cohere-specific test doubles, and
  re-auditing for any place that assumes uniform provider dispatch.
- The `native_cohere_ready()` readiness check is narrower than
  `dispatch.preflight_provider_ready("cohere")` (only checks
  `COHERE_API_KEY`, not `COHERE_BASE_URL`/`COHERE_MODEL`) -- the collector's
  pre-flight-all-providers check would need to call the right one for
  Cohere specifically, not the shared one.
- Canary/micro-pilot config files (`configs/counterfactual_*.json`)
  currently describe Cohere under the same `provider_panel` shape as the
  other three (OpenAI-compatible base URL etc.) -- if Cohere's config
  entry needs new fields (e.g. `transport: "cohere_native_v2"`), that is a
  config-schema change requiring `config.verify_frozen_contract` review,
  not just a code change.

**Recommended order of operations for the next implementation pass** (not
started):

1. Decide (b) vs (a) above -- most likely: keep `call_cohere_native`
   standalone and add a thin adapter inside `dispatch.py` that only
   activates for `provider == "cohere"`, converting `NativeDispatchResult`
   to whatever `_resolve_live` needs, so `collector.py` itself changes
   minimally.
2. Decide the request-hash/cache-identity question above explicitly
   (new collector protocol version vs. another mechanism) before touching
   `collector.py`.
3. Add the Cohere-specific readiness check into whatever pre-flight
   function the collector calls before a live run.
4. Update/extend the uniform-dispatch collector tests to reflect Cohere's
   distinct path, and add new tests specifically for the wired path
   (offline, fake `chat_fn`/`call_fn`, no network).
5. Only after 1-4 are implemented and offline-tested: run a `dry_run`
   collector pass (still zero live calls) to confirm the plan produces the
   expected requests, then request separate, explicit authorization for a
   clean four-provider canary.

This plan is deliberately not executed in this pass.
