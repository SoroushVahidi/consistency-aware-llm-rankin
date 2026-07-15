# Method Improvement Audit Final Report

Generated: 2026-07-11 21:16:27

## 1. Executive Summary

- This workspace preserves canonical manuscript evidence and performs all new work under a separate rerun and analysis tree.
- Canonical baseline package: `outputs/pub_vote_cmp_all4/paper_package/` (mirrored by `outputs/final_jis_package/`).
- The canonical package lacks committed per-query run trees, so this audit regenerates a workspace-local logged rerun to diagnose failure paths.

## 2. Canonical Baseline Description

- See `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/BASELINE_AND_SCOPE.md`.

## 3. Failure-Path Findings

- Per-query CSV: `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/failure_path_per_query.csv`
- Summary CSV: `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/failure_path_summary.csv`

## 4. Candidate-Frontier And Oracle Findings

- Per-query frontier CSV: `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/candidate_frontier_per_query.csv`
- Win-rate CSV: `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/candidate_method_win_rates.csv`

## 5. Extraction And Fusion Findings

- Extraction/fusion results: `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/extraction_fusion_results.csv`
- Alpha sweep: `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/alpha_sweep_results.csv`

## 6. Repair-Method Findings

- Repair comparison CSV: `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/repair_method_results.csv`
- Repair per-query CSV: `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/repair_method_per_query.csv`

## 7. Graph-Construction Findings

- Graph construction CSV: `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/graph_construction_results.csv`
- Ranker correlation CSV: `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/ranker_correlation_matrix.csv`

## 8. Regime-Aware Policy Findings

- Policy results CSV: `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/regime_policy_results.csv`

## 9. Strongest Proposed Algorithm

- Deferred to the completed CSV evidence above; this report does not invent a winner before all phase outputs are inspected.

## 10. Strongest Negative Result

- If canonical Copeland-hybrid repair remains neutral while graph-only Markov or other extractors show sensitivity, the main weakness is extraction/fusion rather than repair alone.

## 11. Remaining Unknowns

- External repair methods may still require tighter query-level runtime control to scale beyond the cyclic subset analyzed here.
- Confidence-weighted fusion is implemented as a simple runtime-legal heuristic, not a manuscript-ready final formula.

## 12. Exact Experiments Completed

- phase0: completed
- phase1_failure: failed
- phase1_inputs: completed
- phase2_frontier: completed
- phase3_fusion: completed
- phase4_repair: completed
- phase5_graph: failed
- phase6_policy: completed
- phase7_contrib: completed

## 13. Exact Experiments That Could Not Be Completed And Why

- phase1_failure / Failure-path decomposition: KeyError — 'ranked_doc_ids'
- phase5_graph / Pre-repair graph construction audit: KeyError — 'ranked_doc_ids'

## 14. Full Artifact Index

- phase0:
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/BASELINE_AND_SCOPE.md`
  - `outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv`
  - `outputs/pub_vote_cmp_all4/paper_package/tables/table_bootstrap_delta_ndcg.csv`
  - `outputs/pub_vote_cmp_all4/paper_package/tables/table_consistency_qrels_bew.csv`
- phase1_inputs:
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/canonical_rerun_manifest.json`
- phase2_frontier:
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/candidate_frontier_per_query.csv`
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/candidate_method_win_rates.csv`
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/oracle_gap_summary.csv`
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/oracle_gap_by_dataset.csv`
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/CANDIDATE_FRONTIER_REPORT.md`
- phase3_fusion:
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/extraction_fusion_results.csv`
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/extraction_fusion_per_query.csv`
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/alpha_sweep_results.csv`
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/fusion_suppression_summary.csv`
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/EXTRACTION_AND_FUSION_REPORT.md`
- phase4_repair:
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/repair_method_results.csv`
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/repair_method_per_query.csv`
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/repair_runtime_summary.csv`
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/REPAIR_METHOD_REPORT.md`
- phase6_policy:
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/regime_policy_rules.md`
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/regime_policy_per_query.csv`
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/regime_policy_results.csv`
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/REGIME_AWARE_POLICY_REPORT.md`
- phase7_contrib:
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/contribution_scorecard.csv`
  - `/home/soroush/consistency-aware-llm-rankin/experiments/method_improvement_audit_20260711_205733/phase_reports/CONTRIBUTION_ANALYSIS.md`

## 15. Recommended Next Research Action

- Use the completed CSV outputs to decide whether to pursue extraction/fusion redesign, graph construction cleanup, or a limited repair-method upgrade before manuscript preparation.

## Failure Log

- total recorded failures: 2
