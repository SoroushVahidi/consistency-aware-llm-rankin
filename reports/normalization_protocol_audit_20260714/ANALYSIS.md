# Cross-Protocol Robustness Analysis and Primary-Protocol Decision

Produced by `scripts/analyze_protocol_robustness.py`, reading only the
per-query paired outputs already written by `run_full_calibrated_core.py`
(6 original protocols, `reports/full_calibrated_core/tables/full_paired_deltas.csv`)
and `run_independent_protocols.py` (6 new protocols,
`tables/independent_protocol_paired_deltas.csv`). No new experiments were
run to produce this file; it is pure re-aggregation with a fresh, jointly
corrected multiplicity analysis. No manuscript figures were touched.

Outputs written to `tables/`: `joint_protocol_statistics_all12.csv` (720
protocol x dataset x regime x pair cells, each with bootstrap CI and a raw
paired-permutation p-value), `joint_multiplicity_by_family.csv` (each of
those cells re-emitted three times, once per pre-specified family, with its
Holm/BH-adjusted p-value *within that family*), `joint_multiplicity_family_summary.csv`,
and `sign_stability_canonical_protocols.csv`.

## 1. Pre-specified multiplicity families

Corrections are never pooled across families, and no family was chosen
after seeing which one had significant cells — all three are reported.

- **F1_headline** = `{primary_minmax_retention_matched, independent_minmax_quantile_q0p5, independent_rank_percentile_q0p5}` x 4 datasets x 3 regimes x 5 pairs = **180 tests**. This is the family that answers the task's central question: does the paper's repair-effect conclusion hold once normalized thresholds are no longer anchored to the raw protocol's retention rate.
- **F2_all_legitimate** = F1 + `robustness_zscore_retention` = **240 tests**. Adds the optional robust-scale calibration the task permits evaluating.
- **F3_everything** = all 12 registered protocols (the above plus `ablation_raw_fixed`, `ablation_minmax_fixed`, `ablation_unit_vote_retention`, `robustness_rank_percentile_retention`, and the q0.3/q0.7 sensitivity-grid points) = **720 tests**. Reported as a conservative upper bound; not used by itself to justify the primary-protocol decision, since it deliberately includes ablations that are not candidate "positive conclusion" protocols.

## 2. Result: the null retrieval conclusion is robust in every family

| family | n_tests | reject Holm(0.05) | reject BH(0.05) | positive AND significant |
|---|---:|---:|---:|---:|
| F1_headline | 180 | 0 | 0 | 0 |
| F2_all_legitimate | 240 | 0 | 0 | 0 |
| F3_everything | 720 | 0 | 0 | 0 |

**No repaired-vs-unrepaired nDCG cell is significant after multiplicity
correction in any family, at any level of independence from the raw
protocol.** This directly answers the task's question: the paper's
existing null-effect conclusion (previously verified only for
`primary_minmax_retention_matched` in isolation, in
`full_multiplicity_adjusted.csv`, 60 tests, 0 rejections) is confirmed to
generalize to the independently-defined `minmax_quantile` and
`rank_percentile` protocols, jointly corrected against each other rather
than tested in separate, smaller families that would have been individually
more permissive.

## 3. Sign stability of the (non-significant) point estimates

Across the 3 canonical protocols (`primary_minmax_retention_matched`,
`independent_minmax_quantile_q0p5`, `independent_rank_percentile_q0p5`),
comparing the sign of `mean_delta_ndcg` per (dataset, regime, pair) cell:
**18 of 60 cells (30%) do not have a consistent sign across the three
protocols.** None of the individual cells are significant in any protocol
(section 2), so this is expected instability of small, noisy point
estimates rather than evidence of a real, protocol-dependent repair effect
— but it means no single protocol's point estimate (including
`primary_minmax_retention_matched`'s) should be quoted as "repair helps
here" or "repair hurts here" for a specific cell without the multiplicity-
corrected null already established in section 2.

## 4. Raw score-scale domination remains uniquely severe to the raw protocol

Mean conditional BM25 edge-weight share (the diagnostic the manuscript
already uses to describe scale distortion), averaged over all
dataset/regime cells:

