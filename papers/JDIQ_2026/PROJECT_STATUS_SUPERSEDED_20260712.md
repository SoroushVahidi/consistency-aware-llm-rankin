# Project Status — JDIQ 2026 Submission

> **SUPERSEDED (as of 2026-07-14); renamed 2026-07-28** from
> `PROJECT_STATUS.md` to disambiguate it from the repository-root
> `PROJECT_STATUS.md` (a different, actively-maintained document about
> current branch/repository state — see that file, not this one, for
> current status). This is a pre-writing readiness snapshot ("Overall
> readiness: 22%", "Writing 0%"); the manuscript is now a complete draft.
> It also lists the six-way failure taxonomy as a "Strong" evidence
> source, which the finished manuscript explicitly excludes as evidence.
> Do not use this file's percentages or evidence ratings as current
> status.

**Prepared:** 2026-07-12  
**Workspace:** `papers/JDIQ_2026/`  
**Target venue:** ACM Journal of Data and Information Quality (JDIQ)  
**Paper type:** Technical / Research paper (~20–23 pages)

---

## Overall readiness: **22%**

| Dimension | Readiness | Weight | Weighted |
|-----------|-----------|--------|----------|
| Evidence / science | 90% | 25% | 22.5% |
| Writing | 0% | 30% | 0% |
| Figures | 15% | 15% | 2.3% |
| Tables | 55% | 10% | 5.5% |
| Artifacts / repro | 40% | 10% | 4.0% |
| CARB / dataset | 35% | 5% | 1.8% |
| Submission admin | 10% | 5% | 0.5% |
| **Total** | | | **~22%** |

**Interpretation:** The scientific evidence is strong and audit-complete. The manuscript infrastructure is now designed. Actual writing and figure/table formatting remain the critical path.

---

## Dimension details

### Writing readiness: **0%**

| Item | Status |
|------|--------|
| LaTeX skeleton (`acmart`) | Not started |
| Abstract | Not started |
| §1–§13 prose | Not started |
| Bibliography | Partial source (`LITERATURE_ALIGNMENT.md`) |
| CCS concepts | Not started |
| Cover letter | Not started |

**Blueprint complete:** `MANUSCRIPT_OUTLINE.md`, `CANONICAL_PAPER_STORY.md`

---

### Figure readiness: **15%**

| Item | Status |
|------|--------|
| Fig 1 pipeline schematic | Not started |
| Fig 2 cyclicity | Script exists; needs regeneration |
| Fig 3 BEW/PIC | Script exists; needs regeneration |
| Fig 4 bootstrap forest | Script exists; needs regeneration |
| Fig 5 baseline bar | Partial; needs extension |
| Fig 6 failure classes | Not started |
| Fig 7–8 optional | Not started |

**Plan complete:** `FIGURE_PLAN.md`

---

### Table readiness: **55%**

| Item | Status |
|------|--------|
| T4 structural metrics | **Data ready** (canonical CSV) |
| T5 bootstrap deltas | **Data ready** (canonical CSV) |
| T6 baseline comparison | **Data ready** (gap audit CSV) |
| T7 failure taxonomy | **Data ready** (failure audit CSV) |
| T9 real-LLM summary | **Data ready** (summary MD) |
| T10 CARB stats | **Data ready** (created data audit) |
| T1–T3 conceptual | Not written |
| LaTeX formatting | Not started for any table |

**Plan complete:** `TABLE_PLAN.md`

---

### Artifact / reproducibility readiness: **40%**

| Item | Status |
|------|--------|
| Reproduction scripts | Exist (`run_publication_vote_suite.py`, etc.) |
| `REPRODUCTION_Q1.md` | Exists; needs JDIQ update |
| Anonymous artifact package | Not prepared |
| Environment pinning | `requirements.txt` exists |
| Checksums for canonical CSVs | Not generated |
| Supplement README | Not written |

**Plan complete:** `SUPPLEMENTARY_MATERIAL.md`

---

### Dataset (CARB) readiness: **35%**

| Item | Status |
|------|--------|
| Schema proposed | **Complete** (`phase10/PROPOSED_DATASET_SCHEMA.md`) |
| Release structure proposed | **Complete** |
| Feature dictionary | **Complete** (14+ groups) |
| Data card | **Not written** |
| License | **Not chosen** |
| Feature files packaged | **Not built** |
| Leakage documentation | **Drafted** in created_data_audit |

---

## Evidence strength (for confidence)

| Contribution | Evidence status |
|-------------|-----------------|
| Structural DQ measurement (4 datasets) | **Strong** — canonical CSVs committed |
| Repair–retrieval decoupling | **Strong** — bootstrap + failure taxonomy |
| Baseline comparison | **Strong** — pooled 1020 records |
| Failure taxonomy | **Strong** — 6 classes, manual + automatic |
| CARB benchmark | **Moderate** — schema ready; packaging needed |
| Real-LLM validation | **Moderate** — bounded N=80 |
| Runtime/memory | **Weak** — synthetic only |
| Selector | **Exploratory** — supplement only |

---

## Remaining work

### Critical path (blocks submission)

1. LaTeX `acmart` skeleton with JDIQ formatting
2. Full manuscript prose (§1–§13)
3. Regenerate figures (Figs 2–6)
4. Format tables (T1–T10) in LaTeX
5. CARB data card
6. Anonymous supplementary package
7. Bibliography completion

### Parallel track (can proceed alongside writing)

- CARB feature packaging
- Checksum generation
- Cover letter drafting
- Supplementary appendix PDFs

### Explicitly not needed

- New algorithm development
- New datasets
- Paid API reruns
- Selector retraining
- Memory benchmarks (optional only)

---

## Timeline estimate

| Phase | Duration | Cumulative |
|-------|----------|------------|
| LaTeX setup + table/figure generation | 1 week | Week 1 |
| First draft (all sections) | 2–3 weeks | Week 3–4 |
| Supplementary packaging | 1 week (parallel) | Week 3–4 |
| Internal review + consistency check | 1 week | Week 5 |
| Revision + anonymization | 1 week | Week 6 |
| Final polish + submit | 0.5 week | **Week 6–7** |

**Estimated weeks until submission:** **6–8 weeks** (part-time) / **4–5 weeks** (full-time)

---

## Risk register

| Risk | Severity | Mitigation |
|------|----------|------------|
| JDIQ desk-reject for IR-only framing | Medium | Lead with DQ vocabulary (story doc) |
| Reviewer demands prior-only paired test | Medium | Derive from per-query CSVs if available |
| BEW/PIC circularity attack | Medium | §11 threats; qualify claims |
| Stale figure/table numbers | High | Regenerate only from `pub_vote_cmp_all4` |
| IJCS overlap concern | Low | ≥30% new material; DQ reframing documented |
| CARB release legal issues | Medium | Feature-only release; no raw text |

---

## Workspace inventory

| File | Purpose | Status |
|------|---------|--------|
| `JDIQ_GUIDELINE_SUMMARY.md` | Journal requirements | **Complete** |
| `MASTER_EVIDENCE_INVENTORY.csv` | 69 artifacts catalogued | **Complete** |
| `CANONICAL_PAPER_STORY.md` | Single narrative | **Complete** |
| `MANUSCRIPT_OUTLINE.md` | Section blueprint | **Complete** |
| `SECTION_EVIDENCE_MAP.csv` | Evidence → section mapping | **Complete** |
| `MISSING_COMPONENTS.md` | Gap analysis | **Complete** |
| `FIGURE_PLAN.md` | Figure specifications | **Complete** |
| `TABLE_PLAN.md` | Table specifications | **Complete** |
| `SUPPLEMENTARY_MATERIAL.md` | Supplement design | **Complete** |
| `PROJECT_STATUS.md` | This dashboard | **Complete** |
| `scripts/build_master_inventory.py` | Inventory generator | **Complete** |

---

## Next actions (recommended order)

1. Initialize `papers/JDIQ_2026/manuscript/main.tex` with `\documentclass[manuscript]{acmart}`
2. Run `scripts/build_manuscript_assets.py` → copy figures to `papers/JDIQ_2026/figures/`
3. Write `scripts/fig06_failure_classes.py` and `fig01_pipeline.py`
4. Begin §1 Introduction using `CANONICAL_PAPER_STORY.md`
5. Format Tables 4–7 from canonical CSVs into LaTeX
6. Draft CARB `DATA_CARD.md` in `supplementary/CARB/`
7. Internal consistency pass against `final_claim_support_matrix.csv`

---

## Decision log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-07-12 | Target JDIQ (not JIIS/IRRJ) | DQ framing stronger than IR framing; CARB fits curation mission |
| 2026-07-12 | Diagnostic DQ paper (not method paper) | Evidence contradicts positive method claims |
| 2026-07-12 | CARB as supplement (not main contribution) | Created data audit: moderate dataset-paper potential |
| 2026-07-12 | No new experiments before submission | All mandatory evidence exists |
| 2026-07-12 | Full rewrite (not IJCS revision) | Rejected framing incompatible with evidence |

---

*This dashboard should be updated as writing progresses. Re-run `scripts/build_master_inventory.py` if repository artifacts change.*
