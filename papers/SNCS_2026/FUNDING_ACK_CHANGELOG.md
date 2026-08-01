# Funding / Acknowledgments Placement Changelog

**Date:** 2026-08-01  
**Branch:** `papers/sncs-2026-foundation`  
**Scope:** Move API/cloud computational-credit disclosure so it appears
only under Funding; keep Acknowledgments personal/non-funding only.
No scientific content, results, citations, figures, tables, or conclusions
changed.

## What changed

| Location | Change |
|---|---|
| `manuscript/main.tex` Acknowledgments | Removed Cohere / Google Cloud / Azure / AMD / Fireworks AI credit wording; personal thanks only (Koutis, mother, Anders Borum / Secure ShellFish). |
| `manuscript/main.tex` Funding | Reworded to “computational support through …” plus funder non-role sentence; Fireworks AI credits credited via the AMD AI Developer Program. |
| `manuscript/main.pdf` | Recompiled. |
| `SUBMISSION_METADATA.md` | Funding + Acknowledgements portal text synchronized; conflict-exclusion row updated to Funding-only. |
| `JOURNAL_COMPLIANCE_CHECKLIST.md` | Acknowledgments / Funding rows updated to match the single-placement rule. |
| `REVIEWER_SUGGESTIONS.md` | Support-provider exclusion row now says Funding declaration (not Acknowledgments). |

## Confirmation: no duplicate API-credit acknowledgment

Active submission-facing files were searched for provider-credit wording
outside Funding. After this pass:

- Provider credit names appear in **Funding only** in `main.tex` /
  `main.pdf`.
- Acknowledgments contain only personal/non-funding thanks.
- Portal copy in `SUBMISSION_METADATA.md` matches the manuscript.
- No `papers/SNCS_2026/submission/` directory exists.

Archival / historical audit notes (`COLD_READ_REPORT.md`,
`STAGE6_*.md`, `INDEPENDENT_PRESENTATION_REVIEW.md`, earlier repetition
audit remarks about dual placement) may still describe the previous
duplicated wording; they are not portal copy-paste sources.

## Policy note (Springer Nature / SN Computer Science)

Rechecked SN Computer Science submission guidelines and Springer journal
policies (2026-08-01):

- **Funding** belongs in the Declarations section and must disclose
  funding / research support. Springer’s competing-interest examples treat
  “research support” (equipment, supplies, and similar) as disclosable
  under funding-related interests, so **in-kind computational / API / cloud
  credits are appropriately listed under Funding**.
- **Acknowledgments** may mention people, grants, or funds, and
  organization names should be written in full when funding is placed
  there. The guidelines do **not** require that the same credit list also
  appear in Acknowledgments when it is already disclosed under Funding.
- **Ambiguity retained:** Acknowledgments are allowed to mention grants,
  so dual placement would not violate the letter of the guide; this
  revision chooses the clearer single placement (Funding only) to avoid
  duplicated disclosure. Personal thanks remain in Acknowledgments only.

## Name / program verification

Spelling checked against prior Stage-6 verified records in this workspace:

- Professor Ioannis Koutis
- Anders Borum
- Secure ShellFish
- Cohere Labs Catalyst Grant Program
- Google Cloud Research Credits Program
- Microsoft Azure for Students
- AMD AI Developer Program / Fireworks AI credits

Terminology: “computational support” / credits — not “financial grants.”
