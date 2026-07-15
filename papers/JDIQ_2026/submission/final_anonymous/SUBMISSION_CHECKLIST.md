# JDIQ Submission Checklist

Status as of this repository state (updated in Task 6, the final
submission-freeze pass). Items marked DONE were verified directly against
the current `main.tex`/`main.pdf`/repository; items marked TODO require
action outside this repository (author identity, venue portal, external
accounts) that cannot be completed from here.

## Manuscript

- [x] **DONE** — Compiles cleanly: 0 undefined references, 0 multiply-
  defined labels, 0 missing citations (`latexmk -pdf -interaction=nonstopmode
  -halt-on-error main.tex`).
- [x] **DONE** — `\documentclass[manuscript,anonymous,review]{acmart}` —
  correct mode for JDIQ double-anonymous review.
- [x] **DONE** — CCS concepts present and relevant: Data cleaning, Data
  quality, Retrieval models and ranking.
- [x] **DONE** — Keywords present (`preference graphs, data quality,
  structural inconsistency, rank aggregation, ...`).
- [x] **DONE** — Abstract present, states problem/methodology/findings/
  robustness/practical implications (see Task 5 abstract polish).
- [x] **DONE** — Author block is `Anonymous Author(s)` /
  `Institution redacted for review` — correct for anonymous review.
- [ ] **TODO (author action)** — Real author names, affiliations, ORCID
  iDs, and emails must be added for camera-ready (not before, if venue
  requires double-anonymous review through this stage). Check JDIQ's
  current instructions for whether ORCID is mandatory at submission or
  only camera-ready.
- [ ] **TODO (author action)** — `\begin{acks}\end{acks}` is intentionally
  empty for anonymous review; fill in funding/acknowledgment text for
  camera-ready.
- [ ] **TODO (author action)** — Confirm current JDIQ length guidance
  against the manuscript's 40 pages (typeset, per `pdfinfo main.pdf` as of
  Task 6); JDIQ journal articles generally have no hard page cap, but
  verify against current author guidelines rather than assuming.
- [ ] **TODO (author action)** — Final proofread pass for typos/grammar;
  this project's revision passes focused on scientific accuracy,
  reproducibility, and structural/consistency editing, not a line-level
  copyedit.

## Bibliography

- [x] **DONE** — All 29 `\cite` keys used in `main.tex` exactly match the
  29 keys defined in `references.bib` (no missing, no unused entries).
- [x] **DONE** — `references.bib` entries include DOIs/URLs where
  available (spot-checked during Task 4/5 audits).
- [ ] **TODO (author action)** — A final pass confirming every DOI still
  resolves and every venue/year is correct is good practice before
  submission; this was not independently re-verified against live DOI
  resolution in this repository (no network access assumed).

## Figures

- [x] **DONE** — 10 figures, all with both `\caption` and an accessibility
  `\Description` (ACM requirement).
- [x] **DONE** — Figures 1, 3, and 5 use the final, independently-prepared
  images (`figure1.png`, `figure3.png`, `figure5.png`), byte-identical to
  the versions adopted in Task 3/4; verified unchanged by checksum in Task
  6 (`SUBMISSION_FREEZE_MANIFEST.json`). Not modified in Task 6 per its
  explicit constraint.
- [x] **DONE** — Figures 2, 4, 6-10 regenerated in Task 6 from frozen
  canonical tables (`figures_v2/generate_figures.py`), vector PDF format,
  no manual value edits. Every plotted value independently re-derived and
  verified against source CSVs (`FIGURE_DATA_VERIFICATION_REPORT.md`,
  13/13 checks passed).
- [x] **DONE** — Embedded `suptitle`s removed from Figures 7-10 (figure
  numbering/caption belongs in LaTeX, not baked into the image); a
  clipped-label defect in Figure 10's x-axis (trailing "$k$" cut off at
  high resolution) was found and fixed by increasing `savefig`'s
  `pad_inches`, then re-verified via a 300dpi render.
- [x] **DONE** — Final page-by-page PDF quality audit (Task 6 step 11):
  all 10 figures visually confirmed rendering correctly in their final
  embedded position within the compiled `main.pdf`, with captions matching
  content and correct sequential numbering; 34/40 pages inspected,
  including every figure-bearing page, front matter, and back matter.
- [x] **DONE** — The old internal `TASK 6 TODO` comment near
  Table~"Structural Sensitivity Across Threshold Protocols" (suggesting a
  Figures 3/5 sensitivity-range panel) was formally closed in Task 6 as
  conflicting with the explicit "do not modify Figures 1/3/5" constraint,
  rather than executed.

## Supplementary material

- [x] **DONE** — `papers/JDIQ_2026/submission/SUPPLEMENTAL_PACKAGE.md`
  inventories reproduction instructions, protocol/pool definitions,
  experiment manifests, per-query records, robustness tables, complete
  statistical outputs, and the test suite.
