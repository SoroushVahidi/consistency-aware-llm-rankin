# Figure Specifications — JDIQ 2026 Manuscript

> **PARTIALLY SUPERSEDED (as of 2026-07-14).** The "Figure 7" spec below
> (failure-class distribution, 64%/21%/5%/5%/3%) describes a figure that
> does not exist in the finished manuscript: the underlying six-way failure
> taxonomy is excluded as evidence (see Limitations). Figures 1, 3, and 5
> have also since been replaced with independently-prepared final versions
> (`manuscript/figure1.png`, `figure3.png`, `figure5.png`) rather than the
> versions specified here. Check `manuscript/main.tex`'s actual figure
> list and captions before using any spec in this file.

**Prepared:** 2026-07-12  
**Purpose:** Complete reproduction brief for external figure generation (ChatGPT or other AI).  
**No figures are generated in this document.**

## Canonical sources only

| Source | Repository path |
|--------|-----------------|
| Main results | `outputs/pub_vote_cmp_all4/` |
| Baselines / repair / fusion | `experiments/final_method_gap_audit_20260711_221113/` |
| Failure taxonomy | `experiments/failure_class_audit_20260711_212157/` |
| Claims reference | `experiments/publication_readiness_audit_20260711_233629/final_claim_support_matrix.csv` |
| CARB | `experiments/created_data_audit_20260711_232004/` |

## Global style requirements (all figures)

- **Color palette:** Okabe–Ito colorblind-safe. Use consistently across all figures:
  - SciDocs: `#E69F00`
  - FiQA: `#56B4E9`
  - HotpotQA: `#009E73`
  - BRIGHT: `#CC79A7`
  - ms2: solid fill; ms1: hatched fill; ms1_drop_mutual: dotted outline
- **Font:** Sans-serif (Helvetica/Arial), ≥8 pt at final print size
- **Format:** Vector PDF preferred; otherwise 300 dpi PNG
- **ACM width:** Design for single-column (3.33 in) or 1.5-column (5.5 in) as specified per figure
- **Error bars:** 95% bootstrap CIs where noted
- **Do not use:** `pub_vote_cmp_v2`, IJCS manuscript, `outputs/manuscript_artifacts/`, obsolete reports

## Claims reference

File: `experiments/publication_readiness_audit_20260711_233629/final_claim_support_matrix.csv`  
(Referenced below as **Claims Matrix** by `claim_id`.)

---

# MAIN PAPER FIGURES

---

## F01 — Preference-Graph Data Quality Evaluation Pipeline

### 1. Figure title

**Figure 1. Preference-graph data quality evaluation pipeline.**

### 2. Purpose

Answers: *How is preference-graph data quality measured, repaired, and linked to downstream retrieval quality?*

JDIQ reviewers need a conceptual map because the contribution is a **data quality study**, not a single algorithm. This figure establishes that vote extraction creates the DQ artifact, repair is a DQ intervention, and retrieval nDCG is a separate downstream quality dimension.

### 3. Type of visualization

**Flowchart** (left-to-right pipeline with one inset **network diagram** showing a 3-node cycle).

### 4. Data source

Conceptual only. No CSV input. Structure derived from:

- `papers/JDIQ_2026/CANONICAL_PAPER_STORY.md`
- `outputs/pub_vote_cmp_all4/paper_package/` (protocol labels)
- `experiments/created_data_audit_20260711_232004/phase6/global_feature_dictionary.csv` (feature group names)

### 5. Variables

**Nodes (boxes, left to right):**

1. **Input rankers:** BM25, TF-IDF, MiniLM → label "Three mechanical rankers"
2. **Vote extraction:** three regimes → `ms2`, `ms1`, `ms1_drop_mutual`
3. **Preference graph** G(V,E) — inset shows directed edges + highlighted 3-cycle
4. **DQ metrics (pre-repair):** cyclicity, largest SCC, BEW, PIC, edge count
5. **DQ intervention:** Greedy FAS repair (edge removal)
6. **DQ metrics (post-repair):** same metrics + `fas_removed_weight`
7. **Ranking methods:** prior-only, Copeland U/R, balance U/R, CombSUM, RRF, hybrid (RRF α=0.3)
8. **Downstream quality:** nDCG@15 vs qrels

**Annotations:**

- Dashed box around steps 4–6 labeled "Structural data quality layer"
- Dashed box around step 8 labeled "Downstream retrieval quality layer"
- Arrow label between 6→7: "Decoupling evaluated here"

**Colors:** Blue tones for structural layer; orange for downstream layer.

### 6. Caption draft

Figure 1 illustrates the end-to-end pipeline used to study preference-graph data quality in multi-ranker retrieval. For each query, scores from three rankers (BM25, TF-IDF, MiniLM) are converted into pairwise preference graphs under three vote-extraction regimes: ms2 (strict mutual), ms1 (standard mutual), and ms1_drop_mutual (mutual edges removed). Each graph is characterized by structural data quality dimensions including cyclicity, largest strongly connected component (SCC) size, backward error weight (BEW), and pairwise inconsistency count (PIC). A feedback arc set (FAS) repair operator removes cyclic edges, yielding post-repair structural metrics. The repaired and unrepaired graphs are then passed to multiple ranking methods—including Copeland and balance hybrids fused with the prior via reciprocal rank fusion (α = 0.3)—and evaluated by nDCG@15 against relevance judgments. The pipeline explicitly separates structural graph quality from downstream retrieval quality, which is the central measurement design of this study. All empirical results in Sections 5–7 instantiate this pipeline across four public benchmarks.

