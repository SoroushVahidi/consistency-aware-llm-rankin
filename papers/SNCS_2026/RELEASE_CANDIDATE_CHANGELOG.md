# Release Candidate Changelog (2026-08-01)

Freeze / release-candidate packaging pass on `papers/sncs-2026-foundation`.
No scientific results, experiments, provider calls, tags, DOIs, or journal
submissions were created.

## Added

- `SUBMISSION_FREEZE.md` — freeze ledger (SHA filled in follow-up pin commit)
- `RELEASE_CANDIDATE_PLAN.md` — unpublished tag/release plan for `sncs-2026-submission-v1`
- `PUBLIC_REPOSITORY_REVIEW.md` — reviewer-arrival audit of the public repo
- `REPRODUCIBILITY_QUICKSTART.md` — labeled fast / full / solver / API tracks
- `RELEASE_CANDIDATE_SMOKE_TEST.md` — smoke-test record
- `UPLOAD_MANIFEST.md` — portal upload inventory
- `PORTAL_DRY_RUN.md` — copy-ready portal fields (no submit)
- `LICENSE_AND_DISTRIBUTION_AUDIT.md` — license/distribution inventory
- `RELEASE_CANDIDATE_DECISION.md` — verdict: READY AFTER MINOR LOGISTICAL FIXES
- `RELEASE_CANDIDATE_CHANGELOG.md` — this file

## Updated

- `papers/SNCS_2026/submission/SNCS_2026_latex_source.zip` — regenerated so
  `main.tex` matches the Funding/Acknowledgments separation (ZIP had been stale
  relative to the 39-page PDF)
- `papers/SNCS_2026/README.md` — replaced obsolete Stage-1 skeleton framing with
  submission-package orientation
- Root `README.md` — added SNCS manuscript + reproducibility quickstart pointers
  without turning the README into a second paper
- `ARCHIVAL_RELEASE_PLAN.md` — corrected repository visibility to public; aligned
  suggested tag name with `sncs-2026-submission-v1`

## Verified (no content change)

- Manuscript PDF SHA-256 `7980e146…` (39 pages, 196-word abstract, 5 figures,
  6 tables, 1 algorithm, 62 cited references)
- Public GitHub URL resolves
- Smoke: imports, CLI help, 81 subset tests, synthetic example, canonical row
  counts, ZIP→PDF compile (39 pages)

## Explicitly not done

- No Git tag / GitHub Release
- No Zenodo DOI
- No journal portal submission
- No new experiments or provider API calls
- No changes to canonical scientific numbers
