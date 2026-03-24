# Bootstrap CIs — SCIDOCS (flip_prob=0.15)

n_bootstrap=2000, seed=42, metric=ndcg_at_k

| Comparison | Δ nDCG | CI 95% low | CI 95% high | Sig. | n |
|------------|--------|------------|-------------|------|---|
| score_sum vs FAS topological | +0.0642 | +0.0600 | +0.0686 | *** | 500 |
| score_sum vs Bradley-Terry | +0.0500 | +0.0448 | +0.0552 | *** | 500 |
| score_sum vs win-rate | +0.0018 | +0.0011 | +0.0028 | *** | 500 |
| score_sum vs tournament sort | +0.2720 | +0.2597 | +0.2849 | *** | 500 |
| FAS-balance vs BT | +0.0491 | +0.0438 | +0.0543 | *** | 500 |
| FAS-balance vs win-rate | +0.0009 | +0.0000 | +0.0019 | *** | 500 |
| FAS-balance vs Markov | +0.0692 | +0.0615 | +0.0766 | *** | 500 |
| FAS-copeland vs unrepaired copeland | -0.0007 | -0.0012 | -0.0003 | *** | 500 |
| FAS-copeland vs BT | +0.0491 | +0.0438 | +0.0543 | *** | 500 |
| Borda vs win-rate | +0.0018 | +0.0011 | +0.0028 | *** | 500 |