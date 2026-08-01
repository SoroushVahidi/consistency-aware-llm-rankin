# SNCS 2026 Submission Portal Upload Manifest

**Date:** 2026-08-01  
**Rule:** upload only what the portal asks for. Do **not** upload internal audit
Markdown from this directory (freeze/review/smoke docs are for authors/agents).

Hashes below match `SUBMISSION_FREEZE.md` at package preparation time.

## Upload items

| # | Item | Local path | Suggested upload filename | Journal file type (typical EM) | Mandatory / optional | Public / confidential | Version / hash | Special instructions |
|---|---|---|---|---|---|---|---|---|
| 1 | Main manuscript PDF | `papers/SNCS_2026/manuscript/main.pdf` | `SNCS_2026_main.pdf` | Manuscript (PDF) | Mandatory | Becomes review/production artifact | SHA-256 `7980e146ef32731405b4e4845f5a70799dd46391b0878bdc1fb8037aac90b3c7` | Primary file. Verify portal proof after upload. |
| 2 | LaTeX source ZIP | `papers/SNCS_2026/submission/SNCS_2026_latex_source.zip` | `SNCS_2026_latex_source.zip` | Manuscript / Source files | Mandatory (journal requires editable source) | Editorial/production | SHA-256 `deca1a011f7e5b3af9facc44c47869211a04b58a5ee1f987ff6f02a053d8418c` | Contains tex/bib/cls/bst + figure PDFs only. |
| 3 | Figure PDFs (if portal requires separate figure slots) | `papers/SNCS_2026/figures/f1_pipeline.pdf` … `f5_exact_vs_greedy_gap.pdf` | `f1_pipeline.pdf` … `f5_exact_vs_greedy_gap.pdf` | Figure | Optional if already inside source ZIP; upload separately only if portal demands | Public with paper | Use committed figure binaries | Tag as Figure, not Supplemental, in Editorial Manager-style portals. |
| 4 | Cover letter | `papers/SNCS_2026/COVER_LETTER.md` (paste or export PDF/TXT) | `SNCS_2026_cover_letter.txt` | Cover Letter | Mandatory if portal has a cover-letter field | Confidential to editors | Text in `COVER_LETTER.md` / `SUBMISSION_METADATA.md` | Do not include internal audit notes. |
| 5 | Highlights | `papers/SNCS_2026/HIGHLIGHTS.md` | `SNCS_2026_highlights.txt` | Highlights | Optional — **only if requested** | Public if used | See file | SNCS guidelines checked did not require highlights. |
| 6 | Suggested reviewers | `papers/SNCS_2026/REVIEWER_SUGGESTIONS.md` | Portal fields (not a file) | Reviewer suggestions | Enter if portal asks | Confidential | See file | Prefer first six; Nihar B. Shah as alternate. |
| 7 | Opposed reviewers | Conflict list in `SUBMISSION_METADATA.md` | Portal fields | Opposed reviewers | Optional / only if asked | Confidential | See metadata | Do not invent opposition beyond the conflict list. |
| 8 | Code/data link | Public GitHub URL | Portal “Data/Code availability” fields | URL / statement | Mandatory statement | Public | https://github.com/SoroushVahidi/consistency-aware-llm-rankin | Optionally note freeze commit after it is recorded. No separate code ZIP required now that the repo is public. |
| 9 | Declarations / metadata | `papers/SNCS_2026/SUBMISSION_METADATA.md` | Portal form fields | Metadata | Mandatory fields as prompted | Mix (funding public; emails as required) | Copy-ready blocks in metadata | Paste abstract, keywords, funding, ethics, AI disclosure, etc. |
| 10 | Running title / keywords | `papers/SNCS_2026/KEYWORDS_RUNNING_TITLE.md` | Portal fields | Metadata | As prompted | Public | See file | Align with manuscript `\keywords`. |

## Explicitly exclude from the submission package

Do **not** upload:

- `SUBMISSION_FREEZE.md`, `RELEASE_CANDIDATE_*.md`, `PUBLIC_REPOSITORY_REVIEW.md`, `LICENSE_AND_DISTRIBUTION_AUDIT.md`, stage changelogs, cold-read / independent-review working notes
- API keys, credentials, `.env`
- Personal email exports; rejected-venue correspondence; private legal files
- Raw provider transcripts / `raw_calls/`
- Internal Gurobi validation report trees as “supplementary evidence”
- Entire git working tree ZIP unless the portal explicitly requests a code archive **and** it is sanitized per `RELEASE_CANDIDATE_PLAN.md`

## Recommended upload order

1. Paste metadata fields (title, abstract, keywords, declarations).
2. Upload `main.pdf`.
3. Upload `SNCS_2026_latex_source.zip` (and separate figures only if required).
4. Paste/upload cover letter.
5. Enter suggested (and opposed, if asked) reviewers.
6. Enter public code/data URL.
7. Review generated proof; **stop before final submit** until author authorizes.
