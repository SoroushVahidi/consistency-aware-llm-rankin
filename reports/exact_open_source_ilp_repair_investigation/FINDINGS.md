# Findings — Exact Open-Source ILP Repair vs. Canonical Greedy Cycle-Peeling Repair

**Question investigated:** Does an exact, open-source-solver MWFAS repair change the
**structural** or **retrieval** conclusions of `reports/full_calibrated_core/` relative
to the canonical greedy cycle-peeling repair?

**Scope:** Primary protocol (`primary_minmax_retention_matched`), all 4 datasets (bright,
fiqa, hotpotqa, scidocs), all 3 vote regimes (ms1, ms1_drop_mutual, ms2) — **1,025 queries
total**, every one solved to **proven optimality** by SCIP (open-source; see Solver section).

## Bottom line

- **Structural conclusion: changes materially.** On the 379 queries whose raw preference
  graph actually contains a cycle (repair matters), the exact solver finds a **different
  feedback-arc set than greedy in 87.9% of them**, and removes **26.3% less total edge
  weight on average** (mean 4.60 vs. 6.24) than the canonical greedy heuristic. Greedy
  cycle-peeling is a real, non-trivial overestimate of the minimum weighted feedback arc
  set on this data — not just a theoretical possibility.
- **Retrieval conclusion: does not change.** Across every repaired-graph-dependent
  downstream method (Copeland, Balance, Markov, both hybrids, topological, priority-
  topological) and every validated metric (nDCG@5/10/20, MRR, MAP), pooled over all 1,025
  queries: **zero of 35 metric×method cells survive Holm correction**, and the largest
  raw (pre-correction) effect is a mean nDCG@10 delta of ‑0.00223 (priority-topological;
  raw p=0.026, Holm p=0.91). At the finer per-dataset/regime granularity (399 cells),
  **zero cells survive Holm correction either.** The manuscript's retrieval-level
  comparisons and conclusions are robust to swapping in the exact repair.
- **Net takeaway:** the greedy heuristic's sub-optimality is real and substantial at the
  *graph-repair* level, but it washes out at the *ranking-quality* level for every
  validated retrieval metric — i.e. classification **B (metric/structure-sensitive
  detail, main retrieval conclusion robust)**, matching the pattern already found by the
  separate, unrelated `reports/additional_metrics_investigation/` for a different axis
  (additional metrics vs. the same greedy repair).

## Per-dataset structural gap (cyclic queries only, i.e. where repair is non-trivial)

| dataset | n cyclic queries | mean weight removed (greedy) | mean weight removed (exact ILP) | % less weight removed by exact | % queries with a different removed-edge set |
|---|---|---|---|---|---|
| bright | 57 | 3.952 | 3.070 | 22.3% | 89.5% |
| fiqa | 155 | 6.368 | 4.508 | 29.2% | 89.7% |
| hotpotqa | 34 | 1.795 | 1.554 | 13.4% | 52.9% |
| scidocs | 133 | 8.194 | 6.136 | 25.1% | 94.0% |

fiqa and scidocs (the two largest, densest candidate graphs, n=20) show the largest gap;
hotpotqa (smallest graphs, n=10) shows the smallest gap. `ms2` queries are never cyclic in
this data (0% across all datasets), so the greedy/exact distinction is moot there; `ms1`
carries essentially all of the cyclic mass, with `ms1_drop_mutual` intermediate.
Full breakdown: `tables/structural_summary_by_dataset_regime.csv`.

## Retrieval-metric detail (pooled across all 1,025 queries)

See `tables/retrieval_metric_paired_summary_pooled.csv` for the full table (35 rows: 7
repaired-graph-dependent methods × 5 metrics). Every `mean_delta` (exact-ILP minus
greedy) is within ±0.0022 in absolute metric units, and signs are inconsistent across
methods/metrics (some positive, some negative) — i.e. noise, not a systematic effect.
Helped/harmed query counts are close to balanced for every cell (e.g. Copeland nDCG@10:
26 helped / 39 harmed / 960 unchanged out of 1,025).

## Solver verification (Phase 1 / Phase 3)

