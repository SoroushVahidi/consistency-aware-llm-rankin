# Manuscript Outline — JDIQ 2026

> **SUPERSEDED (as of 2026-07-14).** This is the pre-writing structural
> plan. In particular, its "§7 Failure Taxonomy and Diagnostic Analysis"
> section does not exist in the finished manuscript -- `main.tex`'s actual
> §7 is "Secondary Analyses and Scope Checks," and the failure taxonomy is
> excluded as evidence (see Limitations). Use `manuscript/main.tex`'s
> actual section headers, not this outline, as the current structure.

**Paper type:** Technical / Research paper  
**Target length:** ~20–23 ACM formatted pages  
**Story:** See `CANONICAL_PAPER_STORY.md`  
**Do not write prose yet** — this is a structural blueprint only.

---

## Front matter

### Title page
- **Purpose:** State DQ-focused title; no algorithm-promising language
- **Length:** 1 page (template-generated)
- **Required:** Title, authors (anonymous for review), CCS concepts, keywords
- **CCS concepts:** Data cleaning; Information retrieval; Data curation
- **Keywords:** preference graphs, data quality, inconsistency, rank aggregation, retrieval evaluation, benchmark
- **Evidence:** `CANONICAL_PAPER_STORY.md` (title options)

### Abstract
- **Purpose:** Summarize DQ problem, method, 4-dataset scope, decoupling finding, CARB, practical implication
- **Length:** 150–250 words
- **Required figures:** None
- **Required tables:** None
- **Required experiments:** Reference main suite (not detailed)
- **Required citations:** 0–2 (DQ framework, preference aggregation)
- **Evidence:** `final_claim_support_matrix.csv` (safe claims only)

---

## 1. Introduction (§1)

- **Purpose:** Motivate preference-graph DQ; state decoupling hypothesis; list contributions; roadmap
- **Length:** ~2.5–3 pages
- **Required figures:** None (optional: conceptual diagram of pipeline)
- **Required tables:** None
- **Required experiments:** None (cite scope: 4 datasets, 1020 records)
- **Required citations:**
  - Data quality frameworks (Wang & Strong; Batini et al.)
  - Preference aggregation / social choice (Young; Cohen et al.)
  - RRF / CombSUM fusion (Cormack et al.; Montague & Aslam)
  - Graph-based ranking (Copeland; Markov chain ranking)
  - Recent LLM reranking surveys (limited)
- **Evidence:**
  - `CANONICAL_PAPER_STORY.md`
  - `reviewer_response_state_audit/CLAIMS_AUDIT.md`
  - `docs/SAFE_CLAIMS_FOR_PAPER.md`
- **Key paragraphs:**
  1. Derived preference data in retrieval pipelines
  2. Inconsistency as a DQ dimension
  3. Repair as DQ intervention; downstream retrieval as quality-of-outcome
  4. Contributions (4–5 bullets)
  5. Distinction from prior IJCS submission (1 sentence; no recycled claims)

---

## 2. Related Work (§2)

- **Purpose:** Position at intersection of DQ, preference aggregation, rank fusion, graph repair
- **Length:** ~2–2.5 pages
- **Required figures:** None
- **Required tables:** Optional comparison table (positioning, not results)
- **Required experiments:** None
- **Required citations:**
  - IQ/DQ dimensions and measurement
  - Preference learning and rank aggregation
  - Feedback arc set / graph acyclicity
  - Learning to rank and fusion methods
  - Diagnostic/negative-result empirical studies in DQ
  - Benchmark datasets in IR (BEIR, etc.) — differentiate CARB
- **Evidence:**
  - `docs/LITERATURE_ALIGNMENT.md`
  - `docs/related_work_positioning_note.md`
  - `docs/THEORETICAL_FOUNDATION.md`

---

## 3. Problem Formulation (§3)

- **Purpose:** Define preference graphs, DQ dimensions, repair operator, evaluation metrics
- **Length:** ~2 pages
- **Required figures:**
  - **Fig. 1:** Preference graph schematic (nodes = documents, edges = pairwise votes, cycle highlighted)
- **Required tables:**
  - **Table 1:** DQ dimensions measured (consistency/cyclicity, BEW, PIC, SCC size, nDCG)
- **Required experiments:** None
- **Required citations:** FAS/acyclicity literature; BEW/PIC if used
- **Evidence:**
  - `docs/THEORETICAL_FOUNDATION.md`
  - `outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv` (metric definitions)
  - Source code: `src/consistency_ranker/` (repair, graph metrics)

---

## 4. Data and Experimental Protocol (§4)

- **Purpose:** Describe datasets, vote construction regimes, methods, evaluation protocol
- **Length:** ~2.5–3 pages
- **Required figures:** None
- **Required tables:**
  - **Table 2:** Dataset statistics (queries per dataset, vote regimes, edge counts)
  - **Table 3:** Method inventory (prior, CombSUM, RRF, Borda, Copeland U/R, balance U/R, Markov U/R, hybrid)
