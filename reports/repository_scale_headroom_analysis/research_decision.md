# Research Decision: Should Preserve-vs-Repair Prediction Continue?

*Companion to `README.md`, `summary.json`, `evidence_table.csv`,
`per_query_effects.csv`, `per_query_aggregated_effects.csv`,
`headroom_by_regime.csv`, `predictability_upper_bounds.json` in this
directory. Produced by a repository-scale, offline-only meta-analysis
(`scripts/run_repository_scale_headroom_analysis.py`) — no new
experiments, no new LLM judgments, no network calls, no model training.
See `docs/research/RESEARCH_TRAJECTORY.md` for the narrative this decision
updates.*

---

## Phase 6 — Failure analysis of every prior selector attempt

Four attempts now exist in this repository's own history at a closely
related question ("can pre-repair signals decide whether to apply
repair?"). All four are compared here on the same axes.

| | **Attempt 1: `outputs/learned_selector/`** | **Attempt 2: `experiments/failure_class_audit_20260711_212157/`** | **Attempt 3: `src/consistency_ranker/repair_selector_mining/`** | **Attempt 4 (this document): repository-scale Gate 0** |
|---|---|---|---|---|
| **Goal** | Decide FAS-apply-or-not per query | Predict harm/help/non-neutral labels | Full repair-selector training pipeline (never run) | Determine whether headroom exists at all before any labeling/model work |
| **Features** | `bew_before, disagreement, n_sccs, cyclic_int` (4 features) | Unspecified feature set (not documented in the report itself) | `is_cyclic, largest_scc_frac, n_non_trivial_sccs, scc_cycle_burden_frac, n_mutual_pairs_frac, graph_density, vote_entropy, fas_removed_weight_frac, prior_top1_margin, prior_entropy, ranker_disagreement, greedy_exact_disagreement` (12 features) | `repair_cost, largest_scc_size, graph_density, is_cyclic, repair_algorithm, dataset, regime` (whatever each source table already exposes) |
| **Labels** | Binary: FAS beats RRF on NDCG@10 | `harm_label`, `help_label`, `any_non_neutral`, `extraction_insensitivity` | Regression + 4-threshold binary (`delta >= {0, 0.0025, 0.005, 0.01}`) | None trained — this attempt stops at the diagnostic (headroom) stage by design |
| **Models** | Logistic regression, shallow tree | Logistic, tree, random forest | logreg, shallow_tree, tree_depth4, random_forest, gradient_boosting, random_forest_calibrated | None (descriptive/statistical only: correlation, mutual information, ANOVA) |
| **Training data** | 300 queries, 3 datasets (FiQA/SciDocs/HotpotQA), 100 each | Not fully documented in the surviving report | Never executed — no training data was ever assembled through this pipeline | 122,203 rows / 419 distinct queries / 4 datasets / 76 source files (this analysis) |
| **Evaluation** | 60/20/20 split + leave-one-dataset-out | Train/test split, ROC-AUC, PR-AUC, balanced accuracy | Locked test split (grouped, leakage-safe), bootstrapped utility CI, oracle regret — designed but never run | Bootstrap CI on headroom (query-level, non-pseudo-replicated); univariate correlation, mutual information, ANOVA |
| **Negative controls** | **None** | **None** | **None** (not implemented even though the pipeline is otherwise rigorous) | Not applicable — no model was trained to control for |
| **Results** | Best fixed threshold (disagreement top-25%) beat both learned models overall; learned logistic won by +0.001 over the fixed threshold on HotpotQA under LODO only | ROC-AUC 0.83–0.88 (looks good) but PR-AUC only 0.09–0.33 (looks weak) — classic imbalanced-problem mismatch | No results — never run | Headroom is real (CI excludes zero) but ~8x below the field's own MDE; near-zero univariate predictive signal from every available covariate |
| **Why it likely failed** | Effect size too small for 4 coarse features and ≤300 queries to separate from noise | Same root cause, plus label imbalance inflating ROC-AUC while PR-AUC (the metric that matters under imbalance) stayed low | N/A (never tested) | This attempt does not "fail" in the modeling sense — it directly measures why 1–2 likely failed: the ceiling on what any model could achieve (headroom) is itself tiny |
| **Fundamental or implementation-related?** | **Fundamental**, given this document's headroom finding: even a perfect selector's ceiling (0.0025–0.0084 depending on slice) is smaller than what 4 coarse features could plausibly resolve from noise at n≤300 | **Fundamental**, same reason, compounded by class imbalance (an implementation-level issue that would remain even if the fundamental ceiling were higher) | Cannot be assessed empirically (never run), but the same fundamental ceiling applies to whatever it would have found | N/A — this is the diagnostic itself |

**Additional context, not a fifth attempt but cited for completeness**
(`papers/JDIQ_2026/CONTRIBUTION_AUDIT.md` line 103): a separate codebase
apparently ran a more developed replication and reached
`PROMISING_BUT_MORE_DATA_REQUIRED`, explicitly failing permutation/random-
feature controls — i.e., the one attempt that *did* include negative
controls also failed them. Out of scope for direct citation (different
repository), but directionally consistent with every finding in this
document.

**Synthesis:** all four independent looks at this question, spanning three
different research sessions, three different feature sets, and one
purpose-built rigorous pipeline, point the same direction. This is not one
inconclusive report — it is convergent evidence from methodologically
distinct attempts.

---

## Phase 7 — Research decision

### A. Should preserve-versus-repair prediction continue, as currently scoped?

**No.**

### B. If yes, why — N/A.

### C. If no, why

1. **The ceiling is below the noise floor the field itself established.**
   Query-level oracle headroom is 0.0025 (95% CI [0.0020, 0.0030], n=419
   independent queries) — even in the single most favorable slice found
   (BRIGHT, `ms1`, n=7,197 query-regime rows), headroom reaches only
   0.0084. The JDIQ manuscript's own power analysis
   (`reports/final_revision_task2_statistical_power_20260715/`) established
   a Holm-adjusted 80%-power minimum-detectable-effect of **0.0207** for
   this exact metric family. A perfect, error-free oracle predicting
   preserve-vs-repair correctly on every query would capture an effect
   roughly **8x smaller** than what this project's own prior work
   considers reliably detectable. No realistic imperfect classifier can
   exceed its oracle ceiling.
2. **Available pre-repair covariates carry negligible predictive signal.**
   Every numeric covariate tested — repair cost, largest-SCC size, graph
   density — has Pearson |r| < 0.04 against the repair effect (r² < 0.2%
   of variance explained), despite p-values below 0.0001 (a p-value this
   small at n>29,000 reflects sample size, not practical importance).
   `is_cyclic` (binary) shows Cohen's d = 0.034, roughly six times smaller
   than the conventional "small effect" threshold (0.2).
3. **Four independent prior attempts, three of them with real modeling
   effort, found the same thing.** See Phase 6. This is not a single
   inconclusive report; the failure is convergent and reproduced across
   different feature sets, different label definitions, and (in the
   externally-cited case) different codebases.
4. **The heterogeneity that exists is concentrated almost entirely in one
   already-known, already-observable variable: vote-construction regime.**
   `ms2` (near-acyclic) shows headroom of essentially exactly zero in all
   four datasets (0.0000009–0.0000093); `ms1` (high-cyclicity) accounts
   for nearly all of the already-small headroom that exists. This is not a
   new discovery requiring a learned model — it is already fully explained
   by a design choice (which vote-construction regime to use) that the
   mature program already controls and already reports on. A learned
   per-query selector would be trying to recover, query-by-query and with
   noisy features, a pattern that regime selection already captures in
   one categorical variable with a much larger effect.

### D. If uncertain, what single experiment would most reduce uncertainty — N/A given (C)

The evidence is not uncertain enough to warrant this branch of the
decision tree; (C) applies. For completeness, if a future researcher
believes a *different* formulation (not "more of the same") might still
have headroom, the one candidate reformulation this analysis cannot rule
out is:

> **Component/edge-level, not whole-graph, effect prediction.** This
> analysis measured whole-query, whole-graph, single-aggregate-metric
> headroom. It is possible that repair effects are large and predictable
> *within specific strongly-connected components or specific edges* even
> while the whole-query nDCG effect averages out to something tiny (a
> large local effect on a few ranks deep in the list can have a small
> whole-list nDCG@10 footprint). This is a **materially different research
> question**, not a continuation of the current one, would need new
> per-component/per-edge outcome data (not available in any source table
> found in this analysis), and should be proposed and gated on its own
> terms — not used to justify continuing the current, now-refuted,
> whole-graph formulation.

## Recommendation

**Stop pursuing whole-graph, aggregate-metric preserve-vs-repair
prediction as a primary research direction.** Do not proceed to Phase 1
(widening the sample) or Phase 2 (feature/label freezing) of
`docs/research/EXPERIMENT_ROADMAP.md` for this formulation — this
document supersedes that roadmap's "next step" for the reasons in Phase 7
above. `docs/research/RESEARCH_TRAJECTORY.md` and
`docs/research/EXPERIMENT_ROADMAP.md` should be updated to record this
outcome (tracked as a follow-up, not done automatically by this analysis,
to avoid silently rewriting a document that itself records a decision
history — see `docs/research/DECISION_LOG.md`'s own convention of
appending, not silently editing).

The manuscript's existing negative result stands and is now *reinforced*,
not merely unchallenged: this analysis is additional, convergent evidence
that the repair-effect signal is small at every level of granularity
tested so far (aggregate: null; per-query: real but far below the noise
floor). The honest, citable framing is a **strengthened negative result**:
"structural inconsistency reduction is a poor proxy for downstream ranking
improvement, the effect is not recoverable through per-query selection
either at the whole-graph level, and the small headroom that does exist is
already explained by vote-construction regime, a variable the project
already controls."

## Exact go/no-go conclusion

**NO-GO** on preserve-vs-repair predictive-model development, whole-graph
formulation, current feature set. **GO** (as a separate, smaller, clearly
scoped decision) on writing up the strengthened negative result, since
that is now well-evidenced and citable. **UNDECIDED, not GO**, on the
component/edge-level reformulation (Phase 7-D) — it has not been evaluated
by this analysis and would require its own Gate-0-equivalent pass on new
per-component outcome data before any investment.
