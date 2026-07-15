# Final Report: Task 2 Statistical Power and Qrels-Reference Revision

## 1. Initial repository state

- Repository: ``
- `git fetch origin` completed before edits.
- Branch: `main`
- Starting commit: `b0d48520b72dfa05f6cfe07309cb39ef980be032`
- Working tree at audit time was not clean because Task 1 outputs and in-progress manuscript/code edits were already present.
- Task 1 manuscript PDF checksum at audit time:
  - `papers/JDIQ_2026/manuscript/main.pdf`
  - `sha256 = 44bcb47339d9036fe531884e7e0e4ca4877e4160fc72c4d2e2910fa8d5addaa9`
- Task 1 required outputs/manifests were verified present via `manifests/initial_audit.json`.

## 2. Qrels-reference audit and final rule

The previous implementation manufactured a total qrels-derived order by filling missing judgments with `0` and tie-breaking equal grades by document ID. That behavior affected BEW, PIC, pairwise relevance-accuracy, `differently_graded_judged_pairs_changed`, and qrels-conditioned subsets.

Final rule adopted and implemented:

- Compare a candidate pair only when both documents have explicit qrels and their grades differ.
- Equal-grade pairs are incomparable and excluded.
- Any pair containing an unjudged document is unavailable for qrels-pair diagnostics.
- Zero-grade judged documents remain eligible when compared against a differently graded judged document.
- No document-ID tie-break manufactures a relevance preference.

Implementation:

- Added [`src/consistency_ranker/qrels_reference.py`](src/consistency_ranker/qrels_reference.py)
- Threaded the judged-pair rule through:
  - [`scripts/run_real_experiment.py`](scripts/run_real_experiment.py)
  - [`src/consistency_ranker/failure_mining/graph_features.py`](src/consistency_ranker/failure_mining/graph_features.py)
  - [`src/consistency_ranker/failure_mining/query_processor.py`](src/consistency_ranker/failure_mining/query_processor.py)
  - [`reports/full_calibrated_core/scripts/full_calibration_utils.py`](reports/full_calibrated_core/scripts/full_calibration_utils.py)
  - [`reports/full_calibrated_core/scripts/run_full_calibrated_core.py`](reports/full_calibrated_core/scripts/run_full_calibrated_core.py)
  - [`reports/full_calibrated_core/scripts/conditional_subsets.py`](reports/full_calibrated_core/scripts/conditional_subsets.py)

## 3. Regenerated BEW/PIC and conditional implications

The qrels-pair diagnostics were regenerated under the corrected rule. The manuscript no longer reports the old FiQA/BRIGHT BEW/PIC deltas because those values depended on the invalid manufactured reference order.

Canonical-pool qrels-pair availability from `tables/qrels_reference_eligibility_summary.csv`:

- SciDocs `pool20_ndcg20`: mean explicit judged docs `29.93`, mean eligible judged pairs `123.33`, zero-eligible query rate `0.00`
- FiQA `pool20_ndcg20`: mean explicit judged docs `1.87`, mean eligible judged pairs `0.00`, zero-eligible query rate `1.00`
- HotpotQA `pool10_ndcg5`: mean explicit judged docs `9.83`, mean eligible judged pairs `10.85`, zero-eligible query rate `0.02`
- BRIGHT `pool20_ndcg20`: mean explicit judged docs `5.58`, mean eligible judged pairs `0.00`, zero-eligible query rate `1.00`

Implications:

- SciDocs and HotpotQA still support qrels-pair diagnostics in the analyzed pools.
- FiQA and BRIGHT do not support qrels-pair diagnostics in those pools under a principled judged-pair rule.
- The conditional subset formerly described as “qrels-labeled ordering changed” is now defined as “repair reverses at least one explicitly judged different-grade pair.”

## 4. MDE methodology

Implemented in [`src/consistency_ranker/statistical_inference.py`](src/consistency_ranker/statistical_inference.py) and emitted into `tables/mde_per_cell.csv` and `tables/dataset_level_mde_summary.csv`.

Analytic MDE:

- Paired-normal approximation using observed paired-delta standard deviation, sample size, two-sided alpha, and target power.
- Reported at 80% and 90% power.
- Reported for nominal `alpha = 0.05`, the full Holm family, and the active `ms1` Holm family.

Simulation-based MDE:

- Prespecified additive shift grid.
- Deterministic seeds.
- Preserves sample size and zero mass by shifting sampled nonzero deltas while keeping zero deltas fixed.
- Uses the same sign-flip test family as the main analysis.

## 5. Analytic and simulation-based MDE results