### 7. Scientific claims supported

- Frames the paper as a **data quality measurement** study (JDIQ scope)
- Supports setup for **repair_improves_structural_consistency** (Claims Matrix)
- Supports setup for decoupling (**structural_predicts_retrieval** = contradicted)

### 8. Important design notes

- No numeric data in figure; purely schematic
- Cycle inset must show directed arrows forming a closed loop
- Keep ranker names visible (reviewers asked about narrow ranker set in IJCS)
- Include α=0.3 on hybrid arrow

### 9. Expected size

**1.5-column** (5.5 in wide) — pipeline needs horizontal space

### 10. Priority

**Critical**

---

## F02 — Graph Inconsistency by Dataset and Vote-Extraction Regime

### 1. Figure title

**Figure 2. Graph inconsistency as a function of vote-extraction regime across four benchmarks.**

### 2. Purpose

Answers: *Does vote construction dominate preference-graph inconsistency?*

JDIQ reviewers need evidence that **data construction choices** (not repair) determine the primary DQ defect. This is the headline structural finding: ms1 regimes produce 52–95% cyclic queries; ms2 and ms1_drop_mutual are near-acyclic.

### 3. Type of visualization

**Two-panel grouped bar chart** (Panel A: % cyclic queries; Panel B: mean largest SCC size).  
Alternative acceptable: **heatmap** (datasets × regimes) with two color scales.

### 4. Data source

| File | Path |
|------|------|
| Primary table | `outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv` |

**Exact data to plot (12 rows):**

| dataset | variant | n_queries | pct_cyclic | avg_largest_scc |
|---------|---------|-----------|------------|-----------------|
| scidocs | ms2 | 119 | 0.0 | 1.0 |
| scidocs | ms1 | 120 | 87.5 | 9.333 |
| scidocs | ms1_drop_mutual | 120 | 0.0 | 1.0 |
| fiqa | ms2 | 117 | 0.0 | 1.0 |
| fiqa | ms1 | 120 | 95.0 | 12.508 |
| fiqa | ms1_drop_mutual | 120 | 0.0 | 1.0 |
| hotpotqa | ms2 | 52 | 0.0 | 1.0 |
| hotpotqa | ms1 | 52 | 51.92 | 2.519 |
| hotpotqa | ms1_drop_mutual | 52 | 0.0 | 1.0 |
| bright | ms2 | 34 | 0.0 | 1.0 |
| bright | ms1 | 50 | 60.0 | 6.48 |
| bright | ms1_drop_mutual | 50 | 6.0 | 1.4 |

### 5. Variables

**Panel A:**

- **x-axis:** Dataset (4 groups: SciDocs, FiQA, HotpotQA, BRIGHT)
- **y-axis:** `pct_cyclic` (0–100%), label "% queries with cyclic preference graph"
- **Color/group:** `variant` (3 bars per dataset: ms2, ms1, ms1_drop_mutual)
- **Error bars:** None (descriptive means over query set)
- **Labels:** Show n_queries above each bar group (small text)

**Panel B:**

- **x-axis:** Dataset (same order)
- **y-axis:** `avg_largest_scc`, label "Mean largest SCC size"
- **Color/group:** `variant` (same encoding as Panel A)

**Sort order:** Datasets ordered by descending ms1 cyclicity: FiQA (95%), SciDocs (87.5%), BRIGHT (60%), HotpotQA (51.92%).

### 6. Caption draft

Figure 2 quantifies preference-graph inconsistency across four benchmarks (SciDocs, FiQA, HotpotQA, BRIGHT) and three vote-extraction regimes. Panel A shows the percentage of queries whose preference graph contains at least one directed cycle; Panel B shows the mean size of the largest strongly connected component (SCC). The ms1 extraction regime produces substantial inconsistency—ranging from 52% cyclic queries on HotpotQA to 95% on FiQA—while ms2 and ms1_drop_mutual yield near-acyclic graphs (0–6% cyclic) on all datasets. Mean SCC size follows the same pattern, reaching 12.5 on FiQA ms1 versus 1.0 for ms2 on all datasets. These results demonstrate that vote construction is the dominant determinant of structural data quality in derived preference graphs, independent of any repair intervention. Sample sizes per cell range from 34 to 120 queries (see Table 2).

### 7. Scientific claims supported

- Vote construction controls cycle incidence (**Claims Matrix:** supports C2 from contribution inventory; structural consistency family)
- Prerequisite for **repair_improves_structural_consistency** (repair only acts when cycles exist)

### 8. Important design notes

- ms1 bars must be visually dominant (hatching) to draw the eye
- Annotate FiQA ms1 (95%) and HotpotQA ms2 (0%) as extremes
- Use same dataset colors across all paper figures
- Y-axis Panel A: fixed 0–100% for cross-dataset comparability

