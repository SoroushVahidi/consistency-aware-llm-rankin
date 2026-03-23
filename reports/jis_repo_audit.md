# JIS repository audit — classification of major docs, reports, and outputs

**Purpose:** Tell authors what to **cite**, what to **read internally**, and what to **avoid** when drafting JIS, given **`outputs/pub_vote_cmp_all4`** as canonical (see `outputs/final_jis_package/README.md`).

**Legend:**  
**USED_IN_PAPER** — primary or appendix evidence chain for the recommended manuscript.  
**INTERNAL_REFERENCE** — helpful for implementation or context; not automatic manuscript citations.  
**DEPRECATED_FOR_PAPER** — misleading if cited **without** heavy qualification or if treated as interchangeable with all4.  
**BACKGROUND_ONLY** — orientation, planning, or non-final narrative.

| Path | Classification | Short reason | Safe to cite / rely on for drafting? |
|------|----------------|--------------|--------------------------------------|
| `outputs/final_jis_package/` | **USED_IN_PAPER** | Canonical **frozen** copy of all4 tables, analysis JSON, summaries, figures for JIS. | **Yes** — preferred citation path for “our results.” |
| `outputs/pub_vote_cmp_all4/paper_package/` | **USED_IN_PAPER** | Source-of-truth **committed** tables + plots for canonical bundle. | **Yes** (same as `final_jis_package/tables`). |
| `outputs/pub_vote_cmp_all4/analysis/` | **USED_IN_PAPER** | JSON inputs to bootstrap / delta aggregation. | **Yes** for methods/trace; readers rarely need direct citation. |
| `outputs/pub_vote_cmp_all4/SUMMARY.md` | **INTERNAL_REFERENCE** | CLI markdown summary; cross-check vs CSVs. | **Cite CSVs instead.** |
| `outputs/pub_vote_cmp_v2/paper_package/` | **DEPRECATED_FOR_PAPER** | Same schema as all4 but **2 datasets** and **conflicting numbers** on overlaps. | **Only** with explicit “archived run / v2” label—not interchangeable. |
| `outputs/q1_journal_package/` | **DEPRECATED_FOR_PAPER** (as authoritative) | Built by `generate_q1_tables.py` defaulting to **v2** unless regenerated for all4. | **Do not** cite as final if manuscript uses all4. |
| `outputs/real_full/` | **BACKGROUND_ONLY** / appendix | Different preference protocol (`qrels` / `qrels_flip`); see `PROVENANCE.md`. | **Cite only** with protocol separation from vote suite. |
| `outputs/noise_sweep_*`, `outputs/margin_multiseed_*` | **INTERNAL_REFERENCE** / appendix | Synthetic committed outputs. | **Yes** for **synthetic** claims only. |
| `reports/jis_final_tables/` | **USED_IN_PAPER** | Renamed, deduplicated **manuscript table** set (main + appendix). | **Yes** — use for LaTeX/Word drafting. |
| `reports/jis_claims_mapping.md` | **USED_IN_PAPER** | Claim ↔ evidence map for conservative wording. | **Yes** (process / supplement). |
| `reports/jis_editorial_summary.md` | **INTERNAL_REFERENCE** | Author-facing orientation. | **Yes** internally; optional supplement. |
| `reports/jis_repo_audit.md` | **INTERNAL_REFERENCE** | This file. | Optional supplement. |
| `reports/claim_support_matrix.csv` | **USED_IN_PAPER** | Machine-readable claim checks (includes all4 vs v2 nuance). | **Yes** for internal QC. |
| `reports/canonical_results_inventory.csv` | **USED_IN_PAPER** | Declares all4 canonical + conflicts. | **Yes** for reproducibility notes. |
| `reports/repo_publication_audit.md` | **USED_IN_PAPER** | Detailed audit of packages and conflicts. | **Yes** for transparency / reviewer response. |
| `reports/repo_cleanup_recommendations.md` | **INTERNAL_REFERENCE** | Housekeeping suggestions. | **No** for scientific claims. |
| `reports/paper_tables/` (except see below) | **DEPRECATED_FOR_PAPER** / mixed | Generator output; **table_01 / table_05** align with **v2/q1**, not all4. | **Cite `reports/jis_final_tables/`** instead. |
| `reports/paper_tables/table_03_*`, `table_04_*`, `table_06_*` | **INTERNAL_REFERENCE** / appendix | Synthetic + inventory helpers; copied into `jis_final_tables` as appendix. | **Yes** with correct **synthetic** framing. |
| `reports/paper_safe_contributions.md` | **BACKGROUND_ONLY** | Narrative draft; may predate all4 freeze. | Cross-check against `jis_claims_mapping.md`. |
| `reports/repaired_vs_unrepaired_master_table.csv` | **INTERNAL_REFERENCE** | Aggregated helper; verify provenance before citing. | **Verify** against canonical CSVs. |
| `reports/experiment_inventory.json` | **INTERNAL_REFERENCE** | Index of experiments. | **No** direct manuscript citation. |
| `reports/README.md` | **BACKGROUND_ONLY** | Reports subtree orientation. | **No** for claims. |
| `docs/jis_paper_scope.md` | **USED_IN_PAPER** | Frozen scope statement. | **Yes** (process / align authors). |
| `docs/jis_reproducibility.md` | **USED_IN_PAPER** | Honest reproducibility paragraph source. | **Yes** (methods / availability). |
| `docs/RESULTS_FOR_PAPER.md` | **DEPRECATED_FOR_PAPER** (partially) | Names **v2** as canonical in places; **superseded** by JIS docs for numbering. | **Update mentally** to all4 + `jis_claims_mapping.md`. |
| `docs/SAFE_CLAIMS_FOR_PAPER.md` | **DEPRECATED_FOR_PAPER** (partially) | Several claims cite **v2** paths and **SciDocs significance** not matching **all4**. | **Do not** copy SC-4/SC-5 verbatim without all4 check. |
| `docs/SAFE_Q1_CLAIMS.md` | **BACKGROUND_ONLY** | Q1-oriented; may reference q1 package. | Cross-check with all4. |
| `docs/Q1_CLAIM_EVIDENCE_MAP.md` | **BACKGROUND_ONLY** | Useful but references **v2**/q1 artifacts. | Update evidence paths if cited. |
| `docs/EVIDENCE_MAP.md` | **BACKGROUND_ONLY** | Broad map; may be stale vs final freeze. | Cross-check. |
| `docs/THREATS_TO_VALIDITY.md` | **USED_IN_PAPER** | Limitations prose source. | **Yes** (limitations section). |
| `docs/REPRODUCTION_Q1.md` | **INTERNAL_REFERENCE** | Commands for many pipelines; **Q1** naming. | **Yes** for engineering; align with `jis_reproducibility.md` for manuscript. |
| `docs/PAPER_TABLES_GENERATION.md` | **INTERNAL_REFERENCE** | Explains `generate_paper_tables.py`. | **Yes** for maintainers. |
| `docs/REPOSITORY_AUDIT_AND_GAP_ANALYSIS.md` | **BACKGROUND_ONLY** | Gap analysis narrative. | **No** automatic claims; cross-check. |
| `docs/JOURNAL_READY_CONTRIBUTIONS.md` | **BACKGROUND_ONLY** | Positioning draft. | Cross-check with `jis_paper_scope.md`. |
| `docs/Q1_POSITIONING_AND_CLAIMS.md` | **BACKGROUND_ONLY** | Q1-specific positioning. | Cross-check. |
| `docs/EXPERIMENTS.md` | **INTERNAL_REFERENCE** | Experiment catalog. | **Yes** for methods context. |
| `docs/READ_ME_FIRST_FOR_AI.md` | **INTERNAL_REFERENCE** | Agent orientation. | **No** for paper. |
| `docs/tables/*.csv` | **INTERNAL_REFERENCE** / mixed | Legacy table exports (synthetic, bootstrap sweeps). | **Cite** only with provenance from `jis_final_tables` or explicit path notes. |
| `figures/manuscript/README.md` | **INTERNAL_REFERENCE** | Figure generation notes. | **Yes** for figure provenance. |
| `figures/graphical_abstract/README.md` | **BACKGROUND_ONLY** | Optional asset. | **Yes** if GA used. |
| `README.md` (repo root) | **BACKGROUND_ONLY** | Project overview. | **Yes** for repo citation. |
| `docs/WULVER_*`, `docs/PAPER_PACKAGE_STATUS_*` | **BACKGROUND_ONLY** | Cluster / execution logs and status. | **No** for scientific claims. |
| `docs/DATASET_ACCESS_*`, `docs/FULL_DATASET_ACCESS_*`, `docs/BRIGHT_ACCESS_*` | **INTERNAL_REFERENCE** | Data access troubleshooting. | **No** for results claims. |
| `docs/METHOD_REPOSITIONING_AUDIT.md`, `docs/AUDIT.md`, `docs/RESULTS_AUDIT.md` | **BACKGROUND_ONLY** | Historical audits. | Cross-check only. |
| `scripts/build_paper_evidence_package.py` | **INTERNAL_REFERENCE** | Defines method IDs and aggregation logic. | **Cite** as “implementation reference” if needed. |
| `scripts/generate_q1_tables.py` | **INTERNAL_REFERENCE** | q1 package generator (**v2 default**). | **Caution** for provenance drift. |

---

## Summary instruction for drafting

- **Primary numeric path:** `outputs/final_jis_package/` → `reports/jis_final_tables/` → `reports/jis_claims_mapping.md`.  
- **Do not** merge **`v2` / `q1_journal_package` / `reports/paper_tables/table_01`** into the same results table as **all4** without a **conflict disclosure**.

*Generated for JIS evidence freezing; no files were deleted.*
