# Figure-Data Verification Report

13/13 checks passed.

Every check below independently re-derives (not re-imports) the data
generate_figures.py plots, straight from the canonical CSVs under
reports/full_calibrated_core/tables/, and confirms it is well-formed
and internally consistent with the manuscript's own stated claims
(e.g. the five named sign-flip cells in Table `tab:raw-calibrated-ablation`
actually flip sign in the source data).

| Figure | Check | Result | Detail |
|---|---|---|---|
| fig2/fig4 | all 12 dataset x regime cells present and in-range for both source columns | PASS |  |
| fig6 | ms2 cells are exactly zero; all cells within plotted axis range | PASS |  |
| fig7 | ms1 primary-protocol rows = 4 datasets x 5 pairs | PASS | found 20 rows |
| fig8 | hotpotqa remove_top_k is a contiguous 1..N sequence | PASS |  |
| fig8 | scidocs remove_top_k is a contiguous 1..N sequence | PASS |  |
| fig9 | all 20 dataset x pair cells present in both raw and calibrated sources | PASS |  |
| fig9 | highlighted sign-flip cell scidocs/copeland_hybrid actually flips sign (raw=-0.0018, cal=+0.0085) | PASS |  |
| fig9 | highlighted sign-flip cell fiqa/copeland_graph actually flips sign (raw=-0.0029, cal=+0.0036) | PASS |  |
| fig9 | highlighted sign-flip cell bright/copeland_hybrid actually flips sign (raw=-0.0045, cal=+0.0006) | PASS |  |
| fig9 | highlighted sign-flip cell scidocs/copeland_graph actually flips sign (raw=-0.0079, cal=+0.0110) | PASS |  |
| fig9 | highlighted sign-flip cell hotpotqa/markov_graph actually flips sign (raw=+0.0087, cal=-0.0023) | PASS |  |
| fig10 | all 4 datasets x 10 methods present and in [0,1] | PASS |  |
| static | no unexplained hardcoded 3+ element float-literal arrays in generate_figures.py (axis ticks/figsize/alpha-filter-values allowlisted) | PASS |  |
