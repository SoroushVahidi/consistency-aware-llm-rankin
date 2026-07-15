# Table Plan — JDIQ 2026

> **SUPERSEDED (as of 2026-07-14).** Pre-writing plan; its baseline-grid
> row list omits PageRank, RankCentrality, Bradley-Terry, and Markov-hybrid
> (all now in the manuscript's actual Table~\ref{tab:baselines}), and its
> "§7 Failure Taxonomy" section reference does not match the finished
> manuscript's structure. Use `manuscript/main.tex`'s actual tables, not
> this plan, as current.

**Prepared:** 2026-07-12  
**Do not generate tables yet** — plan only.  
**Canonical source:** `outputs/pub_vote_cmp_all4/paper_package/` for main results.

---

## Main paper tables

### Table 1 — Data quality dimensions and metrics

| Field | Value |
|-------|-------|
| **Purpose** | Define measured DQ dimensions and their operationalization |
| **Columns** | Dimension, Metric, Definition, Level (graph/query), Direction |
| **Rows** | Cyclicity, SCC size, Edge count, BEW, PIC, FAS weight removed, nDCG@15 |
| **Data source** | `docs/THEORETICAL_FOUNDATION.md`; metric definitions in code |
| **Generation** | Manual LaTeX from outline |
| **Section** | §3 Problem Formulation |
| **Status** | **Not started** — writing only |

---

### Table 2 — Dataset and query statistics

| Field | Value |
|-------|-------|
| **Purpose** | Summarize evaluation corpora and query counts |
| **Columns** | Dataset, Domain, #Queries (ms2), #Queries (ms1), #Queries (ms1_drop_mutual), Source |
| **Rows** | SciDocs, FiQA, HotpotQA, BRIGHT, **Total** |
| **Data source** | `table_graph_ndcg_and_consistency.csv` (`n_queries` column) |
| **Generation** | Extract from canonical CSV |
| **Section** | §4 Protocol |
| **Status** | **Exists in source** — needs formatting |

**Source values (from canonical CSV):**

| Dataset | ms2 | ms1 | ms1_drop_mutual |
|---------|-----|-----|-----------------|
| scidocs | 119 | 120 | 120 |
| fiqa | 117 | 120 | 120 |
| hotpotqa | 52 | 52 | 52 |
| bright | 34 | 50 | 50 |

---

### Table 3 — Method inventory

| Field | Value |
|-------|-------|
| **Purpose** | List all compared ranking methods |
| **Columns** | Method, Type, Repair?, Fusion?, Description |
| **Rows** | prior_only, CombSUM, RRF, Borda, score_sum, Copeland U/R, balance U/R, Markov U/R, proposed_hybrid |
| **Data source** | `final_baseline_comparison.csv`; `table_graph_ndcg_and_consistency.csv` column names |
| **Generation** | Manual from protocol docs |
| **Section** | §4 Protocol |
| **Status** | **Not started** — writing only |

---

### Table 4 — Structural DQ metrics by dataset and regime

| Field | Value |
|-------|-------|
| **Purpose** | Main structural results table |
| **Columns** | Dataset, Regime, n, %Cyclic, Avg SCC, Avg edges, BEW pre, BEW post, ΔBEW, Weight removed |
| **Rows** | 12 rows (4 datasets × 3 regimes) |
| **Data source** | `outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv` + `table_consistency_qrels_bew.csv` |
| **Generation** | `scripts/build_paper_evidence_package.py` or direct CSV → LaTeX |
| **Section** | §5 Structural DQ Results |
| **Status** | **Exists** — use canonical CSV directly |

---

### Table 5 — Bootstrap repair ΔnDCG@15

| Field | Value |
|-------|-------|
| **Purpose** | Retrieval effect of repair with confidence intervals |
| **Columns** | Dataset, Regime, Pair, n, Mean Δ, CI low, CI high |
| **Rows** | Copeland + balance rows from bootstrap CSV (exclude SCC subgroups for main table) |
| **Data source** | `outputs/pub_vote_cmp_all4/paper_package/tables/table_bootstrap_delta_ndcg.csv` |
| **Generation** | Direct from canonical CSV |
| **Section** | §6 Downstream Results |
| **Status** | **Exists** — canonical |

**Key rows to highlight in text:**

- HotpotQA ms1 copeland: mean +0.0167, CI [0, 0.0405]
- SciDocs ms1 copeland: mean −1.27e-4, CI straddles 0
- All ms2/ms1_drop_mutual: mean 0, CI [0, 0]

---

### Table 6 — Pooled baseline comparison

| Field | Value |
|-------|-------|
| **Purpose** | Show proposed method does not beat strong baselines |
| **Columns** | Method, n, Mean nDCG, Median, CI low, CI high, W/T/L vs prior, W/T/L vs best fixed |
| **Rows** | prior_only, borda, rrf, combsum, score_sum, copeland U/R, markov U/R, balance, proposed_hybrid, best_stronger_repair |
| **Data source** | `experiments/final_method_gap_audit_20260711_221113/task3/final_baseline_comparison.csv` (scope=pooled) |
| **Generation** | Filter pooled rows; format to LaTeX |
| **Section** | §6 Downstream Results |
| **Status** | **Exists** — needs formatting |
| **Protocol note** | Label as failure-mining pooled protocol; distinct from Table 5

---

### Table 7 — Failure class taxonomy

| Field | Value |
|-------|-------|
| **Purpose** | Diagnostic failure modes for DQ repair interventions |
| **Columns** | Class, Count, Fraction, Mean ΔnDCG, Median ΔnDCG, Mean SCC, Description |
| **Rows** | repair_inactive, tail_only_change, wrong_direction_repair, metric_neutral_ranking_change, extraction_insensitivity, unknown_or_mixed |
| **Data source** | `experiments/failure_class_audit_20260711_212157/phase_reports/manual_failure_summary.csv` |
| **Generation** | Direct from CSV |
| **Section** | §7 Failure Taxonomy |
| **Status** | **Exists** — canonical |

---

### Table 8 — Minimal intervention summary (optional main / appendix)

| Field | Value |
|-------|-------|
| **Purpose** | Show `no_repair` is minimal fix for harmful cases |
| **Columns** | Intervention, Cases, Mean Δ, Success rate |
| **Data source** | `failure_class_audit/phase_reports/minimal_intervention_summary.csv` |
| **Section** | §7 or Appendix |
| **Status** | **Exists** — verify completeness |

---

### Table 9 — Real-LLM cross-dataset summary

| Field | Value |
|-------|-------|
| **Purpose** | Bounded external validation under API pairwise judgments |
| **Columns** | Dataset, Queries, Cyclic rate, Best method, Best nDCG, ΔnDCG (repair), 95% CI |
| **Rows** | SciDocs 50q, HotpotQA 20q, FiQA 10q |
| **Data source** | `outputs/openai_real_llm_cross_dataset_summary.md` |
| **Generation** | Manual from summary doc |
| **Section** | §8 Real-LLM Validation |
| **Status** | **Exists** — summary doc ready |

---

### Table 10 — CARB benchmark statistics

| Field | Value |
|-------|-------|
| **Purpose** | Describe supplementary benchmark resource |
| **Columns** | Statistic, Value |
| **Rows** | Independent queries, Query×regime records, Methods per record, Feature groups, Source datasets, Valid labels, LLM judgments |
| **Data source** | `created_data_audit/FINAL_REPORT.md`; `phase10/PROPOSED_DATASET_SCHEMA.md` |
| **Generation** | Manual from audit |
| **Section** | §9 CARB Benchmark |
| **Status** | **Exists** — audit complete |

**Values:**

| Statistic | Value |
|-----------|-------|
| Independent queries | 440 |
| Query×regime records | 1020 |
| Methods per record | 366 |
| Feature groups | 14+ |
| Source datasets | SciDocs, FiQA, HotpotQA, BRIGHT |

---

## Supplementary tables

| ID | Title | Source | Appendix |
|----|-------|--------|----------|
| ST1 | Per-dataset baseline breakdown | `final_baseline_comparison.csv` (non-pooled) | A |
| ST2 | Extraction/fusion sensitivity | `extraction_fusion_complete.csv` | B |
| ST3 | Exact vs greedy repair | `repair_comparison_real.csv` | C |
| ST4 | Selector feature importance | `selector_llm_extension/table_failure_features.csv` | D |
| ST5 | Runtime per query | `failure_class_audit/runtime_per_query.csv` | E |
| ST6 | CARB feature dictionary | `global_feature_dictionary.csv` | F |
| ST7 | Claim-evidence matrix | `final_claim_support_matrix.csv` | G |
| ST8 | BEW/PIC full table | `table_consistency_qrels_bew.csv` | H |
| ST9 | SCC-stratified bootstrap | `table_bootstrap_delta_ndcg.csv` (SCC rows) | H |
| ST10 | Counterfactual validity | `counterfactual_validity_summary.csv` | I |

---

## Tables to NOT use

| Table | Location | Reason |
|-------|----------|--------|
| table_1_main_performance | `outputs/manuscript_artifacts/` | Pre-all4; stale |
| q1_journal_package tables | `outputs/q1_journal_package/` | Built from v2 |
| pub_vote_cmp_v2 tables | `outputs/pub_vote_cmp_v2/` | Conflicts with all4 |
| docs/tables/main_results.csv | `docs/tables/` | Legacy; verify date |

---

## Generation workflow

```bash
# Canonical tables (already committed)
ls outputs/pub_vote_cmp_all4/paper_package/tables/

# Regenerate if needed (requires local run trees)
python scripts/run_publication_vote_suite.py  # if outputs missing
python scripts/build_paper_evidence_package.py --root outputs/pub_vote_cmp_all4

# Format for LaTeX (to be written)
python papers/JDIQ_2026/scripts/format_tables.py  # future script
```

---

## Status summary

| Table | Source exists? | Formatted for paper? |
|-------|---------------|---------------------|
| T1 | N/A (conceptual) | No |
| T2 | Yes | No |
| T3 | Partial | No |
| T4 | **Yes (canonical)** | No |
| T5 | **Yes (canonical)** | No |
| T6 | **Yes** | No |
| T7 | **Yes** | No |
| T8 | Yes | No |
| T9 | Yes | No |
| T10 | Yes | No |

**Table readiness:** ~60% (data exists; 0% formatted for LaTeX)
