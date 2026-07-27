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
