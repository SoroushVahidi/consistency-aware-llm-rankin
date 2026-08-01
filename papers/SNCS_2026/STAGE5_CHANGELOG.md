# Stage 5 Change Log

Records what Stage 5 (Discussion, Limitations and Threats to Validity,
literature/policy verification, generative-AI disclosure) did, mapped to
the task brief's required-outputs list (A-M).

## A. Evidence-map and cross-check updates

`EVIDENCE_MAP.md`: claims #5 and #6 in the "Planned main-paper claims"
table now state explicitly that the 10.6% top-$k$ membership-change rate
and the $n=379$ exact-vs-greedy cyclic-query count are **pooled across
all three vote-construction regimes**, not `ms1`-only (restricting to
`ms1` gives 26.2% and $n=316$ respectively -- materially different
numbers, not just imprecise ones). Claim #8's MDE figure is corrected
from the superseded $0.0207$ to the reproducible $0.0201$, and its
evidence path is corrected from
`final_revision_task1_pool_cutoff_20260715/` (wrong -- that report
covers the larger-pool structural study, not statistical power) to
`final_revision_task2_statistical_power_20260715/` (where
`mde_per_cell.csv` actually lives). `RESULTS_CROSS_CHECK.md` gained a
Stage-5 pointer note to `result_claims.yaml` and a record of the
repository-wide stale-value search described in Section B below.
`MANUSCRIPT_PLAN.md` (Section 3, item 2, and Section 8.2) had its
$10.6\%$ and $0.0207$ mentions annotated in place with Stage-4/5
clarification notes -- not silently rewritten, per the task brief's
"mark superseded values clearly rather than silently rewriting historical
records" instruction. `manuscript/main.tex` itself required **no
changes** for scope or value corrections: Stage 4 already stated every
one of these figures with the correct pooled scope and the corrected MDE
value.

## B. Repository-wide stale-value search

Searched the whole repository (not just `papers/SNCS_2026/`) for `0.0207`,
`379`, and `10.6%`/`10.6\%`. Occurrences outside `papers/SNCS_2026/` are
in `papers/JDIQ_2026/` (the separately submitted, frozen manuscript),
`papers/negative_result_2026/` (a separate paper track), and `docs/`/
`reports/` historical records -- all deliberately left untouched, since
none of them are this manuscript and editing them is outside this
project's authority (JDIQ especially: it is a submitted, frozen document
per every prior stage's stated policy). This is noted explicitly in
`RESULTS_CROSS_CHECK.md` rather than left implicit.

## C. `result_claims.yaml`

New machine-readable file indexing 16 headline results with their exact
source CSV, filter, aggregation, reproduced value, and (where different)
the prior manuscript's value, plus a `verification_status` field
(`exact_match` for 15 of 16; `recomputed_discrepancy` for the MDE figure,
the one open, documented, unresolved numeric discrepancy). Complements
`RESULTS_CROSS_CHECK.md`'s narrative (why each scope decision was made)
rather than replacing it.

## D. Discussion

