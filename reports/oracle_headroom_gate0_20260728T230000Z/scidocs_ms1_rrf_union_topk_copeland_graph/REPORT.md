# Oracle-Headroom Gate Report (preserve vs. repair)

Input: `/home/soroush/consistency-aware-llm-rankin/reports/candidate_pool_conditional_audit_20260714/tables/pool_robustness_paired_deltas.csv` (filters: `{'dataset': 'scidocs', 'regime': 'ms1', 'pool_id': 'rrf_union_topk', 'pair_name': 'copeland_graph'}`)
Queries: 120

## Aggregate outcomes

| Policy | Mean metric |
|---|---:|
| always_preserve | 0.324825 |
| always_repair | 0.335868 |
| oracle | 0.341429 |

Safer fixed default: **repair**

## Headroom

H = mean(oracle) - max(mean(preserve), mean(repair)) = **0.005561**
95% CI (percentile, 10000 reps, seed=13): [0.002907, 0.008702]

## Per-query heterogeneity

- Benefit from repair (delta > 0): 30.0%
- Harmed by repair (delta < 0): 18.3%
- Exactly neutral (delta == 0): 51.7%
- Mean regret of always-preserve vs. oracle: 0.016604
- Mean regret of always-repair vs. oracle: 0.005561

## Delta distribution

```
{
  "mean": 0.011042968687951581,
  "median": 0.0,
  "n": 120,
  "nonzero_count": 58,
  "nonzero_fraction": 0.48333333333333334,
  "observed_standardized_effect": 0.1928666636062435,
  "q05": -0.04387703313094845,
  "q25": 0.0,
  "q75": 0.011041952055485985,
  "q95": 0.08053624936086762,
  "se": 0.00522682608727282,
  "std": 0.057257011043115785
}
```

## Gate-0 decision

**NO_HEADROOM_DO_NOT_LEARN**

Headroom 95% CI upper bound (0.00870) does not exceed the threshold (0.01000); a learned selector cannot plausibly beat the stronger fixed baseline by more than noise on this slice. Do not proceed to label/feature/model work on this slice; see the negative-result fallback path.
