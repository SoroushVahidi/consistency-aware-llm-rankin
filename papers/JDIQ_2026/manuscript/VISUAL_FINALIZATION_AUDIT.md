# Visual Finalization Audit — Pass 4 of 5

Baseline commit: `97d34ed` ("Compress manuscript by ~2 pages via evidence-preserving trims").
Baseline compile: `tectonic -X compile main.tex` → **31 pages**, 0 unresolved `??`, 0 undefined
references/citations in the final resolved PDF (natbib/LaTeX "undefined" warnings appear only on
tectonic's internal first pass and are resolved by its automatic second pass).

Figure numbering below is derived from document order of `\label{fig:...}` (confirmed against
`main.aux`-equivalent `\newlabel` ordering: labels appear in the same order as their final printed
numbers, 1–11). Table numbering likewise follows `\label{tab:...}` document order, 1–10.

## Figure/Table inventory

| Figure/Table | Current issue | Scientific role | Keep/redesign/remove | Source data/script | Final action |
|---|---|---|---|---|---|
| Fig. 1 (pipeline) | Raster PNG (`74556F5F-...png`, iOS-style filename, not a screenshot but a non-vector, hand-assembled diagram) with an embedded "Notation highlight" block duplicating Table 1; figure is tall and text-heavy | Orients reader to the 8-stage pipeline and raw-margin ablation before Methodology detail | Redesign | No data (schematic only); vector script already exists: `figures_v2/generate_figure1.py` → `fig1_pipeline.pdf` | Switch to existing vector `fig1_pipeline.pdf` (already has 8 stages, non-intersecting dashed bypass, 3-color legend, **no** notation block); shorten caption |
| Fig. 2 (BM25 share) | Vector, correct; uses raw regime codes `ms2`/`ms1`/`ms1_drop_mutual` as rotated x-tick labels (underscore visible) | Shows raw-vs-normalized BM25 dominance per dataset | Keep design, fix labels | `full_bm25_weight_share.csv` via `generate_figures.py:fig2_bm25_share` | Replace regime codes with reader labels (Two-vote / One-vote / One-vote, mutual pairs removed); keep 4-panel full-width layout (needed for readability with 4 datasets) |
| Fig. 3 (cyclicity by regime) | Y-axis 0–120% though values cannot exceed 100%; raw regime codes on x-axis | Headline structural result: cyclicity is regime-driven | Keep design, fix axis + labels | `full_structural_results.csv` via `fig3_cyclicity_primary` | Y-axis → 0–105%; reader-facing regime labels |
| Fig. 4 (raw vs normalized cyclicity) | Vector, correct in content, but crowded rotated regime labels per panel; duplicative visual weight vs Fig. 3 | Shows headline cyclicity is normalization-insensitive even though edge identity is not | Keep grouped-bar design (already 4-panel raw-vs-normalized, matches task goal), fix labels | `full_structural_results.csv` via `fig4_raw_vs_calibrated_structure` | Reader-facing regime labels, no rotation change needed (labels short once relabeled) |
| Fig. 5 (cyclicity before/after mutual-pair deletion) | Raster PNG (`IMG_5312.png`); embedded chart title duplicates caption; x-axis label uses raw code "ms1" | One of the 3 newly-integrated figures; isolates mutual-pair contribution to cyclicity | Keep (already clean dumbbell plot, no phone UI, no absolute paths) | `full_cycle_decomposition.csv` via existing `generate_figures.py:fig5_cycle_decomposition` (vector `fig5_cycle_decomposition.pdf` already exists, unused) | Switch to existing vector `fig5_cycle_decomposition.pdf` (equivalent content, no embedded title duplication, reader-facing axis label) |
| Fig. 6 (normalized FAS weight removed) | Vector, correct; raw regime codes on x-axis | Repair activity tracks cyclicity | Keep design, fix labels | `full_structural_results.csv` via `fig6_normalized_fas_removed` | Reader-facing regime labels |
| Fig. 7 (forest plot, ΔnDCG) | 15 rows/panel (3 regimes × 5 pairs); all `ms2` rows and nearly all `ms1_drop_mutual` rows collapse to an exact-zero point, only `ms1` rows are active; tiny y-tick text (5.6pt) with raw codes | Shows repaired-minus-unrepaired effect is concentrated in `ms1` | Redesign: main figure shows only active one-vote rows (5 pairs × 4 datasets) | `full_statistical_tests.csv` via `fig7_bootstrap_forest` | New reduced-row function; zero-effect regimes summarized in prose (already stated in text) instead of dropped silently |
| Fig. 8 (influence sensitivity) | Current raster `IMG_5313.png` shows **only HotpotQA**, though text also reports SciDocs numerically; existing unused vector `fig8_influence.pdf` already has both panels but its on-plot value annotations overlap each other/the line when points are close | Shows the HotpotQA positive effect is influence-concentrated; SciDocs is less concentrated | Redesign: use the two-panel vector version | `full_influence_removal_summary.csv` + hardcoded k=0 means via `fig8_influence` | Switch to `fig8_influence.pdf`; move per-point value annotations to a value line below each panel (as `IMG_5313.png` already did for HotpotQA); pull `row0_mean` from source CSV instead of hardcoding |
| Fig. 9 (raw-vs-normalized sign heatmap) | 20-row (4 datasets × 5 pairs) × 2-column heatmap with a color bar; duplicates Table 8 in different form; small text | Shows normalization flips sign in a handful of named cells | Redesign: 4-panel raw-vs-normalized dot+line plot | `full_paired_deltas.csv` (raw) + `full_statistical_tests.csv` (normalized) | New function: one panel per dataset, y = 5 method pairs, x = Δ nDCG, raw/normalized markers joined by a line, zero line, named flips emphasized |
| Fig. 10 (per-dataset baseline comparison) | 4 panels × up to 10 methods, 60°-rotated abbreviated labels, independent y-ranges per panel, subtle alpha-only encoding for graph-independent vs graph-dependent | Shows simple fusion baselines are competitive with graph methods | Redesign: horizontal dot/bar plot | `full_retrieval_results.csv` via `fig10_baseline_comparison` | New function: method names on y-axis, mean nDCG on x-axis, sorted per panel, marker/fill distinguishes graph-independent baselines, no rotated labels |
| Fig. 11 (alpha sensitivity heatmap) | Duplicates Table 10 exactly (same 4×4 values) | Shows sign instability across the small α sweep | Remove from main paper | `full_alpha_sensitivity.csv` via `fig11_alpha_heatmap` | Remove figure + its `\includegraphics`/caption/label; retain Table 10 as the exact-value source; update cross-references in prose |
| Table 1 (notation) | None found | Reference table for symbols | Keep | N/A | No change |
| Table 5 (structural-results) | "Norm. FAS" column not explicitly tied to greedy repair (vs. the exact-ILP robustness check discussed later) | Headline structural diagnostics | Keep, clarify caption | N/A | Add one clause noting FAS-weight-removed values are from the primary greedy repair, not the exact solver |
| Table 7 (bootstrap-delta-ndcg) | Minor: mixed sign/decimal widths in `Mean $\Delta$`, `95% CI` columns | Active-cell effect sizes | Keep | N/A | No structural change; already `scriptsize` with right/center alignment |
| Table 8 (raw-calibrated-ablation) | None | Exact-value companion to Fig. 9 | Keep | N/A | No change (now explicitly the retained exact-value source per Fig. 9 redesign) |
| Table 9 (pooled-baseline) | None; prose interpretation already appropriately cautious | Macro comparison vs. fusion baselines | Keep | N/A | No change |
| Table 10 (alpha-sensitivity) | Duplicated by Fig. 11 | Exact α-sweep values | Keep (sole surviving representation once Fig. 11 removed) | N/A | No change |

## Section 7 (Secondary Analyses and Scope Checks) audit

| Subsection | Assessment | Action |
|---|---|---|
| 7.1 Rule-Based Outcome Taxonomy | Explains why an old raw-margin taxonomy is excluded from the main narrative; internal project history, not evidence | Remove subsection; retain one limitation sentence |
| 7.2 Protocol Audit of Stored LLM Judgments | Strengthens the paper (parser defaults, position bias, agreement, cyclicity reduction after artifact removal); currently long with provider-specific detail | Compress; keep the four load-bearing quantitative facts; consider a compact table |
| 7.3 Implementation Cost Note | Single unbenchmarked-machine observation, not a substantive evidence-backed conclusion | Remove from main paper |
| 7.4 Planned CARB Resource | Discusses an unreleased future resource | Remove entirely; also remove the related CARB sentences in Limitations, Data Availability |

## Other findings

- Source CSVs consumed by `figures_v2/generate_figures.py` and `generate_figure1.py`
  (`reports/full_calibrated_core/tables/*.csv`) are **not currently tracked in git** even though the
  figure scripts depend on them — this pass copies them into the repository so figures are
  regenerable from committed data (see REVISION_SUMMARY.md).
- No screenshots with browser/phone UI chrome were found in any of the three newly-integrated
  figures; the two raster ones (`IMG_5312.png`, `IMG_5313.png`) are clean matplotlib exports, but
  both have already-generated, unused vector equivalents (`fig5_cycle_decomposition.pdf`,
  `fig8_influence.pdf`) that are strictly better (vector, no embedded title duplication, no
  annotation overlap) — this pass switches to those.
- No absolute local paths or identifying metadata found in the inspected image files' visible content.

## Checkpoint page counts

| Checkpoint | Page count |
|---|---:|
| Baseline | 31 |
| Figures 1–11 redesigned/replaced (incl. Fig. 11 removal) | 31 |
| Secondary-section cleanup (Section 7) | 30 |
| Final (practical-implications table added) | 30 |

## Numerical validation result

50 machine-checked comparisons between plotted figure values and the authoritative
source CSVs / manuscript tables and prose, covering Figures 3, 7, 8, 9, and the
retained Table 10 (ex-Figure 11): **0 failures**. See `FIGURE_VALUE_AUDIT.json`
for the full machine-readable record.

## Final visual/compile assessment

- `tectonic -X compile main.tex`: succeeds, 30 pages, 0 `??` markers in the resolved PDF.
- All 10 remaining figures are vector PDFs (`figures_v2/fig*.pdf`); 0 raster figures
  remain in the main paper (previously 3: the pipeline and two newly-integrated
  figures were raster PNGs).
- Every `\includegraphics` path resolves to an existing file; no duplicate labels;
  no dangling references to the removed Figure 11 or Section 7.1/7.3/7.4 labels.
- Full-PDF page-by-page visual inspection (pages 1, 5, 14–30) confirms: no legends
  inside data regions, no numbers overlapping axes/curves, no clipped labels, no
  embedded captions, no stale references, no raw implementation identifiers
  (`ms1`/`ms2`/`ms1_drop_mutual`) on any figure axis or tick label.
