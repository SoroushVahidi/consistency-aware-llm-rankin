# Bootstrap Summary — openai_hotpotqa_real_run_q20_k15

n_bootstrap=2000, seed=42

| Analysis | Method A | Method B | n | Mean | CI low | CI high | Direction | CI excludes 0 |
|----------|----------|----------|---|------|--------|---------|-----------|---------------|
| ndcg_ci | llm_pairwise_copeland | — | 20 | 0.909597 | 0.822800 | 0.973519 | — | — |
| delta_ci | hybrid_rrf_repaired_copeland_a03 | hybrid_rrf_unrepaired_copeland_a03 | 20 | +0.000000 | 0.000000 | 0.000000 | neutral | False |
| delta_ci | hybrid_rrf_repaired_balance_a03 | hybrid_rrf_unrepaired_balance_a03 | 20 | +0.000000 | 0.000000 | 0.000000 | neutral | False |
