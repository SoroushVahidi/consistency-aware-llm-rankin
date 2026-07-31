# SN Computer Science Manuscript Workspace (Stage 1: Foundation)

**Status:** Stage 1 of a planned seven-stage manuscript-writing process.
This directory contains an **initialized skeleton and planning package**,
not a drafted paper. Do not treat `manuscript/main.tex` as finished prose --
every section body is a scope note for later stages. See
[`MANUSCRIPT_PLAN.md`](MANUSCRIPT_PLAN.md) for the full plan and
[`EVIDENCE_MAP.md`](EVIDENCE_MAP.md) for the claim-to-evidence table.

This workspace targets **SN Computer Science** (Springer Nature, ISSN
2661-8907). It does not modify or supersede `papers/JDIQ_2026/` (the
submitted, unrelated-venue manuscript) or `papers/_archive/` (historical
rejected-venue material) -- both remain untouched.

## Directory layout

```
papers/SNCS_2026/
├── README.md                 this file
├── MANUSCRIPT_PLAN.md         Stage-1 plan: titles, RQ, contributions,
│                               outline, tables/figures, scope, exclusions,
│                               forbidden claims, prior-text reuse plan
├── EVIDENCE_MAP.md            claim -> exact repository evidence path table
├── manuscript/
│   ├── main.tex               skeleton (title/author/structured-abstract
│   │                           placeholder/section scope notes)
│   └── references.bib         seed bibliography (50 entries, see its own
│                               header comment for provenance)
├── template/                  vendored Springer Nature LaTeX template
│   ├── sn-jnl.cls              v3.1, December 2024 (see "Template
│   │                           provenance" below)
│   ├── bst/                    all 9 official bibliography styles
│   ├── sn-article-sample.tex   official sample article (reference only,
│   │                           not part of this manuscript)
│   ├── sn-bibliography-sample.bib
│   ├── sn-article-sample.pdf   official compiled sample (reference only)
│   ├── sn-user-manual.pdf      official user manual (reference only)
│   ├── fig.eps, empty.eps      template placeholder figures
├── figures/                   empty; populated in a later stage
└── tables/                    empty; populated in a later stage
```

## Template provenance

`template/sn-jnl.cls` and the `.bst` files were downloaded directly from
Springer Nature's official LaTeX author-support distribution
(`https://www.springernature.com/gp/authors/campaigns/latex-author-support`,
"December 2024" package, confirmed as **Version 3.1, December 2024** from
the sample article's own header) on 2026-07-31, during this stage. That
freshly downloaded `sn-jnl.cls` was byte-for-byte content-identical (modulo
line-ending style: the official download uses CR-only line terminators,
normalized to LF here for git-friendliness) to the copy already vendored
in this repository at `papers/_archive/IJCS_early_draft.zip:sn-jnl.cls`,
confirming that the vendored copy (present since the earlier Iran Journal
of Computer Science submission attempt) was already current and did not
need replacing -- it was re-fetched anyway so this workspace has a clean,
independently verifiable provenance rather than depending on an archived
zip.

**Peer review model:** SN Computer Science uses **single-blind** review
(confirmed from the journal's official submission guidelines,
`https://link.springer.com/journal/42979/submission-guidelines`, fetched
2026-07-31) -- author identity is included, unlike the double-blind
`papers/JDIQ_2026/` submission. `manuscript/main.tex` therefore includes
the real author block (Soroush Vahidi, NJIT) rather than an anonymized
placeholder.

**Reference/documentclass choice:** `\documentclass[pdflatex,sn-basic]{sn-jnl}`
(Basic Springer Nature Numbered reference style), matching the journal's
confirmed "numeric citations in square brackets, numbered consecutively"
requirement. Verify this specific style choice against the journal's
current guidelines again before final submission, since Springer
occasionally revises per-journal defaults.

**Abstract structure:** SN Computer Science requires a **structured
abstract** (bold run-in labels, not subheadings): Purpose, Methods,
Results, Conclusion, 150-250 words total, no citations or equations inside
it. `manuscript/main.tex` follows this structure with placeholder content
for Stage 2.

## Compilation

**Not verified by an actual LaTeX compile this stage** -- no `pdflatex`/
`bibtex` toolchain is installed on the machine this workspace was prepared
on. A lightweight structural check (brace balance, `\begin`/`\end`
environment-count matching) was run instead and passed. Before Stage 2
drafting begins, compile once with either:

```bash
cd papers/SNCS_2026/manuscript
pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

or by uploading `manuscript/` + `template/` (flattened into one directory,
since `sn-jnl.cls` and the `.bst` files must be alongside `main.tex` or on
the `TEXINPUTS`/`BSTINPUTS` path) to Overleaf
(`https://www.overleaf.com/latex/templates/springer-nature-latex-template/gsvvftmrppwq`
hosts the same official template for reference).

## Evidence sources

Every claim planned for this manuscript traces to a specific repository
artifact -- see [`EVIDENCE_MAP.md`](EVIDENCE_MAP.md). The two authoritative
upstream indices are:

- `docs/claim_evidence_registry.yaml` -- machine-readable, repository-wide
  claim status (canonical / exploratory / internal-validation / negative
  result / superseded).
- `docs/CONTRIBUTIONS.md` -- the human-readable narrative version of the
  same information.

This manuscript draws **only** on claims marked `canonical: true` or
explicitly bounded exploratory evidence (the six-query real-LLM pilot,
labeled as directional-only) in that registry. No new experiments were run
to produce this Stage-1 package; a small number of read-only verification
commands (directory-existence checks, a template byte-diff) were used to
confirm cited artifacts actually exist, per the task instruction not to
run expensive new experiments or invent results.

## Relationship to prior manuscripts

- `papers/JDIQ_2026/manuscript/main.tex` -- the current, submitted (ACM
  Journal of Data and Information Quality) manuscript, "Data Quality for
  Derived Preference Graphs: Construction Sensitivity and Repair Outcomes
  in Multi-Ranker Retrieval". Most-vetted source of current numbers,
  terminology, and the Holm-correction protocol; primary reuse source.
- `papers/_archive/IJCS_early_draft.zip` -- the rejected (2026-07-05) Iran
  Journal of Computer Science submission, "Consistency-Aware Reranking via
  Preference Graph Repair: Structural Gains and Conditional Retrieval
  Effects". Reusable for Method/Related-Work prose structure and
  formalism; **not** reusable for its Results tables or "conditional
  positive effect" framing, both superseded by JDIQ's more rigorous,
  Holm-corrected, exact-repair-confirmed null result.
- `docs/historical/REVIEWER_CONCERN_GAP_AUDIT.md` -- the 14-point Iran JCS
  reviewer-concern audit that most directly shapes this manuscript's scope
  decisions (see `MANUSCRIPT_PLAN.md` Section 7).

See `MANUSCRIPT_PLAN.md` Section 8 for the detailed reuse plan.
