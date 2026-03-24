# Bootstrap CIs — SCIDOCS (flip_prob=0.3)

n_bootstrap=2000, seed=42, metric=ndcg_at_k

| Comparison | Δ nDCG | CI 95% low | CI 95% high | Sig. | n |
|------------|--------|------------|-------------|------|---|
| score_sum vs FAS topological | +0.1527 | +0.1423 | +0.1633 | *** | 500 |
| score_sum vs Bradley-Terry | +0.1669 | +0.1574 | +0.1766 | *** | 500 |
| score_sum vs win-rate | +0.0588 | +0.0512 | +0.0672 | *** | 500 |
| score_sum vs tournament sort | +0.3425 | +0.3302 | +0.3546 | *** | 500 |
| FAS-balance vs BT | +0.1268 | +0.1172 | +0.1364 | *** | 500 |
| FAS-balance vs win-rate | +0.0187 | +0.0115 | +0.0263 | *** | 500 |
| FAS-balance vs Markov | -0.0147 | -0.0231 | -0.0067 | *** | 500 |
| FAS-copeland vs unrepaired copeland | -0.0243 | -0.0301 | -0.0194 | *** | 500 |
| FAS-copeland vs BT | +0.1268 | +0.1172 | +0.1364 | *** | 500 |
| Borda vs win-rate | +0.0588 | +0.0512 | +0.0672 | *** | 500 |