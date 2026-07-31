# Repair-Regime Diagnostic Study -- Final Report

Runtime: 4.1s. Query-graphs evaluated: 120 (identical set used by the repair-frontier and extraction studies).

## Predeclared decision

**NO_IDENTIFIABLE_REPAIR_REGIME**

Oracle headroom (0.00009, gate decision 'NO_HEADROOM_DO_NOT_LEARN') does not clear the 0.01 threshold at all -- there is no repair benefit to identify a regime for, predictable or not.

### Gate conditions

```
{
  "pre_repair_features_only": true,
  "survives_grouped_validation": false,
  "policy_beats_never_repair": false,
  "stable_across_subgroups": false,
  "practically_meaningful": false
}
```

## Outcome breakdown

```
{
  "improves": {
    "n": 1,
    "mean_delta": 0.010393774812847534,
    "mean_ndcg_preserve": 0.9565912771023182,
    "mean_ndcg_repair": 0.9669850519151657
  },
  "harms": {
    "n": 9,
    "mean_delta": -0.013497422426815089,
    "mean_ndcg_preserve": 0.8499598064920818,
    "mean_ndcg_repair": 0.8364623840652666
  },
  "no_change": {
    "n": 110,
    "mean_delta": 0.0,
    "mean_ndcg_preserve": 0.8912440380705388,
    "mean_ndcg_repair": 0.8912440380705388
  }
}
```

Overall mean-delta bootstrap 95% CI: [-0.00191, -0.00019].

## Top pre-/post-repair feature associations (by Holm-adjusted significance)

```
- is_cyclic (pre_repair): r=-0.248, raw p=0.0010, Holm p=0.0230
- topk_involvement (pre_repair): r=-0.248, raw p=0.0010, Holm p=0.0230
- largest_scc_size (pre_repair): r=-0.193, raw p=0.0368, Holm p=0.7727
- n_nontrivial_sccs (pre_repair): r=-0.191, raw p=0.0435, Holm p=0.8699
- edge_weight_std (pre_repair): r=-0.187, raw p=0.0478, Holm p=0.9081
- scc_cycle_weight_frac (pre_repair): r=-0.169, raw p=0.0573, Holm p=0.9377
- edge_weight_max (pre_repair): r=-0.183, raw p=0.0521, Holm p=0.9377
- repair_objective_frac (post_repair): r=-0.169, raw p=0.0527, Holm p=0.9377
```

See `tables/FEATURE_ASSOCIATIONS.csv` for the full list (all 23 features, pre- and post-repair clearly tagged) and `tables/FEATURE_STABILITY.csv` for stability across datasets/providers/pool sizes.

## Outlier sensitivity

Mean delta: -0.00093; excluding the single largest delta: -0.0010208134608515613.

## Oracle headroom gate (never-repair vs. always-repair, 2-action)

**NO_HEADROOM_DO_NOT_LEARN**. Headroom 95% CI upper bound (0.00026) does not exceed the threshold (0.01000); a learned selector cannot plausibly beat the stronger fixed baseline by more than noise on this slice. Do not proceed to label/feature/model work on this slice; see the negative-result fallback path.

Baselines (mean nDCG): never_repair=0.888692, always_repair=0.887767, random_selection=0.888229, oracle_selection=0.888779.

## Grouped-CV prediction from pre-repair features only

Status: **UNSUPPORTED**. Only 1 'improves' and 119 non-improving rows -- inadequate class balance for grouped-CV classification (folds without any positive example would trivially inflate balanced accuracy for every model, including negative controls). Reporting UNSUPPORTED rather than a misleading metric.

Subgroup stability (best model, minimum pass-fraction across dataset/provider/pool_size): 0%.

## Are the rare benefits of consistency repair predictable, or isolated and non-deployable?

Isolated and non-deployable, more fundamentally: there is no meaningful repair benefit to identify a regime for in the first place on this data -- consistent with this research thread's other negative results.

## Files in this directory

- `RUN_CONFIG.json`, `diagnostic_results.jsonl`, `failures.jsonl`
- `tables/FEATURE_ASSOCIATIONS.csv`, `tables/FEATURE_STABILITY.csv`
- `FINAL_SUMMARY.json` (this report's machine-readable twin)
