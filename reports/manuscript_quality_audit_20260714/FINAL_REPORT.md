# Task 4 Final Report: Reproducibility, Consistency, and Manuscript-Quality Audit

## 1. Unsupported claims found

None in `main.tex` itself. A dedicated grep/read audit for Gurobi
references, LLM-as-primary-evidence framing, six-way-taxonomy leakage,
stale protocol names, inconsistent query counts, and novelty/superiority
overreach found the manuscript already clean on all counts (see item 3 for
the one exception, which was a factual/numerical error rather than an
unsupported claim). One genuine numerical error was found and fixed: the
Methods and Baselines fairness-verification paragraph stated "1,704
queries," which does not match its own source table
(`baseline_fairness_verification.csv`, sums to 1,026 = 342 usable queries
x 3 regimes, the figure used consistently everywhere else in the
manuscript). Corrected in `main.tex` and in the two Task 3 report files
that originated the error (`ANALYSIS.md`, `FINAL_REPORT.md`), with a
disclosed self-correction note in the latter. The underlying conclusion (0
fairness violations) was unaffected by the arithmetic error.

## 2. Wording improved

- Abstract: added the candidate-pool and additional-baseline robustness
  findings (previously the abstract mentioned only the raw-vs-normalized
  ablation and the primary protocol; it now states that the null result
  survives jointly across independently-defined normalization protocols,
  candidate pools, and additional baselines), and softened "fixed candidate
  pools" to reflect that pooling is now itself a checked, not merely
  assumed, choice.
- Introduction's contributions list: added two new bullets ("Construction-
  choice robustness, checked jointly rather than assumed" and "A
  conditional, activation-aware account of when repair does and does not
  matter") reflecting the Task 2/3 work, which the contributions list
  previously did not mention at all.
- Conclusion: extended the "deliberately layered robustness evidence"
  sentence to include the protocol/pool/baseline joint checks alongside the
  already-listed paired testing/bootstrap/influence/multiplicity/raw-vs-
  normalized evidence.