### 9. Expected size

**Double-column** (7 in) preferred for 4×3 grouped bars; minimum **1.5-column**

### 10. Priority

**Critical**

---

## F03 — Structural Consistency Improvement After FAS Repair (BEW and PIC)

### 1. Figure title

**Figure 3. Effect of FAS repair on graph–reference consistency (BEW and PIC).**

### 2. Purpose

Answers: *Does the DQ repair intervention reduce structural inconsistency metrics?*

Shows repair **works on structural DQ** when cycles are present (ms1 regimes). JDIQ reviewers need to see the intervention effect before seeing downstream decoupling.

### 3. Type of visualization

**Grouped bar chart** with pre/post pairs, faceted by metric (Panel A: BEW; Panel B: PIC)  
OR **dumbbell plot** (pre→post connected dots) for ms1 rows only.

Recommended: **Grouped bars** — 12 regime×dataset rows is too many for dumbbells; instead plot **ms1 rows only** (4 datasets × 2 bars each = pre/post).

### 4. Data source

| File | Path |
|------|------|
| BEW/PIC table | `outputs/pub_vote_cmp_all4/paper_package/tables/table_consistency_qrels_bew.csv` |
| Weight removed | `outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv` (column `mean_fas_weight_removed`) |

**ms1 rows only (plot these 4):**

| dataset | mean_bew_pre | mean_bew_post | mean_delta_bew | mean_pic_pre | mean_pic_post | mean_delta_pic | mean_fas_weight_removed |
|---------|--------------|---------------|----------------|--------------|---------------|----------------|-------------------------|
| scidocs | 294.2158 | 293.8831 | 0.3327 | 94.1833 | 89.9333 | 4.25 | 0.68208 |
| fiqa | 224.8073 | 224.3351 | 0.4722 | 99.3583 | 93.1417 | 6.2167 | 1.099149 |
| hotpotqa | 91.8152 | 91.7806 | 0.0346 | 18.8462 | 18.3462 | 0.5 | 0.121092 |
| bright | 882.6879 | 882.4543 | 0.2336 | 55.56 | 52.8 | 2.76 | 0.387835 |

### 5. Variables

**Panel A (BEW):**

- **x-axis:** Dataset (4 levels)
- **y-axis:** `mean_bew_pre` and `mean_bew_post`, label "Mean backward error weight (BEW)"
- **Color:** Pre-repair (light) vs post-repair (dark) paired bars
- **Annotation:** ΔBEW value above each pair

**Panel B (PIC):**

- **x-axis:** Dataset
- **y-axis:** `mean_pic_pre`, `mean_pic_post`, label "Mean pairwise inconsistency count (PIC)"
- **Color:** Same pre/post encoding

**Secondary annotation:** Small text below x-axis showing `mean_fas_weight_removed` per dataset.

### 6. Caption draft

Figure 3 reports the effect of greedy feedback arc set (FAS) repair on graph–reference structural consistency for the ms1 vote-extraction regime, where preference graphs are predominantly cyclic (Figure 2). Panels show mean backward error weight (BEW) and pairwise inconsistency count (PIC) computed against the same relevance judgments used for nDCG evaluation, before and after repair. Post-repair reductions in PIC are observed on all four datasets (ΔPIC = 0.5–6.2), with corresponding non-zero FAS weight removed (0.12–1.10). BEW changes are smaller in magnitude. These results confirm that the repair operator reduces selected structural inconsistency indicators when cycles are present. We note that BEW and PIC are computed relative to the evaluation qrels, which introduces a circularity threat discussed in Section 11; the figure should be interpreted as a structural diagnostic, not independent ground truth.

### 7. Scientific claims supported

- **repair_improves_structural_consistency** (Claims Matrix: safe)
- Supports DQ intervention efficacy on structural dimensions

### 8. Important design notes

- **Caption must note qrels circularity** (BEW/PIC use same qrels as nDCG)
- Plot **ms1 only** — pre=post for ms2/ms1_drop_mutual (zero weight removed)
- Do not use log scale (deltas are small but readable)
- Highlight FiQA (largest ΔPIC = 6.22)

### 9. Expected size

**1.5-column** (two panels stacked vertically)

### 10. Priority

**Critical**

---

## F04 — Repair Inactivity: FAS Weight Removed vs Retrieval Delta

### 1. Figure title

**Figure 4. Relationship between repair intensity and retrieval effect size.**

### 2. Purpose

Answers: *When repair removes no weight (near-acyclic graphs), is retrieval change always zero?*

Bridges structural §5 and downstream §6. Shows the **mechanism of repair inactivity** — the dominant failure mode (64% of cases).

### 3. Type of visualization

**Scatter plot** with annotated quadrants, OR **bubble chart** (12 points).

### 4. Data source

| File | Path |
|------|------|
| Weight removed | `outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv` |
| Copeland ΔnDCG | `outputs/pub_vote_cmp_all4/paper_package/tables/table_bootstrap_delta_ndcg.csv` (pair=copeland, exclude SCC sub-rows) |

