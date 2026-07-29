# Research Trajectory: From "Does Repair Help?" to "When Should We Preserve, Repair, or Acquire More Evidence?"

*Authoritative narrative document for the revised research direction on this
branch. Read this first if you are new to the project; it is written so a
new researcher, reviewer, collaborator, or future coding agent can
understand where the project came from, what has been learned, and exactly
what would need to be true to continue, redirect, or stop — without needing
prior conversation history.*

*Companion documents: `docs/research/EXPERIMENT_ROADMAP.md` (phased plan),
`docs/research/NOVELTY_AND_RELATED_WORK.md` (positioning),
`docs/research/DECISION_LOG.md` (why each major choice was made),
`docs/research/REPRODUCIBILITY_AND_ARTIFACTS.md` (provenance/artifact
policy for this line of work), `docs/research/MANUSCRIPT_SUMMARY.md`
(concise manuscript-facing version). `PROJECT_STATUS.md` remains the
repository-wide entry point; this document is scoped to the graph-repair
research program specifically (not the separate, more recent
active-acquisition/regularized-aggregation/stopping-rule pivot — see
`PROJECT_STATUS.md`'s "Consistency-aware pivot" section for that work,
which is a different line of research sharing only a general theme
("when should sparse or inconsistent LLM preference evidence be trusted")
with this document.*

---

## 1. What the project originally attempted

The mature research program in this repository (`src/consistency_ranker/`
core modules: `graph_construction.py`, `cycle_detection.py`,
`greedy_fas.py`, `mwfas_solver.py`, `baseline_ranking.py`, `evaluation.py`,
`dag_linear_extensions.py`) studies **rankings derived from pairwise
preferences**, in particular preference graphs built from LLM-judge
pairwise comparisons over retrieval candidates. The original hypothesis,
tested across four datasets (SciDocs, FiQA, HotpotQA, BRIGHT) and three
vote-construction regimes (`ms1`, `ms2`, `ms1_drop_mutual`):

> Pairwise preferences aggregated into a directed graph are often cyclic
> (non-transitive). Repairing that graph — removing or reversing the
> minimum-weight set of edges needed to make it acyclic (Minimum Weighted
> Feedback Arc Set, MWFAS, solved both greedily and exactly via an
> open-source SCIP ILP backend) — should improve the quality of the
> ranking extracted from it, as measured by retrieval metrics (nDCG@k)
> against qrels.

This is the subject of `papers/JDIQ_2026/manuscript/main.tex`, the
project's submitted manuscript.

## 2. What has already been implemented and experimentally established

**Structural machinery (solid, working code, exercised by 1,127 passing
tests as of this document):**
- Preference-graph construction from pairwise judgments
  (`graph_construction.py`).
- Cycle/SCC detection and summarization (`cycle_detection.py`).
- Greedy FAS repair (`greedy_fas.py`) and an exact, open-source
  SCIP-backed MWFAS solver (`mwfas_solver.py`) — **the exact solver is
  implemented and was run at scale**: proven optimal on 1,025/1,025
  nonempty graphs in the manuscript's exact-repair robustness check
  (`docs/THREATS_TO_VALIDITY.md` §5, live-corrected 2026-07-28; see also
  `reports/final_revision_task4_exact_baseline_fairness_20260715/`).
- Multiple ranking-extraction methods from a (repaired or unrepaired)
  graph: Copeland, Borda, PageRank, Rank Centrality, weighted balance,
  Markov-graph, RRF/CombSUM hybrids, plus continuous-score alternatives
  (SpringRank, SerialRank in `soft_score_ranking.py`).
- Structural-consistency metrics: backward-edge weight (BEW), pairwise
  inconsistency count (PIC), linear-extension/ambiguity features
  (`dag_linear_extensions.py`, `dag_ambiguity.py`).

**Established, positive result:**
- **Repair reliably improves structural consistency.** FAS repair removes
  0.029–0.080 of total graph weight under the high-cyclicity `ms1` regime;
  BEW and PIC both decrease after repair in every tested condition (e.g.
  SciDocs `ms1`: BEW 294.22→293.88, PIC 94.18→89.93,
  `outputs/pub_vote_cmp_all4/paper_package/tables/table_consistency_qrels_bew.csv`).
  This part of the original hypothesis is not in question.

**Established, negative/null result (the manuscript's central, current
finding — see `papers/JDIQ_2026/manuscript/main.tex`, finalized
2026-07-15):**
- **Structural improvement does not reliably translate into downstream
  retrieval-quality improvement.** Verbatim from the manuscript: *"no
  repaired-versus-unrepaired nDCG cell survives Holm correction in the
  canonical design, the larger-pool P>k study, or direct exact-repair
  checks."* Exact counts: 0/20 active canonical `ms1` cells, 0/60 full
  canonical cells, 0/110 larger-pool cells, and — critically, since this
  answers a question the project once left open — 0/36 canonical and 0/56
  larger-pool cells even when the **exact** SCIP-proven-optimal repair is
  used instead of greedy: *"Exact SCIP repair improves the graph objective
  but does not reveal a retrieval gain that greedy repair missed."*
- **Always applying repair does not reliably beat the unrepaired
  baseline**, and can be actively harmful in some conditions (a superseded
  but structurally informative earlier snapshot,
  `docs/EVIDENCE_MAP.md` E3/E4, found SciDocs `ms1` mean ΔnDCG = −0.0091,
  CI excluding zero, with harm concentrated in high-SCC queries — the
  *current* canonical package's numbers differ slightly, per the
  power-analysis discussion below, but the qualitative pattern — no
  reliable positive effect, some evidence of harm concentrated in specific
  conditions — is the manuscript's own settled position).
- **A power analysis explains why, without dismissing the result**: median
  observed |Δ| = 0.0036 vs. a Holm-adjusted 80%-power minimum-detectable
  effect (MDE) of 0.0207 in the larger-pool family. Only 13/110 cells
  (equivalence margin ±0.005) and 32/110 (margin ±0.010) reject
  non-equivalence. The manuscript's own conclusion: *"The right conclusion
  is no reliable positive evidence here, not blanket practical
  equivalence."* This matters for the revised direction (§6 below): any
  future per-query effect large enough to be worth detecting and acting on
  must clear a similar bar, or it is not distinguishable from noise at
  current sample sizes.

**A separate, adjacent negative result on this same branch (different
program, same lesson):** the Outcome F policy-selection package
(`src/consistency_ranker/policy_selection/`, unrelated codebase location
but the closest prior methodological analogue in this repository) found
that an **oracle** per-query acquisition-policy selector beats a fixed
default by a real margin (oracle − always-UHT = **0.1965** on a corrected
utility scale, `reports/policy_selection_20260726T030500Z/decision.json`),
but **no learned gate realized that gap** — the best deployable gate did
not beat the fixed default by more than noise, and one gate
(`selective_three_way`) was actively worse. Production was frozen to the
fixed default. This is the single most important piece of internal
evidence motivating the revised direction's staged, gated structure (§6,
§9): *oracle headroom existing is necessary but nowhere near sufficient for
a learned selector to be worth building.*

**Prior, informal attempts at exactly the revised research question — already
tried, already partially negative. Do not present the revised direction as
untried.** Before writing this document, three earlier, independent
attempts at "predict when repair helps" were found in this repository:

1. `outputs/learned_selector/LEARNED_SELECTOR_REPORT.md` (predates the
   JDIQ manuscript freeze): logistic regression and a shallow decision tree
   trained to decide whether to apply FAS, using 4 features
   (`bew_before, disagreement, n_sccs, cyclic_int`) on 300 queries across 3
   datasets. Verdict, quoted directly: *"Does a learned selector beat fixed
   thresholds? No. The best fixed policy (disc25 [top-25%-by-disagreement])
   achieves the highest NDCG@10."* A modest exception on HotpotQA under
   leave-one-dataset-out (+0.001 over the fixed threshold) is explicitly
   called "modest," not a win.
2. `experiments/failure_class_audit_20260711_212157/phase_reports/FAILURE_PATTERN_PREDICTION_REPORT.md`:
   logistic/tree/random-forest models predicting harm/help/non-neutral
   labels reach ROC-AUC 0.83–0.88 but **low PR-AUC (0.09–0.33)** — the
   classic signature of a model that looks informative on a
   threshold-independent ranking metric but is not yet useful at any fixed
   operating point on an imbalanced problem.
3. `src/consistency_ranker/repair_selector_mining/` (1,333 lines across 7
   modules, added in the JDIQ manuscript era, commits `bd2e894`/`b0d4852`):
   a considerably more rigorous, never-executed pipeline — leakage-safe
   query-level splitting (`splits.py`), pre-outcome feature extraction
   explicitly excluding NDCG (`candidate_selection.py`), six model families
   with bootstrapped utility CIs and oracle-regret computation
   (`selector_training.py`), and a sufficiency-classification report writer
   (`reports.py`). **No run outputs exist anywhere in this repository** —
   confirmed by `papers/JDIQ_2026/CONTRIBUTION_AUDIT.md` line 40: *"code
   fully built; no run outputs found in this repo."* The same audit
   document (line 103) also notes, as third-party context only (a separate
   codebase, out of scope for this repository's own claims): a sibling
   repository apparently ran an independent, more developed version of this
   exact research thread and reached verdict `PROMISING_BUT_MORE_DATA_REQUIRED`,
   *"failing permutation/random-feature controls."*

**What this means for the revised direction:** it is not a fresh idea. It
has been tried at least three times, informally, at increasing levels of
rigor, and every attempt so far has landed somewhere between "no signal"
and "some signal, not yet sufficient, fails negative controls." The
contribution of formalizing it now (this document and the accompanying
Gate-0 module, §6–§9) is not "propose something new" — it is **turning a
pattern of ad hoc, under-powered, inconsistently-controlled attempts into
one pre-registered, properly-gated, statistically rigorous research
protocol**, so the next attempt either produces a citable result (positive
or negative) or is stopped early and honestly, instead of producing a
fourth inconclusive report.

## 3. What results were negative, inconclusive, or weaker than initially hoped

Summarized from §2, ranked from most to least settled:

1. **Settled negative**: repair does not reliably move nDCG in the primary
   canonical design, at scale, with proper multiplicity correction — 0/60
   Holm-significant cells. This is the manuscript's central finding, not a
   preliminary one.
2. **Settled negative**: exact (SCIP-proven-optimal) repair does not rescue
   this conclusion relative to greedy repair — 0/36, 0/56.
3. **Settled negative** (adjacent program, same repository): no learned
   acquisition-policy gate beat a fixed default in Outcome F, despite real
   oracle headroom existing.
4. **Inconclusive, not settled**: whether repair effect is *predictable
   per-query from pre-repair features* — three independent informal
   attempts, none conclusive, none properly gated or negative-control-tested
   within this repository (the one rigorous pipeline was never run).
5. **Weaker than hoped, quantified**: statistical power. The manuscript's
   own MDE analysis shows most tested effects are below the detectable
   threshold at current sample sizes — this is a real constraint on any
   future per-query analysis too, not just the aggregate one.

**Nothing in this document should be read as hiding these results.** They
are the motivation for the revised direction, not an embarrassment to work
around.

## 4. Why the project is changing direction

Two independent lines of evidence point the same way:

- The "does repair help, on average, always" question is answered (no),
  robustly, with the right statistical machinery, at scale. Re-running the
  same question on more datasets or newer judge models (an option
  explicitly rejected — see §6) would not change the answer's structure;
  it would only add more null cells.
- The manuscript's own aggregate result is compatible with **per-query
  heterogeneity that a mean-based, Holm-corrected test cannot see**: a
  regime can have zero significant *average* effect while still containing
  a meaningful subset of queries that are helped and a meaningful subset
  that are harmed, if those effects partially cancel in the mean. The
  informal prior attempts (§2) hint at exactly this (BEW/disagreement
  features carry some signal; ROC-AUC is well above chance; the mature
  package's own SCC-stratified analysis in the superseded evidence map
  found harm concentrated in high-SCC queries specifically, not uniform) —
  but none of the three attempts was rigorous enough to turn "some signal"
  into a citable claim.

So the revised direction does not contradict the manuscript's central
finding — it takes it as given and asks the next, narrower question the
aggregate analysis structurally cannot answer.

## 5. What the new research question is

> **When should an inconsistent LLM-derived preference graph be preserved,
> repaired, or subjected to additional judgment acquisition?**

The first and most important subproblem, and the only one this document
licenses starting work on right now:

> **Can observable pre-repair properties of a query's preference graph
> predict the downstream effect of graph repair?**

Formally, for query \(q\) and downstream metric \(M\) (e.g. nDCG@10):

\[
\Delta_q^{\mathrm{repair}} = M_q(\mathrm{repair}) - M_q(\mathrm{preserve})
\]

The initial machine-learning problem is to predict, from features
observable **before** the repair-vs-preserve decision is made, one of:
- the numerical repair effect \(\Delta_q^{\mathrm{repair}}\) (regression);
- whether repair is beneficial, neutral, or harmful (three-way
  classification, threshold-parameterized — see
  `src/consistency_ranker/repair_selector_mining/label_generation.py`);
- the preferred action between `preserve` and `repair` (binary
  classification / policy learning).

The eventual, NOT-yet-licensed extended action space is
\(A = \{\mathrm{preserve}, \mathrm{repair}, \mathrm{requery}\}\) — see §7
and the roadmap doc for exactly what must be true before this expansion is
attempted.

## 6. What the precise novelty claim may be

See `docs/research/NOVELTY_AND_RELATED_WORK.md` for the full related-work
map. Short version, stated cautiously per that document's own rules:

Prior work already substantially covers pairwise LLM reranking, preference-
graph construction and aggregation, LLM-judge non-transitivity detection,
graph denoising, feedback-arc-set/Kemeny ranking, active pairwise-comparison
acquisition, uncertainty-aware reranking, and learning-to-defer /
algorithm-selection in adjacent domains. **None of these, individually, is
being claimed as novel by this project.**

The potential remaining gap, stated as a hypothesis requiring literature
verification, not an established claim:

> Existing work detects, aggregates, denoises, or mitigates inconsistent
> LLM preferences, but — as far as a (non-exhaustive, not yet
> professionally verified) search of this repository's own related-work
> notes and general awareness of the area can determine — does not appear
> to **predict, per retrieval query, whether enforcing consistency through
> graph repair will improve downstream ranking quality**, using only
> pre-repair, pre-outcome signals.

A stronger, later formulation, similarly hedged:

> **Selective consistency management for LLM-derived preference graphs**:
> use pre-intervention graph and uncertainty signals to choose whether to
> preserve the graph, repair it, or acquire additional evidence.

This is "potentially novel," "no direct prior work identified within this
repository's own literature review to date," and explicitly **requires
further literature verification** before any submission-facing claim is
made. See the novelty document's "claims that must not be made" section.

## 7. What remains unproven

Everything downstream of Gate 0 (§9). Concretely, as of this document:

- Whether there is **enough oracle headroom, on already-existing data, to
  justify any further work** — this is exactly what Gate 0 tests, and the
  first real (non-fabricated) run of it (§9, `reports/oracle_headroom_gate0_20260728T230000Z/`)
  did **not** cleanly clear the gate on any of four tested dataset slices —
  three landed `AMBIGUOUS_NEED_MORE_DATA`, one landed
  `NO_HEADROOM_DO_NOT_LEARN`. Nothing about the predictive question has
  been validated; it has not even been shown yet that this problem has
  enough signal to be worth formal labeling/feature/model work at current
  sample sizes on this particular data slice.
- Whether pre-repair features (once properly extracted via the existing
  `candidate_selection.pre_outcome_features`, not yet wired to real query
  graphs at scale in this pass) carry predictive signal beyond the weak,
  inconsistent signal found in the three informal prior attempts.
- Whether any such signal survives negative controls: permutation tests,
  random-feature baselines, and held-out (not just cross-validated) test
  performance — the sibling repository's own verdict on a closely related
  attempt was `PROMISING_BUT_MORE_DATA_REQUIRED... failing
  permutation/random-feature controls`, which is exactly the failure mode
  this project must design against, not repeat.
- The entire re-query action and its cost model (§ "Re-query extension" in
  the roadmap doc) — no design has been chosen, only candidates listed.
- Any causal claim about *why* repair helps or harms specific queries —
  this project's initial phase is supervised effect-prediction /
  algorithm-selection on offline-computable outcomes (§8), not causal
  inference, and should not be described as the latter.

## 8. Important methodological clarification: this is not (yet) causal inference

Both `M_q(\mathrm{preserve})` and `M_q(\mathrm{repair})` can be computed
offline, for the same query, from the same preference graph (repair is
deterministic given the graph; nDCG is computed against fixed qrels). Both
potential outcomes are therefore **observed**, not one observed and one
counterfactual. The initial problem is **supervised effect prediction,
action-value prediction, or algorithm selection** — not observational
causal-effect estimation, and should never be described with causal-
inference vocabulary (treatment effect, confounding, propensity, etc.) at
this stage.

Appropriate initial models (all already available via reused
infrastructure — see `docs/research/EXPERIMENT_ROADMAP.md` and
`selector_training.py`'s existing model zoo): linear/logistic regression,
regularized regression, decision trees, random forests, gradient-boosted
trees, calibrated classifiers, simple threshold policies. A graph neural
network is an explicitly later-only extension, gated behind the tabular
baselines showing real headroom and sufficient data volume (see the
roadmap doc) — do not reach for a GNN before a logistic regression has
been tried and has failed to capture the signal a GNN might.

Causal/uplift/doubly-robust methods become relevant only if a future phase
changes the setting so that: only one action's outcome is observed per
query; historical action assignment was non-random; the acquisition action
itself changes which labels become observable (this becomes relevant once
`requery` enters the action space, since re-querying changes what future
evidence exists); the system uses logged production data instead of
offline replay; or the research question shifts to mechanism rather than
executable policy comparison. None of these conditions hold yet.

## 9. What experiments and implementation work must come next

See `docs/research/EXPERIMENT_ROADMAP.md` for the full phased plan,
including the machine-readable spec
(`configs/preserve_repair_experiment_spec_v1.json`). Summary:

**Phase 0 (done, this pass — read-only analysis of already-existing data,
no new experiments):**
- Built and tested `src/consistency_ranker/repair_selector_mining/oracle_headroom.py`,
  `label_generation.py`, `grouped_splits.py` (see §10 and the artifact doc
  for exactly what was and was not implemented, and why existing
  infrastructure — `policy_selection.policy_utility.regret_vs_oracle`,
  `repair_selector_mining.splits.assign_splits`,
  `statistical_inference.bootstrap_mean_interval` — was reused rather than
  duplicated).
- Ran the oracle-headroom gate on four already-existing, already-committed
  dataset slices from `reports/candidate_pool_conditional_audit_20260714/tables/pool_robustness_paired_deltas.csv`
  (46,170 rows, unmodified). Real result, not fabricated: no slice cleared
  `PROCEED_TO_LABELING` at the pre-registered threshold; see
  `reports/oracle_headroom_gate0_20260728T230000Z/README.md`.

**Phase 1 (next, still offline, still no new experiments — see roadmap
doc for exact steps):** widen the oracle-headroom analysis across more of
the already-existing `pool_robustness_paired_deltas.csv` slices (other
regimes, pools, pair_names — all already on disk) to get a larger,
still-offline sample before deciding whether Gate 0 passes or fails
overall. This is the literal next single experiment (§ "Exact next
experiment" is stated precisely in the roadmap doc and in this session's
final report).

**Phase 2 (gated on Phase 1 passing):** wire `candidate_selection.pre_outcome_features`
to real query graphs at the same scale as the Phase 1 sample; build the
feature table; run the label-sensitivity analysis already implemented
(`label_generation.label_sensitivity_table`) to pick and freeze an
epsilon.

**Phase 3 (gated on Phase 2 showing measurable feature-outcome
association):** train the baseline+learned models already implemented in
`repair_selector_mining/selector_training.py` (never run to completion),
using the grouped, leakage-safe splits from Phase 1/2, WITH permutation
and random-feature negative controls (not present in any prior attempt,
including the never-run rigorous pipeline) added before any positive claim
is made.

**Phase 4 (gated on Phase 3 surviving negative controls):**
generalization checks — leave-one-dataset-out, leave-one-regime-out — and
only then, the re-query extension design work (§ "Re-query extension" in
the roadmap doc).

No phase past Phase 0 has been executed. This document does not claim
otherwise.

## 10. Conditions for continuing, changing direction again, or stopping

Restated precisely from the go/no-go machinery already implemented
(`oracle_headroom.evaluate_go_no_go`) and the roadmap doc's fallback-path
section:

- **If oracle headroom is strong (Gate 0 clears) and later prediction
  succeeds and survives negative controls:** proceed to full
  preserve/repair (and eventually requery) policy learning — the
  "selective consistency management" contribution becomes citable.
- **If oracle headroom is strong but prediction fails or does not survive
  negative controls:** this is itself a citable, rigorous negative result
  — "per-query repair-effect prediction is not achievable from the
  features tested" — matching the pattern of the three prior informal
  attempts, but now with pre-registered controls making the negative
  result trustworthy rather than merely another inconclusive report.
- **If oracle headroom is weak (as it currently appears to be, per §9's
  real Phase 0 result on the tested slices):** do not force a learned
  policy. Widen the offline sample first (Phase 1); if headroom remains
  weak after that, pivot to the negative-result framing: "structural
  inconsistency reduction is a poor proxy for downstream ranking
  improvement, and per-query selection does not recover a practically
  useful signal either" — a stronger, more complete version of the
  manuscript's existing conclusion, not a contradiction of it.
- **If whole-graph prediction fails but component-level (SCC-level or
  edge-level) effects look more promising** in exploratory analysis: this
  is a contingency path, not a commitment — see the roadmap doc.

## 11. How the current branch should serve as the clean baseline for manuscript-oriented work

This branch (`fix/outcome-f-production-operating-point`) already contains:
- The finalized JDIQ manuscript's null result, fully evidenced and
  reproducible (`papers/JDIQ_2026/`).
- A separately-evidenced, independently-audited pivot
  (active-acquisition/regularized-aggregation/stopping-rule — see
  `PROJECT_STATUS.md`) that is NOT part of this research trajectory but
  shares its house style (real-oracle evidence, Wilson/bootstrap CIs,
  qrel-free-at-inference discipline where applicable, explicit go/no-go
  gates) and its statistics module (`statistical_inference.py`).
- Now, this document set plus a tested, working, but deliberately
  **unexecuted-past-Phase-0** Gate-0 module for the preserve-vs-repair
  question.

Nothing about this document's additions changes any existing test,
existing report, or existing manuscript claim. `pytest -q` results before
and after this pass are identical except for the addition of new,
passing tests for the new modules (see the final report for this session
for exact counts). This branch is therefore a valid, clean baseline: a
future researcher can read this document, the roadmap doc, and the
`oracle_headroom` module's tests to understand exactly what is proven,
what is scaffolding, and what is untouched, and can resume at Phase 1
without needing any additional context.