| protocol | mean BM25 conditional weight share |
|---|---:|
| `ablation_raw_fixed` | **0.988** |
| `primary_minmax_retention_matched` | 0.512 |
| `ablation_minmax_fixed` | 0.486 |
| `ablation_unit_vote_retention` | 0.620 |
| `robustness_zscore_retention` | 0.517 |
| `robustness_rank_percentile_retention` | 0.529 |
| `independent_minmax_quantile_q0p3/q0p5/q0p7` | 0.524 / 0.545 / 0.575 |
| `independent_rank_percentile_q0p3/q0p5/q0p7` | 0.537 / 0.575 / 0.619 |

Every calibration (minmax, z-score, rank-percentile, unit-vote), under
*every* threshold policy tested (raw-fixed numeric, retention-matched, or
independently-defined quantile), collapses BM25's share from ~99% to a
50-62% range. **Raw score-scale domination is confirmed to be a property of
the unnormalized score scale itself, not of any particular threshold
policy** — this manuscript claim survives unchanged and is now supported by
12 protocols instead of 1.

## 5. Structure (density, cyclicity, mutual pairs) is sensitive to threshold policy, with a 3x range post-mutual-deletion — but the primary protocol sits inside that range, not at an outlying extreme

An earlier draft of this section averaged `cyclic_query_pct` across all three
vote regimes and reported a spurious "two orders of magnitude" gap between
raw-matched and independently-thresholded protocols. That was a units bug
in the analysis script, not a finding: `full_structural_results.csv` (the 6
original protocols) stores this column as a 0-1 fraction, while
`independent_protocol_diagnostics_summary.csv` (the 6 new protocols) stores
it as a 0-100 percentage, and blending the two without converting produced
numbers around 0.3-0.5 (fractions, i.e. really 30-50%) sitting next to
numbers around 19-42 (already percentages) and being misread as if both
were percentages. This has been fixed in
`analyze_protocol_robustness.py::_write_structural_comparison`, which now
normalizes both sources to percentage units and writes
`tables/structural_comparison_all12_pct_units.csv` (144 dataset x protocol x
regime rows) and `tables/structural_comparison_all12_pct_units_summary.csv`
(36 protocol x regime rows, averaged over datasets); the numbers below are
read directly from the latter.

`ms2` is uninformative for this comparison: by construction its aggregate
threshold is strict enough that every protocol is at or near $0\%$ cyclic,
so a cross-protocol comparison should be read at `ms1` (support $\ge 1$,
mutual pairs retained) and `ms1_drop_mutual` (support $\ge 1$, mutual pairs
deleted), matching how the manuscript itself already separates these
regimes. Mean over the 4 datasets, percentage units throughout:

| protocol | ms1 mutual-pair % | ms1 cyclic % | cyclic % after mutual-pair deletion |
|---|---:|---:|---:|
| `ablation_raw_fixed` | 88.5 | 88.7 | 14.6 |
| `primary_minmax_retention_matched` | 88.2 | 88.2 | 16.4 |
| `ablation_minmax_fixed` | 99.0 | 99.0 | 26.6 |
| `ablation_unit_vote_retention` | 88.5 | 88.7 | 14.6 |
| `robustness_zscore_retention` | 89.2 | 89.2 | 16.3 |
| `robustness_rank_percentile_retention` | 95.6 | 95.6 | 24.3 |
| `independent_minmax_quantile_q0p3` | 93.1 | 93.1 | 25.0 |
| `independent_minmax_quantile_q0p5` | 81.7 | 81.9 | 19.5 |
| `independent_minmax_quantile_q0p7` | 58.1 | 58.8 | 8.6 |
| `independent_rank_percentile_q0p3` | 98.0 | 98.0 | 27.9 |
| `independent_rank_percentile_q0p5` | 91.3 | 91.3 | 25.8 |
| `independent_rank_percentile_q0p7` | 76.9 | 77.3 | 16.6 |

Two corrected findings replace the retracted "two orders of magnitude" claim:

1. **Threshold selectivity (the quantile $q$) drives a real, first-order
   range.** Across the independently-defined quantile grid alone, `ms1`
   cyclicity ranges from 58.8% ($q=0.7$, least selective... i.e. highest
   margin cutoff, fewest retained votes) to 98.0% ($q=0.3$, most retained
   votes), and the post-mutual-deletion residual ranges from 8.6% to 27.9% —
   roughly a 3x spread. This is a genuine, moderate sensitivity to threshold
   policy, consistent with the manuscript's existing "retention-target
   sensitivity changes structure" limitation, and worth reporting as a
   range rather than a point estimate.
