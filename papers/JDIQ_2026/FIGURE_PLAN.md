# Figure Plan — JDIQ 2026

**Prepared:** 2026-07-12  
**Total main-paper figures:** 6 mandatory + 2 optional  
**Do not generate yet** — plan only.

---

## Fig. 1 — Preference-graph DQ pipeline schematic

| Field | Value |
|-------|-------|
| **Purpose** | Introduce data flow: rankers → votes → preference graph → DQ metrics → repair → reranking → retrieval evaluation |
| **Data source** | Conceptual (no empirical data) |
| **Script** | **New:** `papers/JDIQ_2026/scripts/fig01_pipeline.py` (TikZ or matplotlib) |
| **Caption concept** | "Pipeline for measuring preference-graph data quality and evaluating the impact of acyclicity repair on downstream retrieval. Three vote-extraction regimes produce graphs with varying cyclicity." |
| **Importance** | **High** — orients JDIQ readers to DQ framing |
| **Already exists?** | No |
| **Regeneration required?** | **New creation** |
| **Section** | §3 Problem Formulation |
| **Format** | Vector PDF (preferred) or 300+ dpi PNG |

---

## Fig. 2 — Cyclicity rate by dataset and vote regime

| Field | Value |
|-------|-------|
| **Purpose** | Show vote construction is dominant determinant of graph inconsistency |
| **Data source** | `outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv` (column: `pct_cyclic`) |
| **Script** | `scripts/build_manuscript_assets.py` → `figures/manuscript/fig_cyclicity_and_scc.png` |
| **Caption concept** | "Percentage of cyclic queries and mean largest SCC size across four benchmarks and three vote-extraction regimes. ms1 produces 52–95% cyclic queries; ms2 and ms1_drop_mutual are near-acyclic." |
| **Importance** | **High** — key structural DQ result |
| **Already exists?** | Referenced in `figures/manuscript/README.md`; may need regeneration |
| **Regeneration required?** | **Yes** — run `build_manuscript_assets.py` on all4 |
| **Section** | §5 Structural DQ Results |

---

## Fig. 3 — BEW/PIC consistency pre- and post-repair

| Field | Value |
|-------|-------|
| **Purpose** | Show repair reduces graph–reference inconsistency when cycles present |
| **Data source** | `table_consistency_qrels_bew.csv`; `table_graph_ndcg_and_consistency.csv` |
| **Script** | `scripts/build_manuscript_assets.py` → `fig_graph_qrels_bew_pre_post.png` |
| **Caption concept** | "Mean graph–qrels BEW and PIC before and after FAS repair. Reductions occur primarily in ms1 regimes with non-zero weight removed." |
| **Importance** | **High** — demonstrates DQ improvement on structural metrics |
| **Already exists?** | Referenced in README; may need regeneration |
| **Regeneration required?** | **Yes** |
| **Section** | §5 Structural DQ Results |
| **Caveat in caption** | Note BEW/PIC use same qrels as evaluation |

---

## Fig. 4 — Bootstrap ΔnDCG forest plot

| Field | Value |
|-------|-------|
| **Purpose** | Visualize heterogeneous, often-null repair effects on retrieval |
| **Data source** | `table_bootstrap_delta_ndcg.csv`; `outputs/pub_vote_cmp_all4/analysis/*_delta_*.json` |
| **Script** | `scripts/build_manuscript_assets.py` → `fig_delta_ndcg_bootstrap.png` |
| **Caption concept** | "Bootstrap mean ΔnDCG@15 (repaired − unrepaired) with 95% CIs for Copeland and balance hybrids. Most ms2/ms1_drop_mutual intervals are [0,0]; HotpotQA ms1 Copeland shows positive interval." |
| **Importance** | **Critical** — central decoupling evidence |
| **Already exists?** | Referenced in README |
| **Regeneration required?** | **Yes** |
| **Section** | §6 Downstream Results |

---

## Fig. 5 — Mean nDCG by method (baseline comparison)

| Field | Value |
|-------|-------|
| **Purpose** | Show fusion baselines outperform repaired hybrids |
| **Data source** | `final_baseline_comparison.csv` (pooled scope); `table_graph_ndcg_and_consistency.csv` |
| **Script** | `scripts/build_manuscript_assets.py` → `fig_mean_ndcg_hybrids.png`; supplement with new bar chart from baseline CSV |
| **Caption concept** | "Mean nDCG@15 by method pooled across 1020 query×regime records. CombSUM and RRF outperform repaired Copeland and the proposed hybrid." |
| **Importance** | **High** — negative result for method contribution |
| **Already exists?** | Partial (`fig_mean_ndcg_hybrids.png`) |
| **Regeneration required?** | **Yes** — extend to include full baseline grid |
| **Section** | §6 Downstream Results |

