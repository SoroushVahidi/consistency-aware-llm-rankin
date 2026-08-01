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

**Verified by an actual compile in Stage 2** using `tectonic` (a
self-contained TeX engine already available on this machine at
`~/.local/bin/tectonic`; no system `texlive`/`pdflatex` package could be
installed here since `apt-get` requires a password this environment does
not have). `manuscript/main.pdf` is the committed, up-to-date compiled
output as of Stage 2. To reproduce:

```bash
cd papers/SNCS_2026/manuscript
cp ../template/sn-jnl.cls ../template/bst/sn-basic.bst .   # tectonic needs
                                                              # them alongside main.tex
tectonic -X compile main.tex --outdir /tmp/sncs_build
rm sn-jnl.cls sn-basic.bst                                  # keep manuscript/
                                                              # free of duplicated
                                                              # vendored template files
cp /tmp/sncs_build/main.pdf .
```

Equivalently, with a system `pdflatex`/`bibtex` toolchain:

```bash
cd papers/SNCS_2026/manuscript
cp ../template/sn-jnl.cls ../template/bst/sn-basic.bst .
pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
rm sn-jnl.cls sn-basic.bst
```

or by uploading `manuscript/` + `template/` (flattened into one directory,
since `sn-jnl.cls` and the `.bst` files must be alongside `main.tex` or on
the `TEXINPUTS`/`BSTINPUTS` path) to Overleaf
(`https://www.overleaf.com/latex/templates/springer-nature-latex-template/gsvvftmrppwq`
hosts the same official template for reference).

Two class-usage pitfalls discovered and fixed during the Stage-2 compile,
recorded here so they are not rediscovered:

- **Do not add an explicit `\bibliographystyle{sn-basic}` in `main.tex`.**
  `sn-jnl.cls`'s `sn-basic` document-class option already issues that
  command internally (see the class file's "Macros for bibliographystyles"
  section); adding it again in `main.tex` produces a duplicate `\bibstyle`
  command that BibTeX rejects with "Illegal, another \bibstyle command",
  silently breaking every citation resolution while `pdflatex`/`tectonic`
  themselves report no error. `main.tex` calls only
  `\bibliography{references}`.
- **`sn-basic` alone renders author-date citations, not numeric ones.**
  The class's numeric-vs-author-date choice is a second, separate class
  option: `Numbered` (default off; the class file's internal name for the
  author-date default is "Namedate"). SN Computer Science's submission
  guidelines specify numeric, consecutively numbered citations (see
  "Reference/documentclass choice" above), so `main.tex` uses
  `\documentclass[pdflatex,sn-basic,Numbered]{sn-jnl}`.

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

## Stage-2 resolutions of the two Stage-1 inconsistencies

`MANUSCRIPT_PLAN.md` Section 10 flagged two inconsistencies to resolve
before drafting. Both are now resolved:

1. **BRIGHT citation key.** `manuscript/references.bib` cites the
   published venue record: `su2025bright`, an `@inproceedings` entry for
   *BRIGHT: A Realistic and Challenging Benchmark for Reasoning-Intensive
   Retrieval* (Su, Yen, Xia, Shi, Muennighoff, Wang, Liu, Shi, Siegel,
   Tang, Sun, Yoon, Arik, Chen, Yu), ICLR 2025, Spotlight
   (`https://openreview.net/forum?id=ykuc5q381b`). This was verified
   directly against the ICLR 2025 proceedings PDF header
   (`https://proceedings.iclr.cc/paper_files/paper/2025/file/7a0f8055c838df8e62329a76c7c6403d-Paper-Conference.pdf`,
   "Published as a conference paper at ICLR 2025") and the ICLR 2025
   virtual poster page, both fetched 2026-07-31. The earlier
   `su2024bright` arXiv-preprint entry (`arXiv:2407.12883`) has been
   removed from `manuscript/references.bib`; every citation of this
   benchmark in this manuscript uses `su2025bright`. (JDIQ_2026, a
   separately submitted manuscript, is untouched and keeps its own
   `su2024bright` key -- this resolution applies only to `SNCS_2026`.)

