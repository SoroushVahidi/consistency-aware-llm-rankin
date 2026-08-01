# Novelty Front-Matter Revision Changelog

Date: 2026-08-01  
Branch: `papers/sncs-2026-foundation`  
Checkpoint: `checkpoint/sncs-novelty-frontmatter-20260801T233046Z` (@ `9bd414b`)

## Intent

Reframe front matter so novelty is the construction → membership-change →
Holm-null → exact diagnostic → graph-free fusion triad, not the tautology that
repair acts only when cycles exist.

## Validation follow-up (this pass)

- Abstract numbers checked against Results, `result_claims.yaml`,
  `RESULTS_CROSS_CHECK.md`, `EVIDENCE_MAP.md`, and canonical CSVs.
- `10.6%` scope clarified as pooled across three vote-construction regimes
  when \(P>k\) (ms1-only would be ~26.2%).
- nDCG expanded on first abstract use; abstract kept at **250** words.
- Results opening and “RQ4’s second half” wording aligned to revised RQs.
- Active submission-facing abstracts synced (`SUBMISSION_METADATA.md`,
  `PORTAL_DRY_RUN.md`); keywords in metadata aligned to manuscript’s six terms.
- Freeze/upload hashes updated; prior `f42ad47` PDF/ZIP hashes labeled superseded.

## Changed files

- `papers/SNCS_2026/manuscript/main.tex`
- `papers/SNCS_2026/manuscript/main.pdf`
- `papers/SNCS_2026/submission/SNCS_2026_latex_source.zip`
- `papers/SNCS_2026/SUBMISSION_METADATA.md`
- `papers/SNCS_2026/PORTAL_DRY_RUN.md`
- `papers/SNCS_2026/SUBMISSION_FREEZE.md`
- `papers/SNCS_2026/UPLOAD_MANIFEST.md`
- `papers/SNCS_2026/NOVELTY_FRONTMATTER_CHANGELOG.md`

## Compile / hashes

- Engine: `tectonic` — success (underfull-box / duplicate-destination warnings only; no overfull)
- Pages: **39**
- Abstract words: **250**
- Contributions: **3** scientific
- PDF SHA-256: `70bd3bb9af205270de1881e4707783a8e91c07420256999915a3aad5c556e973`
- ZIP SHA-256: `bfe935f090e4651b6add6e45528c90fadad9a35805e83ffb178ddf8406ec8ef7`
- `main.tex` SHA-256: `ff466027d6b9719bc2121eae43ef455a8a1a050f9bcce1ca4b18e951cbbaacbb`

## Scientific content

No new experiments; no claim broadening; numbers used already appear in Results
(`10.6%` pooled, CombSUM `0.554`, hybrid `0.546`, BM25 share `0.988`/`0.512`).