2. **`primary_minmax_retention_matched` is not an outlier within that
   range.** Its `ms1` cyclic rate (88.2%) and post-mutual-deletion residual
   (16.4%) sit inside the span defined by the independently-thresholded
   protocols (58.8-98.0% and 8.6-27.9% respectively), close to the
   `q=0.5` design point on both scales (81.9%/19.5% for minmax,
   91.3%/25.8% for rank-percentile). The retention-matched protocol
   therefore does not systematically understate cyclicity or mutual-pair
   prevalence relative to independently-defined alternatives; it is a
   representative point in the family, not a low-density artifact of
   raw-anchoring.

Mutual-pair deletion still removes the large majority of `ms1` cyclicity in
every protocol (e.g. `primary_minmax_retention_matched`: 88.2% -> 16.4%;
`independent_rank_percentile_q0p3`: 98.0% -> 27.9%), so **mutual pairs
remain the dominant identifiable source of cyclicity across the whole
protocol family**, not just under the primary protocol. A non-trivial
residual (8.6-27.9% of queries, depending on protocol and quantile) remains
cyclic after mutual-pair deletion in every protocol tested; none of the 12
protocols reduces this residual to near zero.

## 6. Removed-edge overlap is moderate, not high

Mean Jaccard overlap of the *removed* (FAS) edge set between each
independently-thresholded protocol and the two raw-anchored reference
protocols, averaged over the 12 dataset/regime cells each:

| protocol | vs `ablation_raw_fixed` | vs `primary_minmax_retention_matched` |
|---|---:|---:|
| `independent_minmax_quantile_q0p3` | 0.596 | 0.674 |
| `independent_minmax_quantile_q0p5` | 0.630 | 0.686 |
| `independent_minmax_quantile_q0p7` | 0.644 | 0.661 |
| `independent_rank_percentile_q0p3` | 0.584 | 0.620 |
| `independent_rank_percentile_q0p5` | 0.599 | 0.617 |
| `independent_rank_percentile_q0p7` | 0.623 | 0.627 |

Roughly 60-69% agreement, i.e. 31-40% of removed edges differ depending on
threshold policy. This is a moderate, not a high, degree of edge-set
stability, consistent with the density/cyclicity finding in section 5:
which edges are removed by repair is meaningfully threshold-policy
dependent, even though the retrieval-metric consequence of removing them is
not statistically distinguishable from zero either way (section 2).

## 7. Primary-protocol decision: Option C

**`primary_minmax_retention_matched` remains the primary protocol**, for
both the retrieval-robustness claim and the headline structural
description, with the methodological justification spelled out below and
with independently-defined protocols reported prominently alongside it
rather than only in a footnote. This is a clean Option C, not a hedged
compromise, because — unlike in the retracted draft of section 5 — the
corrected evidence does not actually split along a retrieval/structural
line once the units bug is fixed:

1. **Retrieval conclusion.** `primary_minmax_retention_matched` is the only
   protocol constructed as a controlled ablation against the historical raw
   protocol (same retained-edge count, different score calibration), which
   isolates a single question — does calibration alone fix the raw
   scale-distortion problem — from retention-rate effects. That isolation
   is methodologically valuable and independently-thresholded protocols
   cannot substitute for it, since their retention rate is a free
   parameter, not held fixed against a reference. Section 2's F1/F2/F3
   joint multiplicity families confirm the null retrieval result generalizes
   to `independent_minmax_quantile_q0p5` and `independent_rank_percentile_q0p5`,
   tested jointly rather than in separate, more permissive per-protocol
   families. Option C's precondition — independently-defined protocols reach
   the same high-level conclusion — holds.
2. **Structural conclusion.** Section 5 (corrected) shows
   `primary_minmax_retention_matched`'s cyclicity and mutual-pair numbers
   are a representative point inside the range spanned by the
   independently-defined quantile grid, not an outlier or an artifact of
   raw-anchoring. There is a real, moderate (roughly 3x) sensitivity to the
   selectivity of the threshold ($q$), and the manuscript must report that
   range rather than a single point estimate (main.tex changes below add
   this range explicitly), but this is a request for completeness, not a
   reason to demote the primary protocol's own numbers as unrepresentative.

The one qualification that does survive from the retraction: **do not
report `primary_minmax_retention_matched`'s structural numbers without also
reporting the range** (Section 5's table), since a single point estimate
understates how much cyclicity/mutual-pair prevalence would change under a
different, equally defensible threshold selectivity. That qualification is
implemented as a manuscript-text addition (Section 10), not as a change to
which protocol is primary.
