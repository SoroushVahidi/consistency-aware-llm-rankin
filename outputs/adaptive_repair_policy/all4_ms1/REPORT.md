# Adaptive repair policy (lightweight)

- Source root: `/workspace/consistency-aware-llm-rankin/outputs/pub_vote_cmp_all4`
- Variant: `ms1`
- Policy: **skip repair when acyclic**, otherwise use repaired method.

## Copeland summary

| Dataset | Trigger repair % | Prior | Unrepaired Copeland | Repaired Copeland | Adaptive Copeland | Δ(adaptive-repaired) |
|---|---:|---:|---:|---:|---:|---:|
| scidocs | 87.50% | 0.306520 | 0.302274 | 0.302148 | 0.302148 | +0.000000 |
| fiqa | 95.00% | 0.237183 | 0.241381 | 0.242837 | 0.242837 | +0.000000 |
| hotpotqa | 51.92% | 0.876742 | 0.889175 | 0.905888 | 0.905888 | +0.000000 |
| bright | 60.00% | 0.522822 | 0.520101 | 0.520122 | 0.520122 | +0.000000 |

## Notes

- Paired deltas are derived from the committed bootstrap analysis strata.
- For this strict policy, skipped queries are the acyclic stratum.
- If acyclic unrepaired-vs-repaired delta is zero, adaptive equals always-repair.

## Balance (optional)

| Dataset | Unrepaired Balance | Repaired Balance | Adaptive Balance | Δ(adaptive-repaired) |
|---|---:|---:|---:|---:|
| scidocs | 0.301644 | 0.301644 | 0.301644 | +0.000000 |
| fiqa | 0.241522 | 0.241522 | 0.241522 | +0.000000 |
| hotpotqa | 0.909397 | 0.909397 | 0.909397 | +0.000000 |
| bright | 0.532291 | 0.532291 | 0.532291 | +0.000000 |