- **Required experiments:** Canonical vote suite protocol
- **Required citations:** SciDocs, FiQA, HotpotQA, BRIGHT dataset papers
- **Evidence:**
  - `outputs/pub_vote_cmp_all4/paper_package/`
  - `reports/canonical_results_inventory.csv`
  - `docs/EXPERIMENTS.md`
  - `docs/READ_ME_FIRST_FOR_AI.md`
- **Critical protocol disclosure:**
  - Three vote regimes: ms2, ms1, ms1_drop_mutual
  - Hybrid RRF with α=0.3
  - Bootstrap: 2000 resamples
  - **Warning box:** failure-mining pooled baseline uses same records but broader method grid — report in separate subsubsection

---

## 5. Structural Data Quality Results (§5)

- **Purpose:** Report how vote regime affects inconsistency; show repair reduces structural DQ metrics
- **Length:** ~2.5 pages
- **Required figures:**
  - **Fig. 2:** Cyclicity rate by dataset × vote regime (bar chart)
  - **Fig. 3:** BEW/PIC pre vs post repair (grouped bar or delta plot)
- **Required tables:**
  - **Table 4:** Structural metrics summary (from `table_graph_ndcg_and_consistency.csv`)
- **Required experiments:** `pub_vote_cmp_all4` canonical suite
- **Required citations:** BEW/PIC definitions; FAS
- **Evidence:**
  - `outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv`
  - `outputs/pub_vote_cmp_all4/paper_package/tables/table_consistency_qrels_bew.csv`
  - `outputs/pub_vote_cmp_all4/analysis/*.json`
  - `scripts/build_manuscript_assets.py` (figure generation)

---

## 6. Downstream Quality Results: Repair vs Retrieval (§6)

- **Purpose:** Present decoupling — structural repair effects on nDCG are heterogeneous, often null
- **Length:** ~3 pages
- **Required figures:**
  - **Fig. 4:** Bootstrap ΔnDCG forest plot by dataset × regime × pair (Copeland, balance)
  - **Fig. 5:** Mean nDCG by method (prior, hybrids, baselines) — pooled or faceted
- **Required tables:**
  - **Table 5:** Bootstrap repair deltas (`table_bootstrap_delta_ndcg.csv`)
  - **Table 6:** Pooled baseline comparison (`final_baseline_comparison.csv`, pooled rows)
- **Required experiments:** Canonical suite + failure-mining pooled baseline
- **Required citations:** Bootstrap for IR evaluation
- **Evidence:**
  - `outputs/pub_vote_cmp_all4/paper_package/tables/table_bootstrap_delta_ndcg.csv`
  - `experiments/final_method_gap_audit_20260711_221113/task3/final_baseline_comparison.csv`
  - `experiments/publication_readiness_audit_20260711_233629/final_results_master.csv`

---

## 7. Failure Taxonomy and Diagnostic Analysis (§7)

- **Purpose:** Explain *why* repair often fails to improve retrieval; provide actionable DQ guidance
- **Length:** ~2.5 pages
- **Required figures:**
  - **Fig. 6:** Failure class distribution (pie or bar; 6 classes)
  - **Fig. 7 (optional):** SCC size vs repair delta scatter
- **Required tables:**
  - **Table 7:** Failure class frequencies and mean deltas (`manual_failure_summary.csv`)
  - **Table 8 (optional):** Minimal intervention summary (counterfactual)
- **Required experiments:** `failure_class_audit`
- **Required citations:** Error analysis in ML/IR; diagnostic evaluation
- **Evidence:**
  - `experiments/failure_class_audit_20260711_212157/phase_reports/manual_failure_summary.csv`
  - `experiments/failure_class_audit_20260711_212157/phase_reports/minimal_intervention_summary.csv`
  - `experiments/failure_class_audit_20260711_212157/phase_reports/counterfactual_repair_per_query.csv`

---

## 8. Bounded Real-LLM Validation (§8)

- **Purpose:** External validity check under genuine API pairwise judgments
- **Length:** ~1–1.5 pages
- **Required figures:** None (or small summary bar chart)
- **Required tables:**
  - **Table 9:** Real-LLM cross-dataset summary (queries, cyclicity rate, ΔnDCG, CI)
- **Required experiments:** `outputs/openai_*` pilots only
- **Required citations:** LLM-as-judge literature
- **Evidence:**
  - `outputs/openai_real_llm_cross_dataset_summary.md`
  - `docs/LLM_REAL_PILOT_RESULTS.md`
- **Limitations paragraph (mandatory):** N ≤ 50 per dataset; single provider; not confirmatory

---

