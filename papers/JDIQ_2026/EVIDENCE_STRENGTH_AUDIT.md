# Evidence Strength Audit

> **PARTIALLY SUPERSEDED (as of 2026-07-14).** This audit's "H7" analysis
> treats the six-class failure taxonomy as central corroborating evidence.
> The finished manuscript's Limitations section subsequently excluded that
> taxonomy as evidence entirely (counts were never regenerated under the
> primary normalized protocol). Read H7 and any dependent conclusions here
> as historical, not current.

**Prepared:** 2026-07-12
**Objective:** For every major scientific conclusion in `main.tex`, enumerate every independent piece of repository evidence, classified by methodology (not merged within an experiment), and assess whether the manuscript's confidence in each conclusion is proportionate to the diversity of evidence behind it. This is an evaluative audit, not a writing task — no manuscript changes were made.

**Convention:** Each evidence table lists everything found in the repository, whether or not it is currently cited in `main.tex`. Rows marked **[not cited]** exist in the repository but are absent from the current manuscript text; this is noted explicitly because it matters for questions D/E/H below and for the coverage matrix, which is repository-wide rather than manuscript-only.

---

## H1. Vote-extraction/construction regime, not repair, is the dominant driver of preference-graph inconsistency

| Supporting evidence | Repository location | Methodology | Independent? | Strength |
|---|---|---|---|---|
| Cyclic%/largest-SCC by dataset × regime, 4 datasets, identical underlying scores | `outputs/pub_vote_cmp_all4/.../table_graph_ndcg_and_consistency.csv`; `main.tex` Table 4 | Controlled regime sweep on fixed ranker scores | — (single design, replicated across 4 datasets) | Strong |
| Real-LLM cyclicity also varies sharply by dataset (92.0/80.0/10.0%) | `outputs/openai_real_llm_cross_dataset_summary.md`; `main.tex` Table 8 | Real-LLM pairwise judgments, single regime per dataset | Yes (different vote source) | Weak — corroborates that cyclicity is vote-source-sensitive in general, but does not sweep regime, so it only tangentially supports "regime is the *dominant* lever" |
| Regime-retention-rule mechanism (Eq. 1) | `main.tex` §3.1 | Definitional/mechanical argument (mutual-direction retention under `ms1` structurally permits cycles that `ms2`'s majority-support threshold precludes) | Yes (theoretical, not empirical) | Strong as an explanatory mechanism, not as independent empirical confirmation |

**Assessment: one empirical methodology** (the regime sweep itself), replicated across four datasets but not independently re-derived by a second method (e.g., a synthetic threshold-sensitivity experiment does not exist in the repository despite `synthetic_data.py` being available for exactly this kind of controlled test).

---

## H2. FAS repair reliably improves structural consistency (BEW/PIC) when the graph is cyclic

| Supporting evidence | Repository location | Methodology | Independent? | Strength |
|---|---|---|---|---|
| Mean ΔBEW/ΔPIC before/after repair, `ms1`, 4 datasets | `table_consistency_qrels_bew.csv`; `main.tex` Table 5 | Structural-diagnostic measurement against a qrels-derived reference ranking | — | Strong, but explicitly qrels-anchored (circularity caveat already stated in `main.tex` §5 and §12) |

**Assessment: one methodology only.** No independent structural diagnostic (e.g., against a reference ranking *not* derived from the same relevance judgments used for nDCG) exists to corroborate this claim free of the disclosed circularity. The manuscript's own caveat is the correct mitigation given this gap, not a missing action item — but the claim's evidential base is narrower than its "reliably" language might suggest to a reader who doesn't reach the caveat.

---

## H3. Structural improvement does not reliably translate into downstream retrieval-quality improvement (the central decoupling claim)

| Supporting evidence | Repository location | Methodology | Independent? | Strength |
|---|---|---|---|---|
| Bootstrap ΔnDCG, repaired vs. unrepaired hybrid, 24 cells | `table_bootstrap_delta_ndcg.csv`; `main.tex` Table 5/Fig. 4 | Paired percentile bootstrap, mechanical votes, vote-suite protocol | — | Strong |
| Pooled baseline ranking, 1,020-record corpus, separate query pool | `final_baseline_comparison.csv`; `main.tex` Table 6 | Mean-nDCG ranking comparison, failure-mining protocol | Yes (different protocol, different query population, different statistic) | Strong (see note below on missing CIs) |
| Exact-vs-greedy solver-strength ablation | `experiments/final_method_gap_audit_20260711_221113/task2/`; `main.tex` §6.3 | Bootstrap-paired comparison across repair-procedure strength, not repair-presence | Yes (different design axis) | Strong |
| Real-LLM bootstrap, OpenAI, 3 datasets | `outputs/openai_real_llm_cross_dataset_summary.md`; `main.tex` Table 8 | Bootstrap on a qualitatively different preference-generation process | Yes | Moderate (small n, one provider) |
| Manual 6-class failure taxonomy | `MANUAL_FAILURE_TAXONOMY_REPORT.md`; `main.tex` Table 7 | Categorical/manual classification, not a continuous statistic | Yes | Strong |
| **[not cited]** Oracle-regret decomposition (repair-choice ≈ 3.6% of gap) | `REGRET_DECOMPOSITION_REPORT.md` | Regret/attribution decomposition against an oracle policy | Yes | Strong |
| **[not cited]** Adversarial counterfactual-generation feasibility (0% non-neutral yield, validated protocol) | `experiments/counterfactual_generation_feasibility_/corrected_run/` | Constructive/adversarial stress-test, not observational | Yes | Strong |
| **[not cited]** Second real-LLM provider (Cohere/Azure), full BRIGHT coverage | `reports/failure_mining_llm_v3/` | Real-LLM bootstrap-style comparison, second provider stack | Yes | Moderate |

**Assessment: five independent methodologies currently cited, three more available and unused.** This is, by a wide margin, the best-triangulated conclusion in the repository (see G below). One caveat: Table 6's point estimates (0.462, 0.459, 0.457, 0.455, 0.455...) carry **no confidence intervals or significance test**, unlike every other quantitative claim in the paper — the pooled-baseline ranking is evidentially real but not formally uncertainty-quantified the way the paper's other bootstrap-based claims are, despite the bootstrap machinery being available and used elsewhere in the same study.

---

## H4. The one reliable positive effect (HotpotQA, `ms1`) is not explained by cyclicity severity, and is the clearest open question

| Supporting evidence | Repository location | Methodology | Independent? | Strength |
|---|---|---|---|---|
| Bootstrap CI, HotpotQA `ms1`, n=52 | `table_bootstrap_delta_ndcg.csv`; `main.tex` Table 5 | Same bootstrap methodology as H3 | — (this *is* one cell of H3's evidence, not a separate confirmation) | Weak |
| Cross-table comparison: HotpotQA has the *lowest* `ms1` cyclicity of the four datasets | `main.tex` Tables 4 and 5, juxtaposed | Observational cross-reference within the same experiment | No — same underlying data | Weak |
| Real-LLM HotpotQA (`ms1`-equivalent, n=20) shows Δ = 0, degenerate | `main.tex` Table 8 | Real-LLM bootstrap | Yes, but **does not replicate** the mechanical-vote positive effect — this is a non-confirming, not confirming, independent data point | N/A (complicating, not supporting) |

**Assessment: this hypothesis is supported by essentially one data point** (n=52, one dataset, one regime), and the one independent check available (real-LLM HotpotQA) does not replicate it. The manuscript is already appropriately conservative here ("we do not have a confirmed explanation... we flag this as the clearest open question this study raises rather than resolves"), which is the correct posture given how thin the evidence is — but it is worth being explicit that this is the paper's single positive empirical result, and it is also its least-replicated one.

---

## H5. Simple, structure-blind aggregation baselines (CombSUM, RRF, prior-only) are competitive with or superior to repaired graph-hybrid methods

| Supporting evidence | Repository location | Methodology | Independent? | Strength |
|---|---|---|---|---|
| Pooled mean-nDCG ranking, Table 6 | `final_baseline_comparison.csv`; `main.tex` Table 6 | Mean-nDCG ranking, pooled 1,020-record corpus | — | Strong direction, but no CIs (see H3 note) |
| **[not cited]** Independent re-derivation via the `failure_mining` exploratory pipeline (separate codebase path) also finds Borda/CombSUM beating the repaired method across several regimes | `reports/failure_mining/`, `reports/failure_mining_llm_v3/` | Same conceptual comparison, different implementation/pipeline, overlapping but not identical query handling | Partially (different code path, likely overlapping query population) | Moderate |

**Assessment: one methodology currently cited**, with a second, weaker-independence replication (different implementation, same general query pool) available in the repository but unused. Combined with the missing-CI issue noted under H3, this conclusion — arguably the paper's second-most load-bearing claim after H3 — currently rests on the least formally uncertainty-quantified evidence in the entire study.

---

## H6. Stronger/exact repair does not change the retrieval conclusion

| Supporting evidence | Repository location | Methodology | Independent? | Strength |
|---|---|---|---|---|
| Exact-for-small-components vs. greedy, full 1,020-record corpus, bootstrap CI | `experiments/final_method_gap_audit_20260711_221113/task2/`; `main.tex` Table `repair-variants`, §6.3 | Bootstrap-paired solver-strength ablation | — | Strong |
| Bounded robustness check against further exact/metaheuristic solvers, fixed sample, qualitative only | Author-maintained external package (withheld from citation for anonymity); `main.tex` §6.3, reported qualitatively | Different solver family, same comparison structure | Yes | Weak (no quantitative disclosure in the anonymous version) |

**Assessment: two methodologies**, one strong and quantitative, one real but currently undisclosed beyond a qualitative sentence for anonymity reasons. The quantitative one alone is already sufficient to support the claim as stated; the qualitative one is a bonus corroboration, appropriately hedged.

---

## H7. The six-class failure taxonomy explains, mechanistically, why repair is inactive/neutral/harmful

| Supporting evidence | Repository location | Methodology | Independent? | Strength |
|---|---|---|---|---|
| Manual 6-class taxonomy, 1,020 records | `MANUAL_FAILURE_TAXONOMY_REPORT.md`; `main.tex` Table 7 | Expert/manual categorical labeling | — | Strong |
| Counterfactual "no-repair is the minimal fix for every harmful case" | `COUNTERFACTUAL_REPAIR_REPORT.md`; `main.tex` §7 | Counterfactual/minimal-intervention analysis | Yes | Strong |
| **[not cited]** Unsupervised GMM clustering recovers 2 stable macro-clusters mapping onto repair-inactive/tail-only (silhouette 0.348) | `AUTOMATIC_FAILURE_CLASS_REPORT.md` | Unsupervised statistical clustering, no manual labels used | Yes | Moderate |

**Assessment: two methodologies currently cited**, a third (unsupervised corroboration of the manual taxonomy's structure) available and unused. Adding it would move this from category B to category C and would pre-empt a natural reviewer question ("was the taxonomy just fit to the data?").

---

## H8. Fusion suppression is a real mechanism (14.7% overall rate, range 4.8–26.4% by component/mode)

| Supporting evidence | Repository location | Methodology | Independent? | Strength |
|---|---|---|---|---|
| Graph-ranking-change-vs-fused-ranking-change comparison | `extraction_fusion_complete.csv`; `main.tex` §7 | Per-query-method comparison of pre/post-fusion ranking changes | — | Moderate |

**Assessment: one methodology, no independent confirmation, and no confidence interval reported** on the 14.7% figure itself (a rate with no stated denominator uncertainty). This is a secondary mechanism claim, not a headline conclusion, so a single-methodology basis is less concerning than it would be for H1–H6, but it is worth noting it is evidentially the thinnest *named, numbered* finding in the Discussion.

---

## H9. The regime-conditional decoupling pattern persists under genuine real-LLM preferences

| Supporting evidence | Repository location | Methodology | Independent? | Strength |
|---|---|---|---|---|
| OpenAI real-LLM pairwise pilot, 3 datasets (10–50 queries each) | `outputs/openai_real_llm_cross_dataset_summary.md`; `main.tex` Table 8 | Bootstrap CI, single LLM provider | — | Moderate |
| **[not cited]** Cohere + Azure real-LLM data, 4 datasets incl. full BRIGHT coverage | `reports/failure_mining_llm_v3/` | Same conceptual test, second provider stack, different codebase path | Yes | Moderate |

**Assessment: one methodology/provider currently cited; a second, independent provider stack with broader dataset coverage (including the one dataset the manuscript states has no real-LLM pilot) exists unused.** This is the clearest case in the whole audit of a conclusion resting on a single evidence source when a second, independent one is already sitting in the repository (see D and E below).

---

## H10. No validated predictive selector exists for deciding, in advance, whether repair will help

| Supporting evidence | Repository location | Methodology | Independent? | Strength |
|---|---|---|---|---|
| Assertion only, no cited quantitative table | `main.tex` §11/§12 (prose only) | — | — | **None cited** |
| **[not cited]** Learned selector vs. fixed-threshold baselines (accuracy 0.48–0.57, precision 0.18–0.19; fixed thresholds beat the learned model) | `outputs/learned_selector/LEARNED_SELECTOR_REPORT.md` | Supervised classification vs. fixed-rule baselines, held-out evaluation | Yes | Strong (as a negative result) |
| **[not cited]** Failure-pattern prediction (ROC-AUC 0.83–0.88 undermined by PR-AUC 0.15–0.33, precision 0.13–0.30, feature importances self-suppressed after failing permutation controls) | `FAILURE_PATTERN_PREDICTION_REPORT.md` | Supervised classification with explicit permutation-control falsification | Yes | Strong (as a negative result) |

**Assessment: the manuscript currently cites zero methodologies for a claim it makes confidently**, despite two independent, methodologically serious negative results (with proper holdout splits and, in one case, permutation-control falsification) already existing in the repository. This is the single largest mismatch in the entire audit between how a claim is stated (a bare assertion) and how well it could be supported (two rigorous negative results) if the existing evidence were simply cited.

---

## H11. Efficiency: greedy repair is near-zero cost; exact-for-small-components adds modest overhead without retrieval benefit

| Supporting evidence | Repository location | Methodology | Independent? | Strength |
|---|---|---|---|---|
| Wall-clock/RSS instrumentation, single machine, full corpus | `experiments/final_method_gap_audit_20260711_221113/task2/`; `main.tex` §9 | Direct runtime/memory measurement | — | Moderate (explicitly and appropriately self-caveated in the manuscript as single-machine, coarse) |
| Synthetic dense-graph runtime scaling study | mentioned in `main.tex` §9 as existing but explicitly **not** treated as evidence about the real pipeline | Synthetic/controlled scaling experiment | Yes, but manuscript correctly declines to use it as corroboration | N/A (deliberately excluded) |

**Assessment: one methodology, appropriately scoped and caveated already.** This is a secondary, low-stakes claim; single-methodology support here is fine given its already-modest framing.

---

## Answers to the audit questions

### A. Hypotheses supported by only one methodology
H1 (construction dominates cyclicity — one empirical design, replicated across datasets, not independently re-derived), H2 (BEW/PIC improvement — one qrels-anchored diagnostic), H5 (simple baselines win — one cited methodology; a second exists unused), H8 (fusion suppression — one uncorroborated rate), H9 (real-LLM generalization — one provider cited; a second exists unused), H11 (efficiency — appropriately scoped as secondary).

### B. Hypotheses supported by two independent methodologies
H6 (exact-vs-greedy quantitative + qualitative external-solver corroboration), H7 (manual taxonomy + counterfactual minimal-fix analysis; a third, unsupervised-clustering corroboration exists unused).

### C. Hypotheses supported by three or more independent methodologies
H3 only — the central decoupling claim, with five methodologies currently cited (mechanical bootstrap, pooled-baseline ranking, solver-strength ablation, real-LLM bootstrap, failure taxonomy) and three more available unused (regret decomposition, adversarial counterfactual generation, second real-LLM provider).

### D. Where existing analyses could be cross-referenced to reinforce one another
- H1 (regime drives cyclicity) ↔ the unused regret decomposition's ~91%/76.6% construction-attributed share of the oracle gap — same conclusion, two measurements, never connected in text.
- H7's manual taxonomy ↔ the unused unsupervised GMM clustering — same classification conclusion via independent methods.
- H9's OpenAI real-LLM pilot ↔ the unused Cohere/Azure real-LLM data — same hypothesis, second provider, currently siloed.
- H10's bare assertion ↔ the unused learned-selector and failure-pattern-prediction reports — the claim already has evidence; it just isn't cited.
- H7's counterfactual minimal-fix analysis ↔ the unused adversarial counterfactual-generation feasibility check — both are "counterfactual" methodology but investigate different questions (retrospective minimal fix vs. prospective adversarial construction); connecting them would turn two separate counterfactual analyses into one clearly triangulated argument.

### E. Which existing experiment is carrying too much weight because no independent confirmation exists
**H9's real-LLM generalization claim** is the clearest case: the entire "this isn't a mechanical-vote artifact" argument — the single most common objection a reviewer would raise against this study's main mechanical-vote design — rests on one provider (OpenAI), three datasets, 10–50 queries each. A second, independent provider stack with broader coverage already exists unused. Close second: **H4's HotpotQA anomaly**, the paper's only positive result, resting on n=52 from a single dataset/regime cell, with the one independent check available (real-LLM HotpotQA) failing to replicate it.

### F. Redundant repository results confirming something already strongly established
- H6's qualitative external-solver check adds little beyond the already-decisive quantitative exact-vs-greedy result; it could be omitted with negligible evidentiary loss (though its current disclosure is honest and low-cost, so removing it is not necessary).
- The two independent RankCentrality-style code implementations (power-iteration vs. PageRank-damped) are redundant with each other at the implementation level — this is code duplication, not evidentiary value, and doesn't strengthen any hypothesis twice over.
- The sequence of self-assessment audits (`reviewer_response_state_audit`, `publication_readiness_audit`) restate conclusions already established by `final_method_gap_audit`/`failure_class_audit` without new data — correctly excluded from the manuscript already.

### G. Strongest evidential support in the entire repository
**H3, the central decoupling claim.** Five independently cited methodologies (mechanical bootstrap across 24 cells, a separately-protocoled pooled-baseline comparison, a solver-strength ablation, real-LLM validation, and a manual failure taxonomy), with three further independent methodologies (regret decomposition, adversarial counterfactual generation, a second real-LLM provider) sitting unused in reserve. No other conclusion in the study comes close to this depth of triangulation.

### H. Scientifically important but comparatively under-supported
**H4, the HotpotQA anomaly**, is the sharpest case: it is the paper's only positive empirical result and its most reviewer-attention-grabbing finding, yet it rests on the thinnest evidence (n=52, one cell, non-replicated under real-LLM judgments). **H10, the no-selector claim**, is a close second: conceptually important (it forecloses the natural next research question) but currently supported by zero cited evidence despite two rigorous negative results existing in the repository.

---

## Evidence Coverage Matrix

Coverage reflects the full repository (cited or not); cells marked with `*` indicate the manuscript currently cites less than what the repository actually contains (see per-hypothesis notes above for detail).

| Conclusion | Benchmark | Synthetic | Real LLM | Counterfactual | Regret decomp. | Failure taxonomy | Statistical | Robustness | Multi-dataset | Multi-provider | Theoretical |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 Construction dominates cyclicity | Strong | None | Partial | None | Strong* | None | Partial | Partial | Strong | None | Strong |
| H2 Repair improves BEW/PIC | Strong | None | None | None | None | None | Partial | Partial | Strong | None | Partial |
| H3 Central decoupling claim | Strong | None | Strong* | Strong* | Strong* | Strong | Strong | Strong | Strong | Partial* | Strong |
| H4 HotpotQA anomaly | Partial | None | None (non-replicating) | None | None | None | Partial | None | None | None | None |
| H5 Simple baselines win | Strong | None | Partial* | None | None | None | Partial (no CIs) | Partial* | Strong | None | None |
| H6 Exact repair ≈ greedy | Strong | None | None | None | Partial | None | Strong | Strong | Strong | None | Strong |
| H7 Failure taxonomy mechanisms | Strong | None | None | Strong | None | Strong | Partial | Strong* | Strong | None | Partial |
| H8 Fusion suppression | Partial | None | None | None | None | Partial | Partial | None | Partial | None | Partial |
| H9 Real-LLM generalization | None (n/a) | None | Strong* | None | None | None | Strong | Partial* | Strong* | Partial* | None |
| H10 No validated selector | None* | None | None | None | None | None | None* | None* | None* | None | None |
| H11 Efficiency | Moderate→Partial | Partial (excluded by design) | None | None | None | None | Partial | None | Partial | None | None |

---

## If I were an Associate Editor

**I would immediately trust:** H3 (central decoupling claim), H6 (stronger repair doesn't change the conclusion), and H7 (failure taxonomy mechanisms). Each rests on multiple independent methodologies, at least one of which is a full-corpus, bootstrap-quantified result, and the paper's own caveats around them are already appropriately conservative.

**I would ask the authors to strengthen, before publication, using evidence that already exists in their own repository (no new experiments required):**
1. **H9 (real-LLM generalization)** — cite the second provider's data (`reports/failure_mining_llm_v3/`) to remove the single-provider dependency, particularly since it already covers the one dataset (BRIGHT) the manuscript states has no real-LLM pilot.
2. **H10 (no validated selector)** — cite the two existing negative results (`LEARNED_SELECTOR_REPORT.md`, `FAILURE_PATTERN_PREDICTION_REPORT.md`) rather than asserting the claim without evidence; this is a strictly stronger, more citable version of the same conservative conclusion.
3. **H5 (simple baselines win)** — add confidence intervals or a significance test to Table 6's point estimates; the bootstrap infrastructure used everywhere else in the paper is available and would resolve whether CombSUM (0.462) is genuinely distinguishable from prior-only (0.457) or the hybrid (0.455), not merely numerically larger.
4. **H4 (HotpotQA anomaly)** — no new evidence exists to strengthen this, and I would not ask for new experiments; I would only ask that the paper's already-appropriate hedging ("clearest open question... rather than resolves") be left exactly as conservative as it currently is, since this is the one conclusion in the paper that cannot currently be made stronger without new data collection.