Primary manuscript-facing summary:

- Final Task 1 active `ms1` nDCG family (`110` cells):
  - median absolute observed mean delta: `0.0035754186474477004`
  - median analytic 80% MDE at nominal alpha: `0.013323432010854265`
  - median analytic 80% MDE at active-family Holm alpha: `0.02067685223390709`
- Original canonical active `ms1` nDCG family (`20` cells):
  - median absolute observed mean delta: `0.003993045230030219`
  - median analytic 80% MDE at nominal alpha: `0.011071781419585053`
  - median analytic 80% MDE at active-family Holm alpha: `0.015274217481269146`

Interpretation:

- The typical observed repaired-vs-unrepaired mean deltas are materially smaller than the study’s Holm-adjusted detectable-effect scale.
- The study supports “no reliable evidence of improvement” more strongly than “evidence that all practically meaningful effects are absent.”

Simulation summary:

- Final active `ms1` family:
  - simulation MDE at nominal alpha was obtained for `32/110` cells
  - simulation MDE at Holm-adjusted active-family alpha was unresolved for `110/110` cells on the prespecified shift grid
- Canonical active `ms1` family:
  - simulation MDE at nominal alpha was obtained for `9/20` cells
  - simulation MDE at Holm-adjusted active-family alpha was unresolved for `20/20` cells on the prespecified shift grid

That behavior is why the manuscript emphasizes the analytic paired-MDE summaries and treats the simulation-based MDEs as artifact-level sensitivity information.

## 6. Equivalence-test results

Implemented paired TOST sensitivity analyses at margins `±0.005` and `±0.010`; outputs are in `tables/equivalence_test_table.csv`.

Active final `ms1` family only:

- Margin `±0.005`: `13/110` cells rejected non-equivalence after Holm
- Margin `±0.010`: `32/110` cells rejected non-equivalence after Holm

Interpretation:

- Equivalence can be established only cellwise, at a stated margin, for a minority of active cells.
- These results do not justify a global practical-equivalence claim for repair.
- The manuscript therefore uses equivalence only as a caution against over-reading non-significance, not as the headline conclusion.

## 7. Interval-method comparison

Outputs: `tables/interval_method_comparison.csv`

Notable canonical cells:

- SciDocs `ms1` Copeland graph:
  - percentile CI: `[0.0019386048064401829, 0.022288801991384107]`
  - basic CI: `[-0.00020286461548095144, 0.020147332569462974]`
  - BCa CI: `[0.003268246600278589, 0.025462338981413674]`
  - studentized CI: `[0.002862915811681785, 0.028253674724453344]`
- SciDocs `ms1` Copeland hybrid:
  - percentile CI: `[0.001808656343045766, 0.01727460048680892]`
  - basic CI: `[-0.0002225242882650559, 0.015243419855498099]`
  - BCa CI: `[0.002964535067139548, 0.020596872145817572]`
  - studentized CI: `[0.0024897673551275744, 0.023349745211963247]`

Conclusion:

- Interval construction can change whether a naive zero-exclusion story appears plausible for the canonical SciDocs Copeland cells.
- It does not change the multiplicity-corrected conclusion: no repaired-vs-unrepaired nDCG cell survives the prespecified Holm families.

## 8. Exact versus Monte Carlo sign-flip findings

Implemented exact sign-flip enumeration when the number of nonzero paired deltas is small enough; otherwise used Monte Carlo sign-flip tests.

Examples from `tables/interval_method_comparison.csv`:

- Canonical HotpotQA `ms1` Copeland graph:
  - exact: `0.328125`
  - Monte Carlo: `0.32196780321967805`
- Canonical HotpotQA `ms1` Copeland hybrid:
  - exact: `0.25`
  - Monte Carlo: `0.25317468253174685`
- Exact larger-pool SciDocs `pool50_ndcg10` Copeland hybrid:
  - exact: `0.218963623046875`
  - Monte Carlo: `0.2186781321867813`

The exact and Monte Carlo values agreed closely where both were available.

## 9. Holm/BH/BY comparison

Primary final Task 1 nDCG families from `manifests/task2_analysis_summary.json`:

- Full final family (`330` cells): Holm `0`, BH `0`, BY `0`
- Active `ms1` family (`110` cells): Holm `0`, BH `0`, BY `0`

Canonical primary-protocol nDCG family from `tables/canonical_primary_statistical_tests.csv`:

- Holm `0`, BH `0`, BY `0`

Cross-protocol dependence sensitivity from `tables/cross_protocol_statistical_tests.csv`:

- Full cross-protocol family: Holm `0`, BH `0`, BY `0`
- Active cross-protocol `ms1` family: one negative FiQA cell survives Holm and BH but not BY
  - dataset: `fiqa`
  - protocol: `ablation_raw_fixed`
  - pair: `copeland_hybrid`
  - mean delta: `-0.006963`
  - raw/sign-flip p-value: `0.0002`
  - Holm active-family adjusted p: `0.023997600239976005`
  - BH active-family adjusted p: `0.023997600239976005`
  - BY active-family adjusted p: `0.1288399549009914`

Interpretation:

- BY sensitivity does not support any positive repaired-vs-unrepaired claim.
- The lone cross-protocol hit is negative and not dependence-robust under BY, so it is not elevated to a headline inference.

## 10. Active-family results

The active-family analysis remains structurally defined by the `ms1` regime rather than by observed p-values.

Results:

- Final larger-pool active `ms1` family: `0/110` Holm, `0/110` BH, `0/110` BY
- Canonical active `ms1` family: `0/20` Holm, `0/20` BH, `0/20` BY

The manuscript now treats this family as the main “scientifically active” multiplicity family and keeps it separate from all-query and structurally inactive families.

## 11. Baseline-comparison analysis

Outputs: `tables/baseline_claim_audit.csv`

Decision:

- Baseline comparisons are retained as descriptive rankings only.
- No inferential superiority claim is made for CombSUM or RRF in this task.
- Every row in the audit has `claim_type = descriptive_only`.

## 12. Manuscript changes

Updated [`papers/JDIQ_2026/manuscript/main.tex`](papers/JDIQ_2026/manuscript/main.tex) to:

- define qrels-pair eligibility precisely and remove manufactured document-ID tie-breaking;
- replace the stale qrels-anchored BEW/PIC table with a qrels-pair availability table;
- distinguish evidence of improvement from no reliable evidence of improvement and from equivalence;
- state Holm as primary under dependence, BH as descriptive, and BY as sensitivity;
- note exact-vs-Monte-Carlo sign-flip handling and interval-method sensitivity;
- add compact MDE/power language for the active families;
- report the limited, margin-specific nature of equivalence findings;
- redefine the conditional qrels subset as explicit judged different-grade pair reversals;
- make baseline comparisons explicitly descriptive rather than inferential;
- revise the abstract, discussion, limitations, and conclusion to avoid claiming that non-significance proves effect absence.

## 13. Code and tests changed

New modules:

- [`src/consistency_ranker/qrels_reference.py`](src/consistency_ranker/qrels_reference.py)
- [`src/consistency_ranker/statistical_inference.py`](src/consistency_ranker/statistical_inference.py)

Patched code:

- [`scripts/run_real_experiment.py`](scripts/run_real_experiment.py)
- [`src/consistency_ranker/failure_mining/graph_features.py`](src/consistency_ranker/failure_mining/graph_features.py)
- [`src/consistency_ranker/failure_mining/query_processor.py`](src/consistency_ranker/failure_mining/query_processor.py)
- [`reports/full_calibrated_core/scripts/conditional_subsets.py`](reports/full_calibrated_core/scripts/conditional_subsets.py)
- [`reports/full_calibrated_core/scripts/full_calibration_utils.py`](reports/full_calibrated_core/scripts/full_calibration_utils.py)
- [`reports/full_calibrated_core/scripts/run_full_calibrated_core.py`](reports/full_calibrated_core/scripts/run_full_calibrated_core.py)

Task-local scripts:

- [`reports/final_revision_task2_statistical_power_20260715/scripts/run_task2_analysis.py`](reports/final_revision_task2_statistical_power_20260715/scripts/run_task2_analysis.py)
- [`reports/final_revision_task2_statistical_power_20260715/scripts/validate_task2_outputs.py`](reports/final_revision_task2_statistical_power_20260715/scripts/validate_task2_outputs.py)
- [`reports/final_revision_task2_statistical_power_20260715/scripts/claim_to_evidence_audit.py`](reports/final_revision_task2_statistical_power_20260715/scripts/claim_to_evidence_audit.py)
- [`reports/final_revision_task2_statistical_power_20260715/run_manifests/run_task2_validation.sh`](reports/final_revision_task2_statistical_power_20260715/run_manifests/run_task2_validation.sh)

Tests:

- [`tests/test_qrels_reference.py`](tests/test_qrels_reference.py)
- [`tests/test_statistical_inference.py`](tests/test_statistical_inference.py)
- [`tests/test_real_experiment_modes.py`](tests/test_real_experiment_modes.py)
- [`tests/test_conditional_subsets.py`](tests/test_conditional_subsets.py)
- Reused Task 1 regression coverage in [`tests/test_pool_cutoff_evaluation.py`](tests/test_pool_cutoff_evaluation.py)

