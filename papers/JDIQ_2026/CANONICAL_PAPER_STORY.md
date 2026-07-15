# Canonical Paper Story for JDIQ

> **SUPERSEDED (as of 2026-07-14).** Written before the manuscript existed;
> its draft abstract/narrative below (CARB benchmark, "64% retrieval-
> inactive," six-way failure taxonomy, a narrow baseline list) does not
> match the finished `manuscript/main.tex`, which excludes the failure
> taxonomy as evidence, never mentions CARB, and reports a wider baseline
> set (adds PageRank, RankCentrality, Bradley-Terry, Markov-hybrid). Treat
> `manuscript/main.tex` as the actual paper story; this file is kept only
> as a record of the pre-writing plan.

**Prepared:** 2026-07-12  
**Venue:** ACM Journal of Data and Information Quality (JDIQ)  
**Evidence base:** `experiments/publication_readiness_audit_20260711_233629/`, `experiments/reviewer_response_state_audit_*/`, `experiments/failure_class_audit_*/`, `experiments/created_data_audit_*/`

This document defines the **single** manuscript narrative. It is derived from existing audits — not invented.

---

## Working title

**When Does Repairing Preference-Graph Inconsistency Improve Retrieval Quality? A Multi-Benchmark Data Quality Study**

Alternative titles (for consideration during writing):

- *Structural Consistency Is Not Retrieval Quality: Measuring the Impact of Preference-Graph Repair Across Four Benchmarks*
- *Diagnosing Preference-Graph Data Quality: Repair Efficacy, Failure Modes, and the CARB Benchmark*

---

## Central hypothesis

**Hypothesis:** Preference graphs derived from multi-ranker votes exhibit measurable inconsistency (cycles, large SCCs) whose severity depends on vote-extraction regime; applying a structural repair (feedback arc set removal) improves graph-level information quality metrics, but this improvement is **decoupled** from downstream retrieval quality (nDCG) in most regimes.

**Sub-hypotheses (supported):**

1. Vote construction regime (ms2 vs ms1 vs ms1_drop_mutual) is the dominant determinant of graph inconsistency.
2. Repair is **inactive** (zero retrieval delta) when graphs are near-acyclic (~64% of query×regime cases).
3. When repair is active, effects on retrieval are **heterogeneous** — positive in some regimes (HotpotQA ms1), null or negative in others.
4. Simple fusion baselines (CombSUM, RRF) outperform repaired Copeland hybrids on pooled retrieval quality.

---

## Central contribution

An **empirical data-and-information-quality study** that:

1. **Measures** preference-graph inconsistency as a DQ dimension across four public benchmarks (440 queries, 1020 query×regime records).
2. **Evaluates** a standard DQ improvement technique (acyclicity repair via FAS) on both structural metrics (cyclicity, BEW, PIC, SCC) and downstream task quality (nDCG@15).
3. **Documents** the decoupling between structural DQ improvement and retrieval DQ improvement — with bootstrap confidence intervals and a manual failure taxonomy.
4. **Introduces CARB** (Consistency-Aware Reranking Benchmark) as a curated supplementary resource for reproducible DQ research on preference graphs.

This is **not** a new algorithm paper. The contribution is **measurement, diagnosis, and curation**.

---

## Secondary contributions

| # | Contribution | Evidence |
|---|-------------|----------|
| S1 | Failure taxonomy for DQ repair interventions (6 classes; 64% inactive) | `failure_class_audit/manual_failure_summary.csv` |
| S2 | Pooled baseline comparison showing fusion methods dominate repaired hybrids | `final_method_gap_audit/task3/final_baseline_comparison.csv` |
| S3 | Regime-specific positive case (HotpotQA ms1, ΔnDCG +0.017, CI > 0) | `pub_vote_cmp_all4/table_bootstrap_delta_ndcg.csv` |
| S4 | Bounded real-LLM validation (structure–retrieval decoupling under genuine API judgments) | `outputs/openai_real_llm_cross_dataset_summary.md` |
| S5 | Exact vs greedy repair comparison (no change to retrieval conclusions) | `final_method_gap_audit/task2/` |
| S6 | CARB v0.1 schema and release plan | `created_data_audit/phase10/` |

---

## What must NOT be claimed

| Prohibited claim | Why | Classification |
|-----------------|-----|----------------|
| "Our method improves retrieval" | Proposed hybrid loses to CombSUM and prior pooled | **contradicted** |
| "Repair uniformly improves nDCG" | 64% repair_inactive; heterogeneous deltas | **contradicted** |
| "Structural consistency predicts retrieval quality" | Decoupling documented across datasets | **contradicted** |
| "Production-ready LLM reranking improvement" | No LLM judges in main suite; tiny pilots | **unsupported** |
| "A selector reliably decides when to repair" | Modest signal only; no decisive win | **exploratory_only** |
| "Real-LLM results confirm generalization" | N = 80 total; conservative null/negative | **unsupported** |
| "Memory is practical" | No real-pipeline memory benchmark | **unsupported** |
| Strict SciDocs harm with CI < 0 (from v2) | all4 CI straddles zero | **stale/wrong package** |

Full matrix: `experiments/publication_readiness_audit_20260711_233629/final_claim_support_matrix.csv`

---

## Why JDIQ is the correct venue

| JDIQ scope element | Our alignment |
|-------------------|---------------|
| Information quality in enterprise/CS context | Preference graphs are derived data assets in retrieval pipelines |
| Database-related technical solutions for IQ | Graph repair = data cleaning for cyclic preferences |
| Information curation | CARB benchmark curates 1020 query×regime evaluation records |
| Rigorous empirical methods | Bootstrap CIs, 4 datasets, failure taxonomy, baseline grid |
| Practical implications required | Actionable guidance: when repair is inactive, harmful, or irrelevant |
| Accepts diverse methods | Quasi-experimental, case-based failure analysis, benchmark curation |

JDIQ is **stronger** than IR venues (TOIS, JIIS) for this story because:

- The **primary finding is about data quality**, not a new ranking algorithm
- **Negative/null results** on retrieval are a DQ insight, not a failure
- **CARB** fits JDIQ's curation/resource mission
- Reviewers expect **practical implications**, which our failure taxonomy provides

---

## Why this story is stronger than the rejected IJCS framing

| Aspect | Rejected IJCS framing | JDIQ framing |
|--------|----------------------|--------------|
| Core claim | Consistency-aware reranking improves retrieval | Structural DQ repair decoupled from retrieval DQ |
| Evidence used | 2 datasets; positive-leaning narrative | 4 datasets; full baseline grid; failure taxonomy |
| Method positioning | Novel algorithm contribution | DQ measurement and diagnosis |
| Negative results | Underreported | Central finding (64% inactive) |
| Baselines | Narrow | CombSUM, RRF, Borda, prior, Markov, etc. |
| Failure analysis | Absent | 6-class taxonomy with counterfactuals |
| Benchmark | None | CARB (1020 records, 366 methods) |
| Real LLM | Minimal | Bounded pilots with conservative interpretation |
| Reviewer objections | "Main conclusion too natural"; "claims too broad" | Directly addressed by claim discipline |
| Venue fit | Cognitive systems / method paper | Data and information quality |

The IJCS paper asked reviewers to accept a **positive method contribution** that the evidence does not support. The JDIQ paper asks reviewers to accept a **diagnostic DQ contribution** that the evidence **does** support.

---

## Evidence summary (one paragraph for introduction)

Across four benchmarks (SciDocs, FiQA, HotpotQA, BRIGHT) and three vote-extraction regimes, we observe that graph inconsistency varies from 0% to 95% cyclic queries depending on regime, and that FAS repair reduces BEW/PIC when cycles are present. However, bootstrap analysis of 1020 query×regime records shows repair is retrieval-inactive in 64% of cases; a failure taxonomy identifies tail-only changes (21%) and wrong-direction repair (5%) as additional modes. Pooled comparison against strong baselines shows CombSUM (mean nDCG 0.462) and RRF (0.459) outperform repaired Copeland hybrids (0.439). A single regime — HotpotQA ms1 — shows positive retrieval repair effect (ΔnDCG +0.017, 95% CI [0, 0.041]). Bounded real-LLM pilots (80 queries) corroborate regime-sensitive decoupling. We release CARB, a 1020-record benchmark with 366 method outputs per query×regime.

---

## Relationship to prior audits

| Audit | Role in this story |
|-------|-------------------|
| `publication_readiness_audit_20260711_233629` | Recommended diagnostic framing (Framing C); adapted here for JDIQ DQ vocabulary |
| `reviewer_response_state_audit_20260711_214959` | Claim discipline; reviewer criticism mapping |
| `failure_class_audit_20260711_212157` | Failure taxonomy — primary Results asset |
| `final_method_gap_audit_20260711_221113` | Baseline and repair comparison tables |
| `created_data_audit_20260711_232004` | CARB schema and release plan |
| `method_improvement_audit_20260711_205733` | Regime policy — Discussion only |

---

## Paper type recommendation

**Technical / Research paper** (~20–23 pages) with **supplementary material** containing CARB schema, extended tables, and reproduction package.

Optional future companion: **Resource paper** (~10 pages) for CARB alone (not required for initial submission).
