# JDSA preparation package — 26 October 2026

The manuscript is prepared for **Regular Paper**, subscription route (no APC), but **submission readiness is not confirmed**. Do not submit, contact the journal, merge this branch, or make the repository public on the basis of this package.

- [Identified main PDF](manuscript/main.pdf), [Online Resource 1](manuscript/ESM_1.pdf), and [editable main source](manuscript/main.tex).
- [Anonymous fallback](manuscript/main_anonymous.pdf) and [fallback supplement](manuscript/supplement_anonymous.pdf), retained because the journal-specific review model remains unconfirmed. Necessary scholarly self-citations remain; this is not a guarantee of unlinkability.
- [Submission checklist](SUBMISSION_CHECKLIST.md), [change log](CHANGELOG.md), [availability and reproduction](AVAILABILITY_AND_REPRODUCTION.md), [reference audit](REFERENCE_AUDIT.md), [visibility audit](REPOSITORY_VISIBILITY_AUDIT.md), [validation](VALIDATION_REPORT.md).
- `packages/JDSA_sources.zip` are flat editable archives with compiled PDFs. They are preparation artifacts, not uploads.
- Local editor-only title page, cover letter and overlap disclosure: `editorial/*.tex` and `editorial/*.pdf`, also `packages/editorial_private.zip`. These files are intentionally excluded from Git and the manuscript source archives. Review them locally.

The latest finalized IJIT scientific state was untracked on the prior manuscript worktree. Commit `53083f31a2f698ecc29ba284f8eb7d070567aefd` preserves that exact source/PDF snapshot in `audit/finalized_IJIT_source.zip`; its foundation is `c5cfafab73cff427e91fc1fd94aca7cbbae6d5d1`. See `audit/AUTHORITATIVE_SOURCE.json`. Earlier `origin/main` PDF updates do not supersede the final corrected sources. The prior IJIT directory and unrelated work are preserved.

Build: `bash papers/JDSA_2026/manuscript/build.sh` from repository root. It compiles identified and fallback versions using pdfLaTeX/BibTeX, without scientific execution. Validate: `python papers/JDSA_2026/scripts/validate_package.py`. Final PDFs and the JSON validation report are versioned; intermediate logs remain local under `manuscript/build/`.
