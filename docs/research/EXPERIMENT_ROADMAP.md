# Experiment Roadmap: Preserve vs. Repair vs. Re-query

*Companion to `docs/research/RESEARCH_TRAJECTORY.md` (read that first for
the narrative/why). This document is the phased, checklist-style plan:
what to build, in what order, gated by what evidence at each step. Phase 0
is done (code + one real, non-fabricated run); nothing past Phase 0 has
been executed.*

---

## Phase 0 — Oracle-headroom gate (DONE this pass)

**Goal:** before any labels, features, or models — is there enough
per-query heterogeneity in the repair effect, on already-existing data, to
justify further work at all?

**Implemented** (`src/consistency_ranker/repair_selector_mining/`):
- `oracle_headroom.py`: `PreserveRepairRecord`, `load_paired_delta_records`
  (reads the existing `pool_robustness_paired_deltas.csv`-shaped tables),
  `compute_oracle_headroom` (means, headroom \(H\), bootstrap CI via
  `statistical_inference.bootstrap_mean_interval`, per-query regret via
  `policy_selection.policy_utility.regret_vs_oracle`), `evaluate_go_no_go`
  (three-way decision: `PROCEED_TO_LABELING` /
  `NO_HEADROOM_DO_NOT_LEARN` / `AMBIGUOUS_NEED_MORE_DATA`),
  `write_oracle_headroom_report` (deterministic Markdown + JSON).
- `label_generation.py`: `regression_labels`, `three_way_label(s)`
  (epsilon-parameterized, never hard-coded), `label_sensitivity_table`
  (reports class balance across an epsilon grid so a threshold choice is
  auditable), `assert_no_outcome_leakage` (name-level leakage guard).
- `grouped_splits.py`: thin, documented wrapper around the EXISTING
  `repair_selector_mining.splits.assign_splits`/`split_rows` (built for
  the JDIQ-era mining pipeline; reused, not duplicated) — see the module
  docstring for a specific, real gotcha it works around (query-text
  fingerprint collision when there is no query text available).
- `scripts/run_oracle_headroom_analysis.py`: CLI gluing the above together
  against a real CSV; no model training.
- `tests/test_oracle_headroom.py`: 26 tests (delta/oracle-action
  correctness, ties, headroom identities, go/no-go boundaries, CSV
  filtering/missing-row handling, label thresholds/sensitivity, leakage
  guard, grouped-split no-leakage + determinism, byte-identical report
  regeneration).

**Real run, real (not fabricated) result:**
`reports/oracle_headroom_gate0_20260728T230000Z/` — four dataset slices
(SciDocs, FiQA, HotpotQA, BRIGHT; `ms1` regime, `rrf_union_topk` pool,
`copeland_graph` pair; n = 50–120 queries each), reading the already-
committed `reports/candidate_pool_conditional_audit_20260714/tables/pool_robustness_paired_deltas.csv`.
**No slice cleared `PROCEED_TO_LABELING`** at `headroom_threshold=0.01`,
`min_heterogeneity_fraction=0.05`: SciDocs → `NO_HEADROOM_DO_NOT_LEARN`;
FiQA, HotpotQA, BRIGHT → `AMBIGUOUS_NEED_MORE_DATA` (CI straddles the
threshold, not "no effect" — see the README in that report directory for
the honest reading, including that both benefit and harm fractions do
clear the heterogeneity bar in the slices checked).

**Exit criterion for Phase 0 → Phase 1:** always met (Phase 0 is
diagnostic; its output determines the framing of Phase 1, not whether
Phase 1 happens).

---

> **SUPERSEDED, 2026-07-28.** Phase 1 as described below has effectively
> been completed and superseded by a repository-scale version of the same
> idea: `reports/repository_scale_headroom_analysis/` widened the sample
> far beyond what Phase 1 proposed (122,203 rows / 419 distinct queries
> across 76 source files, vs. the 4 slices / ~350 rows Phase 0 used) and
> found the widened result does **not** clear the go/no-go gate — headroom
> is real but ~8x below the manuscript's own detectability floor. See
> `reports/repository_scale_headroom_analysis/research_decision.md` for
> the full analysis and the resulting **NO-GO** recommendation. Phases 2–4
> below are correspondingly not recommended to proceed for the whole-graph
> formulation they describe; the roadmap's own Phase-7-D alternative
> (component/edge-level reformulation) remains open and ungated. This
> phase's original text is kept below for provenance of how the plan was
> reasoned about before the wider analysis ran.

