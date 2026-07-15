# Supplemental Package Inventory

What this repository actually contains for a reviewer or reader who wants
to go beyond the manuscript text. This is an inventory, not a how-to; for
exact commands see `docs/REPRODUCTION_CANONICAL.md` (repo root).

## 0. Freeze manifest and figure-data verification (added at final freeze)

- `papers/JDIQ_2026/submission/SUBMISSION_FREEZE_MANIFEST.json` — machine-
  readable record of the exact frozen inputs behind this submission: git
  commit, checksums for every canonical table (54 files across 4 report
  directories), provenance read back from all 204 per-cell manifests
  (qrels hash, score-file hashes per dataset), the full protocol/pool/
  regime/method registries, the statistical-family definitions, and solver
  configuration. Regenerate with `papers/JDIQ_2026/submission/scripts/build_freeze_manifest.py`.
- `papers/JDIQ_2026/submission/FIGURE_DATA_VERIFICATION_REPORT.md` — 13
  independent checks confirming every plotted value in Figures 2, 4, 6-10
  is present, in-range, and consistent with the manuscript's own stated
  claims (including that the 5 named sign-flip cells actually flip sign in
  the source data). Regenerate with
  `papers/JDIQ_2026/submission/scripts/verify_figure_data.py`.
- `papers/JDIQ_2026/submission/FIGURE_INVENTORY.md` — every figure's
  source script, source CSV, protocol/dataset scope, and canonical/
  superseded status.

## 1. Reproduction instructions

`docs/REPRODUCTION_CANONICAL.md` — environment setup, git commit,
dependency versions, the three-layer pipeline map, and exact commands for
every major experiment. `docs/REPRODUCTION_Q1.md` documents an older,
different results package and is marked superseded; do not use it for this
manuscript.

## 2. Protocol and pool definitions

- Normalization/threshold protocols: `reports/full_calibrated_core/scripts/run_full_calibrated_core.py`
  (`PROTOCOL_SPECS`, 12 entries) and `full_calibration_utils.py`
  (`ProtocolSpec` typed dataclass, `choose_threshold_config`). Canonical
  names used in the manuscript (`raw_fixed`, `minmax_raw_matched`,
  `minmax_quantile`, `rank_percentile`) map to internal ids via
  `CANONICAL_NAME_ALIASES`.
- Candidate-pool policies: `reports/full_calibrated_core/scripts/candidate_pool_policies.py`
  (`PoolSpec` typed dataclass, `POOL_SPECS`, 5 entries: canonical
  RRF-fused pool plus 4 independently-defined alternatives).
- Both registries validate their own entries at import time (`__post_init__`)
  and round-trip to/from JSON (`to_dict`/`from_dict`), so the exact
  configuration behind any reported number is machine-readable, not only
  described in prose.

## 3. Experiment manifests

Every protocol/pool x dataset x regime cell writes a `manifest.json`
recording git branch/commit, generation timestamp, protocol/pool spec,
qrels hash, source score-file hashes, the query id list actually evaluated,
excluded query ids and reasons, the random seed, and the exact chosen
thresholds. 144 manifests under
`reports/full_calibrated_core/outputs/calibrated_all4/protocol_runs/*/*/*/manifest.json`
(12 protocols x 4 datasets x 3 regimes) and 60 under
`reports/full_calibrated_core/outputs/calibrated_all4/pool_runs/*/*/*/manifest.json`
(5 pools x 4 datasets x 3 regimes).

## 4. Per-query records

Every evaluated query has a full per-query JSONL record (`query_records.jsonl`
alongside each manifest) with candidate pool, vote thresholds, retained
vote/weight counts, graph statistics before and after repair, removed
edges, and per-method retrieval metrics -- the level of detail underlying
every aggregate number in the manuscript's tables.

## 5. Robustness tables

- Original 6-protocol comparison: `reports/full_calibrated_core/tables/*.csv`
  (structural results, statistical tests, multiplicity correction, BM25
  weight share, cycle decomposition, removed-edge overlap, alpha
  sensitivity, influence removal, leave-one-out, RRF-implementation audit,
  query exclusions).
- Normalization/threshold protocol robustness (6 additional independently-
  defined protocols): `reports/normalization_protocol_audit_20260714/tables/*.csv`,
  including the joint multiplicity family analysis
  (`joint_multiplicity_by_family.csv`, `joint_multiplicity_family_summary.csv`)
  and the corrected, unit-normalized structural comparison
  (`structural_comparison_all12_pct_units_summary.csv`).
- Candidate-pool, conditional-analysis, and baseline robustness:
  `reports/candidate_pool_conditional_audit_20260714/tables/*.csv`,
  including pool overlap/agreement (`pool_overlap_vs_canonical.csv`,
  `pool_removed_edge_overlap_vs_canonical.csv`,
  `pool_repaired_ranking_overlap_vs_canonical.csv`), joint multiplicity for
  pools and new baselines (`pool_robustness_multiplicity_adjusted.csv`,
  `new_baseline_multiplicity_adjusted.csv`), the conditional/failure-
  decomposition tables (`conditional_analysis_primary_protocol.csv`,
  `failure_decomposition_by_protocol.csv`, `failure_decomposition_by_pool.csv`),
  and the fairness-verification table (`baseline_fairness_verification.csv`).
- Exact-solver validation: `reports/exact_open_source_ilp_repair_investigation/`
  (SCIP-vs-greedy comparison across 1,025 query-regime graphs, plus a
  49-case brute-force validation of SCIP's optimality).

## 6. Complete statistical outputs

Every repaired-versus-unrepaired comparison anywhere in this package
reports, per cell: sample size, mean delta, bootstrap 95% CI (10,000
resamples, seed 13), the fraction of bootstrap means above zero, a paired
permutation p-value (10,000 permutations, seed 17), and, wherever the cell
belongs to one of the pre-specified joint multiplicity families, both
Holm-adjusted and Benjamini-Hochberg-adjusted p-values with an explicit
reject/fail-to-reject flag at alpha=0.05. No point estimate anywhere in the
canonical tables is reported without its corresponding uncertainty/
significance columns alongside it.

## 7. Analysis narratives

Each of the three audit rounds that extended the original study has its
own audit trail: `reports/normalization_protocol_audit_20260714/{AUDIT.md,ANALYSIS.md,FINAL_REPORT.md}`
and `reports/candidate_pool_conditional_audit_20260714/{AUDIT.md,ANALYSIS.md,FINAL_REPORT.md}`.
These document the pre-implementation audit, the analysis and any
self-corrections found along the way (including one disclosed numerical
error, since fixed -- see `FINAL_REPORT.md`'s item on the "1,704" vs
"1,026" query count), and a final report against the same 13-item
structure used throughout this project.

## 8. Test suite

550 automated tests (`pytest -q`), including protocol/pool registry
validation and round-trip tests, normalization-invariance property tests
(min-max affine invariance, rank-percentile monotone invariance, missing-
score non-imputation), candidate-pool determinism and no-qrels-leakage
tests, conditional-subset classification tests, new-baseline fairness and
determinism tests, and an exact-vs-brute-force MWFAS validation test suite.
