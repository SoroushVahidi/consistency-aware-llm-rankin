# Oracle-Headroom Gate Report (preserve vs. repair)

Input: `/home/soroush/consistency-aware-llm-rankin/reports/candidate_pool_conditional_audit_20260714/tables/pool_robustness_paired_deltas.csv` (filters: `{'dataset': 'bright', 'regime': 'ms1', 'pool_id': 'rrf_union_topk', 'pair_name': 'copeland_graph'}`)
Queries: 50

## Aggregate outcomes

| Policy | Mean metric |
|---|---:|
| always_preserve | 0.646250 |
| always_repair | 0.632208 |
| oracle | 0.656883 |

Safer fixed default: **preserve**

## Headroom

H = mean(oracle) - max(mean(preserve), mean(repair)) = **0.010633**
95% CI (percentile, 10000 reps, seed=13): [0.005503, 0.016728]

## Per-query heterogeneity

- Benefit from repair (delta > 0): 38.0%
- Harmed by repair (delta < 0): 26.0%
- Exactly neutral (delta == 0): 36.0%
- Mean regret of always-preserve vs. oracle: 0.010633
- Mean regret of always-repair vs. oracle: 0.024675

## Delta distribution

```
{
  "mean": -0.014041497577935984,
  "median": 0.0,
  "n": 50,
  "nonzero_count": 32,
  "nonzero_fraction": 0.64,
  "observed_standardized_effect": -0.16745378202124211,
  "q05": -0.15310814893061933,
  "q25": -0.00371062287728699,
  "q75": 0.015047815391424399,
  "q95": 0.06090849466252464,
  "se": 0.011858601263617334,
  "std": 0.08385297368891179
}
```

## Gate-0 decision

**AMBIGUOUS_NEED_MORE_DATA**

Headroom CI [0.005503308218375989, 0.01672804161891051] straddles the threshold (0.01000) or heterogeneity is one-sided (benefit=38.0%, harm=26.0%, need >= 5.0% each). Do not commit to either path; expand the query sample (e.g. additional regimes/pools/datasets already on disk) before deciding.
