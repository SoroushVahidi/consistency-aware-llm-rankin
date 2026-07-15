# Final Revision Task 1: Pool Size vs. Cutoff Audit

## 1. Initial repository state

- Repository: `consistency-aware-llm-rankin`
- Branch at start: `main`
- HEAD at start: `b0d48520b72dfa05f6cfe07309cb39ef980be032`
- `git fetch origin` executed before changes.
- Working tree at task start: clean
- Canonical manuscript source: `papers/JDIQ_2026/manuscript/main.tex`
- Canonical manuscript PDF at start: `papers/JDIQ_2026/manuscript/main.pdf`
- Initial manuscript PDF SHA-256:
  `7c0213620d6f259964dae17af1d3041b850e8d1984710569caa6a6d5887c6083`
- Canonical rerun manifest:
  `experiments/method_improvement_audit_20260711_205733/phase_reports/canonical_rerun_manifest.json`
- Final anonymous submission package identified and preserved:
  `papers/JDIQ_2026/submission/final_anonymous/`
  `papers/JDIQ_2026/submission/final_anonymous.zip`

## 2. Stored-depth feasibility by dataset and ranker

Direct file audit outputs:

- `tables/score_depth_by_ranker.csv`
- `tables/score_depth_union_overlap.csv`
- `tables/feasible_config_grid.csv`
- `manifests/feasibility.json`

Verified common complete stored depths on usable queries:

- SciDocs: 120 usable queries; common complete depth `50`
- FiQA: 120 usable queries; common complete depth `50`
- HotpotQA: 52 usable queries; common complete depth `35`
- BRIGHT: 50 usable queries; common complete depth `50`

Stored-depth conclusions:

- The manuscript-stated upstream depths were confirmed from the stored score files:
  SciDocs `50`, FiQA `50`, HotpotQA `35`, BRIGHT `50`.
- No dataset had a common complete depth at `100` or `200`.
- Mean union sizes increased substantially with depth:
  SciDocs `20 -> 39.84`, `50 -> 96.88`; FiQA `20 -> 45.11`, `50 -> 109.72`;
  HotpotQA `10 -> 18.46`, `35 -> 70.46`; BRIGHT `20 -> 49.38`, `50 -> 124.72`.

## 3. Exact `P/k` configurations run

Primary greedy study, canonical `minmax_raw_matched` protocol:

- SciDocs: `pool20_ndcg5`, `pool20_ndcg10`, `pool20_ndcg20`, `pool50_ndcg5`, `pool50_ndcg10`, `pool50_ndcg20`
- FiQA: `pool20_ndcg5`, `pool20_ndcg10`, `pool20_ndcg20`, `pool50_ndcg5`, `pool50_ndcg10`, `pool50_ndcg20`
- BRIGHT: `pool20_ndcg5`, `pool20_ndcg10`, `pool20_ndcg20`, `pool50_ndcg5`, `pool50_ndcg10`, `pool50_ndcg20`
- HotpotQA: `pool10_ndcg5`, `pool35_ndcg5`, `pool35_ndcg10`, `pool35_ndcg20`

All four datasets were run under:

- `ms2`
- `ms1`
- `ms1_drop_mutual`

This yielded `66` dataset/regime/config cells total.

Targeted exact SCIP study:

- SciDocs `ms1 pool50_ndcg10`
- FiQA `ms1 pool50_ndcg10`
- BRIGHT `ms1 pool50_ndcg10`
- HotpotQA `ms1 pool35_ndcg10`

## 4. tmux sessions, commands, and logs

Greedy rerun:

- Session: `jdiq_pool_cutoff_task1_greedy`
- Pane PID: `3192903`
- Python PID observed: `3192909`
- Launch manifest:
  `manifests/20260714_233052_greedy_launch.json`
- Log:
  `logs/20260714_233052_greedy.log`
- Status: completed successfully
- Summary:
  `manifests/run_summary.json`

Exact SCIP rerun:

- Session: `jdiq_pool_cutoff_task1_exact`
- Pane PID: `3193197`
- Python PID observed: `3193204`
- Launch manifest:
  `manifests/20260714_233158_exact_launch.json`
- Log:
  `logs/20260714_233158_exact.log`
- Status: completed successfully
- Summary:
  `manifests/exact_run_summary.json`

Validation bundle:

- First attempt:
  `jdiq_pool_cutoff_task1_validate`
  log `logs/20260714_235826_validation.log`
  status: exited after full-file `ruff` style debt in a pre-existing core script; superseded by the successful rerun below
- Successful rerun:
  session `jdiq_pool_cutoff_task1_validate`
  pane PID `3199082`
  child PID observed `3199093`
  launch manifest `manifests/20260715_000102_validation_launch.json`
  log `logs/20260715_000102_validation.log`
  status: completed successfully
