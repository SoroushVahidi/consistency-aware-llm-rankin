# Independent Contribution Audit: Repository vs. Manuscript

> **PARTIALLY SUPERSEDED (as of 2026-07-14).** This audit's "Bradley-Terry
> ... completely missing from the reported comparison" finding is now
> factually wrong: Bradley-Terry (along with PageRank and RankCentrality)
> was subsequently integrated as a graph baseline in the current
> `manuscript/main.tex`. Treat this file as a historical snapshot of a gap
> that has since been closed, not a current finding.

**Prepared:** 2026-07-12
**Method:** Full read of `main.tex` (all 13 sections + abstract/CARB/limitations), cross-referenced against a three-way parallel inventory of (1) `src/` code capabilities, (2) `experiments/`+`reports/` output artifacts, (3) design docs (`AGENTS.md`, `CANONICAL_PAPER_STORY.md`, `MANUSCRIPT_OUTLINE.md`, `PROJECT_STATUS.md`, `MISSING_COMPONENTS.md`, the rejected IJCS manuscript, root `TODO.md`/`README.md`). This document is research/analysis only — no manuscript edits were made.

---

## Part 1: Item-by-item contribution audit

| # | Item | Repo evidence | Manuscript evidence | Communicated well? | Classification | Recommended disposition |
|---|---|---|---|---|---|---|
| 1 | Preference-graph construction from ranker-score votes, 3 regimes (ms2/ms1/ms1_drop_mutual) | `src/consistency_ranker/pairwise_prefs.py`, `graph_construction.py` | §3.1–3.2, Eq. 1, Table 2 | Yes | **A. Fully represented** | Main contribution (already is) |
| 2 | Structural metrics: cyclicity, SCC size, BEW, PIC | `evaluation.py`, `graph_construction.py` | §3.3, Eqs. 2–3, Table 4 | Yes, with correct circularity caveat | **A. Fully represented** | Main contribution (already is) |
| 3 | Greedy FAS repair (cycle-peeling) | `greedy_fas.py` | §3.4, Eq. 4 | Yes | **A. Fully represented** | Main contribution |
| 4 | Exact brute-force FAS (n≤10) as "exact-for-small-components" | `exact_fas.py` | §4.4, Table 5 | Yes | **A. Fully represented** | Main contribution |
| 5 | Gurobi ILP exact solver | `mwfas_solver.py` | §4.7: disclosed as present but "not used to produce any result" | Yes — correctly scoped down | **A. Fully represented** (as a disclosed non-result) | Correct as-is |
| 6 | External exact/metaheuristic solver package (anonymity-sensitive) | sibling repo, traced in `integrity_audit/` | §4.4: reported qualitatively, withheld from citation for anonymity | Yes — this was a deliberate, well-reasoned integrity decision from an earlier pass | **A. Fully represented**, appropriately caveated | Correct as-is; add full citation at camera-ready |
| 7 | Copeland / balance / hybrid ranking extraction | `baseline_ranking.py` | §3.5, Eqs. 5–7 | Yes | **A. Fully represented** | Main contribution |
| 8 | Bootstrap CI methodology (paired percentile, B=2000) | `scripts/run_bootstrap.py` etc. | §4.5, Eq. 8 | Yes | **A. Fully represented** | Main contribution |
| 9 | Structural/retrieval decoupling result (central thesis) | `experiments/final_method_gap_audit_20260711_221113/` | §5–6, Table 5, Fig. 4 | Yes | **A. Fully represented** | Main contribution — correctly the paper's spine |
| 10 | CombSUM/RRF beating all graph methods | `final_baseline_comparison.csv` (verified exact match) | §6.2, Table 6 | Yes | **A. Fully represented** | Main contribution |
| 11 | 6-class manual failure taxonomy | `experiments/failure_class_audit_20260711_212157/phase_reports/MANUAL_FAILURE_TAXONOMY_REPORT.md` (verified exact match to Table 7) | §7, Table 7 | Yes | **A. Fully represented** | Main contribution |
| 12 | Fusion suppression rate (14.7%, range 4.8–26.4%) | same audit directory | §7, one paragraph | Yes | **A. Fully represented** | Secondary contribution (already is) |
| 13 | Counterfactual "no-repair is the minimal fix for every harmful case" | `COUNTERFACTUAL_REPAIR_REPORT.md` | §7, one sentence | Yes, though terse | **A. Fully represented** | Could be promoted with 1–2 more sentences (see Part 2) |
| 14 | Exact-vs-greedy repair doesn't change retrieval conclusion | `experiments/final_method_gap_audit_20260711_221113/task2/` (verified exact match) | §6.3 | Yes | **A. Fully represented** | Main contribution |
| 15 | Runtime/memory efficiency notes | `utils/timing.py`, same audit dir | §9 | Yes, with correct scope caveats | **A. Fully represented** | Secondary contribution |
| 16 | Bounded real-LLM validation (OpenAI, 3 datasets, pairwise) | `outputs/openai_real_llm_cross_dataset_summary.md` | §8, Table 8 | Yes | **A. Fully represented** | Main contribution as scoped |
| 17 | CARB benchmark (planned release) | `experiments/created_data_audit_20260711_232004/` (schema/stats confirmed) | §10, Table 9 | Yes | **A. Fully represented** | Secondary contribution (already is) |
| 18 | Automated unsupervised (GMM) corroboration of the manual failure taxonomy | `AUTOMATIC_FAILURE_CLASS_REPORT.md` (silhouette 0.348, 2 stable macro-clusters mapping onto repair-inactive/tail-only) | **Not mentioned anywhere** | No | **D. Completely missing** | Supplementary material — one sentence/footnote in §7 validating the manual taxonomy isn't arbitrary |
| 19 | Regret decomposition (gap-to-oracle attributed to missing-candidate-information 91.1%, graph-construction 76.6%, repair-choice only 3.6%) | `REGRET_DECOMPOSITION_REPORT.md` | **Not mentioned anywhere** | No | **D. Completely missing** | **Secondary contribution** — directly and independently reinforces the central thesis quantitatively; needs a sentence explaining why components don't sum to 100% (likely non-orthogonal/overlapping) before use |
| 20 | Adversarial/constructive counterfactual-generation feasibility check (5 synthetic stress-test scenario families; validated run: 0% non-neutral yield for the hybrid method) | `experiments/counterfactual_generation_feasibility_/corrected_run/` | **Not mentioned anywhere** | No | **D. Completely missing** | Supplementary robustness analysis — independent (constructive, not observational) corroboration of "repair rarely matters," worth 2–3 sentences or a supplement table |
| 21 | Second real-LLM data collection (Cohere + Azure, all 4 datasets, **full BRIGHT coverage**, repaired-vs-unrepaired comparison) | `reports/failure_mining_llm_v3/` (100% real coverage, fiqa/hotpotqa/bright) | **Not cited anywhere** — §8 states "single provider (OpenAI)... BRIGHT has no real-LLM pilot in this study" | No | **D. Completely missing**, and it **directly contradicts a limitation the manuscript states as still-open** | **Highest-priority item** — see Part 3 |
| 22 | Repair-selector training pipeline (`repair_selector_mining/`): 6 model families, leakage-safe splits, bootstrapped utility CI, oracle regret, sufficiency rubric | `src/consistency_ranker/repair_selector_mining/` (code fully built; no run outputs found in this repo) | §11 Discussion / §12 Limitations: "no validated predictive selector... only modest, non-decisive signal" | Partially — the code is more mature than the prose implies, but the *prose's substantive claim* (no validated selector) is still accurate given no completed run exists | **B. Partially represented** | Add one clause noting a selector-training protocol exists and is pending sufficient data (honest, and slightly strengthens the "we tried seriously" framing) |
| 23 | Failure-pattern prediction (ROC-AUC 0.83–0.88 for harm, but PR-AUC 0.15–0.33, precision 0.13–0.30, feature importances self-suppressed for failing permutation controls) | `FAILURE_PATTERN_PREDICTION_REPORT.md` | §11: only the qualitative "modest, non-decisive signal" claim | Under-evidenced — the claim is true but the actual numbers that would substantiate "non-decisive" (i.e., high AUC undermined by low precision/PR-AUC and failed permutation controls) are not shown | **C. Mentioned but underemphasized** | Add the actual numbers as evidence *for* the existing claim — this strengthens rather than weakens the paper (shows a genuine, quantified negative check, not just an assertion) |
| 24 | `outputs/learned_selector/` (accuracy 0.48–0.57, precision 0.18–0.19, fixed thresholds beat the learned selector) | `outputs/learned_selector/LEARNED_SELECTOR_REPORT.md` | Same as above | Same as above | **C. Mentioned but underemphasized** | Same treatment as #23 |
| 25 | Bradley-Terry MLE and local-Kemenization (adjacent-swap) rank-aggregation baselines | `rerankers/tournament_agg.py`, `baseline_ranking.py::local_adjacent_swap_refinement` — already run informally in `reports/failure_mining*` (Bradley-Terry beats the repaired hybrid in some regimes) | Not in Table 6's 12-method pooled grid | No | **D. Completely missing from the reported comparison** | **Secondary contribution candidate** — Bradley-Terry is a standard, citable classical method; adding it to Table 6 costs little and would only strengthen the "simple baselines beat graph methods" thesis if it holds up |
| 26 | Metric-aware (DCG-surrogate) repair reweighting | `metric_aware_repair.py`, used only as a non-primary label inside `repair_selector_mining/processor.py` | Not mentioned | No | **D. Completely missing / unevaluated** | **Future work** — flag as a natural next repair variant to test, not a current finding (no completed evaluation exists to report) |
| 27 | Two independent RankCentrality-family implementations (power-iteration vs. PageRank-damped) feeding the single "Markov" row in Table 6 | `baseline_ranking.py::rank_centrality_ranking` vs. `markov_graph_ranking.py` | Table 6 lists one "Markov (repaired/unrepaired)" row without specifying which implementation | N/A (internal consistency risk, not a missing contribution) | — | **Verify internally** which implementation produced Table 6's numbers before camera-ready; not a reviewer-facing gap unless the wrong one was used |
| 28 | Multi-provider, production-hardened LLM harness (Vertex AI, structured error taxonomy, circuit breakers, cost-bounded auto-pause, connection-pool reuse) | `rerankers/llm_pairwise.py`, `llm_runner.py`, `scripts/track_selector_llm_cost.py` | §4.6 mentions only "Python 3.11/3.12, networkx" | No | **D. Completely missing** | Supplementary/appendix reproducibility note — relevant to JDIQ's practical/engineering readership, not a scientific finding |
| 29 | Dataset registry supporting 8 datasets (incl. NFCorpus, MS MARCO passage, TREC-DL passage, Robust04) vs. the 4 headline datasets | `data/dataset_registry.py` | §4.1 (4 datasets) | N/A — no results exist on the other 4 | — | **Future work**, not a current gap (no computed results to report) |

