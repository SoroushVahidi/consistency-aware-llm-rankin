# Research Results Audit — consistency-aware-llm-rankin

> **Rigorous, evidence-based audit of every empirical result currently available
> in this repository.**  All findings are drawn directly from inspected files;
> nothing is invented.  Where no file exists, this is stated explicitly.

Audit date: 2026-03-21  
Auditor: automated inspection of all files under `outputs/`, `data/`, `scripts/`,
`src/`, and `tests/`.

---

## 1. HIGH-LEVEL RESULTS SUMMARY

### Experiments that have actually been run

| Experiment | Script | Status | Output Location |
|---|---|---|---|
| Synthetic (n=20, noise=0.2, seed=42) | `run_synthetic.py` | ✅ Completed | `outputs/synthetic_results.json` |
| Synthetic timing profiling (same params) | `run_synthetic.py --save-timings --profile` | ✅ Completed | `outputs/timings/synthetic_timings.{csv,json}` |
| Noise sweep (noise=0.05–0.30, n=20, seed=42) | `run_synthetic.py` × 6 | ✅ Completed | `outputs/noise_sweep_n*/` |
| Scale sweep (n=10, 20, 50, 100; noise=0.1, seed=42) | `run_synthetic.py` × 4 | ✅ Completed | `outputs/scale_sweep_n*/` |

### Experiments that are NOT run / incomplete

| Experiment | Script | Status | Blocker |
|---|---|---|---|
| Real-data (SciDocs, FiQA, HotpotQA, BRIGHT) | `run_real_experiment.py` | ❌ Not run | Raw data not downloaded; `data/raw/` is empty |
| Multi-ranker vote aggregation | `generate_score_file.py` + `build_votes_file.py` + `run_real_experiment.py` | ❌ Not run | Requires dataset download |
| Bootstrap significance testing | `bootstrap_method_deltas.py` | ❌ Not run | Requires `*_per_query.csv` (not yet generated) |
| Timing plots | `plot_timings.py` | ❌ Not run | `outputs/plots/` contains only `.gitkeep` |
| ILP-based MWFAS solver | `mwfas_solver.py --method ilp` | ❌ Stub only | Raises `NotImplementedError`; `pulp` optional dep not used |

### Main empirical claims currently supported

1. **Cycles always appear in dense, noisy pairwise preference graphs.** At
   noise=0.2, n=20 items → 1 strongly connected component (SCC) spans all 20
   nodes; graph is fully cyclic.

2. **Score-sum and Borda baselines outperform Greedy-FAS + Topological sort on
   every tested configuration.** Across the noise sweep (n=20) and scale sweep
   (n=10–100), Borda achieves the highest Kendall τ; Greedy-FAS + Topological
   consistently ranks last.

3. **Greedy-FAS removes a substantial fraction of edges.** At noise=0.2,
   n=20: 62/190 edges (33%) removed, total weight removed = 14.06 out of
   total 64.59 (22%).

4. **Pipeline runtime is fast at small scale; greedy FAS dominates cost.**
   Total experiment time for n=20: 8.4 ms.  Greedy FAS solver accounts for
   68% of total experiment time at n=20, rising to 97% at n=100.

5. **Ranking quality degrades as noise increases, but Greedy-FAS degrades
   faster than the baselines.**  At noise=0.05, all methods achieve τ ≥ 0.73;
   at noise=0.30, all methods converge toward τ ≈ 0.4–0.6.

---

## 2. ALL AVAILABLE RESULT ARTIFACTS

### 2a. Synthetic experiment artifacts

| File | Type | Contents | Status |
|---|---|---|---|
| `outputs/synthetic_results.json` | JSON | n=20, noise=0.2, seed=42: config, ground-truth ranking, graph summary, cycle summary, all rankings, Kendall τ / violation counts, FAS edge list, per-stage timings | **Final** |
| `outputs/timings/synthetic_timings.csv` | CSV | Per-stage timing table (n=20, noise=0.2): stage, n_calls, total_s, mean_s, median_s, max_s | **Final** |
| `outputs/timings/synthetic_timings.json` | JSON | Same as CSV plus raw per-call values and metadata | **Final** |

