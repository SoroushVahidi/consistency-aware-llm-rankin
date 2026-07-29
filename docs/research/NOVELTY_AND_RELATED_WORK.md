# Novelty and Related-Work Map: Preserve vs. Repair vs. Re-query

*Companion to `docs/research/RESEARCH_TRAJECTORY.md`. This document exists
to prevent an overclaim. Every citation below is either (a) already
referenced in this repository's own prior related-work notes
(`docs/related_work_positioning_note.md`, `docs/LITERATURE_ALIGNMENT.md`,
dated 2026-04-06, covering classical rank-aggregation literature — Dwork,
Ailon-Charikar-Newman — not LLM-judge-specific work), or (b) named by the
task that produced this document as a paper to check. **None of the
LLM-judge-era citations below (PRP-Graph, LLM-RankFusion, TrustJudge,
AcuRank, GNNRank, "Active Learners as Efficient PRP Rerankers," "Learning
to Defer in Ranking Systems," etc.) have been independently verified
against a live bibliography, arXiv, or publisher record by this
repository's own tooling — no live web/API lookups were made while writing
this document (offline-only constraint). Treat every such citation as
"requires literature verification" until an agent or researcher with web
access confirms the exact venue, year, and claim.**

## What must not be claimed

- That any of the eight categories below, individually, is novel to this
  project. They are not; substantial prior work exists in every one.
- That the "selective consistency management" formulation (bottom of this
  document) has been confirmed novel by a professional literature review.
  It has not. It is a hypothesis about a gap, stated for the first time in
  this repository in this document, pending verification.
- That any citation's bibliographic metadata (exact venue, year, author
  list) below is confirmed. Several are given as they were named by the
  task/prior conversation context; they are placeholders for verification,
  not confirmed references.

## Related-work categories

### 1. LLM pairwise reranking and preference-graph aggregation
Directly implemented and cited in this repository already
(`docs/related_work_positioning_note.md`): Pairwise Ranking Prompting
(Qin et al., 2023, cited and implemented as `llm_pairwise`), Bradley-Terry
MLE, Markov-chain/PageRank aggregation (Dwork et al., 2001, cited and
partially implemented as a local-Kemenization baseline). Additional
named-for-verification: **PRP-Graph**, **LLM-RankFusion** — status:
*requires verification* (not found cited anywhere in this repository as of
this document).

### 2. LLM-as-a-judge non-transitivity
This repository's own graph-construction/cycle-detection work is itself
evidence that non-transitivity is real and measured (E1 in the superseded
`docs/EVIDENCE_MAP.md`: cyclicity ranges from 1.68% to 97.5% of graphs
depending on vote construction). Named-for-verification: **"Investigating
Non-Transitivity in LLM-as-a-Judge"**, **TrustJudge** — status: *requires
verification*.

### 3. Preference-graph denoising and acyclicity enforcement
This is squarely what the mature program's FAS repair already does (§2 of
the trajectory doc). Named-for-verification: **GED / "Preference Graph
Ensemble and Denoise"** — status: *requires verification*; if the acronym
expansion above is wrong, the citation should be dropped rather than
guessed at.

### 4. Feedback-arc-set and Kemeny-style ranking
Already covered in depth by `docs/LITERATURE_ALIGNMENT.md` §0.1–0.3:
Dwork et al. (2001) and Ailon-Charikar-Newman (2008) are cited, compared,
and distinguished from this repository's own prior MWFAS-ranking paper
(cited as "our prior MWFAS ranking paper" in that document — full
bibliographic details not reproduced here; see the source document).

### 5. Active ranking and adaptive comparison acquisition
This is the closest category to the "re-query" extension (roadmap doc
Phase 4). Named-for-verification: **"Active Learners as Efficient PRP
Rerankers"**, **AcuRank** — status: *requires verification*. This
repository's own `adaptive_acquisition/` and `active_acquisition/`
packages (a separate, already-audited pivot — see `PROJECT_STATUS.md`)
are directly relevant prior art **within this repository** for what
active/adaptive pairwise acquisition looks like in this codebase's own
style, including a documented negative result (the active pair-selection
proposal there lost to random selection) — any re-query design in Phase 4
should read that pivot's own audit before designing new acquisition
heuristics, to avoid repeating a documented mistake.

