# Task 2 Final Report: Normalization / Threshold Protocol Redesign

## 1. Weaknesses in the old threshold design

The canonical pipeline (`full_calibration_utils.py` + `run_full_calibrated_core.py`)
registered 6 protocols. 5 of the 6 non-raw protocols used `threshold_mode="retention_matched"`:
their per-ranker vote threshold was the quantile of the calibrated margin
distribution that reproduced the *raw* protocol's retained-vote rate, and
their aggregate threshold minimized the gap to the raw protocol's retained-
edge count. No protocol combined a normalization with a threshold policy
that was defined independently of the raw protocol's own (scale-distorted)
retention behavior — exactly the weakness the task named. A secondary,
uncommitted investigation (`reports/retention_matching_investigation/`)
had already sensitivity-tested several retention targets, but only for
`minmax_query_ranker`, only as dataset-level aggregates (no per-query
records, no manifests), and via a duplicate one-off script rather than the
canonical registry. A tie-handling inconsistency was also found:
`rank_percentile`'s percentile transform broke every raw-score tie
deterministically by document id, converting genuine ranker indifference
into a manufactured directional vote — inconsistent with every other
calibration, which correctly abstains on ties.

## 2. Protocols implemented

Four canonical names, each mapped to a registered `protocol_id` via
`CANONICAL_NAME_ALIASES` in `run_full_calibrated_core.py`:

| Canonical name | protocol_id | calibration | threshold_mode |
|---|---|---|---|
| `raw_fixed` | `ablation_raw_fixed` | raw | fixed_numeric |
| `minmax_raw_matched` | `primary_minmax_retention_matched` | minmax_query_ranker | retention_matched |
| `minmax_quantile` | `independent_minmax_quantile_q0p5` | minmax_query_ranker | quantile_independent_q0p5 |
| `rank_percentile` | `independent_rank_percentile_q0p5` | rank_percentile_independent | quantile_independent_q0p5 |

Plus a sensitivity grid (`independent_minmax_quantile_q0p3/q0p7`,
`independent_rank_percentile_q0p3/q0p7`) and a new tie-safe calibration,
`rank_percentile_independent` (same percentile values as `rank_percentile`,
but direction/tie-abstention decided from raw scores, not the percentile
transform). 12 protocols are registered in total (6 original + 6 new), all
validated through a new typed `ProtocolSpec` dataclass.

## 3. Exact mathematical definitions

- **Independently-defined quantile threshold** (`quantile_independent_qX`):
  for ranker $s$, dataset/regime cell, $\lambda_s = Q_q(\{m_{q,s}(u,v)\})$,
  the $q$-th empirical quantile ($q\in\{0.3,0.5,0.7\}$, linear interpolation,
  `np.quantile` default) of *that calibration's own* pooled pairwise-margin
  distribution. $\gamma_r = 0$ (no aggregate cut beyond min-support). Never
  reads `baseline_vote_rates`/`baseline_edge_count`/qrels (verified: unit
  test `test_quantile_independent_threshold_ignores_raw_baseline_even_if_supplied`,
  and `test_choose_threshold_config_signature_has_no_qrels_or_relevance_parameter`
  inspects the function signature for forbidden substrings).
- **`rank_percentile_independent` calibration**: percentile value from
  `_rank_percentile_scores` (sort by `(-score, doc_id)`, unique descending
  percentiles), but direction map and tie/abstention decided from the raw
  score map, via the new shared `_direction_and_margin_maps(ranker, ...)`
  helper, so a genuine raw-score tie abstains instead of being broken by
  document id.
- **Retention matching** (`minmax_raw_matched`, unchanged): as already
  documented in `main.tex` Eq. 6 (§3.5.1), reproduced verbatim, not altered
  by this task.

## 4. Files changed

