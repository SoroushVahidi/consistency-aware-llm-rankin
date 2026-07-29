# Project Status

*Canonical entry point for humans and agents. If this document and any other document
disagree about current state, re-verify Git/code directly (see "Last verified state")
rather than trusting either document blindly.*

## Status snapshot

| Field | Value |
|---|---|
| Generated | 2026-07-28T22:15:00Z (code state); documentation committed slightly later — see note below |
| Branch | `fix/outcome-f-production-operating-point` |
| `documented_code_head` | `cd678f02cec725496c484757146d44649ac0d034` |
| origin/main | `3e02b73666506f3eb894f5df2c531284ea31a60e` |
| Ahead / behind (of `documented_code_head`) | 28 ahead / 0 behind |
| Working tree | Clean of source/config/test changes at write time (see "Last verified state"). |
| Current phase | **Consistency-aware active-acquisition / regularized-aggregation / stopping-rule pivot — three real-oracle pilots complete.** See "Consistency-aware pivot" section below. The multi-provider counterfactual-benchmark engineering work described later in this document (Cohere transport wiring, provider panel, micro-pilot) is still real and unresolved, but is **not** the branch's current focus; it was paused mid-stream when the branch pivoted, not abandoned or superseded. |
| Current blocker | None blocking for the pivot itself (all three pilots ran to completion, offline, no live calls). For the still-paused counterfactual-benchmark work: native Cohere `ClientV2` transport (`cohere_native.py` + `cohere_schema_projection.py`, schema projection v3) is confirmed working live but not yet wired into `dispatch.call_provider`/the frozen collector — unchanged since the last update to this section. |
| Exact next action | See "Exact next action" section at the end of this document. |

**Note on `documented_code_head`:** this snapshot describes the scientific
and code state immediately *before* this documentation-only commit. A
committed status document cannot reliably contain the hash of the commit
that contains itself — the actual documentation-commit hash is reported
separately by whichever agent creates it. **Always re-run the Git-state
commands below before trusting any hash in this document**; do not assume
`documented_code_head` remains the branch tip.

## Documentation authority map

The repository accumulates status/evidence documents faster than they can
all be kept current. This map states which single file is authoritative
for each concern — consult it before trusting any other document that
claims to describe the same thing.

| Concern | Authoritative file | Notes |
|---|---|---|
| Repository/branch state, current blockers, next action | This file (`PROJECT_STATUS.md`, repo root) | Re-verify against Git directly per the note above |
| Branch-specific history and exact continuation point | `docs/handoff/CURRENT_BRANCH_HANDOFF.md` | Companion to this file; branch-scoped |
| Machine-readable snapshot | `docs/handoff/state_snapshot.json` | Same scope as the handoff doc, structured for tooling |
| Scientific claims actually being made | `papers/JDIQ_2026/manuscript/main.tex` | The submitted manuscript source — not any `docs/*CLAIMS*.md` file |
| Evidence-to-claim mapping | `papers/JDIQ_2026/SECTION_EVIDENCE_MAP.csv`, `papers/JDIQ_2026/MASTER_EVIDENCE_INVENTORY.csv` | Correctly distinguishes canonical (`outputs/pub_vote_cmp_all4/`) from stale/`do_not_use` (`outputs/pub_vote_cmp_v2/`, `outputs/q1_journal_package/`) packages |
| Manuscript status (readiness, drafting) | `papers/JDIQ_2026/CANONICAL_PAPER_STORY.md`, `papers/JDIQ_2026/CONTRIBUTION_AUDIT.md` | **Not** `papers/JDIQ_2026/PROJECT_STATUS_SUPERSEDED_20260712.md` (renamed 2026-07-28 from `PROJECT_STATUS.md` — it described 22%-readiness pre-writing state and is obsolete now the manuscript is a complete draft) |
| Protocol freezes (counterfactual benchmark) | `docs/benchmarks/COUNTERFACTUAL_PILOT_FREEZE_V1.md` | Frozen protocol identifiers and the Cohere investigation narrative |
| Preserve-vs-repair research trajectory (revised direction for the mature graph-repair program; now concluded NO-GO) | `docs/research/RESEARCH_TRAJECTORY.md` | Narrative; see also `EXPERIMENT_ROADMAP.md`, `NOVELTY_AND_RELATED_WORK.md`, `DECISION_LOG.md` (entry D6 = final decision), `REPRODUCIBILITY_AND_ARTIFACTS.md`, `MANUSCRIPT_SUMMARY.md` in the same `docs/research/` directory, and `configs/preserve_repair_experiment_spec_v1.json` for the machine-readable spec |
| Negative-result manuscript package (formalizes the NO-GO finding for external publication) | `papers/negative_result_2026/MANUSCRIPT_PLAN.md` | Companion paper to `papers/JDIQ_2026/`, not a revision of it; see also `CLAIMS_AND_EVIDENCE.md`, `RELATED_WORK_POSITIONING.md`, `FIGURE_AND_TABLE_PLAN.md`, `LIMITATIONS.md`, `ABSTRACT_DRAFTS.md`, `OUTLINE.md` in the same directory |
| Historical/superseded records | `docs/historical/`, and any file carrying a `SUPERSEDED` banner (e.g. `docs/THREATS_TO_VALIDITY.md`, `docs/RESULTS_AUDIT.md`, `docs/RESULTS_FOR_PAPER.md`, `docs/EVIDENCE_MAP.md`, `docs/SAFE_CLAIMS_FOR_PAPER.md`, `docs/revision_strategy.md`, `docs/Q1_POSITIONING_AND_CLAIMS.md`) | Kept for provenance; banner states the current replacement |

If a document is not listed here and is not explicitly marked historical,
treat its claims as unverified until cross-checked against the
authoritative file for that concern.

## Repository purpose

This repository now spans three research threads sharing one codebase
(this list itself was stale until 2026-07-28 — it previously said "two,"
omitting the pivot below; corrected here rather than left inconsistent
with the rest of this document):