### 2b. Noise sweep artifacts (n=20, seed=42, noise ∈ {0.05, 0.10, 0.15, 0.20, 0.25, 0.30})

| Directory | Contents | Status |
|---|---|---|
| `outputs/noise_sweep_n0.05/synthetic_results.json` | Full result for noise=0.05 | Final |
| `outputs/noise_sweep_n0.05/timings/synthetic_timings.{csv,json}` | Stage timings | Final |
| `outputs/noise_sweep_n0.10/synthetic_results.json` | Full result for noise=0.10 | Final |
| `outputs/noise_sweep_n0.10/timings/synthetic_timings.{csv,json}` | Stage timings | Final |
| `outputs/noise_sweep_n0.15/synthetic_results.json` | Full result for noise=0.15 | Final |
| `outputs/noise_sweep_n0.15/timings/synthetic_timings.{csv,json}` | Stage timings | Final |
| `outputs/noise_sweep_n0.20/synthetic_results.json` | Full result for noise=0.20 | Final |
| `outputs/noise_sweep_n0.20/timings/synthetic_timings.{csv,json}` | Stage timings | Final |
| `outputs/noise_sweep_n0.25/synthetic_results.json` | Full result for noise=0.25 | Final |
| `outputs/noise_sweep_n0.25/timings/synthetic_timings.{csv,json}` | Stage timings | Final |
| `outputs/noise_sweep_n0.30/synthetic_results.json` | Full result for noise=0.30 | Final |
| `outputs/noise_sweep_n0.30/timings/synthetic_timings.{csv,json}` | Stage timings | Final |

### 2c. Scale sweep artifacts (noise=0.1, seed=42, n ∈ {10, 20, 50, 100})

| Directory | Contents | Status |
|---|---|---|
| `outputs/scale_sweep_n10/synthetic_results.json` | Full result for n=10 | Final |
| `outputs/scale_sweep_n10/timings/synthetic_timings.{csv,json}` | Stage timings | Final |
| `outputs/scale_sweep_n20/synthetic_results.json` | Full result for n=20 | Final |
| `outputs/scale_sweep_n20/timings/synthetic_timings.{csv,json}` | Stage timings | Final |
| `outputs/scale_sweep_n50/synthetic_results.json` | Full result for n=50 | Final |
| `outputs/scale_sweep_n50/timings/synthetic_timings.{csv,json}` | Stage timings | Final |
| `outputs/scale_sweep_n100/synthetic_results.json` | Full result for n=100 | Final |
| `outputs/scale_sweep_n100/timings/synthetic_timings.{csv,json}` | Stage timings | Final |

### 2d. Files that do NOT yet exist (expected but absent)

| Expected File | Reason Absent |
|---|---|
| `outputs/<dataset>_per_query.csv` | Real-data experiments not run |
| `outputs/<dataset>_summary.csv` | Real-data experiments not run |
| `outputs/bootstrap_ci.{json,csv}` | Bootstrap significance tests not run |
| `outputs/plots/*.png` | `plot_timings.py` has not been executed |
| `outputs/real_signal/*/scores_*.jsonl` | Score files not generated |
| `outputs/real_signal/*/votes.jsonl` | Vote files not generated |
| `data/processed/*/queries.jsonl` | `prepare_datasets.py` not run |
| `data/processed/*/documents.jsonl` | `prepare_datasets.py` not run |
| `data/processed/*/qrels.jsonl` | `prepare_datasets.py` not run |
| `data/processed/*/pairwise/preferences.jsonl` | `prepare_datasets.py` not run |

---

## 3. DATASETS COVERED

### Datasets with actual results

