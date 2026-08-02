# Stage 3 Change Log and Open Questions

Records what Stage 3 (complete experimental Methodology, no Results prose)
actually did, mapped to the task brief's required-outputs list (A-J), for
whoever runs Stage 4 (Results).

## A. Methodology section

Drafted a full `\section{Methodology}` (label `sec:experimental_setup`,
kept from the Stage-1/2 "Experimental Design" skeleton it replaces) in
`manuscript/main.tex`, with eleven subsections exactly matching the task
brief's 3.1-3.11: Research Questions (RQ1-RQ4, none about
policy-selection/active-acquisition, per scope), Experimental Pipeline
(nine numbered stages), Datasets and Retrieval Tasks (Table~1,
`tab:setup`), Base Rankers and Judgment Sources (BM25/TF-IDF/MiniLM, with
exact implementation parameters read from
`scripts/generate_score_file.py`, not assumed), Preference-Graph
Construction (protocol prose + one new `algorithm` environment,
`alg:construction`, reflecting the actual construction code), Repair
Methods (greedy and exact SCIP, with solver version, gap, and time-limit
facts read from `mwfas_solver.py` and
`reports/exact_open_source_ilp_repair_investigation/FINDINGS.md`), Ranking
Extraction Methods (one new equation, Bradley-Terry's MLE model,
Equation~(9)/`eq:bt`; every other method described in prose with
citations, not re-derived), Baselines and Comparisons (Table~2,
`tab:baselines`, a 15-row method-family table), Evaluation Metrics (nDCG
promoted to a numbered equation, `eq:ndcg`, fixing a Stage-2 gap -- see
Section C below), Statistical Analysis (sign-flip permutation test,
Holm/BH, bootstrap, TOST, MDE, all read from
`src/consistency_ranker/statistical_inference.py`, not assumed), and
Reproducibility and Implementation. No outcome value (no number that
depends on having run the analysis) appears anywhere in this section, per
the task brief's explicit constraint.

Every equation is numbered; every table uses `booktabs` (`\toprule`
etc.); no table required `\resizebox`; heading depth stayed at
`\section`/`\subsection` only (two levels), within the confirmed
three-level SN Computer Science limit; every table and the algorithm are
referenced in the surrounding prose; no `\subsubsection` was used anywhere
in the manuscript.

## B. `MANUSCRIPT_PLAN.md` and `EVIDENCE_MAP.md` updates

- `MANUSCRIPT_PLAN.md`: **no changes needed.** The task brief anticipated
  needing to correct a Bradley-Terry claim there; a full audit
  (Section C below) found the opposite -- `MANUSCRIPT_PLAN.md`'s original
  C9/C10 row was already correct, and it was Stage 2's own conclusion that
  needed correcting.
- `EVIDENCE_MAP.md`: added a "Stage-3 clarification on claim #4 vs. claim
  #6's method-family scope" note after the "Planned main-paper claims"
  table, distinguishing the three separate exact-repair-adjacent
  evidence sources (`full_calibrated_core` five-pair greedy family;
  `final_revision_task4_exact_baseline_fairness_20260715`'s expanded
  nine-pair exact-vs-unrepaired family; `exact_open_source_ilp_repair_investigation`'s
  seven-method exact-vs-greedy family) and which headline numbers each
  backs.

## C. Stage-2 open questions resolved

Of `STAGE2_CHANGELOG.md`'s nine open questions, this stage resolves:

