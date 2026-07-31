# Canonical Clustered-Inference Protocol for Real-LLM Studies

**Applies to**: `repair_frontier_20260729T144742Z`, `extraction_study_20260729T151610Z`, `repair_diagnostic_20260729T162748Z`, and any future study built on the same 6-real-query, real-multi-provider-LLM sample.

**Why this protocol exists**: all three studies report "n=120" observations. Direct enumeration this stage (see `analysis_population_manifest.csv`) confirms these 120 rows are **6 unique underlying natural-language queries** (3 SciDocs + 3 FiQA), each replicated across 4 construction variants (`pool6_original`, `pool8_complete`, `pool8_sparse57`, `pool10_sparse56`) × 5 providers (azure/gemini/cohere/fireworks/aggregate) = 20 rows/query × 6 queries = 120. The original analyses' bootstrap CIs and correlation p-values resampled/tested at the row level (n=120), which silently treats within-query replicates as independent evidence. This protocol makes the query the unit of inference everywhere.

## 1. Independence cluster

**The independence cluster is `query_id`.** Confirmed (not assumed) that all three studies share the identical 6 query_id values and the identical 120-unit_key construction grid (verified via `frozenset`-normalized unit_key comparison across all three studies' JSONL files — see `population.py`). Provider and construction-variant are treated as *repeated measurements within* a query cluster, not additional independent samples, because all providers/variants for a given query operate on the same underlying documents and the same qrels.

## 2. Required methods (all four implemented, none treated as a substitute for another)

1. **Query-level cluster (block) bootstrap** — `cluster_bootstrap_mean_interval()` (`src/consistency_ranker/statistical_inference.py`). Resamples the **cluster labels**, not rows: each of 10,000 replicates draws 6 cluster identities with replacement from the observed 6, then averages those clusters' already-aggregated per-cluster means. Method: percentile CI. Seed: 13. Reps: 10,000.
2. **Exact permutation-based paired tests** — `cluster_exact_sign_flip_pvalue()` for mean deltas (enumerates all 2⁶=64 sign patterns exactly) and `cluster_exact_permutation_correlation()` for feature-outcome associations (enumerates all 6!=720 relabelings exactly for n≤8 clusters, falls back to seeded Monte Carlo for larger cluster counts — not needed here since every study has exactly 6 clusters).
3. **Query-level aggregation followed by paired comparison** — `compute_cluster_means()` aggregates each query's 20 (or more, for `repair_frontier`) replicate rows to one mean before any test is run; this aggregated 6-number vector is what every test in this protocol actually operates on, never the raw 120-row vector.
4. **Descriptive effect sizes and complete per-query results** — `per_query_effects.csv` reports every cluster's raw mean effect for every comparison, with no significance filtering; this is the primary output a reader should look at first, before any p-value.

## 3. Explicit small-sample discipline

- **Row-level asymptotic standard errors are never reported as authoritative.** `bootstrap_mean_interval()` (the original, row-level function) is not called anywhere in this re-analysis.
- **No claim of high statistical power.** With 6 clusters, the cluster bootstrap can only realize `comb(11,6) = 462` distinct resample compositions; this is stated plainly, not glossed over.
- **Failure to reject is never read as proof of equality.** Every "not significant" result in this package is reported as "no evidence of an effect, given 6 queries," not "no effect."
- **Effect direction consistency across the 6 queries is reported for every comparison** (`n_query_level_wins`/`n_query_level_losses`/`n_query_level_ties`, `direction_consistent_across_queries`) — this is often more informative than the p-value at n=6.
- **The number of independent queries (6) is reported alongside every statistic**, never left implicit behind an "n=120" label.

## 4. Handling of missing configurations, ties, and family definitions

- **Missing configurations**: none found (see `analysis_population_manifest.csv` — every query has exactly 20 rows in `extraction_study`/`repair_diagnostic`; `repair_frontier` has a variable candidate count per unit by design, not a missing-data gap — see `frontier_reconstruction_verification.json`'s `n_outcomes_recomputed == n_outcomes_published == 120`).
- **Ties**: a query-level "tie" is recorded when the cluster mean effect equals exactly 0.0 (e.g. `balance_score` and `fas_balance_prior_fusion` in `extraction_clustered_results.csv`, reflecting queries where that extractor's ranking was byte-identical to the incumbent's for every row in that cluster).
- **Multiple-comparison family definitions** — declared *before* looking at results, per `multiple_comparison_families.csv`:
  - `extraction_study_vs_incumbent`: all 8 extractors compared against the incumbent (7 alternatives + `copeland`, which is numerically identical to incumbent by construction and included as the 8th declared family member per the task brief's explicit "eight extractors" framing).
  - `repair_diagnostic_feature_associations`: all 23 pre-/post-repair features (19 pre-repair + 4 post-repair), matching the original study's own family definition.
  - `repair_frontier_comparisons`: the 3 `repair_frontier` diagnostics (oracle-upper-bound, whole-graph-repair, best-alt-extraction) are reported **without** cross-correction, because they are conceptually distinct diagnostics answering different questions (an upper bound is not a hypothesis test), not repeated tests of the same hypothesis — matching the original study's own framing (`FINAL_REPORT.md`'s sections 1-6 pose distinct questions, not a single repeated comparison).
- **Correction method**: Holm step-down (`holm_adjust()`, already used throughout this codebase) applied within each declared family.

## 5. Minimum sample requirements

`cluster_bootstrap_mean_interval()` raises `ValueError` rather than silently returning a CI if fewer than 3 clusters are present. `cluster_exact_permutation_correlation()` returns `method="insufficient_clusters"` (no p-value) below 3 clusters. Neither function will silently produce a number for degenerate cluster counts.

## 6. Determinism

Every stochastic step (the cluster bootstrap) uses `numpy.random.default_rng(seed=13)`. The exact permutation tests are deterministic by construction (full enumeration, no randomness). Re-running `scripts/run_real_llm_clustered_reanalysis.py` twice produces byte-identical output (verified this stage — see `validation_results.md`).

## 7. What this protocol does NOT do

- It does not collect new data, call any LLM API, or add a 7th query. It re-analyzes only the 120/120/432 already-stored rows across the three studies.
- It does not claim equivalence (`Δ ≈ 0`) for any non-significant result — no equivalence margin is defined anywhere in this package, per the task brief's explicit instruction not to claim equivalence without one.
- It does not modify `repair_frontier_20260729T144742Z/`, `extraction_study_20260729T151610Z/`, or `repair_diagnostic_20260729T162748Z/`'s original numeric files — see the `STATUS.md` marker added to each (non-destructive, additive only).
