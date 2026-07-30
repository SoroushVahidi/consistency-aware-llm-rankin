# JDIQ 2026 Manuscript Workspace

> **SUPERSEDED (as of 2026-07-14).** This file predates the completed
> manuscript and is stale in two important ways: (1) `manuscript/main.tex`
> is now a complete draft through Conclusion and Data Availability, not
> "writing not started"; (2) the "canonical evidence sources" below include
> the six-way rule-based failure taxonomy
> (`experiments/failure_class_audit_20260711_212157/`) and a "CARB"
> benchmark, both of which the finished manuscript's Limitations section
> explicitly excludes as evidence -- they are **not** part of the current
> empirical narrative. For the manuscript's actual, current claims and
> their evidence, read `manuscript/main.tex` directly; for reproduction
> commands, use `docs/REPRODUCTION_CANONICAL.md` (repo root). This file is
> kept for historical reference to the pre-writing planning stage only.

# JDIQ 2026 Manuscript Workspace

**Venue:** ACM Journal of Data and Information Quality (JDIQ)  
**Status:** Publication infrastructure complete; writing not started  
**Created:** 2026-07-12

This workspace is the **master blueprint** for the JDIQ submission. It is isolated from all existing manuscripts and audit workspaces.

## Start here

1. `JDIQ_GUIDELINE_SUMMARY.md` — journal requirements and submission checklist
2. `CANONICAL_PAPER_STORY.md` — the single evidence-backed narrative
3. `MANUSCRIPT_OUTLINE.md` — detailed section blueprint
4. `PROJECT_STATUS.md` — readiness dashboard (currently ~22%)

## File index

| File | Step | Purpose |
|------|------|---------|
| `JDIQ_GUIDELINE_SUMMARY.md` | 1 | Journal study |
| `MASTER_EVIDENCE_INVENTORY.csv` | 2 | **STALE (2026-07-30):** 69 repository artifacts, dated 2026-07-12, predates `reports/full_calibrated_core/` (2026-07-15) and still lists the historical `outputs/pub_vote_cmp_all4/` as canonical. See `EVIDENCE_PROVENANCE_20260730.md` for the current mapping; kept here for provenance only. |
| `CANONICAL_PAPER_STORY.md` | 3 | Canonical story |
| `MANUSCRIPT_OUTLINE.md` | 4 | Section outline |
| `SECTION_EVIDENCE_MAP.csv` | 5 | **STALE (2026-07-30):** Evidence → section mapping, same staleness as `MASTER_EVIDENCE_INVENTORY.csv` above. See `EVIDENCE_PROVENANCE_20260730.md`. |
| `EVIDENCE_PROVENANCE_20260730.md` | 2b/5b | **Current** evidence-to-claim mapping, added 2026-07-30 repo hygiene Stage 1 (supersedes the two rows above for lookups) |
| `MISSING_COMPONENTS.md` | 6 | Gap analysis |
| `FIGURE_PLAN.md` | 7 | Figure plan (superseded by FIGURE_SPECIFICATIONS.md) |
| `FIGURE_SPECIFICATIONS.md` | 7+ | **Complete figure reproduction briefs** |
| `FIGURE_DATA_MAP.csv` | 7+ | Figure index with sources and variables |
| `TABLE_PLAN.md` | 8 | Table specifications |
| `SUPPLEMENTARY_MATERIAL.md` | 9 | Supplement design |
| `PROJECT_STATUS.md` | 10 | Project dashboard |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `scripts/` | Workspace-specific generation scripts |
| `figures/` | JDIQ figures (to be populated) |
| `tables/` | LaTeX tables (to be populated) |
| `supplementary/` | Supplementary package (to be populated) |
| `artifacts/` | Reproduction artifacts (to be populated) |

## Regenerate inventory

```bash
python papers/JDIQ_2026/scripts/build_master_inventory.py
```

## Canonical evidence sources (do not mix)

- **Main results:** `outputs/pub_vote_cmp_all4/paper_package/`
- **Baselines:** `experiments/final_method_gap_audit_20260711_221113/`
- **Failure taxonomy:** `experiments/failure_class_audit_20260711_212157/`
- **CARB:** `experiments/created_data_audit_20260711_232004/phase10/`
- **Claims:** `experiments/publication_readiness_audit_20260711_233629/final_claim_support_matrix.csv`

## Do not use

- `outputs/pub_vote_cmp_v2/` (superseded)
- `outputs/manuscript_artifacts/` (stale)
- `Consistency_Aware_Reranking*_IJCS.zip` (rejected framing)