## 14. Tmux sessions and logs

Analysis sessions:

- Superseded launch:
  - session: `jdiq_stats_task2_power`
  - manifest: `manifests/20260715_010146_analysis_launch.json`
  - log: `logs/20260715_010146_analysis.log`
  - status: superseded before meaningful output
- Successful launch:
  - session: `jdiq_stats_task2_power`
  - manifest: `manifests/20260715_011014_analysis_launch.json`
  - log: `logs/20260715_011014_analysis.log`
  - tmux pane PID: `3207387`
  - python PID during run: `3207399`
  - status: completed successfully

Validation sessions:

- First validation launch:
  - session: `jdiq_stats_task2_validate`
  - manifest: `manifests/20260715_013338_validation_launch.json`
  - log: `logs/20260715_013338_validation.log`
  - status: failed at an over-broad lint scope; preserved and superseded
- Final validation launch:
  - session: `jdiq_stats_task2_validate`
  - manifest: `manifests/20260715_013624_validation_launch.json`
  - log: `logs/20260715_013624_validation.log`
  - tmux pane PID: `3213054`
  - status: completed successfully; no active tmux jobs remain

## 15. Validation results

Task-specific tests:

- `pytest -q tests/test_qrels_reference.py tests/test_statistical_inference.py tests/test_real_experiment_modes.py tests/test_conditional_subsets.py tests/test_pool_cutoff_evaluation.py`
- Passed

Full test suite:

- `pytest -q`
- Passed: `584 passed in 9.01s`

Linting:

- `ruff check --select F,E9 ...` on touched Python files and task-local scripts
- Passed

Compilation:

- `py_compile` on touched/task-local Python files
- Passed

Repository readiness:

- `python scripts/check_repo_ready.py`
- Passed with non-critical pre-existing documentation warnings only

Per-query-to-aggregate verification:

- `python reports/final_revision_task1_pool_cutoff_20260715/scripts/verify_pool_cutoff_outputs.py`
- Passed

Table-regeneration verification:

- `python reports/final_revision_task2_statistical_power_20260715/scripts/run_task2_analysis.py`
- Completed successfully during validation

Task 2 output verification:

- `python reports/final_revision_task2_statistical_power_20260715/scripts/validate_task2_outputs.py`
- Passed
- Output file: `validation/task2_output_validation.json`

Claim-to-evidence audit:

- `python reports/final_revision_task2_statistical_power_20260715/scripts/claim_to_evidence_audit.py`
- Passed
- Output file: `validation/claim_to_evidence_audit.md`

LaTeX build:

- `cd papers/JDIQ_2026/manuscript && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex`
- Passed
- Final manuscript PDF checksum:
  - `sha256 = cd9aba45b2206d9363d73278284c9f18abcfaadaf18a9593a6a5dd92ac9185ff`

## 16. Remaining statistical limitations

- The paired deltas remain highly zero-inflated and skewed.
- The simulation-based MDE procedure is sensitive to the chosen shift grid and did not yield Holm-adjusted active-family thresholds on that grid.
- Equivalence depends on the stated margin and was established only for a minority of active cells.
- FiQA and BRIGHT lack eligible judged different-grade pairs in the analyzed candidate pools, so qrels-pair diagnostics remain unavailable there.
- BY sensitivity eliminates the lone negative cross-protocol active-family hit that survives Holm/BH.

## 17. Exact reproduction commands

Primary Task 2 analysis:

```bash
cd 
./.venv/bin/python reports/final_revision_task2_statistical_power_20260715/scripts/run_task2_analysis.py
```

Full Task 2 validation bundle:

```bash
cd 
bash reports/final_revision_task2_statistical_power_20260715/run_manifests/run_task2_validation.sh
```

Key validation subcommands:

```bash
cd 
./.venv/bin/python reports/final_revision_task2_statistical_power_20260715/scripts/validate_task2_outputs.py
./.venv/bin/python reports/final_revision_task2_statistical_power_20260715/scripts/claim_to_evidence_audit.py
cd papers/JDIQ_2026/manuscript && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Logged tmux launch equivalents are preserved in:

- `manifests/20260715_011014_analysis_launch.json`
- `manifests/20260715_013624_validation_launch.json`

## 18. Proposed commit message

`Task 2: tighten qrels-reference diagnostics and add power-aware statistical audit`
