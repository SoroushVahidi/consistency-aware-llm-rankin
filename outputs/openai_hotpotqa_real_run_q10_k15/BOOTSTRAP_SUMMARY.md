# Bootstrap Summary — openai_hotpotqa_real_run_q10_k15

n_bootstrap=1000, seed=42

| Analysis | Method A | Method B | n | Mean | CI low | CI high | Direction | CI excludes 0 |
|----------|----------|----------|---|------|--------|---------|-----------|---------------|
| ndcg_ci | llm_pairwise_copeland | — | 10 | 0.892865 | 0.776186 | 0.979772 | — | — |
| delta_ci | hybrid_rrf_repaired_copeland_a03 | hybrid_rrf_unrepaired_copeland_a03 | 10 | -0.006932 | -0.020797 | 0.000000 | negative | False |
| delta_ci | hybrid_rrf_repaired_balance_a03 | hybrid_rrf_unrepaired_balance_a03 | 10 | -0.006932 | -0.020797 | 0.000000 | negative | False |
