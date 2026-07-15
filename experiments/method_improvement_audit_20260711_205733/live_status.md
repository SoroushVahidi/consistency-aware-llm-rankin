# Method Improvement Audit

- updated_at: 2026-07-11 21:16:27
- current_phase: Contribution analysis
- active_task: Contribution analysis
- completed_tasks: 8
- queries_processed: 0
- failures: 2
- workspace: /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733
- final_report: /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/FINAL_REPORT.md

## Completed Tasks

- workspace initialized
- Canonical baseline identification
- Canonical logged rerun input generation
- Candidate frontier and oracle analysis
- Extraction and fusion audit
- Repair-method comparison
- Regime-aware transparent policy feasibility
- Contribution analysis

## Latest Provisional Findings

- Canonical evidence package confirmed as outputs/pub_vote_cmp_all4/paper_package.
- Per-query canonical run trees are absent; a workspace-local logged rerun is required for failure-path analysis.
- Offline score generation and canonical vote regeneration are feasible with local data and local models.
- Natural-query extraction audit logged 0 repaired/unrepaired comparisons across graph-only and fused methods.

## Output Paths

- phase0:
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/BASELINE_AND_SCOPE.md
  - outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv
  - outputs/pub_vote_cmp_all4/paper_package/tables/table_bootstrap_delta_ndcg.csv
  - outputs/pub_vote_cmp_all4/paper_package/tables/table_consistency_qrels_bew.csv
- phase1_inputs:
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/canonical_rerun_manifest.json
- phase2_frontier:
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/candidate_frontier_per_query.csv
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/candidate_method_win_rates.csv
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/oracle_gap_summary.csv
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/oracle_gap_by_dataset.csv
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/CANDIDATE_FRONTIER_REPORT.md
- phase3_fusion:
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/extraction_fusion_results.csv
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/extraction_fusion_per_query.csv
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/alpha_sweep_results.csv
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/fusion_suppression_summary.csv
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/EXTRACTION_AND_FUSION_REPORT.md
- phase4_repair:
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/repair_method_results.csv
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/repair_method_per_query.csv
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/repair_runtime_summary.csv
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/REPAIR_METHOD_REPORT.md
- phase6_policy:
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/regime_policy_rules.md
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/regime_policy_per_query.csv
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/regime_policy_results.csv
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/REGIME_AWARE_POLICY_REPORT.md
- phase7_contrib:
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/contribution_scorecard.csv
  - /home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/CONTRIBUTION_ANALYSIS.md