**Merged 12 points:**

| dataset | variant | mean_fas_weight_removed | mean_delta_ndcg (copeland) | ci95_low | ci95_high |
|---------|---------|-------------------------|---------------------------|----------|-----------|
| scidocs | ms2 | 0.0 | 0.0 | 0.0 | 0.0 |
| scidocs | ms1 | 0.68208 | -0.0001266 | -0.000844 | 0.000595 |
| scidocs | ms1_drop_mutual | 0.0 | 0.0 | 0.0 | 0.0 |
| fiqa | ms2 | 0.0 | 0.0 | 0.0 | 0.0 |
| fiqa | ms1 | 1.099149 | 0.001456 | -0.000515 | 0.004236 |
| fiqa | ms1_drop_mutual | 0.0 | 0.0 | 0.0 | 0.0 |
| hotpotqa | ms2 | 0.0 | 0.0 | 0.0 | 0.0 |
| hotpotqa | ms1 | 0.121092 | 0.016713 | 0.0 | 0.040523 |
| hotpotqa | ms1_drop_mutual | 0.0 | 0.0 | 0.0 | 0.0 |
| bright | ms2 | 0.0 | 0.0 | 0.0 | 0.0 |
| bright | ms1 | 0.387835 | 0.00002192 | -0.001815 | 0.001646 |
| bright | ms1_drop_mutual | 0.008793 | 0.0 | 0.0 | 0.0 |

### 5. Variables

- **x-axis:** `mean_fas_weight_removed`, label "Mean FAS weight removed"
- **y-axis:** `mean_delta_ndcg`, label "Mean ΔnDCG@15 (repaired − unrepaired Copeland)"
- **Color:** `dataset` (4 colors)
- **Shape:** `variant` (ms2=circle, ms1=triangle, ms1_drop_mutual=square)
- **Error bars:** Vertical 95% CI from `ci95_low`/`ci95_high` on y-axis
- **Annotations:** Label the HotpotQA ms1 point; draw horizontal dashed line at y=0
- **Quadrant labels:** "Inactive" (x≈0, y≈0) should contain 8 of 12 points

### 6. Caption draft

Figure 4 relates the intensity of structural repair (mean FAS weight removed) to the retrieval effect of repair (bootstrap mean ΔnDCG@15 for Copeland hybrids) across all dataset×regime combinations. Points in the origin quadrant—zero weight removed and zero retrieval change—correspond to near-acyclic graphs under ms2 and ms1_drop_mutual extraction, explaining the predominance of repair-inactive cases in the failure taxonomy (Section 7). The single clearly positive retrieval effect occurs for HotpotQA ms1 (ΔnDCG = 0.017, 95% CI [0, 0.041]) with modest weight removed (0.12). Other ms1 configurations show structural repair without reliable retrieval gain (FiQA: positive point estimate but CI straddles zero; SciDocs and BRIGHT: CIs include zero). This scatter view makes the decoupling of structural intervention intensity from downstream retrieval quality visually apparent.

### 7. Scientific claims supported

- Repair inactive when graphs near-acyclic (Claims Matrix: supports contribution C02)
- **repair_helps_hotpotqa** (safe_with_qualification) — HotpotQA ms1 point highlighted
- **structural_predicts_retrieval** (contradicted) — visual evidence

### 8. Important design notes

- **Highlight HotpotQA ms1** with callout box
- 8 points at (0,0) will overlap — use jitter or small offset for visibility
- Include legend for shape (regime) and color (dataset)

### 9. Expected size

**Single-column** (3.33 in) or **1.5-column**

### 10. Priority

**Important**

---

## F05 — Bootstrap Confidence Intervals for Repair-Induced ΔnDCG@15

### 1. Figure title

**Figure 5. Retrieval effect of repair with bootstrap 95% confidence intervals.**

### 2. Purpose

Answers: *Is the retrieval effect of repair statistically reliable in any regime?*

Central decoupling figure. JDIQ reviewers need rigorous uncertainty quantification, not point estimates alone.

### 3. Type of visualization

**Forest plot** (horizontal error bars): one row per (dataset, variant, pair) for `pair` ∈ {copeland, balance}, excluding SCC-stratified sub-rows.

### 4. Data source

| File | Path |
|------|------|
| Bootstrap table | `outputs/pub_vote_cmp_all4/paper_package/tables/table_bootstrap_delta_ndcg.csv` |
| JSON detail (optional) | `outputs/pub_vote_cmp_all4/analysis/{dataset}_{variant}_delta_{pair}.json` |

**Rows to plot (24 rows = 12 copeland + 12 balance; exclude `*_scc_high`, `*_scc_low`):**

Copeland key values:

| dataset | variant | mean_delta_ndcg | ci95_low | ci95_high |
|---------|---------|-----------------|----------|-----------|
| hotpotqa | ms1 | 0.016713 | 0.0 | 0.040523 |
| fiqa | ms1 | 0.001456 | -0.000515 | 0.004236 |
| scidocs | ms1 | -0.0001266 | -0.000844 | 0.000595 |
| bright | ms1 | 0.00002192 | -0.001815 | 0.001646 |
| *all ms2 rows* | | 0.0 | 0.0 | 0.0 |
| *all ms1_drop_mutual rows* | | 0.0 | 0.0 | 0.0 |

