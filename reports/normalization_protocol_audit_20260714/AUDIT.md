# Normalization / Threshold Protocol Audit

Prepared before implementing any new protocol or threshold behavior, per task
instruction. Scope: every component responsible for per-query/per-ranker
normalization, pairwise-margin construction, vote/aggregate/support
thresholds, retention matching, protocol manifests, and prior sensitivity
experiments; plus the manuscript text that describes them.

## 1. Where the canonical pipeline actually lives

The manuscript's committed primary-protocol numbers are produced by
**`reports/full_calibrated_core/scripts/full_calibration_utils.py`** (shared
engine, 1065 lines) driven by **`run_full_calibrated_core.py`** (2116 lines).
This is a *separate* implementation from the installable `src/consistency_ranker`
package's `graph_construction.py`; the package provides the general-purpose
`build_graph`/normalization primitives used elsewhere (e.g. `repair_selector_mining`),
while this pair of scripts is the actual source of truth for every number in
`reports/full_calibrated_core/tables/*.csv` and therefore for the manuscript.

Key functions (`full_calibration_utils.py`):
- `calibrate_query_ranker_scores` — dispatches on a `calibration` string:
  `raw`, `minmax_query_ranker`, `zscore_query_ranker`, `rank_percentile`,
  `unit_vote`. `_norm_minmax`/`_norm_zscore` are imported from
  `experiments/method_improvement_audit_20260711_205733/run_method_improvement_audit.py`
  (an experiment-audit module, not the package). `_rank_percentile_scores` and
  an unused `_robust_iqr_scores` (median/IQR, never wired into the dispatch —
  dead code) are defined locally.
- `build_query_vote_artifacts` — builds pairwise margins and votes for one
  query given a `ThresholdConfig`.
- `choose_threshold_config` — **the threshold-selection logic**, dispatches
  on `threshold_mode`: `fixed_numeric` (thresholds fixed at the historical raw
  values regardless of calibration) or `retention_matched` (per-ranker vote
  thresholds set to the empirical quantile of the *calibrated* margin
  distribution that reproduces the *raw* protocol's retained-vote rate, then
  an aggregate threshold chosen to minimize the gap to the raw protocol's
  retained-edge count).
- `raw_baseline_statistics` — computes the raw protocol's retained-vote rates
  and edge count that `retention_matched` targets.

Protocol registry (`run_full_calibrated_core.py: PROTOCOL_SPECS`), each a
`(calibration, threshold_mode)` pair:

| Protocol id (current) | calibration | threshold_mode | kind |
|---|---|---|---|
| `primary_minmax_retention_matched` | minmax_query_ranker | retention_matched | primary |
| `ablation_raw_fixed` | raw | fixed_numeric | ablation |
| `ablation_minmax_fixed` | minmax_query_ranker | fixed_numeric | ablation |
| `ablation_unit_vote_retention` | unit_vote | retention_matched | ablation |
| `robustness_zscore_retention` | zscore_query_ranker | retention_matched | robustness |
| `robustness_rank_percentile_retention` | rank_percentile | retention_matched | robustness |

Every protocol above whose `threshold_mode` is `retention_matched` (5 of 6,
all but the raw ablation itself) has its retention **anchored to the raw
protocol**, confirming the task's diagnosis: no currently-registered protocol
combines a normalization with an independently-defined (non-raw-anchored)
threshold. `ablation_minmax_fixed`'s `fixed_numeric` mode reuses the *raw
scale's* numeric constant (0.05) regardless of calibration, which is a fixed
value, not derived from raw retention *rates*, but was also not designed as a
deliberately-chosen selectivity target for each calibration — it is a
leftover ablation, not a principled independent policy.

Both `run_full_calibrated_core.py` (per protocol/dataset/regime) and the
older experiment-audit module underneath it already write genuine **per-query**
JSONL records (`protocol_runs/{protocol}/{dataset}/{regime}/query_records.jsonl`)
plus a machine-readable `manifest.json` per cell containing git provenance,
score-file hashes, qrels hash, seed, and the exact chosen `vote_thresholds`/
`aggregate_threshold`. This infrastructure already satisfies most of the
"per-query outputs" and "machine-readable manifest" requirements for any
*existing* protocol — new protocols added to `PROTOCOL_SPECS` inherit it for
free.

## 2. A prior investigation already exists — do not duplicate