- Validation command script:
  `run_manifests/run_validation.sh`

## 5. Code changes

Evaluation pipeline:

- `reports/full_calibrated_core/scripts/full_calibration_utils.py`
  - separated candidate-pool size from metric cutoff
  - added `mrr_at_k`
  - added top-`k` comparison diagnostics
  - stored `candidate_pool_size`, `metric_cutoff`, `top_k_prefix`, and pairwise repaired-vs-unrepaired metadata
  - raised clear errors when requested `k` exceeds realized pool size
- `reports/full_calibrated_core/scripts/run_full_calibrated_core.py`
  - threaded `pool_size_override` through dataset loading
  - preserved `top_k_prefix` and `mrr_at_k` in method-level outputs

Task 1 study drivers:

- `scripts/run_pool_cutoff_study.py`
- `scripts/run_pool_cutoff_exact.py`
- `scripts/verify_pool_cutoff_outputs.py`

Task 1 run manifests:

- `run_manifests/run_pool_cutoff_study.sh`
- `run_manifests/run_pool_cutoff_exact.sh`
- `run_manifests/run_validation.sh`

Manuscript:

- `papers/JDIQ_2026/manuscript/main.tex`
  - updated methods to state verified stored depths and the prespecified `P,k` grid
  - separated original small-pool full-order analysis from the new genuine prefix study
  - revised conditional analysis, discussion, limitations, abstract, and conclusion
  - removed obsolete universal claims that top-`k` membership never changes

## 6. Tests added

Added:

- `tests/test_pool_cutoff_evaluation.py`

Covers:

- `P = k`
- `P > k`
- identical top-`k` membership with changed order
- changed top-`k` membership
- changes below `k` that must not affect nDCG@`k`
- changes crossing the `k` boundary
- clear failure when requested cutoff exceeds realized pool
- deterministic behavior
- real data path for `pool_size_override`

## 7. Statistical methods and correction families

Per repaired-vs-unrepaired cell we computed:

- paired query count
- mean and median delta
- population standard deviation
- `q05/q25/q50/q75/q95`
- helped / harmed / unchanged counts
- paired sign-flip permutation p-value
- paired bootstrap CI
- bootstrap fraction of means above zero
- top-influence query and leave-one-out summary

Multiplicity control:

- Primary confirmatory method: Holm
- Descriptive secondary method: BH

Pre-specified nDCG correction families:

- Full family: all `330` greedy nDCG cells
- Active-regime family: `110` greedy `ms1` nDCG cells

Secondary metrics:

- MAP and MRR were computed at every `P,k` cell
- They were treated as descriptive robustness diagnostics, not as the primary confirmatory family

## 8. Complete key results

Primary result tables:

- `tables/pool_cutoff_pair_metrics.csv`
- `tables/pool_cutoff_method_metrics.csv`
- `tables/pool_cutoff_statistics.csv`
- `tables/pool_cutoff_structural_summary.csv`
- `tables/pool_cutoff_exact_pair_metrics.csv`
- `tables/pool_cutoff_exact_statistics.csv`
- `tables/pool_cutoff_exact_solver_status.csv`

Confirmatory nDCG result:

- `0 / 330` nDCG cells survive Holm in the full family
- `0 / 110` nDCG cells survive Holm in the active `ms1` family

Smallest raw p-value in the active greedy family:

- FiQA `ms1 balance_graph pool50_ndcg20`
  - mean `ΔnDCG = +0.004533`
  - raw `p = 0.003200`
  - Holm active-family `p = 0.351965`

Larger pools changed graph structure materially:

- SciDocs cycle rate `0.369 -> 0.586`, largest SCC `6.37 -> 17.76`
- FiQA cycle rate `0.431 -> 0.547`, largest SCC `6.84 -> 15.39`
- HotpotQA cycle rate `0.218 -> 0.340`, largest SCC `2.06 -> 5.39`
- BRIGHT cycle rate `0.380 -> 0.453`, largest SCC `4.97 -> 9.97`

## 9. Does top-`k` membership change when `P > k`?

Yes.

Aggregate rates from `pool_cutoff_structural_summary.csv`:

- `P = k`: top-`k` membership change rate `0.000000`
- `P > k`: top-`k` membership change rate `0.105776`

High-activity examples under `ms1` Copeland graph:

- SciDocs `pool50_ndcg10`: `0.783333`
- FiQA `pool50_ndcg10`: `0.733333`
- BRIGHT `pool50_ndcg10`: `0.520000`
- HotpotQA `pool35_ndcg10`: `0.365385`

