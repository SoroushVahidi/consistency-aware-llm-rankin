# Reproducibility Guide

This guide regenerates every mechanical table and figure cited in the
manuscript from the stored intermediates included in this package (or, for
the full per-query detail, from the code-and-data artifact this package is
extracted from). No step requires rerunning upstream retrieval or any paid
LLM API.

## 1. Environment

- Python 3.12 (tested with 3.12.3; 3.11 also supported).
- Dependency versions used to generate the manuscript's numbers: `numpy
  2.5.1`, `pandas 3.0.3`, `networkx 3.6.1`, `scipy 1.18.0`, `pyscipopt
  6.2.1`, `matplotlib 3.11.0`, `pytest 9.1.1`, `ruff 0.15.20`.
- Exact solver: **SCIP** via `pyscipopt` (open-source; no commercial
  solver dependency anywhere in this pipeline).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
python scripts/check_repo_ready.py   # expect: 0 failures
pytest -q                            # expect: 550 passed
```

## 2. Canonical pipeline map

The manuscript's numbers come from three layers, each building on the last
without modifying it:

| Layer | Directory | Driver script(s) | What it covers |
|---|---|---|---|
| 1. Core protocol comparison | `reports/full_calibrated_core/` | `run_full_calibrated_core.py` | Original 6 protocols x 4 datasets x 3 regimes. **Also regenerates every manuscript figure — only run this if figure regeneration is intended.** |
| 2. Normalization/threshold protocol taxonomy | `reports/normalization_protocol_audit_20260714/` | `run_independent_protocols.py`, `analyze_protocol_robustness.py` | 6 additional independently-defined protocols plus the joint multiplicity-family analysis and the unit-normalized 12-protocol comparison. No figures touched. |
| 3. Candidate-pool, conditional-analysis, and baseline robustness | `reports/candidate_pool_conditional_audit_20260714/` | `run_pool_robustness.py`, `run_conditional_and_failure_analysis.py`, `run_baseline_comparison.py` | 4 alternative candidate pools, the 6-subset conditional analysis, the 5-category failure decomposition, and 4 new baselines. No figures touched. |

Shared modules used by all three layers: `full_calibration_utils.py` (the
calibration/threshold/vote-extraction/repair/evaluation engine),
`candidate_pool_policies.py` (typed `PoolSpec` registry),
`conditional_subsets.py` (per-query classification and failure
decomposition). Copies of all driver and shared-module scripts are under
`supplemental/scripts/`.

## 3. Protocol, pool, and regime identifiers

- **Vote-extraction regimes**: `ms2`, `ms1`, `ms1_drop_mutual`.
- **Protocol registry** (12 entries): canonical-name aliases used in the
  manuscript's prose (`raw_fixed`, `minmax_raw_matched`, `minmax_quantile`,
  `rank_percentile`) map to internal protocol ids; see
  `run_full_calibrated_core.py`.
- **Candidate-pool registry** (5 entries): `rrf_union_topk` (canonical),
  `equal_depth_union`, `neutral_round_robin_union`, `bm25_only`,
  `combsum_union_topk`.
- **Datasets**: `scidocs`, `fiqa`, `hotpotqa`, `bright`; usable query
  counts 120/120/52/50 (Table "Dataset and Query Statistics" in the
  manuscript).

## 4. Seeds and solver configuration

- Bootstrap CI: 10,000 resamples, `seed=13`.
- Paired permutation test: 10,000 permutations, `seed=17`.
- SCIP is used only for the exact-FAS robustness check; the primary repair
  procedure used everywhere else is greedy cycle peeling (deterministic,
  solver-free).

## 5. Exact commands, by manuscript section

```bash
# Layer 1 (WARNING: regenerates figures_v2/*.pdf; only run if intended)
cd reports/full_calibrated_core/scripts && python3 run_full_calibrated_core.py

# Layer 2: normalization/threshold protocol taxonomy
cd reports/normalization_protocol_audit_20260714/scripts
python3 run_independent_protocols.py
python3 analyze_protocol_robustness.py

# Layer 3: candidate-pool robustness, conditional analysis, new baselines
cd reports/candidate_pool_conditional_audit_20260714/scripts
python3 run_pool_robustness.py
python3 run_conditional_and_failure_analysis.py
python3 run_baseline_comparison.py

# Exact-solver robustness check
pytest tests/test_exact_mwfas_scip.py -q

# Full validation
pytest -q
python3 scripts/check_repo_ready.py
cd papers/JDIQ_2026/manuscript && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Layers 2 and 3 each take under two minutes end-to-end on a single CPU core
(no GPU, no paid API calls, no network access required — all inputs are
already-stored score files and qrels).

## 6. Table-to-command map (canonical tables cited in the manuscript)

| Manuscript item | Source table | Produced by |
|---|---|---|
| Structural results, BM25 weight share (Fig. 2) | `full_structural_results.csv`, `full_bm25_weight_share.csv` | Layer 1 |
| Raw-vs-calibrated ablation table | `full_paired_deltas.csv`, `full_statistical_tests.csv`, `full_multiplicity_adjusted.csv` | Layer 1 |
| Structural sensitivity range table | `structural_comparison_all12_pct_units_summary.csv` | Layer 2 |
| Joint multiplicity families (F1/F2/F3) | `joint_multiplicity_family_summary.csv`, `joint_multiplicity_by_family.csv` | Layer 2 |
| Sign-flip statistic (30%, 18/60) | `sign_stability_canonical_protocols.csv` | Layer 2 |
| Candidate-pool robustness table | `pool_overlap_vs_canonical.csv`, `pool_removed_edge_overlap_vs_canonical.csv`, `pool_repaired_ranking_overlap_vs_canonical.csv` | Layer 3 |
| Pool joint multiplicity (240/300 tests) | `pool_robustness_multiplicity_adjusted.csv` | Layer 3 |
| Conditional decomposition table | `conditional_analysis_primary_protocol.csv`, `failure_decomposition_by_protocol.csv`, `failure_decomposition_by_pool.csv` | Layer 3 |
| New-baseline fairness/statistics (48-test family) | `baseline_fairness_verification.csv`, `new_baseline_statistics.csv`, `new_baseline_multiplicity_adjusted.csv` | Layer 3 |

Every row above is regenerated by re-running the listed command(s); none of
these CSVs are hand-edited.

## 7. Per-query detail

This package includes only aggregate tables (`supplemental/tables/`). The
per-query records (`manifest.json` + `query_records.jsonl`, one pair per
protocol/pool x dataset x regime cell, 204 cells total) that back every
aggregate number are not included here because they are large (~1.2 GB)
and their `manifest.json` files record local filesystem paths from the
private working repository. Regenerating Layers 1–3 above from the stored
score files reproduces them exactly, seeded and deterministic.