- **#3 (Markov vs.\ Rank Centrality naming) and #4 (Bradley-Terry
  evaluation status) -- both resolved, and #4 required retracting a
  Stage-2 error, not confirming it.** Reading
  `reports/full_calibrated_core/scripts/run_full_calibrated_core.py`
  (`METHOD_LABELS`, `PAIR_SPECS`, `LEGACY_PAIR_NAMES`,
  `NEW_BASELINE_PAIR_NAMES`) and
  `reports/final_revision_task4_exact_baseline_fairness_20260715/FINAL_REPORT.md`
  in full (not just the primary `full_calibrated_core` "paper_package"
  tables Stage 2 checked) found: Bradley-Terry (`src/rerankers/tournament_agg.py::bradley_terry_ranking`,
  an MM-algorithm MLE fit) **is** evaluated, alongside PageRank, an
  undamped Rank Centrality implementation genuinely distinct from the
  primary family's damped "Markov" method, and a Markov hybrid, as an
  *expanded* nine-pair method family used specifically in Task 4's
  36-cell canonical and 56-cell larger-pool exact-repair-vs-unrepaired
  comparison. "Markov" and "Rank Centrality" are two related but distinct
  evaluated methods, not two names for one method (`markov_graph_ranking.py`'s
  damped chain vs.\ `baseline_ranking.py::rank_centrality_ranking`'s
  undamped, self-loop-ergodic chain). Both corrections are now stated
  precisely in Methodology Sections~\ref{sec:extraction-methods}
  and~\ref{sec:baselines} (Table~2) and amended into
  `STAGE2_CHANGELOG.md` directly (struck through, not deleted, with a
  dated Stage-3 amendment explaining the error) and `EVIDENCE_MAP.md`
  (Section B above).
- **#1 (conceptual pipeline figure)**: not added to the manuscript this
  stage either (Methodology is prose/table/algorithm only, no figures
  drafted, per the task brief), but a concrete, reviewable
  generation prompt now exists
  (`figure_prompts/f1_pipeline_dual_repair.md`) specifying exactly what
  must change from the existing `figures_v2/fig1_pipeline.pdf` (add the
  exact-repair branch as a co-equal box, not a relabel) -- this was a
  genuine gap `FIGURE_TABLE_AUDIT.md` surfaced: the existing figure only
  shows greedy repair and would visually contradict this manuscript's
  framing if reused unchanged.
- **A latent nDCG-equation gap, not on the original Stage-2 open-question
  list, found and fixed while cross-referencing Methodology against
  Background**: Background's nDCG definition (Stage 2) was written as
  inline, unlabeled math (`$\mathrm{DCG}@k = \dots$`), so Methodology's
  Evaluation Metrics subsection had nothing to `\ref{}`. Promoted it to a
  numbered `equation` environment (`eq:ndcg`) in Background and fixed the
  forward reference. Caught by re-reading the compiled PDF's rendered
  text, not just by rendering without visible errors -- `pdflatex`/`tectonic`
  do not error on a missing numbered-equation cross-reference to inline
  math; they simply have nothing to point `\eqref` at, so this required
  a placeholder self-check ("Equation not renumbered here") before it was
  caught, not a compiler warning.

Still open (see Section G below): #2 (seven-dimension taxonomy
reappearance), #6 (page-budget overlap, now addressed by Section E below),
#7 (funding statement), #8 (bibliography pruning), and the general
figure-regeneration items now tracked in `FIGURE_TABLE_AUDIT.md` instead
of the Stage-2 list.

## D. `FIGURE_TABLE_AUDIT.md` and `figure_prompts/`

New `papers/SNCS_2026/FIGURE_TABLE_AUDIT.md`: visually inspected (not just
listed) the four most likely-reusable existing figures
(`fig1_pipeline.png`, `fig2_bm25_share.png`, `fig5_cycle_decomposition.png`,
`fig7_bootstrap_forest.png`), confirmed vector `.pdf` counterparts exist
for each, read `figures_v2/style.py` to confirm the categorical palette is
already colorblind-validated (not something Stage 3 needed to redo), and
flagged the superseded raster `.png` duplicates in `papers/JDIQ_2026/manuscript/`
and the redundant `.png` copies throughout `reports/full_calibrated_core/figures/`
as do-not-reuse. Two new generation prompts written under
`papers/SNCS_2026/figure_prompts/`: `f1_pipeline_dual_repair.md` (F1,
adds the exact-repair branch) and `f5_exact_vs_greedy_gap.md` (F5, a
genuinely new appendix figure with no prior artifact, grounded in
`reports/exact_open_source_ilp_repair_investigation/tables/structural_summary_by_dataset_regime.csv`).
Neither figure was actually generated this stage -- that is correctly
Stage 4+ work, once Results data is being assembled and the figures can
be checked against final section/table numbers.

