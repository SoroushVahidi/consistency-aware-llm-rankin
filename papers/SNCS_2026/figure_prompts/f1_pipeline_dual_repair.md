# Figure-generation prompt: F1, updated pipeline schematic with dual repair branch

**Status:** not generated. Write this prompt now (Stage 3); generate the
actual figure in a later stage once Results are being assembled, so the
figure can be checked against final terminology and section numbers.

## Context for whoever runs this prompt

This is a Cursor-ready prompt for regenerating `papers/JDIQ_2026/manuscript/figures_v2/fig1_pipeline.pdf`
for the SN Computer Science manuscript (`papers/SNCS_2026/`). The existing
figure shows a single linear pipeline with one box labeled "Optional
greedy repair." This manuscript's headline contribution treats **exact
SCIP repair as a co-equal diagnostic-control branch alongside greedy
repair**, not a footnote (`MANUSCRIPT_PLAN.md` Section 3, Contribution 1;
`papers/SNCS_2026/manuscript/main.tex` Section~\ref{sec:repair-protocol}).
Reusing the existing single-repair-box figure as-is would visually
contradict the paper's own framing, so it needs a new box/branch, not a
relabel.

## Prompt

```
Regenerate the pipeline schematic in
papers/JDIQ_2026/manuscript/figures_v2/generate_figures.py (the function
that produces fig1_pipeline.pdf/.png), reusing
papers/JDIQ_2026/manuscript/figures_v2/style.py for palette and font
choices so the new figure stays visually consistent with the other
figures in that directory.

Changes needed from the current figure:

1. Keep the existing linear stages up to and including "Preference graph
   G_q (regime r)" and the "Mutual-pair, SCC & FAS diagnostics" box
   unchanged in position and wording.

2. Replace the single "Optional greedy repair" box with two parallel
   boxes at the same pipeline position, both fed from the diagnostics
   box, both feeding into the same downstream "Ranking extraction &
   hybrid fusion" box:
   - "Greedy repair (cycle-peeling)"
   - "Exact repair (SCIP MWFAS)"
   Connect both with arrows into and out of these two boxes so the figure
   reads as two alternative branches through the same pipeline, not two
   separate pipelines. Use the same "Processing step" color (teal, per
   style.py) for both boxes so they read as the same category of step,
   not as a diagnostic vs. a processing step.

3. Add a small caption note near the two repair boxes (small italic text,
   consistent with the existing "Raw-margin ablation" note style already
   in the figure) reading: "Exact repair is a diagnostic control on
   greedy repair, not a proposed replacement." This is essential --
   without it, a reader skimming only the figure could misread exact
   repair as this paper's proposed method, which the manuscript
   explicitly disclaims (Introduction, Section~\ref{sec:repair-protocol}).

4. Keep the final "nDCG evaluation & paired tests" box unchanged in
   wording, since both repair branches feed into the identical evaluation
   protocol -- that symmetry is the point of the figure.

5. Keep the existing three-category legend (Data/artifact, Processing
   step, Diagnostic/evaluation) unchanged; do not add a fourth legend
   category for the split -- the two repair boxes are still "Processing
   step" category.

Output requirements:
- Vector PDF (primary, for \includegraphics in the LaTeX manuscript) and
  a PNG at matching aspect ratio (preview convenience only, not for
  inclusion).
- Single-column width appropriate for the sn-jnl.cls Springer Nature
  template (papers/SNCS_2026/template/sn-jnl.cls) -- match the current
  fig1_pipeline.pdf's aspect ratio and font sizes; do not shrink text
  below the current figure's font size to fit the extra branch box --
  widen the figure instead if needed.
- No decorative elements (no icons, no gradients, no drop shadows) beyond
  what the current figure already uses.
- Must remain legible if printed in grayscale: verify the two repair
  boxes (same teal fill) are still distinguishable from each other by
  their text label alone, since color will not distinguish them from one
  another (only from the blue "Data" and orange "Diagnostic" categories).
- Save both the editable generation script change (in
  generate_figures.py) and the output PDF/PNG; do not hand-edit a
  rasterized image directly.

Do not change any other figure in figures_v2/ as part of this task.
```
