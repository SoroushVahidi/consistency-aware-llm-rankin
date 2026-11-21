# Prospective opportunity audit v1 — frozen before inference

Classification: preregistered prospective exploratory external-validity study;
not canonical manuscript evidence. This is an internal timestamped/hashed
preregistration, not registration in an external registry. Authority/base:
`2c69f331fa4add10ce577c17516afb997b630dfe`. No historical outcomes, manuscript
files, model caches, or unrelated processes may be overwritten.

## Questions and estimands

RQ1: On a fresh, independently selected query roster, where do graph repair,
ranking response, and measured relevance response cease to propagate?
RQ2: Conditional on a changed ranking, how often does measured nDCG improve,
worsen, or remain unchanged, and how do positive-pool and grade-profile classes
explain zeros? RQ3: How do descriptive compositions vary by dataset and by
natural versus explicitly relevance-enriched diagnostic candidate pools?
Historical selected-cache frequencies are context, never prospective targets.

The primary endpoint is the greedy-versus-unrepaired Copeland outcome
decomposition in the **natural BM25 pool**: no structural intervention;
intervention with unchanged ranking; changed ranking/no positive in pool;
changed ranking/positive pool/equal top-ten grade profile; changed profile but
zero measured delta; improved utility; harmed utility. Also report the direct
gain/zero/harm distribution conditional on ranking change, with its actual
denominator. The first two classes are reported regardless of label content.
Report all sampled queries and cyclic-positive/non-cyclic/zero-positive
opportunity classes separately. Exact repair repeats this decomposition as a
secondary endpoint; non-proven exact results are missing, not greedy substitutes.

The two prespecified efficacy contrasts are natural-pool query-level mean
nDCG@10 differences: greedy minus unrepaired and exact minus unrepaired. They
are secondary to the descriptive endpoint. Enriched-pool, dataset-specific,
forward-only, reverse-only, and pool-normalized results are descriptive only.
No outcome, including a zero, is predetermined. No repair selector is trained.

## Sampling, sample size, and candidates

Seed: 2026102607. Exclude historical dataset/query IDs from the preserved
historical exclusion manifest, selected-cache numeric identity records, and
frozen rosters of the previous prospective and candidate-intervention runs.
Also exclude historical untyped IDs conservatively and duplicate normalized
query texts across the current development/evaluation sets. Log every exclusion
source and identity hash; do not inspect historical raw responses.

Eligible universes: nonempty FiQA and SciDocs queries having official **test**
qrels, and BRIGHT earth_science/economics examples with nonempty gold IDs.
Use query-ID-only projection of test qrels for eligibility before selection;
no relevance values or retrieval utility used to choose query identities.
BRIGHT historical biology is not silently extended or pooled as its old cohort.
Choose hash-ordered disjoint development/evaluation IDs: development 4 FiQA,
4 SciDocs, 2 earth_science, 2 economics; evaluation 130 FiQA, 130 SciDocs,
65 earth_science, 65 economics. If insufficient eligible queries, fail without
replacement or unregistered quota changes. Freeze ID/text hashes before
loading grade values or building candidate pools. Interleave datasets in a
fixed order to make resource-censored prefixes explicit.

For n=390 a worst-case binomial proportion has approximate 95% half-width
1.96*sqrt(.25/390)=.0496 (Wilson slightly narrower). The equal-dataset mixture
is the target, not deployment prevalence. At n=130 per dataset, worst-case
half-width is about .086; subgroup and conditional-ranking-change denominators
may be much smaller. This is a precision design for **all-query rates**, not
a power/equivalence guarantee or a promise of 5% conditional precision. No
adaptive enlargement based on gains, cyclicity, or observed conditional n.

Reuse repository BM25Ranker, k1=1.5, b=.75, ASCII lexical tokenization and
document-ID ties, over the entire official short-document corpus. BRIGHT
official excluded_ids are removed **before** candidate selection; gold-answer,
reasoning, and long-document gold fields never enter prompts.
Natural pool: first 12 BM25 documents without label enrichment. Diagnostic
pool: first ten natural candidates plus up to two hash-selected official
positive documents not already in the first ten; fill any shortfall from
natural BM25 order. This intentionally label-informed diagnostic pool is
reported separately and is never portrayed as natural retrieval. Query roster
is fixed first. All candidate IDs, scores, corpus/qrel hashes, exclusions,
and exact text are frozen privately before model use. No retrieval utility is
computed during preparation or development. No query is dropped for lacking
positive candidates or cyclicity. All official qrels define full-query IDCG.

