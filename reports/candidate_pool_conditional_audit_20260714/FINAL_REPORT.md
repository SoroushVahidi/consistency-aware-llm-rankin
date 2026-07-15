# Task 3 Final Report: Candidate-Pool Dependence, Conditional Analysis, and Stronger Baselines

## 1. Candidate-pool audit

Canonical pool construction: `run_phase0_phase1._select_candidates(ranker_scores, top_k)`
— union of BM25/TF-IDF/MiniLM scored docs; if the union exceeds `top_k`,
RRF-fuse ($k{=}60$) over each ranker's *full native* ranked list and keep
the top `top_k` of that fusion. `top_k` = 20 (SciDocs/FiQA/BRIGHT), 10
(HotpotQA), from the canonical manifest. Fully deterministic (every tie
broken by ascending `doc_id`); no qrels involved. The pool is computed once
per query and shared by object identity across all 22 compared methods
(verified empirically, 0 fairness violations across 1,026 queries — see
item 6). A byte-for-byte duplicate of `_select_candidates` exists in
`scripts/build_votes_file.py` (used only to pre-build vote files for other
diagnostic phases, not read by the canonical pipeline's own pool
computation); marked with a comment, not touched, since other committed
outputs depend on its current behavior. Full detail:
`reports/candidate_pool_conditional_audit_20260714/AUDIT.md` section 1.

