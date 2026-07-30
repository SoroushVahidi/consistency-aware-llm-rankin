# Manuscript Reframing Analysis: Toward a Coherent IR Paper

**Purpose**: answer, concretely and with file-level citations, how this project's manuscript should be reshaped into a defensible information-retrieval paper given (a) editor feedback that the current framing is too broad/audit-like and edges toward overclaiming, and (b) four completed empirical studies. No new experiments were run to produce this document; no prior report or manuscript file was modified.

**Inputs consulted** (read-only): `papers/JDIQ_2026/manuscript/main.tex` (the finalized, submission-frozen manuscript); `papers/negative_result_2026/{MANUSCRIPT_PLAN,OUTLINE,ABSTRACT_DRAFTS,CLAIMS_AND_EVIDENCE,LIMITATIONS,FIGURE_AND_TABLE_PLAN}.md` (a second, prose-less planning track); `reports/repository_scale_headroom_analysis/` (repo-scale classical oracle-headroom analysis, n=419 queries); `reports/reviewer_concerns_program_20260729T035320Z/` (small real-LLM construction-variant pilot); and the three studies completed this session: `reports/repair_frontier_20260729T144742Z/`, `reports/extraction_study_20260729T151610Z/`, `reports/repair_diagnostic_20260729T162748Z/`.

---

## 0. Direct answer

**Reshape the paper around one convergent empirical arc, told across two independent graph-construction mechanisms, with a single honest headline: preference-graph construction choices reliably reshape graph structure, but no amount of structural remediation — repair, richer repair candidates, or choosing a different graph-to-ranking extractor — reliably improves retrieval effectiveness beyond a simple structure-agnostic baseline, and the rare cases where it does are not identifiable in advance.** This is not a repackaged negative result; it is a rigorous, multi-angle characterization of *why* structural consistency and retrieval utility diverge for LLM- and multi-ranker-derived preference graphs, using two evidence bases of different scale and character:

- **Evidence base 1 (large-scale, classical multi-ranker construction)**: `papers/JDIQ_2026` and `reports/repository_scale_headroom_analysis/` — n=419 queries, 4 datasets (BRIGHT, FiQA, HotpotQA, SciDocs), graphs built from classical retriever score fusion. This is the statistical backbone: cyclicity swings from 63.5–99.2% down to 1.9–30.8% depending on construction, yet oracle headroom is 0.0025 (CI [0.0020, 0.0030]) — about 8x below the study's own minimum-detectable-effect (0.0207).
- **Evidence base 2 (small-scale, real multi-provider LLM-judge construction)**: this session's three studies plus the reviewer-concerns Branch B pilot — n=120 query-graphs (6 underlying queries × 4 LLM providers + aggregate × up to 3 pool/sparsity variants), 2 datasets (SciDocs, FiQA), real Azure/Gemini/Cohere/Fireworks pairwise judgments. This is a **directional robustness check, not a second large-n study** (6 groups is not enough for a standalone claim), but it reproduces the same qualitative divergence with three independent angles: a richer repair-candidate frontier (still no meaningful headroom, 0.0054 CI [0.0029,0.0084]), a systematic extractor comparison (no extractor beats the incumbent meaningfully; the extractor that most resembled "helping" — Borda — is actually significantly *worse* on average), and a predictability diagnostic (repair is mildly *harmful* on average, CI [-0.00191, -0.00019], and its rare benefits are not predictable from any pre-repair feature).

Do **not** keep the "seven-dimension data-quality audit" framing (main.tex:49-51) as the paper's identity for an IR venue — it is accurate but reads as infrastructure/methodology-first, not research-question-first, which is precisely the friction an IR reviewer would flag. Do **not** introduce any claim that repair or alternative extraction improves retrieval — no such claim currently exists in the live manuscript text (see §9), so this is about *not adding one* while integrating new evidence, not about walking one back.

---

## 1. Recommended central thesis

> **Preference-graph construction — how pairwise comparisons are normalized, pooled, and aggregated across rankers or LLM judges — materially determines the graph's structural consistency, but structural consistency is not a reliable proxy for retrieval effectiveness: repairing inconsistency, using a richer set of repair strategies, or substituting the graph-to-ranking extraction method all fail to produce a dependable retrieval gain, and the few cases where they help cannot be identified in advance from observable graph properties.**