### 6. Uncertainty-aware adaptive reranking
Overlaps with category 5. No specific additional citation named for
verification beyond those above.

### 7. Learned ranking from comparison graphs
Named-for-verification: **GNNRank** — status: *requires verification*.
Directly relevant to the roadmap doc's explicit gating of GNN-based models
behind tabular baselines (Phase 3) — if GNNRank or similar work already
does per-query, per-graph learned ranking well, it is a candidate *later*
model class, not evidence that this project's simpler tabular-baseline-
first approach is already obsolete; the two questions (rank the items vs.
predict the repair *action*) are related but not identical.

### 8. Learning to defer, algorithm selection, and intervention-value prediction
This is the closest category to the actual research question (§5 of the
trajectory doc: predict per-query whether an intervention — repair — helps
or harms). Named-for-verification: **"Learning to Defer in Ranking
Systems"**, and unspecified "relevant uplift or intervention-ranking
work" — status: *requires verification*. This repository's own Outcome F
policy-selection package (`policy_selection/`) is the closest **internal**
prior art for this category — see the trajectory doc §2 for its result
(oracle headroom existed, no learned gate realized it) and §9/roadmap doc
Phase 3 for how its infrastructure is reused, not duplicated, here.

## Potentially novel gap (hypothesis, not established)

> Existing work (categories 1–7 above, to the extent verified) detects,
> aggregates, denoises, or mitigates inconsistent LLM preferences, but
> does not appear — based on this repository's own related-work notes and
> the categories above, **not** a verified professional literature
> search — to predict, per retrieval query, whether enforcing consistency
> through graph repair will improve downstream ranking quality, using only
> pre-repair, pre-outcome signals.

Cautious language required in any external-facing use of this claim:
"potentially novel," "no direct prior work identified [within this
repository's review]," "requires further literature verification," "novel
only under the precise per-query intervention-utility formulation," never
"we have established novelty" or "this is a novel contribution" without
the qualifiers above.

A stronger, later formulation (also unverified, also requires the same
qualifiers):

> **Selective consistency management for LLM-derived preference graphs**:
> use pre-intervention graph and uncertainty signals to choose whether to
> preserve the graph, repair it, or acquire additional evidence.

## Internal prior-art table (verified directly from this repository, not literature)

| What | Where | Verdict |
|---|---|---|
| Repair reliably improves structural consistency | `outputs/pub_vote_cmp_all4/paper_package/` | Established positive |
| Repair does not reliably move nDCG (0/60 Holm-significant, canonical) | `papers/JDIQ_2026/manuscript/main.tex` | Established negative |
| Exact ILP repair does not rescue the conclusion (0/36, 0/56) | Same | Established negative |
| Oracle acquisition-policy selector beats fixed default by 0.1965; no learned gate realizes it | `reports/policy_selection_20260726T030500Z/decision.json` | Established negative (adjacent program) |
| Learned FAS-apply-or-not selector vs. fixed disagreement threshold | `outputs/learned_selector/LEARNED_SELECTOR_REPORT.md` | Negative (fixed threshold wins) |
| Harm/help/non-neutral prediction: high ROC-AUC, low PR-AUC | `experiments/failure_class_audit_20260711_212157/phase_reports/FAILURE_PATTERN_PREDICTION_REPORT.md` | Weak/inconclusive |
| Rigorous repair-selector pipeline (leakage-safe, bootstrapped, oracle-regret) | `src/consistency_ranker/repair_selector_mining/` | Built, never run in this repo |
| Independent, more developed replication (separate codebase, cited for context only) | Referenced in `papers/JDIQ_2026/CONTRIBUTION_AUDIT.md` line 103 | `PROMISING_BUT_MORE_DATA_REQUIRED`, failed permutation/random-feature controls |
| Oracle-headroom gate-0, real run, this document's own pass | `reports/oracle_headroom_gate0_20260728T230000Z/` | No slice cleared the gate; 3/4 `AMBIGUOUS`, 1/4 `NO_HEADROOM` |

This table is the actual evidentiary basis for the novelty hedge above:
the internal record shows repeated, independent attempts at a closely
related question landing on "no" or "not yet," which is exactly why any
external novelty claim must stay conditional until a genuinely new,
properly-controlled attempt (roadmap doc Phase 3) either succeeds or adds
one more rigorous negative data point.