**Key finding, already partly known and now precisely re-confirmed**: RRF
plays two different, non-identical roles in this pipeline — candidate
*selection* (ranks over each ranker's full native list) and the compared
RRF *baseline method* (same formula, but restricted to the already-fixed
pool). This was previously investigated in an uncommitted prior pass
(`reports/rrf_pool_investigation/`); this task's work supersedes it with
per-query records, manifests, and the canonical engine rather than a
duplicate implementation.

## 2. New pool definitions

Four independently-defined alternatives, all in the new
`reports/full_calibrated_core/scripts/candidate_pool_policies.py` (typed
`PoolSpec` registry, same pattern as Task 2's `ProtocolSpec`):
- **Equal-depth union**: union of each ranker's own top-$k$ documents.
- **Neutral round-robin union**: alternates bm25/tfidf/minilm in fixed
  order, one rank position at a time, until reaching exactly $k$ documents;
  never computes a fused score.
- **BM25-only**: top-$k$ BM25 documents, ignoring TF-IDF/MiniLM for pool
  membership.
- **CombSUM-fused union**: top-$k$ of the existing, tested
  `consistency_ranker.combsum_ranking.combsum_ranking` over the full union.

All four share `_select_candidates`'s exact signature
(`(ranker_scores, top_k) -> list[str]`), are deterministic, take no qrels,
and preserve the query set. `prepare_dataset_inputs`/`_analysis_dataset_inputs`
gained an optional `pool_policy` parameter (default `None` = canonical,
byte-identical to before — verified by MD5).

## 3. Robustness results

72-cell sweep (5 pools × 4 datasets × 3 regimes), 0 exclusions, ~110s.
Pool overlap with canonical (`ms1`, Jaccard): 0.44–0.64. Removed-edge
overlap: 0.40–0.61. Repaired-ranking agreement among documents eligible
under both pools: **0.955–0.962**, essentially constant across all four
alternative pools — the headline finding: pool choice changes *which*
documents compete, only weakly changes *how already-common competitors are
ordered*. Jointly Holm/BH-corrected across the four alternative pools
(240 tests): **zero** significant repaired-vs-unrepaired cells; including
the canonical pool (300 tests): still zero. Full detail and exact
per-cell numbers: `ANALYSIS.md` section 1;
tables: `pool_overlap_vs_canonical.csv`,
`pool_removed_edge_overlap_vs_canonical.csv`,
`pool_repaired_ranking_overlap_vs_canonical.csv`,
`pool_robustness_multiplicity_adjusted.csv`.

*Self-correction disclosed*: an intermediate draft of this section (and of
the corresponding manuscript paragraph) reported pool-overlap and
edge-overlap numbers that were transcribed from memory rather than read
back from the CSVs and were measurably wrong (e.g. "0.51" instead of the
correct 0.438 for equal-depth-union pool overlap). This was caught before
finalizing by recomputing directly from the CSVs, and both `ANALYSIS.md`
and `main.tex` were corrected to the verified values before this report was
written. No committed number in this final report or in `main.tex` is
unverified against its source CSV.

## 4. Conditional-analysis results

Primary protocol × canonical pool, 4 datasets × 3 regimes × 5 pairs × 6
subsets = 360 rows (`conditional_analysis_primary_protocol.csv`). Worked
example (HotpotQA `ms1` Copeland-hybrid, reproducing the manuscript's
already-published +0.0123 mean exactly): conditioning on activation raises
the point estimate (+0.0123 → +0.0193 has-cycle → +0.0290
ranking-changed), the top-$k$ document *set* never changes (0/52), and
nearly all the residual effect concentrates in the 3/52 queries where
qrels-labeled document ordering changes (+0.2126 mean there) — mechanistic
confirmation of, not new evidence beyond, the manuscript's already-existing
influence-removal finding that this cell collapses to zero once the top 3
influential queries are removed.

## 5. Active-query statistics

Failure decomposition (5 mutually-exclusive, exhaustive categories) by
protocol (4 canonical protocols × 4 datasets × 3 regimes × 5 pairs = 240
rows, `failure_decomposition_by_protocol.csv`) and by pool (5 pools × 4 ×
3 × 5 = 300 rows, `failure_decomposition_by_pool.csv`). "Cycle but repair
inactive" is exactly $0\%$ everywhere (repair always resolves detected
cycles, as required). Under `ms1`, most queries fall into "repair active
but ranking unaffected" or "ranking changed but metric stable" rather than
"metric changed," for every protocol and every pool — structural repair
activity exceeds retrieval-metric activity as a general pattern, not an
artifact of one setting.

## 6. Fairness verification

`baseline_fairness_verification.csv`: for all 12 dataset/regime cells
(1,026 queries = 342 usable queries x 3 regimes), every one of the 22
compared methods' output rankings —
legacy and newly-added alike — was confirmed a subset of that query's
single candidate pool. **0 violations.** Holds by construction
(`evaluate_query` fixes `candidate_nodes` once) and was checked empirically,
not only asserted.

*Self-correction disclosed (found during Task 4's claim-to-evidence audit)*:
this section, `ANALYSIS.md`, and `main.tex` originally stated "1,704
queries" for this count, which does not match `baseline_fairness_verification.csv`
(sums to 1,026) or the 342-usable-queries figure used consistently
elsewhere in the manuscript. Corrected to 1,026 in all three places; the
substantive finding (0 violations) was unaffected by the arithmetic error.

## 7. Baseline additions

Four new pairs wired into the canonical `evaluate_query()`, all reusing
pre-existing, already-tested ranking code (no new ranking algorithm
implemented): `pagerank_graph` (`baseline_ranking.pagerank_ranking`,
previously a dead import), `rank_centrality_graph`
(`baseline_ranking.rank_centrality_ranking`, previously dead), `markov_hybrid`
(mirrors the existing Copeland/balance hybrid pattern, using the Markov
component score the dispatcher already supported), `bradley_terry_graph`
(`src/rerankers/tournament_agg.bradley_terry_ranking`, previously
unreachable from this pipeline, graph edges converted to
`(winner, loser, weight)` preference tuples). HodgeRank/Elo/TrueSkill were
deliberately **not** implemented — none exists anywhere in the repo, and
building HodgeRank's Helmholtz decomposition from scratch was judged
excessive complexity relative to the task's "reasonable effort using
existing infrastructure" guidance. Statistics
(`new_baseline_statistics.csv`, 48 cells) jointly Holm/BH-corrected
(`new_baseline_multiplicity_adjusted.csv`): **zero** significant. Verified
regression-safe: the only change to already-committed per-query records is
the addition of these 8 new `method_metrics` entries; every pre-existing
field, for every pre-existing method, is byte-identical (checked by parsing
and diffing every field except the newly-added keys).

## 8. Manuscript changes

`main.tex`: (a) §4.7 and §3.1 updated to note the alternative pools and
forward-reference the new robustness section; (b) §4.8 baselines section
and `tab:baselines` extended with PageRank/RankCentrality/Markov-hybrid/
Bradley-Terry, with a paragraph explaining why HodgeRank/Elo/TrueSkill were
not added; (c) new §6.4 "Candidate-Pool Robustness"
(`sec:pool-robustness`) with `tab:pool-robustness` and the joint
multiplicity result; (d) new §6.5 "Conditional Analysis and Failure
Decomposition" (`sec:conditional-analysis`) with `tab:conditional-hotpotqa`
and the failure-decomposition summary; (e) Discussion paragraph
("Structural success does not guarantee retrieval gain") extended with a
cross-reference to the new failure decomposition; (f) Limitations bullet
"Candidate pooling ... is RRF-centered" rewritten to report that this is
now checked, not only disclaimed, with the actual overlap/agreement/
multiplicity numbers. `references.bib`: added `page1999pagerank`; fixed a
citation-key typo (`negahban2017rank` → the bib's actual
`negahban2017rankcentrality`). No manuscript figure file was regenerated,
edited, or redrawn in this task; only two figure-generation *scripts*
(`generate_figure1.py`, `generate_figures.py`) received a `SUPERSEDED`
comment (carried over from the separate figure-swap request handled earlier
in this session, not new to Task 3).

## 9. Figure replacements (Figures 1, 3, and 5)

Handled as a separate, explicit request earlier in this session, not as
part of Task 3's own scope (Task 3's instructions say "do not regenerate
figures other than replacing the manuscript references with the newly
uploaded Figure 1.png, Figure 3.png, and Figure 5.png," and that swap was
already completed and verified before Task 3 began): `main.tex`'s three
`\includegraphics` lines for Figures 1, 3, and 5 reference `figure1.png`,
`figure3.png`, `figure5.png` respectively (uploaded to
`papers/JDIQ_2026/manuscript/` via a GitHub web-UI commit, `git fetch` +
fast-forward merge, confirmed at the time against the actual repository
state rather than taken on claim). No further figure changes were made
during Task 3 itself.

## 10. Files changed

Modified: `papers/JDIQ_2026/manuscript/main.tex`, `main.pdf`,
`references.bib`; `reports/full_calibrated_core/scripts/full_calibration_utils.py`
(pool_policy param on `prepare_dataset_inputs`; Bradley-Terry import; 4 new
`add_method` calls); `reports/full_calibrated_core/scripts/run_full_calibrated_core.py`
(`_analysis_dataset_inputs` pool_policy param; `PoolSpec`/`POOL_SPECS`
import; 8 new `METHOD_LABELS` entries; 4 new `PAIR_SPECS` entries;
`LEGACY_PAIR_NAMES`/`NEW_BASELINE_PAIR_NAMES`); `scripts/build_votes_file.py`
(comment only, marking the duplicate `_select_candidates`).

Created: `reports/full_calibrated_core/scripts/candidate_pool_policies.py`,
`reports/full_calibrated_core/scripts/conditional_subsets.py`;
`reports/candidate_pool_conditional_audit_20260714/{AUDIT.md,ANALYSIS.md,FINAL_REPORT.md}`;
`reports/candidate_pool_conditional_audit_20260714/scripts/{run_pool_robustness.py,run_conditional_and_failure_analysis.py,run_baseline_comparison.py}`;
`reports/candidate_pool_conditional_audit_20260714/tables/*.csv` (16
files); `reports/full_calibrated_core/outputs/calibrated_all4/pool_runs/<5 pools>/<4 datasets>/<3 regimes>/{query_records.jsonl,manifest.json,query_method_metrics.csv}`
(60 cells); `tests/test_candidate_pool_policies.py` (21 tests),
`tests/test_conditional_subsets.py` (10 tests),
`tests/test_new_baseline_methods.py` (9 tests).

## 11. Commands executed

```bash
python3 reports/candidate_pool_conditional_audit_20260714/scripts/run_pool_robustness.py
python3 reports/candidate_pool_conditional_audit_20260714/scripts/run_conditional_and_failure_analysis.py
python3 reports/candidate_pool_conditional_audit_20260714/scripts/run_baseline_comparison.py
python3 -m pytest -q
python3 scripts/check_repo_ready.py
ruff check / ruff format --line-length 100  (newly authored files only)
cd papers/JDIQ_2026/manuscript && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
git fetch origin && git merge --ff-only origin/main   # figure upload, handled earlier in session
```

## 12. Test results

`pytest -q`: **550 passed** (510 pre-existing + 21 + 10 + 9 new). Includes
qrels-leakage guards, determinism checks, fairness checks, and a Bradley-
Terry-specific check that repaired-graph edge count never exceeds
unrepaired. `ruff check` on all newly authored files: 0 errors after
`ruff format` + a handful of manual line-length/import-order fixes; the
two extended pre-existing files retain their pre-existing lint debt,
unchanged by this task (same finding and same scoping decision as Task 2).
Repo readiness: 56 OK, 5 pre-existing warnings, 0 failures. LaTeX build:
0 undefined references, 0 multiply-defined labels, clean compile.
Regression safety: MD5-verified byte-identical for the primary protocol's
manuscript-critical cell before/after every code change in this task
(pool-policy wiring, then baseline wiring, then final reformatting).

## 13. Remaining limitations

- The four alternative pools are all still built from the same three
  upstream score files (BM25/TF-IDF/MiniLM); this task does not check
  robustness to different upstream rankers or different score files
  entirely.
- Conditional-subset sample sizes are frequently small in individual
  dataset/regime/pair cells; no subset-level significance test was
  computed (deliberately, per the task's framing — averages within a
  subset are descriptive, not a new positive claim), so a reader wanting a
  formally corrected subset-level test would need to run one.
- Failure decomposition's five categories are exhaustive given the
  classification rules in `conditional_subsets.py`, but "ranking changed"
  is defined as exact list inequality; a reader could reasonably want a
  distance-based (e.g. Kendall-tau-threshold) definition instead, which
  would shift mass between the "repair active but ranking unaffected" and
  "ranking changed but metric stable" categories without changing the
  overall "metric changed" fraction.
- HodgeRank remains unimplemented and unevaluated by design (see item 7);
  if a reviewer specifically requires it, that is new work, not a
  correction of this task.
- As in Task 2, the two large pre-existing canonical engine files retain
  their pre-existing lint debt; a full reformat was judged out of scope and
  risky for a manuscript-critical file.
