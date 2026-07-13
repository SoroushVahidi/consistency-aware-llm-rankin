# VALIDATION_CHECKS

## Results

- `no_duplicate_queries` on `openai_scidocs_real_pairwise_q50_k15`: PASS
- `help_harm_inactive_sum` on `openai_scidocs_real_pairwise_q50_k15`: PASS
- `ci_contains_mean` on `openai_scidocs_real_pairwise_q50_k15`: PASS
- `no_duplicate_queries` on `openai_hotpotqa_real_run_q20_k15`: PASS
- `help_harm_inactive_sum` on `openai_hotpotqa_real_run_q20_k15`: PASS
- `ci_contains_mean` on `openai_hotpotqa_real_run_q20_k15`: PASS
- `no_duplicate_queries` on `openai_fiqa_real_run_q20_k15`: PASS
- `help_harm_inactive_sum` on `openai_fiqa_real_run_q20_k15`: PASS
- `ci_contains_mean` on `openai_fiqa_real_run_q20_k15`: PASS
- `no_duplicate_queries` on `gemini_scidocs_real_pilot`: PASS
- `help_harm_inactive_sum` on `gemini_scidocs_real_pilot`: PASS
- `ci_contains_mean` on `gemini_scidocs_real_pilot`: PASS
- `no_duplicate_queries` on `openai_scidocs_real_run_q20_k15`: PASS
- `help_harm_inactive_sum` on `openai_scidocs_real_run_q20_k15`: PASS
- `ci_contains_mean` on `openai_scidocs_real_run_q20_k15`: PASS
- `no_duplicate_queries` on `openai_scidocs_real_pairwise_q30_k15`: PASS
- `help_harm_inactive_sum` on `openai_scidocs_real_pairwise_q30_k15`: PASS
- `ci_contains_mean` on `openai_scidocs_real_pairwise_q30_k15`: PASS
- `no_duplicate_queries` on `openai_hotpotqa_real_run_q10_k15`: PASS
- `help_harm_inactive_sum` on `openai_hotpotqa_real_run_q10_k15`: PASS
- `ci_contains_mean` on `openai_hotpotqa_real_run_q10_k15`: PASS
- `no_duplicate_queries` on `openai_smoke_scidocs_q1_k5`: PASS
- `help_harm_inactive_sum` on `openai_smoke_scidocs_q1_k5`: PASS
- `ci_contains_mean` on `openai_smoke_scidocs_q1_k5`: PASS
- `provider_total_matches_subtotals` on `openai-primary`: PASS
- `common_query_file_present` on `policy_sensitivity_common_queries.csv`: PASS
- `forward_reverse_doc_identity` on `not_applicable_no_debias_runs`: PASS

## Notes

- Alternative-policy common-query sensitivity is marked not reproducible rather than failing validation.
- Forward/reverse document-identity validation is not applicable because no auditable debiased pairwise runs are present.