## Model, prompt, and presentation

One model: Qwen/Qwen2.5-7B-Instruct, immutable revision
`a09a35458c702b33eeacc393d103063234e8bc28`, complete cached BF16 weights.
Verify official public metadata/license (Apache-2.0) and hashes for every
weight/tokenizer/config file against official LFS identities where available.
This 2024 family is not a modern frontier panel; no model heterogeneity claim
is supported by a single model. No paid API, cloud purchase, training,
quantization, remote trust-code, model substitution, or serving endpoint.

Exact system/user strings and parser are in common.py and frozen by source
hash. The task is binary **relative usefulness**, including imperfect pairs;
it is not a claim that either passage is truly relevant. There is no forced
token constraint. Explicit spontaneous ties/refusals are recorded as
abstentions; abstention rate under this forced-choice instruction is not
comparable to a schema inviting abstention. Other non-exact outputs and caps
are invalid; never default A or repair malformed output.

Query first 128 tokenizer tokens, each document first 256 tokens; preserve
exact retained-token counts and input-token hashes. Maximum chat input 1024
tokens; an over-limit request is an error, not silent further truncation.
Greedy decoding, do_sample=False, max_new_tokens=4, use_cache=True; fixed
torch/NumPy/Python seeds, BF16, SDPA, batch size one. Record actual package,
CUDA/device, generation/tokenizer/template identities. No thinking mode.
Deterministic algorithms enabled; fresh repeat forward passes test actual
repeatability, rather than assuming it. No random generation or hidden retries.

Collect both A/B and B/A presentations of every distinct unordered pair needed
by either pool. Shared pairs are reused only when exact query/document/token
content and model/prompt parameters match. Pair order is seeded hash order;
both orientations are retained. Document-ID sorting only defines pair identity.
There are at most 87 unique pairs/query (66+66-45); at most 67,860 main
responses. No cross-pairs unused by either pool are collected.

## Development gate — thresholds fixed before responses

Twelve disjoint development queries, four hash-selected real candidate pairs
each: 48 pairs. Obtain both orientations under two fixed paraphrases (192
responses), fresh repeats of the first pair per query (24), and 12 explicitly
synthetic, unambiguous semantic-control pairs in both orientations (24):
240 development responses. Controls test content sensitivity only and never
enter scientific graphs or evidence counts. Controls are fixed in prepare.py.
The primary prompt is preselected; the robustness prompt cannot be promoted
based on better outcomes. Both are tested; failure stops this v1 campaign.

Gate requires, separately for each real-pair prompt: valid directional
fraction >=98%, abstention <=10%, displayed-A share in [40%,60%], actual-document
reversal agreement >=80% among both-directional pairs, corroborated directional
pairs >=75% of planned pairs. Require >=95% exact fresh-repeat agreement,
>=85% actual-document winner agreement between prompt variants over all 96
orientation cases (missing counts against), and >=90% semantic-control accuracy
on each orientation. Peak allocated GPU memory <=96% total. Extrapolated
collection plus a 1-hour analysis reserve must fit a 12-hour total budget;
latency uses the more conservative of mean and p90 per-response time with
1.5x allowance. Required free disk >=25 GiB, no unrelated GPU compute PID,
and minimum runtime free host RAM 24 GiB. Failure preserves diagnostics and
does not run evaluation responses. Report Wilson intervals and denominators;
thresholds are finite engineering screens, not proven population guarantees.
Reversal thresholds restrict contradictory evidence; content controls and
prompt/repeat checks reject a parser-valid, order-driven or insensitive judge.
Twelve queries still give limited reliability-generalization precision.

No development retrieval-utility calculations or final-evaluation prompt
tuning. No automatic second model or revised-prompt attempt if this gate fails.

## Graphs, repairs, and measurement

Primary strict-agreement graph: both orientations valid and selecting the
same actual document -> winner-to-loser edge, unit weight. Conflict,
abstention, invalid or missing orientation -> no edge; retain every candidate
as a node. Record each disposition. Repeats and robustness controls never
vote. Preserve edge/node sorted insertion, existing greedy_fas, existing
Copeland degree score/document-ID tie rule, and PySCIPOpt 6.2.1 _solve_scip
with zero MIP gap and ten-second limit. Require proven optimality/trivial DAG.
Save original/repaired edges, deletions, solver status/gap/objective, orders,
degree/profile changes and timings. Acyclicity does not imply Copeland respects
every edge. Exact chosen optima are solver-specific; no all-optima envelope or
prevalence claim. Secondary forward-only/reverse-only graph sensitivities
use their recorded orientations on identical pools, never a pooled new model.

