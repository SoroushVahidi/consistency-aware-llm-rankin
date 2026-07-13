# REAL_LLM_INTEGRITY_FINAL_REPORT

Audit of every real-LLM (OpenAI/Azure/Cohere/Gemini) judgment source behind
the JDIQ manuscript, using only already-stored requests/responses/logs. No
API was called. See PROVENANCE.txt for exact data sources and worktree setup.

## Executive summary

The manuscript's headline mechanical-graph numbers for the "200-record
multi-provider corpus" (repair inactive in 62 `ms2` + 69 `ms1_drop_mutual`
records; 1 help + 1 harm in 69 `ms1` records) are **correct and independently
reproduced** by this audit directly from stored data (VALIDATION_CHECKS.md).
The problem is not those numbers -- it is that the manuscript's surrounding
prose and Table 5 attribute them to "Cohere/Azure pairwise judgments," when
the code that produced them never uses those judgments to build the graph
(PROVIDER_COUNT_RESOLUTION.md). Separately, this audit found and quantified
three real data-quality issues in the Cohere/Azure judgments themselves that
the manuscript does not currently discuss at all: a parser that silently
defaults ambiguous/malformed responses to `"A"` (PARSER_AUDIT.md), provider-
specific and statistically significant position bias (opposite-signed between
Cohere and Azure; POSITION_BIAS_REPORT.md), and substantial forward/reverse
order-sensitivity (fair-to-substantial agreement only; FORWARD_REVERSE_REPORT.md).
None of these three issues affect any currently-published number, because
none of the currently-published real-LLM repair/cyclicity numbers are
computed from these judgments -- but they would need to be resolved before
any *future* revision uses this corpus's judgments as primary graph-
construction evidence, and the manuscript should say so rather than imply the
question is already settled.

## Provider inventory

Full detail: REAL_LLM_FILE_INVENTORY.md. Highlights: the primary OpenAI
pairwise pilot (scidocs 50 / hotpotqa 20 / fiqa 10-of-20-usable queries) is
committed and citable but has no preserved raw response text, so it cannot be
re-audited at the response level. The Cohere/Azure "200 query-regime" corpus
exists only as uncommitted local data (not on origin/main) and does have
54.6% raw-text coverage. An earliest version of this corpus
(`reports/failure_mining_llm/`) includes a fourth, `cloudrift`/Qwen-family
provider never mentioned in the manuscript -- harmless (that version is
superseded), but flagged per the inventory instruction to verify provider
identity from data, not filenames.

## Provider-count resolution

**Resolved as a genuine contradiction in framing, not in the numbers.** See
PROVIDER_COUNT_RESOLUTION.md for the full code-level trace. Short version:
Cohere and Azure each independently cover all 200 query-regime slots; neither
contributes to the graph/cyclicity/repair statistics the manuscript quotes
for that corpus, which are 100% mechanical.

## Parser audit

The shared `_parse_winner()` silently defaults every ambiguous or malformed
response to `"A"`, with no distinguishing signal preserved in stored output
(the `parse_error` field meant to flag this is dead code -- it can never
fire). The `debias_position=True` combination rule used for Cohere/Azure has
its own, structurally identical default: on forward/reverse disagreement, it
silently favors the first-shown document rather than abstaining. Neither
default is currently disclosed in the manuscript.

## Ambiguity statistics

1.1% of the 12,020 raw responses with preserved text triggered the parser's
default (0% on FiQA for both providers; up to 3.8% on HotpotQA for Cohere).
Zero retries occurred anywhere in the corpus. Full breakdown:
RESPONSE_QUALITY_REPORT.md.

## Position bias

Every provider/dataset group shows statistically significant position bias
among **unambiguous, exact** responses (p < 0.01 throughout) -- and Cohere and
Azure are biased in **opposite directions** (Cohere: 61-70% toward the
second-shown document; Azure: 53-58% toward the first-shown document).
Pooling the two providers, as the manuscript's prose currently does, nearly
cancels this out and hides both effects. POSITION_BIAS_REPORT.md.

## Forward/reverse agreement

Even restricted to individually well-formed responses, forward and reverse
presentations of the same pair agree only 59-85% of the time depending on
provider/dataset (Cohen's kappa 0.27-0.71: fair to substantial, never
"almost perfect"). This is a larger source of unreliable signal than
ambiguous/malformed responses. FORWARD_REVERSE_REPORT.md.

## Policy sensitivity

For a preference graph built directly from these judgments (a new analysis
this audit performed; not the manuscript's existing mechanical graph),
alternative parsing policies change conclusions substantially: cyclicity
falls by 91-100% once fallback-defaulted and disagreement-defaulted edges are
removed, and every non-zero help/harm case found under the current parser
(P0) disappears under the three stricter policies (P1/P2/P3). The
manuscript's *actual, currently-published* repair/cyclicity numbers are
unaffected by any of this, because they don't use these judgments.
POLICY_SENSITIVITY_REPORT.md, CYCLICITY_SOURCE_AUDIT.md.

## Manuscript corrections required

See MANUSCRIPT_PATCH_RECOMMENDATIONS.md for exact replacement wording
(Section 4.8, Table 5, a new parser-description sentence, a new order-bias
disclosure, Section 8, Limitations, Data Availability). Summary classification:

| Issue | Classification |
|---|---|
| Section 8's 62/69/69/help/harm numbers themselves | **resolved** (independently reproduced, correct as stated) |
| Section 4.8/Table 5 attributing the 200-record repair/cyclicity result to Cohere/Azure judgments | **changes numerical [framing]; does not change any number, but is presently misleading about what was measured -- correct before further drafting** |
| Missing parser-default disclosure | **harmless but document** |
| Missing position-bias measurement/disclosure | **harmless but document** (no current claim depends on it) |
| Missing forward/reverse-agreement disclosure | **harmless but document** |
| 4th provider (`cloudrift`) in superseded v1 corpus, absent from manuscript | **harmless but document** (superseded version, not cited) |
| OpenAI primary pilot has no re-auditable raw text | **harmless but document**; if full response-level reproducibility is later required, this is a **requires new experiments** item (a re-run with logging enabled), not something fixable from stored data |
| Whether alternative parsing changes the manuscript's headline conclusion | **resolved: no**, because the headline numbers don't use these judgments at all |

## Is any new API call scientifically necessary?

**No, not to fix any of the above.** Every issue found is resolvable by
patching the manuscript's prose to correctly describe what the stored
pipeline already computed. A new API call would only be needed if a future
revision wants to (a) obtain raw-text-auditable data for the OpenAI primary
pilot, or (b) actually build and report a Cohere/Azure-judgment-derived
repair/cyclicity result as primary evidence (as opposed to the auxiliary
ranking-comparison role it currently plays) -- and even then, only after
first deciding how to handle the position-bias and forward/reverse-
disagreement issues documented here (e.g., adopt an abstain-on-disagreement
policy resembling P1 rather than the current default-to-first-shown-document
rule).
