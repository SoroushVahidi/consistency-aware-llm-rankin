# Submission Freeze Changelog (2026-08-02)

Final submission-package correction and freeze pass on branch
`papers/sncs-2026-foundation`. No new experiments. No scientific numbers,
table bodies, figure data, statistical families, or claim classifications
changed.

## Abstract

- Shortened structured abstract to ≤250 words.
- Method A (`wc`/whitespace): **219**
- Method B (alphanumeric tokens; hyphen compounds split): **245**
- Preserved: 0.988 / 0.512 / 10.6% / CombSUM 0.554 vs 0.546 / Holm nulls /
  exact removes less weight / missing Holm evidence ≠ equivalence.

## Terminology synchronization

Corrected obsolete wording in active submission surfaces
(`COVER_LETTER.md`, `SUBMISSION_METADATA.md`, `PORTAL_DRY_RUN.md`,
`HIGHLIGHTS.md`, `README.md`, `KEYWORDS_RUNNING_TITLE.md`,
`REVIEWER_SUGGESTIONS.md`, `REPRODUCIBILITY_QUICKSTART.md`, manuscript):

| Obsolete / risk phrasing | Replacement / disposition |
|---|---|
| under-repair (as active claim language) | greedy graph-objective / edge-deletion MWFAS suboptimality |
| outdated absolute title *Is Not Retrieval Utility* | *Does Not Reliably Predict Retrieval Utility* |
| “rules out greedy heuristic suboptimality” (highlights) | diagnoses greedy suboptimality; does not prove repair never helps |
| Acknowledgments “his mother” / emotional-support wording | Mitra Sharifani; guidance and support / personal support |
| Funding as broad sponsorship | in-kind support for bounded real-LLM pilot only |

Historical changelogs/audits may still quote prior wording; they are not
portal copy sources.

## Acknowledgments / Funding / AI / Declarations

- Acknowledgments: Professor Ioannis Koutis; Mitra Sharifani; Anders Borum /
  Secure ShellFish (exact verified names).
- Funding: Cohere Labs Catalyst Grant Program; Google Cloud Research Credits
  Program; Microsoft Azure for Students; Fireworks AI credits via AMD AI
  Developer Program — pilot only; principal experiments = stored BM25/TF-IDF/
  MiniLM + local SCIP.
- Generative-AI disclosure shortened in Methods/Reproducibility; synced to
  portal/metadata.
- Declarations split: Funding; Competing interests; Ethics approval; Consent
  to participate; Consent for publication; Data availability; Code
  availability; Materials availability; Authors' contributions.

## Figure 1

- Freeze-pass selection (historical): `figures/f1_pipeline.pdf`
  (SHA-256 `61070c6e…021ce2`).
- **Superseded for release:** author-uploaded
  `figures/f1_pipeline.png` (SHA-256
  `4feeac61a348f526f79393be017734a7dba45f6502004c8d557c93379bfe5af2`;
  source commit `3de82709c5af4c44951c2d57285aa914896cc85a`). Unused PDF
  removed from the tree.

## Length

| Metric | Before freeze pass (stated) | After clean compile |
|---|---|---|
| Pages | ~36 | **36** |
| Approx. word tokens | ~10,500 | ~10,242 |

No supplementary-information file created (not needed to stay ≤36 pages).

## Validation (2026-08-02)

| Check | Result |
|---|---|
| `tectonic -X compile main.tex` | PASS (36 pp); no undefined citations/refs |
| `validate_claim_evidence_registry.py` | PASS (12 claims) |
| `validate_canonical_evidence_manifest.py` | PASS |
| `validate_report_links.py` | PASS |
| `check_active_portability.py` | PASS |
| `validate_repo_clarity.py` | PASS |
| `run_secret_scan.py` | PASS (0 findings) |

## Compiled PDF

- Path: `papers/SNCS_2026/manuscript/main.pdf`
- SHA-256: `d256ae8819223fe928bd68823885c7858cc942938d343c8a6767676b29928bf7`

## 2026-08-02 materials-generation pass

Generated professionally typeset:

- `COVER_LETTER.pdf`
- `HIGHLIGHTS.pdf` (optional; SNCS does not require highlights)
- `SUBMISSION_CHECKLIST.pdf` (author-only)

Inserted verified ORCID `https://orcid.org/0000-0003-1934-6282` on the
manuscript title page (text ORCID link; sn-jnl logo EPS not vendored) and
synchronized portal/metadata/cover materials. Funding wording now names the
pilot providers (Azure / Gemini / Cohere / Fireworks) without implying paid
API dependence for the principal score-derived experiments.