Drafted `\section{Discussion}` (six subsections: main findings; why
structural improvement need not improve retrieval, with mechanisms
explicitly labeled as consistent-with-but-not-demonstrated-by the design;
exact repair as a diagnostic control, not a solver contribution; relation
to prior literature; practical implications; implications for LLM-based
ranking). Language checked against the task brief's required bounded
phrasing ("did not yield a statistically supported general improvement,"
etc.) and forbidden phrasing ("repair never helps," "acyclicity is
useless," "the null hypothesis is proven," etc.) -- zero forbidden
phrases found by direct `grep`.

**A significant, evidence-driven correction happened while researching
the literature-comparison subsection.** Verifying the framing that the
author's earlier related work is an "unpublished, rejected manuscript"
not to be cited (established in Stages 2-4) turned up a fact those
stages did not have: the earlier IJCS-submission manuscript
("Consistency-Aware Reranking via Preference Graph Repair: Structural
Gains and Conditional Retrieval Effects") is posted as a public,
DOI-bearing preprint on Research Square
(`10.21203/rs.3.rs-9335700/v1`, posted 2026-06-17 -- before the IJCS
rejection date of 2026-07-05 recorded in this repository's own history,
consistent with automatic in-review preprint posting that a later
journal-level rejection does not retract). Verified via the Crossref API
(`api.crossref.org/works/...`), an authoritative machine-readable source,
not a search-engine summary: type `posted-content`, publisher "Springer
Science and Business Media LLC," single author Soroush Vahidi (NJIT),
title matching the archived draft exactly. This matches the Stage-5 task
brief's own phrasing, "the author's earlier **public** MWFAS ranking
work" -- which, in hindsight, was a signal this stage's research
confirmed rather than a loose word choice. Because it is a genuine public
record, not citing it when discussing "the author's earlier work" would
have been less transparent than citing it correctly, with its preprint
status and non-peer-reviewed status stated explicitly. Added a new bib
entry (`vahidi2026consistencyaware`) and revised both Related Work 2.3
(previously: "That manuscript did not complete peer review and is not
cited here as a prior publication") and the new Discussion 5.4 paragraph
to cite it properly as a preprint while preserving the substance of the
original caveat (not peer-reviewed; results superseded, not confirmed, by
this study). See `CITATION_AUDIT_STAGE5.md` for the full verification
record.

## E. Limitations and Threats to Validity

Drafted `\section{Limitations and Threats to Validity}` (renamed from the
Stage-1 skeleton's plain "Limitations," per the task brief's suggested
title), five subsections following the requested validity taxonomy
(internal, construct, external, statistical conclusion, computational).
Each limitation states the limitation itself, what mitigates it, and what
remains unresolved, per the task brief's explicit three-part structure
requirement -- checked by re-reading each subsection's closing sentences
against that requirement before finalizing.

## F. `POLICY_CHECK.md`

New file recording Stage-5's verification (via a background research
agent using official Springer Nature sources: Nature Portfolio editorial
policies, the Springer group-wide journal-policies page, the SN Computer
Science submission-guidelines page, the Code Policy page, and the
Software/Code Sharing support article) of: the AI-authorship prohibition
and its exact wording; the Methods-section (not Declarations-heading)
placement requirement for AI-use disclosure; the copy-editing exemption;
the absence of a tool/version-naming mandate; a confirmed policy gap
around AI-assisted code specifically (Springer Nature's Code Policy is
silent on AI); the full Declarations order (unchanged from Stage 3,
now with the combined "Data, Material and/or Code availability" heading
form independently reconfirmed); and CRediT's status as recommended, not
mandatory.

## G. Generative-AI disclosure

New `GENERATIVE_AI_DISCLOSURE.md` recording the placement decision (inside
`\subsection{Reproducibility and Implementation}`, Methodology's
Methods-equivalent section, per `POLICY_CHECK.md`) and the disclosure
text itself, which was also **inserted into `manuscript/main.tex`**
directly (policy verification supported doing so this stage, per the task
brief's conditional instruction). The disclosure covers both
software-development assistance and manuscript-drafting assistance in one
statement, states author verification of every AI-assisted output
category the task brief lists, and explicitly denies AI authorship or
independent scientific decision-making, using Springer Nature's own
stated rationale (accountability) as the standard. One open item flagged
for the author: the exact per-stage model identity was not asserted with
certainty (the disclosure names the tool family, "Claude," rather than a
specific model version, since this drafting process cannot fully verify
which specific model handled every one of the seven stages).

## H. Declarations

Updated two backmatter items found to need clearer wording while
implementing item G: the Funding placeholder was reworded to the task
brief's requested `[AUTHOR CONFIRMATION REQUIRED: ...]` format (previously
a less formal Stage-2-era bracketed note); the Authors' Contributions
statement had its self-contradictory "Not applicable; ... Soroush Vahidi
conceived the study..." wording fixed (a statement that both says "not
applicable" and then gives a substantive answer is a genuine
contradiction, not just informal phrasing -- it is now a plain
substantive statement with no "not applicable" prefix, since single-author
attribution is straightforwardly applicable, not an exempted case).

## I. Figure/table reassessment

Re-read every figure and table caption in the context of the completed
Discussion (`FIGURE_TABLE_AUDIT.md`'s new Stage-5 section records this).
No caption implies significance where none exists (checked by `grep` for
"significant" outside an already-qualified context: zero unqualified
matches). Figure 5's caption is confirmed purely structural, with no
retrieval-level implication. No figure was regenerated; no new figure was
added. A conceptual "structural objective vs.\ retrieval objective"
figure, suggested as optional in the task brief, was considered and
declined: the existing prose in Background
(Section~\ref{sec:extraction-eval}'s closing paragraph) and Discussion
(Section~\ref{sec:discussion-mechanism}) already states that distinction
in words precisely enough that a diagram would duplicate the pipeline
figure (Figure 1) rather than add new explanatory value.

## J. Page budget and repetition audit

Updated `README.md`'s page-budget table: 40 pages total (Discussion 5 pp,
Limitations 2 pp -- Discussion ran slightly over and Limitations slightly
under their Stage-4 projections, net roughly on budget). Repetition
checked by `grep` for narrative-transition phrases ("we next," "we then,"
narrative "finally,") outside legitimate list-final-item uses, and for
verbatim-repeated thesis-statement phrasing across sections: no new
repetition introduced beyond the three restatements (Results, Discussion,
Conclusion-to-come) already budgeted in Stage 3.

## K. Compilation

`tectonic` (same toolchain as Stages 2-4; `apt-get` still unavailable).
Final Stage-5 compile: 40 pages, zero undefined references, zero
undefined citations, zero BibTeX errors, zero overfull boxes. The
structured-abstract placeholder and the Conclusion section skeleton are
both confirmed unchanged (`grep` for "Stage 2 drafting" still finds the
abstract's four placeholder paragraphs; the Conclusion section still
contains only its Stage-1 scope-note comment), per the task brief's
explicit "do not write the final Abstract or Conclusion" instruction.
`main.pdf` is the verified output.

## L. This file

Self-referential.
