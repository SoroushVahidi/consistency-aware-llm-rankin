# Evidence Provenance (current, 2026-07-30)

**Supersedes `MASTER_EVIDENCE_INVENTORY.csv` and `SECTION_EVIDENCE_MAP.csv`
in this directory for evidence-to-claim lookups.** Those two files are
dated 2026-07-12 and predate `reports/full_calibrated_core/` (2026-07-15,
the pipeline that actually backs the submitted `manuscript/main.tex`); they
are kept unmodified for historical provenance, not deleted. This file was
produced during a repository hygiene pass
(`reports/repo_hygiene_audit_20260729T235053Z/`,
`reports/repo_cleanup_stage1_20260730T004010Z/`) that found the staleness
by direct number-matching against `main.tex`, not by trusting either CSV's
self-description.

Every row below states: the claim/category, the canonical source result
file, the generating script, the report it lives in, and the manuscript
section (if any) that currently cites it.

## 1. Original historical pipeline (superseded, not cited by current `main.tex`)

| Category | Source | Generating script | Cited by current manuscript? |
|---|---|---|---|
| Four-dataset vote-comparison suite | `outputs/pub_vote_cmp_all4/paper_package/tables/*.csv` | `scripts/run_publication_vote_suite.py` → `scripts/build_paper_evidence_package.py` | **No** (zero `pub_vote_cmp` references in `main.tex`) |
| Two-dataset predecessor | `outputs/pub_vote_cmp_v2/paper_package/` | same scripts, earlier run | **No** |
| Q1 journal aggregation | `outputs/q1_journal_package/` | `scripts/generate_q1_tables.py` (defaults to `pub_vote_cmp_v2`) | **No** |

Kept on disk and still git-tracked because `generate_q1_tables.py` and
`build_paper_evidence_package.py` still function against these paths by
default; not moved or deleted (see
`reports/repo_hygiene_audit_20260729T235053Z/proposed_moves.csv`).

## 2. Current classical-study canonical evidence (backs `main.tex`)