1. **Mature program (publication-ready, submitted with a revised research
   question):** preference-graph construction and repair for retrieval
   ranking, using Minimum Weighted Feedback Arc Set (MWFAS) optimization to
   resolve cyclic pairwise preferences. Subject of the JDIQ 2026 manuscript
   (`papers/JDIQ_2026/`), which reaches a settled negative/conditional
   result (repair improves structure, not retrieval quality reliably). As
   of 2026-07-28 this program has an actively-documented **revised
   direction** — see "Preserve-vs-repair research trajectory" below — that
   is a continuation of this program, not a separate one.
2. **Counterfactual benchmark (paused, not abandoned):** a real,
   qrels-grounded, multi-provider LLM-judge counterfactual benchmark —
   engineering/canary stage, not yet executed at benchmark scale. See
   "Consistency-aware pivot" below for why this is currently paused.
3. **Consistency-aware active-acquisition / regularized-aggregation /
   stopping-rule pivot (current branch focus):** see "Consistency-aware
   pivot" section below. Independent of program 1's revised direction —
   they share only a general theme (sparse/inconsistent LLM preference
   evidence), not code or data.

## Preserve-vs-repair research trajectory (2026-07-28) — revised direction for the mature program

The JDIQ manuscript's settled null result (program 1 above: repair does
not reliably move nDCG in aggregate, robustly, including under exact
repair) motivated a narrower follow-on question: can a query's pre-repair
graph properties predict whether repair will help or harm *that specific
query*, even though the aggregate effect is null? Full narrative,
evidence, and staged plan: `docs/research/RESEARCH_TRAJECTORY.md` (start
here — includes a 2026-07-28 status update pointing at the answer below),
`docs/research/EXPERIMENT_ROADMAP.md`, `docs/research/NOVELTY_AND_RELATED_WORK.md`,
`docs/research/DECISION_LOG.md` (see entry D6),
`docs/research/REPRODUCIBILITY_AND_ARTIFACTS.md`,
`docs/research/MANUSCRIPT_SUMMARY.md`.

**Status as of this entry: answered — NO-GO.** A small-scale Gate-0 pass
(`reports/oracle_headroom_gate0_20260728T230000Z/`, 4 dataset slices) found
no slice cleared the pre-registered threshold. A follow-up
**repository-scale meta-analysis**
(`reports/repository_scale_headroom_analysis/`, 122,203 rows unified from
76 already-existing per-query source files, 419 distinct queries across
all 4 datasets) widened this far beyond Phase 1's plan and reached a firm
conclusion: oracle headroom is real (query-level 95% CI [0.0020, 0.0030])
but **~8x smaller** than the manuscript's own Holm-adjusted 80%-power
minimum-detectable-effect (0.0207) — the ceiling on what any predictive
model could achieve is below this project's own noise floor. Every
available pre-repair covariate shows negligible univariate association
with the effect. **Recommendation: stop the whole-graph, aggregate-metric
preserve-vs-repair predictive-model direction** — see
`reports/repository_scale_headroom_analysis/research_decision.md` for the
full reasoning. No predictive model was ever trained in this line of work;
none should be described as working or planned going forward for this
formulation. A component/edge-level reformulation remains a distinct,
ungated, unevaluated question (not a continuation of this one).

This is important context for **three prior, informal, independent
attempts** at closely related questions already in this repository,
surfaced honestly rather than left buried:
`outputs/learned_selector/LEARNED_SELECTOR_REPORT.md` (fixed threshold
beat learned models), `experiments/failure_class_audit_20260711_212157/phase_reports/FAILURE_PATTERN_PREDICTION_REPORT.md`
(high ROC-AUC, low PR-AUC — inconclusive), and
`src/consistency_ranker/repair_selector_mining/` (a considerably more
rigorous pipeline, built in the JDIQ era, **never executed** — confirmed
by `papers/JDIQ_2026/CONTRIBUTION_AUDIT.md` line 40). The revised
direction's contribution is turning this pattern of ad hoc attempts into
one pre-registered, properly-gated, negative-control-tested protocol — see
the trajectory doc §2 for the full accounting.

## Scientific questions

Mature program:
- How often do pairwise preference graphs form cycles under different vote
  constructions?
- Can MWFAS-based graph repair resolve these inconsistencies?
- Does repaired-graph ranking improve retrieval quality vs. baselines?
- Does vote construction mediate the repair effect?

Active program (target, not yet achieved):
- For a real IR query, candidate pool, and budget: which acquisition policy
  and which provider/model judge should be jointly selected under cost,
  reliability, and safety constraints — evaluated against qrels, not against
  another LLM's opinion.

## Validated current contributions

**[VALIDATED]** Mature preference-graph program (see `README.md`,
`docs/EVIDENCE_MAP.md`, `outputs/pub_vote_cmp_all4/paper_package/`):

1. Preference graphs are **derived data artifacts**, not objective inputs —
   they depend on how votes are constructed.
2. Normalization, vote construction, thresholds, graph regime, and
   candidate-pool construction materially affect graph topology and repair
   activity.
3. Raw heterogeneous retriever score scales can create artificial
   edge-weight dominance (motivating normalized vote construction).
4. Structural graph repair (greedy FAS; exact open-source SCIP ILP) removes
   cycles and reduces feedback-arc mass — this part reliably works.
5. **Structural improvement does not imply a robust retrieval-quality
   improvement.** This is the central conditional/negative result.
6. Exact ILP repair does not rescue the downstream retrieval-quality
   conclusion relative to greedy repair.
7. The repair effect can disappear at any of several stages: no repair
   activation; edge changes without ranking changes; ranking changes without
   metric changes; or qrels-relevant changes that do move retrieval metrics
   (sometimes negatively).
8. Overall: a rigorous negative/conditional result about when structural
   graph repair helps retrieval, not a universal retrieval-improvement
   claim.

**[ENGINEERING COMPLETE]** Active-program infrastructure (this branch):
- Provider capability audit: all four provider APIs (Azure, Cohere,
  Fireworks, Vertex AI/Gemini) authenticate and respond live; structured-
  output instrumentation exercised. **Connectivity only — not ranking-
  quality evidence.**
- Frozen provider panel (`counterfactual_provider_panel_v1`), frozen prompt
  (`counterfactual_pairwise_judge_v1`), frozen judgment schema
  (`counterfactual_pairwise_judgment_v1`).
