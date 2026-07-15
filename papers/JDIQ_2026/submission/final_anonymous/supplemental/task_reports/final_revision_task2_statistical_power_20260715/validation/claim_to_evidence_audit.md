# Claim-to-Evidence Audit

| Claim | Value | Evidence |
| --- | --- | --- |
| Task 1 larger-pool rerun changes top-k membership when P>k. | `"0.105776"` | `reports/final_revision_task1_pool_cutoff_20260715/validation/pool_cutoff_verification.json` |
| Task 2 final full and active ms1 families have zero Holm/BH/BY-significant repaired-vs-unrepaired nDCG cells. | `{"active_bh": 0, "active_by": 0, "active_holm": 0, "full_bh": 0, "full_by": 0, "full_holm": 0}` | `reports/final_revision_task2_statistical_power_20260715/manifests/task2_analysis_summary.json` |
| Canonical SciDocs ms1 Copeland graph interval sensitivity changes with bootstrap construction but not the multiplicity conclusion. | `{"basic_low": -0.00020286461548095144, "bca_low": 0.003268246600278589}` | `reports/final_revision_task2_statistical_power_20260715/tables/interval_method_comparison.csv` |
| FiQA and BRIGHT canonical pools have no eligible judged different-grade candidate pairs under the final qrels-reference rule. | `{"bright_zero_pair_rate": 1.0, "fiqa_zero_pair_rate": 1.0}` | `reports/final_revision_task2_statistical_power_20260715/tables/qrels_reference_eligibility_summary.csv` |
| The active larger-pool ms1 family is underpowered for effects as small as the typical observed mean delta. | `{"median_abs_observed_mean": 0.0035754186474477004, "median_holm80_mde": 0.02067685223390709}` | `reports/final_revision_task2_statistical_power_20260715/tables/mde_per_cell.csv` |
| The original canonical active ms1 design had similar observed means but lower, still nontrivial Holm-adjusted MDE thresholds. | `{"median_abs_observed_mean": 0.003993045230030219, "median_holm80_mde": 0.015274217481269146}` | `reports/final_revision_task2_statistical_power_20260715/tables/mde_per_cell.csv` |
| Cross-protocol dependence-robust sensitivity does not preserve the lone active-family negative FiQA hit seen under Holm/BH. | `{"bh": 0.023997600239976005, "by": 0.1288399549009914, "holm": 0.023997600239976005}` | `reports/final_revision_task2_statistical_power_20260715/tables/cross_protocol_statistical_tests.csv` |
| Baseline comparisons remain descriptive only. | `["descriptive_only"]` | `reports/final_revision_task2_statistical_power_20260715/tables/baseline_claim_audit.csv` |