---

## Part 2: Overlooked scientific contributions (targeted search)

Beyond the audit table, explicitly checking the categories you listed:

- **Negative results:** #19 (regret decomposition) and #20 (counterfactual-generation feasibility, 0% non-neutral yield under valid protocol) are strong, currently-unused negative results that *independently corroborate* the paper's central thesis through two different methodologies (attribution and constructive stress-testing) rather than restating it.
- **Robustness/ablation:** #20 is exactly a robustness analysis (does the null result survive adversarial graph construction?) and is absent.
- **Validation of methodology itself:** #18 (unsupervised clustering corroborating the manual taxonomy) is a methodological-validity check that is currently unused; it answers a reviewer's likely question ("was your manual taxonomy just picked to fit the data?") pre-emptively.
- **Solver comparison:** already well-handled (#4–6), no gap.
- **Reproducibility infrastructure:** #28 is real and substantial but appropriately belongs in a supplement/appendix, not the main scientific narrative — JDIQ readers building similar LLM-evaluation pipelines would benefit from it, but it is not itself a data-quality finding.
- **Benchmark creation:** CARB (#17) is already represented at the correct weight (secondary, not primary).
- **Statistical methodology:** the bootstrap approach is standard and correctly represented; the repair-selector's separate bootstrap+oracle-regret framework (#22) is more novel but tied to an incomplete result.
- **Unexpected empirical discovery already in the manuscript but under-mined for its full implication:** HotpotQA being the *least* cyclic dataset yet the only one with a reliable effect (§11) is flagged as an open question — this is honest and correct; the regret decomposition (#19) is one candidate explanation path the manuscript doesn't currently connect to this open question, and could be worth one cross-reference sentence.

---

## Part 3: Direct answers to your four framing questions

**1. Strongest contribution currently emphasized:** The structural/retrieval decoupling result (item #9) — correctly the spine of the paper, correctly placed as the central finding in Abstract, Results, Discussion, and Conclusion.

**2. Strongest contribution currently underemphasized:** The failure-pattern prediction numbers (#23/#24) — real, already-computed quantitative evidence for the "modest, non-decisive signal" claim currently exists but isn't cited, so the claim reads as asserted rather than demonstrated. This is a low-cost, low-risk addition: it only makes an already-conservative claim more credible.

**3. Strongest contribution completely absent from the manuscript:** **Item #21 — the second real-LLM dataset (Cohere + Azure, full BRIGHT coverage, 3 fully-covered datasets).** This is the one finding on this list that isn't just "nice to add" — it's real, already-collected data that directly closes a limitation the manuscript itself names as still open ("BRIGHT has no real-LLM pilot in this study," "a single LLM provider was used"). Leaving it out means the paper is *understating its own evidentiary strength* on a point reviewers are likely to press on (real-LLM generalization, the most commonly requested robustness check for LLM-adjacent IR papers).

**4. Stronger paper framing that better matches the repository:** No reframing is needed at the structural level — "diagnostic, curatorial" framing (not a new-algorithm paper) is exactly right and matches what the repository actually supports, per the project's own internal `publication_readiness_audit` and `reviewer_response_state_audit`. The one framing adjustment worth considering: the paper could support a slightly stronger claim than "modest, non-decisive signal" for the predictive-selector question — not "we found a working selector," but "we built and evaluated a validated selector-training protocol against multiple negative controls (permutation tests, precision/PR-AUC, held-out regret) and it did not survive them," which is a more rigorous and citable negative result than the current one-clause dismissal, and matches what the code and `FAILURE_PATTERN_PREDICTION_REPORT.md`/`outputs/learned_selector/` actually did.

---

## Part 4: Ranked table of every publishable contribution

| Contribution | Novelty | Evidence strength | Importance | Current emphasis | Should be emphasized? | Suggested section |
|---|---|---|---|---|---|---|
| Structural/retrieval decoupling (central thesis) | 7 | 9 | 10 | High | Yes (already is) | Abstract/Results §5-6/Discussion |
| CombSUM/RRF beat all graph methods | 6 | 9 | 9 | High | Yes (already is) | Results §6.2 |
| 6-class manual failure taxonomy | 7 | 8 | 8 | High | Yes (already is) | Results §7 |
| **Second real-LLM dataset closing the BRIGHT/single-provider gap** | 5 | 7 | 8 | **None** | **Yes** | Results §8 |
| Exact-repair-doesn't-change-conclusion | 5 | 8 | 7 | High | Yes (already is) | Results §6.3 |
| Fusion suppression rate | 6 | 7 | 6 | High | Yes (already is) | Results §7 |
| **Regret decomposition (oracle gap attribution)** | 7 | 6 | 7 | **None** | **Yes** | Discussion / Supplement |
| **Counterfactual-generation feasibility (0% non-neutral yield)** | 6 | 6 | 5 | **None** | **Yes, as supplement** | Supplement / Discussion footnote |
| **Failure-pattern-prediction negative result (AUC vs. PR-AUC/precision gap)** | 5 | 6 | 6 | **Low (asserted, not shown)** | **Yes** | Limitations §12 |
| Repair-selector training protocol (built, not yet sufficient data) | 6 | 4 | 5 | Low | Optional, one clause | Limitations §12 |
| **Unsupervised clustering validation of manual taxonomy** | 3 | 5 | 4 | **None** | **Yes, briefly** | Results §7 footnote |
| Bradley-Terry / local-Kemenization as additional Table 6 baselines | 3 | 5 | 4 | None | Optional (nice-to-have) | Results §6.2 |
| Metric-aware (DCG-surrogate) repair variant | 5 | 2 | 4 | None | No (unevaluated) | Future work, §13/Conclusion |
| LLM-harness engineering (multi-provider, cost governance) | 4 | 6 | 3 | None | No (not a scientific finding) | Supplementary/Appendix reproducibility note |
| Broader dataset registry (8 vs. 4 datasets) | 2 | 1 | 2 | None | No (no results exist) | Future work |

---

## Caveats on this audit

- Conservative by design: every "missing" item above is backed by a concrete file path an author can open and check; nothing here is invented.
- Two of the three research passes flagged that a **sibling repository** (`consistency-aware-llm-rankin-caar`) contains a more developed, independent repair-selector research thread whose own verdict (`PROMISING_BUT_MORE_DATA_REQUIRED`, failing permutation/random-feature controls) is consistent with, not contradictory to, this manuscript's current limitation — worth being aware it exists, but it is a separate codebase and out of scope for direct citation here.
- Item #21 (second real-LLM dataset) is the one recommendation in this audit with real time-sensitivity: if the authors want to use it, it should be evaluated for protocol compatibility with §8's existing OpenAI-based comparison (different providers, possibly different query sets) before merging, following the same "distinct-protocol, clearly labeled" discipline already used elsewhere in this manuscript for the vote-suite vs. pooled-corpus distinction.