This thesis is falsifiable, IR-native (it is about retrieval effectiveness, not data governance), and directly supported by four converging studies rather than one. It replaces the audit framing's implicit promise ("here is a checklist for auditing your preference graphs") with a research claim ("here is what we now know about the structure-utility relationship, and how far it extends").

---

## 2. IR-centered research questions

Replace the seven-dimension audit's implicit question inventory with four sharply scoped RQs:

- **RQ1 (Construction → Structure).** How do preference-graph construction choices (score normalization, pooling policy, provider/ranker choice, aggregation regime) affect structural properties — cyclicity, SCC size, edge-weight margins — of the resulting graph? *(Answered by JDIQ §4.1 + reviewer-concerns Branch B.)*
- **RQ2 (Structure → Effectiveness).** Does the structural change from RQ1 translate into a retrieval-effectiveness (nDCG) change, and does the two-action comparison (preserve vs. repair) reveal exploitable headroom at repository scale? *(Answered by JDIQ §4.2-4.3 + `repository_scale_headroom_analysis`.)*
- **RQ3 (Richer repair, real judges).** Does a substantially richer repair strategy space — SCC-local, incumbent-protected, confidence-aware repair, evaluated on real multi-provider LLM preference graphs — recover headroom that whole-graph repair missed? *(Answered by `repair_frontier_20260729T144742Z`.)*
- **RQ4 (Extraction as an alternative lever).** If not repair, does changing the graph-to-ranking extraction method (Borda, PageRank, rank centrality, HodgeRank, prior-fused variants) provide a dependable retrieval gain? *(Answered by `extraction_study_20260729T151610Z`.)*
- **RQ5 (Predictability).** When repair or an alternative extractor does help on a specific query, is that benefit predictable in advance from observable, pre-repair graph properties — making a deployable selective policy possible? *(Answered by `repair_diagnostic_20260729T162748Z`.)*

RQ3-RQ5 are the paper's novel empirical contribution beyond the already-frozen JDIQ result; RQ1-RQ2 are the load-bearing large-*n* foundation the new work builds on and must not duplicate wholesale (see §5).

---

## 3. Paper architecture

### 3.1 Title options

1. *Structure Is Not Utility: Why Repairing and Re-Ranking Preference Graphs Rarely Improves Retrieval*
2. *When More Repair Doesn't Help: An Empirical Limit Study of Consistency Repair for LLM-Derived Preference Graphs*
3. *Consistency Without Reward: Construction Sensitivity, Repair, and Extraction in Preference-Graph Retrieval*
4. *The Structure-Utility Gap in Preference-Graph Ranking: Evidence from Repair, Extraction, and Predictability*
5. *Diagnosing the Limits of Consistency Repair for Multi-Ranker and LLM-Judge Preference Graphs*

Recommendation: **#1**, for the sharpest single-sentence takeaway an IR reviewer can repeat, with **#4** as a strong, more literal fallback if the venue prefers a less rhetorical title.

### 3.2 Abstract (revised, full text)

> Retrieval systems increasingly aggregate pairwise preferences — from multiple retrievers or from LLM judges — into a preference graph before extracting a final ranking. Because pairwise comparisons can disagree, these graphs are often cyclic, motivating a natural hypothesis: repairing structural inconsistency should improve retrieval effectiveness. We test this hypothesis directly and at scale. Using 419 queries across four IR datasets, we show that construction choices (score normalization, pooling policy, aggregation regime) materially reshape graph structure — cyclicity ranges from 63.5% to 99.2% before normalization and falls to 1.9%-30.8% after removing directly contradicted pairs — yet the resulting oracle headroom between always-preserving and always-repairing a graph is only 0.0025 nDCG (95% CI [0.0020, 0.0030]), roughly eight times below our own minimum-detectable-effect floor. We then test whether this null result reflects a weakness in the repair method itself, using real multi-provider LLM-judge preference graphs (Azure, Gemini, Cohere, Fireworks; SciDocs and FiQA). A substantially richer repair strategy space — SCC-local, incumbent-protected, confidence-aware repair — does not recover meaningful headroom (0.0054, CI [0.0029, 0.0084], still below threshold). Replacing the graph-to-ranking extraction method (Borda, PageRank, rank centrality, a new HodgeRank-based extractor, and prior-fused variants) also fails to produce a practically meaningful gain; the extractor most associated with occasional wins (Borda) is in fact significantly *worse* than the incumbent on average. Finally, we show repair's rare benefits are not predictable from any observable pre-repair graph property (cyclicity, SCC size, edge-weight margin, provider disagreement, or six others): repair is mildly harmful on average (mean delta CI entirely below zero) and improves only 1 of 120 evaluated query-graphs. Together, these four studies characterize a robust structure-utility gap: preference-graph construction is consequential for structure, but neither repair nor extraction choice is a dependable lever for retrieval effectiveness, and no observable signal currently licenses a selective policy. We discuss what this implies for practitioners building preference-graph pipelines and outline the narrow conditions under which structural repair remains worth attempting.

