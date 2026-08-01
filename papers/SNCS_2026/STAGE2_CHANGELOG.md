# Stage 2 Change Log and Open Questions

This records what Stage 2 (front-half drafting: `STORY.md`, Introduction,
Related Work, Background and Problem Formulation) actually did, for the
benefit of whoever runs Stage 3+. It is a change log, not manuscript prose.

## A. Stage-1 inconsistencies resolved

- **BRIGHT citation key** (`MANUSCRIPT_PLAN.md` Section 10, item 1):
  resolved to `su2025bright`, an `@inproceedings` entry for the published
  ICLR 2025 (Spotlight) version, verified directly against the ICLR 2025
  proceedings PDF and the ICLR virtual poster page (both fetched
  2026-07-31). The old `su2024bright` arXiv-preprint entry was removed from
  `manuscript/references.bib`. See `README.md`, "Stage-2 resolutions."
- **"Dimension F" / "Outcome F" naming collision** (`MANUSCRIPT_PLAN.md`
  Section 10, item 3): resolved by not lettering diagnostic dimensions in
  this manuscript's prose at all; the specific question JDIQ called
  "dimension F" is referred to directly (e.g. "the retrieval-utility
  check"). See `README.md`, "Stage-2 resolutions," for the full rationale
  and the constraint this places on any later reintroduction of a compact
  lettered table.

## B. New files

- `STORY.md` -- new. Internal narrative plan; not manuscript prose.
- `manuscript/main.pdf` -- new. Compiled output of the current `main.tex`
  (Stage 2 state), verified to build cleanly (see Section D below).

## C. `manuscript/main.tex` changes, by section

- **Introduction**: fully drafted (was a scope-note comment). Written
  fresh for this stage rather than copied from either prior draft, but
  informed by both: the four-stage decomposition (construction / repair /
  extraction / evaluation) and the "exact repair as diagnostic control,
  not a proposed method" framing are new to this manuscript and did not
  appear in this form in the IJCS draft or JDIQ. Ends with exactly four
  contributions, matching this stage's brief and consistent with
  `MANUSCRIPT_PLAN.md` Section 3's contribution list (recombined to match
  this stage's specific four-item framing).
- **Related Work**: fully drafted (was a scope-note comment), reorganized
  by scientific topic rather than by manuscript history, per this stage's
  brief. Substantially reuses and revises prose and citation choices from
  the IJCS draft's "Learning to Rank and Reranking" / "Preference Modeling
  and Graph-Based Ranking" subsections and JDIQ's "Background and Related
  Work" section (`MANUSCRIPT_PLAN.md` Section 8.1/8.2 reuse plan), but no
  paragraph is copied verbatim -- every paragraph was rewritten to fit the
  new four-subsection structure (2.1 pairwise ranking and preference
  aggregation; 2.2 pairwise and graph-based IR ranking; 2.3 inconsistency,
  cycles, and repair; 2.4 structural quality versus downstream utility).
  Subsection 2.4 has no direct precedent in either prior draft; it is new
  and states this paper's positioning relative to the literature directly.
  Added an explicit, non-cited paragraph in 2.3 positioning this
  manuscript relative to the author's earlier, unpublished, rejected IJCS
  draft (no `\cite` entry -- per this stage's instruction not to imply a
  rejected/unpublished manuscript is a prior publication).
- **Background and Problem Formulation** (renamed from the Stage-1
  skeleton's "Preference-Graph Construction and Repair"): fully drafted
  (was a scope-note comment). Reuses and adapts core formalism from JDIQ's
  Methodology section verbatim or near-verbatim where the underlying
  object is unchanged: the $G_q=(V_q,E_q,w_q)$ definition, the min-max
  normalization equation, the MWFAS objective equation, and the hybrid
  prior-plus-graph scoring equation. Reuses the three vote-construction
  regime definitions (`ms2`/`ms1`/`ms1_drop_mutual`) and their rationale
  from the IJCS draft's Method section (`tab:vote_construction_regimes`
  content, presented here in prose/itemize form rather than as a table,
  since this stage's brief excludes drafting tables). New material not
  present in either prior draft: an explicit exact-repair linear-ordering
  MIP formulation (binary `before[u,v]` variables, antisymmetry and
  transitivity constraints, objective), reconciled directly against
  `src/consistency_ranker/mwfas_solver.py`'s `_solve_scip` implementation
  (read in full this stage, not assumed); an explicit description of
  greedy repair reconciled against
  `src/consistency_ranker/greedy_fas.py` (confirmed: iterative
  minimum-weight-edge-on-a-cycle removal, not the Eades--Lin--Smyth
  linear-arrangement heuristic cited in Related Work as adjacent
  literature); an explicit list of the extraction methods actually present
  in the canonical package's method-key vocabulary (verified against
  `reports/full_calibrated_core/METHODS_AND_PROTOCOL.md` and the
  `method_key` column of
  `reports/full_calibrated_core/outputs/calibrated_all4/paper_package/tables/table_primary_macro_method_comparison.csv`,
  not assumed from either prior draft); and an explicit nDCG definition
  with a citation to the original Järvelin & Kekäläinen paper (not present
  in either prior draft's method section). No table or figure was added
  in this section, per this stage's "no tables/figures except an optional
  pipeline figure" constraint; the optional pipeline figure was not added
  (see Open Question 1 below).
- **Sections intentionally left untouched** (still Stage-1 scope-note
  comments, per this stage's explicit brief not to draft them yet):
  Experimental Design, Results, Discussion, Limitations, Conclusion, Data
  Availability and Reproducibility, Declarations. The structured-abstract
  placeholder is likewise intentionally untouched.
- **Two LaTeX-class bug fixes**, found only by actually compiling (see
  `README.md`, "Compilation," for the full explanation):
  - Removed a redundant `\bibliographystyle{sn-basic}` call that
    duplicated the one `sn-jnl.cls`'s `sn-basic` option already issues
    internally, which was silently breaking every citation via a
    `bibtex` "Illegal, another \bibstyle command" error that neither
    `pdflatex` nor `tectonic` themselves surfaced as an error.
  - Added the `Numbered` document-class option. `sn-basic` alone renders
    author-date citations (the class's "Namedate" default); `Numbered` is
    a separate option required to get the numeric, consecutively numbered
    citation style SN Computer Science's guidelines specify. Verified by
    inspecting the actual rendered PDF text before and after the fix.

## D. `manuscript/references.bib` changes

- `su2024bright` -> `su2025bright` (see Section A above).
- Added, copied from the already DOI-verified IJCS archive bibliography
  (`papers/_archive/IJCS_early_draft.zip:references.bib`, per that
  archive's own documented "verified DOI-complete entries" disposition):
  `burges2010ranknet` (RankNet/LambdaRank/LambdaMART overview),
  `fagin2004aggregating` (rank comparison with ties), `ferrara2024biasaware`
  (bias-aware pairwise ranking, DMKD 2024), `jarvelin2002cumulated` (the
  original nDCG paper, needed for the Background section's metric
  definition).
- Added `hu2024acyclic`, a new entry not present in either prior draft's
  bibliography: "Towards Acyclic Preference Evaluation of Language Models
  via Multiple Evaluators" (Hu, Zhang, Xiong, Ratner, Ding, Krishna;
  arXiv:2410.12869), found via a Stage-2 literature search and verified
  directly against the arXiv abstract page (title, author list, and
  subject class cross-checked across two independent fetches after an
  initial fetch returned an inconsistent, stale-version title). Cited in
  Related Work 2.3/2.4 as directly on-point recent evidence that other
  work treats acyclicity as valuable and reports downstream gains on
  different tasks (model ranking, response selection, fine-tuning data
  selection) than this paper's retrieval setting.
- No entries were removed for being unused (see Open Question 9 below);
  only the `su2024bright` -> `su2025bright` swap changed an existing
  entry's key/type.

## E. `README.md` changes

- Added a "Stage-2 resolutions of the two Stage-1 inconsistencies"
  section (see Section A above).
- Rewrote the "Compilation" section: it previously stated compilation had
  not been verified (no toolchain available); Stage 2 found and used
  `tectonic` (already installed at `~/.local/bin/tectonic`; `apt-get`
  installation of a system `texlive` was attempted first and failed for
  lack of passwordless `sudo`), verified a full clean compile, and
  documented the two class-usage pitfalls from Section C.

## F. Verification performed this stage

- BRIGHT bibliographic metadata verified against the ICLR 2025 proceedings
  PDF and virtual poster page (primary sources), not only OpenReview.
- `hu2024acyclic`'s title/authors verified against the arXiv abstract page
  directly (not a secondary summary), after an initial WebFetch returned
  an inconsistent (evidently stale-version) title/author combination for
  the same arXiv ID -- a second, more literal fetch resolved the
  discrepancy against the "Submission history" version list.
- `mwfas_solver.py`, `greedy_fas.py`, `baseline_ranking.py`,
  `markov_graph_ranking.py`, `graph_construction.py`, and
  `pairwise_prefs.py` were read in full to reconcile the Background
  section's equations and method descriptions with the actual
  implementation, per this stage's "do not invent a formulation" and
  "reconcile the equations with the canonical implementation" instructions.
- `reports/full_calibrated_core/METHODS_AND_PROTOCOL.md` and the
  `method_key` column of its `table_primary_macro_method_comparison.csv`
  were read to confirm exactly which extraction methods are in the
  canonical evaluated set (see Open Question 4, which surfaces a
  discrepancy this check found).
- `main.tex` was compiled end-to-end (`tectonic`, BibTeX pass included)
  to a clean 17-page PDF with zero undefined references, zero undefined
  citations, and zero BibTeX errors in the final pass. `main.pdf` in the
  manuscript directory is that verified output.

## G. Unresolved questions for Stage 3+ (Methods / Experimental Design / Results)

1. **Conceptual pipeline figure**: this stage's brief allowed one small
   conceptual pipeline figure in the Introduction "only if it substantially
   improves" it. Not added this stage -- the four-stage distinction
   (construction / repair / extraction / evaluation) is already stated
   clearly in prose, and adding a new figure asset was judged higher risk
   than benefit for this stage. Revisit if an editor or reviewer wants a
   visual, or when Experimental Design is drafted and a figure may serve
   double duty there.
2. **Seven-dimension audit taxonomy**: whether JDIQ's `tab:dq-taxonomy`
   (or an expanded, worked-example version of it) reappears in this
   manuscript at all, and if so where (Background vs. Results) and in
   what form, is not decided. `MANUSCRIPT_PLAN.md` Section 8.2 leaves two
   options open (expand with named, not lettered, rows; or fold into
   ordinary prose without a table). The Stage-2 naming-collision
   resolution (Section A above) constrains whichever choice Stage 3+
   makes: no lettered dimensions, ever.
3. **"Markov" vs. "Rank Centrality" naming**: the canonical package's
   stored `method_key` is `markov_graph`/`markov_graph_repaired`
   (implemented in `markov_graph_ranking.py` as an explicitly
   Rank-Centrality-style, PageRank-damped Markov chain). Related Work
   cites Rank Centrality (Negahban, Oh & Shah) for this method family.
   Stage 3+ (Results tables) should decide whether to relabel this method
   "Rank Centrality" for reader clarity or keep "Markov" to match the
   stored artifact names exactly, and state the equivalence explicitly
   wherever the method first appears in a table.
4. **Bradley-Terry is not an evaluated canonical-package baseline** --
   this is a correction to carry into Stage 3, not just an open question.
   `MANUSCRIPT_PLAN.md`'s response to reviewer concern C9/C10 states
   "PageRank, Rank Centrality, and Bradley-Terry are already implemented
   and evaluated." Checking `reports/full_calibrated_core/`'s actual
   method-key vocabulary this stage found only: `prior_only`, `rrf`,
   `combsum`, `borda_fuse`, `copeland_graph`(`_repaired`),
   `balance_graph`(`_repaired`), `markov_graph`(`_repaired`), and the two
   `hybrid_*_a0p3_minmax` families -- no Bradley-Terry method key appears
   anywhere in that package's tables, and no Bradley-Terry ranking
   function exists in `src/consistency_ranker/`. Bradley-Terry is citable
   as literature (Related Work 2.1) but must **not** be described as an
   evaluated method in this manuscript's Experimental Design or Results
   sections. `MANUSCRIPT_PLAN.md` Section 7's C9/C10 row should be
   corrected accordingly before or during Stage 3.
5. **HodgeRank is implemented but explicitly out of scope**:
   `baseline_ranking.hodge_rank_ranking` exists in the codebase and is
   exercised by unit tests, but
   `reports/final_revision_task9_final_peer_review_20260715/tables/baseline_completeness_decision.md`
   explicitly scopes it out of the canonical evaluated set. Related Work
   2.1 cites the underlying Hodge-theoretic literature but does not claim
   HodgeRank was evaluated. Stage 3+ (Limitations) should consider one
   explicit sentence noting HodgeRank is implemented but not run as part
   of the canonical evaluation, so a reader who inspects the repository
   does not read its absence from Results as an oversight.
6. **Page-budget overlap check**: Background 3.1-3.5 absorbed some
   material that `MANUSCRIPT_PLAN.md`'s original Section 4 outline
   ("Preference-Graph Construction and Repair") assigned to what is now a
   separate Experimental Design section. Stage 3 should draft Experimental
   Design with this already-covered ground in mind and avoid restating
   the graph/repair/extraction formalism.
7. **Funding/acknowledgment statement**: `manuscript/main.tex`'s
   Declarations backmatter still reads "[Stage 2: confirm funding
   statement...]" -- this was explicitly out of this stage's
   Introduction/Related-Work/Background scope and was not verified. Must
   be confirmed before a submission-track stage.
8. **Bibliography pruning**: `references.bib`'s header comment calls for
   pruning unused entries "once main.tex prose is drafted (Stage 2+)."
   Not done this stage, because Experimental Design/Results/Discussion
   (Stage 3+) will cite additional currently-unused seed entries (dataset
   citations, statistical-methodology citations for the Holm-correction
   protocol, etc.); pruning now would likely remove entries Stage 3+ needs
   back. Defer pruning to after Stage 3+ drafting is complete.
