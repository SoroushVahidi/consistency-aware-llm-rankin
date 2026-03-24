# Modern Baseline Comparison Results


## SCIDOCS

| Method | Source | nDCG@k | MAP@k | Prec@k | n |
|--------|--------|--------|-------|--------|---|
| borda | qrels | 1.0000 | 1.0000 | 0.2470 | 150 |
| bt_from_qrels | qrels | 1.0000 | 1.0000 | 0.2470 | 100 |
| fas_balance_score_prior_alpha_beta | qrels | 1.0000 | 1.0000 | 0.2470 | 150 |
| hybrid_rrf_balance_a05 | qrels | 1.0000 | 1.0000 | 0.2470 | 150 |
| hybrid_rrf_copeland_a03 | qrels | 1.0000 | 1.0000 | 0.2470 | 150 |
| hybrid_rrf_fas_regularized | qrels | 1.0000 | 1.0000 | 0.2470 | 150 |
| markov_from_qrels | qrels | 1.0000 | 1.0000 | 0.2470 | 100 |
| score_sum | qrels | 1.0000 | 1.0000 | 0.2470 | 150 |
| win_rate_from_qrels | qrels | 1.0000 | 1.0000 | 0.2470 | 100 |
| greedy_fas_copeland | qrels | 0.9992 | 0.9976 | 0.2470 | 150 |
| greedy_fas_weighted_balance | qrels | 0.9992 | 0.9976 | 0.2470 | 150 |
| hybrid_rrf_priority_topo_a03 | qrels | 0.9459 | 0.8642 | 0.2470 | 150 |
| greedy_fas_score_augmented_topological | qrels | 0.9441 | 0.8597 | 0.2470 | 150 |
| greedy_fas_topological | qrels | 0.9398 | 0.8492 | 0.2470 | 150 |
| pagerank | qrels | 0.9295 | 0.8769 | 0.2470 | 150 |
| cross_encoder | cross_encoder | 0.9083 | 0.7983 | 0.2470 | 100 |
| tournament_sort_from_qrels | qrels | 0.8190 | 0.6693 | 0.2470 | 100 |
| llm_listwise_mock | llm_listwise | 0.6474 | 0.4488 | 0.2470 | 100 |
| llm_pointwise_mock | llm_pointwise | 0.6061 | 0.3635 | 0.2470 | 100 |
| llm_pairwise_mock | llm_pairwise | 0.5817 | 0.3379 | 0.2470 | 100 |