### 3.3 Introduction narrative (outline)

1. Motivate preference-graph construction as increasingly common in IR (rank fusion, LLM-judge aggregation, multi-ranker ensembles).
2. State the natural but untested assumption: inconsistency (cycles) signals a ranking problem worth fixing.
3. Preview the four-study arc and the headline structure-utility gap finding.
4. State scope up front (datasets, providers, pool sizes — see §7) to preempt "is this general?" pushback.
5. State the paper's stance explicitly: neither "repair never helps" nor "repair helps" — a *quantified, scoped* null with a floor (MDE) and a predictability test, which is the stronger and more falsifiable claim.

### 3.4 Contributions (bullets)

- A repository-scale (n=419, 4-dataset) characterization of how preference-graph construction choices affect structure, replacing an ad hoc audit framing with a direct structure-vs-utility comparison anchored to a pre-registered minimum-detectable-effect.
- A real multi-provider LLM-judge robustness check (4 providers, 2 datasets) confirming the same qualitative divergence holds outside the classical multi-ranker setting, via three independent instruments: a richer repair-candidate frontier, a systematic extraction-method comparison (including a new HodgeRank-based extractor), and a feature-predictability diagnostic.
- Evidence that a plausible alternative lever — extraction-method choice, not repair — also fails to help, and that the specific method (Borda) most implicated in prior oracle-attribution analysis is a significant *loser* on average, correcting a natural but wrong inference.
- A predictability result showing repair's rare benefit is not identifiable from nine categories of pre-repair graph features, with proper grouped cross-validation and negative controls, closing off the natural "just learn a selector" follow-up.
- A scoped, practitioner-facing recommendation: do not deploy consistency repair as a default retrieval-improvement step under the tested conditions; the paper specifies exactly which conditions those are.

### 3.5 Experiment organization (maps existing artifacts to sections)

| Paper section | Source study | n / scope |
|---|---|---|
| §4.1 Construction → Structure | JDIQ main.tex §4.1 (retained, lightly re-titled) | n=419, 4 datasets, classical multi-ranker |
| §4.2 Structure → Effectiveness (repository scale) | JDIQ §4.2-4.3 + `repository_scale_headroom_analysis` | n=419, 4 datasets |
| §4.3 Richer repair, real LLM judges | `repair_frontier_20260729T144742Z` | n=120 query-graphs, 2 datasets, 4 providers |
| §4.4 Extraction as an alternative lever | `extraction_study_20260729T151610Z` | same 120 query-graphs |
| §4.5 Is repair's benefit predictable? | `repair_diagnostic_20260729T162748Z` | same 120 query-graphs |

### 3.6 Results narrative (per subsection, with the numbers to lead with)

- **§4.1**: BM25 conditional edge-weight share 0.988 (raw) → 0.512 (normalized); cyclicity 63.5-99.2% → 1.9-30.8% after dropping directly contradicted pairs. Frame as: *construction is not a nuisance parameter — it is the dominant determinant of graph shape.*
- **§4.2**: Oracle headroom 0.0025 (CI [0.0020,0.0030], n=419) vs. MDE 0.0207 → ~8x below detectability. Benefit/harm asymmetry: mean benefit +0.0054 vs. mean harm −0.0116 (harm is ~2.1x larger in magnitude) — lead with this, it is a sharper point than the symmetric-looking 28.2%/27.2% win/loss counts.
- **§4.3**: Richer frontier headroom 0.0054 (CI [0.0029,0.0084]) — larger than repo-scale but still below the 0.01 practical threshold used throughout; oracle-best-method attribution: incumbent wins 87/120, alternative extractors 30/120, repair variants only 3/120 combined. Frame the 30/120 as the motivation for §4.4, not as a positive repair finding.
- **§4.4**: Best single extractor (HodgeRank) mean delta +0.0041 (CI [0.0020,0.0067], below 0.01 threshold); Borda mean delta −0.0080 (CI [-0.0139,-0.0033], significantly negative). Frame explicitly: *the method that appeared to win most often in the oracle sense is a loser on average — oracle-best attribution among many candidates is not evidence of a good fixed policy.*
- **§4.5**: 1/120 improved, 9/120 harmed, 110/120 unchanged; overall mean delta CI [-0.00191,-0.00019] (entirely negative); grouped-CV predictor honestly reported UNSUPPORTED (1 positive example is too few); two features (cyclicity, top-k involvement) show a significant Holm-corrected *negative* association with repair benefit (r≈-0.25, Holm p≈0.023) — repair hurts more, not less, when the graph is more cyclic or touches top-k. This is worth a sentence: it is evidence *against* the "structural severity should predict repair value" intuition, not evidence for a usable rule.