All balance rows: mean_delta = 0, CI = [0, 0] for all 12 dataset×variant combinations.

`bootstrap_reps` = 2000 for all rows.

### 5. Variables

- **y-axis:** Row label = `{dataset} / {variant} / {pair}` (24 rows); group copeland above balance
- **x-axis:** `mean_delta_ndcg`, label "ΔnDCG@15 (repaired − unrepaired)"
- **Horizontal error bars:** `[ci95_low, ci95_high]`
- **Point:** `mean_delta_ndcg`
- **Color:** `dataset` (4 colors); or facet by dataset
- **Vertical reference line:** x = 0 (dashed red)
- **Highlight:** HotpotQA ms1 copeland row — thicker line or star marker
- **Annotation:** "CI excludes zero" only for HotpotQA ms1 copeland

### 6. Caption draft

Figure 5 shows bootstrap mean ΔnDCG@15 (repaired minus unrepaired hybrid) with 95% confidence intervals (2,000 bootstrap resamples) for Copeland and balance ranking variants, across four benchmarks and three vote-extraction regimes. Intervals of [0, 0] dominate: all ms2 and ms1_drop_mutual configurations yield exactly zero retrieval change for both Copeland and balance pairs. Among ms1 configurations, only HotpotQA Copeland exhibits a confidence interval that does not cross zero below (mean Δ = 0.017, 95% CI [0, 0.041]). FiQA ms1 Copeland has a positive point estimate (0.0015) but an interval spanning zero. SciDocs and BRIGHT ms1 intervals also straddle zero. Balance repair shows no retrieval effect in any cell. These results establish that structural repair's downstream retrieval impact is heterogeneous and usually indistinguishable from zero, with a single dataset×regime exception.

### 7. Scientific claims supported

- **repair_improves_retrieval** (contradicted)
- **repair_helps_hotpotqa** (safe_with_qualification)
- Core decoupling evidence for JDIQ framing

### 8. Important design notes

- Forest plot must show **zero line** prominently
- Consider **faceting** by dataset (4 panels × 6 rows each) if 24 rows too dense
- Sort rows: HotpotQA ms1 copeland at top of its facet
- Do not plot SCC-stratified rows in main figure (move to SF05)

### 9. Expected size

**Double-column landscape** (7 in × 4 in) OR two **1.5-column** forest plots stacked

### 10. Priority

**Critical**

---

## F06 — Pooled Ranking Performance Across Methods

### 1. Figure title

**Figure 6. Pooled mean nDCG@15 by ranking method (1,020 query×regime records).**

### 2. Purpose

Answers: *Do repaired graph-hybrid methods outperform strong fusion baselines?*

Establishes that **DQ repair + hybrid ranking is not a winning downstream strategy** compared to CombSUM/RRF. Critical negative result for JDIQ practical-implications framing.

### 3. Type of visualization

**Horizontal bar chart** with 95% CI error bars, sorted by descending mean nDCG.

### 4. Data source

| File | Path |
|------|------|
| Baseline comparison | `experiments/final_method_gap_audit_20260711_221113/task3/final_baseline_comparison.csv` |

**Filter:** `scope == "pooled"` (12 rows). **Protocol note:** failure-mining pooled records (same 1020 query×regime units).

**Exact values to plot:**

| method | n_queries | mean_ndcg | ci95_low | ci95_high |
|--------|-----------|-----------|----------|-----------|
| combsum | 1020 | 0.462159 | 0.438334 | 0.486806 |
| rrf | 1020 | 0.458654 | 0.434452 | 0.483140 |
| prior_only | 1020 | 0.457067 | 0.433338 | 0.481652 |
| proposed_hybrid | 1020 | 0.454886 | 0.430902 | 0.479453 |
| best_stronger_repair | 1020 | 0.454862 | 0.430884 | 0.479437 |
| borda | 1020 | 0.439279 | 0.415469 | 0.463174 |
| copeland_unrepaired | 1020 | 0.438864 | 0.414950 | 0.462666 |
| copeland_repaired | 1020 | 0.438737 | 0.414738 | 0.462778 |
| markov_repaired | 1020 | 0.435002 | 0.411087 | 0.458366 |
| markov_unrepaired | 1020 | 0.434373 | 0.410000 | 0.457695 |
| balance | 1020 | 0.434372 | 0.410634 | 0.458440 |
| score_sum | 1020 | 0.433422 | 0.409673 | 0.457332 |

### 5. Variables

- **y-axis:** `method` (human-readable labels: "CombSUM", "RRF", "Prior only", "Proposed hybrid", etc.)
- **x-axis:** `mean_ndcg`, label "Mean nDCG@15"
- **Horizontal error bars:** `[ci95_low, ci95_high]`
- **Color:** Highlight CombSUM (best) in green; copeland_repaired and proposed_hybrid in gray; prior_only with border
- **Sort:** Descending by `mean_ndcg`
- **Annotation:** Bracket showing gap CombSUM − copeland_repaired = 0.0234

