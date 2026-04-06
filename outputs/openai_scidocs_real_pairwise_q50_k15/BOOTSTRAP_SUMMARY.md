# Bootstrap Summary — openai_scidocs_real_pairwise_q50_k15

n_bootstrap=2000, seed=42

| Analysis | Method A | Method B | n | Mean | CI low | CI high | Direction | CI excludes 0 |
|----------|----------|----------|---|------|--------|---------|-----------|---------------|
| ndcg_ci | llm_pairwise_copeland | — | 50 | 0.974890 | 0.957949 | 0.988180 | — | — |
| delta_ci | hybrid_rrf_repaired_copeland_a03 | hybrid_rrf_unrepaired_copeland_a03 | 50 | -0.000953 | -0.001905 | -0.000208 | negative | True |
| delta_ci | hybrid_rrf_repaired_balance_a03 | hybrid_rrf_unrepaired_balance_a03 | 50 | -0.000953 | -0.001905 | -0.000208 | negative | True |
