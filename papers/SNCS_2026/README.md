# SN Computer Science Manuscript Workspace

**Status:** submission package prepared on branch `papers/sncs-2026-foundation`
(freeze / release-candidate docs in this directory). The compiled manuscript is
`manuscript/main.pdf` (39 pages). **Do not treat internal audit Markdown as
supplementary files for the journal portal.**

Target journal: **SN Computer Science** (Springer Nature, ISSN 2661-8907).
This workspace does not modify or supersede `papers/JDIQ_2026/` or
`papers/_archive/`.

## Start here for submission

| Document | Role |
|---|---|
| [`SUBMISSION_FREEZE.md`](SUBMISSION_FREEZE.md) | Exact commit, PDF/ZIP hashes, metrics |
| [`UPLOAD_MANIFEST.md`](UPLOAD_MANIFEST.md) | What to upload to the portal |
| [`PORTAL_DRY_RUN.md`](PORTAL_DRY_RUN.md) | Copy-ready portal fields |
| [`REPRODUCIBILITY_QUICKSTART.md`](REPRODUCIBILITY_QUICKSTART.md) | Reviewer reproduction tracks |
| [`RELEASE_CANDIDATE_DECISION.md`](RELEASE_CANDIDATE_DECISION.md) | Freeze/submit readiness verdict |
| [`SUBMISSION_METADATA.md`](SUBMISSION_METADATA.md) | Title, abstract, declarations, cover letter |
| [`COVER_LETTER.md`](COVER_LETTER.md) | Cover letter text |

## Manuscript identity

- **Title:** Structural Consistency Is Not Retrieval Utility: An Exact-and-Heuristic Audit of Preference-Graph Repair for Multi-Ranker Retrieval
- **Principal conclusion:** preference-graph repair is structurally real but not a validated surrogate for improving retrieval effectiveness under the reported Holm-corrected protocols.
- **PDF:** `manuscript/main.pdf`
- **Source ZIP:** `submission/SNCS_2026_latex_source.zip`
- **Code/data:** https://github.com/SoroushVahidi/consistency-aware-llm-rankin (public)

## Directory layout

```
papers/SNCS_2026/
├── manuscript/main.tex|.bib|.pdf
├── figures/                 vector PDFs used by the manuscript
├── template/                Springer Nature sn-jnl v3.1 + bst
├── submission/              uploadable LaTeX source ZIP
├── tables/                  planning/support materials
└── *.md                     submission + audit documentation
```

## Template provenance

`template/sn-jnl.cls` and bibliography styles come from Springer Nature’s
official LaTeX author-support distribution (Version 3.1, December 2024).
Peer review is **single-blind**; author identity is included.

Document class used:

```latex
\documentclass[pdflatex,sn-basic,Numbered]{sn-jnl}
```

## Compilation

```bash
cd papers/SNCS_2026/manuscript
cp ../template/sn-jnl.cls ../template/bst/sn-basic.bst .
tectonic -X compile main.tex
# or: pdflatex && bibtex && pdflatex && pdflatex
rm sn-jnl.cls sn-basic.bst
```

Prefer compiling from `submission/SNCS_2026_latex_source.zip` when checking the
exact upload archive (see `REPRODUCIBILITY_QUICKSTART.md`).

Pitfalls:

- Do not add a second `\bibliographystyle{sn-basic}` (the class option already does).
- `sn-basic` alone is author-date; add `Numbered` for numeric citations.

## Evidence and scope

Claims map to repository artifacts via [`EVIDENCE_MAP.md`](EVIDENCE_MAP.md) and
`docs/CONTRIBUTIONS.md`. Canonical classical evidence lives under
`reports/full_calibrated_core/` and
`reports/exact_open_source_ilp_repair_investigation/`. The six-query real-LLM
pilot is directional only. Gurobi solver cross-validation reports are
internal-only and must not be cited as manuscript evidence.

## Relationship to other manuscripts

- `papers/JDIQ_2026/` — separate venue manuscript sharing much of the same
  classical evidence backbone.
- `papers/_archive/` — historical / rejected-venue material; not SNCS evidence.
