# Real-LLM Clustered Re-Analysis (Repo Stage 3)

**Purpose**: correct the inferential treatment of `repair_frontier_20260729T144742Z/`, `extraction_study_20260729T151610Z/`, and `repair_diagnostic_20260729T162748Z/` — all three report "n=120" observations that decompose to only 6 independent underlying real-LLM queries — and establish one authoritative, cluster-aware interpretation. **This is a re-analysis of data already stored in the repository.** No external API call was made, no new judgment was collected, no provider/query/repair-method/extractor was added, and no manuscript content was touched (`papers/JDIQ_2026/manuscript/main.tex` has zero diff from `HEAD`, confirmed both before and after this stage).

**Governing sources reviewed before any work began**: `reports/repo_preparation_stage1_20260730T011354Z/`, `reports/repo_structural_org_stage2_20260730T014347Z/`, `reports/ir_evidence_audit_review_20260729T235053Z/FINAL_META_AUDIT_REVIEW.md`, `reports/manuscript_reframing_20260729T174326Z/REFRAMING_ANALYSIS.md`, and the Stage 1 canonical evidence inventory / dependency map.

---

## 1. Analysis population (directly enumerated, not assumed)

| Study | Rows | Unique queries | Rows/query | Providers | Construction variants |
|---|---:|---:|---|---:|---:|
| `extraction_study` | 120 | 6 | 20 (uniform, no gaps) | 5 | 4 |
| `repair_diagnostic` | 120 | 6 | 20 (uniform, no gaps) | 5 | 4 |
| `repair_frontier` | 432 (candidate-level; 120 distinct unit_keys) | 6 | 55-95 (variable candidate count per unit, by design) | 5 | 4 |

All three studies share the **identical** 6 query IDs and the identical 120-unit_key construction grid (verified by `frozenset`-normalized comparison across all three studies' raw JSONL files — not assumed from prose). Zero missing/incomplete configurations found. Full detail in `analysis_population_manifest.csv` (672 rows spanning all three studies' different native granularities — this total is a bookkeeping artifact of combining three different row-shapes into one CSV, not a new sample-size claim).

**The independence cluster is `query_id`.** Provider (azure/gemini/cohere/fireworks/aggregate) and construction variant (pool6_original/pool8_complete/pool8_sparse57/pool10_sparse56) are repeated measurements within a query cluster, not additional independent samples — all operate on the same underlying documents and qrels for that query.

## 2. Canonical protocol

Full specification in `canonical_analysis_protocol.md`. Summary: query-level cluster (block) bootstrap (10,000 reps, seed=13, percentile CI) + exact permutation-based paired tests (2⁶=64 sign patterns for mean deltas, 6!=720 relabelings for correlations) + query-level aggregation as the basis for both + complete per-query descriptive tables reported unconditionally. Holm correction applied within two pre-declared families (8 extractors; 23 diagnostic features). No equivalence claims are made anywhere (no margin was defined).

## 3. Repair-frontier re-analysis

Per-unit nDCG reconstructed from stored `global_ranking` data (the original run persisted only aggregate statistics, not per-unit values) using the exact same `ndcg_at_k` function and relevance maps the original pipeline used. **Reconstruction verified byte-exact against the published aggregates** (max abs diff 1.1×10⁻¹⁶ — see `frontier_reconstruction_verification.json`), so the per-unit values below are trustworthy, not a new computation.

| Comparison | Point estimate | Original CI (row-level, n=120) | Cluster CI (n=6) | Exact sign-flip p |
|---|---:|---|---|---:|
| Oracle full-frontier headroom (**upper-bound diagnostic, not deployable**) | 0.00537 | [0.00291, 0.00841] | [0.00124, 0.01270] | not informative (non-negative by construction — see caveat below) |
| Whole-graph repair alone | 0.00019 | not previously isolated | [-0.00072, +0.00140] | 0.875 |
| Best alt-extraction candidate | 0.00483 | not previously isolated | [0.00046, 0.01190] | 0.0625 |

**Caveat on the oracle sign-flip test**: the full-frontier oracle always includes the incumbent as a candidate, so its delta is non-negative by construction — all 6 cluster signs are trivially non-negative, making the sign-flip p-value uninformative for this specific comparison. The magnitude (CI) is the meaningful output here, and it is now materially wider than originally reported, with its upper bound (0.0127) exceeding the 0.01 practical-significance threshold that the original CI sat entirely below.

## 4. Extraction-study re-analysis (8-extractor family, Holm-corrected)

| Extractor | Mean | Cluster CI | Sign-flip raw p | Sign-flip Holm p | Direction consistent? |
|---|---:|---|---:|---:|---|
| borda | -0.00795 | [-0.01731, -0.00017] | 0.156 | 0.938 | No (2 win / 4 loss) |
| hodge_rank | +0.00407 | [0.00065, 0.00964] | 0.063 | 0.500 | Yes (5/6) |
| rank_centrality | +0.00221 | [-0.00119, 0.00828] | 0.938 | 1.0 | No |
| fas_balance_prior_fusion | +0.00075 | [0.00020, 0.00145] | 0.125 | 0.875 | Mostly (4/0/2 ties) |
| hybrid_rrf_prior_fusion | +0.00051 | [-0.00014, 0.00094] | 0.188 | 0.938 | Yes (5/6) |
| balance_score | +0.00024 | [-0.00018, 0.00093] | 1.0 | 1.0 | No |
| pagerank | -0.00076 | [-0.00301, 0.00096] | 0.656 | 1.0 | No |
| copeland | 0.0 | [0.0, 0.0] | 1.0 | 1.0 | trivial (identical to incumbent) |

