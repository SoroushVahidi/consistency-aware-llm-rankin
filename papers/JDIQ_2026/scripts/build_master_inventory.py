#!/usr/bin/env python3
"""Build MASTER_EVIDENCE_INVENTORY.csv for JDIQ manuscript workspace (read-only)."""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1] / "MASTER_EVIDENCE_INVENTORY.csv"

SKIP = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules", ".pixi"}

# Curated high-value artifacts with publication metadata
CURATED: list[dict] = [
    # Canonical results
    {"artifact": "table_graph_ndcg_and_consistency", "location": "outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv",
     "description": "Four-dataset graph consistency and nDCG summary by vote regime", "publication_quality": "high",
     "recommended_usage": "main_table", "manuscript_section": "Results", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "table_bootstrap_delta_ndcg", "location": "outputs/pub_vote_cmp_all4/paper_package/tables/table_bootstrap_delta_ndcg.csv",
     "description": "Bootstrap repair deltas (2000 reps) per dataset×variant×pair", "publication_quality": "high",
     "recommended_usage": "main_table", "manuscript_section": "Results", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "table_consistency_qrels_bew", "location": "outputs/pub_vote_cmp_all4/paper_package/tables/table_consistency_qrels_bew.csv",
     "description": "BEW/PIC consistency metrics pre/post repair vs qrels", "publication_quality": "high",
     "recommended_usage": "main_table", "manuscript_section": "Results", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "pub_vote_cmp_all4_package", "location": "outputs/pub_vote_cmp_all4/paper_package/",
     "description": "Canonical four-dataset publication evidence package", "publication_quality": "high",
     "recommended_usage": "canonical_source", "manuscript_section": "Methods;Results", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "final_jis_package", "location": "outputs/final_jis_package/",
     "description": "Packaged JIS-oriented tables aligned with all4", "publication_quality": "high",
     "recommended_usage": "reference", "manuscript_section": "Results", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "final_baseline_comparison", "location": "experiments/final_method_gap_audit_20260711_221113/task3/final_baseline_comparison.csv",
     "description": "Pooled 1020 query×regime baseline grid (prior, CombSUM, RRF, proposed, etc.)", "publication_quality": "high",
     "recommended_usage": "main_table", "manuscript_section": "Results;Discussion", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "repair_comparison_real", "location": "experiments/final_method_gap_audit_20260711_221113/task2/repair_comparison_real.csv",
     "description": "Exact vs greedy vs stronger repair on real pooled records", "publication_quality": "high",
     "recommended_usage": "supplementary_table", "manuscript_section": "Results", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "extraction_fusion_complete", "location": "experiments/final_method_gap_audit_20260711_221113/task1/extraction_fusion_complete.csv",
     "description": "Extraction and fusion sensitivity analysis", "publication_quality": "medium-high",
     "recommended_usage": "supplementary_table", "manuscript_section": "Results;Discussion", "confidence": "medium", "canonical": "yes", "historical": "no", "stale": "no"},
    # Failure analysis
    {"artifact": "manual_failure_summary", "location": "experiments/failure_class_audit_20260711_212157/phase_reports/manual_failure_summary.csv",
     "description": "Manual failure taxonomy frequencies (repair_inactive 64%, tail_only 21%)", "publication_quality": "high",
     "recommended_usage": "main_figure;main_table", "manuscript_section": "Results;Discussion", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "failure_mining_v3_package", "location": "reports/failure_mining_llm_v3/",
     "description": "Full failure-mining with multi-provider LLM judgments (Cohere, Azure)", "publication_quality": "high",
     "recommended_usage": "supplementary_data", "manuscript_section": "Methods;Supplement", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "failure_mining_canonical", "location": "reports/failure_mining/",
     "description": "Mechanical-vote failure mining (no LLM cost)", "publication_quality": "high",
     "recommended_usage": "supplementary_data", "manuscript_section": "Methods;Supplement", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "failure_mining_llm_v2", "location": "reports/failure_mining_llm_v2/",
     "description": "Superseded failure-mining LLM run", "publication_quality": "low",
     "recommended_usage": "do_not_use", "manuscript_section": "n/a", "confidence": "low", "canonical": "no", "historical": "yes", "stale": "yes"},
    # CARB / data
    {"artifact": "carb_schema_proposal", "location": "experiments/created_data_audit_20260711_232004/phase10/PROPOSED_DATASET_SCHEMA.md",
     "description": "CARB v0.1 unified schema (1020 query×regime, 366 methods)", "publication_quality": "high",
     "recommended_usage": "supplementary_resource", "manuscript_section": "Data Availability;Supplement", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "carb_release_structure", "location": "experiments/created_data_audit_20260711_232004/phase10/PROPOSED_RELEASE_STRUCTURE.md",
     "description": "Proposed public release layout for CARB", "publication_quality": "medium-high",
     "recommended_usage": "supplementary_resource", "manuscript_section": "Data Availability", "confidence": "medium", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "dataset_contribution_scorecard", "location": "experiments/created_data_audit_20260711_232004/phase9/dataset_contribution_scorecard.csv",
     "description": "Dataset publication potential scoring", "publication_quality": "medium",
     "recommended_usage": "internal_planning", "manuscript_section": "n/a", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "global_feature_dictionary", "location": "experiments/created_data_audit_20260711_232004/phase6/global_feature_dictionary.csv",
     "description": "14+ documented feature groups for CARB records", "publication_quality": "high",
     "recommended_usage": "supplementary_table", "manuscript_section": "Supplement", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    # Real LLM
    {"artifact": "openai_cross_dataset_summary", "location": "outputs/openai_real_llm_cross_dataset_summary.md",
     "description": "Consolidated real OpenAI pairwise runs (SciDocs 50q, HotpotQA 20q, FiQA 10q)", "publication_quality": "medium",
     "recommended_usage": "appendix_table", "manuscript_section": "Results;Limitations", "confidence": "medium", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "openai_scidocs_pairwise_q50", "location": "outputs/openai_scidocs_real_pairwise_q50_k15/",
     "description": "Real OpenAI pairwise SciDocs 50-query pilot", "publication_quality": "medium",
     "recommended_usage": "appendix", "manuscript_section": "Results", "confidence": "medium", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "openai_hotpotqa_q20", "location": "outputs/openai_hotpotqa_real_run_q20_k15/",
     "description": "Real OpenAI HotpotQA 20-query run", "publication_quality": "medium",
     "recommended_usage": "appendix", "manuscript_section": "Results", "confidence": "medium", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "openai_fiqa_q20", "location": "outputs/openai_fiqa_real_run_q20_k15/",
     "description": "Real OpenAI FiQA run (10 usable queries)", "publication_quality": "low-medium",
     "recommended_usage": "appendix", "manuscript_section": "Results;Limitations", "confidence": "low", "canonical": "yes", "historical": "no", "stale": "no"},
    # Audits
    {"artifact": "publication_readiness_audit", "location": "experiments/publication_readiness_audit_20260711_233629/",
     "description": "Full publication readiness synthesis (11 phases)", "publication_quality": "high",
     "recommended_usage": "authoring_blueprint", "manuscript_section": "n/a", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "reviewer_response_audit", "location": "experiments/reviewer_response_state_audit_20260711_214959/",
     "description": "Reviewer criticism status and claim discipline", "publication_quality": "high",
     "recommended_usage": "authoring_blueprint", "manuscript_section": "Introduction;Limitations", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "created_data_audit", "location": "experiments/created_data_audit_20260711_232004/",
     "description": "Repository-wide data provenance and CARB assessment", "publication_quality": "high",
     "recommended_usage": "data_availability", "manuscript_section": "Data Availability", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "failure_class_audit", "location": "experiments/failure_class_audit_20260711_212157/",
     "description": "Failure taxonomy, counterfactuals, regret decomposition", "publication_quality": "high",
     "recommended_usage": "main_results", "manuscript_section": "Results;Discussion", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "method_improvement_audit", "location": "experiments/method_improvement_audit_20260711_205733/",
     "description": "Regime policy, repair method, baseline scope analysis", "publication_quality": "medium-high",
     "recommended_usage": "discussion", "manuscript_section": "Discussion", "confidence": "medium", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "counterfactual_feasibility", "location": "experiments/counterfactual_generation_feasibility_/",
     "description": "Counterfactual repair impact feasibility (40 attempts, 7 invalid)", "publication_quality": "medium",
     "recommended_usage": "supplementary", "manuscript_section": "Methods;Supplement", "confidence": "medium", "canonical": "yes", "historical": "no", "stale": "no"},
    # Historical / stale
    {"artifact": "pub_vote_cmp_v2", "location": "outputs/pub_vote_cmp_v2/paper_package/",
     "description": "Two-dataset publication suite (conflicts with all4)", "publication_quality": "low",
     "recommended_usage": "do_not_use", "manuscript_section": "n/a", "confidence": "low", "canonical": "no", "historical": "yes", "stale": "yes"},
    {"artifact": "q1_journal_package", "location": "outputs/q1_journal_package/",
     "description": "Q1 tables built from v2 by default", "publication_quality": "low",
     "recommended_usage": "do_not_use", "manuscript_section": "n/a", "confidence": "low", "canonical": "no", "historical": "yes", "stale": "yes"},
    {"artifact": "ijcs_manuscript_zip", "location": "Consistency_Aware_Reranking_via_Preference_Graph_Repair__Structural_Gains_and_Conditional_Retrieval_Effects_IJCS.zip",
     "description": "Rejected IJCS submission archive", "publication_quality": "low",
     "recommended_usage": "historical_reference_only", "manuscript_section": "n/a", "confidence": "low", "canonical": "no", "historical": "yes", "stale": "yes"},
    {"artifact": "manuscript_artifacts_stale", "location": "outputs/manuscript_artifacts/",
     "description": "Pre-all4 generated LaTeX/CSV tables", "publication_quality": "low",
     "recommended_usage": "regenerate", "manuscript_section": "n/a", "confidence": "low", "canonical": "no", "historical": "yes", "stale": "yes"},
    {"artifact": "MANUSCRIPT_SUMMARY_root", "location": "MANUSCRIPT_SUMMARY.md",
     "description": "Root manuscript summary (may predate all4)", "publication_quality": "low",
     "recommended_usage": "historical_reference_only", "manuscript_section": "n/a", "confidence": "low", "canonical": "no", "historical": "yes", "stale": "yes"},
    {"artifact": "PAPER_DRAFT_WORDING", "location": "PAPER_DRAFT_WORDING.md",
     "description": "Draft wording snippets", "publication_quality": "low",
     "recommended_usage": "historical_reference_only", "manuscript_section": "n/a", "confidence": "low", "canonical": "no", "historical": "yes", "stale": "yes"},
    # Baselines / modern
    {"artifact": "final_modern_baselines", "location": "outputs/final_modern_baselines/",
     "description": "Modern baseline comparison (different protocol)", "publication_quality": "medium",
     "recommended_usage": "supplementary", "manuscript_section": "Related Work;Supplement", "confidence": "medium", "canonical": "no", "historical": "no", "stale": "no"},
    {"artifact": "adaptive_repair_policy", "location": "outputs/adaptive_repair_policy/",
     "description": "Adaptive when-to-repair policy experiments", "publication_quality": "medium",
     "recommended_usage": "discussion", "manuscript_section": "Discussion;Implications", "confidence": "medium", "canonical": "no", "historical": "no", "stale": "no"},
    {"artifact": "selector_llm_extension", "location": "reports/selector_llm_extension/",
     "description": "Selector training extension with LLM features", "publication_quality": "medium",
     "recommended_usage": "supplementary", "manuscript_section": "Discussion;Supplement", "confidence": "medium", "canonical": "no", "historical": "no", "stale": "no"},
    # Efficiency
    {"artifact": "efficiency_evidence_audit", "location": "experiments/failure_class_audit_20260711_212157/phase_reports/EFFICIENCY_EVIDENCE_AUDIT.md",
     "description": "Runtime/memory evidence synthesis", "publication_quality": "medium",
     "recommended_usage": "supplementary", "manuscript_section": "Results;Limitations", "confidence": "medium", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "runtime_per_query", "location": "experiments/failure_class_audit_20260711_212157/phase_reports/runtime_per_query.csv",
     "description": "Per-query runtime measurements", "publication_quality": "medium",
     "recommended_usage": "supplementary_table", "manuscript_section": "Results", "confidence": "medium", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "scale_sweep_outputs", "location": "outputs/scale_sweep_n20/",
     "description": "Synthetic scalability timing (n=20)", "publication_quality": "medium",
     "recommended_usage": "supplementary", "manuscript_section": "Results;Supplement", "confidence": "medium", "canonical": "no", "historical": "no", "stale": "no"},
    # Docs / claims
    {"artifact": "repo_publication_audit", "location": "reports/repo_publication_audit.md",
     "description": "Conservative publication audit (2026-03-22)", "publication_quality": "high",
     "recommended_usage": "authoring_blueprint", "manuscript_section": "n/a", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "claim_support_matrix", "location": "reports/claim_support_matrix.csv",
     "description": "Original claim-evidence matrix", "publication_quality": "high",
     "recommended_usage": "claims_discipline", "manuscript_section": "Introduction;Limitations", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "final_claim_support_matrix", "location": "experiments/publication_readiness_audit_20260711_233629/final_claim_support_matrix.csv",
     "description": "Definitive claim classification (safe/contradicted/etc.)", "publication_quality": "high",
     "recommended_usage": "claims_discipline", "manuscript_section": "All sections", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "SAFE_CLAIMS_FOR_PAPER", "location": "docs/SAFE_CLAIMS_FOR_PAPER.md",
     "description": "Documented safe claim boundaries", "publication_quality": "high",
     "recommended_usage": "authoring_blueprint", "manuscript_section": "All sections", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "THREATS_TO_VALIDITY", "location": "docs/THREATS_TO_VALIDITY.md",
     "description": "Threats to validity documentation", "publication_quality": "high",
     "recommended_usage": "limitations_section", "manuscript_section": "Threats to Validity", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "REPRODUCTION_Q1", "location": "docs/REPRODUCTION_Q1.md",
     "description": "Reproduction instructions", "publication_quality": "high",
     "recommended_usage": "artifact_package", "manuscript_section": "Reproducibility", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    # Figures
    {"artifact": "manuscript_figures_readme", "location": "figures/manuscript/README.md",
     "description": "Curated figure list from build_manuscript_assets.py", "publication_quality": "medium",
     "recommended_usage": "figure_plan", "manuscript_section": "Results", "confidence": "medium", "canonical": "no", "historical": "no", "stale": "partial"},
    {"artifact": "pub_vote_analysis_jsons", "location": "outputs/pub_vote_cmp_all4/analysis/",
     "description": "Per-dataset bootstrap delta JSONs for figure regeneration", "publication_quality": "high",
     "recommended_usage": "figure_source", "manuscript_section": "Results", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    # Exploratory
    {"artifact": "real_full", "location": "outputs/real_full/",
     "description": "qrels-derived preference experiments (different protocol)", "publication_quality": "low-medium",
     "recommended_usage": "do_not_mix", "manuscript_section": "Supplement (labeled)", "confidence": "low", "canonical": "no", "historical": "no", "stale": "no"},
    {"artifact": "noise_sweep_synthetic", "location": "outputs/noise_sweep_n0.20/",
     "description": "Synthetic noise sensitivity experiments", "publication_quality": "medium",
     "recommended_usage": "supplementary", "manuscript_section": "Supplement", "confidence": "medium", "canonical": "no", "historical": "no", "stale": "no"},
    {"artifact": "exact_vs_greedy_docs", "location": "docs/tables/exact_vs_greedy_summary.csv",
     "description": "Exact vs greedy FAS structural comparison (synthetic)", "publication_quality": "medium",
     "recommended_usage": "supplementary", "manuscript_section": "Methods;Supplement", "confidence": "medium", "canonical": "no", "historical": "no", "stale": "no"},
    {"artifact": "docs_tables_legacy", "location": "docs/tables/",
     "description": "Legacy aggregated tables (mixed dates)", "publication_quality": "low-medium",
     "recommended_usage": "verify_before_use", "manuscript_section": "Supplement", "confidence": "low", "canonical": "no", "historical": "partial", "stale": "partial"},
    # Scripts
    {"artifact": "run_publication_vote_suite", "location": "scripts/run_publication_vote_suite.py",
     "description": "Reproduce canonical four-dataset vote suite", "publication_quality": "high",
     "recommended_usage": "artifact_package", "manuscript_section": "Reproducibility", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "build_paper_evidence_package", "location": "scripts/build_paper_evidence_package.py",
     "description": "Build paper_package tables from vote suite outputs", "publication_quality": "high",
     "recommended_usage": "artifact_package", "manuscript_section": "Reproducibility", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
    {"artifact": "build_manuscript_assets", "location": "scripts/build_manuscript_assets.py",
     "description": "Generate manuscript figures from paper_package", "publication_quality": "high",
     "recommended_usage": "figure_generation", "manuscript_section": "Figures", "confidence": "high", "canonical": "yes", "historical": "no", "stale": "no"},
]


def _scan_additional() -> list[dict]:
    """Add openai runs and experiment dirs not in curated list."""
    rows = []
    seen = {c["location"].rstrip("/") for c in CURATED}
    patterns = [
        ("outputs/openai_*", "real_llm_run", "medium", "appendix", "Results", "medium"),
        ("experiments/*_audit_*", "audit_workspace", "high", "authoring_blueprint", "n/a", "high"),
        ("reports/failure_mining*", "failure_mining", "medium-high", "supplementary_data", "Methods", "medium"),
    ]
    for glob_pat, atype, qual, usage, section, conf in patterns:
        for p in sorted(REPO.glob(glob_pat)):
            rel = str(p.relative_to(REPO))
            if rel.rstrip("/") in seen or not p.exists():
                continue
            seen.add(rel.rstrip("/"))
            stale = "v2" in rel or "smoke" in rel
            rows.append({
                "artifact": p.name,
                "location": rel,
                "description": f"Auto-discovered {atype}",
                "publication_quality": qual,
                "recommended_usage": usage,
                "manuscript_section": section,
                "confidence": conf,
                "canonical": "no" if stale else "conditional",
                "historical": "yes" if stale else "no",
                "stale": "yes" if stale else "no",
            })
    return rows


def main() -> None:
    rows = list(CURATED) + _scan_additional()
    # Deduplicate by location
    seen_loc: set[str] = set()
    unique = []
    for r in rows:
        loc = r["location"]
        if loc not in seen_loc:
            seen_loc.add(loc)
            unique.append(r)

    unique.sort(key=lambda x: (x.get("canonical", ""), x["location"]))
    fieldnames = [
        "artifact", "location", "description", "publication_quality",
        "recommended_usage", "manuscript_section", "confidence",
        "canonical", "historical", "stale",
    ]
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(unique)
    print(f"Wrote {len(unique)} rows to {OUT}")


if __name__ == "__main__":
    main()
