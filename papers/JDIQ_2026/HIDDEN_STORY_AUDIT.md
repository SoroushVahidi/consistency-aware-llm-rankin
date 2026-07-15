# Hidden-Story Audit: Area-Chair Read of the Repository, Manuscript Unseen

> **PARTIALLY SUPERSEDED (as of 2026-07-14).** Built on `CONTRIBUTION_AUDIT.md`
> (itself now partially superseded -- see its banner) and includes a draft
> abstract citing the six-class failure taxonomy as central evidence, which
> the finished manuscript's Limitations section subsequently excluded.
> Read as historical repository-exploration context, not as a description
> of the current manuscript's actual framing.

**Prepared:** 2026-07-12
**Method:** Reasoning from the raw repository evidence already assembled in `CONTRIBUTION_AUDIT.md` (file paths and numbers re-cited below), deliberately bracketing the manuscript's own framing, title, and abstract while doing so. No new repository exploration was needed — this is a synthesis/judgment pass over facts already verified.

---

## 1. Results that would surprise a cold reader

- **A single threshold change flips graph cyclicity from 0% to up to 95% of queries, using the identical underlying ranker scores** (`table_graph_ndcg_and_consistency.csv`: `ms2` 0.0% cyclic on every dataset vs. `ms1` 51.9–95.0%). The "inconsistency" this paper studies is overwhelmingly a construction-rule artifact, not an intrinsic property of the rankers or the data.
- **The one dataset where repair reliably helps (HotpotQA, `ms1`) is the *least* cyclic of the four** (51.9% vs. 60–95% for the others; `table_bootstrap_delta_ndcg.csv`). The naive dose-response story — more inconsistency, more room for repair to help — is directly falsified by the paper's own best result.
- **Solving the repair objective exactly instead of greedily changes retrieval outcome by essentially nothing** (paired Δ = −0.0000358, 95% CI [−0.000107, 0.0], `experiments/final_method_gap_audit_20260711_221113/task2/`). This rules out "the heuristic wasn't good enough" as an explanation for the null results — a much stronger claim than most repair papers can make.
- **An oracle-regret decomposition attributes only ~3.6% of the achievable quality gap to which repair procedure is chosen, versus ~91% to missing candidate information** (`REGRET_DECOMPOSITION_REPORT.md`, `experiments/failure_class_audit_20260711_212157/`). This is the single most surprising number in the repository: it says the entire object of study — repair — is a minor lever next to upstream retrieval/candidate-generation quality.
- **Decades-old, structure-blind fusion methods (CombSUM 1994, RRF 2009) beat every graph-based method tested**, including every repaired hybrid (`final_baseline_comparison.csv`, Table 6). Structural sophistication is a net cost here, not a benefit.
- **A deliberate, adversarial attempt to manufacture scenarios where repair matters still produced a 0% non-neutral outcome rate under a validity-checked protocol** (`experiments/counterfactual_generation_feasibility_/corrected_run/`). The authors tried to break their own null result on purpose and could not.
- **A trained "should I repair?" selector performs worse than a two-line heuristic rule** (accuracy 0.48–0.57, precision 0.18–0.19, `outputs/learned_selector/LEARNED_SELECTOR_REPORT.md`) — machine learning applied to the most natural follow-up question in this line of work loses to "if cyclic and SCC ≥ 2."
- **The one real-LLM condition with a statistically confident effect is negative, not positive** (SciDocs, real OpenAI judgments, Δ = −0.0010, CI [−0.0019, −0.0002], `outputs/openai_real_llm_cross_dataset_summary.md`). Under genuine LLM preferences, the paper's only non-null real-LLM finding cuts against repair, not for it.

## 2. Negative results that are actually scientifically valuable

Ranked by how directly they close off an objection a reviewer would otherwise raise:

1. **Exact-vs-greedy indistinguishability** — closes off "your heuristic was the problem."
2. **Simple baselines beating all graph methods** — closes off "maybe repair just needs better fusion/extraction."
3. **Counterfactual-generation 0% yield** — closes off "you just didn't sample the right queries"; this is a constructive, not merely observational, null.
4. **Learned-selector failure** (`outputs/learned_selector/`, `FAILURE_PATTERN_PREDICTION_REPORT.md`: ROC-AUC 0.83–0.88 undermined by PR-AUC 0.15–0.33 and self-suppressed feature importances after failing permutation controls) — closes off "surely you can at least predict when it'll help," with actual holdout and permutation-control rigor behind the "no" answer.
5. **Regret decomposition** — closes off "maybe repair matters more than the headline retrieval numbers suggest," by directly quantifying "at most."

All five are currently used in the manuscript only as a single asserted sentence ("modest, non-decisive signal") or, for #3 and #5, not used at all. Every one of them is a *stronger* negative result than its current billing.

## 3. Diagnostics that deserve headline status

