# Final Submission Materials Report

Date: 2026-07-15

## 1. Initial state

- Repository: `consistency-aware-llm-rankin`
- Branch at start: `main`
- Local `HEAD` at start: `e873017e1d1f28ff140ef0a006fba8aeaa4edcb6`
- `origin/main` at start: `e873017e1d1f28ff140ef0a006fba8aeaa4edcb6`
- Start-state branch sync: matched
- Frozen anonymous main manuscript PDF:
  - Path: `papers/JDIQ_2026/manuscript/main.pdf`
  - SHA-256: `93265e1ab13571101d4ef260b3afb61c6089a03e257e7c9e49fd79c2640f3840`
  - Page count: `10`
- Frozen anonymous supplement PDF:
  - Path: `papers/JDIQ_2026/manuscript/supplement.pdf`
  - SHA-256: `31c5f4a5006af24ba12adeb14f3a861e8159250a07779fed86be100d2ac6c4b3`
  - Page count: `8`

## 2. Current JDIQ submission-material findings

Best current official evidence consulted:

- JDIQ author guidelines: supplementary electronic material can accompany a submission.
  - `https://dl.acm.org/journal/jdiq/author-guidelines`
- JDIQ call for papers: review is double-anonymous and such submissions must include a cover letter as the first page(s) of the submitted manuscript.
  - `https://dl.acm.org/journal/jdiq/call-for-papers`

Material-status conclusion for this freeze:

- Anonymous supplementary material: permitted and prepared.
- Cover letter: expected by JDIQ double-anonymous submission guidance and prepared anonymously.
- Highlights: no official JDIQ requirement was found in the consulted official ACM/JDIQ pages; prepared as an optional convenience file because it was explicitly requested.
- Graphical abstract: no official JDIQ requirement was found in the consulted official ACM/JDIQ pages.

## 3. Finalized submission materials

Created or finalized under `papers/JDIQ_2026/submission/final_submission_materials/`:

- `anonymous_supplementary.zip`
- local unpacked `anonymous_supplementary/` working copy used for audit and ZIP validation
- `highlights.pdf`
- `highlights.tex`
- `cover_letter.pdf`
- `cover_letter.tex`
- `README.md`
- `CHECKSUMS.sha256.txt`

Output checksums:

- `anonymous_supplementary.zip`
  - `6e59aa7dcbc92302c0258b8f47f456d9193ad2b35395050276c422b4fe9388dd`
- `highlights.pdf`
  - `241a72bb27dc8fedf1ba5f7afb3484265a2bdc2d182a45d3788a4ea868bfb28c`
- `cover_letter.pdf`
  - `f0a73eca53a9d3a914ca4b1db7533ff6eb6ca0d6ee3fff5d78a0eaf3f62b9e26`

## 4. Supplementary ZIP contents

The anonymous reviewer-facing ZIP includes:

- anonymous README and reproduction guide;
- data-availability note;
- figure inventory and figure-data verification report;
- final anonymous manuscript and supplement source/PDFs;
- manuscript figure assets and figure-generation code;
- canonical Python source, driver scripts, and regression tests;
- canonical aggregate tables for the main Task 1–10 evidence families;
- task-report tables and claim-audit scripts limited to public-safe material;
- package metadata, environment metadata, file manifest, and checksums.

Excluded from the ZIP:

- Gmail-derived rejection material;
- reviewer correspondence;
- internal readiness scores;
- local absolute paths in packaged copies;
- personal emails, affiliations, GitHub profile URLs, and Research Square identifiers;
- private credentials, tokens, and license files;
- third-party datasets not appropriate for redistribution;
- caches, venvs, shell history, and temporary logs.

## 5. Anonymity and integrity audit

Final packaged-copy checks performed:

- recursive identity scan over text files and extracted PDF text;
- recursive secrets scan over text-bearing files;
- PDF metadata scan;
- ZIP internal-path scan;
- ZIP integrity test;
- ZIP extraction parity test against the unpacked working copy;
- checksum verification against the packaged manifest.

