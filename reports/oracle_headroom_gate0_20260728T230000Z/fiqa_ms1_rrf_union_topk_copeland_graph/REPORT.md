# Oracle-Headroom Gate Report (preserve vs. repair)

Input: `/home/soroush/consistency-aware-llm-rankin/reports/candidate_pool_conditional_audit_20260714/tables/pool_robustness_paired_deltas.csv` (filters: `{'dataset': 'fiqa', 'regime': 'ms1', 'pool_id': 'rrf_union_topk', 'pair_name': 'copeland_graph'}`)
Queries: 120

## Aggregate outcomes

| Policy | Mean metric |
|---|---:|
| always_preserve | 0.276707 |
| always_repair | 0.280342 |
| oracle | 0.286103 |

Safer fixed default: **repair**

## Headroom

H = mean(oracle) - max(mean(preserve), mean(repair)) = **0.005762**
95% CI (percentile, 10000 reps, seed=13): [0.001120, 0.013079]

## Per-query heterogeneity

- Benefit from repair (delta > 0): 17.5%
- Harmed by repair (delta < 0): 8.3%
- Exactly neutral (delta == 0): 74.2%
- Mean regret of always-preserve vs. oracle: 0.009396
- Mean regret of always-repair vs. oracle: 0.005762

## Delta distribution

```
{
  "mean": 0.003634275353696659,
  "median": 0.0,
  "n": 120,
  "nonzero_count": 31,
  "nonzero_fraction": 0.25833333333333336,
  "observed_standardized_effect": 0.0773876491800859,
  "q05": -0.027246031215337734,
  "q25": 0.0,
  "q75": 0.0,
  "q95": 0.07953176504596222,
  "se": 0.00428702041495996,
  "std": 0.046961955715174565
}
```

## Gate-0 decision

**AMBIGUOUS_NEED_MORE_DATA**

Headroom CI [0.0011202241406369727, 0.013079439754137017] straddles the threshold (0.01000) or heterogeneity is one-sided (benefit=17.5%, harm=8.3%, need >= 5.0% each). Do not commit to either path; expand the query sample (e.g. additional regimes/pools/datasets already on disk) before deciding.