## E. Page budget

Added a "Page budget (Stage 3)" section to `README.md`: confirmed (via a
background research pass against `link.springer.com/journal/42979`'s
official submission guidelines, not a secondary summary) that SN Computer
Science states no page/word/figure-count limit for original-research
articles beyond the structured abstract's 150-250 words; set an internal
target of roughly 34-40 total pages given the current, actually-compiled
26-page front-half-plus-Methodology state (Introduction 3pp, Related Work
3pp, Background 5pp, Methodology 8pp, all drafted; Results/Discussion/
Limitations/Conclusion/Data-Availability still 0pp skeletons).

## F. Bibliography

Added, all independently verified this stage (not copied from an
unverified secondary source): `robertson2009probabilistic` (BM25),
`salton1988termweighting` (TF-IDF), `wang2020minilm` (MiniLM), `holm1979simple`
(Holm correction), `benjamini1995controlling` (Benjamini-Hochberg),
`efron1993introduction` (bootstrap). No existing entry was removed;
bibliography pruning remains explicitly deferred (Section G).

## G. Unresolved questions for Stage 4 (Results)

1. **Seven-dimension audit taxonomy** (carried over from Stage 2, still
   undecided): whether it reappears at all, and if so where and in what
   (named, not lettered) form.
2. **Funding statement**: `manuscript/main.tex`'s Declarations backmatter
   still reads a placeholder pending author confirmation; every other
   required declaration heading (Conflict of interest, Ethics approval,
   Consent to participate, Consent for publication, Data/materials/code
   availability, Authors' contributions) was completed this stage per the
   verified SN Computer Science requirement that every heading must
   appear even as "Not applicable," on pain of the submission being
   returned as incomplete.
3. **Bibliography pruning**: still deferred; Results/Discussion will cite
   further currently-unused seed entries (dataset citations already used
   in Methodology now; statistical-methodology entries now used too).
   Prune only after Results/Discussion/Conclusion are drafted.
4. **T1 table (vote-construction regimes)**: still prose-only (Background
   Section~\ref{sec:pref-graph}, Methodology
   Section~\ref{sec:construction-protocol}), not a table, per the Stage-2
   "no tables" carryover and this stage's own scope. Revisit in Stage 4
   if a compact table would help Results readability once actual
   cyclicity numbers are being reported per regime.
5. **F1/F5 figures**: prompts written, not executed (Section D). Stage 4
   should run them once Results tables are assembled, so the figures can
   cite final table/section numbers rather than placeholders.
6. **A benign but unexplained `xdvipdfmx` warning**: every Stage-3 compile
   emits `warning: Object @table.1 already defined.` and
   `@table.2 already defined.` (once each, matching the manuscript's two
   tables). This does not affect the rendered PDF (both tables render
   correctly, confirmed via `pdftotext`) and is not an undefined-reference
   or BibTeX error; it appears to be a `hyperref`/`xdvipdfmx`
   PDF-destination-naming quirk rather than a duplicate `\label`
   (verified no duplicate `\label{tab:...}` exists). Not investigated
   further this stage since it does not block a clean, correct compile;
   flagged here so it is not mistaken for a new problem if it recurs in
   Stage 4 with more tables.
7. **BRIGHT's `examples` HuggingFace configuration**: Methodology states
   the study accesses BRIGHT via its public `examples` configuration
   (confirmed from `src/consistency_ranker/data/bright_loader.py`), but
   this stage did not verify which of BRIGHT's underlying domain splits
   that configuration draws from. Not needed for Methodology (which
   states protocol, not per-domain results), but worth a one-line check
   before Results prose makes any domain-specific claim about BRIGHT.

## H. Compilation

`tectonic` (no system `pdflatex`/`bibtex`; `apt-get` still requires a
password this environment does not have -- unchanged from Stage 2).
Final Stage-3 compile: 26 pages, zero undefined references, zero
undefined citations, zero BibTeX errors (`main.blg` clean). `main.pdf`
in the manuscript directory is that verified output.