2. **"Dimension F" vs. "Outcome F" naming collision.** JDIQ_2026's
   compact audit taxonomy (`tab:dq-taxonomy`) lettered its seven failure
   modes A-G, and its dimension F ("graph repair is assumed to improve
   retrieval") is the letter that collides with the unrelated
   POLICY-01/"Outcome F" production-policy-selection research thread
   (`docs/CONTRIBUTIONS.md` SS1.7) -- a thread this manuscript excludes
   entirely (`MANUSCRIPT_PLAN.md` Section 6.3). Resolution: this
   manuscript does not letter its diagnostic dimensions at all. Where
   Stage 2 prose needs to refer to the specific diagnostic question that
   JDIQ called "dimension F" -- whether graph repair itself improves
   retrieval -- it is named directly (e.g. "the retrieval-utility
   check") rather than lettered, and it is never called "Dimension F."
   If a later stage reintroduces a compact lettered table for the full
   seven-part audit (as an expanded, worked-example version per
   `MANUSCRIPT_PLAN.md` Section 8.2 option (a)), that table must use
   named rows, not letters, specifically to avoid recreating this
   collision. No manuscript-facing text in this repository should use
   the bare string "Dimension F" or "Outcome F" interchangeably; they
   denote two unrelated research threads.

## Page budget (Stage 5)

SN Computer Science states no explicit word-count, page-count, or
figure/table-count limit for original-research articles (verified against
official Springer Nature sources during Stage 3, 2026-07-31); the only
stated numeric constraint anywhere in the guidelines is the structured
abstract's 150-250 word limit. This project keeps its own internal budget
so the manuscript stays a focused empirical study rather than growing
without bound. Current state (compiled this stage, `tectonic`,
`sn-basic`+`Numbered`, single column, 40 pages total) and the projected
budget for the remaining stages:

| Section | Current pages | Projected final pages | Note |
|---|---|---|---|
| Title/abstract/keywords | <1 (part of p.1) | <1 | Structured abstract still a Stage-1 placeholder |
| 1 Introduction | 1-3 (3 pp) | 3 | Drafted Stage 2; not expected to grow |
| 2 Related Work | 4-6 (3 pp) | 3 | Drafted Stage 2; not expected to grow |
| 3 Background and Problem Formulation | 7-11 (5 pp) | 5 | Drafted Stage 2; not expected to grow |
| 4 Methodology | 12-19 (8 pp) | 8 | Drafted Stage 3; includes Figure 1 (pipeline schematic) added Stage 4 and the generative-AI disclosure paragraph added Stage 5; not expected to grow further |
| 5 Results | 20-25 (6 pp) | 6 | Drafted Stage 4; unchanged this stage |
| 6 Discussion | 26-30 (5 pp) | 5 | **Drafted Stage 5.** Six subsections (main findings, mechanism, exact-repair-as-control, literature, practical implications, LLM implications); came in near the Stage-4 projected 1-2 pp budget's high end given the literature-comparison and mechanism subsections the Stage-5 brief added to scope beyond Stage 4's simpler projection |
| 7 Limitations and Threats to Validity | 31-32 (2 pp) | 2 | **Drafted Stage 5.** Five subsections (internal, construct, external, statistical-conclusion, computational validity), within the Stage-4 projected 1 pp budget's low end (came in slightly over; validity-framed structure is more thorough than the originally-projected five-bullet-point form) |
| 8 Conclusion | 33 (0 pp, skeleton) | <1 | Not yet drafted (Stage 5 explicitly excludes it) |
| 9 Data Availability and Reproducibility | 33 (0 pp, skeleton) | <1 | Not yet drafted |
| References | 34-39 (~6 pp) | 6-7 | Grew this stage with one new reference (`vahidi2026consistencyaware`); will grow further only if Conclusion cites anything new; prune unused entries only after Conclusion is drafted |
| Declarations (backmatter) | 39-40 (~1 pp) | 1 | Funding remains an explicit `[AUTHOR CONFIRMATION REQUIRED]` placeholder; every other heading is substantively complete |
| Appendix | 0 | 0 | Confirmed not needed as of Stage 5; both items originally scoped here were placed in main-text Results (Stage 4). No robustness table has needed to move out of Table 6 for length. |
| **Total** | **40** | **~41-43** | Internal target, not a journal-imposed limit; the remaining growth is almost entirely the Conclusion (<1 pp) and the final structured Abstract, which does not add a page (front matter) |

Reducing repetition across sections was an explicit Stage-3 concern: the
central null-result thesis is stated once in the Introduction (as the
paper's central finding), once in Background's closing paragraph (as the
formal reason the repair objective and nDCG are distinct), and is
deliberately *not* restated a third time anywhere in Methodology, which
describes protocol only and reports no outcome values. It will
necessarily be restated in Results (as the finding itself), Discussion
(as the organizing thesis), and Conclusion (as the closing statement) --
three restatements across those three sections, matching
`MANUSCRIPT_PLAN.md` Section 9, item 14's explicit budget ("no repeated
null-result restatement across more than the Results + Discussion +
Conclusion sections already required by the outline").

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
