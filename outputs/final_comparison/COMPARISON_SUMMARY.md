# Modern Baseline Comparison Results


## SCIDOCS

| Method | Source | nDCG@k | MAP@k | Prec@k | n |
|--------|--------|--------|-------|--------|---|
| borda | qrels | 1.0000 | 1.0000 | 0.2462 | 1000 |
| bt_from_qrels | qrels | 1.0000 | 1.0000 | 0.2462 | 500 |
| fas_balance_score_prior_alpha_beta | qrels | 1.0000 | 0.9999 | 0.2462 | 1000 |
| hybrid_rrf_balance_a05 | qrels | 1.0000 | 1.0000 | 0.2462 | 1000 |
| hybrid_rrf_copeland_a03 | qrels | 1.0000 | 1.0000 | 0.2462 | 1000 |
| hybrid_rrf_fas_regularized | qrels | 1.0000 | 1.0000 | 0.2462 | 1000 |
| markov_from_qrels | qrels | 1.0000 | 1.0000 | 0.2462 | 500 |
| score_sum | qrels | 1.0000 | 1.0000 | 0.2462 | 1000 |
| win_rate_from_qrels | qrels | 1.0000 | 1.0000 | 0.2462 | 500 |
| greedy_fas_copeland | qrels | 0.9994 | 0.9983 | 0.2462 | 1000 |
| greedy_fas_weighted_balance | qrels | 0.9994 | 0.9983 | 0.2462 | 1000 |
| hybrid_rrf_priority_topo_a03 | qrels | 0.9596 | 0.8981 | 0.2462 | 1000 |
| greedy_fas_score_augmented_topological | qrels | 0.9586 | 0.8956 | 0.2462 | 1000 |
| greedy_fas_topological | qrels | 0.9552 | 0.8872 | 0.2462 | 1000 |
| pagerank | qrels | 0.9478 | 0.9060 | 0.2462 | 1000 |
| cross_encoder | cross_encoder | 0.8977 | 0.7807 | 0.2462 | 500 |
| tournament_sort_from_qrels | qrels | 0.8059 | 0.6518 | 0.2462 | 500 |

## HOTPOTQA

| Method | Source | nDCG@k | MAP@k | Prec@k | n |
|--------|--------|--------|-------|--------|---|
| borda | qrels | 1.0000 | 1.0000 | 0.1375 | 994 |
| bt_from_qrels | qrels | 1.0000 | 1.0000 | 0.1375 | 497 |
| hybrid_rrf_fas_regularized | qrels | 1.0000 | 1.0000 | 0.1375 | 994 |
| markov_from_qrels | qrels | 1.0000 | 1.0000 | 0.1375 | 497 |
| score_sum | qrels | 1.0000 | 1.0000 | 0.1375 | 994 |
| tournament_sort_from_qrels | qrels | 1.0000 | 1.0000 | 0.1375 | 497 |
| win_rate_from_qrels | qrels | 1.0000 | 1.0000 | 0.1375 | 497 |
| hybrid_rrf_balance_a05 | qrels | 0.9999 | 0.9998 | 0.1375 | 994 |
| hybrid_rrf_copeland_a03 | qrels | 0.9999 | 0.9998 | 0.1375 | 994 |
| fas_balance_score_prior_alpha_beta | qrels | 0.9988 | 0.9980 | 0.1375 | 994 |
| greedy_fas_copeland | qrels | 0.9948 | 0.9920 | 0.1375 | 994 |
| greedy_fas_weighted_balance | qrels | 0.9948 | 0.9920 | 0.1375 | 994 |
| pagerank | qrels | 0.9900 | 0.9841 | 0.1375 | 994 |
| cross_encoder | cross_encoder | 0.9499 | 0.9241 | 0.1392 | 498 |
| hybrid_rrf_priority_topo_a03 | qrels | 0.8388 | 0.7761 | 0.1375 | 994 |
| greedy_fas_score_augmented_topological | qrels | 0.8387 | 0.7760 | 0.1375 | 994 |
| greedy_fas_topological | qrels | 0.8386 | 0.7756 | 0.1375 | 994 |

## BRIGHT

| Method | Source | nDCG@k | MAP@k | Prec@k | n |
|--------|--------|--------|-------|--------|---|
| borda | qrels | 1.0000 | 1.0000 | 0.2040 | 142 |
| bt_from_qrels | qrels | 1.0000 | 1.0000 | 0.2040 | 71 |
| fas_balance_score_prior_alpha_beta | qrels | 1.0000 | 0.9999 | 0.2040 | 142 |
| hybrid_rrf_balance_a05 | qrels | 1.0000 | 1.0000 | 0.2040 | 142 |
| hybrid_rrf_copeland_a03 | qrels | 1.0000 | 1.0000 | 0.2040 | 142 |
| hybrid_rrf_fas_regularized | qrels | 1.0000 | 1.0000 | 0.2040 | 142 |
| markov_from_qrels | qrels | 1.0000 | 1.0000 | 0.2040 | 71 |
| score_sum | qrels | 1.0000 | 1.0000 | 0.2040 | 142 |
| win_rate_from_qrels | qrels | 1.0000 | 1.0000 | 0.2040 | 71 |
| greedy_fas_copeland | qrels | 0.9989 | 0.9974 | 0.2040 | 142 |
| greedy_fas_weighted_balance | qrels | 0.9989 | 0.9974 | 0.2040 | 142 |
| pagerank | qrels | 0.9704 | 0.9553 | 0.2040 | 142 |
| cross_encoder | cross_encoder | 0.8877 | 0.8424 | 0.7131 | 197 |
| hybrid_rrf_priority_topo_a03 | qrels | 0.8590 | 0.7920 | 0.2040 | 142 |
| greedy_fas_score_augmented_topological | qrels | 0.8582 | 0.7906 | 0.2040 | 142 |
| greedy_fas_topological | qrels | 0.8562 | 0.7863 | 0.2040 | 142 |
| tournament_sort_from_qrels | qrels | 0.6999 | 0.5776 | 0.2040 | 71 |