## Phase 1 — Widen the offline oracle-headroom sample (SUPERSEDED — see note above)

**Goal:** the Phase 0 result was `AMBIGUOUS` in 3/4 slices mostly because
of small n (50–120 queries) relative to a small effect. Before concluding
either way, widen the sample using data **already on disk** — this is
still Phase 0's question (does headroom exist), just with more power.

**Concrete, bounded, offline steps (all read `pool_robustness_paired_deltas.csv`,
which has 46,170 rows — the four Phase-0 slices used only ~350 of them):**
1. Re-run `scripts/run_oracle_headroom_analysis.py` across the other two
   vote regimes (`ms2`, `ms1_drop_mutual`) and the other four `pool_id`
   values (`equal_depth_union`, `neutral_round_robin_union`, `bm25_only`,
   `combsum_union_topk`) already present in the same CSV.
2. Re-run across the other `pair_name` values already present
   (`balance_graph`, `markov_graph`, `pagerank_graph`,
   `rank_centrality_graph`, `bradley_terry_graph`, and the `*_hybrid`
   family) — each is a different repair/extraction combination and should
   be treated as a separate slice, not pooled blindly with `copeland_graph`
   (pooling them would mix different action definitions).
3. Also probe the exact-ILP-repair per-query table
   (`reports/final_revision_task4_exact_baseline_fairness_20260715/tables/exact_repaired_vs_unrepaired_pair_metrics.csv`,
   local-only — regenerate via that task's own reproduction steps if
   working from a fresh clone) as an independent, higher-rigor comparison
   point to the greedy-repair slices above.
4. Tabulate all slices' `(decision, headroom, CI, n)` in one combined
   report (extend `write_oracle_headroom_report`'s caller or write a small
   aggregation script — not yet built).

**Exit criterion for Phase 1 → Phase 2:** at least one dataset × regime ×
pool × pair slice (or a principled pooling of several — e.g. all slices
within one dataset, respecting that they are NOT independent since they
share the same underlying judgments, so pooling must not silently inflate
apparent \(n\)) reaches `PROCEED_TO_LABELING`. If none do after Phase 1,
follow the negative-result fallback path in the trajectory doc §10 rather
than proceeding to Phase 2 anyway.

---

## Phase 2 — Feature extraction and label freezing (gated on Phase 1)

**Feature groups** (status: which already have working code vs. need new
work):

- **Graph topology** — MOSTLY EXISTS: `cycle_detection.py`
  (`count_cycles`, `nodes_in_cycles`, `cycle_summary`),
  `graph_construction.graph_summary` (node/edge counts, density),
  `candidate_selection.pre_outcome_features` (`is_cyclic`,
  `largest_scc_frac`, `n_non_trivial_sccs`, `scc_cycle_burden_frac`,
  `n_mutual_pairs_frac`, `graph_density`). Cycle-length statistics and
  top-rank cyclic-node involvement are NOT yet exposed as named features —
  new, small work.
- **Edge confidence and instability** — PARTIALLY EXISTS: vote entropy
  (`candidate_selection._vote_entropy`), FAS-removed-weight fraction, and
  greedy/exact-repair disagreement (`candidate_selection._greedy_exact_disagreement`,
  though gated on SCIP availability and small graphs) already implemented.
  Edge-weight variance, minimum/mean margin, low-margin-edge fraction,
  bidirectional disagreement, and repeated-sampling stability are NOT yet
  implemented (the current oracle only has one judgment per pair in most
  of this repository's real-data slices, so "repeated-sampling stability"
  may not be computable at all without new judgments — flag this
  explicitly rather than silently skipping it).
- **Repair descriptors (pre-decision, not post-outcome)** — PARTIALLY
  EXISTS: FAS removed weight already a feature. Preliminary rank
  displacement and top-k-node-affected counts are NOT yet implemented as
  named features but are computable from existing repair output (the
  repaired ranking is already produced by `greedy_fas`/`mwfas_solver`; the
  gap is only in packaging the comparison as a feature, not in re-running
  repair). **Guardrail, not yet enforced by code**: a repair candidate may
  be computed for feature extraction, but its NDCG must never leak into
  the feature vector — `label_generation.assert_no_outcome_leakage` exists
  for exactly this check and must be run against any new feature schema
  before use.