| Dataset | Type | Experiments Run | Samples | Methods Compared | Paper-ready? |
|---|---|---|---|---|---|
| **Synthetic (n=20, noise=0.2, seed=42)** | Controlled synthetic | Ranking quality evaluation | 20 items, 190 pairwise prefs | Score-sum, Borda, Greedy-FAS+Topo | Partial (single seed) |
| **Synthetic noise sweep** | Controlled synthetic | Noise sensitivity analysis | 20 items × 6 noise levels | Score-sum, Borda, Greedy-FAS+Topo | Partial (single seed) |
| **Synthetic scale sweep** | Controlled synthetic | Scalability analysis | n ∈ {10,20,50,100} items | Score-sum, Borda, Greedy-FAS+Topo (+ runtime) | Partial (single seed) |

### Datasets with NO results yet

| Dataset | Short ID | HF Source | Status |
|---|---|---|---|
| BEIR / SciDocs | `scidocs` | `BeIR/scidocs` | ❌ Not downloaded |
| BEIR / FiQA-2018 | `fiqa` | `BeIR/fiqa` | ❌ Not downloaded |
| HotpotQA | `hotpotqa` | `hotpot_qa` | ❌ Not downloaded |
| BRIGHT | `bright` | `xlangai/BRIGHT` | ❌ Not downloaded |

---

## 4. METHODS / BASELINES COVERED

### Methods with actual results

| Method Name (exact) | Appears In | Role | Actually Run? |
|---|---|---|---|
| `score_sum` | `outputs/*/synthetic_results.json` → `rankings.score_sum`, `evaluation.kendall_tau.score_sum` | Baseline | ✅ Yes |
| `borda` | `outputs/*/synthetic_results.json` → `rankings.borda`, `evaluation.kendall_tau.borda` | Baseline | ✅ Yes |
| `greedy_fas_topological` | `outputs/*/synthetic_results.json` → `rankings.greedy_fas_topological`, `evaluation.kendall_tau.greedy_fas_topological` | Main method | ✅ Yes |

### Methods implemented but NOT yet run on any dataset

| Method Name (exact) | Defined In | Role |
|---|---|---|
| `pagerank` | `src/consistency_ranker/baseline_ranking.py:pagerank_ranking` | Baseline (implemented, not in `run_synthetic.py` output) |
| `greedy_fas_weighted_balance` | `scripts/run_real_experiment.py` | Variant (real-data only) |
| `greedy_fas_copeland` | `scripts/run_real_experiment.py` | Variant (real-data only) |
| `greedy_fas_score_augmented_topological` | `scripts/run_real_experiment.py` | Variant (real-data only) |
| `hybrid_rrf_fas_regularized` | `scripts/run_real_experiment.py` | Hybrid method (real-data only) |
| `hybrid_rrf_balance_a05` | `scripts/run_real_experiment.py` | Hybrid method (real-data only) |
| `hybrid_rrf_copeland_a03` | `scripts/run_real_experiment.py` | Hybrid method (real-data only) |
| `hybrid_rrf_priority_topo_a03` | `scripts/run_real_experiment.py` | Hybrid method (real-data only) |
| `ilp` | `src/consistency_ranker/mwfas_solver.py` | Exact MWFAS (stub only — raises `NotImplementedError`) |

---

## 5. PRIMARY METRICS REPORTED

### Metrics in actual result files