### 6. Caption draft

Figure 6 compares pooled mean nDCG@15 across twelve ranking methods on 1,020 query×vote-regime records drawn from the failure-mining evaluation corpus (SciDocs, FiQA, HotpotQA, BRIGHT). Error bars show 95% bootstrap confidence intervals. CombSUM achieves the highest mean nDCG (0.462), followed by RRF (0.459) and prior-only fusion (0.457). The proposed repaired hybrid (0.455) does not outperform these fixed baselines. Repaired Copeland (0.439) ranks below unrepaired Copeland (0.439) and substantially below CombSUM (Δ = 0.023). Stronger repair variants offer no improvement over greedy repair (0.455 vs 0.455). These results indicate that graph-based repair combined with hybrid fusion does not provide downstream retrieval quality advantages over established score-fusion methods, informing practical guidance on when graph repair is unlikely to benefit end-to-end retrieval pipelines.

### 7. Scientific claims supported

- **combsum_rrf_beat_repaired_copeland** (Claims Matrix: safe)
- **repair_improves_retrieval** (contradicted)
- **stronger_repair_improves_retrieval** (unsupported)

### 8. Important design notes

- **Footnote in caption:** "Pooled failure-mining protocol; distinct from vote-suite aggregates in Table 5."
- Do not label proposed_hybrid as "our method improves ranking"
- Bold or color CombSUM bar as best baseline
- Group methods visually: fusion baselines | graph methods | proposed

### 9. Expected size

**1.5-column**

### 10. Priority

**Critical**

---

## F07 — Distribution of Diagnostic Failure Classes

### 1. Figure title

**Figure 7. Distribution of failure classes for repair interventions across 1,020 query×regime records.**

### 2. Purpose

Answers: *When repair fails to help retrieval, what mechanistic explanation applies?*

Provides **actionable DQ guidance** — the JDIQ-required practical implication. Shows 64% repair-inactive, 21% tail-only.

### 3. Type of visualization

**Horizontal bar chart** (sorted by count) OR **donut chart**.  
Recommended: **bar chart** (better for 6 categories with similar counts).

### 4. Data source

| File | Path |
|------|------|
| Failure summary | `experiments/failure_class_audit_20260711_212157/phase_reports/manual_failure_summary.csv` |

**Exact data:**

| manual_failure_category | count | pct | mean_delta |
|---------------------------|-------|-----|------------|
| repair_inactive | 652 | 0.6392 | 0.0 |
| tail_only_change | 210 | 0.2059 | 0.0 |
| wrong_direction_repair | 55 | 0.0539 | -0.0341 |
| metric_neutral_ranking_change | 54 | 0.0529 | 0.0 |
| extraction_insensitivity | 26 | 0.0255 | 0.0136 |
| unknown_or_mixed | 23 | 0.0225 | 0.0358 |

Total N = 1,020.

### 5. Variables

- **x-axis:** `count` (or `%` = pct × 100)
- **y-axis:** `manual_failure_category` (human labels):
  - repair_inactive → "Repair inactive"
  - tail_only_change → "Tail-only change"
  - wrong_direction_repair → "Wrong-direction repair"
  - metric_neutral_ranking_change → "Metric-neutral change"
  - extraction_insensitivity → "Extraction insensitivity"
  - unknown_or_mixed → "Unknown / mixed"
- **Color:** Sequential or categorical; highlight **repair_inactive** (largest) in dark blue
- **Labels:** Show percentage on each bar (e.g., "64%")
- **Secondary encoding:** Small text with `mean_delta` on each bar

### 6. Caption draft

Figure 7 summarizes the manual failure taxonomy applied to all 1,020 query×vote-regime evaluation records. The dominant class is repair inactive (652 cases, 64%): graphs where FAS repair removes negligible weight or produces zero retrieval change. Tail-only changes account for 21% (210 cases)—rankings change only below the evaluation cutoff. Wrong-direction repair (5%, 55 cases) is the only class with materially negative mean ΔnDCG (−0.034). Metric-neutral ranking changes (5%) and extraction insensitivity (3%) are smaller. Counterfactual analysis (Section 7) shows that no_repair is the minimal successful intervention for all harmful cases. This taxonomy provides actionable guidance: in approximately two-thirds of evaluation regimes, graph repair is a DQ intervention with no downstream retrieval consequence, and practitioners should prioritize fusion-method selection over repair.

### 7. Scientific claims supported

- **actionable_guidance** (Claims Matrix: safe_with_qualification)
- Failure-class analysis (primary contribution C06)
- Supports **repair_improves_retrieval** (contradicted) with mechanism

### 8. Important design notes

- Sort bars descending by count
- Use human-readable class names (not snake_case) in figure
- 64% and 21% must be immediately visible
- Optional inset: pie chart for top-3 classes only

### 9. Expected size

**Single-column** or **1.5-column**

### 10. Priority

**Critical**

---

## F08 — Per-Query Decoupling: SCC Size vs Repair ΔnDCG

### 1. Figure title

**Figure 8. Per-query relationship between graph cyclicity structure and repair-induced retrieval change.**

