# Release Candidate Decision

**Date:** 2026-08-01  
**Branch:** `papers/sncs-2026-foundation`

## Verdict

**READY AFTER MINOR LOGISTICAL FIXES**

Scientific content, public repository access, manuscript PDF/source ZIP, and
smoke-tested reproduction entry points are ready for a submission freeze.
Remaining items are portal logistics and author confirmations — not manuscript
science blockers.

## Blockers

None that prevent preparing the freeze commit or uploading a draft package for
author review.

Previously material issues already resolved before this pass:

- Repository is **public** (URL in Code/Data Availability resolves).
- Funding vs Acknowledgments separation is in the current `main.tex` / PDF.
- Stale LaTeX source ZIP (pre-funding-edit) was regenerated to match `main.tex`.

## Author confirmations required

1. Exact portal article-type label if not “Original Research.”
2. ORCID (if any) — do not invent.
3. Phone / full postal address if the portal requires them.
4. Any structured funding award IDs.
5. Exact subject-area classification codes in the portal taxonomy.
6. Whether opposed reviewers must be entered (conflict list ready if yes).
7. Whether highlights are requested.
8. Authorization to create annotated tag `sncs-2026-submission-v1`.
9. Authorization to click final journal submit (explicitly out of scope here).
10. Authorization before any DOI/Zenodo public archive.

## Exact commit to submit

Treat the novelty/front-matter revision commit recorded in
`SUBMISSION_FREEZE.md` (PDF/ZIP hashes
`70bd3bb9…` / `bfe935f0…`) as the current submission freeze candidate.
The earlier packaging commit `f42ad47f66fe73c14f4cac52b23876b264c10739`
is superseded for manuscript PDF/ZIP contents.

## Exact files to upload

Per `UPLOAD_MANIFEST.md`:

1. `papers/SNCS_2026/manuscript/main.pdf`
2. `papers/SNCS_2026/submission/SNCS_2026_latex_source.zip`
3. Cover letter text from `COVER_LETTER.md`
4. Portal metadata from `SUBMISSION_METADATA.md` / `PORTAL_DRY_RUN.md`
5. Suggested reviewers from `REVIEWER_SUGGESTIONS.md`
6. Separate figure files **only if** the portal requires them
7. Public code URL: https://github.com/SoroushVahidi/consistency-aware-llm-rankin

Do **not** upload internal freeze/review/smoke Markdown as supplementary files.

## Tag timing

| Action | Recommendation |
|---|---|
| Create annotated tag `sncs-2026-submission-v1` | **Immediately before** final portal submit, on the freeze commit, after author confirms upload set |
| Push tag / GitHub Release | Only with explicit authorization |
| Do not create tag in this packaging pass | Confirmed — not created |

## DOI-backed archive timing

| Action | Recommendation |
|---|---|
| Zenodo / DOI archive at submission | **Wait** — not required while the GitHub repo is public and cited |
| DOI-backed archive | Prefer **at acceptance** (or when the author explicitly wants a submission-time archive), after sanitization per `RELEASE_CANDIDATE_PLAN.md` and `LICENSE_AND_DISTRIBUTION_AUDIT.md` |
| Create DOI in this pass | **No** |

## Supporting package index

| Doc | Role |
|---|---|
| `SUBMISSION_FREEZE.md` | Exact hashes / metrics / paths |
| `RELEASE_CANDIDATE_PLAN.md` | Tag/release notes draft (unpublished) |
| `PUBLIC_REPOSITORY_REVIEW.md` | Reviewer-arrival audit |
| `REPRODUCIBILITY_QUICKSTART.md` | Reviewer commands |
| `RELEASE_CANDIDATE_SMOKE_TEST.md` | What was actually run |
| `UPLOAD_MANIFEST.md` | Portal file list |
| `PORTAL_DRY_RUN.md` | Copy-ready fields |
| `LICENSE_AND_DISTRIBUTION_AUDIT.md` | License inventory |
| `RELEASE_CANDIDATE_CHANGELOG.md` | This pass’s changes |
