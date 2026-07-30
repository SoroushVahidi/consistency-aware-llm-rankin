# Reports

**Start here:** [`../PROJECT_STATUS.md`](../PROJECT_STATUS.md) (canonical
entry point) and
[`ir_evidence_audit_20260729T182949Z/FINAL_IR_EVIDENCE_AUDIT.md`](ir_evidence_audit_20260729T182949Z/FINAL_IR_EVIDENCE_AUDIT.md)
(current integrated evidence audit, with
[`ir_evidence_audit_review_20260729T235053Z/FINAL_META_AUDIT_REVIEW.md`](ir_evidence_audit_review_20260729T235053Z/FINAL_META_AUDIT_REVIEW.md)
as an independent check on its conclusions). The current classical-study
canonical numeric backbone is `reports/full_calibrated_core/` — see
`docs/REPRODUCTION_CANONICAL.md` at the repo root.

**Real-LLM studies (repair_frontier / extraction_study / repair_diagnostic):**
for any inferential claim (a CI, a significance test, "X is better/worse
than Y"), the authoritative source is
[`real_llm_clustered_reanalysis_20260730T023745Z/REAL_LLM_CLUSTERED_REANALYSIS.md`](real_llm_clustered_reanalysis_20260730T023745Z/REAL_LLM_CLUSTERED_REANALYSIS.md),
**not** the row-level statistics in the three original study directories
(each now carries a `STATUS.md` pointing here). Those three directories'
raw observations and point estimates remain valid; only their row-level
CIs/p-values (which treated 120 rows as 120 independent queries, when
there are only 6) are superseded.

## Historical: publication audit (2026-03/04, `pub_vote_cmp_all4`/`v2` era)

**The five documents below analyze `outputs/pub_vote_cmp_all4/` and
`outputs/pub_vote_cmp_v2/`, a pipeline last regenerated 2026-03-24 that is
not referenced anywhere in the current, submitted
`papers/JDIQ_2026/manuscript/main.tex`.** They are kept for provenance and
historical/ablation comparison; do not treat them as describing the paper's
current evidence. See
`repo_hygiene_audit_20260729T235053Z/canonical_artifacts.md` for the full
account of how this was determined.

**Moved to `_archive/publication_audit_20260406/` in repo Stage 2 (2026-07-30)** — same six documents, new location, links below updated accordingly.

| Document | Description |
|----------|-------------|
| [`_archive/publication_audit_20260406/repo_publication_audit.md`](_archive/publication_audit_20260406/repo_publication_audit.md) | Historical publication-readiness audit — canonical-package recommendation for the pre-`full_calibrated_core` pipeline |
| [`_archive/publication_audit_20260406/canonical_results_inventory.csv`](_archive/publication_audit_20260406/canonical_results_inventory.csv) | Historical result-package/experiment-family inventory |
| [`_archive/publication_audit_20260406/claim_support_matrix.csv`](_archive/publication_audit_20260406/claim_support_matrix.csv) | Historical claim × evidence classification |
| [`_archive/publication_audit_20260406/repaired_vs_unrepaired_master_table.csv`](_archive/publication_audit_20260406/repaired_vs_unrepaired_master_table.csv) | Historical merged table from `outputs/pub_vote_cmp_all4/paper_package/tables/` |
| [`_archive/publication_audit_20260406/paper_safe_contributions.md`](_archive/publication_audit_20260406/paper_safe_contributions.md) | Historical conservative contribution paragraph |
| [`_archive/publication_audit_20260406/repo_cleanup_recommendations.md`](_archive/publication_audit_20260406/repo_cleanup_recommendations.md) | Historical cleanup and coherence steps (see `repo_hygiene_audit_20260729T235053Z/` for the current hygiene audit) |