Important scan refinements:

- the audit explicitly allowed the unrelated cited author string `Soroush Vosoughi` and the generic ACM permissions email `permissions@acm.org` as non-identity-bearing false positives;
- the secrets scan explicitly allowed test placeholder strings used in regression tests, while still rejecting real credential-like values.

Final status: clean.

## 6. Build and validation record

Build scripts added:

- `papers/JDIQ_2026/submission/scripts/build_anonymous_supplementary.py`
- `papers/JDIQ_2026/submission/scripts/validate_submission_materials.py`

Primary long-running logged sessions:

- `jdiq_submission_supplement`
- `jdiq_submission_highlights`
- `jdiq_submission_cover_letter`
- `jdiq_submission_validation`

Logs and manifests were written locally under:

- `reports/final_submission_materials_20260715/logs/`
- `reports/final_submission_materials_20260715/manifests/`

Final validation result:

- `python papers/JDIQ_2026/submission/scripts/validate_submission_materials.py`
- Result: `17/17 checks passed`

Validated conditions:

- required submission files present;
- final title reflected in the package README;
- reproducibility guide updated to `617 passed`;
- package freeze manifest aligned with package metadata;
- identity scan clean;
- secrets scan clean;
- manuscript/supplement PDF metadata clean;
- highlights and cover-letter PDF metadata clean;
- ZIP integrity and internal paths clean;
- ZIP extraction matches unpacked directory;
- package checksums verify.

## 7. Files intended for commit

- `papers/JDIQ_2026/submission/final_submission_materials/anonymous_supplementary.zip`
- `papers/JDIQ_2026/submission/final_submission_materials/highlights.pdf`
- `papers/JDIQ_2026/submission/final_submission_materials/highlights.tex`
- `papers/JDIQ_2026/submission/final_submission_materials/cover_letter.pdf`
- `papers/JDIQ_2026/submission/final_submission_materials/cover_letter.tex`
- `papers/JDIQ_2026/submission/final_submission_materials/README.md`
- `papers/JDIQ_2026/submission/final_submission_materials/CHECKSUMS.sha256.txt`
- `papers/JDIQ_2026/submission/scripts/build_anonymous_supplementary.py`
- `papers/JDIQ_2026/submission/scripts/validate_submission_materials.py`
- `reports/final_submission_materials_20260715/FINAL_REPORT.md`

## 8. Files intentionally excluded from commit

- local build logs and tmux manifests under `reports/final_submission_materials_20260715/logs/` and `manifests/`;
- unrelated earlier task reports and visual-audit dumps;
- local-only anonymous-package working diagnostics outside the finalized materials folder;
- temporary LaTeX intermediates not needed for submission.

## 9. Remaining human-only issues

- Research Square preprint decision.
- Author metadata completion in the submission system.
- ORCID entry.
- Final live submission-system verification immediately before upload.

## 10. GitHub paths

Repository:

- `https://github.com/SoroushVahidi/consistency-aware-llm-rankin`

Exact manuscript source path on GitHub:

- `https://github.com/SoroushVahidi/consistency-aware-llm-rankin/blob/main/papers/JDIQ_2026/manuscript/main.tex`

Exact supplement source path on GitHub:

- `https://github.com/SoroushVahidi/consistency-aware-llm-rankin/blob/main/papers/JDIQ_2026/manuscript/supplement.tex`

Submission-material directory on GitHub:

- `https://github.com/SoroushVahidi/consistency-aware-llm-rankin/tree/main/papers/JDIQ_2026/submission/final_submission_materials`

## 11. Commit and push note

This committed report cannot embed the exact SHA of the final commit that
contains the report itself without a self-reference cycle. The exact pushed
commit SHA, push result, and local-versus-remote equality check are therefore
recorded in the terminal handoff accompanying this freeze and can be verified
directly from `git rev-parse HEAD`, `git rev-parse origin/main`, and the
repository history after push.

## 12. Final judgment

Submission materials are ready for author upload review, subject only to the
human-only items listed above.