Modified (tracked, pre-existing):
- `papers/JDIQ_2026/manuscript/main.tex` — new §3.5 "Threshold Protocols"
  taxonomy + renamed §3.5.1 "Retention Matching"; new
  §4.x "Structural Sensitivity Across Threshold Protocols" with
  `Table~\ref{tab:structural-sensitivity-range}`; new paragraph in
  §5.2 "Multiplicity and Influence Robustness" reporting the joint
  multiplicity families; new paragraph in §5.3 "Raw Versus Normalized Sign
  Instability" reporting the 30% sign-flip rate; updated Limitations bullet;
  one `TASK 6 TODO` internal comment (no figure files touched).
- `papers/JDIQ_2026/manuscript/main.pdf` — recompiled from the above (figure
  PDFs under `figures_v2/` untouched, verified via `git status`).
- `reports/full_calibrated_core/scripts/full_calibration_utils.py` —
  added `rank_percentile_independent` to `CALIBRATIONS`; added
  `quantile_independent_q0p3/q0p5/q0p7` to `THRESHOLD_MODES`; added
  `ProtocolSpec` frozen dataclass with validation and JSON round-trip; added
  `_direction_and_margin_maps` helper (used by both
  `build_query_vote_artifacts` and a refactored `direction_maps_for_query`);
  added `_parse_quantile_independent_mode`; added the independent-quantile
  branch to `choose_threshold_config`; marked `_robust_iqr_scores` as stale
  dead code with a comment (not deleted, not wired up).
- `reports/full_calibrated_core/scripts/run_full_calibrated_core.py` —
  added 6 new entries to `PROTOCOL_SPECS`; added `CANONICAL_NAME_ALIASES`
  and `PROTOCOL_REGISTRY`.

Created (new):
- `reports/normalization_protocol_audit_20260714/AUDIT.md`,
  `ANALYSIS.md`, `FINAL_REPORT.md` (this file).
- `reports/normalization_protocol_audit_20260714/scripts/run_independent_protocols.py`
  (non-plotting driver for the 6 new protocols; reuses the canonical engine).
- `reports/normalization_protocol_audit_20260714/scripts/analyze_protocol_robustness.py`
  (joint multiplicity families, sign stability, unit-normalized structural
  comparison).
- `reports/normalization_protocol_audit_20260714/tables/*.csv` (13 files:
  per-query paired deltas, structural/ranker diagnostics, statistics,
  removed-edge overlap, joint multiplicity tables, structural comparison).
- `reports/full_calibrated_core/outputs/calibrated_all4/protocol_runs/<6 new protocols>/<4 datasets>/<3 regimes>/{query_records.jsonl,manifest.json,query_method_metrics.csv}`
  (72 cells, per-query records + manifests, same directory convention as
  the 6 original protocols).
- `tests/test_normalization_protocols.py` (26 tests: `ProtocolSpec`
  validation/round-trip, qrels-leakage guard, min-max and rank-percentile
  invariance properties, missing-score non-imputation across all 6
  calibrations).
- `reports/retention_matching_investigation/SUPERSEDED.md` (marks the prior
  duplicate investigation stale; nothing deleted).

## 5. Commands run

```
python3 reports/normalization_protocol_audit_20260714/scripts/run_independent_protocols.py
python3 reports/normalization_protocol_audit_20260714/scripts/analyze_protocol_robustness.py
python3 -m pytest -q
python3 scripts/check_repo_ready.py
ruff check / ruff format --line-length 100  (on newly authored files only)
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex  (in papers/JDIQ_2026/manuscript/)
```

## 6. Tests / experiment results

- Full protocol sweep: 4 datasets x 6 new protocols x 3 regimes = 72 cells,
  30,780 per-query paired rows, 6,156 structural rows, 0 exclusions,
  ~54s wall time. Re-run twice; identical row counts and identical joint
  multiplicity results both times (deterministic).
