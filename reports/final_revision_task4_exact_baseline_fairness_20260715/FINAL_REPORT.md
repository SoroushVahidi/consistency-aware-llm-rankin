# Final Report: Task 4, Exact-Repair Fairness and Baseline-Comparison Audit

## 1. Initial repository state

- Repository: `/home/soroush/consistency-aware-llm-rankin`
- `git fetch origin` completed before edits; `origin/main` matched local `HEAD`.
- Branch: `main`
- Starting commit: `b0d48520b72dfa05f6cfe07309cb39ef980be032` (unchanged throughout the task; no commits made)
- Manuscript PDF checksum at Task 4 start:
  `sha256 = 39b01ed32afb54023b965b5b52619b37457cc8244d90a24e2de5b803f6da4cc5`
  (identical to Task 3's final checksum, confirming Tasks 1-3 outputs were present and consistent).
- Verified present: `reports/final_revision_task1_pool_cutoff_20260715/`, `reports/final_revision_task2_statistical_power_20260715/`, `reports/final_revision_task3_ranker_dependence_20260715/` with their `FINAL_REPORT.md`, tables, manifests, and validation artifacts intact.
- Located and reused (via a dedicated Explore pass rather than re-deriving):
  - Exact MWFAS/SCIP pipeline: `src/consistency_ranker/mwfas_solver.py` (`solve`, `_solve_scip`, `SolveStatus`), `src/consistency_ranker/greedy_fas.py`, `src/consistency_ranker/exact_fas.py` (brute-force oracle, tests only).
  - Task 1's existing exact-vs-unrepaired study: `reports/final_revision_task1_pool_cutoff_20260715/scripts/run_pool_cutoff_exact.py` (covers only the larger-pool `(P,k{=}10)` cells, 5 method pairs).
  - Candidate-pool policies: `reports/full_calibrated_core/scripts/candidate_pool_policies.py` (5 policies).
  - Existing per-pool, per-query, per-method nDCG outputs: `reports/full_calibrated_core/outputs/calibrated_all4/pool_runs/{pool_id}/{dataset}/{regime}/query_method_metrics.csv` (60 files, already covering Prior/RRF/CombSUM/Borda and all graph-dependent methods across all 5 pools -- reused rather than recomputed).
  - Prior implementation: `_rrf_prior_scores_for_query`/`_prior_only_ranking` in `scripts/run_real_experiment.py`.
  - Standalone RRF: `src/consistency_ranker/rrf_ranking.py`.
  - CombSUM: `src/consistency_ranker/combsum_ranking.py`. Borda: `src/consistency_ranker/borda_fuse_ranking.py`.
  - Baseline-comparison table code and manuscript claims: `reports/full_calibrated_core/scripts/run_full_calibrated_core.py` (`PAIR_SPECS`, `PRIMARY_BASELINE_COMPARISON_METHODS`, `BASELINES`), `papers/JDIQ_2026/manuscript/main.tex` sections `sec:baselines` and "Comparison with Fixed Aggregation Baselines".
  - Graph-dependent baselines: PageRank/RankCentrality in `src/consistency_ranker/baseline_ranking.py`; Bradley-Terry in `src/rerankers/tournament_agg.py`; Markov hybrid in `src/consistency_ranker/markov_graph_ranking.py`.
- Full initial audit manifest: `manifests/initial_audit.json`.

## 2. Exact-repaired vs unrepaired direct results

New work (previously only exact-vs-greedy existed at the canonical pool; only Task 1's 4 larger-pool `(P,k{=}10)` cells had an exact-vs-unrepaired comparison).

Script: `scripts/run_exact_repaired_vs_unrepaired.py`. Tables: `tables/exact_repaired_vs_unrepaired_pair_metrics.csv`, `tables/exact_repaired_vs_unrepaired_solver_status.csv`, `tables/exact_canonical_family_statistics.csv`, `tables/exact_larger_pool_family_statistics.csv`.

- **Canonical pool (P=k), all 4 datasets, `ms1`, all 9 graph-dependent method pairs (the 5 original pairs plus PageRank, RankCentrality, Markov hybrid, Bradley-Terry) = 36 pre-specified cells.** Every solve reached proven optimality (mean solve time `18.14 ms`, max `61.25 ms`). **0 of 36 Holm-significant** (BCa intervals, exact/Monte-Carlo sign-flip p-values, Holm correction; Task 2's statistical framework).
- **Larger-pool family**: reused Task 1's existing `(P,k{=}10)` exact cells unchanged, and added a new `(P,k{=}5)` cell for all 4 datasets (cheap: the SCIP-repaired graph does not depend on the metric cutoff, only the nDCG readout does, so no new solve was needed beyond the pool-size-dependent repair already computed). Combined **56-cell larger-pool family: 0 Holm-significant**.
- Two families are kept strictly separate (never jointly corrected), per the task's instruction not to merge with each other or with Task 1/2/3 families.

## 3. Exact/greedy/unrepaired three-way results

Script: `scripts/run_three_way_comparison.py`. Table: `tables/three_way_unrepaired_greedy_exact.csv` (36 dataset x pair cells at the canonical pool, reusing the existing canonical-pool greedy/unrepaired per-query data already in `query_method_metrics.csv` and this task's new exact data).

Direct answers (`manifests/three_way_comparison_run_summary.json`):

1. **Does exact repair ever produce a statistically reliable retrieval gain where greedy does not?** No: 0/36 canonical and 0/56 larger-pool exact cells are Holm-significant, and greedy shows 0 Holm-significant cells in the same families (Tasks 1-2).
2. **Does exact repair ever reverse the sign of greedy's repaired-vs-unrepaired effect?** No: 0 of 36 dataset/pair cells show a sign reversal (mean-nDCG-delta sign for greedy vs. exact).
3. **Does exact repair improve the graph objective materially without improving retrieval?** Yes, by construction and directly observed: every exact solve reaches the proven-optimal minimum-weight feedback arc set while showing no Holm-significant retrieval gain.
4. **Does exact repair change the Task 1 larger-pool conclusion?** No: the extended 56-cell larger-pool family (original `k=10` cells plus new `k=5` cells) remains 0 Holm-significant.

## 4. Solver optimality/runtime summary

- 684 total exact solves across canonical (342) and larger-pool-new (342) configs: **100% proven optimal**, MIP gap 0.
- Canonical pool: mean solve time `18.1 ms`, max `61.3 ms`.
- Larger pool: mean solve time `284 ms`, max `459 ms` (consistent with Task 1's previously reported `93`-`328 ms` range for the `k=10` cells).
- Verified via `tests/test_task4_exact_baseline_fairness.py`: `solve()` raises `RuntimeError` rather than silently returning a non-optimal exact result (forced with an artificially tiny `time_limit_s` on a 14-node dense random graph).

## 5. Baseline fairness across candidate pools

Script: `scripts/run_baseline_pool_fairness.py`, reusing the existing 60 per-pool `query_method_metrics.csv` files rather than recomputing. Table: `tables/baseline_pool_fairness_descriptive.csv` (mean nDCG per pool x dataset for Prior/RRF/CombSUM/Borda and the 5 methods in `run_full_calibrated_core.PRIMARY_BASELINE_COMPARISON_METHODS`, a pre-existing fixed method family used rather than a post-hoc per-pool "best" pick).

**Reviewer concern tested directly: does the RRF-centered canonical pool give a home-field advantage to RRF-family baselines?** No. Pre-specified primary family (`tables/baseline_targeted_tests_primary_canonical.csv`): `{RRF, CombSUM}` vs. the fixed repaired Copeland hybrid, 4 datasets, canonical pool only = 8 cells, Holm-corrected jointly: **0/8 significant**. Descriptive full five-pool sweep (`tables/baseline_targeted_tests_all_pools.csv`): the **only** nominally significant cell across all 5 pools x 4 datasets x 2 baselines = 40 descriptive cells occurs under the **neutral round-robin pool** (not canonical), FiQA, CombSUM beating the repaired Copeland hybrid by mean nDCG `+0.014` (Holm `p=0.013` within its own secondary 8-cell family). This is the opposite of a home-field-advantage pattern.

## 6. Targeted baseline significance tests

- Primary pre-specified family (canonical pool, `{RRF, CombSUM}` vs. fixed repaired Copeland hybrid, 4 datasets = 8 cells): **0/8 Holm-significant**. Effect sizes are small (standardized effect size magnitudes mostly `<0.3`; see `tables/baseline_targeted_tests_primary_canonical.csv`).
- Secondary (neutral pool, robustness context only, not jointly corrected with the primary family): **1/8 nominally significant** (FiQA CombSUM, described above).
- The manuscript's "simple baselines remain strong" claim is kept **descriptive** (dataset-macro mean nDCG ranking), consistent with the evidence: no family supports an inferential superiority claim for CombSUM/RRF over graph methods in general, and the one significant cell found is itself evidence against a pool-driven inflation story, not for one.

## 7. Prior vs RRF root-cause analysis

Script: `scripts/run_prior_vs_rrf_audit.py`. Tables: `tables/prior_vs_rrf_per_query.csv`, `tables/prior_vs_rrf_summary.csv`. Worked example: `outputs/prior_vs_rrf_worked_examples.json`.

Audited line-by-line (not assumed): tokenization/candidate-set identity, raw fused-score identity, tie-group structure, rank-universe construction, and tie-break rules for both `_rrf_prior_scores_for_query` (Prior) and `rrf_scores_and_best_ranks`/`per_query_rrf_ranking_from_score_maps` (standalone RRF).

Findings (canonical pool, `ms1`, 342 queries, matching the manuscript's existing full-study 216/6,156 = 3.5% exact-match rate almost exactly at 12/342 = 3.5%):

- **Candidate sets are always identical** (both methods restricted to the same `candidate_pool` argument at output time) -- verified, not assumed.
- **Native-score ties are rare**: mean RRF tie groups per query range `0.019`-`1.14` across datasets.
- **The dominant cause of Prior/RRF divergence is NOT tie-breaking.** Decomposing every mismatch into "tie-break-only" (fused scores induce the same order modulo ties) vs. "genuine score-order difference" (scores disagree on the relative order of at least one non-tied pair) shows: tie-break-only explains only **0-3.8%** of queries, while genuine score-order differences occur in **79-100%** of queries (by dataset; HotpotQA is the low end at 78.8%, SciDocs/FiQA are 100%, BRIGHT is 94%).
- **Root cause, confirmed via a concrete worked example** (`outputs/prior_vs_rrf_worked_examples.json`, SciDocs query `78495383...`): Prior computes each ranker's reciprocal rank **among candidate-pool documents only** (rank 1..\|candidates scored by that ranker\|); the standalone RRF baseline computes it over that ranker's **entire stored list** and only restricts the final ranking to candidates afterward. In the worked example this flips which document is ranked #1 between the two methods (`2a43d3905699...` is Prior's top document but RRF's third), with no tie involved at all.
- Kendall's tau-b between the two full rankings remains high (`0.87`-`0.91`) -- the methods broadly agree on overall ordering, but rarely produce bit-identical rankings, consistent with a systematic per-document rank-position shift rather than random noise or a bug.
- **The manuscript's prior statement ("that tie-breaking difference alone yields identical full rankings in only 216 of 6,156 cases") was misleading** in attributing the mismatch rate to tie-breaking; it has been corrected throughout `main.tex` (Sections `sec:score-calibration`, `sec:baselines`, "Comparison with Fixed Aggregation Baselines", Discussion, Limitations) to state the actual, measured root cause.

## 8. Final decision on keeping/unifying/renaming Prior and RRF

**Decision: keep both, correct the causal explanation (Option A from the task, corrected), do not unify or rename the code-level `method_key`s.** Rationale: Prior and RRF represent two legitimately different, purposeful constructions -- Prior is the graph-hybrid's hierarchy-local fusion signal used elsewhere in the pipeline (`_rrf_prior_scores_for_query` also feeds `_hybrid_ranking` and repair prioritization), scoped deliberately to the candidate pool; the standalone RRF baseline represents a corpus-consistent, textbook full-list RRF ranking used as an independent graph-free comparator. Merging them would conflate two different research questions ("what does RRF fusion look like restricted to this candidate pool" vs. "what would a standard full-corpus RRF system return here"). Renaming the code identifiers (`prior_only`/`rrf`) was considered (`Option C`) but not done, since it would require regenerating every table/figure that references those `method_key` strings for a purely cosmetic gain; instead, the manuscript's exposition was tightened (Section `sec:score-calibration`, `sec:baselines`) to describe the distinction precisely and mechanistically rather than by an inaccurate "tie-breaking" shorthand.

## 9. Graph-dependent baseline implementation audit

Reproducibility-level specifications (verified by direct code reading and, for PageRank, a targeted empirical check that surfaced a documentation/behavior mismatch):

- **PageRank** (`baseline_ranking.py:292-345`): computed via `nx.pagerank` on the **reversed** preference graph, `alpha=0.85`, `max_iter=100`, `tol=1e-6`, edge-weighted. Dangling nodes use NetworkX's default handling (no explicit `dangling=` argument). **Finding**: the function's docstring claims reversal makes "being beaten by a strong competitor increase your authority" (implying the loser of an edge should rank higher), but empirically (and per a new regression test) the **winner** of a single preference edge receives the higher PageRank score, since `graph.reverse()` sends PageRank mass from loser to winner. This is a genuine docstring/behavior mismatch, documented here and pinned by `test_pagerank_winner_outranks_loser_on_a_single_edge`, but not "fixed" in this task since changing it would alter every committed PageRank-based result. **Also**: PageRank's final sort has no explicit doc-id tie-break (unlike Copeland/RankCentrality/Markov), so tied scores fall back to `nx.pagerank`'s dict iteration order -- deterministic for a fixed graph, but not principled the way other methods' tie-breaks are; pinned by `test_pagerank_has_no_explicit_tie_break_and_relies_on_dict_order`.
- **RankCentrality** (`baseline_ranking.py:429-498`): no damping/teleportation term; ergodicity via explicit self-loops (`self_loop = 1 - row_mass[i]/d_max`). All-zero-weight graphs return a uniform distribution (verified by test). Disconnected comparison components each converge internally without cross-component teleportation-driven equalization (verified by test on two disjoint 2-node comparisons). Doc-id tie-break present. Convergence: `max_iter=200`, `tol=1e-8`.
- **Bradley-Terry** (`tournament_agg.py:108-186`): MM/iterative-scaling MLE; nodes with zero observed comparisons get score exactly `0.0` and sort to the bottom (verified by test); disconnected comparison groups each converge to internally consistent relative strengths, with total probability mass normalized to `1.0` (verified by test). Doc-id tie-break present. Convergence: `max_iter=100`, `tol=1e-6`.
- **Markov hybrid** (`markov_graph_ranking.py`): explicit teleportation `alpha=0.15` (module-level `DEFAULT_MARKOV_DAMPING`, distinct from the hybrid hybrid-fusion `alpha=0.3` -- same Greek letter, two unrelated roles, worth noting for readers). Guarantees a unique stationary distribution regardless of cyclicity/disconnection by construction. Three-level tie-break (score, weighted in-degree, doc_id) -- the only method with this level of tie-break granularity.

## 10. Manuscript changes

File: `papers/JDIQ_2026/manuscript/main.tex`. Changes:

- Abstract: added sentences reporting the direct exact-vs-unrepaired canonical result and the pool-fairness finding.
- Contributions list: added one bullet for the exact-vs-unrepaired evaluation and baseline-fairness audit.
- `sec:score-calibration`: corrected the Prior-vs-RRF description to name the rank-universe difference as the primary mechanism, not tie-breaking.
- `sec:baselines`: rewrote the PageRank/RankCentrality/Bradley-Terry justification to use principled methodological-family criteria (random-walk with/without damping, probabilistic pairwise) instead of "implemented elsewhere in the codebase"/"none exists in the codebase" framing; rewrote the Prior-vs-RRF paragraph with the measured root cause and corrected percentages.
- New paragraph + `\label{sec:exact}` in the larger-pool prefix-evaluation discussion: reports the new canonical-pool exact-vs-unrepaired results (36 cells, 0 significant) and the extended 56-cell larger-pool family.
- "Comparison with Fixed Aggregation Baselines": added a new paragraph and a **compact new table** (`tab:pool-fairness`, canonical + neutral-pool columns for the 8-cell targeted family) addressing the home-field-advantage concern directly, plus a cross-reference to the exact-repair confirmation.
- Discussion: added one clause noting the home-field-advantage concern was tested directly.
- Limitations (`sec:threats`): extended the existing RRF-centered-pool limitation paragraph with the new baseline-pool-fairness finding and the corrected Prior/RRF root-cause description.
- No figures were regenerated; Figure 10 (`fig10_baseline_comparison.pdf`) remains factually accurate (it already shows Prior/RRF as separate points) and was not marked stale.
- Rebuilt PDF: `papers/JDIQ_2026/manuscript/main.pdf`, final SHA-256
  `b001504a110f76880fb3159afa3ca8566b147aacc9464c6304a216c01ef5ef31`
  (46 pages; this differs from an earlier intermediate rebuild's checksum
  only in the PDF's embedded `CreationDate` metadata timestamp from the
  validation bundle's final `latexmk` invocation, not in content).

**One correction made during validation**: an initial draft of the new text stated the underlying-score-divergence range as "94-100%"; the claim-to-evidence audit caught that the true minimum (HotpotQA) is 78.8%, not 94%, before the manuscript was finalized. Fixed to "79-100%" throughout (two locations) and the PDF was rebuilt.

## 11. Code and tests changed

New task-local scripts (`reports/final_revision_task4_exact_baseline_fairness_20260715/scripts/`):

- `task4_common.py` -- shared setup, reuses `full_calibration_utils`/`run_full_calibrated_core`, adds Task 2's richer statistics (BCa, sign-flip, MDE) as `rich_cell_statistics`.
- `run_exact_repaired_vs_unrepaired.py` -- sections 2/3 (canonical-pool exact study + larger-pool extension, reusing Task 1's existing `k=10` cells).
- `run_three_way_comparison.py` -- section 3 (unrepaired/greedy/exact three-way table and direct answers).
- `run_baseline_pool_fairness.py` -- sections 4/5 (baseline pool fairness, targeted significance tests).
- `run_prior_vs_rrf_audit.py` -- section 6/7 (Prior vs RRF root-cause audit).
- `claim_to_evidence_audit.py` -- verifies every manuscript numeric claim against its source table (caught and enabled the 94%->79% correction above).

No existing repository source files (`src/`, `scripts/`) were modified by Task 4; only new task-local scripts, `tests/test_task4_exact_baseline_fairness.py`, and the manuscript were added/changed.

Tests: `tests/test_task4_exact_baseline_fairness.py` (20 tests) covering: exact-repaired-vs-unrepaired pipeline construction, forcing a non-optimal SCIP status and confirming `solve()` raises rather than returning a partial result, Prior/RRF score identity when pool equals the full stored list, Prior/RRF divergence when a non-candidate document outranks candidates (isolating the rank-universe cause), Prior's doc-id-only tie-break vs. RRF's best-rank-then-doc-id tie-break, Prior's graph-fallback vs. RRF's zero-fallback for documents unscored by every ranker, deterministic Prior ranking across repeated calls, the baseline-pool-fairness paired-delta helper, PageRank's winner-ranks-higher behavior and lack of an explicit tie-break, RankCentrality on disconnected components and all-zero-weight graphs, and Bradley-Terry on isolated nodes and disconnected comparison groups.

## 12. tmux sessions and logs

- `jdiq_task4_exact_unrepaired`: first launch crashed on a CSV schema mismatch (missing `reused_from` key across merged row sources); fixed and relaunched under the same session name.
  - Final successful launch: manifest `manifests/20260715_120632_exact_unrepaired_launch.json`, log `logs/20260715_120632_exact_unrepaired.log`, completed successfully (180.5 s; 36 canonical-pool cells + 56 larger-pool cells, 0/0 Holm-significant).
- `jdiq_task4_validate`: manifest `manifests/20260715_122225_validation_launch.json`, log `logs/20260715_122225_validation.log`; ran the full validation bundle (see Section 13).
- The baseline-pool-fairness, three-way-comparison, and Prior-vs-RRF-audit scripts all completed in under 6 seconds each (they reuse existing per-pool CSVs or operate on small canonical-pool graphs) and were run directly rather than in tmux, per the policy's ">~10 min or uncertain duration" threshold.
- No tmux session from this task remains running.

## 13. Validation results

- Task-specific tests: `pytest tests/test_task4_exact_baseline_fairness.py -q` -- **20 passed**.
- Full test suite: `pytest -q` -- **617 passed** (597 pre-existing + 20 new).
- Linting: `ruff check` on all new Task 4 scripts and the test file -- **all checks passed** (fixed several `ruff --fix`-induced import-order breaks using the same `# ruff: noqa: I001` + explanatory-comment pattern established in Task 3, since `task4_common` must import before `full_calibration_utils` for its `sys.path` bootstrap to take effect).
- `py_compile` on all new files: **OK**.
- `scripts/check_repo_ready.py`: passed with the same pre-existing non-critical warnings as Tasks 1-3.
- Claim-to-evidence audit (`claim_to_evidence_audit.py`): **53/53 checks verified** against source CSV/JSON tables after fixing the 94%->79% transcription error described in Section 10.
- LaTeX build: `latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex` -- **passed**, only pre-existing cosmetic font/box warnings, no errors, no undefined references.
- All exact-solver outputs verified: 684/684 solves proven optimal, MIP gap 0.
- Per-query-to-aggregate consistency: the three-way comparison script and both statistics tables were regenerated from final code state and cross-checked against the claim-to-evidence audit.

## 14. Remaining limitations

- The canonical-pool exact study and the larger-pool `k=5` extension use the same fixed vote-threshold/normalization protocol as the manuscript's primary pipeline; they do not re-derive thresholds independently the way Task 3's pre/post-normalization study did.
- The baseline-pool-fairness targeted tests reuse the existing per-pool `query_method_metrics.csv` outputs, which were generated under each pool policy's own candidate-pool membership but the dataset's canonical `top_k` cutoff (not a `P>k` design); a full pool-x-`(P,k)` cross product was judged out of scope for this task.
- The PageRank docstring/behavior mismatch and the missing doc-id tie-break are documented and pinned by tests, but not corrected in the production code, since doing so would silently change every committed PageRank-based table and figure -- flagged for a future task if a correction is wanted.
- The Prior-vs-RRF root-cause analysis is restricted to the canonical pool under `ms1`; the exact 216/6,156 figure spans additional regimes and protocols not re-audited here, though the canonical-pool subset matches it almost exactly (3.51% vs. 3.51%), supporting that the same mechanism operates throughout.
- The secondary neutral-pool significant cell (FiQA, CombSUM) is reported for robustness context only and is not jointly corrected with the primary family, per the task's "small pre-specified family" instruction; a reviewer could still ask for a single larger cross-pool family in a future revision.

## 15. Exact reproduction commands

```bash
cd /home/soroush/consistency-aware-llm-rankin

# Exact-repaired vs unrepaired (canonical + larger-pool extension), sections 2/3
./.venv/bin/python reports/final_revision_task4_exact_baseline_fairness_20260715/scripts/run_exact_repaired_vs_unrepaired.py

# Three-way unrepaired/greedy/exact comparison, section 3
./.venv/bin/python reports/final_revision_task4_exact_baseline_fairness_20260715/scripts/run_three_way_comparison.py

# Baseline pool fairness + targeted significance tests, sections 4/5
./.venv/bin/python reports/final_revision_task4_exact_baseline_fairness_20260715/scripts/run_baseline_pool_fairness.py

# Prior vs RRF root-cause audit, sections 6/7
./.venv/bin/python reports/final_revision_task4_exact_baseline_fairness_20260715/scripts/run_prior_vs_rrf_audit.py

# Claim-to-evidence audit
./.venv/bin/python reports/final_revision_task4_exact_baseline_fairness_20260715/scripts/claim_to_evidence_audit.py

# Full validation bundle
bash reports/final_revision_task4_exact_baseline_fairness_20260715/run_manifests/run_task4_validation.sh
```

## 16. Proposed commit message

`Task 4: direct exact-repaired-vs-unrepaired evaluation, reject RRF-pool home-field-advantage hypothesis, correct Prior/RRF root cause`
