# Oracle-Headroom Gate Report (preserve vs. repair)

Input: `/home/soroush/consistency-aware-llm-rankin/reports/candidate_pool_conditional_audit_20260714/tables/pool_robustness_paired_deltas.csv` (filters: `{'dataset': 'hotpotqa', 'regime': 'ms1', 'pool_id': 'rrf_union_topk', 'pair_name': 'copeland_graph'}`)
Queries: 52

## Aggregate outcomes

| Policy | Mean metric |
|---|---:|
| always_preserve | 0.873450 |
| always_repair | 0.888956 |
| oracle | 0.897166 |

Safer fixed default: **repair**

## Headroom

H = mean(oracle) - max(mean(preserve), mean(repair)) = **0.008210**
95% CI (percentile, 10000 reps, seed=13): [0.000000, 0.023248]

## Per-query heterogeneity

- Benefit from repair (delta > 0): 9.6%
- Harmed by repair (delta < 0): 5.8%
- Exactly neutral (delta == 0): 84.6%
- Mean regret of always-preserve vs. oracle: 0.023716
- Mean regret of always-repair vs. oracle: 0.008210

## Delta distribution

```
{
  "mean": 0.015506071177538171,
  "median": 0.0,
  "n": 52,
  "nonzero_count": 8,
  "nonzero_fraction": 0.15384615384615385,
  "observed_standardized_effect": 0.15621701701149765,
  "q05": -0.006311267653355103,
  "q25": 0.0,
  "q75": 0.0,
  "q95": 0.22629438553091674,
  "se": 0.013764858799329363,
  "std": 0.0992598084010074
}
```

## Gate-0 decision

**AMBIGUOUS_NEED_MORE_DATA**

Headroom CI [0.0, 0.02324775538832708] straddles the threshold (0.01000) or heterogeneity is one-sided (benefit=9.6%, harm=5.8%, need >= 5.0% each). Do not commit to either path; expand the query sample (e.g. additional regimes/pools/datasets already on disk) before deciding.
