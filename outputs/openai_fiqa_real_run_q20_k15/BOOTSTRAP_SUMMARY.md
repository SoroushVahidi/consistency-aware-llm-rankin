# Bootstrap Summary — openai_fiqa_real_run_q20_k15

n_bootstrap=1000, seed=42

| Analysis | Method A | Method B | n | Mean | CI low | CI high | Direction | CI excludes 0 |
|----------|----------|----------|---|------|--------|---------|-----------|---------------|
| ndcg_ci | llm_pairwise_copeland | — | 10 | 1.000000 | 1.000000 | 1.000000 | — | — |
| delta_ci | hybrid_rrf_repaired_copeland_a03 | hybrid_rrf_unrepaired_copeland_a03 | 10 | +0.000000 | 0.000000 | 0.000000 | neutral | False |
| delta_ci | hybrid_rrf_repaired_balance_a03 | hybrid_rrf_unrepaired_balance_a03 | 10 | +0.000000 | 0.000000 | 0.000000 | neutral | False |
