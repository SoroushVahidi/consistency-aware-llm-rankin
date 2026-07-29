# Manuscript-Facing Summary: Preserve vs. Repair (Draft Framing, Not a Submission Draft)

*Companion to `docs/research/RESEARCH_TRAJECTORY.md`. This is a concise,
manuscript-oriented framing for a possible future paper or paper section —
it is explicitly NOT a claim that this work is submission-ready, and it
must not be copied into a manuscript without updating it to match whatever
Phase 1–3 (roadmap doc) actually find. Every sentence below is tagged with
its evidentiary status.*

## Problem statement

LLM-derived pairwise preference graphs for retrieval reranking are often
non-transitive. A natural response is to repair the graph (minimum
weighted feedback-arc-set removal) before extracting a ranking. **[established
result]** Repair reliably reduces structural inconsistency but does not
reliably improve retrieval quality in aggregate, even under exact
(SCIP-proven-optimal) repair, with proper multiplicity correction, at
scale (`papers/JDIQ_2026/manuscript/main.tex`).

## Motivating negative finding

**[established result]** Zero of 60 canonical, Holm-corrected
repaired-vs-unrepaired nDCG comparisons are statistically significant; the
same holds under a larger candidate pool (0/110) and under exact repair
(0/36, 0/56). A power analysis shows most observed effects are below the
sample size's detectable threshold. This is not preliminary; it is the
manuscript's finalized, submitted position.

## Research gap

**[working hypothesis, not established]** An aggregate null result is
consistent with query-level heterogeneity in the repair effect that a
mean-based test cannot see. **[established, internal, repeated finding —
not yet a positive result]** Three independent prior informal attempts in
this repository to detect such heterogeneity from pre-repair features
found weak-to-inconclusive signal (a fixed disagreement-threshold
heuristic beat learned models in one attempt; ROC-AUC well above chance
but PR-AUC low in another; a more rigorous pipeline was built but never
executed in a third). No attempt included permutation or random-feature
negative controls.

## Proposed formulation

**[proposed, not executed beyond Phase 0]**

\[
\Delta_q^{\mathrm{repair}} = M_q(\mathrm{repair}) - M_q(\mathrm{preserve})
\]

predicted from pre-repair, pre-outcome features, as a supervised
regression/classification/algorithm-selection problem (not causal
inference — see trajectory doc §8), gated by an oracle-headroom check
before any labeling/feature/model investment (roadmap doc Phase 0–3).

## Hypotheses

- H1: per-query repair-effect heterogeneity exists and is large enough,
  relative to sampling noise, to be worth modeling (**tested, Phase 0,
  real result: not yet confirmed** — see below).
- H2: pre-repair graph/uncertainty features carry predictive signal for
  this effect that survives permutation and random-feature controls
  (**not yet tested**).
- H3: a learned preserve/repair selector beats both fixed baselines by a
  margin with a CI excluding zero on a locked, query-grouped test split
  (**not yet tested**).

## Contributions that are completed

- A tested, working, offline oracle-headroom analysis module
  (`src/consistency_ranker/repair_selector_mining/oracle_headroom.py`,
  `label_generation.py`, `grouped_splits.py`; 26 passing tests) that
  computes H1's test statistic with a proper bootstrap CI and a
  pre-registered three-way decision rule.
- One real (non-fabricated) run of that module against already-existing,
  committed data across four datasets
  (`reports/oracle_headroom_gate0_20260728T230000Z/`). **Result: no tested
  slice cleared the pre-registered `PROCEED_TO_LABELING` threshold** — one
  slice (SciDocs) cleanly failed the gate; three (FiQA, HotpotQA, BRIGHT)
  were ambiguous due to sample size, not a clean pass.
- A related-work map identifying eight relevant prior-work categories and
  a cautiously-worded, unverified novelty hypothesis
  (`docs/research/NOVELTY_AND_RELATED_WORK.md`).
- Full documentation of three prior, informal, inconclusive attempts at
  this same question already present in this repository, prominently
  surfaced rather than left buried (trajectory doc §2).

## Contributions that are planned, not completed

- Widening the Phase-0 sample (roadmap doc Phase 1) — the literal next
  experiment.
- Pre-repair feature extraction at scale, label freezing with a documented
  epsilon choice (Phase 2).
- Baseline and learned-model training with mandatory permutation/random-
  feature negative controls (Phase 3) — the single most important
  methodological addition over every prior attempt.
- Generalization checks and the re-query extension (Phase 4) — explicitly
  gated, not started.

## Threats to validity (anticipated, to be revisited once later phases run)

- Multiple-comparisons risk across many dataset/regime/pool/pair slices in
  Phase 1 — any positive finding there must itself be corrected (Holm or
  similar) before being treated as confirmatory, not just used to pick
  which slice to study further.
- The oracle-headroom statistic is a max-type quantity and can show
  small positive apparent headroom from pure noise (a "winner's curse"
  effect) even under a true null — this is why the go/no-go rule requires
  the CI *lower* bound (not just the point estimate) to clear the
  threshold before proceeding, and why the current real result (CI
  spanning or below the threshold in all four slices) is treated as "not
  yet passed," not "close enough."
- Label-threshold sensitivity: any three-way classification result is
  conditional on the frozen epsilon; the sensitivity table
  (`label_generation.label_sensitivity_table`) must be reported alongside
  any downstream result, not hidden.
- The internal precedent (Outcome F: real oracle headroom existed, no
  learned gate realized it) means even a Phase 0 pass in a future,
  wider-sample run does not guarantee Phase 3 success — this must be
  stated explicitly in any future paper draft, not treated as a formality.

## Go/no-go experiments

See `docs/research/EXPERIMENT_ROADMAP.md` for the full phase-by-phase gate
list; the immediate one is Phase 0 → Phase 1 → (re-evaluate Gate 0 on a
wider sample) → Phase 2, or the stopping path in trajectory doc §10 if
Gate 0 still does not clear after Phase 1.