- **Solver:** PySCIPOpt 6.2.1 (SCIP), open-source, installed locally into the existing
  `.venv` (`pip install pyscipopt`; no global/system package changes; network access to
  PyPI confirmed available). This was preference-order option **A** (top choice) and
  succeeded, so options B/C/D (HiGHS via `scipy.optimize.milp`, CBC, GLPK) were not
  needed — though `scipy.optimize.milp` (HiGHS-backed) was confirmed available too as a
  fallback (scipy 1.18.0 pre-installed).
- **Formulation:** the exact same linear-ordering MIP as the pre-existing (Gurobi-only,
  unusable) `src/consistency_ranker/mwfas_solver.py::_solve_ilp` — `n*(n-1)` binary
  "before" variables, antisymmetry + transitivity constraints, minimize removed edge
  weight — ported unchanged in structure to SCIP in a new, separate module
  (`scripts/exact_ilp_scip.py`). `mwfas_solver.py` itself was **not modified**.
  `limits/gap = 0.0` was used (SCIP must prove exact optimality, not just a small gap),
  with a 300s per-query time-limit safety net that was never approached.
- **Independent cross-check (Phase 3):** the SCIP port's objective value was verified
  against the pre-existing brute-force `exact_fas.py` (a completely independent exact
  method: exhaustive `n!` permutation search) on 34 random synthetic cyclic graphs
  (n∈{4,6,8,10}, 3 edge densities × 3 seeds) **and** 15 real hotpotqa n=10 preference
  graphs from the canonical package. **All 49 cases matched exactly** (`tables/scip_vs_bruteforce_validation.json`),
  and SCIP reported proven-optimal status in every case.
- **Full-study solver statistics:** all 1,025 canonical queries returned `status ==
  "optimal"` (proven optimality; zero timeouts, zero gap-limited results). Solve times:
  mean 7.4ms, median 0.25ms, max 236ms (the largest graphs, n=20, bright/fiqa/scidocs
  ms1). No query anywhere near the 300s safety-net time limit.

## What was held fixed (per task scope)

Everything except the repair back-end was inherited, unmodified, from
`reports/full_calibrated_core/scripts/full_calibration_utils.py`: candidate pools,
per-query/per-ranker min-max calibration, raw-reference retention-matched vote
thresholds, graph construction, and every downstream ranking method / metric
implementation. The only code difference between the "greedy" and "ilp_scip" evaluation
runs in this study is which function computes the repaired DAG
(`ScipIlpCalibrationEvaluator._apply_repair` in
`scripts/run_exact_open_ilp_study.py` calls `exact_ilp_scip.solve_ilp_scip` instead of
`greedy_fas`). No manuscript file, canonical output, candidate-pooling logic, retention
policy, calibration variant, or taxonomy/LLM-evidence artifact was read for scoring
purposes or modified.

## Outputs

- `tables/structural_per_query.csv` — per-query structural comparison (edges/weight
  removed, proven-optimality, whether the removed-edge sets are identical).
- `tables/structural_summary_greedy_vs_ilp.csv`, `structural_summary_by_dataset_regime.csv`
  — aggregated structural summaries, computed with the **unmodified** canonical
  `full_calibration_utils.summarize_structural_records` function.
- `tables/ilp_solver_status_per_query.csv` — solver diagnostics per query (status, gap,
  time, variable/constraint counts).
- `tables/retrieval_metric_paired_per_query.csv` — per-query nDCG@{5,10,20}/MRR/MAP for
  greedy vs. exact-ILP, per repaired-graph-dependent method.
- `tables/retrieval_metric_paired_summary.csv` (per dataset/regime) and
  `retrieval_metric_paired_summary_pooled.csv` (pooled) — bootstrap CIs, paired
  permutation p-values, Holm/BH-adjusted p-values.
- `tables/scip_vs_bruteforce_validation.json` — Phase 3 independent-method cross-check.
- `manifests/study_summary.json` — top-line counts (1,025 queries; 692 same removed-edge
  set / 333 different; 333 queries with strictly lower ILP weight removed; 0 not-proven-optimal).