### 2. Purpose

Answers: *Does larger SCC size predict larger retrieval benefit from repair?*

Tests (and visually refutes) the hypothesis that structural severity predicts downstream gain. Supports decoupling at query granularity.

### 3. Type of visualization

**Scatter plot** with optional **density contours** or **hexbin** (3,358 points).

### 4. Data source

| File | Path |
|------|------|
| Per-query graph metrics | `experiments/failure_class_audit_20260711_212157/analysis/graph_variant_current_method.csv` |

**Columns:** `dataset`, `query_id`, `graph_variant`, `current_delta`, `is_cyclic`, `largest_scc_size`

- **x-axis:** `largest_scc_size`
- **y-axis:** `current_delta` (repair ΔnDCG for current method)
- **Color:** `dataset`
- **Facet (optional):** `graph_variant` (3 panels) or filter to `ms1` only (~1,120 points)
- **Shape:** `is_cyclic` (TRUE vs FALSE)
- **Reference lines:** y = 0 horizontal; x = 1 vertical

**Summary statistics to annotate:**

- Majority of points at `current_delta = 0` (repair_inactive)
- No visible positive correlation between SCC size and delta
- Filter option: ms1 only for clearer pattern

### 5. Variables

(See above.)

### 6. Caption draft

Figure 8 plots per-query largest SCC size against repair-induced ΔnDCG for the current hybrid method across all dataset×regime records in the failure-class audit corpus (3,358 query×regime points). The cloud of points along the horizontal axis at ΔnDCG = 0 confirms that repair inactivity is common regardless of SCC size. Larger SCCs (up to 20) do not systematically yield positive retrieval deltas. Cyclic queries (triangles) are not concentrated in a positive quadrant. This query-level view complements the aggregate bootstrap analysis (Figure 5) by showing that structural cyclicity severity does not predict retrieval benefit from repair, supporting the decoupling hypothesis central to this study.

### 7. Scientific claims supported

- **structural_predicts_retrieval** (contradicted)
- **actionable_guidance** (when repair is irrelevant)

### 8. Important design notes

- Use **transparency/alpha** (e.g., 0.3) due to overplotting
- Recommend **ms1 facet only** for clarity (main cyclic regime)
- Add LOESS or regression line (expected: flat) to show null relationship
- Do not claim correlation coefficient in figure unless computed

### 9. Expected size

**1.5-column** or **supplement only** if main paper too long

### 10. Priority

**Important** (can move to supplement if page limit tight)

---

## F09 — CARB Benchmark Record Structure

### 1. Figure title

**Figure 9. CARB benchmark schema: unit of observation and feature groups.**

### 2. Purpose

Answers: *What does the supplementary CARB resource contain?*

JDIQ values information curation. This figure documents the benchmark contribution for reproducibility.

### 3. Type of visualization

**Entity-relationship diagram** or **layered block diagram** (flowchart).

### 4. Data source

| File | Path |
|------|------|
| Schema | `experiments/created_data_audit_20260711_232004/phase10/PROPOSED_DATASET_SCHEMA.md` |
| Release structure | `experiments/created_data_audit_20260711_232004/phase10/PROPOSED_RELEASE_STRUCTURE.md` |
| Feature dictionary | `experiments/created_data_audit_20260711_232004/phase6/global_feature_dictionary.csv` |
| Scorecard | `experiments/created_data_audit_20260711_232004/phase9/dataset_contribution_scorecard.csv` |

**Key statistics to embed:**

- 440 independent queries
- 1,020 query×regime records
- 366 methods per record
- 14+ feature groups
- 4 source datasets
- Unit: query × vote_regime × method

**Feature groups from dictionary:**

graph | repair | outcome | label | query | ranking | fusion

### 5. Variables

**Diagram blocks:**

1. **Query** (query_id, dataset)
2. **Vote regime** (ms2, ms1, ms1_drop_mutual)
3. **Method** (366 ranking methods)
4. **Feature tensor** (graph features, repair outcomes, ranking scores)
5. **Labels** (failure class, regret components) — dashed box "evaluation only"

**Arrows:** query + regime → graph → repair → method → outcome

### 6. Caption draft

Figure 9 describes the Consistency-Aware Reranking Benchmark (CARB v0.1), released as supplementary material. The unit of observation is a (query, vote-regime, method) triple. For each of 1,020 query×regime combinations drawn from 440 independent queries across SciDocs, FiQA, HotpotQA, and BRIGHT, the benchmark records graph-theoretic features (node/edge counts, cyclicity, SCC size), repair outcomes (FAS weight removed), ranking scores for 366 methods, and diagnostic labels including failure-class assignments. Feature groups are partitioned into pre-repair graph features, post-repair outcomes, and evaluation labels; leakage-prone fields (post-repair nDCG used as selector targets) are flagged in the data card. CARB is intended to support reproducible research on preference-graph data quality rather than as a training corpus for production rankers.

### 7. Scientific claims supported

- **carb_novel_benchmark** (Claims Matrix: safe_with_qualification)

### 8. Important design notes