Reuse ndcg_at_k, k=10, gain 2^grade-1, log2(rank+1), full official-query IDCG;
IDCG zero -> numeric zero explicitly flagged. Also give pool-conditioned
nDCG@10, top-ten grade vectors, judged/positive counts and relevance-opportunity
classes. Unjudged means gain zero for this evaluation, not proven irrelevance.
Grade-prefix equality is sufficient, not necessary, for a zero delta.
Delta tolerance 1e-12. Keep all gains and harms; no qrel-based selection of
repair, extractor, prompt, candidate-pool condition, or solver solution.

## Statistics and missingness

Independent unit is dataset/query, not orientation, pair, branch, pool, or
configuration. Report planned/collected/valid/complete counts at each level.
Primary counts include all 390 roster slots, with incomplete acquisition
explicitly missing rather than silently absent or zero. A response-invalid
but fully attempted query is evaluable under the declared no-edge rule, with
reliability dispositions exposed. Infrastructure-incomplete queries are not
evaluated as complete graphs. Missing qrels/absent gold-document identities
halt preparation rather than invent labels or resample queries.

Report all-query class rates and conditional gain/zero/harm rates with actual
denominators. Use within-dataset query bootstrap (10,000 draws, seed fixed),
recomputing ratios for conditional frequencies. Save denominators and empty
conditional resample counts; do not report a degenerate interval as reliable.
Wilson intervals for binomial displays are descriptive; paired branches are
never independent replications. Report per-dataset descriptive counts.

For exactly two natural-pool mean-nDCG contrasts, preserve query-paired
differences and zeros, equal query weights in the prespecified dataset mix;
within-dataset bootstrap pointwise 95% intervals and whole-query sign flips
(exact <=16 nonzero differences, otherwise 10,000 Monte Carlo, plus-one
correction). Holm alpha=.05 over the fixed two slots, unavailable contrast
p=1. No global error claim for all summaries. Sign-flip symmetry/exchangeability
is an assumption, not randomized treatment assignment; report skew/nonzero n.
Do not infer equivalence from absent significance. Complete-case effects must
show intended and matched n; diagnostic/conditional samples do not become
population causal evidence. No powered model/provider comparisons.

## Resources, checkpointing, and stopping

Preferred host is the idle local RTX 5060 Ti, one GPU, two CPU threads,
24-GiB host-memory budget target (hard process address-space limits are not
used with CUDA); CPU evaluator at most two threads. No other process may be
terminated or existing environment modified. Wulver ikoutis/debug_gpu is an
audited alternative, not an automatic second allocation. No simultaneous
local/HPC campaigns. No new downloads of model weights are planned.

Limits: 12 cumulative active wall-hours including development/model load,
collection, and 1-hour reserved CPU analysis; <=30 GiB new disk footprint;
<=67,860 main responses +240 development responses, plus at most 16 explicit
resume reissues of interrupted in-flight infrastructure attempts. Actual
planned calls are frozen from the roster/pool union. Scientific invalidity or
abstention is never retried. SQLite WAL/FULL commits every response/attempt;
atomic progress every response and atomic per-query evaluation. Session time
charged before each inference using a persistent ledger. After a hard crash,
the elapsed interval since its last heartbeat is conservatively charged on
explicit resume. Completed records immutable. Lock run and GPU cooperatively;
refuse incompatible manifest, changed code/model/input hashes, failed gate,
duplicate worker, or exhausted attempt/time/disk budget. No automatic requeue.

Main reliability surveillance is label-blind: after >=100 responses, halt on
>5% invalid/capped or >20% abstentions; after >=30 paired comparisons halt on
<60% corroborated directional pairs. The evaluation roster never changes.
Stop for unrelated GPU activity, OOM, invalid input, checkpoint failure,
insufficient disk, or resource cap. No stopping based on utility, gains,
cyclicity, significance, or conditional denominator. Partial rosters are
explicitly incomplete, never substitutes for the full sample.

Launch only after the gate and frozen identity checks pass. Persistent tmux
with an outer timeout, logs, launch receipt and exit sentinel. Observe startup
and about two minutes of main progress, then leave it running; do not wait
for completion. Raw text, prompts, responses, SQLite, qrels and per-query
results remain private outside Git. Draft PR contains implementation/protocol
and sanitized verification only. No manuscript insertion, merge, publication,
or journal submission is authorized.
