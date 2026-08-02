# SNCS 2026 Submission Portal Upload Manifest

**Date:** 2026-08-02  
**Rule:** upload only what the portal asks for. Do **not** upload internal audit
Markdown from this directory (freeze/review/smoke docs are for authors/agents).

## Upload items

| # | Item | Local path | Suggested upload filename | Mandatory / optional | Notes |
|---|---|---|---|---|---|
| 1 | Main manuscript PDF | `manuscript/main.pdf` | `SNCS_2026_main.pdf` | Mandatory | Primary file |
| 2 | Editable LaTeX source | `manuscript/` + `template/` + `figures/*.pdf` (ZIP if portal requires) | `SNCS_2026_latex_source.zip` | Mandatory | Journal requires editable source |
| 3 | Cover letter PDF | `COVER_LETTER.pdf` | `SNCS_2026_cover_letter.pdf` | Mandatory if cover-letter field exists | Professionally typeset |
| 4 | Highlights PDF | `HIGHLIGHTS.pdf` | `SNCS_2026_highlights.pdf` | Optional — only if requested | Journal guidelines do not require highlights |
| 5 | Figures (separate slots) | `figures/f1_pipeline.pdf` … `f5_*.pdf` | same basenames | Optional if already in source ZIP | All vector PDFs |
| 6 | Suggested reviewers | `REVIEWER_SUGGESTIONS.md` | Portal fields | If asked | Prefer first six |
| 7 | Opposed reviewers | Conflict list in `SUBMISSION_METADATA.md` | Portal fields | Only if asked | Conflict list only |
| 8 | Code/data URL | Public GitHub | Portal fields | Mandatory statement | `https://github.com/SoroushVahidi/consistency-aware-llm-rankin` |
| 9 | ORCID | Portal ORCID field | — | Recommended by SNCS | `https://orcid.org/0000-0003-1934-6282` |
| 10 | Declarations / metadata | `SUBMISSION_METADATA.md` | Portal form fields | Mandatory as prompted | Abstract, funding, AI, etc. |

## Author-only (do not upload unless asked)

- `SUBMISSION_CHECKLIST.pdf` — internal author checklist
- Freeze/audit/changelog Markdown

## Explicitly exclude

- API keys, credentials, `.env`
- Raw provider transcripts
- Internal Gurobi validation report trees as manuscript evidence
- Entire unsanitized working tree ZIP

## Recommended upload order

1. Paste metadata (title, abstract, keywords, ORCID, declarations).
2. Upload `manuscript/main.pdf`.
3. Upload editable source ZIP / figures as required.
4. Upload `COVER_LETTER.pdf`.
5. Upload `HIGHLIGHTS.pdf` only if requested.
6. Enter reviewers and code/data URL.
7. Review proof; **stop before final submit** until author authorizes.