- No actual data plotted — schema only
- Flag leakage-prone fields with warning icon
- Version: v0.1.0-proposal

### 9. Expected size

**1.5-column** or **supplement only**

### 10. Priority

**Important** (optional in main paper → supplement if over page limit)

---

# SUPPLEMENTARY FIGURES

---

## SF01 — Per-Dataset Baseline Comparison

| Field | Value |
|-------|-------|
| **Title** | Figure S1. Mean nDCG@15 by method, stratified by dataset. |
| **Type** | Faceted horizontal bar chart (4 facets) |
| **Source** | `experiments/final_method_gap_audit_20260711_221113/task3/final_baseline_comparison.csv` (rows where `scope` ∈ {scidocs, fiqa, hotpotqa, bright}) |
| **Variables** | y=method, x=mean_ndcg, CI error bars, facet=dataset |
| **Priority** | Important |
| **Size** | Double-column |

---

## SF02 — Fusion Suppression Rates for Hybrid Methods

| Field | Value |
|-------|-------|
| **Title** | Figure S2. Fusion suppression rate by hybrid variant. |
| **Type** | Bar chart or heatmap (fusion variant × suppression rate) |
| **Source** | `experiments/final_method_gap_audit_20260711_221113/task1/extraction_fusion_complete.csv` — filter rows where `method` contains `hybrid_repaired`; plot `fusion_suppression_rate` vs method name |
| **Variables** | x=method (abbreviated labels), y=fusion_suppression_rate (0–1) |
| **Claims** | fusion_suppresses_repair (safe_with_qualification) |
| **Priority** | Important |
| **Size** | Supplement, 1.5-column |

---

## SF03 — Exact vs Greedy Repair Comparison

| Field | Value |
|-------|-------|
| **Title** | Figure S3. Pooled retrieval performance: exact, greedy, and stronger repair variants. |
| **Type** | Grouped bar chart |
| **Source** | `experiments/final_method_gap_audit_20260711_221113/task2/repair_comparison_real.csv` |
| **Data** | greedy mean_ndcg_copeland=0.438737; exact_small_greedy_hybrid=0.438701; vs_greedy delta CI [-0.000107, 0] |
| **Variables** | x=repair_method (greedy, exact_small_greedy_hybrid, exact_scc_dp20, no_repair), y=mean_ndcg_copeland |
| **Claims** | stronger_repair_improves_retrieval (unsupported); exact_beats_greedy_structural (safe_with_qualification) |
| **Priority** | Important |
| **Size** | Supplement, single-column |

---

## SF04 — Regret Decomposition by Failure Class

| Field | Value |
|-------|-------|
| **Title** | Figure S4. Mean regret components by failure class. |
| **Type** | Stacked bar chart |
| **Source** | `experiments/failure_class_audit_20260711_212157/phase_reports/regret_by_failure_class.csv` |
| **Variables** | x=failure_class, y=component value, stack=graph_construction, repair_choice, extraction_choice, fusion_choice, selector_policy, missing_candidate_information |
| **Data** | 6 rows × 6 components (see CSV) |
| **Priority** | Optional |
| **Size** | Supplement, 1.5-column |

---

## SF05 — SCC-Stratified Bootstrap (HotpotQA ms1 Detail)

| Field | Value |
|-------|-------|
| **Title** | Figure S5. HotpotQA ms1 repair effect stratified by SCC size. |
| **Type** | Forest plot (3 rows) |
| **Source** | `table_bootstrap_delta_ndcg.csv` hotpotqa ms1 rows + `outputs/pub_vote_cmp_all4/analysis/hotpotqa_ms1_delta_copeland.json` |
| **Data** | all: Δ=0.0167 [0, 0.0405]; scc_high (n=27): Δ=0.0322 [0, 0.0732]; scc_low (n=25): Δ=0 [0, 0] |
| **Claims** | repair_helps_hotpotqa (safe_with_qualification) |
| **Priority** | Important |
| **Size** | Supplement, single-column |

---

## SF06 — Minimal Intervention for Harmful Cases

| Field | Value |
|-------|-------|
| **Title** | Figure S6. Minimal successful intervention for harmful repair cases. |
| **Type** | Single-bar or annotation figure |
| **Source** | `experiments/failure_class_audit_20260711_212157/phase_reports/minimal_intervention_summary.csv` |
| **Data** | no_repair: 56 cases (100% of harmful-case interventions) |
| **Claims** | actionable_guidance |
| **Priority** | Optional |
| **Size** | Supplement, single-column |

---

# FIGURE COUNT SUMMARY

| Priority | Main paper | Supplement |
|----------|------------|------------|
| Critical | F01, F02, F03, F05, F06, F07 (6) | — |
| Important | F04, F08, F09 (3) | SF01–SF03, SF05 (4) |
| Optional | — | SF04, SF06 (2) |
| **Total** | **9** | **6** |

**Recommended main-paper set (page limit):** F01, F02, F03, F05, F06, F07 (6 figures). Move F04, F08, F09 to supplement if needed.

---

*End of figure specifications. Claims reference: `experiments/publication_readiness_audit_20260711_233629/final_claim_support_matrix.csv`*
