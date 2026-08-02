# Final Submission Decision

Date: 2026-08-02 (freeze pass; prior cold-read 2026-08-01)
Branch: `papers/sncs-2026-foundation`

> Superseded for freeze/tag/DOI timing by
> [`RELEASE_CANDIDATE_DECISION.md`](RELEASE_CANDIDATE_DECISION.md)
> (verdict: READY AFTER MINOR LOGISTICAL FIXES). This file remains useful for
> the earlier cold-read upload list.

## Verdict

**SUBMISSION PACKAGE READY** (2026-08-02 freeze). See `SUBMISSION_FREEZE_CHANGELOG.md`.

Portal click still requires author confirmations below and explicit submit authorization.

## Blocking Issue

No scientific, manuscript-text, repository-access, or submission-package blocker
was found in the final cold read and independent review. The repository URL in
the manuscript is public and accessible:
`https://github.com/SoroushVahidi/consistency-aware-llm-rankin`.

## Author Confirmations Still Required

- Confirm the exact article-type label if the portal does not use "Original
  Research."
- Confirm whether the portal wants opposed reviewers entered explicitly; if so,
  use the conflict list in `SUBMISSION_METADATA.md`.

## Files To Upload

Primary manuscript:

1. `papers/SNCS_2026/manuscript/main.pdf`

Source files if requested by the portal:

1. `papers/SNCS_2026/manuscript/main.tex`
2. `papers/SNCS_2026/manuscript/references.bib`
3. `papers/SNCS_2026/template/sn-jnl.cls`
4. `papers/SNCS_2026/template/bst/sn-basic.bst`
5. `papers/SNCS_2026/figures/f1_pipeline.pdf`
6. `papers/SNCS_2026/figures/f2_bm25_share.pdf`
7. `papers/SNCS_2026/figures/f3_cycle_decomposition.pdf`
8. `papers/SNCS_2026/figures/f4_bootstrap_forest.pdf`
9. `papers/SNCS_2026/figures/f5_exact_vs_greedy_gap.pdf`

Portal text/supporting metadata:

1. `papers/SNCS_2026/SUBMISSION_METADATA.md`
2. `papers/SNCS_2026/COVER_LETTER.md`
3. `papers/SNCS_2026/REVIEWER_SUGGESTIONS.md`
4. `papers/SNCS_2026/KEYWORDS_RUNNING_TITLE.md`
5. `papers/SNCS_2026/GENERATIVE_AI_DISCLOSURE.md`

Local source archive prepared for upload if appropriate:

1. `papers/SNCS_2026/submission/SNCS_2026_latex_source.zip`

## Supplementary Files

Upload supplementary/source files separately if the portal has separate slots
for manuscript PDF, source files, cover letter, reviewer suggestions, and
supplementary code/data. Do not upload raw provider request/response payloads.

If the portal permits a code/data ZIP and the repository remains private, prepare
a separate sanitized code/artifact archive from the release plan rather than
using the LaTeX source ZIP alone.

## Submission Order

1. Resolve the repository-access route or prepare a sanitized code/artifact
   archive.
2. Upload `main.pdf` as the manuscript file.
3. Upload or paste the abstract, keywords, funding, declarations, data/code
   availability, generative-AI disclosure, acknowledgments, and cover letter
   from `SUBMISSION_METADATA.md`.
4. Upload `SNCS_2026_latex_source.zip` if source files are requested.
5. Enter suggested reviewers from `REVIEWER_SUGGESTIONS.md`.
6. Enter opposed reviewers only if the portal asks for them.
7. Verify generated proof/PDF in the portal, including title page, figures,
   tables, references, declarations, acknowledgments, and URLs.
8. Stop before final submission unless the author explicitly authorizes
   submission.

## Source ZIP

A LaTeX source ZIP should be prepared locally. It is appropriate because
Springer portals often request source files after or during submission, and it
keeps the submission package independent of local build paths.