- **Aggregator disagreement** — PARTIALLY EXISTS:
  `candidate_selection._ranker_disagreement` (top-1 disagreement across
  provided score maps) exists but is generic/coarse. Pairwise Kendall
  distance, rank-variance, and top-k-overlap between specific aggregators
  (Copeland/PageRank/Bradley-Terry/HodgeRank/Rank Centrality/Borda) are NOT
  yet implemented as a feature set — would need to call
  `baseline_ranking.py`'s several ranking functions on the same graph and
  compare, which is straightforward given existing code but not yet
  wired.
- **Query and candidate-set features** — MOSTLY ABSENT as named features
  in this feature-extraction module (first-stage retriever score
  dispersion, candidate similarity/diversity are computable from existing
  loaders but not yet extracted here) — new work, offline (uses existing
  retrieved candidate pools, no new retrieval calls needed).
- **Cross-judge features** — NOT APPLICABLE YET: this repository's current
  real-data slices are single-judge (one LLM judge per pair, mostly). Only
  relevant once/if a multi-judge preference dataset is used; document as
  future work, do not build speculative code for it now.
- **Explicitly forbidden as features** (checked by
  `assert_no_outcome_leakage` and, more importantly, by the fact that
  `pre_outcome_features` is a genuinely separate code path from any
  metric/label computation): relevance judgments, qrels, downstream metric
  outcomes, the target label itself.