### 3.7 Discussion & practical implications

- For practitioners: do not add consistency repair as a default post-processing step for fused/LLM-judge preference rankings under the tested conditions (pool sizes 6-10, 2-4 comparisons per pair, nDCG@10); the cost (implementation + compute for MWFAS solving) is not repaid.
- The 8x gap between observed headroom and MDE is itself informative: it bounds how much *future* data collection could plausibly change the conclusion — closing this gap would need roughly 64x the query sample (since CI width scales as 1/sqrt(n)) at the current effect size, which is a concrete, falsifiable prediction for follow-up work.
- The extraction-method finding is a genuine "check the alternative before you build the complex thing" cautionary result: a per-query oracle over a small candidate set will always name a winner; only an average-case, bootstrap-CI'd comparison reveals whether that winner is real. This methodological point (oracle-attribution ≠ deployable-policy evidence) generalizes beyond this paper's specific setting and is worth stating as a standalone discussion point for IR practitioners evaluating any multi-method ensemble.
- Where structural repair *might* still be worth it: settings with much larger candidate pools, sparser pairwise coverage, or objectives other than top-10 nDCG (e.g., full ranking agreement, fairness-of-exposure) were not tested and are explicitly out of scope (see §7) — state this as the honest boundary of the null, not hedge it away.

### 3.8 Limitations

- The real-LLM evidence base (repair-frontier/extraction/diagnostic studies) has only 6 underlying queries; grouped cross-validation and subgroup-stability checks are reported, but this is not a substitute for a larger real-LLM sample — say this plainly, do not average away the distinction between the n=419 backbone and the n=6-query robustness check.
- Only 2 datasets (SciDocs, FiQA) were used for the real-LLM studies (vs. 4 for the classical backbone); no claim should imply the LLM-judge finding was tested on BRIGHT/HotpotQA.
- Only greedy (and, where computationally feasible, exact SCIP) whole-graph MWFAS repair, plus the SCC-local/protected variants in `repair_frontier`, were tested; other repair formulations (e.g., rank-aggregation-theoretic alternatives, learned repair) are untested.
- Only 9 extraction methods were compared, all deterministic, graph-structure-based, or simple prior-fusion; learned/neural rerankers as an "extraction" alternative were not tested.
- All effectiveness comparisons use nDCG@10 with the pools' own qrels; other metrics (MRR, recall at larger k, calibration-sensitive metrics) were not evaluated.

### 3.9 Conclusion

Restate the structure-utility gap thesis; state the concrete, falsifiable boundary conditions (§7); state the one methodological takeaway most transferable outside this paper's setting (oracle-attribution across many candidates is not evidence for a deployable fixed policy — average-case, CI'd, negative-controlled evaluation is required); close with the practitioner recommendation from §3.7.

---

## 4. Material disposition