- `pytest -q`: **510 passed**, including the new 26-test
  `test_normalization_protocols.py` and the pre-existing 510-test suite
  (SCIP exact-solver tests from the prior task's fix still pass, confirming
  no regression there either).
- `scripts/check_repo_ready.py`: 56 OK, 5 pre-existing warnings (missing
  optional docs, `ir-datasets` not installed — unrelated to this task),
  0 failures.
- `ruff check` on the 3 newly authored files: 0 errors (was 55, mostly
  line-length, fixed via `ruff format` + 6 manual wraps). The 2 pre-existing
  files I extended (`full_calibration_utils.py`,
  `run_full_calibrated_core.py`) retain 173 pre-existing lint findings
  (145 of them line-length) that predate this task and were not introduced
  by my edits — verified by isolating non-line-length findings and
  confirming none fall inside code I added or modified; a full reformat of
  those 1000+/2000+-line manuscript-critical files was judged out of scope
  and risky for this task.
- Regression safety: byte-for-byte MD5 comparison of regenerated
  `query_records.jsonl` for `primary_minmax_retention_matched/hotpotqa/ms1`
  and `robustness_zscore_retention/hotpotqa/ms1` against pre-existing files
  on disk — identical. A third cell,
  `robustness_rank_percentile_retention/hotpotqa/ms1`, differed only in the
  `calibration_meta.tie_rule` *description string* (an intentional
  documentation clarification); every `rows`/`retained_vote_counts`/nDCG
  field was confirmed identical across all 52 queries by parsing both files
  and diffing every field except that one string.

## 7. Did the manuscript's high-level conclusion change?

