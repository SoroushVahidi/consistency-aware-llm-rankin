# Figure-generation prompt: F5 (appendix), exact-vs-greedy structural gap

**Status:** not generated -- no prior figure exists for this comparison in
any prior manuscript (`FIGURE_TABLE_AUDIT.md` confirmed this by searching
`reports/exact_open_source_ilp_repair_investigation/` for any image
output and finding only CSV tables). This is a genuinely new figure, not
a resize/relabel of an existing one.

## Context for whoever runs this prompt

This figure directly supports the manuscript's elevated exact-repair
contribution (`MANUSCRIPT_PLAN.md` Contribution 1; `main.tex`
Section~\ref{sec:repair-protocol}): exact SCIP repair reaches proven
optimality and removes systematically **less** total edge weight than
greedy repair, on the same graphs, even though the retrieval-level
conclusion does not change. The figure's job is to make the structural
gap visible at a glance, per-dataset, so Results prose can point to it
instead of only citing numbers. Source data:
`reports/exact_open_source_ilp_repair_investigation/tables/structural_summary_by_dataset_regime.csv`
(per-dataset breakdown) and
`reports/exact_open_source_ilp_repair_investigation/tables/structural_summary_greedy_vs_ilp.csv`
(pooled summary, columns include `mean_fas_weight_removed` and
`mean_normalized_fas_weight_removed` for `repair_method` in
`{greedy, ilp_scip}`). Do not invent numbers -- read the actual CSVs
before generating; do not use the numbers quoted in this prompt's
background paragraph below for anything other than sanity-checking that
the regenerated figure's shape looks right (they are from the report at
the time this prompt was written and may not be the exact values used at
generation time if the underlying report is regenerated).

Background (for context only, not necessarily current): the investigation
report found the exact solver removes about 22-29% less mean weight than
greedy on the cyclic subset of SciDocs, FiQA, and BRIGHT, and about 13%
less on HotpotQA (the smallest graphs), with the exact solver finding a
different removed-edge set than greedy in 53-94% of cyclic queries
depending on dataset.

## Prompt

```
Create a new figure for papers/SNCS_2026/ showing the structural gap
between greedy and exact (SCIP) minimum-weight feedback-arc-set repair,
per dataset, using only the cyclic-query subset (repair is a no-op on
already-acyclic graphs, so including acyclic queries would dilute and
mislead the comparison).

Data source: read
reports/exact_open_source_ilp_repair_investigation/tables/structural_summary_by_dataset_regime.csv
directly (do not hand-copy numbers from any manuscript or report text).
Filter to the primary ms1 regime and to cyclic queries only, matching how
the source investigation report itself scoped its "per-dataset structural
gap" table. Confirm which exact columns the CSV provides before choosing
what to plot -- do not assume a column exists without checking the
header row first.

Figure design:
- A grouped bar chart, one panel or one group per dataset (SciDocs, FiQA,
  HotpotQA, BRIGHT, in that fixed order), following the same per-dataset
  ordering and color assignment as
  papers/JDIQ_2026/manuscript/figures_v2/style.py's DATASET_COLORS (reuse
  that module directly, do not redefine a new palette).
- Within each dataset's group, two bars: mean feedback-arc weight removed
  by greedy repair, and mean feedback-arc weight removed by exact repair
  -- on the cyclic-query subset only.
- Y-axis: mean removed edge weight (state the units/normalization used --
  check whether the CSV's raw or normalized removed-weight column is more
  interpretable for this comparison, and label the axis accordingly; do
  not silently pick one without checking both).
- Distinguish the two bars (greedy vs. exact) by a fill-pattern or
  saturation difference in addition to any color/legend text, so the
  figure remains interpretable in grayscale printing -- do not rely on
  color alone to distinguish greedy from exact, since both bars in a pair
  may otherwise use the same per-dataset hue.
- Legible font size matching the other figures_v2 outputs (do not go
  below what fig2_bm25_share.pdf currently uses).
- One-line caption-adjacent note (small italic, consistent with the style
  already used in fig1_pipeline.pdf's "Raw-margin ablation" note):
  "Exact repair consistently removes less total weight than greedy on
  the same graphs; both reach the same retrieval-level conclusion
  (Table T3)." -- adjust the table cross-reference to whatever table
  number Results drafting assigns; do not leave a broken forward
  reference.

Output requirements:
- Vector PDF (primary) plus PNG preview, saved into
  papers/JDIQ_2026/manuscript/figures_v2/ alongside the other regenerated
  figures for this manuscript family (or into a new
  papers/SNCS_2026/figures/ location if the manuscript's figure-asset
  convention has moved by the time this is run -- check
  papers/SNCS_2026/figures/README.md first).
- Single-column width appropriate for sn-jnl.cls
  (papers/SNCS_2026/template/sn-jnl.cls); this is an appendix figure, so
  it does not need double-column width.
- No decorative elements; no 3D bar effects; no drop shadows.
- Save the generation script (add a new function to
  papers/JDIQ_2026/manuscript/figures_v2/generate_figures.py rather than
  a one-off throwaway script) so the figure can be regenerated if the
  underlying report is rerun.

Before finalizing, cross-check the figure's qualitative shape (exact
removes less weight than greedy in every dataset panel) against the
investigation report's own FINDINGS.md prose -- if the regenerated numbers
disagree qualitatively with that prior report, stop and flag the
discrepancy rather than silently plotting numbers that contradict the
report the figure is supposed to illustrate.
```