| Material | Disposition | Rationale |
|---|---|---|
| JDIQ main.tex §4.1 "Construction Quality Dominates the Graph" | **Retain**, re-title to match RQ1 framing (e.g. "Construction Determines Structure") | Already rigorous, already has the right numbers; only the framing sentence needs to change, not the content. |
| JDIQ main.tex §4.2-4.3 (repair vs. retrieval null, exact-repair robustness) | **Retain**, compress | This is the RQ2 backbone; keep the statistics, cut restatements/hedging that served the audit framing's caution but read as repetitive for an IR reviewer. |
| JDIQ's "seven-dimension data-quality audit" framing sentence(s) (main.tex:49-51, and wherever the seven dimensions are enumerated as the paper's organizing structure) | **Rewrite** | Replace with the RQ1-RQ5 structure; the seven dimensions (provenance, calibration, vote semantics, conflict structure, repair quality, downstream utility, reproducibility) can survive as a **methods appendix checklist**, not the paper's spine. |
| `repository_scale_headroom_analysis/` figures/tables (headroom vs. MDE bar chart, benefit/harm histogram, per-covariate |r| chart) | **Retain**, reuse directly | Already built for exactly this argument (`FIGURE_AND_TABLE_PLAN.md`); minimal rework needed. |
| `reviewer_concerns_program_20260729T035320Z` Branch B (pool/sparsity real-LLM sweep, n=6 queries) | **Move to appendix** | Directionally confirms "no headroom" but is too underpowered (its own report says so) to carry weight in the main results; useful as a robustness footnote, not a headline. |
| `repair_frontier_20260729T144742Z` (SCC-local/protected repair, oracle-best attribution) | **Rewrite into §4.3**, condensed | The full sensitivity sweep (confidence thresholds, protection rules, etc.) belongs in an appendix; the main text needs only: headroom number, CI, and the oracle-best-method attribution table motivating §4.4. |
| `extraction_study_20260729T151610Z` (9-extractor comparison incl. HodgeRank) | **Rewrite into §4.4**, condensed | Lead with the summary table (mean delta, CI, win/tie/loss per extractor); move per-dataset/per-provider breakdowns to appendix. |
| `repair_diagnostic_20260729T162748Z` (predictability diagnostic) | **Rewrite into §4.5**, condensed | Lead with outcome counts + overall CI + the UNSUPPORTED predictor result; move the full feature-association table (23 features) to appendix, keep only the two Holm-significant features in-text. |
| `docs/safe_claims.md`, `docs/SAFE_Q1_CLAIMS.md`, `docs/SAFE_CLAIMS_FOR_PAPER.md`, `docs/Q1_POSITIONING_AND_CLAIMS.md` | **Retain as internal working docs, not manuscript material** | These are exactly the guardrails that kept the live manuscript honest (see §9) — keep using them as a pre-submission checklist, but they are not paper content. |
| `papers/negative_result_2026/*.md` (Track B planning docs) | **Superseded / merge** | This reframing effectively replaces Track B's narrower "oracle-selectability" framing with the broader, four-study RQ1-RQ5 arc; the Track B claims-and-evidence discipline (explicit required/forbidden phrasing per claim) should be **retained as a process**, applied to the new claims in §6 below. |
| Old exploratory figures (`docs/figures/`, `docs/tables/`, top-level `figures/`, dated 2026-07-05) | **Remove from consideration** | Superseded by the JDIQ finalized figure set (`figures_v2/`); not cited by either current manuscript track. |

---

## 5. Empirical findings — accurate integration

All numbers below are quoted directly from the source reports; do not round in ways that hide the CI or the sign.

| Finding | Number | Source |
|---|---|---|
| Cyclicity range, before → after dropping contradicted pairs | 63.5-99.2% → 1.9-30.8% | `papers/JDIQ_2026/manuscript/main.tex:322-324,398` |
| BM25 conditional edge-weight share, raw → normalized | 0.988 → 0.512 | `main.tex:54-56,310-312` |
| Repo-scale oracle headroom (query-level, n=419) | 0.0025 (CI [0.0020, 0.0030]) | `reports/repository_scale_headroom_analysis/summary.json` |
| Minimum detectable effect (Holm-adjusted, 80% power) | 0.0207 | `reports/final_revision_task2_statistical_power_20260715/FINAL_REPORT.md:79`; `main.tex:429-430` |
| Benefit/harm magnitude asymmetry | mean benefit +0.0054 vs. mean harm −0.0116 (~2.1x) | `papers/negative_result_2026/CLAIMS_AND_EVIDENCE.md:34` |
| Richer repair-frontier headroom (real LLM, n=120 query-graphs) | 0.0054 (CI [0.0029, 0.0084]) | `reports/repair_frontier_20260729T144742Z/FINAL_SUMMARY.json` |
| Oracle-best-method attribution (of 120) | incumbent 87, alt-extraction 30, whole-graph-exact 2, scc-local-greedy 1, protected 0 | `reports/repair_frontier_20260729T144742Z/discovery/oracle_best_method_per_query.jsonl` |
| Best single extractor (HodgeRank) mean delta | +0.0041 (CI [0.0020, 0.0067]) | `reports/extraction_study_20260729T151610Z/FINAL_SUMMARY.json` |
| Borda mean delta (significantly negative) | −0.0080 (CI [−0.0139, −0.0033]) | same |
| Repair outcome counts (n=120 query-graphs) | 1 improves / 9 harms / 110 unchanged | `reports/repair_diagnostic_20260729T162748Z/FINAL_SUMMARY.json` |
| Overall repair mean-delta CI (entirely negative) | [−0.00191, −0.00019] | same |
| Holm-significant negative feature associations | is_cyclic r=−0.248 (Holm p=0.023); topk_involvement r=−0.248 (Holm p=0.023) | same |
| Predictor status | UNSUPPORTED (1 positive example; correctly gated, not fit to noise) | same |