- [x] **DONE** — Packaged into an upload-ready bundle in Task 6:
  `papers/JDIQ_2026/submission/final_anonymous/` contains the manuscript
  source/PDF/figures, every aggregate CSV table cited in the manuscript
  (grouped by originating report directory), the driver/verification
  scripts that produced them, the freeze manifest, and an anonymized
  reproducibility guide — zipped as `final_anonymous.zip` with a recorded
  SHA-256 checksum.
- [ ] **TODO (author action)** — If applying for ACM artifact badges
  (Available / Evaluated / Reproducible), review ACM's current artifact
  review criteria and prepare the badge-specific submission separately.

## Repository / anonymization

- [x] **DONE** — Manuscript source (`main.tex`) contains no author-
  identifying text (verified: "Anonymous Author(s)", "Institution redacted
  for review", no acknowledgments).
- [x] **DONE** — Full anonymity audit performed in Task 6
  (`ANONYMITY_AUDIT.md`): `main.tex`, `main.pdf`, and all authored
  submission docs scanned for author name/username/email/hostname —
  clean. One real risk was found (204 per-cell `manifest.json` files
  contain absolute local paths) and resolved by exclusion: those raw
  per-cell files are not part of `final_anonymous/`; only path-scrubbed
  aggregate tables are included. A second leak was found and fixed during
  packaging: `query_exclusion_audit.csv` carried an absolute path in its
  `source_file` column on every row — scrubbed to a repo-relative path in
  the copy shipped inside `final_anonymous/`. A full recursive scan of the
  assembled `final_anonymous/` directory for author name, institution
  email-domain, and absolute-local-path patterns returned zero matches
  (Task 7 update: re-run and reconfirmed clean after the Task 7 artifact
  rebuild, which also added a defense-in-depth identity-string scrub to
  the build script itself; the exact pattern list is intentionally not
  reproduced here to avoid the checklist document itself becoming the leak
  it is checking for).
- [x] **DONE** — This checklist and package apply only to
  `final_anonymous/`, a scrubbed bundle; the private working repository
  (with full git history and real commit authorship) is correctly *not*
  scrubbed, per this task's explicit instruction not to erase provenance
  there.
- [x] **DONE** — Stale planning documents under `papers/JDIQ_2026/`
  (marked superseded in Task 4) are excluded from `final_anonymous/` by
  category, regardless of content, so their anonymity status is moot for
  the submission package; they remain in the private repository only.

## Metadata

- [ ] **TODO (author action)** — ORCID iDs for all authors.
- [ ] **TODO (author action)** — ACM computing classification / rights
  management information (typically collected via the ACM submission
  system, not hand-written in the `.tex` source under `anonymous,review`
  mode).
- [ ] **TODO (author action)** — Corresponding author contact information
  for the editorial system.

## Data and artifact availability

- [x] **DONE** — Manuscript's "Data Availability and Reproducibility"
  section (Section~\ref{sec:data-availability}) states dataset sources,
  redistribution policy (no raw third-party document collections
  redistributed), and artifact contents.
- [x] **DONE** — `docs/REPRODUCTION_CANONICAL.md` provides exact, verified
  commands and a table-to-source map for every canonical result in the
  private working repository (it contains a `git clone` line with the
  author-identifying repository URL, so it is not itself included in
  `final_anonymous/`); `final_anonymous/supplemental/REPRODUCIBILITY.md`
  is the anonymized equivalent shipped in the submission package.
- [x] **DONE** — `final_anonymous/` is the actual scrubbed anonymous
  artifact, assembled and zipped in Task 6
  (`papers/JDIQ_2026/submission/scripts/build_final_anonymous.py`).
- [ ] **TODO (author action)** — Attach `final_anonymous.zip` (or its
  contents) through the venue submission system before review, as the
  manuscript's own Data Availability section specifies; a public,
  author-identified repository URL should be added only after
  double-anonymous review concludes (or immediately if the venue does not
  require anonymity for artifacts).

## Cover letter

- [x] **DONE** — Drafted at `papers/JDIQ_2026/submission/COVER_LETTER.md`;
  contains placeholder fields for author identity that must be filled in
  before use (none were fabricated). Kept in `submission/` alongside this
  checklist rather than inside `final_anonymous/`, since it is the one
  artifact meant to carry real author identity once completed and is not
  part of the double-anonymous package.

## Validation run for this checklist

- [x] `pytest -q`: 550 passed.
- [x] `python3 scripts/check_repo_ready.py`: 56 OK, 5 pre-existing
  non-blocking warnings, 0 failures.
- [x] LaTeX build: clean, 0 undefined references/labels.
- [x] Bibliography cross-check: 29/29 cite keys resolved both directions.