- Fail-closed collector (`counterfactual_benchmark/collector.py`): exactly
  one of dry-run / cache-only / live-with-caps; no provider fallback; every
  request identity-hashed; resume never repeats a completed call.
- `lexical_prior_pool_v2` + `document_validity_v2`: eliminated a measured
  short-document/title-only selection bias (v1: 17/80 candidates and 16/64
  pairs title-only across the 8 frozen queries; v2: 0/80 and 0/64).
- Vertex AI (`gemini-2.5-flash`) fenced-JSON response normalization fix,
  confirmed live in `counterfactual_collector_canary_v2`.
- Azure and Fireworks: reliable bare-JSON normalization, confirmed across
  both canaries.

## Important negative results

**[NEGATIVE RESULT]** Outcome F policy-selection (synthetic, canonical
evidence `reports/policy_selection_20260726T030500Z/`, committed):
- An **oracle** query-specific policy selector beats always-UHT on
  corrected utility on held-out burial-heavy regimes (oracle
  U_corr = 0.1708 vs. always-UHT U_corr = −0.0257).
- **No** learned/hard/calibrated/selective/soft/staged/contextual gate beat
  always-UHT. `selective_three_way` was *worse* than always-UHT
  (U_corr = −0.1121).
- Decision rule **Outcome F** fired: query-level selection is valuable in
  principle, but no current gate realizes it. Production was changed to
  **fail closed to always-UHT** with a lightweight, non-routing safety floor
  (`src/consistency_ranker/policy_selection/production_config.py`,
  frozen by commit `3614333`).
- Learned routing remains experimental. The selector is **not** currently a
  successful scientific contribution.

**[NEGATIVE RESULT]** Corrected multifactor production-UHT evaluation
(`docs/MULTIFACTOR_PRODUCTION_UHT_EVAL_INVALIDATION.md`,
`docs/multifactor_production_uht_corrected_summary_20260727.json`,
committed):
- An earlier evaluation (`reports/real_query_multifactor_acquisition_20260726T044254Z/`,
  local-only, **invalid, do not cite**) scored `production_uht` against its
  own prior instead of qrels, and recorded execution config without
  confirming actual safeguard execution.
- Corrected offline replay (zero paid API calls; cache-only re-score of
  already-collected live judgments) replaced full-pool top-k Jaccard
  (structurally `≡ 1.0` and uninformative whenever `k == pool_size`) with
  `prior_kendall_tau`, and separated safeguard *eligibility* from actual
  *execution* (`outsider_probe_executed_rate = 0.0` across all 720
  `production_uht` rows — the probe was never eligible, not silently
  skipped).
- **Verdict:** `NO MATCHED-BUDGET QUALITY WIN ESTABLISHED — COST-ONLY
  UTILITY SIGNALS PRESENT`. Do not read this as a positive nDCG result for
  any non-baseline policy.

**[NEGATIVE RESULT]** Cohere structured-output enforcement (this session;
see `docs/benchmarks/COUNTERFACTUAL_PILOT_FREEZE_V1.md` findings 4-5):
- Canary-v1's Cohere cell abstained correctly on a genuinely content-poor
  (title-only) pair. Canary-v2 (after the pool fix) revealed a *new*,
  unrelated Cohere failure: syntactically valid bare JSON with a
  `reason_code` value leaked into `evidence_strength`
  (`"unsupported"`) — correctly rejected by strict local validation.
- Two bounded live diagnostic/confirmation calls were made (the maximum
  authorized): first with `response_format: {"type": "json_object"}`
  (JSON-syntax enforcement only), then with the full frozen JSON Schema
  (`response_format: {"type": "json_object", "schema": ...}`, Cohere's own
  documented compatibility-API convention). **Both calls returned
  byte-identical output** (`raw_response_sha256` unchanged across all
  three: original canary, first diagnostic, and schema-constrained
  confirmation). This is strong evidence Cohere's compatibility endpoint is
  not enforcing the supplied schema for this model, not merely that the
  model is noisy.
- **The compatibility-path implementation is unsupported** for the frozen
  4-provider panel under this model/access path. It is preserved for
  diagnosis only on the local archive branch
  `archive/cohere-compat-schema-failed-20260727`
  (commit `0646fde88a3d529ce4ebd4a4c2d5b6d3b21074a2`) — it is **not** part of
  this branch's history and must not be presented as a working fix.
- **A separate native `ClientV2` transport was then implemented and
  offline-tested (28 tests)** — a genuinely different wire protocol from
  the compatibility path. Its one authorized live confirmation call
  (request_hash `d6ba44eb9fc254a2bdd9cbae2c3005f56e4c849f6b35788998031fb88c8338fe`)
  was **rejected by Cohere's API with a 400 Bad Request before producing
  any content** — this is not a judgment-validity failure like the
  compatibility path's; root cause is unestablished (possibly a fixable
  JSON-Schema-shape issue). See "Current blocker" above.

## Consistency-aware pivot (2026-07-28) — current branch focus

Three sequential, same-day pilots (`756495d`, `91b8973`, `fc866d7`, each
followed by a `docs: freeze *_pilot_v1 config` commit), all built on **one
shared, real, pre-existing, frozen oracle**:
`outputs/openai_scidocs_real_pairwise_q50_k15/judgments.jsonl` — 50 SciDocs
queries, 15 candidates each, exactly C(15,2)=105 exhaustive real gpt-4o-mini
pairwise judgments per query (5,250 total), collected weeks earlier, never
re-collected or modified by any of the three pilots (SHA-256-verified
unchanged across all three `MANIFEST.json`s). No live provider/API calls
were made in any of the three pilots.

**1. Offline active-acquisition pilot** (`756495d`/`e4566aa`,
`reports/offline_active_acquisition_pilot_20260728T142414Z/`, tracked in
Git minus one regenerable raw log — see `docs/ARTIFACT_POLICY.md`):
**[NEGATIVE RESULT]** the proposed active pair-selection strategy
(uncertainty × counterfactual top-k impact × ambiguity) is **not
supported** — it loses to random unrevealed-pair selection at both the 10%
and 20% budget checkpoints (Holm-corrected, e.g. budget=10: mean ΔnDCG
−0.145, 9 wins / 41 losses vs. random). No leakage into the scoring
functions (structurally and behaviorally tested). This closes out the
active-pair-selection research direction as evidenced-unsupported on this
oracle, rather than leaving it as an open, unresolved proposal.

