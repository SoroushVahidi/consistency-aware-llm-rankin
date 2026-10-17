# Schema and data dictionary

`data/novel_ndcg.csv.gz` is UTF-8 CSV with one row per `(benchmark, regime, config_id, pool_size, metric_cutoff, unit_id, method_key)`. There are 93,504 unique keys; no null nDCG values.

| Column | Type | Meaning |
|---|---|---|
| `record_id` | 64-character hex | SHA-256 of the canonical JSON scientific-key tuple; stable row identity. |
| `benchmark` | enum | `scidocs`, `fiqa`, `hotpotqa`, or `bright`. |
| `unit_id` | 64-character hex | SHA-256 of UTF-8 `ranking-poolcutoff-v1\0` + benchmark + `\0` + original query ID. Raw IDs are absent. |
| `regime` | enum | `ms2`, `ms1`, or `ms1_drop_mutual`. |
| `pool_policy_id` | string | `rrf_union_topk` in this study. |
| `pool_size` | integer | Requested candidate-pool size `P`. |
| `metric_cutoff` | integer | nDCG cutoff `k`, with `k ≤ P`. |
| `config_id` | string | `pool{P}_ndcg{k}`. |
| `method_key` | enum | One of the 16 methods enumerated in the dataset card and validator. |
| `metric_name` | string | `ndcg`. |
| `ndcg_value` | finite float | Candidate-set-relative nDCG@`metric_cutoff` in [0,1]. |
| `run_id` | string | Logical cell ID `greedy-20260714/{benchmark}/{regime}/{config_id}`; 66 values. |
| `protocol_id` | string | `minmax_raw_matched`. |
| `replicate_id`, `seed` | empty | No independent replicate or run seed recorded; summary-test seeds do not count. |
| `comparator_method_key` | string/empty | `prior_only` for non-prior rows; empty for `prior_only`. Comparator values occur as separate rows. |

`data/configurations.csv` has one row per `run_id` and gives the calibration (`minmax_query_ranker`), threshold mode (`retention_matched`), vote thresholds by retrieval ranker, aggregate threshold, minimum support, mutual-edge setting, and source/observed/excluded query counts. It is necessary for interpreting between-cell comparisons.

`comparison/public_vs_new.csv.gz` has one row per `record_id`: a four-way publication class, exact public full-key match count, a flag for older query/method/numeric coincidences **without matching protocol identity**, and the comparison scope. Every curated row is classed `NEW_MEASUREMENT_ABSENT_FROM_CHECKED_PUBLIC_RELEASES`; 107 rows have such loose numeric coincidences. These are not counted as identical observations.

The private `source_map.csv.gz` maps each `record_id` to the raw query ID, original per-run CSV path and data-row number, source-row hash, and paired JSONL path. It is **not** part of the proposed public supplement.
