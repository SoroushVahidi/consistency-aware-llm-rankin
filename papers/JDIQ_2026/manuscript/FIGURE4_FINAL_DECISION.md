# Figure 4 Final Decision

**Prepared:** 2026-07-12
**Scope:** Re-evaluate Figure 4 now that §1–§4 are complete and `RESULTS_EVIDENCE_MAP.md`/`RESULTS_SECTION_PLAN.md` exist. No image is generated here. This document either reaffirms or revises the earlier decision made in `papers/JDIQ_2026/figure4_evidence/` (a prior, separate task, outside this task's editable scope — read but not modified).

---

## Option comparison

| Criterion | A. Copeland repair-effect forest plot | B. Structural-quality vs.\ retrieval-effect paired figure | C. Baseline comparison figure | D. Failure-taxonomy figure |
|---|---|---|---|---|
| Scientific importance | **Highest** — directly visualizes R3, the paper's central decoupling claim (24 cells, 20 null, 1 reliable) | High — visualizes the same decoupling from a different angle (structural intensity vs. retrieval effect) | High but answers a different question (R4: is the pipeline competitive with simple baselines?) | High but answers a different, later question (R6: why does repair fail when it does?) |
| Clarity | High — forest plots are the standard, expected form for a CI-per-condition claim; a reviewer sees the zero line and the one exception immediately | Medium — requires the reader to hold two different units (structural weight removed; ΔnDCG) in one frame, and only 4 of 12 dataset×regime cells have non-trivial x-values (the rest collapse to x=0), leaving 8 overlapping points at the origin | High — a sorted bar chart with CIs is standard and immediately legible | Medium-high — a sorted bar/donut chart of 6 categories is legible but is inherently a single-figure answer to a narrower question |
| Redundancy with Figures 2–3 | None — Figures 2–3 are purely structural (cyclicity, BEW/PIC); this figure is the first to show a *retrieval* outcome | Partial — reuses the same structural quantity (FAS weight removed) already shown in Figure 2/3's data, now paired with a new retrieval axis; risks feeling like "Figure 3, again, with an extra axis" | None | None |
| Fit with Results flow (per `RESULTS_SECTION_PLAN.md`) | **Exact fit** — §6's first and largest finding (R3) is precisely this forest plot's content | Would need to be inserted *before* Figure 4/R3 as a bridge between §5 and §6, effectively becoming a second "Figure 4-and-a-half" — the section plan does not have a natural second full-page figure slot at that point without displacing Figure 5/6 (R4) | Fits §6's second finding (R4) — but that slot is already filled by the planned baseline-comparison figure (Figure 5/6, extending `fig_mean_ndcg_hybrids.png`); making baseline comparison *the* Figure 4 would leave R3 (the actual central claim) without its own dedicated figure | Fits §7 (R6) — but using it as Figure 4 would place the paper's central claim (R3) without a figure at all, or push R3 to a later, "supporting evidence" figure number, working against the paper's own narrative emphasis |
| Page efficiency | Good — one double-column-landscape or two stacked 1.5-column panels, 24 rows fit comfortably with modest row height | Poor-to-medium — 8 of 12 points overlap exactly at the origin and need jitter/annotation to remain legible, adding visual complexity for the same page budget | Good — 12 sorted bars is a compact, standard form | Good — 6 categories is a compact, standard form |
| Risk of text/overlap or whitespace | Low with the already-designed row ordering (`forest_plot_order.csv`) and Copeland/balance faceting | **High** — the 8 overlapping origin points require jitter, callout boxes, or an inset, all of which risk clutter at 1.5-column or single-column width | Low | Low |
| Grayscale accessibility | Good — point + horizontal whisker + a dashed zero line all read in grayscale; dataset can be encoded by marker shape as a fallback to color | Medium — requires distinguishing dataset (color) *and* regime (shape) *and* reading two axes; grayscale collapse is harder | Good — sorted bars with CI whiskers read fine in grayscale | Good — sorted bars read fine in grayscale |
| Usefulness to reviewers | **Highest** — a reviewer evaluating "is the central claim statistically sound?" gets the complete answer in one figure, including the one dataset where repair helps and by how much | Medium — useful as a *secondary*, exploratory figure (this is exactly what the earlier `FIGURE_SPECIFICATIONS.md` called "F04," explicitly distinct from and complementary to the forest plot) | Medium — useful but answers "is this a good method" rather than "is the central claim true," a question JDIQ reviewers (per `JDIQ_GUIDELINE_SUMMARY.md`'s DQ framing) will weight less heavily than the decoupling evidence | Medium — useful but this is the paper's *explanatory* payoff, better placed after the reader already believes the central claim (R3), not before |

**Option E (another design):** considered and rejected. A combined "all six structural + retrievable metrics in one multi-panel dashboard" figure was considered and rejected as overloaded — it would violate the "not too much inside one image" principle and duplicate content already given its own figure elsewhere (Figures 2, 3, 5/6, 7).

---

## Selected design: **Option A — Copeland/balance repair-effect forest plot**

This reaffirms the decision already made in `papers/JDIQ_2026/figure4_evidence/FIGURE4_COMPARISON_SELECTION.md` and `FIGURE4_SPECIFICATION.md` (a prior task, that directory outside this task's editable scope). Re-evaluated fresh against the now-completed §1–§4 and the Results plan, the same conclusion holds, for a reason that is if anything sharper now than before: `RESULTS_SECTION_PLAN.md`'s §6 explicitly makes R3 (the decoupling claim) the section's first and largest finding, and Table 5 (the bootstrap-delta table) is already slotted as its companion table — a forest plot is the direct, standard visualization of exactly that table, with no redesign needed. Option B (the structural/retrieval paired figure) remains valuable but as a **secondary, optional** figure (already cataloged as "F04" / a §5–§6 "bridge" figure in the earlier planning documents) — not as Figure 4 itself.

---

## Exact specification

**Title:** Figure 4. Retrieval effect of preference-graph repair with bootstrap 95% confidence intervals.

**Panels:** Two, stacked vertically — Panel A: Copeland hybrid (repaired $-$ unrepaired); Panel B: balance hybrid (repaired $-$ unrepaired). (Equivalently, one panel with a categorical facet/color for pair; either layout is acceptable — see "ACM width" below for the tradeoff.)

**Variables:**
- $y$-axis (categorical): row label `{dataset} / {regime}`, ordered per `forest_plot_order.csv` (dataset blocks in descending `ms1` cyclicity order — FiQA, SciDocs, BRIGHT, HotpotQA — matching the ordering convention already used for Figure 2; natural regime order `ms2`→`ms1`→`ms1_drop_mutual` within each dataset block).
- $x$-axis (continuous): $\Delta\mathrm{nDCG@}k$ (repaired $-$ unrepaired), matching the notation of Eq.~(8) [nDCG@$k$, `eq:ndcg` in `main.tex` §3.6] applied to the hybrid ranking of Eq.~(7) [`eq:hybrid`].
- Point: $\bar\delta$, the observed mean delta (Eq.~(9), `eq:bootstrap-ci`'s notation in `main.tex` §4.5).
- Horizontal whisker: $[\mathrm{ci95\_low}, \mathrm{ci95\_high}]$, the same percentile bootstrap interval defined in Eq.~(9).
- Color: dataset (4 levels — reuse the same 4 colors as Figures 2–3 for cross-figure consistency, per `FIGURE_SPECIFICATIONS.md`'s global style guide).
- Highlight: the HotpotQA/`ms1`/Copeland row (the only interval bounded away from negative) — bold row label or a distinct marker (star/filled point vs. hollow points elsewhere).

**Canonical source files (read-only, not modified by this task):**
- `outputs/pub_vote_cmp_all4/paper_package/tables/table_bootstrap_delta_ndcg.csv` (primary; re-verified this session, byte-identical to the earlier extraction)
- `papers/JDIQ_2026/figure4_evidence/figure4_bootstrap_data.csv` (already-audited 24-row extraction with `ci_relation_to_zero` classification, from the prior task)
- `papers/JDIQ_2026/manuscript/figure4_evidence/figure4_ready_to_plot.csv` (this task's copy, identical content, created below so this manuscript workspace is self-contained per this task's directory scope)

**Plotting-ready row structure:** 24 rows = 4 datasets $\times$ 3 regimes $\times$ 2 pairs (Copeland, balance); excludes the `*_scc_high`/`*_scc_low` sub-strata (reserved for Supplementary Figure SF05, per `RESULTS_EVIDENCE_MAP.md` R3's placement note).

**Ordering:** Per `forest_plot_order.csv` (already produced, prior task): FiQA block, SciDocs block, BRIGHT block, HotpotQA block (last, so the one reliable positive effect lands as the closing, most memorable row); within each block, `ms2`→`ms1`→`ms1_drop_mutual`; within each regime, Copeland before balance.

**Axis labels:** $x$: "$\Delta$nDCG@$k$ (repaired $-$ unrepaired)"; $y$: none (categorical row labels serve as the axis).

**Reference line:** Vertical dashed line at $x=0$.

**Annotations:** Highlight the HotpotQA/`ms1`/Copeland row only; optionally annotate "20 of 24 intervals: $[0,0]$" once, near the top of the figure or in the caption, rather than repeating a null-result label on every row.

**Caption draft:** "Bootstrap mean $\Delta$nDCG@$k$ (repaired minus unrepaired hybrid ranking) with 95% confidence intervals (2,000 resamples; Eq.~(9)), for Copeland and balance hybrids, across four benchmarks and three vote-extraction regimes. Twenty of twenty-four intervals are exactly $[0,0]$ (near-acyclic regimes and the balance hybrid throughout). Of the four active `ms1`/Copeland cells, three intervals straddle zero; HotpotQA's interval is the only one bounded away from negative (mean $+0.017$, CI $[0, 0.041]$) — notably not the dataset with the most severe structural inconsistency (Table 4)."

**ACM width recommendation:** 1.5-column (two stacked panels) if the two-panel layout is used; double-column landscape if a single 24-row panel with a `pair` facet color is preferred instead. Recommend the **two-panel stacked** layout, since it avoids needing a third visual encoding (shape or facet) beyond color (dataset) and position (regime block), keeping the figure legible at single-column width if page budget later requires shrinking it.

**What must not appear inside the image:** any $p$-value or significance-star notation not already implied by the CI (per `main.tex` §4.5's stated preference for percentile CIs over significance stars); the word "significant" without the CI shown alongside it; any reference to the four now-removed external-solver repair variants (irrelevant to this figure in any case, since Figure 4 concerns the canonical hybrid comparison, not the repair-variant comparison of Table 4).

**Is a new query needed to extract additional plotting data?** No. All 24 rows and every field required by the ready-to-plot schema are already present in the canonical source and the already-audited extraction; no new computation, join, or statistic is required.

---

## New file created (per this task's directory scope)

`papers/JDIQ_2026/manuscript/figure4_evidence/figure4_ready_to_plot.csv` — a verbatim, freshly-verified copy of the same 24-row, already-audited data (re-checked against the canonical source this session, not recomputed), placed under this task's editable directory so the manuscript workspace does not depend on reading outside `papers/JDIQ_2026/manuscript/`. The original at `papers/JDIQ_2026/figure4_evidence/` (a sibling directory, out of this task's scope) is unmodified and remains the historical record of the earlier evidence-collection task.
