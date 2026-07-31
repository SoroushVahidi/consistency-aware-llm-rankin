# Real-Query Repair and Policy-Utility Replay
## 1. Executive Verdict
**NO CURRENT CRITERION BEATS ALWAYS-UHT**
Primary analysis: unrepaired vs greedy (and exact where available) Copeland rankings on cached OpenAI pairwise judgments. Independent queries in primary gain table: **80**. Mean greedy−unrepaired nDCG: **-0.005402**.
## 2. Git and Provenance State
- Starting commit (pre-review-boundary): `3e02b73666506f3eb894f5df2c531284ea31a60e`
- Review-boundary commits:
  - `361433358b756965ab8ae2459892019f3ba9f4f9` — Enforce Outcome F production operating point
  - `51fec8908918ef5ba79c6fc91dc049d223c34a2b` — Add Outcome F audit and reviewer concern gap reports
- Scientific replay commit: `19d8304c50b812106bfbef8a4438fd55647ad99c` — offline real-query repair/policy-utility replay
- Report hash commit: `65b1427d930fbfe2b08c2aa3005f84d2d53f419d` (and follow-up provenance fix)
- Output dir: `reports/real_query_policy_replay_20260726T042025Z`
- Network calls: **0**
- Local cache dependencies: see `canonical_evidence_manifest.json`
- Mapping note: on complete-graph OpenAI pairwise caches, the conservative analogue of always-UHT is **always unrepaired**; budgeted UHT/challenger routing was not reconstructible here.
## 3. Canonical Evidence Inventory
```json
{
  "n_sources": 8,
  "n_independent_queries": 148,
  "n_queries_with_qrels": 148,
  "datasets": [
    "bright",
    "fiqa",
    "hotpotqa",
    "scidocs"
  ],
  "providers": [
    "azure",
    "cohere",
    "fireworks",
    "gemini",
    "openai"
  ]
}
```
## 4. Deduplication and Missing Cells
SciDocs q20/q30 treated as nested subsets of q50 (see `duplicate_evidence_report.csv`). Missing factorial cells listed in `missing_factor_cells.csv`.
## 5. Reconstructed Policies and Metrics
Per-query unrepaired / greedy / exact Copeland & balance + hybrid α=0.3 rows in `query_policy_rows.csv`. Primary target `repair_gain` = greedy_copeland − unrepaired_copeland nDCG.
## 6. Feature-Schema Versioning
- `policy_gate_features_v1` (`legacy_v1`): frozen defective constants (`preliminary_g_prior=1.0`, `evidence_only_stability_proxy=0.0`).
- `policy_gate_features_coverage_v2` (`coverage_v2`): uses `topk_evidence_coverage.fraction_acquired` under unambiguous names.
Demo rows: `feature_rows_legacy_v1.csv`, `feature_rows_coverage_v2.csv`.
## 7. Prediction Targets
1. `repair_gain` (primary)
2. `exact_repair_gain` where exact SCIP succeeded
3. UHT-optimality / policy routing: **not evaluable** on all-pairs OpenAI caches (no budgeted acquisition trace); see INCOMPLETE.md
## 8. Predictor Results
| criterion | n | mean ΔU | esc. rate | cat. false-trust |
|---|---:|---:|---:|---:|
| always_unrepaired | 80 | 0.000000 | 0.000 | 0.000 |
| always_repair | 80 | -0.005402 | 1.000 | 0.163 |
| oracle_repair_if_positive | 80 | 0.000000 | 0.000 | 0.000 |
| cycle_presence | 80 | -0.005402 | 0.787 | 0.206 |
| largest_scc_frac_ge_0.25 | 80 | -0.005402 | 0.863 | 0.188 |
| largest_scc_frac_ge_0.5 | 80 | -0.002552 | 0.412 | 0.212 |
| random_matched_rate_0.79 | 80 | -0.004421 | 0.787 | 0.175 |
| lodo_fiqa_largest_scc_frac | 10 | 0.000000 | 0.000 | 0.000 |
| lodo_hotpotqa_largest_scc_frac | 20 | 0.000000 | 0.000 | 0.000 |
| lodo_scidocs_largest_scc_frac | 50 | 0.000000 | 0.000 | 0.000 |
| lodo_fiqa_is_cyclic | 10 | 0.000000 | 0.000 | 0.000 |
| lodo_hotpotqa_is_cyclic | 20 | 0.000000 | 0.000 | 0.000 |
| lodo_scidocs_is_cyclic | 50 | 0.000000 | 0.000 | 0.000 |