## 9. CARB Benchmark (§9)

- **Purpose:** Introduce supplementary benchmark; schema; release plan
- **Length:** ~1.5 pages
- **Required figures:**
  - **Fig. 8 (optional):** CARB record structure diagram
- **Required tables:**
  - **Table 10:** CARB statistics (queries, regimes, methods, features)
- **Required experiments:** None (resource description)
- **Required citations:** Dataset paper conventions; BEIR/Benchmark positioning
- **Evidence:**
  - `experiments/created_data_audit_20260711_232004/phase10/PROPOSED_DATASET_SCHEMA.md`
  - `experiments/created_data_audit_20260711_232004/phase10/PROPOSED_RELEASE_STRUCTURE.md`
  - `experiments/created_data_audit_20260711_232004/phase6/global_feature_dictionary.csv`

---

## 10. Discussion (§10)

- **Purpose:** Interpret decoupling; practical implications; comparison to IJCS expectations; fusion suppression
- **Length:** ~2 pages
- **Required figures:** None
- **Required tables:** None
- **Required experiments:** Referenced only
- **Required citations:** DQ improvement literature; rank fusion
- **Evidence:**
  - `experiments/method_improvement_audit_20260711_205733/phase_reports/REGIME_AWARE_POLICY_REPORT.md`
  - `experiments/reviewer_response_state_audit_20260711_214959/FAILURE_CLASS_SYNTHESIS.md`
  - `final_claim_support_matrix.csv`
- **Subsections:**
  10.1 When repair is a DQ win (structural only)
  10.2 When repair is retrieval-neutral (inactive, tail-only)
  10.3 When repair is harmful (wrong-direction)
  10.4 Implications for retrieval pipeline design
  10.5 Why stronger repair does not change conclusions

---

## 11. Threats to Validity (§11)

- **Purpose:** Pre-empt reviewer attacks on validity
- **Length:** ~1 page
- **Required figures:** None
- **Required tables:** None
- **Evidence:**
  - `docs/THREATS_TO_VALIDITY.md`
  - `experiments/reviewer_response_state_audit_20260711_214959/DATASET_AND_PROTOCOL_STATUS.md`
- **Must address:**
  - BEW/PIC evaluated against same qrels (circularity)
  - Three rankers only (BM25, TF-IDF, MiniLM)
  - Protocol heterogeneity across experiment families
  - LLM pilot scale
  - ms1_drop_mutual ad-hoc regime

---

## 12. Conclusion (§12)

- **Purpose:** Summarize DQ findings; restate actionable guidance; future work
- **Length:** ~0.5–1 page
- **Evidence:** `CANONICAL_PAPER_STORY.md`

---

## 13. Data Availability and Reproducibility (§13)

- **Purpose:** CARB release; code; reproduction commands
- **Length:** ~0.5 page
- **Evidence:**
  - `docs/REPRODUCTION_Q1.md`
  - `experiments/created_data_audit_20260711_232004/phase8/RELEASE_READINESS_REPORT.md`
  - `scripts/run_publication_vote_suite.py`
  - `scripts/build_paper_evidence_package.py`

---

## 14. References

- **Format:** ACM Reference Format
- **Estimated count:** 40–60 references
- **Evidence:** `docs/LITERATURE_ALIGNMENT.md` as starting bibliography

---

## Appendices (supplementary material, not main paper)

| Appendix | Content | Source |
|----------|---------|--------|
| A | Full per-dataset baseline tables | `final_baseline_comparison.csv` |
| B | Extraction/fusion sensitivity | `extraction_fusion_complete.csv` |
| C | Exact vs greedy repair comparison | `repair_comparison_real.csv` |
| D | Selector and regime policy | `method_improvement_audit/` |
| E | Runtime evidence | `failure_class_audit/EFFICIENCY_EVIDENCE_AUDIT.md` |
| F | CARB feature dictionary | `global_feature_dictionary.csv` |
| G | Claim-evidence matrix | `final_claim_support_matrix.csv` |
| H | Reproduction manifest | `docs/REPRODUCTION_Q1.md` |

---

## Page budget summary

| Section | Pages |
|---------|-------|
| Abstract + CCS | 0.5 |
| §1 Introduction | 2.5–3 |
| §2 Related Work | 2–2.5 |
| §3 Problem Formulation | 2 |
| §4 Protocol | 2.5–3 |
| §5 Structural DQ Results | 2.5 |
| §6 Downstream Results | 3 |
| §7 Failure Taxonomy | 2.5 |
| §8 Real-LLM | 1–1.5 |
| §9 CARB | 1.5 |
| §10 Discussion | 2 |
| §11 Threats | 1 |
| §12 Conclusion | 0.5–1 |
| §13 Data Availability | 0.5 |
| References | 2–3 |
| **Total** | **~22–25** |
