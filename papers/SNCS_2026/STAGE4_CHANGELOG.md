# Stage 4 Change Log

Records what Stage 4 (complete Results section and its supporting
figures/tables) did, mapped to the task brief's required-outputs list
(A-I).

## A. Results section

Drafted `\section{Results}` in `manuscript/main.tex`, organized by
research question per the task brief: 5.1 Structural Inconsistency Before
Repair (RQ1), 5.2 Structural Effect of Repair (RQ2), 5.3 Retrieval
Effectiveness (RQ3), 5.4 Exact Versus Heuristic Repair (RQ4, first half),
5.5 Robustness (RQ4, second half), 5.6 Supporting LLM Evidence (bounded
addendum). No Discussion, Conclusion, or Abstract prose was written, per
the task brief. Every subsection opens with a purpose paragraph, then
introduces its table/figure before it appears and interprets it
immediately after, per the task's "each subsection should begin with one
paragraph describing the purpose" and "each table and figure should be
introduced before it appears" instructions. Statistical language follows
the task's required convention throughout (e.g. "not statistically
supported under the canonical protocol after Holm correction," never
"repair does not work" or "almost significant" -- verified by `grep` for
both the required and forbidden phrasings; see
`RESULTS_CROSS_CHECK.md`'s final section).

## B. Figures

Five figures, all under `papers/SNCS_2026/figures/`:

- **F1** (pipeline schematic, placed in Methodology Section 4.2 rather
  than Results, since it illustrates the pipeline defined there): newly
  generated (`generate_f1_pipeline.py`), adding the exact-repair branch
  as a co-equal box next to greedy repair, per
  `figure_prompts/f1_pipeline_dual_repair.md`. Purely schematic, no data.
- **F2** (BM25 edge-weight share) and **F3** (cyclic-query
  before/after-mutual-deletion decomposition): copied unchanged from
  `papers/JDIQ_2026/manuscript/figures_v2/`, per `FIGURE_TABLE_AUDIT.md`'s
  finding that both were already publication quality and generated from
  the same canonical data this manuscript cites.
- **F4** (repaired-minus-unrepaired bootstrap forest plot, active
  `ms1` regime): copied unchanged, same reasoning.
- **F5** (exact-vs-greedy structural gap): newly generated
  (`generate_f5_exact_vs_greedy_gap.py`) directly from
  `reports/exact_open_source_ilp_repair_investigation/tables/structural_per_query.csv`,
  per `figure_prompts/f5_exact_vs_greedy_gap.md`. Its output numbers were
  cross-checked against that report's own `FINDINGS.md` table before
  being trusted (see Section E below) -- this caught and resolved a
  regime-pooling scope error on the first attempt (see Section E).

`figures/style.py` (copied from `figures_v2/style.py`) had its
single-column width constant resized from ACM's 3.35in to `sn-jnl.cls`'s
actual single-column text width (~5.10in, no `iicol` option in use);
every other convention (palette, regime labels, font sizes) is unchanged,
so old and new figures remain visually consistent.

**Deviation from the original `FIGURE_TABLE_AUDIT.md` plan**: F5 was
originally scoped as "appendix, new." Once Results was actually drafted,
Section 5.4 (Exact Versus Heuristic Repair) turned out to be exactly
where F5 belongs -- it is main-text evidence directly answering RQ4's
"does exact change the conclusion" question, not a secondary appendix
check. Placed in main-text Results instead. No appendix section exists in
the manuscript as of this stage (see the page-budget table in
`README.md`).

## C. Tables