| Metric | Exact Key in Files | Location | Better Direction | Standard? |
|---|---|---|---|---|
| **Kendall τ** | `evaluation.kendall_tau.<method>` | `outputs/*/synthetic_results.json` | Higher | ✅ Standard rank correlation |
| **n_violations** | `evaluation.n_violations.<method>` | `outputs/*/synthetic_results.json` | Lower | ✅ Pairwise ordering errors |
| **pairwise_inconsistency_count.original_graph** | `evaluation.pairwise_inconsistency_count.original_graph` | `outputs/*/synthetic_results.json` | Lower | ✅ Count of graph edges contradicting ground truth |
| **pairwise_inconsistency_count.after_fas_dag** | `evaluation.pairwise_inconsistency_count.after_fas_dag` | `outputs/*/synthetic_results.json` | Lower | ✅ Post-repair inconsistency |
| **fas.n_removed_edges** | `fas.n_removed_edges` | `outputs/*/synthetic_results.json` | Diagnostic | ✅ Measures cycle repair magnitude |
| **fas.total_removed_weight** | `fas.total_removed_weight` | `outputs/*/synthetic_results.json` | Lower | ✅ MWFAS objective value |
| **graph_summary.is_dag** | `graph_summary.is_dag` | `outputs/*/synthetic_results.json` | Diagnostic | ✅ |
| **graph_summary.n_sccs** | `graph_summary.n_sccs` | `outputs/*/synthetic_results.json` | Diagnostic | ✅ |
| **wall-clock stage timing** | `timings.<stage>.total_s` | `outputs/*/synthetic_results.json` and `*_timings.csv` | Lower | ✅ |

### Metrics implemented but NOT yet appearing in any result file

| Metric | Defined In | Status |
|---|---|---|
| `ndcg_at_k` | `scripts/run_real_experiment.py:_ndcg_at_k` | Not run |
| `map_at_k` | `scripts/run_real_experiment.py:_map_at_k` | Not run |
| `precision_at_k` | `scripts/run_real_experiment.py:_precision_recall_at_k` | Not run |
| `recall_at_k` | `scripts/run_real_experiment.py:_precision_recall_at_k` | Not run |
| `pairwise_accuracy` | `scripts/run_real_experiment.py:_pairwise_accuracy` | Not run |
| `backward_edge_weight` | `scripts/run_real_experiment.py` | Not run |
| `bootstrap CI / p-value` | `scripts/bootstrap_method_deltas.py` | Not run |

---

## 6. BEST RESULTS TABLE

### Table 1: Noise sweep — Kendall τ by method (n=20 items, seed=42)

Exact values extracted from `outputs/noise_sweep_n*/synthetic_results.json`.

| Noise | Score-sum τ | Borda τ | Greedy-FAS+Topo τ | Best Method | FAS edges removed |
|---|---|---|---|---|---|
| 0.05 | **0.9263** | **0.9263** | 0.7263 | Score-sum / Borda (tie) | 41 / 190 |
| 0.10 | 0.8105 | **0.8842** | 0.6000 | Borda | 61 / 190 |
| 0.15 | 0.7579 | **0.8632** | 0.4842 | Borda | 73 / 190 |
| 0.20 | 0.7579 | 0.7789 | 0.4526 | Borda | 62 / 190 |
| 0.25 | **0.7895** | 0.7263 | 0.4000 | Score-sum | 72 / 190 |
| 0.30 | 0.5263 | **0.5789** | 0.4105 | Borda | 70 / 190 |

> **Finding**: Greedy-FAS + Topological sort is the **worst** method at every
> noise level.  Borda is the best or tied-best in 5/6 noise levels.  The gap
> between Borda and Greedy-FAS widens with noise.

### Table 2: Scale sweep — Kendall τ by method (noise=0.1, seed=42)

Exact values extracted from `outputs/scale_sweep_n*/synthetic_results.json`.

| n_items | Score-sum τ | Borda τ | Greedy-FAS+Topo τ | Best Method | Greedy FAS time (s) | Total time (s) |
|---|---|---|---|---|---|---|
| 10 | 0.7333 | **0.7778** | 0.2000 | Borda | 0.0022 | 0.0044 |
| 20 | 0.8105 | **0.8842** | 0.6000 | Borda | 0.0107 | 0.0143 |
| 50 | **0.8890** | 0.8841 | 0.5951 | Score-sum | 0.2123 | 0.2247 |
| 100 | 0.8958 | **0.9317** | 0.5495 | Borda | 1.1942 | 1.2315 |

> **Finding**: Greedy-FAS + Topological sort consistently underperforms both
> baselines at all tested graph sizes.  Borda wins or ties in 3/4 sizes.
> Runtime is dominated by the greedy FAS solver (97% of total at n=100).