**Do not** state these findings as five isolated bullet points (as the user's own task list enumerates them) without the connective explanation: the paper's contribution is that these five numbers *cohere* into a single explanatory story (structure ≠ utility, confirmed across two construction mechanisms and three independent remediation strategies), not that they are five separate negative results.

---

## 6. Positive-contribution framing

Frame explicitly, in the paper's own words (suggested phrasing for the Discussion or Conclusion):

> "This is not a report of five failed experiments. It is a characterization: across two independent preference-graph construction mechanisms (classical multi-ranker score fusion and real multi-provider LLM pairwise judging), three independent remediation strategies (whole-graph repair, a substantially richer repair-candidate space, and alternative graph-to-ranking extraction), and a direct predictability test, the same structure-utility gap appears with consistent sign and comparable (small) magnitude. That consistency — not any single null result — is the paper's evidence that the gap is a property of the *problem*, not an artifact of any one repair algorithm, extraction method, or dataset."

This framing does the work the "seven-dimension audit" framing was trying to do (comprehensiveness, rigor) without the connotation of a checklist/governance document, which is what likely read as off-genre to an IR editor.

---

## 7. Scope definition (what is and is not supported)

State this as an explicit, numbered scope box early in the paper (Introduction or start of Experimental Design), not scattered through Limitations:

- **Datasets tested**: BRIGHT, FiQA, HotpotQA, SciDocs (classical backbone, n=419 queries); SciDocs and FiQA only (real-LLM studies, n=6 underlying queries).
- **Preference sources tested**: classical multi-ranker score fusion (backbone); 4 real LLM judges — Azure OpenAI (gpt-4.1-mini), Vertex AI Gemini (gemini-2.5-flash), Cohere (command-r-plus-08-2024), Fireworks (gpt-oss-120b) — plus their unweighted aggregate.
- **Pool sizes tested**: repository-scale backbone uses each dataset's native qrel-derived pools; real-LLM studies use pool sizes 6, 8, and 10, with complete and ~56-57%-sparse pairwise coverage.
- **Repair methods tested**: greedy and exact (SCIP) whole-graph MWFAS; SCC-local, incumbent-protected, and confidence-weighted repair variants (5 protection-rule kinds).
- **Extraction methods tested**: Copeland (incumbent), Borda, PageRank, rank centrality, weighted balance score, HodgeRank (new), and two prior-fused hybrid variants.
- **Metric tested**: nDCG@10 exclusively.
- **What is NOT supported by this evidence**: any claim about datasets/providers/pool sizes outside this list; any claim about metrics other than nDCG@10; any claim generalizing the real-LLM findings (n=6 queries) with the same confidence as the n=419 backbone — these must remain distinctly captioned throughout.

---

## 8. Claims that must be deleted or weakened

No sentence currently in the live manuscript (`main.tex`) claims repair improves retrieval in aggregate — confirmed by direct search; existing phrasing is already disciplined (e.g. main.tex:459, 525-526 explicitly reject both "repair helps" and "repair never helps"). The changes needed are additions/reframings, not deletions of oversold claims:

1. **Delete or relocate**: the "seven-dimension data-quality audit" framing sentence(s) as the paper's stated contribution — this is the one framing element inconsistent with an IR-reviewer's expectations; move the seven dimensions to a methods appendix checklist.
2. **Weaken/qualify**: any Track B (`papers/negative_result_2026/ABSTRACT_DRAFTS.md`) sentence that reports the oracle headroom CI excluding zero without immediately pairing it with the MDE comparison in the same sentence — reviewed drafts already do this reasonably well, but re-verify during final editing that no trimmed/shortened abstract variant separates "headroom is statistically real" from "...but 8x below our detectability floor" across a paragraph break.
3. **Add explicit non-claims** (per Track B's own `CLAIMS_AND_EVIDENCE.md` discipline, now extended to the three new studies): do not claim "prediction of repair benefit is impossible" — only that it is not achieved by the nine tested feature categories and three tested simple model classes on n=120 rows / 6 groups; do not claim "no extraction method ever helps" — only that none of the nine tested methods shows a practically meaningful, CI-supported average gain on the tested data.
4. **Verify consistently**: any sentence using the oracle-best-method attribution from `repair_frontier` (30/120 wins for alt-extraction) must NOT be phrased as "alternative extraction methods help" — the extraction study itself shows this is false on average for the specific method (Borda) most responsible for those wins. This is the single most important internal-consistency check across the two new studies.

---

## 9. Recommended IR venue categories and evaluation criteria

Chosen by fit to contribution type, not prestige:

- **Empirical / reproducibility track** (e.g., a venue's "resource and reproducibility" or "empirical methods" track): fits best, since the core contribution is a rigorous, well-powered empirical characterization with negative/null results, pre-registered thresholds, and multiple-testing correction — exactly what such tracks are built to reward. Evaluation criteria to anticipate and preempt: statistical rigor (CIs, correction for multiple comparisons — already strong here), reproducibility (data/code availability — already a stated JDIQ section), and scope honesty (the §7 scope box directly serves this).
- **Full research track, "ranking/learning to rank" or "evaluation" area**: viable if the paper leads harder with the methodological takeaway (oracle-attribution ≠ deployable-policy evidence) as a generalizable contribution, not only the domain-specific null result. Evaluation criteria to anticipate: novelty (the four-study convergence and the HodgeRank addition help here), significance (the practitioner recommendation in §3.7 helps), and generalizability (must be paired honestly with §7's scope limits — do not overreach here).
- **Short paper / perspectives or resource paper**: a fallback if reviewers view the null result as insufficiently novel for a full paper despite the rigor — the four-study convergence argument is the strongest lever against this outcome, so lead with it in the abstract and introduction, not bury it in results.

Across all three, the paper's best defense against a "just another negative result" rejection is the explicit, upfront framing from §6: this is a *characterization* built from convergent evidence across two construction mechanisms and three remediation strategies, not a single null finding.

---

## Appendix: source manifest

- `papers/JDIQ_2026/manuscript/main.tex` (569 lines; title, abstract, §4.1-4.3, Discussion/Limitations/Conclusion cited above)
- `papers/negative_result_2026/{MANUSCRIPT_PLAN,OUTLINE,ABSTRACT_DRAFTS,CLAIMS_AND_EVIDENCE,LIMITATIONS,FIGURE_AND_TABLE_PLAN}.md`
- `reports/repository_scale_headroom_analysis/summary.json`, `manuscript_tables/table_3_oracle_headroom.csv`
- `reports/final_revision_task2_statistical_power_20260715/FINAL_REPORT.md`
- `reports/reviewer_concerns_program_20260729T035320Z/{BRANCH_DECISION.json,FINAL_REPORT.md,FINAL_SUMMARY.json}`
- `reports/repair_frontier_20260729T144742Z/{FINAL_REPORT.md,FINAL_SUMMARY.json,discovery/oracle_best_method_per_query.jsonl}`
- `reports/extraction_study_20260729T151610Z/{FINAL_REPORT.md,FINAL_SUMMARY.json}`
- `reports/repair_diagnostic_20260729T162748Z/{FINAL_REPORT.md,FINAL_SUMMARY.json}`
- `docs/safe_claims.md`, `docs/SAFE_Q1_CLAIMS.md`, `docs/SAFE_CLAIMS_FOR_PAPER.md`, `docs/Q1_POSITIONING_AND_CLAIMS.md`, `docs/research/{EXPERIMENT_ROADMAP,DECISION_LOG,MANUSCRIPT_SUMMARY,RESEARCH_TRAJECTORY}.md`

No file outside this new report directory was modified.
