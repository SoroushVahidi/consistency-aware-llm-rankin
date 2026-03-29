# Routing study: cost–accuracy / decision analysis

## Status: **BLOCKED — analysis not run**

Per project rules, this pass **validates routing-study artifacts first** and **does not** build tables, plots, or recommendations from retrieval/qrels/ranking outputs (SciDocs, BRIGHT, FiQA, HotpotQA, cross-encoder, etc.).

**Result:** Required routing directories and oracle summaries are **absent** in this workspace. **No** `unified_routing_results.csv`, **no** per-dataset PNG/CSV analysis bundle, and **no** cross-dataset routing insights were generated, to avoid misleading substitutes.

Machine-readable log: `outputs/analysis/routing_study_validation_blocker.txt`.

---

## 1. Exact artifact sources used

**None.** No files were accepted from the allowed routing-only list.

---

## 2. Datasets covered

**None** for the routing study. The allowed reasoning benchmarks (GSM8K, Hard GSM8K, MATH500, AIME, GPQA) have **no** corresponding routing outputs in the checked paths.

---

## 3. Methods compared

**N/A** — no routing method results were loaded.

---

## 4. Budget-sensitive recommendations

**N/A** — blocked pending routing artifacts.

---

## 5. Do adaptive methods beat static baselines?

**Not evaluated** — blocked.

---

## 6. Do hard datasets reduce label degeneracy?

**Not evaluated** — blocked. (This question requires routing-study accuracy/cost traces per dataset.)

---

## 7. Missing artifacts / blockers (precise)

### Valid sources that must exist (all missing)

| Expected location | Workspace status |
|-------------------|------------------|
| `outputs/real_policy_eval/*` | **Missing** — `/workspace/outputs/real_policy_eval/` does not exist |
| `outputs/real_routing_model/*` | **Missing** — `/workspace/outputs/real_routing_model/` does not exist |
| `outputs/multi_action_models/*` | **Missing** — `/workspace/outputs/multi_action_models/` does not exist |
| `outputs/baselines/*` | **Missing** — `/workspace/outputs/baselines/` does not exist |
| `outputs/*oracle*summary*.json` (datasets: GSM8K, Hard GSM8K, MATH500, AIME, GPQA) | **Missing** — no files matching `*oracle*summary*.json` under `outputs/` |

### What was explicitly not used

Anything outside the list above, including existing retrieval experiment trees (`outputs/real_full/`, `outputs/final_modern_baselines*/`, `outputs/openai_*`, `outputs/analysis/` from the prior non-routing bundle, etc.).

### Outputs intentionally **not** produced (until unblock)

- `outputs/analysis/unified_routing_results.csv`
- `outputs/analysis/{dataset}_cost_accuracy_curve.png`
- `outputs/analysis/{dataset}_pareto.csv`
- `outputs/analysis/{dataset}_regret.csv`
- `outputs/analysis/{dataset}_decision_table.csv`
- `outputs/analysis/cross_dataset_routing_insights.csv`

---

## Unblock checklist

1. Populate `outputs/real_policy_eval/`, `outputs/real_routing_model/`, `outputs/multi_action_models/`, and/or `outputs/baselines/` with committed routing-study results (schema documented by the routing pipeline).
2. Add oracle summary JSON files under `outputs/` matching `*oracle*summary*.json` for the target datasets.
3. Implement or run a **routing-only** generator script (analogous to the retrieval analysis script, but restricted to these paths) and re-run validation.

Until then, **stop here**; do not infer routing conclusions from unrelated outputs.
