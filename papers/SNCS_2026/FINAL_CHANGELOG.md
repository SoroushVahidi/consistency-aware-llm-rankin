# Final Stage Changelog

Date: 2026-08-01
Branch: `papers/sncs-2026-foundation`

## Manuscript Changes

- Corrected the smallest Holm-adjusted p-values in Table `tab:retrieval-holm` and adjacent prose:
  - Active canonical family: 0.240.
  - Full canonical family: 0.720.
  - Holm-rejected counts remain unchanged: 0/20 and 0/60.
- Split dense Related Work citation clusters so no sentence contains more than four cited works.
- Renamed `Acknowledgements` to `Acknowledgments` for American English and Springer style consistency.
- Renamed the backmatter declaration heading to `Statements and Declarations`.

## Evidence Synchronization

- Updated `result_claims.yaml` and `RESULTS_CROSS_CHECK.md` to document the corrected canonical-family smallest adjusted p-values.
- Updated active workspace notes in `README.md`, `GENERATIVE_AI_DISCLOSURE.md`, and Stage 6 reports to remove stale placeholder-style language.

## Submission Package Added

- `PRE_SUBMISSION_SCIENTIFIC_AUDIT.md`
- `SIMULATED_REVIEWS.md`
- `REPRODUCIBILITY_AUDIT.md`
- `JOURNAL_COMPLIANCE_CHECKLIST.md`
- `COVER_LETTER.md`
- `REVIEWER_SUGGESTIONS.md`
- `KEYWORDS_RUNNING_TITLE.md`
- `HIGHLIGHTS.md`
- `SUBMISSION_CHECKLIST.md`
- `FINAL_CHANGELOG.md`

## Final Cold-Read / Portal-Preparation Pass

- Added `COLD_READ_REPORT.md` from a PDF-only cold read of the compiled
  manuscript.
- Added `SUBMISSION_METADATA.md` with copy-ready portal fields, cover-letter
  text, declarations, suggested reviewers, and opposed-reviewer/conflict notes.
- Added `ARCHIVAL_RELEASE_PLAN.md` documenting the recommended release tag,
  include/exclude policy, raw-provider exclusion, license considerations, and
  DOI steps.
- Added `FINAL_SUBMISSION_DECISION.md` with upload files, submission order, and
  the remaining repository-access confirmation.
- Updated `REVIEWER_SUGGESTIONS.md`: removed Guido Zuccon due to a possible
  perceived Google-support conflict and added Nir Ailon for rank-aggregation and
  feedback-arc-set expertise.
- Prepared `submission/SNCS_2026_latex_source.zip` with 9 LaTeX-source entries:
  `main.tex`, `references.bib`, five figure PDFs, `sn-jnl.cls`, and
  `sn-basic.bst`.
- No manuscript results, canonical numbers, or scientific conclusions were
  changed in this pass.

## Scientific Scope

- No new experiments were run.
- No provider calls were made.
- No new analyses or scientific claims were introduced.
- The central scientific conclusion is unchanged.

## Final QA

- Tectonic compile succeeded and produced `manuscript/main.pdf`.
- Final PDF page count: 41 A4 pages.
- Structured abstract word count: 196 words.
- Citation and reference checks: 59 cited keys, 62 unique BibTeX entries, 0 missing cited keys, 0 duplicate BibTeX keys.
- Cross-reference checks: 65 labels, all unique; 0 missing `\ref`/`\eqref` targets.
- PDF text scan: no unresolved-reference markers, placeholders, stale `0.384` result text, or forbidden out-of-scope manuscript terms.
- Secret scan: PASS, 0 findings.
- `git diff --check`: PASS.

Known residual compile warnings:

- `algorithm.sty` emits an invalid UTF-8 warning outside the manuscript source.
- The Springer template/table-heavy layout produces underfull box warnings.
- The PDF backend emits duplicate object warnings for floats. No fatal error, missing citation, or missing reference warning was observed.

## Final Cold-Read Pass QA

- Recompiled with Tectonic on 2026-08-01; output remains a 41-page A4 PDF.
- Visual PDF QA sampled the title page, pipeline figure page, results
  figure/table pages, declarations, and final reference page. No meaningful
  layout problem was found.
- `git diff --check`: PASS.
- Secret scan: PASS, 0 findings across 2,795 scanned files.
- Citation-key validation: 59 cited keys, 62 BibTeX entries, 0 missing cited
  keys, 0 duplicate BibTeX keys.
- Reference-label validation: 65 labels, 160 `\ref`/`\eqref`-style references,
  0 missing targets, 0 duplicate labels.
- Manuscript/PDF scan found no unresolved placeholders, TODO/FIXME markers,
  stale superseded p-values, Gurobi manuscript evidence, DeepInfra mention,
  Outcome-F/Dimension-F leakage, or repository-report language.
- The only broad stale/excluded-term hits outside the manuscript were
  intentional exclusion notes in `ARCHIVAL_RELEASE_PLAN.md` and
  `FINAL_SUBMISSION_DECISION.md` about `gurobi.lic` and raw provider payloads.
