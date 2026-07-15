# Task 5 Final Report: Submission-Quality Revision

## 1. Remaining weaknesses (from the fresh reviewer read)

Not everything raised could be fixed by text alone. Still open after this
task, honestly:

- **Significance/adoption case is asserted, not demonstrated on a second
  representation.** The Discussion's claim that the construction-first
  lesson generalizes to learned fusion, cross-encoder blending, and
  LLM-generated graphs is argued by analogy, not tested empirically on a
  second derived-structure method. Closing this fully would require a new
  experiment outside this paper's scope.
- **No specific prior work is shown asserting that FAS repair improves
  retrieval nDCG for multi-ranker IR specifically.** Reframed honestly in
  §1 (the paper now states plainly that the assumption under test is the
  gap between a structural guarantee and a retrieval-effectiveness claim,
  not a specific published claim) rather than fixed by finding a citation
  that may not exist.
- **The null retrieval-robustness conclusion has not been tested under a
  genuine top-k-from-a-larger-pool evaluation** (k meaningfully smaller
  than the candidate pool). This is now explicitly flagged as an open
  question in both the Discussion and Limitations (see item 2 below) —
  the most consequential single finding from the fresh review — but
  answering it requires new experiments, not text.
- **The four newly-added baselines (PageRank, RankCentrality, Bradley-Terry,
  Markov hybrid) are not included in the absolute-performance comparison**
  against CombSUM/RRF/Prior/Borda (Table `tab:pooled-baseline`); they
  appear only in the null-effect robustness check. Not fixed in this task
  (would need to locate or recompute their absolute macro-nDCG from
  already-generated per-query data, which was judged lower priority than
  the other findings given the time available).
- **BM25-TF-IDF correlation is now disclosed as a limitation but not
  measured.** The paper acknowledges the two lexical rankers are not fully
  independent evidence sources; it does not report an actual correlation
  statistic between them.

## 2. Reviewer concerns addressed

A dedicated fresh-eyes review (a separate agent, instructed to read only
`main.tex` cold, ignoring every prior audit report from Tasks 1-4) produced
12 ranked criticisms. Addressed in this task:

1. **The k=|D_q| tautology (the review's top concern).** The nDCG cutoff
   equals the candidate-pool size in every dataset, so the "top-k document
   set never changes" finding in the conditional analysis is a structural
   consequence of the evaluation design, not an independent empirical
   discovery. Corrected in three places: the conditional-analysis table's
   surrounding text, the Discussion's mechanistic explanation (replaced a
   flawed "top-k boundary" argument with the correct position-discounted-
   gain mechanism), and a substantially expanded Limitations bullet that
   states the open question directly. A self-correction note is included
   in the Discussion disclosing that an earlier draft's boundary-crossing
   explanation was wrong.
2. **Dataset-list contradiction (SciDocs vs.\ BRIGHT) in the real-LLM
   section.** Verified against the actual stored-corpus directory
   (`experiments/real_llm_integrity_audit_20260713_034713/`, which covers
   `bright`, `fiqa`, `hotpotqa` — not SciDocs) and corrected the one wrong
   instance.
3. **"Twelve registered protocols" and the undefined "z-score robustness
   calibration."** Added a paragraph enumerating all twelve registered
   protocol configurations (the four named ones plus their quantile grid,
   plus four further ablation/robustness configurations previously
   referenced only by an aggregate count), with a one-line definition of
   each of the four that were missing.
4. **Unattributed "myth" framing.** Reframed the Introduction to state
   precisely what is and is not established by the cited combinatorial
   literature (a structural guarantee, not a retrieval-effectiveness
   claim), rather than implying a specific unattributed claim is being
   debunked.
5. **BM25/TF-IDF correlation.** Added to Limitations (see item 1 above).
6. **Leftover internal TODO comment with internal file paths.** Scrubbed
   the `reports/normalization_protocol_audit_20260714/...` path references
   (anonymization hygiene) while keeping the substantive forward-looking
   note; also strengthened the adjacent visible prose to explicitly name
   Figures 3-5 as showing only the primary protocol, addressing the
   substance of the comment without regenerating any figure.
7. Baselines-not-in-absolute-table, significance/adoption case: see item 1
   (remaining weaknesses) — acknowledged, not fully closed.
8. **No anonymized artifact link.** Cannot be fixed inside this repository
   (requires external hosting at actual submission time); captured as an
   explicit TODO in `SUBMISSION_CHECKLIST.md`.
9. **Upstream ranker implementation details never specified.** Located the
   actual implementations in the codebase (`rank_bm25.BM25Okapi` at library
   defaults $k_1=1.5$, $b=0.75$; a custom log-TF/smoothed-IDF/cosine-
   normalized TF-IDF; `sentence-transformers/all-MiniLM-L6-v2` with cosine
   similarity) and added them to the manuscript with an explicit caveat
   that the reported scale-dominance magnitude is a property of this
   specific configuration.
10. **"N tests" framing inflated by structurally-trivial `ms2`/
    `ms1_drop_mutual` cells.** Added an explicit clarification that roughly
    two-thirds of each joint-multiplicity family's cells are near-
    tautological, so the correction is conservative rather than
    significance-manufacturing, without changing any reported test count
    or p-value.
