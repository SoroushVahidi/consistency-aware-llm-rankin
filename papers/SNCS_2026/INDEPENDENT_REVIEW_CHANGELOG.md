# Independent Review Changelog

Date: 2026-08-01

Branch: `papers/sncs-2026-foundation`

## Inputs Reviewed

- Read `papers/SNCS_2026/manuscript/main.pdf` first as an external reviewer.
- Checked `papers/SNCS_2026/manuscript/main.tex` and
  `papers/SNCS_2026/manuscript/references.bib` after the PDF read.
- Checked `papers/SNCS_2026/result_claims.yaml`,
  `papers/SNCS_2026/EVIDENCE_MAP.md`, `docs/claim_evidence_registry.yaml`, and
  canonical result files cited by the manuscript.
- Checked exact-repair, greedy-repair, graph-construction, ranking-extraction,
  and statistical-inference implementation files.
- Verified current SN Computer Science submission guidance from the official
  Springer Nature journal page.
- Verified closely related references through official publication pages and
  DOIs.

## Safe Manuscript Corrections Applied

- Reduced the manuscript keywords from 8 to 6 to match SN Computer Science's
  official 4-6 keyword guidance.
- Added PRP-Graph to Related Work as a recent graph-based LLM pairwise-ranking
  reference.
- Added exact MWFAS and linear-ordering references to clarify that exact repair
  is known optimization machinery used here as a diagnostic control.
- Widened Table 6's result column to improve PDF readability without changing
  any numerical result.
- Removed internal-only TeX source comments from `main.tex` so the source ZIP
  is clean if uploaded through the submission portal.

## Evidence Documentation Corrections Applied

- Updated a stale MDE value from `0.0207` to `0.0201` in current evidence
  documentation where the manuscript and `result_claims.yaml` already used the
  canonical `0.0201` value.
- No canonical result files were changed.
- `result_claims.yaml`, `EVIDENCE_MAP.md`, and `RESULTS_CROSS_CHECK.md` did not
  require result-value edits after the manuscript corrections.

## Review Artifacts Added

- `INDEPENDENT_MANUSCRIPT_REVIEW.md`
- `INDEPENDENT_PRESENTATION_REVIEW.md`
- `MISSING_REFERENCES_AND_BASELINES.md`
- `INDEPENDENT_REVIEW_ACTION_PLAN.md`
- `INDEPENDENT_REVIEW_CHANGELOG.md`

## Figure Prompts

No required figure-regeneration prompts were created. Figure 3 has an optional
minor readability improvement, but no figure defect rises to the level of a
submission blocker.

## Build Outcome

- Recompiled the manuscript with Tectonic.
- Final PDF: `papers/SNCS_2026/manuscript/main.pdf`
- Final page count: 42 A4 pages.
- Refreshed local source archive:
  `papers/SNCS_2026/submission/SNCS_2026_latex_source.zip`.
- Compile warnings are limited to existing template/underfull box warnings; no
  undefined citations or undefined cross-references were reported by the build.

## Prohibited Work Not Performed

- No new experiments were run.
- No canonical results were changed.
- No provider/API calls were made.
- No manuscript submission was attempted.
- No pull request was opened.
- No public release or DOI was created.