**0 of 8 extractors are Holm-significant.** The original "Borda is significantly worse than the incumbent" claim (row-level CI [-0.01392, -0.00329]) **does not survive**: the exact cluster-level test gives p=0.156 uncorrected, p=0.938 after Holm correction, and the direction is not even consistent across the 6 queries (2 show Borda better, 4 show it worse). HodgeRank remains the most directionally-consistent candidate (5/6 queries) but does not reach significance even before correction.

## 5. Repair-diagnostic re-analysis (23-feature family, Holm-corrected)

Overall effect: mean delta -0.00093, cluster CI **[-0.00143, -0.00052]** (entirely negative), exact sign-flip p=**0.031** — **all 6 independent queries show a negative mean delta**, the strongest direction-consistency of any result in this package. This finding is unchanged and, if anything, more robust than the original row-level presentation suggested.

Feature associations: **0 of 23 features are Holm-significant.** The original study's single flagged association (`is_cyclic`/`topk_involvement`, row-level Holm p=0.023) **does not survive**: query-level r=-0.34, exact permutation p=0.55, Holm p=1.0 across the family.

Grouped cross-validation: confirmed (not re-implemented) that `src/consistency_ranker/repair_diagnostic/prediction.py` already used `sklearn.model_selection.GroupKFold` grouped by `(dataset, query_id)` from the start. No leakage found. The original "UNSUPPORTED" predictor verdict (1 positive example across 6 groups) is a genuine data limitation, not a methodology bug, and is unchanged.

## 6. Cross-study alignment (verified via source code, not assumed)

All three studies call the identical `frontier_lib.load_all_units()` for their relevance maps (same qrels, zero drift risk) and the identical `consistency_ranker.evaluation.ndcg_at_k` function at `k=10` for every metric computed (verified by reading `src/consistency_ranker/extraction_study/evaluation.py` and `src/consistency_ranker/repair_diagnostic/outcomes.py` directly). Sign convention is consistent (positive = alternative/treatment better than incumbent/preserve baseline) across all three. No comparison in this package is improperly paired.

## 7. Conclusion-change matrix

Full 9-row matrix in `conclusion_change_matrix.csv`. Distribution across the required classification categories:

- **Unchanged** (2): whole-graph repair alone (no effect); overall repair-is-harmful direction (if anything, reinforced).
- **Unchanged, methodologically strengthened** (2): grouped-CV status (no bug existed); extraction family-wide "no meaningful gain" conclusion (now properly Holm-corrected, was previously just 8 uncorrected CIs).
- **Numerically unchanged but uncertainty wider** (1): repair-frontier oracle headroom.
- **Weakened** (2): HodgeRank's "best extractor" framing; the general "n=120" population framing.
- **No longer supported** (2): Borda "significantly worse"; `is_cyclic`/`topk_involvement` feature association.

No conclusion reversed sign; none were found "not testable with six queries" (six clusters was always sufficient for the exact tests used, just not for high power).

## 8. Canonical artifacts and status markers

New canonical directory: this one (`reports/real_llm_clustered_reanalysis_20260730T023745Z/`), containing every deliverable listed in the task brief. The three original study directories were **not modified** except for one additive `STATUS.md` file each (verified via `find -newer`), pointing here and stating plainly: raw observations remain valid; row-level inferential statistics are superseded; cluster-aware results here are authoritative.

## 9. Validation

All 16 checks in `validation_results.md` were actually run this session, including the load-bearing frontier-reconstruction accuracy check (max abs diff 1.1×10⁻¹⁶), two independent deterministic reruns (byte-identical), the full 1249-test suite (up from 1237, zero regressions), and explicit confirmations that no raw observation file, no manuscript file, and no external API call occurred.

---

## Readiness decision

**EVIDENCE_READY_FOR_WRITING** — for the combined classical-backbone + real-LLM-exploratory evidence base, *conditioned on using the corrected wording in `conclusion_change_matrix.csv`* rather than the original studies' row-level claims.

Rationale against the three-way test:
- The classical evidence remains canonical and reproducible (unchanged this stage; confirmed in Stage 1/2).
- The real-LLM results have been corrected for query clustering (this stage, in full — all three studies, all declared families).
- Multiplicity has been handled (Holm correction applied to both the 8-extractor and 23-feature families; the frontier study's 3 diagnostics were declared and justified as NOT one family, per its own original framing).
- Limitations are fully documented (`conclusion_change_matrix.csv`'s "required repository wording" column, this report's §3-5 caveats, and `deferred_items.csv`'s explicit statement that the 6-query power limit is fundamental, not a remaining analysis gap).
- No unresolved *inferential* issue prevents accurate future writing — every previously-ambiguous claim now has an unambiguous, cluster-aware, corrected number attached to it.

This is **not** a claim that the real-LLM evidence is strong — it is a claim that it is now *honestly characterized*. Several claims that looked like corroborating evidence for the paper's main thesis under the original (uncorrected) analysis no longer hold up (Borda, is_cyclic), while others survive or are strengthened (whole-graph repair null result, overall repair-harm direction). A future writing stage should use `conclusion_change_matrix.csv` directly rather than either the original reports or this document's prose summary, since the matrix is the more precise source.