**2. Regularized (prior-regularized Bradley-Terry) aggregation pilot**
(`91b8973`/`c568b87`, `reports/regularized_aggregation_pilot_20260728T164943Z/`,
tracked in Git in full): **[SAFETY-DOMINANT, NOT UNIVERSALLY SUPERIOR]** a
regularized Bradley-Terry aggregator that reduces to the BM25 prior exactly
at zero pairwise evidence and relaxes its regularization strength as
evidence accumulates. On the 35-query held-out test split: significantly
beats BM25 at 10%/20% budget (Holm-corrected); significantly reduces the
severe-harm rate (per-query ΔnDCG@10 ≤ −0.05 vs. BM25) relative to naive
sparse Copeland aggregation at 5%/10% budget (95% CI excludes zero); does
**not** establish significantly higher raw mean nDCG or AUC than the
strongest non-oracle baseline (`pure_bt_no_prior`) — this is a genuine,
disclosed limit on the claim, not an oversight. Motivating evidence for
regularization: naive sparse Copeland aggregation is measurably unstable
(41.4% of per-step top-k sets churn on a single new revealed edge; 5.7% of
steps eject a currently-relevant document from the top-k, of which 93.3%
return once evidence is exhaustive — i.e. largely transient/fragile, not
durable corrections).

**3. Risk-controlled qrel-free stopping-rule pilot** (`fc866d7`/`b007a13`,
`reports/stopping_rule_pilot_20260728T190000Z/`, tracked in Git minus one
regenerable raw log): builds a counterfactual worst-case top-k-change
stopping statistic on top of pilot 2's aggregator, calibrated
(`tau=0.20, m=3`) on a 15-query dev split, evaluated on the same 35-query
held-out test split. The stopping decision itself is qrel-free at
inference (verified both structurally — no function signature accepts
qrels/oracle/exhaustive-ranking — and behaviorally — a test flips the
hidden answer for an unrevealed pair and confirms the decision is
unchanged). On the test split: median stop budget 34.3% (< 40% target);
**31/35 walks triggered a genuine stop, 4/35 hit the 60%-budget
simulation cap without triggering** (censored, not a stop — this
distinction is preserved end-to-end and, as of this polish pass, is also a
machine-readable `run_status` field in `statistical_analysis.json`, not
just inferable from per-row data); **0/35 test queries showed severe harm**
— the strongest safety result in the pilot, though a post-audit correction
replaced a degenerate bootstrap `[0.0%, 0.0%]` interval with a valid
Wilson interval (`[0.0%, 9.9%]`): **zero observed severe-harm events at
n=35 does not imply a true rate of exactly zero.** The rule does **not**
meet its own quality-recovery sub-criteria (≥95% of exhaustive improvement
recovered; within 0.02 nDCG of exhaustive) — traced to the aggregator's own
slow-converging tail past 60% coverage, disclosed as an aggregator
property, not a stopping-rule defect. Overall classification in the
pilot's own report: closest to "useful but incomplete" — a genuine,
well-powered safety/quality-per-dollar improvement over naive fixed
low-budget policies, not yet a complete, deployment-ready contribution on
its own.

**Independent audit:** all three pilots' headline statistics (oracle
counts/hashes, core negative and positive results, capped-vs-stopped
bookkeeping) were independently recomputed from raw artifacts during a
2026-07-28 branch audit and matched exactly; two statistical-methodology
defects (the degenerate severe-harm CI above, and an unsurfaced
capped-walk count) were found and corrected in this same polish pass. See
each pilot's own `REPORT.md` for full detail, and the branch's git history
for the audit trail.

## What is not yet established

- A clean four-provider canary pass (currently 3/4: Azure, Fireworks, Vertex
  AI/Gemini pass; Cohere fails).
- The bounded 256-initial/128-reserve/384-hard-max micro-pilot
  (`counterfactual_micro_pilot_v2`) — designed, frozen, **never executed**
  (`execute_in_this_task: false` in its config).
- A real oracle-pair-provider-opportunity audit for the counterfactual
  benchmark (only designed in `docs/benchmarks/REAL_COUNTERFACTUAL_BENCHMARK_SPEC.md`).
- A matched-budget retrieval-quality win for any multifactor acquisition
  policy over always-UHT.
- A successful learned policy selector (Outcome F gap unresolved).
- Leave-one-dataset-out / leave-one-provider-out validation for the
  counterfactual benchmark.
- Any claim that Cohere's compatibility endpoint can be made to honor a
  schema-constrained judgment format for this model.
