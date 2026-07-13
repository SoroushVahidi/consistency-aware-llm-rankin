# RESPONSE_QUALITY_REPORT

This report summarizes what can and cannot be recovered about stored response quality from the committed artifact set.

| Experiment                                               | Prompt mode | Total | Raw text available | Auditable ambiguity/fallback? | Notes                        |
| -------------------------------------------------------- | ----------- | ----- | ------------------ | ----------------------------- | ---------------------------- |
| openai_scidocs_real_pairwise_q50_k15                     | pairwise    | 5250  | 0                  | no                            | Raw text not preserved.      |
| openai_hotpotqa_real_run_q20_k15                         | pairwise    | 900   | 0                  | no                            | Raw text not preserved.      |
| openai_fiqa_real_run_q20_k15                             | pairwise    | 46    | 0                  | no                            | Raw text not preserved.      |
| gemini_scidocs_real_pilot                                | pairwise    | 491   | 0                  | no                            | Raw text not preserved.      |
| openai_scidocs_real_run_q20_k15                          | pairwise    | 2100  | 0                  | no                            | Raw text not preserved.      |
| openai_scidocs_real_pairwise_q30_k15                     | pairwise    | 3150  | 0                  | no                            | Raw text not preserved.      |
| openai_hotpotqa_real_run_q10_k15                         | pairwise    | 450   | 0                  | no                            | Raw text not preserved.      |
| openai_smoke_scidocs_q1_k5                               | pairwise    | 10    | 0                  | no                            | Raw text not preserved.      |
| openai_scidocs_real_pointwise_q20_k15                    | pointwise   | 300   | 0                  | no                            | Raw text not preserved.      |
| openai_hotpotqa_real_pointwise_q10_k15                   | pointwise   | 100   | 0                  | no                            | Raw text not preserved.      |
| openai_robustness_checks/scidocs_pointwise_temp03_q5_k15 | pointwise   | 75    | 0                  | no                            | Raw text not preserved.      |
| openai_scidocs_real_listwise_q20_k15                     | listwise    | 20    | 20                 | yes                           | Listwise raw text preserved. |
| openai_hotpotqa_real_listwise_q10_k15                    | listwise    | 10    | 10                 | yes                           | Listwise raw text preserved. |
| openai_robustness_checks/scidocs_listwise_temp03_q5_k15  | listwise    | 5     | 5                  | yes                           | Listwise raw text preserved. |

## Findings

- Pairwise OpenAI/Gemini responses cannot be partitioned into exact A/B, verbose-valid, ambiguous, malformed, or fallback-derived subsets because raw response texts were not committed.
- Pointwise OpenAI responses likewise cannot be reclassified retrospectively because only parsed numeric scores were committed.
- Listwise OpenAI responses are auditable and, in the committed runs, are stored as direct ranking strings.
- Retry distributions are not reconstructible from committed logs; aggregate retry-capable settings exist in code, but per-response retry histories were not recorded.
