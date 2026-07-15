# Visual Polish Pass — Figure Redesign, Typography, Layout, and Flow

**Scope of this pass:** presentation only. No numerical result, table value, or
scientific claim was changed. All redesigned figures were regenerated directly
from the same canonical CSVs already verified in the prior scientific-accuracy
pass (`reports/full_calibrated_core/tables/*.csv`); no new experiment was run.

**New artifacts:**
- `figures_v2/style.py` — shared design system (validated palette, typography, spacing)
- `figures_v2/generate_figures.py` — regenerates Figures 2–11 from canonical CSVs
- `figures_v2/generate_figure1.py` — regenerates Figure 1 (vector pipeline diagram)
- `figures_v2/*.pdf` / `*.png` — the 11 regenerated figures (vector PDF used in the manuscript; PNG kept as a preview)

**Design system:** a 4-color categorical palette (one fixed color per dataset:
SciDocs blue `#0072B2`, FiQA orange `#E69F00`, HotpotQA green `#009E73`, BRIGHT
purple `#CC79A7`) plus a 2-color diverging pair for signed deltas (orange
`#E66101` negative, purple `#5E3C99` positive). Both were run through the
dataviz skill's `validate_palette.js` — lightness band, chroma floor, CVD
(colorblind) separation, and contrast all pass. One consistent sans-serif
typographic scale (8.5pt body / 9.5pt titles / 7.5pt ticks) is applied via
shared `matplotlib` rcParams across every figure, so all 11 look like one
family rather than 11 independently-styled plots.

---

## 1. Figure-by-figure redesign report

| # | Old design | Problem(s) found | New design | Why it's better |
|---|---|---|---|---|
| 1 (pipeline) | Bordered text box (`\fbox{\parbox}`), plain arrows, no color | No visual hierarchy; looked like a wireframe, not a journal figure | 8-stage color-coded vector diagram (blue=data, green=process, amber=diagnostic/eval), rounded boxes, dashed ablation branch | Role of each stage is legible at a glance; matches ACM figure conventions |
| 2 (BM25 share) | 4 tiny multi-panel line/dot mini-charts, illegible at print size | Failed the 5-second and readable-without-zooming tests | 4-panel grouped bar chart, raw (gray) vs. calibrated (blue) | Answers "how much did BM25 dominance drop" in one glance |
| 3 (cyclicity by regime) | Categorical regimes (ms2/ms1/ms1_drop_mutual) connected by lines — implies a false continuum | Anti-pattern named explicitly in the brief | Grouped bars, one bar per dataset per regime | No implied trend between unrelated categories |
| 4 (raw vs. calibrated structure) | 4 tiny inset line-mini-charts | Same anti-pattern, smaller and more illegible | 4-panel grouped bars, raw vs. calibrated | Consistent with Fig. 3's new visual language |
| 5 (cyclicity before/after) | Tiny 4-panel 2-point line "before/after" charts | Wrong chart type for a paired before/after comparison | Dumbbell plot, one row per dataset | This is the textbook dumbbell use case; now a 5-second read |
| 6 (FAS weight removed) | Same line-over-categorical-regime anti-pattern as Fig. 3 | Same as Fig. 3 | Grouped bars | Same fix, same family |
| 7 (bootstrap forest) | 4 tiny panels, invisible CI whiskers, no zero-line emphasis, x-range too wide (±0.25) so all real effects (≤0.045) collapsed to invisible dots | Failed "is the CI obvious," "is the zero line prominent" | Same forest-plot idea but x-range tightened to ±0.065, zero line in a bold accent color, larger panels | CI widths and the zero-vs-nonzero pattern are now immediately visible |
| 8 (influence removal) | Two full-width stacked bar-histograms of every individual query's delta — large footprint, weak signal | "Occupies too much space relative to information," per the brief | Compact side-by-side step/lollipop plot of remaining mean vs. top-*k*-removed, annotated values | Same finding, roughly 1/3 the vertical space, clearer trend line |
| 9 (raw vs. calibrated sign changes) | 10-panel scatterplot grid, axes/titles illegible | Explicitly called out as "not publication quality" | Dataset×method heatmap, raw/calibrated columns, numeric values overlaid, the 5 text-discussed sign flips outlined | Answers "which conclusions changed?" directly; matches Table 8 exactly (see accuracy note below) |
| 10 (baseline comparison) | Dot+errorbar across 3 regimes, method labels combining `\n` + 90° rotation — this **rendered as overlapping garbled text**, a real bug | Broken tick labels, illegible at any size | Bars sorted by value, single-line rotated labels, solid = graph-independent baseline | Fixes the rendering bug and gives a clean, sorted ranking per dataset |
| 11 (alpha sensitivity) | 4-panel overlapping multi-line "spaghetti" plot, indistinguishable colors | "Avoid many overlapping curves... consider a heatmap," per the brief | Dataset×α heatmap with annotated values | Sign and magnitude pattern across the sweep is now immediate |

