# Reviewer-Concerns Follow-On Program — Final Report

**Git:** `fix/outcome-f-production-operating-point` @ `8761004cb5749db515a5de9f7fc5fb14c7ee4de3` (dirty working tree at program start)

## 1. Do real modern LLM preference graphs exhibit more recoverable
   inconsistency than the classical score-derived graphs?

Real LLM graphs DID show more structural inconsistency than the classical score-derived comparison (repo-scale classical oracle headroom ≈0.0025, n=419) at the aggregate-graph level (6/6 multi-provider aggregate graphs cyclic in the original pilot), but whole-graph query-level oracle headroom in the original pilot was exactly 0.0 (CI [0,0], n=6) -- i.e. more cycles did not translate into more recoverable nDCG opportunity at pool_size=6, top-relevance-only construction. See Stage 6 for whether Branch B's varied constructions changed this.

## 2. How often does consistency repair help, hurt, or do nothing?

In the original pilot's primary (greedy) method: repair helped 0, hurt 0, and did nothing to 30 of 30 rows. See STAGE6_ROBUSTNESS.json's per-slice breakdown for the pooled original+Branch B picture.

## 3. Is benefit concentrated in particular providers, aggregation
   methods, SCCs, edges, or top-k regions?

See `STAGE6_ROBUSTNESS.json` (per-provider/aggregate/dataset/variant slices) and `STAGE7_COUNTERFACTUAL.json` (inside- vs outside-top-k single-edge-removal deltas) for the direct evidence.

## 4. Can graph features predict when repair helps on held-out queries?

"See STAGE5_PREDICTION.json for model-by-model results."

## 5. Does a learned selective policy improve over always-repair and
   never-repair baselines?

See `STAGE5_PREDICTION.json`'s `models` block (`always_repair`, `never_repair`, `logistic_regression`, `decision_tree` balanced accuracies) — not evaluated if Stage 5 was skipped for inadequate label variation.

## 6. Are results robust to reasonable methodological choices?

See `STAGE6_ROBUSTNESS.json`'s per-slice oracle headroom (greedy vs exact, per-provider vs aggregate, per-dataset, per-construction-variant).

## 7. Which findings are statistically supported, exploratory, or
   falsified?

Statistically supported (query-level CI, n=6 original pilot queries): whole-graph repair produced exactly zero measurable nDCG change at pool_size=6, top-relevance-only construction, despite genuine structural cyclicity in aggregate graphs. Exploratory only: Stage 5 predictive-model numbers (tiny n), Stage 7 synthetic counterfactual deltas (single-edge perturbation, not a full re-solve, not independently LLM-validated).

## 8. What is the strongest defensible manuscript contribution after
   this experiment?

Consistent with the repository's existing negative-result manuscript package (`papers/negative_result_2026/`): this program's evidence, at pilot scale, does not overturn that conclusion for whole-graph repair, and additionally shows that even with genuine real-LLM-induced aggregate-graph cyclicity, repair-induced ranking change was not observed at all under the original construction — strengthening rather than weakening the negative result, subject to the small-sample caveats documented throughout this report.

## 9. What additional evidence would still be required to satisfy the
   reviewers?

At minimum: (a) a Branch-A-style scale-up to tens of independent queries once a construction is found that produces nonzero-delta variation, since n=6 unique queries cannot support any reliable predictive claim regardless of feature quality; (b) resolution of whether the Cohere/schema and Fireworks reasoning-token paths generalize to larger candidate pools without cost or latency surprises; (c) an actual construction (see Stage 6/7) that produces repair-induced ranking changes with more than a handful of nonzero examples before any Stage-5-style modeling claim could be treated as more than illustrative.

## Files in this directory

- `STAGE1_INTERPRETATION.json`, `BRANCH_DECISION.json`
- `ESTIMATE_branch_b.json`, `smoke_branch_b/SMOKE_BRANCH_B_RESULT.json`
- `checkpoint/branch_b_results.jsonl`, `checkpoint/branch_b_provider_prefs.jsonl`
- `raw_calls/*.jsonl`, `cache/**`, `provider_usage.jsonl`, `provider_failures.jsonl`
- `stage4_feature_rows.jsonl`, `STAGE5_PREDICTION.json`, `STAGE6_ROBUSTNESS.json`,
  `STAGE7_COUNTERFACTUAL.json`
- `ENVIRONMENT_pip_freeze.txt`, `FINAL_SUMMARY.json` (this report's machine-readable twin)