| Category | Source | Generating script | Manuscript section |
|---|---|---|---|
| Construction → structure (cyclicity, SCC, edge weight) | `reports/full_calibrated_core/outputs/calibrated_all4/paper_package/tables/table_primary_graph_structure.csv` | `reports/full_calibrated_core/scripts/full_calibration_utils.py` (`run_full_core()`) | §4.1 |
| Repair effects, primary protocol | `.../table_primary_repair_effects.csv` | same | §4.2 |
| Macro method comparison (CombSUM/RRF/Prior/Borda/graph methods) | `.../table_primary_macro_method_comparison.csv` | same | §4.2-4.3 (CombSUM=0.554, RRF=0.546) |
| Additional normalization/threshold protocols | `reports/normalization_protocol_audit_20260714/tables/independent_protocol_*.csv` | `scripts/run_independent_protocols.py`, `scripts/analyze_protocol_robustness.py` | §4.2 robustness |
| Candidate-pool / conditional / new-baseline robustness | `reports/candidate_pool_conditional_audit_20260714/` | `scripts/run_pool_robustness.py`, `scripts/run_conditional_and_failure_analysis.py`, `scripts/run_baseline_comparison.py` | §4.2-4.3 robustness |
| Larger-pool greedy repair, multi-cutoff | `reports/final_revision_task1_pool_cutoff_20260715/tables/pool_cutoff_statistics.csv`, `pool_cutoff_pair_metrics.csv` | `reports/final_revision_task1_pool_cutoff_20260715/scripts/run_pool_cutoff_study.py` | §4.2 ("0/110 active larger-pool cells") |
| Exact SCIP repair vs. greedy | `reports/exact_open_source_ilp_repair_investigation/tables/*.csv` | `reports/exact_open_source_ilp_repair_investigation/scripts/run_exact_open_ilp_study.py` | §4.2 robustness ("1,025/1,025 proven optimal") |
| Larger-pool exact repair + baseline fairness (RRF/CombSUM vs. repair) | `reports/final_revision_task4_exact_baseline_fairness_20260715/tables/*.csv` | `reports/final_revision_task4_exact_baseline_fairness_20260715/scripts/*.py` | §4.2-4.3 ("0/56 larger-pool Holm-significant") |
| Repository-scale oracle headroom (n=419, query-level) | `reports/repository_scale_headroom_analysis/manuscript_tables/table_3_oracle_headroom.csv` | (see that report's own scripts) | **Not cited by `main.tex`** — belongs to the separate `negative_result_2026` track (see §5 below) |

See `docs/REPRODUCTION_CANONICAL.md` (repo root) for the exact reproduction commands and the full protocol/pool/regime identifier registry.

## 3. Real-LLM exploratory evidence (this session, 2026-07-29)

| Category | Source | Generating script | Manuscript section | Caveat |
|---|---|---|---|---|
| Richer repair-candidate frontier | `reports/repair_frontier_20260729T144742Z/` | `scripts/run_repair_frontier_pilot.py` | Not yet in `main.tex` — proposed text lives in `reports/ir_evidence_audit_20260729T182949Z/FINAL_IR_EVIDENCE_AUDIT.md` §7 | 120 "query-graphs" = 6 real queries × ~20 provider/pool constructions each; not 120 independent observations |
| Extraction-method comparison (incl. HodgeRank) | `reports/extraction_study_20260729T151610Z/` | `scripts/run_extraction_study.py` | Same | Same 6-query sample; 8-extractor family has no Holm/BH correction applied (see meta-audit) |
| Repair-predictability diagnostic | `reports/repair_diagnostic_20260729T162748Z/` | `scripts/run_repair_diagnostic_study.py` | Same | Same 6-query sample; univariate p-values computed at n=120 are not valid given the true n=6 cluster count |

## 4. Integrated evidence audit and meta-audit (this session)

| Document | Role |
|---|---|
| `reports/ir_evidence_audit_20260729T182949Z/FINAL_IR_EVIDENCE_AUDIT.md` | Integrates §2 (classical backbone) and §3 (real-LLM exploratory) above into one unified table + proposed manuscript text. Verdict at the time: READY_TO_REWRITE. |
| `reports/ir_evidence_audit_review_20260729T235053Z/FINAL_META_AUDIT_REVIEW.md` | Independent meta-audit of the above. Verdict: READY_TO_REWRITE for the classical backbone; ONE_SMALL_GAP_REMAINS for the manuscript as a whole, pending the fix in §5 below. |

## 5. Query-clustered real-LLM re-analysis — RESOLVED 2026-07-30 (repo Stage 3)

The meta-audit (§5-6 of `FINAL_META_AUDIT_REVIEW.md`) recommended recomputing the bootstrap CIs and p-values in §3 above using a cluster/block bootstrap over the 6 underlying `query_id` groups instead of the 120 rows, and applying Holm correction across the 8-extractor family in `extraction_study`. **This is now done.** `src/consistency_ranker/statistical_inference.py` gained `cluster_bootstrap_mean_interval()`, `cluster_exact_sign_flip_pvalue()`, and `cluster_exact_permutation_correlation()`; `src/consistency_ranker/real_llm_reanalysis/` implements the per-study re-analysis; the canonical output lives in `reports/real_llm_clustered_reanalysis_20260730T023745Z/`.

Headline corrections (see that directory's `conclusion_change_matrix.csv` for the full account): the extraction study's "Borda is significantly worse than incumbent" claim and the repair-diagnostic study's "is_cyclic/topk_involvement Holm-significant association" claim **do not survive** cluster-aware, Holm-corrected re-analysis. The repair-frontier oracle headroom's point estimate is unchanged but its uncertainty is wider (cluster CI now spans the 0.01 practical-significance threshold rather than sitting entirely below it). The repair-diagnostic study's "repair is net-harmful on average" finding is unchanged and, if anything, more robust (all 6 independent queries agree on direction).

## 6. `negative_result_2026` (separate paper track, not part of `main.tex`)

`papers/negative_result_2026/` is plan-only (no `main.tex` yet). Its evidence base is `reports/repository_scale_headroom_analysis/` (§2 above). Do not conflate its claims with the `JDIQ_2026` manuscript's.