### Accuracy correction made during redesign (not a numeric change, a labeling correction)

While redesigning Figure 9, an initial version flagged **every** technical
sign flip (14 of 20 rows), including several where both raw and calibrated
deltas were noise-level (e.g., ±0.000–0.002). That diluted the figure's one
job. It was corrected to outline exactly the 5 rows the manuscript's own
Table 8 ("five most consequential sign flips") already discusses in prose —
so the figure and the text now point at the same cells. No underlying value
changed; only which cells get the outline annotation.

While redesigning Figure 10's caption, an initial draft claimed "no repaired
graph-dependent method leads its panel," which was factually wrong for
SciDocs (a repaired Copeland-hybrid narrowly leads that panel). Caught on
visual re-inspection of the rendered chart and corrected before finalizing.

---

## 2. Typography improvements

- Fixed one broken hyphenation ("ver-sion" in Table 4's header) caused by an
  unnecessarily narrow `p{2.9cm}` column; widened both columns to use the
  available page width and shortened the header text.
- Established one consistent figure typeface (`DejaVu Sans`) and a fixed size
  scale (8.5/9.5/7.5pt) across all 11 regenerated figures, replacing 11
  independently-styled plots with inconsistent fonts and sizes.
- Standardized numeric precision and alignment inside figures (e.g., all
  delta annotations to 4 decimal places, all percentages to whole numbers)
  so figures read consistently with the tables reporting the same numbers.
- No other widow/orphan defects were found in a full page-by-page pass (see
  §4, Reviewer read-through) — acmart's own paragraph and page-breaking
  already avoids them; the one remaining minor overfull `\hbox` (9.7pt, in a
  paragraph unrelated to this pass) does not materially affect readability
  and was left as documented in the prior audit.

## 3. Layout improvements

- Every regenerated figure is sized to the actual manuscript column width
  (`\linewidth`) rather than the previous `0.95\linewidth` applied uniformly
  regardless of the figure's native aspect ratio, which had left some
  figures needlessly small and others (the old Fig. 9) so wide-and-short
  that 10 panels were each under an inch across.
- Figure 8 (influence) and Figure 11 (alpha heatmap) now take roughly a
  third to a half of the vertical space their predecessors did, which
  eliminated a large block of dead white space at the bottom of what was the
  last content page (previously ~40% of that page was empty below Figure
  11; now the page runs to a normal margin).
- Figure 9's aspect ratio (tall heatmap) is now explicitly sized
  (`0.6\linewidth`) rather than inheriting a default width meant for wide
  landscape figures, which had made it either illegibly small or
  absurdly tall depending on the naive width choice.
- Table column specifications were widened/renormalized in three tables
  (Table 2, Table 4, and implicitly Tables 6/8/9/10 via alignment changes
  below) to remove unnecessary line wraps.
- No isolated floats, split captions across pages, or oversized figures were
  found in the full page-by-page pass; all 11 figures now sit on the same
  page as (or the page immediately following) their first textual reference.

## 4. Caption improvements

Every one of the 11 figure captions was rewritten to follow "what is shown /
how it was computed / what to notice" instead of restating axis labels:

- Each caption now states the exact quantity plotted (e.g., "conditional
  BM25 edge-weight share," "cyclic-query percentage under `ms1`") rather
  than a generic description.
- Each caption states the concrete pattern a reader should take away (e.g.,
  "BM25 share is near 1.0 under raw and drops to 0.4–0.7 after calibration,"
  "the drop is largest for HotpotQA (63%→2%) and smallest for FiQA
  (98%→31%)") rather than leaving the reader to infer it from the plot alone.
- Where a figure's story could be misread in isolation (Figure 4's raw vs.
  calibrated cyclicity looking similar, unlike Figure 2's dramatic BM25
  shift), the caption explicitly flags the correct interpretation and
  cross-references the removed-edge-overlap numbers that explain it, rather
  than leaving an apparent inconsistency unaddressed.
- All 11 `\Description{}` (alt-text) blocks were rewritten in parallel to
  describe the same content for accessibility/screen-reader users, not left
  as stale descriptions of the old chart types (several previously described
  "multi-line plots" that no longer exist).

## 5. Reading-flow / structural review

A full page-by-page pass (all 27 pages, rendered and visually inspected) was
performed as a JDIQ reviewer would read the PDF, checking specifically for
"I don't immediately understand this" moments. Findings:

- No section transition was found where the reader would be confused about
  why a section exists — each section opens by stating the question it
  answers (this was already true of the manuscript entering this pass; no
  rewrite was needed here, per the instruction not to make conceptual
  changes).
- Limitations are stated once each in their dedicated bolded paragraph in
  §9 (Limitations), with brief one-line cross-references elsewhere (e.g., in
  §8 Discussion) rather than repeated at length — this was already the
  pattern in the manuscript and was left as is, since re-litigating it risked
  exactly the "large conceptual change" the instructions asked to avoid.
- No table mixes incompatible historical/canonical packages, no figure is
  purely decorative, and every figure and table is referenced in the text
  (verified programmatically: zero unreferenced figure/table labels).

---

## 6. Final assessments

**Visual-quality assessment: 8.5 / 10.**
Rationale: all 11 figures now share one coherent, validated, colorblind-safe
design system; every figure passes the 5-second/no-zoom test that the
originals mostly failed (three were genuinely below publication quality: the
old Figs. 9 and 10 had real legibility failures, and Fig. 10 had an actual
tick-label rendering bug). Docked from a 9–10 because: (a) Figure 1 is a
matplotlib-patches diagram rather than a hand-tuned vector illustration, so
its polish is good but not at the level of a professional graphic designer's
TikZ/Illustrator work; (b) a handful of underfull/overfull LaTeX boxes remain
(cosmetic, pre-existing, not addressed per their own low materiality); (c)
true decimal-point column alignment (e.g., `siunitx` `S` columns) was not
adopted for tables, only right-alignment, which is a smaller version of the
same improvement.

**Reviewer-first-impression assessment: 8 / 10.**
Rationale: flipping through the PDF now immediately telegraphs the paper's
structure — a clean pipeline diagram, a clear BM25-dominance bar chart, a
grouped-bar structural story, a forest plot whose zero-line pattern is
legible at a glance, and a heatmap that answers "what changed" without
reading a word of text. This is a large improvement over the prior state,
where several figures required zooming to 200%+ to read at all and one
(Fig. 10) had genuinely garbled tick labels. It is not a 9–10 because the
paper is still text-dense in its middle sections (§3–§4, Methodology and
Experimental Setup) with few visual anchors beyond Figure 1 and Table 1–4,
which is inherent to a methods-heavy data-quality paper and was out of scope
for a "no conceptual changes" pass to restructure.

## 7. Compilation

```bash
cd papers/JDIQ_2026/manuscript
tectonic -X compile main.tex --keep-logs
```

Result: 27 pages, compiles cleanly, zero undefined references/citations, zero
literal `??` in the extracted text, 3 pre-existing/unavoidable BibTeX
metadata warnings (arXiv/NeurIPS-track page-number fields), 2 minor overfull
`\hbox` warnings (9.7pt and 1.4pt — both below any materiality threshold).