---

## Fig. 6 — Failure class distribution

| Field | Value |
|-------|-------|
| **Purpose** | Show dominant failure modes (repair_inactive 64%, tail_only 21%) |
| **Data source** | `experiments/failure_class_audit_20260711_212157/phase_reports/manual_failure_summary.csv` |
| **Script** | **New:** `papers/JDIQ_2026/scripts/fig06_failure_classes.py` |
| **Caption concept** | "Distribution of manual failure classes across 1020 query×regime records. Repair is retrieval-inactive in 64% of cases; tail-only ranking changes account for 21%." |
| **Importance** | **Critical** — actionable DQ diagnostic |
| **Already exists?** | No |
| **Regeneration required?** | **New creation** |
| **Section** | §7 Failure Taxonomy |

---

## Fig. 7 — SCC size vs repair ΔnDCG (optional)

| Field | Value |
|-------|-------|
| **Purpose** | Explore whether cyclicity severity predicts repair benefit |
| **Data source** | `failure_class_audit/phase_reports/counterfactual_repair_per_query.csv` or per-query records |
| **Script** | **New:** `papers/JDIQ_2026/scripts/fig07_scc_scatter.py` |
| **Caption concept** | "Scatter of largest SCC size vs repair ΔnDCG. No strong linear relationship; decoupling visible." |
| **Importance** | **Medium** — supports decoupling narrative |
| **Already exists?** | No |
| **Regeneration required?** | **New creation** |
| **Section** | §7 Failure Taxonomy (optional) |

---

## Fig. 8 — CARB record structure (optional)

| Field | Value |
|-------|-------|
| **Purpose** | Illustrate benchmark unit of observation (query × regime × method) |
| **Data source** | `experiments/created_data_audit_20260711_232004/phase10/PROPOSED_DATASET_SCHEMA.md` |
| **Script** | **New:** manual TikZ or draw.io |
| **Caption concept** | "CARB record structure: each row encodes one query×regime×method with graph features, repair outcomes, and ranking metrics." |
| **Importance** | **Medium** — helps resource reviewers |
| **Already exists?** | No |
| **Regeneration required?** | **New creation** |
| **Section** | §9 CARB Benchmark (optional) |

---

## Supplementary figures

| ID | Content | Source | Script |
|----|---------|--------|--------|
| SF1 | Per-dataset baseline breakdown | `final_baseline_comparison.csv` | New |
| SF2 | Extraction/fusion sensitivity | `extraction_fusion_complete.csv` | New |
| SF3 | Runtime scaling (synthetic) | `outputs/scale_sweep_n20/` | Existing data |
| SF4 | Exact vs greedy repair | `repair_comparison_real.csv` | New |
| SF5 | Real-LLM cyclicity rates | `openai_real_llm_cross_dataset_summary.md` | New |

---

## Figure generation workflow

```bash
# Step 1: Regenerate from canonical suite
python scripts/build_manuscript_assets.py  # outputs to figures/manuscript/

# Step 2: Copy to JDIQ workspace
cp figures/manuscript/*.png papers/JDIQ_2026/figures/

# Step 3: Generate new figures
python papers/JDIQ_2026/scripts/fig06_failure_classes.py
python papers/JDIQ_2026/scripts/fig01_pipeline.py  # when written
```

---

## Style guidelines

- Colorblind-safe palette (Okabe-Ito or similar)
- Font size ≥ 8pt at final print size
- Error bars / CIs where applicable (Fig 4)
- Consistent dataset colors across all figures
- Vector format for TikZ/ggplot; 300 dpi minimum for raster

---

## Status summary

| Figure | Status | Action |
|--------|--------|--------|
| Fig 1 | **Missing** | Create new |
| Fig 2 | **Exists (stale?)** | Regenerate |
| Fig 3 | **Exists (stale?)** | Regenerate |
| Fig 4 | **Exists (stale?)** | Regenerate |
| Fig 5 | **Partial** | Regenerate + extend |
| Fig 6 | **Missing** | Create new |
| Fig 7 | **Missing** | Optional create |
| Fig 8 | **Missing** | Optional create |

**Figure readiness:** ~25% (2/6 may exist but need regeneration; 4 need creation)