**No.** The null retrieval-robustness conclusion ("no positive repaired-
versus-unrepaired nDCG cell survives multiplicity correction") is now
confirmed under three pre-specified joint multiplicity families spanning
the independently-defined protocols (180, 240, and 720 jointly-corrected
tests; 0 rejections in every family), not just under the primary protocol
in isolation as before. Raw score-scale domination (BM25 ~99% share) is
confirmed unique to the unnormalized protocol across all 12 protocols
(50-62% for every calibration/threshold combination). Mutual pairs are
confirmed as the dominant source of cyclicity across the whole protocol
family, not only the primary protocol. One earlier internal draft finding
("structural sensitivity spans two orders of magnitude and the primary
protocol understates it") was a units bug in my own analysis script (mixing
0-1 fraction and 0-100 percentage columns from two different CSVs) — it was
caught before reaching the manuscript, the script was fixed, and the
corrected finding (a real but roughly threefold sensitivity range, with the
primary protocol sitting inside that range rather than at an outlying
extreme) is what was actually written into `main.tex` and `ANALYSIS.md`.

## 8. Which protocol is now primary, and why

**`minmax_raw_matched` (`primary_minmax_retention_matched`) remains
primary**, per Option C. Justification (`ANALYSIS.md` section 7,
`main.tex` §3.5.1): it is the only protocol constructed as a controlled
ablation against the raw protocol (retained-edge count held approximately
fixed), which isolates score-scale handling from retention-rate effects;
independently-defined protocols cannot substitute for that isolation since
their retention rate is a free, pre-registered parameter. The retrieval
conclusion produced under it is confirmed (section 7 above) to generalize
to the independently-defined protocols under a joint multiplicity
correction, satisfying Option C's precondition. Structural diagnostics must
now be reported as a range across the protocol family
(Table~\ref{tab:structural-sensitivity-range} in `main.tex`), not as a
single point estimate from the primary protocol alone — this is the one
qualification added to how the primary protocol's own numbers may be used,
not a change in which protocol is primary.

## 9. Canonical result tables

- `reports/normalization_protocol_audit_20260714/tables/joint_protocol_statistics_all12.csv`
  (720 rows: every protocol x dataset x regime x pair cell).
- `reports/normalization_protocol_audit_20260714/tables/joint_multiplicity_by_family.csv`
  and `joint_multiplicity_family_summary.csv` (the F1/F2/F3 joint
  corrections cited in `main.tex` §5.2).
- `reports/normalization_protocol_audit_20260714/tables/structural_comparison_all12_pct_units.csv`
  and `..._summary.csv` (source of `main.tex`
  Table~\ref{tab:structural-sensitivity-range}).
- `reports/normalization_protocol_audit_20260714/tables/sign_stability_canonical_protocols.csv`
  (source of the 30% sign-flip figure in `main.tex` §5.3).
- The 6 original protocols' existing tables under
  `reports/full_calibrated_core/tables/` remain canonical and unchanged for
  everything not superseded above (e.g. `full_multiplicity_adjusted.csv`
  for the primary-protocol-only correction, still cited in §5.2 for
  context alongside the new joint families).

## 10. Which figures are now stale (for task 6, not touched here)

None of fig2-fig9 are factually wrong (the primary protocol's own numbers
did not change), but fig3 (`fig3_cyclicity_primary.pdf`) and fig5
(`fig5_cycle_decomposition.pdf`) currently show only the primary protocol's
cyclicity, while the manuscript text now also reports the independently-
defined protocols' range in a text table
(`Table~\ref{tab:structural-sensitivity-range}`). Task 6 should consider
adding a panel or overlay showing the `minmax_quantile`/`rank_percentile`
$q\in\{0.3,0.5,0.7\}$ range alongside the primary protocol's line so the
sensitivity range is visible in the figure, not only in the table. This is
flagged with a `% TASK 6 TODO` comment directly above
`Table~\ref{tab:structural-sensitivity-range}` in `main.tex`, per the task's
instruction not to touch figures in this pass.

## 11. Remaining limitations

- The independently-defined quantile grid (`q=0.3/0.5/0.7`) is a
  pre-registered but still finite grid; a continuous sensitivity curve was
  not computed (would be a straightforward extension of the same driver).
- `minmax_quantile`/`rank_percentile` thresholds are pooled per
  dataset/regime cell (population-level, not per-query), matching the
  existing `minmax_raw_matched` convention and the manuscript's own
  "not a claim of query-level independence" framing — this is by design,
  not a new gap.
- The `q=0.5` design points were chosen as the "headline" independent
  protocols before seeing results, but the choice of exactly 3 grid points
  (not, say, 5 or 9) was a scope/compute-budget decision, not derived from
  a formal power analysis.
- The pre-existing lint debt in the two large canonical engine files
  (173 findings, overwhelmingly line-length) was left as-is; a full
  reformat was judged out of scope and risky for a manuscript-critical file
  in this task.

## 12. Exact reproduction command

```bash
cd /home/soroush/consistency-aware-llm-rankin
python3 reports/normalization_protocol_audit_20260714/scripts/run_independent_protocols.py
python3 reports/normalization_protocol_audit_20260714/scripts/analyze_protocol_robustness.py
python3 -m pytest tests/test_normalization_protocols.py -q
cd papers/JDIQ_2026/manuscript && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

## 13. Summary

The redesign implements all four minimum-required protocols
(`raw_fixed`, `minmax_raw_matched`, `minmax_quantile`, `rank_percentile`)
plus a 2-point sensitivity grid for each independent protocol, all through
the existing canonical engine (no parallel implementation), with per-query
outputs and manifests for every cell, a fixed tie-handling bug isolated to
a new calibration identifier (old protocol byte-identical), a typed and
tested `ProtocolSpec` configuration layer, a jointly-corrected multiplicity
analysis spanning 1,140 tests across three pre-specified families, and
manuscript text/table updates that report the finding honestly, including
a self-caught and corrected units bug in the intermediate structural
analysis. No manuscript figures were regenerated or edited. The paper's
null retrieval-robustness conclusion is confirmed to generalize beyond the
primary protocol; the primary protocol itself remains
`minmax_raw_matched`, now justified explicitly rather than by default.
