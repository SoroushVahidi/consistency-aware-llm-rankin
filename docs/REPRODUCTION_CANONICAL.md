# Canonical Reproduction Guide (JDIQ 2026 Manuscript)

> **This is the current, accurate reproduction guide for
> `papers/JDIQ_2026/manuscript/main.tex`.** It supersedes
> `docs/REPRODUCTION_Q1.md`, which describes an older, different results
> package (`outputs/pub_vote_cmp_all4/` / `outputs/pub_vote_cmp_v2/`) that
> is **not** what the current manuscript cites. `REPRODUCTION_Q1.md` is
> kept for historical reference and marked accordingly; do not follow it to
> reproduce this manuscript's numbers.

## 1. Environment

- Python 3.12 (tested with 3.12.3; 3.11 is also supported per `pyproject.toml`).
- Dependency constraints are declared in `pyproject.toml` and
  `requirements.txt`. These are install constraints, not a lock file; exact
  versions for individual generated outputs are recorded in their
  reproducibility manifests or report-level environment captures.
- Exact solver: **SCIP** via `pyscipopt` (open-source, no commercial
  solver dependency — Gurobi is not used anywhere in the current pipeline).

```bash
git clone https://github.com/SoroushVahidi/consistency-aware-llm-rankin.git
cd consistency-aware-llm-rankin
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e ".[dev,exact]"  # [exact] installs PySCIPOpt==6.2.1,
                                         # required for SCIP-dependent
                                         # exact-repair validation
python scripts/check_repo_ready.py   # expect: 0 failures
make verify-env                      # expect: PySCIPOpt 6.2.1 reported, exits 0
make test-full                       # expect: 0 skipped (fails otherwise); run `pytest -q`
                                      # for the pass count, which changes as tests are added --
                                      # require zero failures and zero skips, not a fixed count
```

## 2. Repository state

This guide is maintained as a living document. Record the exact code state
used for any reproduction run with:

```bash
git rev-parse HEAD
git status --short --branch
```

For manuscript evidence, prefer each report's own manifest/provenance files
over any static commit hash in prose.

## 3. Canonical pipeline map

The manuscript's numbers come from three layers, each building on the last
without modifying it:

| Layer | Directory | Driver script(s) | What it covers |
|---|---|---|---|
| 1. Core protocol comparison | `reports/full_calibrated_core/` | `scripts/run_full_calibrated_core.py` (`run_full_core()`) | The original 6 protocols (`ablation_raw_fixed`, `primary_minmax_retention_matched`, `ablation_minmax_fixed`, `ablation_unit_vote_retention`, `robustness_zscore_retention`, `robustness_rank_percentile_retention`) x 4 datasets x 3 regimes. **Also regenerates all manuscript figures (`figures_v2/*.pdf`) — do not run this unless you intend to regenerate figures.** |
| 2. Normalization/threshold protocol taxonomy | `reports/normalization_protocol_audit_20260714/` | `scripts/run_independent_protocols.py`, `scripts/analyze_protocol_robustness.py` | 6 additional independently-defined protocols (`independent_minmax_quantile_q0p3/q0p5/q0p7`, `independent_rank_percentile_q0p3/q0p5/q0p7`) plus the joint multiplicity-family analysis (F1/F2/F3) and the unit-normalized structural comparison across all 12 protocols. No figures touched. |
| 3. Candidate-pool, conditional-analysis, and baseline robustness | `reports/candidate_pool_conditional_audit_20260714/` | `scripts/run_pool_robustness.py`, `scripts/run_conditional_and_failure_analysis.py`, `scripts/run_baseline_comparison.py` | 4 alternative candidate pools, the 6-subset conditional analysis, the 5-category failure decomposition, and 4 new baselines (PageRank, RankCentrality, Markov-hybrid, Bradley-Terry). No figures touched. |

Shared, reusable modules (imported by all three layers' scripts):
`reports/full_calibrated_core/scripts/full_calibration_utils.py` (the
calibration/threshold/vote-extraction/repair/evaluation engine),
`candidate_pool_policies.py` (typed `PoolSpec` registry),
`conditional_subsets.py` (per-query classification and failure
decomposition).

## 4. Protocol, pool, and regime identifiers

- **Vote-extraction regimes** (`REGIMES` in `full_calibration_utils.py`):
  `ms2`, `ms1`, `ms1_drop_mutual`.
- **Protocol registry** (`PROTOCOL_SPECS` /
  `run_full_calibrated_core.PROTOCOL_REGISTRY`, 12 entries): see
  `run_full_calibrated_core.py` for the full `{calibration, threshold_mode,
  label, kind}` definition of each. Canonical-name aliases used in the
  manuscript's prose (`raw_fixed`, `minmax_raw_matched`, `minmax_quantile`,
  `rank_percentile`) map to internal protocol ids via
  `CANONICAL_NAME_ALIASES`.