- Limitations: merged two overlapping bullets ("Normalization remains a
  design choice, not a proven optimum," which had gone stale and vague
  since Task 2's work superseded it, and "Retention-target sensitivity...")
  into one consolidated, precise bullet, removing the redundant and now-
  inaccurate reference to "the pilot."
- Baselines paragraph (Methods): added a new paragraph reporting the
  fairness-verification and joint-multiplicity result for the four new
  baselines (PageRank, RankCentrality, Markov-hybrid, Bradley-Terry), which
  had been computed in Task 3 but never actually written into the
  manuscript text.
- Figure 1 caption and accessibility Description: fully rewritten to match
  the actual replacement figure (8 stages with their real per-panel text,
  the dataset/regime/solver/statistics summary panels), removing a claim
  about a "dashed arrow" raw-margin-ablation bypass that is not present in
  the new figure, and a "three-color-coding" claim that doesn't match the
  new figure's per-stage color scheme.

## 3. Duplicated/inconsistent material found and marked

A cross-document consistency audit found that ~9 pre-writing planning docs
under `papers/JDIQ_2026/` (not `manuscript/`) predate the finished
manuscript and, in several cases, actively contradict it: `README.md`,
`CANONICAL_PAPER_STORY.md`, `PROJECT_STATUS.md`, `MANUSCRIPT_OUTLINE.md`,
`TABLE_PLAN.md`, `JDIQ_GUIDELINE_SUMMARY.md`, `SUPPLEMENTARY_MATERIAL.md`,
`CONTRIBUTION_AUDIT.md`, `EVIDENCE_STRENGTH_AUDIT.md`,
`HIDDEN_STORY_AUDIT.md`, `FIGURE_SPECIFICATIONS.md`, and
`manuscript/README.md` itself. The most serious: several present the
six-way rule-based failure taxonomy and an unreleased "CARB" benchmark as
central, current evidence, when the finished manuscript's Limitations
section explicitly excludes that taxonomy as evidence and never mentions
CARB at all; `SUPPLEMENTARY_MATERIAL.md` in particular is an actionable
packaging plan that, if followed literally, would attach the deprecated
taxonomy to a real submission. All twelve files were marked with a clear,
specific `SUPERSEDED`/`PARTIALLY SUPERSEDED` banner (not deleted, not
rewritten) explaining exactly what is stale and pointing to
`manuscript/main.tex` as the source of truth. `docs/REPRODUCTION_Q1.md`
(documents an older, different results package) was similarly marked and
`README.md` (repo root) updated to point new readers to the new canonical
guide first.

## 4. Documentation changes

- New: `docs/REPRODUCTION_CANONICAL.md` — the current, accurate
  reproduction guide for `main.tex`, covering environment setup, the
  three-layer pipeline map (`full_calibrated_core` /
  `normalization_protocol_audit_20260714` /
  `candidate_pool_conditional_audit_20260714`), every protocol/pool/dataset
  identifier, seeds, solver configuration, exact commands for every major
  experiment, and a table-to-command map so every canonical manuscript
  table can be traced to the exact script that produces it.
- `docs/REPRODUCTION_Q1.md`, `README.md` (repo root): updated pointers, per
  item 3.
- `docs/AUDIT.md`: fixed a stale test count (149 -> 550).

## 5. Table inconsistencies corrected

One (the "1,704" vs "1,026" query-count error, item 1). A systematic
verification of every manuscript table against its source CSV --
`tab:structural-sensitivity-range`, `tab:pool-robustness`,
`tab:conditional-hotpotqa`, the joint multiplicity family counts
(180/240/720/240/300/48 tests), and the sign-flip statistic (18/60) -- found
all other numbers exactly matching their source tables to the reported
precision. No other manually-edited or drifted numbers were found.

## 6. Figure-caption corrections

Figure 1 only (see item 2). Figures 3 and 5's captions were independently
re-checked against their (already-verified, in the prior figure-swap turn)
replacement images and found still accurate -- no changes needed. No figure
image file was regenerated, edited, or redrawn.

## 7. Reproducibility improvements

`docs/REPRODUCTION_CANONICAL.md` (item 4) is the main deliverable here:
git commit hash, Python/dependency versions actually used, the three-layer
pipeline map, all protocol/pool/dataset/regime identifiers, bootstrap and
permutation-test seeds, SCIP solver role, exact commands for every major
experiment (none requiring network access or paid APIs), and a table-to-
command map for every canonical table cited in the manuscript.

## 8. Files changed

Manuscript: `papers/JDIQ_2026/manuscript/main.tex`, `main.pdf`,
`references.bib`. Planning/audit docs marked superseded (banners only, no
content rewritten): `papers/JDIQ_2026/{README.md, CANONICAL_PAPER_STORY.md,
PROJECT_STATUS.md, MANUSCRIPT_OUTLINE.md, TABLE_PLAN.md,
JDIQ_GUIDELINE_SUMMARY.md, SUPPLEMENTARY_MATERIAL.md, CONTRIBUTION_AUDIT.md,
EVIDENCE_STRENGTH_AUDIT.md, HIDDEN_STORY_AUDIT.md, FIGURE_SPECIFICATIONS.md,
manuscript/README.md}`. Reproducibility docs: `docs/REPRODUCTION_CANONICAL.md`
(new), `docs/REPRODUCTION_Q1.md`, `README.md` (repo root), `docs/AUDIT.md`.
Task 3 report corrections:
`reports/candidate_pool_conditional_audit_20260714/{ANALYSIS.md,FINAL_REPORT.md}`.
No files under `src/`, `scripts/`, or any driver script were modified --
this task found the underlying code and generated data to already be
accurate, so no regeneration was required.

## 9. Commands run

```bash
git fetch origin  # verify no new upload since last check (none)
python3 -m pytest -q
python3 scripts/check_repo_ready.py
cd papers/JDIQ_2026/manuscript && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
# (run repeatedly, once per manuscript edit, ~10 times total this task)
grep-based citation/label/reference cross-checks (see item 10)
python3 one-off scripts re-verifying every manuscript table's numbers
  against reports/*/tables/*.csv directly (see item 5)
```

Three background research agents were used for the highest-breadth
discovery work (claim-to-evidence extraction across the full manuscript,
cross-document terminology consistency, and a targeted outdated-wording
sweep of `main.tex`); their findings were independently spot-checked
against source CSVs before any manuscript edit was made on their basis.

## 10. LaTeX / structural audit results

0 duplicate labels, 0 unresolved `\ref`/`\eqref` targets, 0 undefined
references or multiply-defined labels in any build, all 29 `\cite` keys
used in `main.tex` exactly match the 29 keys defined in `references.bib`
(no missing, no unused), all 10 figures have both a caption and an
accessibility `\Description`. 13 equation labels exist that are never
cross-referenced via `\eqref`/`\ref` elsewhere in the text -- not a LaTeX
error, and common in papers that label every equation for precision even
when prose doesn't need to point back to all of them; left as-is.
Remaining overfull `\hbox` warnings: about a dozen, all but one under
10pt (cosmetic, typical for a `texttt`/inline-math-heavy manuscript), one
at ~18-21pt in the "Structural Sensitivity Across Threshold Protocols"
paragraph (pre-existing from Task 2). Not fixed in this pass -- the task's
own instruction treats overfull-box cleanup as "if practical," and the
risk of a miscue from aggressive paragraph rewording this late in the
process was judged higher than the cosmetic benefit; flagged here
explicitly rather than silently left.

## 11. Tests passed

`pytest -q`: 550 passed (unchanged from before this task -- no code was
modified, since the claim-to-evidence audit found nothing requiring
regeneration). `check_repo_ready.py`: 56 OK, 5 pre-existing warnings
(missing optional docs, `ir-datasets` not installed), 0 failures. LaTeX
build: 0 undefined references, 0 multiply-defined labels, clean compile,
verified after every substantive edit (~10 rebuilds total).

## 12. Remaining limitations

- The manuscript's own Limitations section (reviewed and lightly
  consolidated in this task) is judged honest and complete for the
  pipeline's actual scope; no new scientific limitation was discovered
  during this audit that the manuscript did not already disclose.
