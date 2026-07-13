# VALIDATION_CHECKS

All checks below were computed programmatically against this audit's own
output CSVs and the stored `query_level_full_records.jsonl`. **All checks
pass.**

| Check | Result | Detail |
|---|---|---|
| No duplicated (dataset, vote_regime, query_id) records in the 200-record mechanical corpus | **PASS** | 200 rows, 200 unique keys |
| Mechanical 200-record total reproduces manuscript's regime subtotals | **PASS** | 62 (ms2) + 69 (ms1_drop_mutual) + 69 (ms1) = 200 |
| help + harm + inactive = regime total, `ms1` | **PASS** | help=1, harm=1, inactive=67, total=69 -- **independently re-derives the manuscript's exact quoted numbers from stored data** |
| help + harm + inactive = regime total, `ms2` | **PASS** | help=0, harm=0, inactive=62, total=62 |
| help + harm + inactive = regime total, `ms1_drop_mutual` | **PASS** | help=0, harm=0, inactive=69, total=69 |
| help + harm + inactive = usable total, every (provider, dataset, policy) group in `policy_sensitivity_full.csv` | **PASS** | 0 violations across 30 groups |
| Common-query analysis (`policy_sensitivity_common_queries.csv`) uses an identical query set across all 5 policies x 2 providers | **PASS** | 10 groups, all size 196, all equal as sets |
| Forward/reverse mapping (`forward_reverse_consistency.csv`) keys on document identity (`doc_a_id`/`doc_b_id`), not on the A/B label, which is presentation-order-dependent and would silently misattribute agreement | **PASS** | verified by construction and spot-checked |
| Every bootstrap 95% CI (`_bootstrap_summary.csv`) contains its own point estimate | **PASS** | 0 violations across 30 rows (11 non-degenerate; 19 degenerate [0,0] rows where repair was inactive for every query in the group, discussed in POLICY_SENSITIVITY_REPORT.md) |

## What this validation does and does not establish

- It confirms this audit's own P0 reparse and the mechanical-graph re-read
  are **internally consistent** and **reproduce the manuscript's existing
  62/69/69/help=1/harm=1 numbers exactly** from stored data -- i.e. those
  specific manuscript numbers are correct and reproducible as stated, which
  is a "resolved" item, not a correction.
- It does **not** by itself validate the manuscript's *prose framing* of
  those numbers (i.e., attributing them to "Cohere/Azure judgments") -- that
  is a separate, narrative-level finding documented in
  PROVIDER_COUNT_RESOLUTION.md and is not a "validation check" in the
  numeric sense used here.
- Per the task's stopping rule ("stop if validation fails"): **no failures
  occurred, so the audit proceeded to the final report and commit steps.**