Important nuance:

- `P = k` suppresses visibility of membership changes by construction.
- It does not suppress all nDCG sensitivity: average nDCG-change rate was higher in the `P = k` cells (`0.100852`) than in the `P > k` cells (`0.061126`) because full-order nDCG can move on any differently graded within-pool reorder.

## 10. Does the original retrieval conclusion survive?

Yes, but with a narrower and more accurate statement.

Supported conclusion after the new evidence:

- Repair can change top-`k` membership when `P > k`.
- Larger pools make the graphs more cyclic and increase SCC size.
- Despite that, no repaired-vs-unrepaired nDCG cell is Holm-significant in the full prespecified greedy family, the active `ms1` family, or the targeted exact larger-pool study.

What no longer remains valid as a universal statement:

- “top-`k` membership never changes” across the study

What remains valid:

- The paper does not support a robust positive repaired-vs-unrepaired retrieval gain under the tested data and protocols.

## 11. Direct exact-vs-unrepaired results

Exact SCIP solver summary from `pool_cutoff_exact_solver_status.csv`:

- All prioritized exact larger-pool cells solved to proven optimality
- Maximum gap: `0.0`
- Mean solve times:
  - SciDocs: `0.3284s`
  - FiQA: `0.3045s`
  - BRIGHT: `0.3006s`
  - HotpotQA: `0.0928s`

Exact nDCG result:

- `0` Holm-significant cells in the targeted active-family exact study

Smallest exact raw p-value:

- FiQA `balance_graph pool50_ndcg10`
  - mean `ΔnDCG = +0.004650`
  - raw `p = 0.015798`
  - Holm active-family `p = 0.315968`

## 12. Manuscript changes

Updated in `papers/JDIQ_2026/manuscript/main.tex`:

- Abstract
- Experimental setup table and methods text
- new subsection defining the `P,k` grid before results
- results section distinguishing:
  - original small-pool full-order analysis
  - new larger-pool prefix evaluation
- conditional analysis example replaced with `HotpotQA ms1 Copeland graph (35,10)`
- discussion updated to explain:
  - `P = k` suppresses membership-change visibility
  - `P > k` reveals such changes empirically
  - neither setting yields Holm-robust retrieval improvement
- limitations updated to replace the old “not established here” statement
- conclusion updated to include the larger-pool exact audit

Rebuilt manuscript PDF:

- `papers/JDIQ_2026/manuscript/main.pdf`
- Final SHA-256:
  `44bcb47339d9036fe531884e7e0e4ca4877e4160fc72c4d2e2910fa8d5addaa9`

## 13. Figures now stale, if any

- No figure was regenerated in this task.
- No current figure is factually stale after the text revision, provided the figures are read as part of the original small-pool analysis.
- No mandatory figure regeneration was identified for Task 1.

## 14. Limitations

- Stored common complete depths stop at `50` for SciDocs/FiQA/BRIGHT and `35` for HotpotQA.
- No common complete depth exists at `100` or `200`.
- The study still evaluates reranking over stored candidate sets, not fresh upstream retrieval runs.
- MAP and MRR remain descriptive secondary diagnostics.
- Larger-pool exact solving was only run for the prioritized `ms1` cells, not the entire grid.

## 15. Unresolved failures or incomplete tmux jobs

- No tmux job from this task is still running.
- No incomplete experiment remains.
- One validation tmux attempt (`logs/20260714_235826_validation.log`) stopped at a too-broad `ruff` invocation over legacy style debt in a large pre-existing file; this was resolved by narrowing the lint step to:
  - full `ruff` on the new Task 1 files
  - `ruff --select F,E9` plus `py_compile` on the two large touched core modules

## 16. Exact reproduction commands

Greedy study:

```bash
cd 
./.venv/bin/python reports/final_revision_task1_pool_cutoff_20260715/scripts/run_pool_cutoff_study.py
```

Exact study:

```bash
cd 
./.venv/bin/python reports/final_revision_task1_pool_cutoff_20260715/scripts/run_pool_cutoff_exact.py
```

Task-specific verification:

```bash
cd 
./.venv/bin/python reports/final_revision_task1_pool_cutoff_20260715/scripts/verify_pool_cutoff_outputs.py
```

Full validation:

```bash
cd 
reports/final_revision_task1_pool_cutoff_20260715/run_manifests/run_validation.sh
```

Successful validation log:

- `logs/20260715_000102_validation.log`

Machine-readable validation summaries:

- `validation/pool_cutoff_verification.json`
- `manifests/validation_summary.json`

## 17. Proposed commit message

`Add genuine pool-size vs cutoff evaluation and larger-pool exact audit for JDIQ Task 1`