- A dozen minor overfull-hbox warnings remain (item 10), cosmetic only.
- The ~9-12 flagged pre-writing planning docs under `papers/JDIQ_2026/`
  were marked superseded, not rewritten to match the current manuscript;
  if any of them (particularly `SUPPLEMENTARY_MATERIAL.md`) is intended to
  be used as an actual submission artifact, it needs to be rebuilt from
  `main.tex`, not merely flagged.
- `papers/JDIQ_2026/manuscript/README.md` still lists many per-section
  evidence-map files (`INTRODUCTION_EVIDENCE_MAP.md`,
  `FULL_DRAFT_EVIDENCE_MAP.md`, etc.) that were not individually re-audited
  in this pass beyond the top-level status-line fix; the independent
  claim-to-evidence audit performed directly against `main.tex` (item 1)
  is the authoritative check for this task, but those older per-section
  maps were not reconciled against it line by line.
- **Is the manuscript now internally consistent enough for submission?**
  Yes, on every axis actually checked in this task: every quantitative
  claim traces to a generated artifact (one numerical error found and
  fixed), every table's numbers match their source CSVs, the bibliography
  and cross-reference graph are fully resolved, terminology is consistent
  throughout `main.tex` itself, and the positioning/contributions/
  limitations framing is coherent and not overclaiming. The one caveat is
  scope: this task audited `main.tex` and its direct reproducibility
  trail exhaustively, but did not attempt a full line-by-line rewrite of
  every historical planning document in the wider `papers/JDIQ_2026/`
  tree -- those are now clearly marked rather than fully reconciled.