- A complete, deployment-ready "safe anytime reranking" contribution: the
  regularized aggregator plus stopping rule is safety-dominant and
  quality-per-dollar-superior to naive fixed low budgets, but does not meet
  its own near-exhaustive-quality-recovery bar (§ "Consistency-aware
  pivot").
- External validity of the pivot beyond one real oracle: all three pilots
  use the same single SciDocs q50/k15 (50 query, 15-candidate, 105-pair)
  oracle. No second dataset, candidate-pool size, or judge model has been
  tried.
- Any claim that the active pair-selection proposal (uncertainty ×
  counterfactual impact × ambiguity) is a viable acquisition strategy — it
  is evidenced-worse than random on this oracle.

## Repository architecture

```
src/consistency_ranker/
├── graph_construction.py, cycle_detection.py, greedy_fas.py,   # mature program:
│   mwfas_solver.py, baseline_ranking.py, evaluation.py,        # preference-graph
│   rrf_ranking.py, combsum_ranking.py, ...                     # construction + repair
├── data/                                                        # dataset loaders (BEIR, HotpotQA, BRIGHT, ...)
├── policy_selection/                                            # Outcome F: gate/selector research + frozen
│                                                                 # production_config.py (always-UHT default)
├── multifactor_acquisition/                                     # production UHT + factorial acquisition,
│                                                                 # evaluation_contract.py (qrels-based metrics)
├── multi_provider_eval/                                         # shared provider dispatch, provenance store,
│                                                                 # spending ceilings (used across experiment families)
├── provider_capability/                                         # bounded connectivity/instrumentation audit
├── counterfactual_pilot/                                        # frozen v1 prompt/schema/panel/presentation
├── counterfactual_benchmark/                                    # active collector: pools, pairs, dispatch,
│                                                                 # request identity, reserve, cache, report
├── active_acquisition/                                          # CURRENT: offline pair-selection strategies,
│   oracle.py, scoring.py, strategies.py, simulate.py,            # regularized Bradley-Terry aggregation, and the
│   evaluate.py, stats.py, regularized_aggregation.py,            # qrel-free stopping rule (consistency-aware pivot)
│   stopping.py                                                   #
└── adaptive_acquisition/, prior_robust/, reliability_repair/,    # Outcome B-D driver subsystems (offline-safe;
    dag_linear_extensions/, ...                                  # see docs/experiments/OUTCOME_BCD_DRIVERS.md)
```

## Experimental families

| Family | Status | Entry point |
|---|---|---|
| Preference-graph construction/repair | Publication-ready (mature) | `scripts/run_real_experiment.py`, `scripts/run_publication_vote_suite.py` |
| Outcome F policy selection (synthetic) | Negative result, frozen | `scripts/run_policy_selection_experiment.py` |
| Multifactor acquisition (real queries) | Negative result, corrected | `scripts/reevaluate_multifactor_offline.py` |
| Outcome B-D drivers | Offline-safe, experimental | see `docs/experiments/OUTCOME_BCD_DRIVERS.md` |
| Provider capability audit | Engineering complete (connectivity only) | `scripts/audit_provider_capabilities.py` |
| Counterfactual benchmark | Engineering, canary stage, **paused** (not current focus) | `scripts/run_counterfactual_micro_pilot.py` |
| Offline active-acquisition (real oracle) | **Negative result, complete** | `scripts/run_offline_active_acquisition_pilot.py` |
| Regularized Bradley-Terry aggregation (real oracle) | **Safety-dominant result, complete** | `scripts/run_regularized_aggregation_pilot.py` |
| Risk-controlled stopping rule (real oracle) | **Complete, useful-but-incomplete** | `scripts/run_stopping_rule_pilot.py` |
| Preserve-vs-repair oracle-headroom gate (real data, mature-program follow-on) | **NO-GO — repository-scale analysis complete, direction stopped** | `scripts/run_oracle_headroom_analysis.py`, `scripts/run_repository_scale_headroom_analysis.py` |

## Current multi-provider benchmark direction

Nearby published work already covers active pair selection, noisy top-k
ranking, pairwise LLM reranking, multiple LLM judges, cost-aware model
routing, and complete pairwise-matrix replay in isolation. The differentiated
target for this repository is therefore **not** "use several LLMs" or
"actively choose document pairs" alone, but:

> A qrels-grounded, trajectory-level benchmark for **jointly** selecting
> document pairs and provider-model judges under cost, reliability, and
> safety constraints.

Design: `docs/benchmarks/REAL_COUNTERFACTUAL_BENCHMARK_SPEC.md` (status:
design only, not executed). Freeze: `docs/benchmarks/COUNTERFACTUAL_PILOT_FREEZE_V1.md`.

## Provider panel

| Provider | Model | Role |
|---|---|---|
| Microsoft Azure | `gpt-4.1-mini` | Closed-model production-style judge; **not** ground truth |
| Cohere | `command-r-plus-08-2024` | Independent Command-family judge — **currently unsupported** for schema-constrained normalization (see blocker) |
| Fireworks | `accounts/fireworks/models/gpt-oss-120b` | Hosted open-weight / economical judge |
| Google Vertex AI | `gemini-2.5-flash` | Gemini-family judge accessed through Vertex AI |

Always distinguish `provider: vertex`, `model_family: gemini`,
`model_id: gemini-2.5-flash`, `access_path: Google Vertex AI` — never refer
to a standalone "Gemini provider". qrels are evaluation truth; every LLM
provider, including Azure, is a noisy judge, never ground truth.

## Protocol and configuration registry

| Protocol | Status | Notes |
|---|---|---|
| `counterfactual_pairwise_judge_v1` | Frozen | `prompts/counterfactual_pairwise_judge_v1.txt`; unchanged by v2 work |
| `counterfactual_pairwise_judgment_v1` | Frozen | `schemas/counterfactual_pairwise_judgment_v1.json`; unchanged by v2 work |
| `counterfactual_provider_panel_v1` | Frozen, currently unsatisfiable end-to-end | 4-provider panel; Cohere cannot currently pass |
| `lexical_prior_pool_v1` | Frozen, superseded for new work | Unbounded-denominator prior; reproducibility preserved, not deleted |
| `lexical_prior_pool_v2` | Frozen, current | Bounded-denominator prior + `document_validity_v2` gate |
| `document_validity_v2` | Frozen, current | Pre-scoring eligibility gate (≥15 alpha tokens, ≥100 substantive chars, nonempty body) |
| `title_plus_prefix_truncate_v1` | Frozen, unchanged since v1 | Rendering policy; audit found no independent rendering defect |
| `counterfactual_micro_pilot_v1` | Frozen, not executed | `configs/counterfactual_micro_pilot_v1.json` |
| `counterfactual_micro_pilot_v2` | Frozen, not executed | `configs/counterfactual_micro_pilot_v2.json`; `execute_in_this_task: false` |
| `counterfactual_collector_canary_v1` | Executed (local evidence) | Instrumentation only; diagnosed content-poor pool + Vertex parse failure |
| `counterfactual_collector_canary_v2` | Executed (local evidence) | Conditional pass: 3/4 providers normalized; Cohere failed |
| `cohere_json_schema_v1` (compatibility-path) | Implemented, offline-tested, **live-confirmation FAILED** | Archived on `archive/cohere-compat-schema-failed-20260727` (`0646fde8`), **not** in this branch's history; do not present as a working fix |
| `cohere_native_v2_json_schema_v1` (native ClientV2 transport) | Implemented, offline-tested (59 tests), **4th live confirmation SUCCEEDED** (request_hash `f062ea28...`; valid judgment, passed canonical validation) after 3 prior rejections (400) on 3 different fields in turn | `src/consistency_ranker/counterfactual_benchmark/cohere_native.py`; standalone, still not wired into `dispatch.call_provider` or the frozen panel — see wiring plan in the freeze doc |
| `cohere_native_v2_schema_projection_v1` (superseded) | Removed `minimum`/`maximum` only — historical identity, one live call persisted under it (`41f1de66...`, rejected) | `src/consistency_ranker/counterfactual_benchmark/cohere_schema_projection.py` |
| `cohere_native_v2_schema_projection_v2` (superseded) | Additionally removed `$id` (live-evidenced) — historical identity, one live call persisted under it (`be312ecf...`, rejected) | Same module |
| `cohere_native_v2_schema_projection_v3` (current) | Additionally adds `type: "string"` to `schema_version` (live-evidenced: `const` alone was rejected as missing `type`); `$schema` untouched (unevidenced). **Live-confirmed working** (request_hash `f062ea28...`). | Same module; fail-closed on any other unreviewed keyword |

v1 protocols remain frozen and byte-reproducible (tested); v2 is additive,
not a silent edit — see `config.verify_frozen_contract` and
`tests/test_counterfactual_versioning.py`.

## Evidence and artifact registry

See `docs/ARTIFACT_POLICY.md` for the general policy. Current classification:

**Canonical, committed evidence:**
- `outputs/pub_vote_cmp_all4/paper_package/` — mature program's canonical result package.
- `reports/policy_selection_20260726T030500Z/` — Outcome F canonical synthetic package.
- `reports/real_query_policy_replay_20260726T042025Z/` — tracked offline replay.
- `docs/multifactor_production_uht_corrected_summary_20260727.json` — compact corrected-multifactor summary.
- `reports/offline_active_acquisition_pilot_20260728T142414Z/` — real-oracle negative result (active pair-selection); tracked minus one regenerable raw log (`raw_trajectories.jsonl`, gitignored).
- `reports/regularized_aggregation_pilot_20260728T164943Z/` — real-oracle safety-dominant result; tracked in full.
- `reports/stopping_rule_pilot_20260728T190000Z/` — real-oracle stopping-rule pilot; tracked minus one regenerable raw log (`simulate/raw_stopping_histories.jsonl`, gitignored).
- `reports/oracle_headroom_gate0_20260728T230000Z/` — preserve-vs-repair Gate-0 analysis on already-existing data (4 slices); tracked in full (~90KB); no slice cleared the gate.
- `reports/repository_scale_headroom_analysis/` — repository-scale follow-up (122,203 rows, 76 source files, 419 distinct queries); tracked minus one regenerable raw file (`per_query_effects.csv`, ~38MB, gitignored). **Concludes NO-GO** on whole-graph preserve-vs-repair prediction — see `research_decision.md` in that directory.

**Valid local-only evidence (reproducible, not committed by policy):**
- `reports/real_query_multifactor_acquisition_corrected_20260727T030457Z/` — full corrected tree (compact summary above is committed).
- `reports/provider_capability_audit_live_20260727T042703Z/` — 4/4 providers authenticated live (connectivity only).
- `reports/counterfactual_collector_canary_v1_20260727T145126Z/` — canary v1, instrumentation only.
- `reports/counterfactual_collector_canary_v2_20260727T161921Z/` — canary v2, conditional pass.
- `reports/cohere_normalization_diagnostic_20260727T183000Z/` — one bounded diagnostic call (json_object-only fix).
- `reports/cohere_json_schema_confirmation_20260727T200000Z/` — one bounded confirmation call (full schema fix); both failed identically.

**Invalid / not citable:**
- `reports/real_query_multifactor_acquisition_20260726T044254Z/` — scientifically invalid `production_uht` scoring (prior-based, not qrels-based); see invalidation doc. Kept locally for provenance only.
- `reports/policy_selection_20260726T025426Z/` — superseded `--quick`-scale smoke; do not treat as canonical.

**Canary / diagnostic only (never benchmark data):**
- Both counterfactual canary directories and both Cohere diagnostic/confirmation directories above are explicitly labeled instrumentation-only in their own `FINAL_REPORT.md` / status fields and must never be merged into `counterfactual_micro_pilot_v2` benchmark data.

## Current validation status

**Most recent (post-pivot polish pass, this local environment, `.venv`,
base + `dev` deps only — no `llm`/`exact` extras installed here):**
`pytest -q` → **1127 passed, 0 skipped, 0 failed** in 162.25s.
`ruff check` on all branch-changed files → clean; full-repository
`ruff check .` → 1,545 pre-existing findings (unrelated historical debt
outside this branch's touched files, unchanged by this pass — see
"Known limitations and blockers"). **No type checker (mypy or otherwise)
is configured in this repository** (no `[tool.mypy]` section in
`pyproject.toml`; not a dev dependency); do not expect `mypy` to be
installed without adding and configuring it first. `python -m compileall`
clean on `src`/`scripts`. `git diff --check` clean (no whitespace errors).

**Earlier snapshot (previous session, different environment):** verified
2026-07-28T03:14:55Z with the `dev`, `llm`, and `exact` optional dependency
groups installed (`pip install -e ".[dev,llm,exact]"`): `pytest -q` →
1038 passed, 0 skipped, 0 failed; `ruff check` and `python -m compileall`
clean on all changed files; `python scripts/check_repo_ready.py` → 56 OK /
5 pre-existing unrelated warnings / 0 failures. That snapshot's "mypy
clean" claim reflected that session's ad hoc use of the tool in a
different environment, not a repository-configured check — see the
correction above.

Test/skip/pass counts are environment-dependent, not a fixed repository
property (exact-repair tests skip without PySCIPOpt; provider-SDK tests
fail rather than skip if their SDK is absent; the two snapshots above
differ partly because of different installed optional-dependency groups,
not because the branch regressed) — re-run `pytest -q` against the
current HEAD rather than trusting any cached number, including these.

## Known limitations and blockers

1. **Blocking:** Cohere's OpenAI-compatibility endpoint does not appear to
   honor `response_format` (neither `json_object`-only nor schema-
   constrained) for `command-r-plus-08-2024` on the frozen prompt — two
   live confirmation calls reproduced byte-identical malformed output.
   The failed attempt is preserved only on the local archive branch
   `archive/cohere-compat-schema-failed-20260727` (`0646fde8...`), not on
   this branch.
2. Mature program: FAS repair is neutral/inactive under near-acyclic vote
   constructions and can be significantly harmful under high-cyclicity
   constructions on some benchmarks — there is no committed condition where
   repair is unconditionally beneficial.
3. Outcome F: no learned gate beats always-UHT; production is intentionally
   non-adaptive (fail-closed) until this changes.
4. Multifactor: cost-only utility signals exist; no matched-budget quality
   win is established.
5. The counterfactual benchmark has never run past a single-pair,
   single-orientation, 4-call canary; the 256-384 call micro-pilot has never
   executed. Currently paused, not the branch's active focus.
6. The active-acquisition proposal is evidenced-worse than random on the
   one oracle tested; do not resume that specific proposal without new
   evidence.
7. The regularized-aggregation + stopping-rule pivot is validated on
   exactly one real oracle (50 SciDocs queries, 15 candidates each); no
   cross-dataset or cross-judge-model generalization evidence exists yet.
8. The stopping rule does not meet its own near-exhaustive quality-recovery
   bar (traced to the aggregator's slow-converging tail past 60% coverage,
   not a stopping-rule defect) — see "Consistency-aware pivot" above.
9. No type checker (mypy or otherwise) is configured in this repository
   (no `[tool.mypy]` section in `pyproject.toml`; not a dev dependency) —
   any historical claim in this document of a "clean mypy" run describes a
   different environment/session's ad hoc use of the tool, not a repository
   convention; do not expect `mypy` to be installed or runnable without
   installing it separately.

## Publication readiness

**Strong paper currently supportable:** the construction-sensitive
preference-graph and structural-vs-retrieval decoupling result (mature
program; JDIQ 2026 manuscript already exists for this).

**Not yet supportable:** a successful learned policy selector (Outcome F is
a negative result); a matched-budget multifactor quality win.

**Potential future strong contribution:** the real multi-provider
counterfactual benchmark and a safe joint pair-provider acquisition method —
contingent on resolving the Cohere blocker and completing, at minimum:
- valid four-provider normalization (currently 3/4);
- the bounded micro-pilot (never executed);
- a real oracle-opportunity audit (only designed);
- a larger gold core or logged shell beyond the current 1-query canary;
- a matched-budget evaluation;
- leave-one-dataset-out / leave-one-provider-out validation;
- a successful method or a rigorous, well-evidenced negative benchmark result.

## Readiness gates

- [x] Provider capability audit
- [x] Frozen initial provider panel
- [x] Frozen prompt and judgment schema
- [x] Fail-closed collector
- [x] Candidate-pool v2 validity protocol
- [x] Vertex AI/Gemini wrapper normalization
- [x] Valid Cohere transport/access path selected — native `ClientV2` transport, schema projection v3
- [x] Cohere schema-valid judgment confirmed — compatibility-API path **failed twice** (archived); native `ClientV2` path **succeeded on the 4th confirmation** (request_hash `f062ea28...`) after 3 prior rejections on 3 different fields; response passed full canonical local validation
- [ ] Native Cohere transport wired into `dispatch.call_provider`/the frozen collector — plan documented in the freeze doc, not yet implemented
- [ ] Clean full-panel canary
- [ ] Bounded micro-pilot
- [ ] Micro-pilot integrity audit
- [ ] Real oracle-opportunity analysis
- [ ] Benchmark scale-up decision
- [ ] Final branch-level audit
- [ ] Push or pull request

## Roadmap

1. ✅ Keep the compatibility-shim failure archived and off the active
   branch (`archive/cohere-compat-schema-failed-20260727`, `0646fde8...`).
2. ✅ Implement a native Cohere Chat API v2 (`ClientV2`) adapter as a
   separate provider transport (`cohere_native.py`), distinct from the
   OpenAI-compatibility shim.
3. ✅ Run offline request-capture and strict-schema regression tests
   against the new adapter (28 tests, no network).
4. ✅ Authorize and execute one bounded Cohere-only live confirmation call
   against the new adapter — **result: 400 Bad Request before any content,
   root cause unestablished** (see freeze doc finding 7). Improved the
   error-message capture (previously lost the rejection reason behind HTTP
   headers) for the next attempt.
5. ✅ Authorize and execute one bounded confirmation with `minimum`/
   `maximum` removed (schema projection v1) — **result: 400 again, but the
   fixed error capture recovered the real reason for the first time:
   `$id` unsupported** (freeze doc finding 9).
6. ✅ Authorize and execute one bounded confirmation with `$id` also
   removed (schema projection v2) — **result: 400 a third time, on a new
   field: `schema_version` missing required `type`** (freeze doc finding
   11).
7. ✅ Implement the `type` addition for `const`-only properties (schema
   projection v3, freeze doc finding 12).
8. ✅ Authorize and execute one fresh bounded confirmation call under
   schema projection v3 — **result: SUCCESS.** request_hash `f062ea28...`,
   `finish_reason: COMPLETE`, valid judgment (`preference: "ABSTAIN"`,
   `confidence: 0.0`) parsed and passed full canonical local validation
   (freeze doc finding 13). This is the first successful native Cohere
   structured-output judgment in this investigation.
9. **Next:** wire the native Cohere transport into `dispatch.call_provider`/
   the frozen collector — a deliberate, reviewed implementation, not a
   trivial one; see the "Native Cohere collector-wiring plan" in the
   freeze doc for the concrete open design questions (adapter shape,
   request-hash/cache-identity extension, readiness-check routing,
   collector-test updates). Not yet implemented.
10. Once wired and offline-tested, run a clean four-provider canary under
    the existing frozen panel.
11. If native Cohere is confirmed unworkable after wiring (unexpected,
    given step 8's success, but not ruled out): freeze a new
    three-provider (Azure, Fireworks, Vertex AI/Gemini) or
    replacement-provider panel version instead.
12. Only after a clean canary passes under whichever panel is frozen,
    consider the bounded micro-pilot v2 under explicit separate
    authorization.

Steps 1-8 are done; steps 9-12 are planned, not executed.

## How to resume safely

1. Read this document, then `docs/handoff/CURRENT_BRANCH_HANDOFF.md`, then
   `docs/handoff/state_snapshot.json`.
2. Re-run the git-state commands in the handoff doc — do not trust
   `documented_code_head` or any other hash in these documents once new
   commits or staged changes exist. These documents describe the state
   immediately before their own commit, not a live, self-updating source
   of truth.
3. Never run a provider call without explicit, scoped authorization (query,
   pair, provider, call ceiling stated up front).
4. Never treat a canary or diagnostic report as benchmark data.
5. Never treat connectivity evidence as ranking-quality evidence.
6. Never treat a cost-only utility signal as a retrieval-quality win.
7. Never edit a frozen protocol artifact in place — add a new version and a
   migration note instead.

## Claims that must not be made

- "The counterfactual benchmark validates provider or policy superiority" —
  no benchmark-scale run has ever occurred.
- "Cohere is fixed" — two bounded live calls with the best available fix
  both failed identically.
- "The learned policy selector works" — Outcome F is a negative result.
- "Multifactor acquisition improves retrieval quality at matched budget" —
  only cost-only signals are established.
- "Structural graph repair improves retrieval quality" as a general claim —
  the validated result is conditional/negative.
- "Provider connectivity/capability-audit calls establish ranking quality"
  — they establish connectivity only.
- Any claim in the past tense about work that is designed but not executed
  (the micro-pilot, the oracle-opportunity audit, benchmark scale-up).
- "The active pair-selection proposal works" — it is evidenced-worse than
  random on the one oracle tested (offline active-acquisition pilot).
- "Regularized aggregation is universally superior to every baseline" — it
  is safety-dominant (severe-harm reduction, significant nDCG win over
  BM25) but is **not** established as beating the strongest non-oracle
  baseline on raw mean nDCG or AUC; do not drop this qualifier.
- "Zero observed severe-harm events means the true severe-harm rate is
  zero" — the correct statement is a Wilson 95% CI of roughly [0.0%, 9.9%]
  at n=35, not certainty of zero.
- "A capped stopping walk is a successful stop" — capped (censored, hit the
  60%-budget simulation cap without triggering) and stopped (patience
  condition triggered) are tracked as distinct outcomes throughout; do not
  conflate them.
- "The stopping rule achieves near-exhaustive quality" — it does not meet
  its own ≥95%-recovered / within-0.02-of-exhaustive bar.

## Exact next action

**For the consistency-aware pivot (current focus):** per the stopping-rule
pilot's own stop/go recommendation, the next useful increment is *not* a
broader acquisition-policy search, but a better-calibrated worst-case
statistic or regularization schedule that narrows the gap to exhaustive
quality at moderate budgets — e.g. investigating whether the
cycle/upset-fraction association found in the stopping pilot's mechanism
analysis could inform a coverage-and-consistency-aware (not just
coverage-aware) schedule, tested as a small, separate follow-up. Do not
expand into further acquisition-policy research (closed out as
unsupported), and do not yet present the pivot as a complete,
deployment-ready contribution — see "Known limitations and blockers" above.

**For the paused counterfactual-benchmark thread (not current focus, but
not abandoned):** the native Cohere transport is **live-confirmed working**
as of the 4th confirmation call (request_hash `f062ea286398b73316c1dcbbc6a9868ab698491d47a6cd0d8041a43718d1e829`,
schema projection v3, projected schema sha256
`d001a8a52fb72f5a0798e7468411348eed16516104ba00c7ba69aeb8bdcdba26`):
`finish_reason: COMPLETE`, a valid judgment returned, and it passed full
canonical local validation unchanged. Evidence at
`reports/cohere_native_v2_schema_projection_v3_confirmation_20260728T011703Z/`.

This resolves the schema/transport question but does **not** make Cohere
ready for a canary yet: the native transport is still standalone, not
wired into `dispatch.call_provider`/the frozen collector. The next step is
implementing that wiring — see "Native Cohere collector-wiring plan" in
`docs/benchmarks/COUNTERFACTUAL_PILOT_FREEZE_V1.md` for the concrete open
design questions (this is a deliberate, reviewed implementation task, not
a trivial one). Only after that is implemented and offline-tested should a
clean four-provider canary be attempted. **Do not run the micro-pilot
before the wiring is implemented and a clean canary passes.**

## Last verified state

**Post-pivot polish pass (current):** re-verified directly against Git and
the filesystem: branch `fix/outcome-f-production-operating-point`,
`documented_code_head` `cd678f02cec725496c484757146d44649ac0d034`, 28
commits ahead of `origin/main` (`3e02b73...`), 0 behind. Four new commits
landed in this pass on top of the audited `b007a13`: `a3bc58c`
(`fix(stats)`: centralized Wilson/Clopper-Pearson proportion interval),
`7c7bbfd` (`fix(stopping)`: valid severe-harm CI + explicit stopped/
capped/failed counts), `9dcc80e` (`fix(regularized-aggregation)`: Wilson
CI on per-method severe-harm rates), `cd678f0` (`chore`: track the third
pilot's report directory, update `docs/ARTIFACT_POLICY.md`). This
documentation commit (`docs: update project status and branch handoff for
the consistency-aware pivot`) lands after `cd678f0`, per the note above.
A backup branch, `backup/pre-final-branch-polish-20260728-174708`, was
created at `b007a13` before any of this pass's changes. No history was
rewritten; all changes are additive commits. See
`docs/handoff/CURRENT_BRANCH_HANDOFF.md` for the exact commands used.

**Earlier snapshot (previous session):** branch tip at that time
`3a47e90...`, 13 commits ahead of `origin/main`, 0 behind — superseded by
the state above; kept for provenance of the doc's own history.