## 9. Calibration
```json
{
  "n": 80,
  "positive_rate_repair_helps": 0.0,
  "mean_repair_gain": -0.005401927423255629,
  "mean_exact_minus_greedy_ndcg": 0.011799381919800395
}
```
## 10. Utility and Regret
See `regret_results.csv` (always-unrepaired regret = max(0, repair_gain)).
## 11. Dataset and Provider Transfer
Datasets in primary table: ['fiqa', 'hotpotqa', 'scidocs']. Providers: ['openai']. LODO logistic results are in `model_results.csv`.
## 12. Orientation and Prompt Sensitivity
OpenAI SciDocs/HotpotQA/FiQA caches were collected with `debias_position=false` (no orientation factor). Failure-mining oriented metrics are recorded separately in `failure_mining_metric_rows.csv` but are not pooled into the primary gain table to avoid mixing incompatible schemas.
## 13. Safeguard-Cost Reconstruction
```json
{
  "n_cells": 36,
  "mean_jaccard_delta": 0.01111111111111111,
  "mean_call_delta": -0.16666666666666666,
  "n_adverse_delta_lt_m0_2": 3,
  "budget8_mean_jaccard_delta": -0.075,
  "recommendation": "minimum-budget-constrained; diagnostically recommended but not yet empirically validated on real queries"
}
```
Recommendation: **diagnostically recommended but not yet empirically validated** on real queries; treat as **minimum-budget-constrained** (2–3 reserved calls dominate at budget 8).
## 14. Reviewer Concerns Addressed
- **C2/C11 (actionable criterion):** no deployable criterion beat always-unrepaired with stable multi-dataset support under the prespecified rule. On the **primary greedy table** (80 queries) repair never helped (`positive_rate_repair_helps=0.0`, so `oracle_repair_if_positive` is also 0.0 and shows **no** primary-table heterogeneity). A separate **exact-SCIP subset** (63 rows) shows limited sign variation (8 positive / 4 negative exact−unrepaired gains; mean ≈ +0.00494) but does **not** overturn the always-unrepaired headline.
- **C4 (limited real LLM):** reused existing caches; did not expand paid calls.
- **C7/C8 (exact vs greedy):** exact SCIP reconstructed where solvable; compare `exact_repair_gain_rows.csv` (exploratory subset, not the primary success criterion).
- **C12 (statistical uncertainty):** query-clustered sign-flip CIs in criterion notes.
- **C1 (obviousness):** negative mean greedy repair gain on the primary table shows the conditional effect is empirical, not a tautology on these real caches; the primary oracle-if-positive rule is vacuous here because no greedy gain is positive.
## 15. Remaining Gaps
- UHT/challenger/hybrid/robust acquisition replay requires provenance-rich budgeted judgment pools; SciDocs OpenAI q50 is full all-pairs (no acquisition trace). Multi-provider pilot has only 2 queries. Policy-routing conclusions are therefore limited to repair-vs-unrepaired on complete graphs plus synthetic safeguard-cost cells.
## 16. Next Experiment
Only if a matched multi-factor calibration is still required after this negative/underpowered result:

| Missing cell | Provider | Model | Prompt | Queries | Orient | Est. calls | Cache avoids |
|---|---|---|---|---:|---|---:|---|
| SciDocs 30–40 × 2 prov × 2 prompts × AB/BA | azure + cohere | gpt-4.1-mini + command-r-plus-08-2024 | legacy_v1 + concise_v1 | 30 | both | ~C(10,2)×30×2×2×2 ≈ 10.8k worst-case; with top-6 ≈ 2.7k | skip keys already in multi_provider judgment_records + failure_mining caches |

Expansion: only if offline LODO gains stay positive but CI includes 0. Stop: when a deployable criterion’s sign-flip CI excludes 0 on ≥2 datasets, or after one matched 30-query pilot fails the success rule.
**Do not execute these calls in this task.**
## 17. Final Answers
1. Independent original queries (primary): **80**
2. Datasets: **['fiqa', 'hotpotqa', 'scidocs']**; providers: **['openai']**
3. Policy heterogeneity (repair): **no positive repair-gain cells** — fraction with repair_gain>0 = 0.000; magnitude of non-positive gains still varies across queries
4. Repair help: **no** under the primary unrepaired-vs-greedy Copeland nDCG comparison (mean gain −0.005402)
5. Exact vs greedy: n_exact_gain_rows=63, mean exact−unrepaired=0.004940 (exact can differ from greedy; does not reverse the always-unrepaired headline)
6. Pre-decision features: `is_cyclic`, `largest_scc_frac` evaluated; see model_results
7. UHT optimality features: **not estimable** from all-pairs caches
8. Deployable criterion beat always-unrepaired? **always_unrepaired** ΔU=0.0
9. Stable across datasets? see LODO rows
10. Stable across providers? OpenAI-only in primary table
11. Orientation sensitivity: **not measurable** on primary OpenAI caches
12. coverage_v2 vs legacy_v1: demo rows written; legacy constants preserved
13. Production safeguards utility-positive on real queries? **unknown** (synthetic only); synthetic mean ΔJ=0.0111
14. Reviewer concerns moved: C2/C11 evidence deepened (negative/underpowered); C7/C8 reconfirmed via reconstruction; C4 reused caches
15. Smallest justified paid pilot: matched 30×azure+cohere×2 prompts×orientation only for cells absent from existing provenance stores