Two tables from Stage 3 (`tab:setup`, `tab:baselines`) already covered
what the task brief's suggested T1 ("datasets and experimental settings")
and T2 ("compared methods, distinguishing the primary canonical study
from the exact-repair fairness study") ask for; **not duplicated**, per
the task's own "reduce unnecessary repetition" and "do not repeat numbers
already visible in tables" instructions -- Results prose references
Table~1 and Table~2 by number instead. Four new tables were added:

- `tab:structural-outcomes` (T3): structural metrics only (cyclic %,
  post-mutual %, normalized FAS weight removed), 4 datasets x 3 regimes.
- `tab:retrieval-holm` (T4): Holm-corrected cell-family counts (top
  block) + macro-mean nDCG for context (bottom block), primary canonical
  greedy-repair comparison.
- `tab:exact-vs-greedy` (T5): structural weight-removed comparison,
  exact vs.\ greedy, per dataset; the pooled retrieval-level result
  (0/35, 0/399) is stated in the caption rather than forced into a
  per-dataset row it does not have (see Section E -- this table's first
  draft used `\multirow` to mix per-dataset and pooled-only figures in a
  way that read as implying a per-dataset breakdown that does not exist;
  corrected before this cross-check was finalized).
- `tab:robustness` (T6, the brief's "optional" table): baseline
  fairness, power/MDE, narrow equivalence, and a cross-reference back to
  the larger-pool family already in Table 4 rather than restating it.

All four use `booktabs` rules, `\scriptsize`, and fit the single-column
width without `\resizebox`.

## D. Bibliography

No changes. The Results section states repository-derived findings, not
literature claims, and cites nothing (`grep -c "\\cite"` inside
`\section{Results}` is `0`).

## E. Numeric cross-check

New `papers/SNCS_2026/RESULTS_CROSS_CHECK.md`: every numerical claim in
Results traced to a specific canonical CSV, recomputed directly with
`pandas` (not read off a prior report's prose), and compared against the
same quantity where JDIQ's submitted manuscript or a `reports/*/FINDINGS.md`
also stated it. Two real discrepancies surfaced and are recorded there in
full:

1. **Two aggregate statistics (top-$k$ membership-change rate; the
   exact-vs-greedy per-dataset structural-gap table) initially
   miscomputed by restricting to the active `ms1` regime alone**, which
   seemed like the natural scope but gives $26.2\%$ and $n=316$
   respectively -- not JDIQ's/`FINDINGS.md`'s stated $10.6\%$ and
   $n=379$. Tracing the discrepancy to
   `reports/final_revision_task1_pool_cutoff_20260715/FINAL_REPORT.md`
   Section 9 and `reports/exact_open_source_ilp_repair_investigation/FINDINGS.md`'s
   own stated scope showed both are **pooled across all three
   vote-construction regimes**, not `ms1`-only; recomputing with that
   scope reproduces both cited figures exactly. The manuscript states the
   correct pooled scope explicitly in prose, not just the number.
2. **One statistic does not reproduce exactly and is reported as
   recomputed, not as JDIQ's original value**: the Holm-adjusted
   80%-power minimum detectable effect in the active larger-pool family.
   JDIQ states $0.0207$; the current canonical
   `mde_per_cell.csv` gives a median of $0.0201$ under the matching
   scope (checked against every plausible alternative column in the same
   file; none reproduces $0.0207$). Most likely cause: the underlying
   statistical-power report was regenerated after JDIQ's manuscript text
   was last written. The manuscript reports $0.0201$, the value
   reproducible from the current canonical artifact, per this stage's
   "never invent numbers" / "correct the manuscript rather than the
   repository" instructions -- this is the one open numeric discrepancy
   from this stage's cross-check.

Every other cross-checked number (BM25 share, Table 3's structural
figures, Holm-rejected counts 0/20, 0/60, 0/110, 0/36, 0/56, 0/35, 0/399,
0/8, macro-mean nDCG, equivalence counts 13/110 and 32/110, solver
statistics) was reproduced exactly from its canonical source, independent
of the prior manuscripts' prose.

## F. Page budget

Updated `README.md`'s page-budget table with Stage 4's actual compiled
page ranges (33 pages total; Results landed at 7 pages, within the
Stage-3 projected 6-9 page budget) and revised the remaining-stages
projection (~38-42 total pages).

## G. Compilation

`tectonic` (same toolchain as Stages 2-3; `apt-get` still unavailable).
One `Overfull \hbox` (5.76pt) in the first draft of Table 5, caused by a
`\multirow`-heavy column design -- fixed by simplifying that table's
column layout (see Section C above), not by shrinking font size or using
`\resizebox`. Final Stage-4 compile: 33 pages, zero undefined references,
zero undefined citations, zero BibTeX errors. Two straight-quote
typos (`"..."` instead of `` `...' ``) introduced while drafting Table 5's
caption were also caught and fixed during the same pass, consistent with
the same class of fix made in Stages 2-3. `main.pdf` is that verified
output.

## H. This file

Self-referential; see also `RESULTS_CROSS_CHECK.md` for the detailed
per-claim numeric verification this changelog summarizes.