- **Candidate-pool registry** (`POOL_SPECS` in `candidate_pool_policies.py`,
  5 entries): `rrf_union_topk` (canonical), `equal_depth_union`,
  `neutral_round_robin_union`, `bm25_only`, `combsum_union_topk`.
- **Datasets**: `scidocs`, `fiqa`, `hotpotqa`, `bright` (`DATASETS` in
  `run_full_calibrated_core.py`); usable query counts 120/120/52/50
  (Table~\ref{tab:dataset-stats} in the manuscript).

## 5. Seeds and solver configuration

- Bootstrap CI: 10,000 resamples, `seed=13` (`bootstrap_ci` in
  `full_calibration_utils.py`).
- Paired permutation test: 10,000 permutations, `seed=17`
  (`paired_permutation_pvalue`).
- Per-query manifests additionally record `"seed": 13` as the run-level
  seed for the driver scripts themselves.
- SCIP (via `pyscipopt`) is used only for the exact-FAS robustness check
  (`tests/test_exact_mwfas_scip.py` and the repair-variants section of the
  manuscript); the primary repair procedure used everywhere else is greedy
  cycle peeling, which is deterministic and solver-free.

## 6. Exact commands, by manuscript section

```bash
# Layer 1 (WARNING: regenerates figures_v2/*.pdf; only run if that is intended)
cd reports/full_calibrated_core/scripts && python3 run_full_calibrated_core.py

# Layer 2: normalization/threshold protocol taxonomy (Sec. "Threshold Protocols",
# "Structural Sensitivity Across Threshold Protocols", the F1/F2/F3 joint
# multiplicity paragraphs in "Multiplicity and Influence Robustness")
cd reports/normalization_protocol_audit_20260714/scripts
python3 run_independent_protocols.py
python3 analyze_protocol_robustness.py

# Layer 3: candidate-pool robustness, conditional analysis, new baselines
# (Sec. "Candidate-Pool Robustness", "Conditional Analysis and Failure
# Decomposition", the extended Table~\ref{tab:baselines})
cd reports/candidate_pool_conditional_audit_20260714/scripts
python3 run_pool_robustness.py
python3 run_conditional_and_failure_analysis.py
python3 run_baseline_comparison.py

# Exact-solver robustness check (Sec. "Repair Configuration" / repair variants)
pytest tests/test_exact_mwfas_scip.py -q

# Full validation
pytest -q
python3 scripts/check_repo_ready.py
ruff check <touched files>
cd papers/JDIQ_2026/manuscript && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Layers 2 and 3 each take under two minutes end-to-end on a single CPU core
(no GPU, no paid API calls, no network access required — all inputs are
already-stored score files and qrels under
`experiments/method_improvement_audit_20260711_205733/inputs/`).

## 7. Table-to-command map (canonical tables cited in the manuscript)

| Manuscript item | Source table | Produced by |
|---|---|---|
| Table~\ref{tab:structural-results}, BM25 weight share (Fig. 2) | `reports/full_calibrated_core/tables/full_structural_results.csv`, `full_bm25_weight_share.csv` | Layer 1 |
| Table~\ref{tab:raw-calibrated-ablation} | `full_paired_deltas.csv`, `full_statistical_tests.csv`, `full_multiplicity_adjusted.csv` | Layer 1 |
| Table~\ref{tab:structural-sensitivity-range} | `reports/normalization_protocol_audit_20260714/tables/structural_comparison_all12_pct_units_summary.csv` | Layer 2 |
| Joint multiplicity families (F1/F2/F3) | `joint_multiplicity_family_summary.csv`, `joint_multiplicity_by_family.csv` | Layer 2 |
| Sign-flip statistic (30%, 18/60) | `sign_stability_canonical_protocols.csv` | Layer 2 |
| Table~\ref{tab:pool-robustness} | `reports/candidate_pool_conditional_audit_20260714/tables/pool_overlap_vs_canonical.csv`, `pool_removed_edge_overlap_vs_canonical.csv`, `pool_repaired_ranking_overlap_vs_canonical.csv` | Layer 3 |
| Pool joint multiplicity (240/300 tests) | `pool_robustness_multiplicity_adjusted.csv` | Layer 3 |
| Table~\ref{tab:conditional-hotpotqa}, failure decomposition | `conditional_analysis_primary_protocol.csv`, `failure_decomposition_by_protocol.csv`, `failure_decomposition_by_pool.csv` | Layer 3 |
| New-baseline fairness/statistics (48-test family) | `baseline_fairness_verification.csv`, `new_baseline_statistics.csv`, `new_baseline_multiplicity_adjusted.csv` | Layer 3 |

Every row above is regenerated by re-running the listed command(s); none of
these CSVs are hand-edited (verified by the consistency checks in
`reports/*/FINAL_REPORT.md` for Tasks 2 and 3, and re-verified as part of
this manuscript-quality audit).