`reports/retention_matching_investigation/` (uncommitted, dated 2026-07-13)
already ran a 5-policy-family sensitivity sweep (`raw_reference_retention`,
`fixed_calibrated`, `calibrated_quantile_common`, `calibrated_density_target`,
`calibrated_support_only`) — all using **`minmax_query_ranker` calibration
only** — across all 4 datasets × 3 regimes, and its `EXECUTIVE_CONCLUSION.md`
already states the finding this task asks me to re-derive: *"Retention-target
choice materially changes graph density, cyclicity, and edge removal
patterns... no positive repaired-vs-unrepaired cell survives multiplicity
correction... the calibrated paper's negative robustness conclusion therefore
survives, but the graph construction is not policy-invariant."* This is
already reflected in the current manuscript (`main.tex` §3.5 "Retention-Matched
Thresholds" and the Limitations item "Retention-target sensitivity changes
structure more than retrieval robustness") — a prior pass already integrated
it. **This is materially consistent with Option C** in the current task's
framing, already partially adopted.

**Real gaps** relative to what this task requires, that the prior
investigation does not cover:
1. It never tested an independently-thresholded **`rank_percentile`**
   protocol — only `minmax_query_ranker` variants. The task explicitly
   requires `rank_percentile` as one of the four minimum comparison protocols.
2. It saved **aggregates only** (`retention_policy_statistics.csv`,
   `retention_policy_retrieval.csv` — both cell-level means/CIs/p-values, no
   per-query rows), not per-query records. The current task explicitly
   requires per-query outputs.
3. Its `manifests/` directory is empty — thresholds are not saved in a
   machine-readable per-run manifest (only aggregated into summary CSVs).
4. It used a separate one-off script (`run_retention_sensitivity.py`, 1396
   lines) rather than the same `PROTOCOL_SPECS`/`choose_threshold_config`
   registry used for the manuscript's canonical numbers — a second,
   parallel implementation of near-identical logic (the task explicitly asks
   to consolidate rather than duplicate).
5. No typed protocol configuration object, no round-trip tests, no explicit
   qrels-leakage guard, no normalization-invariance unit tests.

**Decision:** extend the *canonical* `full_calibration_utils.py` /
`run_full_calibrated_core.py` pipeline with one new, genuinely independent
threshold policy (`quantile_independent`, see §3), add it to `PROTOCOL_SPECS`
for both `minmax_query_ranker` and `rank_percentile` calibrations (yielding
`minmax_quantile` and `rank_percentile_independent`), and let the existing,
already-validated per-query/manifest infrastructure produce fresh evidence —
rather than re-running or duplicating the prior investigation's own
already-adequate `minmax`-only sweep, which is retained as corroborating
evidence.

## 3. Findings on potential leakage / inconsistency

Checked explicitly, as required:

- **Qrels in threshold selection?** No. `choose_threshold_config`,
  `raw_baseline_statistics`, `build_query_vote_artifacts`, and
  `direction_maps_for_query` take only `raw_scores_by_ranker` and
  `candidate_pool` — qrels are loaded separately in `prepare_dataset_inputs`
  and only reach `CalibrationEvaluator.evaluate_query` (used solely for nDCG
  *evaluation*, never for graph/threshold construction). Confirmed by
  reading every call site; no qrels object is ever passed into
  `choose_threshold_config` or anything it calls.
- **Retrieval outcomes used to pick thresholds?** No — `choose_threshold_config`
  never touches nDCG/ranking outputs; it only aggregates pairwise margins and
  edge counts.
- **Cross-fold information leakage?** Thresholds are pooled **per
  dataset+regime**, computed once from all queries in that cell, then
  applied to the same queries — this is a population-level (not per-query)
  threshold, consistent with the manuscript's own description ("we pool all
  normalized margins ... across the dataset"). There is no train/test split
  in this pipeline to leak across, so this is by design, not a bug — but it
  does mean the threshold is *not* independent of the queries it is later
  applied to (matches the manuscript's honest framing: "not a qrels-tuned"
  threshold, not a claim of query-level independence).
- **Raw-protocol statistics used in places not clearly labeled?** No new
  finding beyond the by-design `retention_matched` policy itself, which *is*
  clearly labeled (`threshold_mode="retention_matched"`, `notes=` field
  states exactly what was matched).
- **Inconsistent denominators for retention rates?** Checked: the "possible"
  (denominator) pair count in `raw_baseline_statistics` requires both
  documents scored and native scores unequal — this exactly matches the
  eligibility check inside `build_query_vote_artifacts`/`direction_maps_for_query`
  (`if direction_a == direction_b: continue` after restricting to scored
  documents). Denominators are consistent.
- **Inconsistent quantile interpolation?** `np.quantile` (default linear
  interpolation) is used uniformly in `choose_threshold_config`. Consistent.
- **Inconsistent tie handling — real finding.** `_rank_percentile_scores`
  breaks *every* tie deterministically by `doc_id` (`sorted(..., key=lambda
  x: (-x[1], x[0]))`) so that no two documents ever receive the same
  percentile value, *even when their native scores were exactly equal*. For
  every other calibration (`raw`, `minmax_query_ranker`,
  `zscore_query_ranker`), a genuine score tie produces
  `direction_a == direction_b` in `build_query_vote_artifacts`, which
  **abstains** (no vote cast) — the documented, intended semantics. For
  `rank_percentile`, the same genuine tie is silently converted into a
  **directional vote** favoring the lexicographically smaller `doc_id`,
  because the percentile transform itself already broke the tie before the
  abstention check ever runs. This is an inconsistency between calibrations:
  `rank_percentile` manufactures pairwise evidence from genuine indifference.
  This does not affect any already-committed number (this behavior is
  internal to the existing `robustness_rank_percentile_retention` protocol,
  which is a secondary robustness check, not the primary protocol, and no
  manuscript claim depends on its exact tie count) — it is fixed for the new
  independently-thresholded `rank_percentile_independent` protocol introduced
  by this task (see §4), and the old protocol is left byte-for-byte
  unchanged to avoid altering any committed result.
- **Missing scores silently imputed?** No — `build_query_vote_artifacts`
  requires `a in raw_direction_map and b in raw_direction_map`; a ranker that
  did not score a document contributes no vote for any pair involving it.
  Confirmed no imputation anywhere in the calibration or thresholding path.