11. **SciDocs's positive point estimate dismissed only by a large,
    multi-dataset correction family.** Computed a SciDocs-`ms1`-scoped
    Holm correction over exactly its own 5 method pairs directly from
    already-generated data (`full_statistical_tests.csv`): the smallest
    raw p-value ($0.012$) becomes $0.060$ under this narrower, more
    defensible test — still short of significance. Added this as an
    explicit sensitivity check that preempts the objection with a
    positive result, strengthening rather than merely defending the
    paper's central claim.
12. **Figures 3-5 known-incomplete relative to prose sensitivity claims.**
    Addressed via items 6 above (comment cleanup) and explicit prose
    naming the figures and directing readers to the complete numeric
    table; still not fixed by regenerating figures, per this task's
    explicit constraint.

## 3. Manuscript improvements (general)

Beyond the specific reviewer-criticism fixes above: the Introduction now
explicitly answers why the problem matters to a data-quality journal
(preference graphs as derived data artifacts, analogous to any other
audited dataset) and why reproducibility is part of the paper's claim, not
an appendix concern. The Related Work section gained an explicit
reproducibility-positioning paragraph. The Discussion gained a new
paragraph on lessons for LLM-generated preference graphs, tying the
paper's central thesis to the increasingly relevant LLM-as-judge setting
using the paper's own already-reported real-LLM audit numbers. The
Practical Implications section grew from 5 to 10 concrete, evidence-
grounded recommendations, explicitly covering threshold selection,
candidate-pool policy, exact-vs-greedy repair, statistical reporting
discipline, and reproducibility as a design requirement — the topics the
task asked for that were previously only implicitly covered. The
Introduction's contributions list gained two bullets reflecting the
Task 2/3 robustness work, which had not been mentioned there at all. The
Abstract and Conclusion were extended to state that the null result is
itself robustness-checked across protocols, pools, and baselines, not
only true under one convenient configuration.

## 4. Introduction improvements

See item 3. Concretely: added a new paragraph directly after the "derived
data artifact" framing making the JDIQ/data-quality fit and the
reproducibility motivation explicit (previously implicit at best); added
two contribution bullets; softened the FAS-repair motivating claim to
state precisely what the cited literature does and does not establish.

## 5. Discussion improvements

Expanded the top-k mechanism explanation (now corrected, see item 1 above);
added a full paragraph on lessons for LLM-generated preference graphs
(previously absent entirely); the "structural success does not guarantee
retrieval gain" paragraph now states the k=|D_q| design property explicitly
rather than implying an unconditional finding.

## 6. Practical-impact improvements

Table `tab:practical-implications` grew from 5 to 10 rows; five new
paragraphs added covering threshold-selection discipline, candidate-pool
policy reporting, exact-vs-greedy repair guidance (a genuinely new,
previously-absent recommendation directly following from the exact-solver
robustness check already in the paper), statistical-reporting discipline,
and reproducibility as a design requirement.

## 7. Title assessment

**Recommendation: keep the current title** ("Score Normalization and Vote
Construction Govern Preference-Graph Repair Outcomes in Multi-Ranker
Retrieval"). It is specific, accurately scoped, and immediately
communicates the paper's actual claim. Candidate alternatives considered
(e.g., leading with "data quality" or "reproducibility" more explicitly, or
folding in "candidate pooling") were evaluated and rejected: each traded
the current title's precision for either added length or vaguer framing,
without being a clear improvement, and the task's own instruction was to
change the title only if a clearly superior alternative exists. None did.

## 8. Cover-letter location

`papers/JDIQ_2026/submission/COVER_LETTER.md`. Contains motivation,
contribution, JDIQ relevance, reproducibility/artifact-availability, and
ethical-considerations paragraphs; author-identity fields are explicit
placeholders (`[Corresponding Author Name]`, etc.) since no real author
information exists in this anonymized repository and none was invented.
Not submitted anywhere.

## 9. Submission checklist

`papers/JDIQ_2026/submission/SUBMISSION_CHECKLIST.md` — organized by
manuscript, bibliography, figures, supplementary material, repository/
anonymization, metadata, data/artifact availability, and cover letter, with
each item marked DONE (verified in this repository) or TODO (requires
author action outside this repository's scope, e.g. real ORCID iDs,
external artifact hosting). Companion inventory:
`papers/JDIQ_2026/submission/SUPPLEMENTAL_PACKAGE.md`.

## 10. Remaining limitations

See item 1. In addition: this task's fresh-review agent was instructed not
to read prior audit reports, by design, to get a genuinely cold read; that
means it independently rediscovered some ground Tasks 2-4 had already
covered (e.g., candidate-pool robustness, joint multiplicity families) and
confirmed those were already well handled, which is a useful cross-check
but not new information. The one substantive new empirical finding from
this task's own analysis (not just editing) is the SciDocs-scoped Holm
correction (item 2.11) — everything else in this report is either a text
correction, a reframing for honesty/precision, or a documentation
deliverable, consistent with the task's own instruction not to modify
scientific conclusions without new supporting evidence.

**Validation:** `pytest -q`: 550 passed (unchanged, no code modified this
task). `check_repo_ready.py`: 56 OK, 5 pre-existing warnings, 0 failures.
LaTeX build: 0 undefined references, 0 multiply-defined labels, clean
compile (verified after every substantive edit, ~9 rebuilds this task).
Bibliography: 29/29 cite keys resolved both directions. No duplicate
labels. No figure file touched (verified via `git status` against
`figures_v2/*.pdf` and `figure{1,3,5}.png`).