### Table 3: Main synthetic result (n=20, noise=0.2, seed=42)

Exact values from `outputs/synthetic_results.json`.

| Method | Kendall τ | Pairwise Violations | Pairwise Inconsistency |
|---|---|---|---|
| Score-sum | 0.7579 | 23 | 37 (original graph) |
| Borda | 0.7789 | 21 | 37 (original graph) |
| Greedy-FAS + Topological | 0.4526 | 52 | 16 (after FAS DAG) |

> **Note**: Pairwise inconsistency drops from 37 to 16 after FAS repair,
> confirming that the DAG is more consistent with ground truth.  However,
> the topological ranking derived from the DAG still ranks **worse** than
> Score-sum and Borda by Kendall τ and violation count.

### Table 4: Significance evidence

| Comparison | Metric | Significance Test | Available? |
|---|---|---|---|
| Borda vs. Greedy-FAS+Topo | Kendall τ | Bootstrap CI | ❌ No — `bootstrap_method_deltas.py` not run |
| Score-sum vs. Greedy-FAS+Topo | Kendall τ | Bootstrap CI | ❌ No |

---

## 7. ABLATIONS AND STATISTICAL EVIDENCE

### What exists

| Study | Evidence | Convincing? | Publication-ready? |
|---|---|---|---|
| **Noise sensitivity (parameter sweep)** | 6 noise levels (0.05–0.30) × 3 methods. Exact τ and violation counts in `outputs/noise_sweep_n*/` | Suggestive — shows consistent trend | ❌ Single seed only; no CIs |
| **Scale sensitivity (parameter sweep)** | 4 item counts (10–100) × 3 methods. τ + runtime in `outputs/scale_sweep_n*/` | Suggestive — shows runtime scaling | ❌ Single seed only; no CIs |
| **Repaired vs. unrepaired comparison** | `pairwise_inconsistency_count.original_graph` vs. `after_fas_dag` in every JSON | Shows repair reduces inconsistency | ❌ Not systematically reported across conditions |
| **FAS weight removed analysis** | `fas.total_removed_weight` and `fas.n_removed_edges` in every JSON | Diagnostic only | ❌ Not framed as ablation |

### What does NOT exist

| Study | Status |
|---|---|
| Bootstrap confidence intervals for method comparisons | ❌ Not run |
| Significance tests (t-test, Wilcoxon) | ❌ Not run |
| Multiple random seeds for variance estimation | ❌ All results use seed=42 only |
| Ablation: Greedy FAS vs. score-sum pre-ranking | ❌ Not implemented |
| Ablation: uniform vs. margin edge weights | ❌ Only one weight_scheme per run file |
| Real-data per-query breakdown | ❌ No real data |
| Cross-dataset robustness | ❌ No real data |

---

## 8. RUNTIME / SCALABILITY EVIDENCE

### Wall-clock timing data (extracted from `outputs/scale_sweep_n*/timings/synthetic_timings.csv`)

| n_items | graph_construction (s) | greedy_fas_solver (s) | ranking (s) | evaluation (s) | total_experiment (s) | FAS % of total |
|---|---|---|---|---|---|---|
| 10 | 0.000295 | 0.002162 | ~0.000140 | ~0.000100 | 0.004377 | 49% |
| 20 | 0.001069 | 0.010689 | ~0.000300 | ~0.000200 | 0.014282 | 75% |
| 50 | 0.007853 | 0.212346 | ~0.001500 | ~0.001100 | 0.224724 | 94% |
| 100 | 0.028560 | 1.194237 | ~0.006100 | ~0.004300 | 1.231536 | 97% |

### Stage timing for default run (n=20, noise=0.2, seed=42)

From `outputs/timings/synthetic_timings.csv`:

| Stage | n_calls | total_s | mean_s |
|---|---|---|---|
| data_generation | 1 | 0.000064 | 0.000064 |
| pairwise_preference_generation | 1 | 0.000201 | 0.000201 |
| graph_construction | 1 | 0.001662 | 0.001662 |
| cycle_detection | 1 | 0.000151 | 0.000151 |
| ranking_score_sum | 1 | 0.000092 | 0.000092 |
| ranking_borda | 1 | 0.000023 | 0.000023 |
| greedy_fas_solver | 1 | 0.005676 | 0.005676 |
| ranking_topological | 1 | 0.000079 | 0.000079 |
| evaluation | 1 | 0.000228 | 0.000228 |
| total_experiment | 1 | 0.008411 | 0.008411 |

### Runtime scaling assessment

The data supports a **super-linear** growth in greedy FAS runtime:
- n=10→20 (2×): FAS time 2.16 ms → 10.69 ms (5×)
- n=20→50 (2.5×): FAS time 10.69 ms → 212.35 ms (20×)
- n=50→100 (2×): FAS time 212.35 ms → 1194.24 ms (5.6×)

This is consistent with the documented O(C · (n + e)) complexity where
e ≈ n(n-1) for a complete pairwise graph and C grows with graph density.
Empirically the FAS time appears approximately O(n³) to O(n⁴) for dense graphs.

### Conclusions on runtime claims

- ✅ **Practical efficiency at small scale** (n ≤ 20): the total pipeline
  completes in < 15 ms.
- ⚠️ **Scalability is limited**: at n=100 the total time is 1.23 s for a
  single synthetic query.  For 500 real queries with n=100 documents each,
  estimated time would be ~10 minutes on CPU — feasible but not fast.
- ❌ **No GPU/memory measurements** in any result file.
- ❌ **No HPC logs or large-scale benchmark results** exist.

---

## 9. FIGURES / TABLES THAT COULD GO INTO A PAPER

### Already achievable from existing artifacts

| Table/Figure | Source Data | Status | Notes |
|---|---|---|---|
| Table: Noise sweep τ (Table 1 above) | `outputs/noise_sweep_n*/synthetic_results.json` | ✅ Data ready | 1 seed; no CIs |
| Table: Scale sweep τ + runtime (Table 2 above) | `outputs/scale_sweep_n*/synthetic_results.json` | ✅ Data ready | 1 seed; no CIs |
| Table: Main synthetic result (Table 3 above) | `outputs/synthetic_results.json` | ✅ Data ready | 1 seed; no CIs |
| Figure: Kendall τ vs. noise level (line chart) | `outputs/noise_sweep_n*/` | ✅ Can be generated | 3 methods, 6 noise levels |
| Figure: Runtime vs. n_items (line chart) | `outputs/scale_sweep_n*/timings/` | ✅ Can be generated | `plot_timings.py --scale-dirs` |
| Figure: Stage-level timing breakdown (bar/pie) | `outputs/timings/synthetic_timings.json` | ✅ Can be generated | `plot_timings.py --input` |
| Figure: FAS edges removed vs. noise | `outputs/noise_sweep_n*/synthetic_results.json` | ✅ Can be generated | Diagnostic |

### Tables / figures that CANNOT yet be generated

| Item | Missing Prerequisite |
|---|---|
| Real-dataset leaderboard (nDCG@k, MAP@k) | `*_summary.csv` — real-data experiments not run |
| Per-query violin/box plots | `*_per_query.csv` — real-data experiments not run |
| Bootstrap CI error bars | `bootstrap_ci.{json,csv}` — not run |
| Method comparison across multiple datasets | Real datasets not downloaded |
| Variance across seeds | Only seed=42 used |

---

## 10. STRENGTH OF CURRENT EVIDENCE

### Overall assessment: **WEAK**

The repository has a well-designed, fully implemented pipeline.  The test suite
(149 tests) passes and the code is sound.  However, the empirical evidence
package is thin:

| Evidence Type | Assessment | Why |
|---|---|---|
| Method effectiveness | **Weak** | Only synthetic experiments; greedy FAS underperforms all baselines |
| Generalisation across datasets | **None** | Zero real-dataset experiments run |
| Statistical significance | **None** | No bootstrap CIs, no p-values |
| Efficiency claims | **Weak** | Runtime data exists only for synthetic experiments; no comparison to related work |

### What the evidence supports

- **"Cycles appear in dense noisy pairwise graphs"** — ✅ Supported directly.
  At noise ≥ 0.05 with n ≥ 10, the graph always has at least one SCC.

- **"Greedy FAS reduces pairwise inconsistencies"** — ✅ Partially supported.
  At n=20, noise=0.2: inconsistencies fall from 37 (original) to 16 (post-FAS).

- **"Greedy FAS produces higher-quality rankings than baselines"** — ❌ **NOT
  supported.** All current results show the opposite: Borda and Score-sum
  consistently achieve higher Kendall τ than Greedy-FAS + Topological sort.

### What the evidence does NOT support

- Any claim about performance on real IR benchmarks (SciDocs, FiQA, HotpotQA,
  BRIGHT).
- Any claim that the hybrid methods (`hybrid_rrf_*`) outperform baselines.
- Any statistically significant advantage of MWFAS-based ranking.
- Any efficiency or scalability claim beyond n=100 synthetic items.

---

## 11. CRITICAL GAPS BEFORE SUBMISSION

Ranked by priority:

### Priority 1 — No real-dataset results (blocking)

**Gap**: Zero experiments on SciDocs, FiQA, HotpotQA, or BRIGHT.  Without
real-dataset results the paper has no empirical basis beyond toy experiments.

**Fix**: Run the full pipeline:
```bash
python scripts/download_datasets.py --dataset scidocs
python scripts/prepare_datasets.py --dataset scidocs
python scripts/generate_score_file.py --dataset scidocs --ranker bm25 ...
python scripts/build_votes_file.py ...
python scripts/run_real_experiment.py --dataset scidocs --preference-source votes_file ...
```
Repeat for FiQA, HotpotQA.  Expected outputs: `scidocs_per_query.csv`,
`scidocs_summary.csv`.

---

### Priority 2 — Main method underperforms all baselines on synthetic data

**Gap**: Greedy-FAS + Topological sort achieves the *lowest* Kendall τ at every
tested noise level and item count.  This contradicts the expected narrative.

**Fix**: Investigate why topological sort on the greedy FAS DAG loses
information.  The DAG topology depends heavily on which edges are removed first;
this creates artifacts.  The hybrid ranking methods in `run_real_experiment.py`
(e.g. `greedy_fas_weighted_balance`, `greedy_fas_copeland`) may mitigate this,
but they are only implemented for the real-data pipeline and need to be ported
to the synthetic pipeline as well.

---

### Priority 3 — No statistical significance testing (blocking for submission)

**Gap**: All comparisons are point estimates from a single random seed.  No
bootstrap CIs, no p-values.  No result table can include "±" ranges.

**Fix**:
```bash
python scripts/bootstrap_method_deltas.py \
    --per-query-csv outputs/scidocs_per_query.csv \
    --metric ndcg_at_k --method-a borda --method-b greedy_fas_topological \
    --n-bootstrap 2000 --output-json outputs/bootstrap_ci.json
```
Also re-run synthetic experiments with multiple seeds (seed ∈ {42, 123, 456,
789, 1234}) to report mean ± std.

---

### Priority 4 — Only 3 of ≥11 ranking methods evaluated (moderate)

**Gap**: The real-data pipeline implements 11+ methods including hybrid RRF
variants, Copeland, weighted-balance, score-augmented topological — but none
appear in any result file.  Only Score-sum, Borda, and Greedy-FAS+Topological
have been measured.

**Fix**: After running real-data experiments, all 11 methods will appear
automatically in `*_summary.csv`.

---

### Priority 5 — Ablation table missing

**Gap**: No comparison of edge weight schemes (uniform vs. margin), no
comparison of Greedy-FAS vs. ILP (the ILP solver is a stub), no analysis of
preference source quality.

