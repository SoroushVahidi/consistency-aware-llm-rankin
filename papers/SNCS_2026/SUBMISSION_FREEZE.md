# SNCS 2026 Submission Freeze Record

**Purpose:** identify the exact manuscript and repository artifact version that
corresponds to the SN Computer Science submission package. This file is the
authoritative freeze ledger for this branch.

**Status:** freeze package prepared on branch `papers/sncs-2026-foundation`.
The commit SHA below is the submission freeze commit that introduced this
ledger, the regenerated source ZIP, and the release-candidate package docs
(see `RELEASE_CANDIDATE_DECISION.md`). Later documentation-only tip commits
may exist; tag `sncs-2026-submission-v1` should still point at this SHA unless
the PDF/ZIP hashes change.

| Field | Value |
|---|---|
| Freeze date (UTC calendar) | 2026-08-01 |
| Branch | `papers/sncs-2026-foundation` |
| Repository commit SHA | `f42ad47f66fe73c14f4cac52b23876b264c10739` |
| Canonical repository URL | https://github.com/SoroushVahidi/consistency-aware-llm-rankin |
| Commit-pinned tree URL | https://github.com/SoroushVahidi/consistency-aware-llm-rankin/tree/f42ad47f66fe73c14f4cac52b23876b264c10739 |
| Repository visibility at freeze | Public (`gh repo view`: `visibility=PUBLIC`) |
| Proposed release tag (not created) | `sncs-2026-submission-v1` |

## Manuscript identity

| Field | Value |
|---|---|
| Title | Structural Consistency Is Not Retrieval Utility: An Exact-and-Heuristic Audit of Preference-Graph Repair for Multi-Ranker Retrieval |
| Running title | Structural Consistency Is Not Retrieval Utility |
| Target journal | SN Computer Science (Springer Nature, ISSN 2661-8907) |
| Article type (intended) | Original Research |
| Manuscript PDF path | `papers/SNCS_2026/manuscript/main.pdf` |
| Manuscript PDF SHA-256 | `7980e146ef32731405b4e4845f5a70799dd46391b0878bdc1fb8037aac90b3c7` |
| LaTeX source ZIP path | `papers/SNCS_2026/submission/SNCS_2026_latex_source.zip` |
| Source ZIP SHA-256 | `deca1a011f7e5b3af9facc44c47869211a04b58a5ee1f987ff6f02a053d8418c` |
| Source `main.tex` SHA-256 | `4f3cb0e09e282b0af0effb2cfe8005d4113e804ddbb50ee087143e930af0f151` |
| Page count (compiled PDF) | 39 |
| Structured abstract word count | 196 (Purpose / Methods / Results / Conclusion) |
| Figures | 5 |
| Tables | 6 |
| Algorithms | 1 |
| Cited references | 62 (compiled bibliography entries `[1]`–`[62]`; BibTeX file has 65 keys, 3 unused) |

## Source ZIP contents

The uploadable LaTeX archive contains exactly:

- `manuscript/main.tex`
- `manuscript/references.bib`
- `figures/f1_pipeline.pdf` … `figures/f5_exact_vs_greedy_gap.pdf`
- `template/sn-jnl.cls`
- `template/bst/sn-basic.bst`

It deliberately excludes internal audit Markdown, reviewer notes, cover-letter
drafts, PNG previews, and repository code.

## Exact code/data paths needed for reproduction

These paths exist at the freeze commit and back the manuscript tables/figures.
Do not substitute historical packages under `outputs/pub_vote_cmp_*`.

### Primary retrieval and structural results

- `reports/full_calibrated_core/`
- `reports/full_calibrated_core/outputs/calibrated_all4/paper_package/tables/`
  - `table_primary_graph_structure.csv` (12 data rows)
  - `table_primary_bootstrap_permutation.csv` (60 data rows)
  - `table_primary_macro_method_comparison.csv`
- Driver: `reports/full_calibrated_core/scripts/run_full_calibrated_core.py`
  (regeneration is expensive; prefer verifying against stored tables)

### Exact-repair comparison

- `reports/exact_open_source_ilp_repair_investigation/`
- `reports/exact_open_source_ilp_repair_investigation/tables/structural_per_query.csv` (1,025 rows)
- Solver status / paired retrieval families under the same report directory

### Pool-cutoff and robustness families

- `reports/final_revision_task1_pool_cutoff_20260715/`
- `reports/final_revision_task4_exact_baseline_fairness_20260715/`
- `reports/final_revision_task2_statistical_power_20260715/` (MDE / equivalence)
- `reports/normalization_protocol_audit_20260714/`
- `reports/candidate_pool_conditional_audit_20260714/`

### Statistical inference implementation

- `src/consistency_ranker/statistical_inference.py`
- Graph/repair core: `src/consistency_ranker/{graph_construction,cycle_detection,greedy_fas,mwfas_solver,baseline_ranking,evaluation}.py`

### Six-query real-LLM pilot (directional only; not primary evidence)

- Compact reanalysis: `reports/real_llm_clustered_reanalysis_20260730T023745Z/`
- Pilot report root: `reports/multi_provider_repair_pilot_20260729T032348Z/`
- **Excluded from public redistribution:** any `raw_calls/` provider request/response payloads

### Manuscript figure sources

- `papers/SNCS_2026/figures/` (committed vector PDFs used by `\includegraphics`)
- Regenerators: `papers/SNCS_2026/figures/generate_f1_pipeline.py`, `generate_f5_exact_vs_greedy_gap.py`
- F2–F4 provenance: copied from `papers/JDIQ_2026/manuscript/figures_v2/` (same canonical CSVs)

### Reviewer entry points

- `papers/SNCS_2026/REPRODUCIBILITY_QUICKSTART.md`
- Repository-wide classical reproduction map: `docs/REPRODUCTION_CANONICAL.md`
- Contribution classification: `docs/CONTRIBUTIONS.md`

## Explicit non-evidence (do not cite as manuscript results)

- `reports/gurobi_vs_scip_solver_cross_validation_20260731T162314Z/`
- `reports/exact_solver_scaling_study_20260731T162314Z/`
- Historical packages: `outputs/pub_vote_cmp_all4/`, `outputs/pub_vote_cmp_v2/`, `outputs/q1_journal_package/`

## How to verify this freeze later

```bash
git fetch origin
git checkout papers/sncs-2026-foundation
git rev-parse HEAD   # must equal the SHA recorded above after freeze commit
sha256sum papers/SNCS_2026/manuscript/main.pdf
sha256sum papers/SNCS_2026/submission/SNCS_2026_latex_source.zip
pdfinfo papers/SNCS_2026/manuscript/main.pdf | grep Pages   # expect 39
```
