# Bootstrap CIs — HOTPOTQA (flip_prob=0.15)

n_bootstrap=2000, seed=42, metric=ndcg_at_k

| Comparison | Δ nDCG | CI 95% low | CI 95% high | Sig. | n |
|------------|--------|------------|-------------|------|---|
| score_sum vs FAS topological | +0.3229 | +0.3055 | +0.3390 | *** | 497 |
| score_sum vs Bradley-Terry | +0.2749 | +0.2573 | +0.2927 | *** | 497 |
| score_sum vs win-rate | +0.2423 | +0.2233 | +0.2621 | *** | 497 |
| score_sum vs tournament sort | +0.1903 | +0.1705 | +0.2099 | *** | 497 |
| FAS-balance vs BT | +0.2644 | +0.2462 | +0.2817 | *** | 497 |
| FAS-balance vs win-rate | +0.2318 | +0.2121 | +0.2513 | *** | 497 |
| FAS-balance vs Markov | +0.0096 | +0.0018 | +0.0173 | *** | 497 |
| FAS-copeland vs unrepaired copeland | -0.0010 | -0.0020 | -0.0002 | *** | 497 |
| FAS-copeland vs BT | +0.2644 | +0.2462 | +0.2817 | *** | 497 |
| Borda vs win-rate | +0.2423 | +0.2233 | +0.2621 | *** | 497 |