# Public Repository Review (Reviewer Arrival Audit)

**Date:** 2026-08-01  
**Perspective:** a reviewer who opens the public repository URL cited in the
manuscript Code/Data Availability statement.  
**Repository:** https://github.com/SoroushVahidi/consistency-aware-llm-rankin  
**Visibility verified:** public.

## Checklist against root README

| Reviewer need | Root README status before this pass | Classification | Action taken |
|---|---|---|---|
| Research question | Clear in “Project identity” | Acceptable as written | None |
| Principal conclusion (null/conditional repair result) | Clear, correctly framed as thesis | Acceptable as written | None |
| How the manuscript relates to the repository | Pointed primarily to `papers/JDIQ_2026/`; SNCS package under-signposted | Strongly recommended | Added SNCS pointer in “Where to look”; clarified dual-manuscript relationship without expanding into a second paper |
| Which results are canonical | Strong via `docs/CONTRIBUTIONS.md` links and non-contribution list | Acceptable as written | None beyond SNCS pointer |
| How to reproduce headline tables/figures | Points to `docs/REPRODUCTION_CANONICAL.md` (JDIQ-oriented map of same evidence) | Strongly recommended | Added `papers/SNCS_2026/REPRODUCIBILITY_QUICKSTART.md` and linked it |
| Required software / solver deps | Present (Python, SCIP via `[exact]`, Gurobi optional) | Acceptable as written | None |
| Approximate runtime | Partial (cloud-validation / synthetic); not SNCS-scoped | Optional | Covered in SNCS quickstart, not duplicated as a README essay |
| Which experiments need external APIs | Stated for real-LLM / provider scripts; raw transcripts excluded | Acceptable as written | Reinforced in SNCS quickstart |
| Which experiments are fully local | Synthetic + canonical CSV verification + SCIP tests | Acceptable as written | Reinforced in SNCS quickstart |
| Six-query real-LLM pilot vs primary study | Mentioned (n=6, not ~120 rows) | Acceptable as written | None |
| Where archived/historical work lives | `papers/_archive/`, historical docs, `outputs/pub_vote_cmp_*` warnings | Acceptable as written | None |

## Findings

### Blocking for submission

None found for repository accessibility. The manuscript URL resolves to a
public repository. Code/data availability text matches the public surface
(raw provider payloads correctly excluded).

### Strongly recommended

1. **SNCS manuscript under-linked from root README** — fixed this pass.
2. **`papers/SNCS_2026/README.md` still described Stage-1 skeleton** — fixed this pass so a reviewer landing in the paper directory is not told the manuscript is unfinished.
3. **Commit-pinned reproduction URL** — recorded in `SUBMISSION_FREEZE.md` / quickstart; manuscript keeps the stable repo homepage URL (appropriate for journals).

### Optional

1. Approximate wall-clock times for full Layer-1 regeneration could be summarized in the root README; left in the SNCS quickstart to avoid README bloat.
2. A one-line “current paper” badge at the very top of the README; deferred.

### Acceptable as written

- Research question and principal conclusion.
- Canonical vs non-canonical warnings (especially Gurobi internal-only studies).
- Pilot independence correction (6 queries).
- Install / validation entry points.
- Historical package cautions.

## Residual reviewer friction (not blockers)

- The repository still contains multiple paper directories (`JDIQ_2026`, `SNCS_2026`, `negative_result_2026`, `_archive`). That is intentional; the README now points to SNCS explicitly.
- `docs/REPRODUCTION_CANONICAL.md` remains titled for JDIQ but maps the same classical evidence used by SNCS; the SNCS quickstart is the reviewer-facing front door.
- `ARCHIVAL_RELEASE_PLAN.md` previously said the repository was private; visibility is now public (corrected in related freeze docs).