- **The regret decomposition** is the strongest candidate for elevation. It is the one number in the entire repository that answers "how much does this paper's subject matter, at most?" directly and quantitatively, and it says: not much. This deserves to sit next to the central decoupling result, not to remain an unused side-analysis.
- **The fusion-suppression rate** (14.7%, range 4.8–26.4%, already in §7 but as one paragraph) is a transferable systems-design insight beyond this narrow pipeline: fixed-weight fusion of a structural signal into a prior score can silently absorb a genuine structural change before it reaches the final ranking. This generalizes to any hybrid/ensemble reranker, not just FAS repair, and is under-sold relative to its generality.
- **The construction-vs-repair magnitude comparison** (0%→95% cyclicity from a threshold change, vs. repair's marginal BEW/PIC reductions once cyclic) is already the paper's stated headline claim, but the regret decomposition would make it quantitatively undeniable rather than qualitatively argued.

## 4. Experiments that look stronger in the raw data than in the manuscript

- **Failure-pattern prediction** (item 2 above): the manuscript's one-clause dismissal undersells a properly-controlled (holdout + permutation-test) negative result.
- **Counterfactual-generation feasibility**: entirely absent, despite being the most rigorous form of evidence for the null (constructive, adversarial, protocol-validated).
- **The second real-LLM dataset** (Cohere + Azure, full BRIGHT coverage, `reports/failure_mining_llm_v3/`): the manuscript scopes its real-LLM claim down to "single provider, no BRIGHT" when the repository actually contains corroborating data on a second provider stack covering the missing dataset. The manuscript is more modest about its own real-LLM coverage than the evidence supports.
- **The regret decomposition**: not merely under-emphasized but entirely unused, despite being computed from the same canonical corpus (`experiments/failure_class_audit_20260711_212157/`) already cited for the failure taxonomy.

## 5. Independent analyses converging on one conclusion, currently kept apart

| Conclusion | Analysis A | Analysis B | Currently connected? |
|---|---|---|---|
| Construction dominates repair | Regime-driven cyclicity swing (§5, headline) | Regret decomposition (91% candidate/construction vs. 3.6% repair-choice, unused) | **No** — same conclusion, two measurements, never cross-referenced |
| Repair rarely matters at the query level | Bootstrap null results (§6, observational) | Counterfactual-generation 0% yield (unused, constructive/adversarial) | **No** |
| The "inactive/invisible" pattern is real, not a taxonomy artifact | Manual 6-class taxonomy (§7) | Unsupervised GMM clustering recovering the same 2 macro-clusters (unused) | **No** |
| The pattern persists under real LLM judgments | OpenAI real-LLM pilot (§8, 3 datasets) | Cohere/Azure real-LLM data (unused, 4 datasets incl. BRIGHT) | **No** |
| No advance-prediction of repair benefit is possible | "No validated predictive selector" prose (§11/§12) | Learned-selector negative result + failure-pattern-prediction negative result (both unused) | **Partially** — asserted, not demonstrated |

This is the audit's most actionable structural observation: the repository contains **methodological triangulation** — the same conclusions reached by independent methods (observational vs. constructive, manual vs. unsupervised, one provider vs. two) — but the manuscript currently presents each analysis in isolation rather than as corroborating evidence for one another. Triangulation is a genuinely strong evidentiary posture and is currently invisible as such.

---

## Verdict: wrong story, or strongest story left partly untold?

**The manuscript is not telling the wrong story.** Its core claim — repair fixes the graph, not the retrieval metric, and construction/fusion choices dominate the outcome — is exactly what the repository supports, and it is told carefully, without overclaiming, with appropriate caveats at every turn (BEW/PIC circularity, HotpotQA sample size, real-LLM scope, CARB licensing). An Area Chair reading only the repository would arrive at the same conclusion the authors did.

**But it is not yet the strongest version of that story.** Two specific, already-computed, already-verified pieces of evidence — the regret decomposition and the counterfactual-generation feasibility check — would convert the paper from "we checked, and mostly repair doesn't help" (solid, modest) into "we quantified exactly how little repair matters relative to the rest of the pipeline (3.6% of the oracle gap), and we tried, including by adversarial construction, to find a case where it does matter, and could not" (assertive, rigorously negative, more citable). This is not a reframing risk — every one of these findings is *more* conservative and *more* consistent with the manuscript's existing limitations than what's currently written, not less.

---

## A. If only four scientific contributions could be kept

1. **Structural/retrieval decoupling with regime-stratified bootstrap evidence** (§5–6, Table 5, the HotpotQA counter-intuitive exception) — the load-bearing result.
2. **Simple, structure-blind baselines beat every graph-repaired method, and exact repair doesn't change this** (Table 6 + the exact-vs-greedy comparison) — the practical "should you build this" answer.
3. **The regret decomposition: repair-choice explains ~3.6% of the achievable gap; candidate generation/construction explains ~91%** (currently unused) — the single number that bounds how much this paper's subject matters.
4. **The 6-class failure taxonomy** (§7) — the mechanistic "why," complementing #1.

Demoted to supporting evidence rather than standalone headline contributions, if forced to choose: the bounded real-LLM validation (folds under #1 as corroboration) and CARB (a release, not a finding).

## B. Single strongest sentence for the paper's actual contribution

> "Feedback-arc-set repair reliably fixes the graph-internal inconsistency it targets, but that structural correction is a minor and largely inert lever on retrieval quality — vote-construction rules, not repair, determine whether a graph is inconsistent at all; an oracle-regret decomposition shows the choice of repair procedure accounts for only a few percent of the achievable ranking-quality gap; and simple score-fusion baselines that never inspect graph structure outperform every graph-repaired ranking tested — so structural consistency and retrieval quality must be measured, budgeted, and reported as separate axes of data quality, not assumed to move together."

## C. Title to maximize JDIQ acceptance probability

The current title (*"When Does Repairing Preference-Graph Inconsistency Improve Retrieval Quality?"*) is honest and accurately scoped, and would not need to change to avoid overclaiming. If reframing around the regret-decomposition finding, a stronger candidate for a data-quality venue:

> **"Structural Repair, Retrieval Quality, and the Limits of the Connection: A Data-Quality Study of Preference-Graph Consistency"**

— leads with the decoupling finding (JDIQ's core interest — data quality as a measurable, separable property) rather than posing it as an open question, while remaining exactly as conservative as the current title.

## D. Abstract that follows from the repository rather than the current manuscript

> Retrieval systems that aggregate multiple ranking signals into a preference graph can produce cyclic, internally inconsistent evidence, and a standard remedy repairs the graph by removing a minimum-weight feedback arc set before extracting a ranking. Using four public retrieval benchmarks, three graph-construction regimes, and a paired bootstrap comparison over more than a thousand query-level records, we find that whether a graph is inconsistent at all is governed overwhelmingly by the construction rule, not by any property of the underlying rankers — the same scores yield near-acyclic or substantially cyclic graphs depending on a single retention threshold. Repair reliably reduces graph-level inconsistency whenever it is present, but an oracle-regret decomposition shows the choice of repair procedure accounts for only a small fraction of the retrieval-quality gap achievable on these benchmarks, while candidate-generation and graph-construction choices account for the large majority of it; correspondingly, structural repair changes retrieval quality in only one of twenty-four tested conditions, and exact optimization of the repair objective changes this picture not at all. Simple, structure-blind score-fusion baselines outperform every graph-repaired ranking method we test. A six-class failure taxonomy, corroborated by unsupervised clustering and by a deliberately adversarial counterfactual-generation check that failed to produce a repair-sensitive test case even by construction, explains why: repair is usually inactive or invisible to the retrieval metric, rarely harmful, and reliably beneficial in only one dataset-regime combination, which is not the most structurally inconsistent one. We release a companion resource, CARB, packaging these graph features, repair outcomes, and diagnostic labels for further data-quality research on preference graphs.

(This differs from the current abstract mainly in leading with the regret-decomposition quantification and naming the counterfactual/clustering corroboration explicitly — every claim in it is already fully supported by material in the repository, most of it already cited in the current manuscript.)

## E. Is there a stronger organizing principle than the current section structure?

No wholesale reorganization is warranted — the current Background→Methodology→Setup→Structural Results→Downstream Results→Taxonomy→Real-LLM→Efficiency→CARB→Discussion→Limitations→Conclusion sequence is a conventional, appropriate empirical-paper structure and matches the paper's careful, non-promotional character.

The one structural upgrade worth making: the **Discussion currently lacks a single unifying frame for its several findings**, several of which (construction dominance, fusion suppression, dataset-specific resistance to explanation) are presented as a list of distinct observations. An explicit "ranked by impact" framing — construction/candidate-generation choices (dominant) > fusion/extraction rule (moderate) > repair itself (minor, ~3.6% of oracle gap) — would give the Discussion a spine that ties its existing subsections together and would be the natural home for the regret-decomposition number if it is added. This is an emphasis/framing change within the existing Discussion section, not a reorganization of the paper.

---

## Evidence index (file paths cited above)

- `outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv`, `table_bootstrap_delta_ndcg.csv`
- `experiments/final_method_gap_audit_20260711_221113/task2/`, `task3/final_baseline_comparison.csv`
- `experiments/failure_class_audit_20260711_212157/phase_reports/{MANUAL_FAILURE_TAXONOMY_REPORT.md, AUTOMATIC_FAILURE_CLASS_REPORT.md, REGRET_DECOMPOSITION_REPORT.md, FAILURE_PATTERN_PREDICTION_REPORT.md}`
- `experiments/counterfactual_generation_feasibility_/corrected_run/`
- `outputs/learned_selector/LEARNED_SELECTOR_REPORT.md`
- `outputs/openai_real_llm_cross_dataset_summary.md`
- `reports/failure_mining_llm_v3/`
- `papers/JDIQ_2026/manuscript/main.tex` (current manuscript text, all sections read in full this session)