**Label freezing:** run `label_generation.label_sensitivity_table` over a
predeclared epsilon grid (e.g. `[0.0, 0.0025, 0.005, 0.01, 0.02, 0.05]`,
matching the manuscript's own equivalence-margin vocabulary) on the
Phase-1-selected slice(s), and freeze one epsilon **before** looking at any
model's performance — record the choice and its stated rationale in
`docs/research/DECISION_LOG.md`, not just in code.

**Data splitting** (already implemented, reused from Phase 0 —
`grouped_splits.split_records`): grouped by `(dataset, query_id)`, no
query in more than one split. **Required, not yet all implemented**:
leave-one-dataset-out and leave-one-regime-out evaluation protocols
(the existing `policy_selection.policy_benchmark.leave_one_regime_out_folds`
groups by *regime name*, a usable pattern to adapt) — leave-one-judge-
family-out is not applicable until multi-judge data exists (see above). A
**random per-row split that lets the same query appear in both train and
test is prohibited** — `grouped_splits.split_records` structurally
prevents this; do not bypass it with an ad hoc `train_test_split` call
elsewhere.

**Exit criterion for Phase 2 → Phase 3:** the frozen epsilon and feature
schema pass `assert_no_outcome_leakage`; the label distribution at the
frozen epsilon has enough members in both the beneficial and harmful
classes (a concrete number should be set once Phase 1's n is known, e.g.
"at least 15 held-out test-split beneficial and 15 harmful," mirroring the
never-fully-cleared "Locked test: 15/10/5 positives" target already
written into `repair_selector_mining/reports.py`'s aspirational-targets
table — that target was never reached in any run found in this
repository, so treat it as a real, historically-unmet bar, not a formality).

---

## Phase 3 — Baselines and learned models (gated on Phase 2)

**Static baselines:** always-preserve, always-repair, oracle
(preserve/repair), majority-class action — all already computable via
`oracle_headroom`/`compute_oracle_headroom` plus a trivial majority-vote
helper (not yet written; small addition).

**Heuristic gates** (require Phase 2's topology features): repair-if-
cyclic, repair-if-cyclic-node-fraction-exceeds-threshold, repair-if-
largest-SCC-exceeds-threshold, repair-if-estimated-cost-below/above-
threshold, repair-based-on-mean-confidence, repair-based-on-order-
instability, repair-based-on-aggregator-disagreement. The
`heuristic_cyclic_scc` baseline already exists in
`selector_training._train_one_threshold` (never run) as a concrete
existing implementation of the first of these.

**Learned policies:** `selector_training.py` already implements logistic
regression, two shallow-tree depths, random forest, gradient boosting, and
a calibrated random forest, each threshold-tuned on validation only, with
bootstrapped-CI utility, precision/recall/F1/balanced-accuracy/ROC-AUC/
PR-AUC/Brier score, and oracle-regret reporting
(`selector_training._summarize_model`). **Do not rewrite this — run it**,
once Phase 2 produces a real feature table in the shape it expects
(`train_repair_selectors(train_records, val_records, test_records,
extract_features=..., feature_names=..., out_dir=...)`).

**Required, not present in ANY prior attempt in this repository, and
mandatory before any positive claim:** permutation tests (shuffle labels,
re-fit, confirm performance collapses to chance) and random-feature
baselines (fit the same models on features replaced by independent noise
of the same shape, confirm they do not match the real-feature models).
This is precisely the check that the sibling repository's own related
attempt reportedly failed — treat it as the single most important gate in
this entire roadmap, not an afterthought.

**Evaluation criteria** (primary: downstream policy quality, not
classifier accuracy — do not treat high accuracy alone as success): nDCG@k
/ MRR / Recall under the selected policy; regret relative to oracle
(`policy_selection.policy_utility.regret_vs_oracle`, reused); improvement
over always-preserve and always-repair; coverage-vs-gain for selective
(abstaining) policies; precision/recall/balanced-accuracy/PR-AUC for
identifying beneficial repairs specifically (not overall accuracy, which
can be dominated by the majority class); calibration
(`policy_selection.policy_calibration.evaluation_metrics`, reused);
bootstrap/Wilson CIs via `statistical_inference` (reused — **do not
reintroduce a degenerate bootstrap CI for a 0/n or n/n rate; use
`proportion_interval`**, per the lesson already learned and fixed
elsewhere on this branch); severe-harm rate with a valid binomial CI (same
`proportion_interval`); policy stability across datasets/judges (leave-
one-X-out, above).

**Exit criterion for Phase 3 → Phase 4:** best learned policy beats both
always-preserve and always-repair by a margin whose CI excludes zero on
the LOCKED test split, AND survives both the permutation test and the
random-feature-baseline control. If it does not: stop here and write up
the negative result (trajectory doc §10) — this is a valid, citable
outcome, not a failure to hide.

---

## Phase 4 — Generalization and the re-query extension (gated on Phase 3)

**Generalization:** leave-one-dataset-out, leave-one-regime-out (patterns
above); leave-one-pool-construction-method-out if Phase 1's slice selection
used multiple pool_ids.

**Re-query extension — design candidates only, NOT implemented, do not
claim otherwise.** The eventual, principled policy:

\[
\pi(G_q) =
\begin{cases}
\mathrm{repair}, & \widehat{\Delta}_q > \tau_+ \\
\mathrm{preserve}, & \widehat{\Delta}_q < \tau_- \\
\mathrm{acquire\ more\ evidence}, & \text{otherwise}
\end{cases}
\]

where the acquisition branch is triggered by **uncertainty in the
predicted intervention value**, not merely graph uncertainty (a subtly
different, and more relevant, quantity — a graph can be topologically
uncertain, e.g. many small SCCs, while the model is nonetheless confident
that repair won't move nDCG much either way).

"Re-query" must mean one precisely specified acquisition operation before
any implementation starts, chosen from (not yet decided between):
reversing the order of an uncertain comparison; repeating a comparison
with the same judge; obtaining a comparison from a second judge; querying
the edge with the highest uncertainty-weighted structural influence;
querying an edge inside an influential SCC; acquiring one comparison and
then recomputing the preserve-vs-repair decision. Cost must be explicit:

\[
U_q(a) = M_q(a) - \lambda \, C_q(a)
\]

with \(C_q(a)\) = judgment cost / token cost / latency / call count,
mirroring `policy_selection.policy_utility.compute_utility`'s
`lambda_c` term (reusable directly once an action-cost model is chosen).
Candidate acquisition-selection policies to compare (design only): lowest-
confidence cyclic edge; highest-expected-FAS-impact edge; highest-top-k-
structural-influence edge; edge whose reversal most changes aggregator
consensus; highest cross-judge disagreement (once multi-judge data
exists); uncertainty sampling; an "active-PRP"-style baseline (see the
novelty doc's related-work category 5).

**This entire phase is explicitly out of scope until Phase 3 exits
successfully.** Do not build re-query infrastructure speculatively.

---

## Machine-readable specification

`configs/preserve_repair_experiment_spec_v1.json` records the action
definitions, target metrics, label-threshold grid, feature-group names,
split rule parameters, baseline list, and gate thresholds in one
versioned, schema-checked file, so future phases read configuration rather
than re-deriving it from prose. See that file directly; it is the
executable source of truth for parameters quoted in prose above (if this
document and that file ever disagree, trust the JSON file and fix this
document).