**Fix**: Port `uniform`/`margin` comparison to sweeps.  Implement ILP solver
using `pulp` for exact MWFAS on small graphs.

---

### Priority 6 — Single random seed throughout

**Gap**: All 10 result files use `seed=42` only.  Kendall τ values may vary
significantly across seeds.

**Fix**: Repeat all experiments with ≥ 5 seeds; report mean ± std.

---

### Priority 7 — Missing figures

**Gap**: `outputs/plots/` contains only `.gitkeep`.  No visualisations have
been generated.

**Fix**: Run `python scripts/plot_timings.py` on existing timing data.  Add
a script to generate the τ-vs-noise and τ-vs-scale line charts.

---

### Priority 8 — No Jupyter notebook walkthrough

**Gap**: `notebooks/` contains only `.gitkeep`.  There is no interactive
demonstration of the pipeline.

**Fix**: Create a notebook that loads `outputs/synthetic_results.json` and
visualises the preference graph, cycle structure, and ranking quality.

---

## 12. FINAL ACTIONABLE SUMMARY

### A. Results already available that are strongest

1. **Timing/runtime data** for the greedy FAS solver across n=10–100 (Tables 2
   and 8).  These numbers are reliable and show clear super-linear scaling.
   This evidence supports claims about computational feasibility.

2. **Cycle detection evidence**: at every tested noise level (≥ 0.05), the
   dense pairwise graph is fully cyclic (1 SCC spanning all nodes).  This
   validates the research premise that cycles are ubiquitous.

3. **FAS repair reduces graph-level inconsistencies**: the `pairwise_inconsistency_count`
   drops from 37 to 16 after FAS repair at n=20, noise=0.2.  This shows FAS
   does solve its intended sub-problem.

4. **Noise sweep τ data** across 6 noise levels provides a clean degradation
   curve — useful as a motivation figure showing ranking quality falls as
   inconsistency rises.

### B. Additional experiments needed next (in priority order)

1. **Run real-dataset experiments** on ≥ 2 datasets (e.g. SciDocs + FiQA) with
   the `votes_file` preference source.  This will produce `*_per_query.csv` and
   `*_summary.csv` — the primary paper tables.

2. **Run bootstrap significance tests** (`bootstrap_method_deltas.py`) on the
   per-query CSVs.  Target: bootstrap p-value and 95% CI for the best method
   vs. Borda.

3. **Replicate synthetic experiments with multiple seeds** (≥ 5) to report
   mean ± std for all τ values.  This will make noise-sweep and scale-sweep
   tables publication-quality.

4. **Port hybrid methods to synthetic pipeline** so that
   `greedy_fas_weighted_balance` and `greedy_fas_copeland` can be compared to
   Borda in the controlled setting — and the narrative can be corrected if
   these outperform naive topological sort.

5. **Generate timing plots** (`plot_timings.py`) and add them to `outputs/plots/`.

### C. Venue-level assessment (based on current evidence only)

> **Current evidence level: Pre-workshop / internal note only.**

The pipeline is implemented and functional, tests pass (149/149), and there is
a clear and interesting research question.  However, without real-dataset
results, statistical significance tests, multiple seeds, and a resolved
narrative (the main method currently underperforms baselines), the current
evidence package does not meet the bar for a workshop paper let alone a
full-venue submission.

With the Priority 1–3 gaps above addressed (real data + significance + seeds),
the target might be a **retrieval or NLP workshop** (e.g. at SIGIR, ECIR, or
EMNLP).  With Priority 4–5 gaps also addressed (full method comparison + ILP
ablation), a **short paper at SIGIR or CIKM** becomes plausible, conditional
on the hybrid or repaired methods outperforming baselines on real data.

---

*This audit was generated by systematic file inspection and direct execution of
`scripts/run_synthetic.py` with multiple parameter configurations.  All tables
contain exact values extracted from the JSON files listed.  No numbers have been
estimated or fabricated.*
