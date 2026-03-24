# Bootstrap Summary — openai_scidocs_real_pairwise_q30_k15

n_bootstrap=1000, seed=42

| Analysis | Method A | Method B | n | Mean | CI low | CI high | Direction | CI excludes 0 |
|----------|----------|----------|---|------|--------|---------|-----------|---------------|
| ndcg_ci | llm_pairwise_copeland | — | 30 | 0.964899 | 0.938444 | 0.986035 | — | — |
| delta_ci | hybrid_rrf_repaired_copeland_a03 | hybrid_rrf_unrepaired_copeland_a03 | 30 | -0.000895 | -0.001934 | 0.000000 | negative | False |
| delta_ci | hybrid_rrf_repaired_balance_a03 | hybrid_rrf_unrepaired_balance_a03 | 30 | -0.000895 | -0.001934 | 0.000000 | negative | False |
