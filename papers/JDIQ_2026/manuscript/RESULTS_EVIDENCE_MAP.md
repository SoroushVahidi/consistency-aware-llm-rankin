# Results Evidence Map

**Prepared:** 2026-07-12
**Scope:** Not manuscript prose. A claim-by-claim inventory of what the future Results section (§5–§8 of `main.tex`, per `MANUSCRIPT_OUTLINE.md`'s numbering, or §5–§9 per the Introduction's current roadmap) can say, each claim traced to a canonical source file, with the exact table/row/field, dataset/regime, method comparison, sample size, point estimate, interval, placement recommendation, caveat, and related reviewer concern. No stale or historical (pre-`pub_vote_cmp_all4`, `pub_vote_cmp_v2`-derived) results are included.

Organized by the nine scientific questions the Results section must answer (R1–R9).

---

## R1. How strongly does graph-construction regime control cyclicity?

| Field | Value |
|---|---|
| Claim ID | R1-C1 |
| Exact claim | Under `ms2`, all four datasets are 0% cyclic (avg. largest SCC = 1.0); under `ms1`, cyclic-query prevalence ranges 51.9%–95.0% and avg. largest SCC ranges 2.5–12.5; under `ms1_drop_mutual`, cyclicity returns to near-zero (0–6.0%) except a residual 6.0% on BRIGHT. |
| Source file | `outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv` |
| Table/row/field | All 12 rows (4 datasets × 3 regimes); fields `pct_cyclic`, `avg_largest_scc` |
| Dataset/regime | All four × all three |
| Method comparison | N/A (structural property of the graph, not a ranking method) |
| Sample size | SciDocs 119/120/120; FiQA 117/120/120; HotpotQA 52/52/52; BRIGHT 34/50/50 (ms2/ms1/ms1\_drop\_mutual) |
| Point estimate | See Table 2 in `main.tex` for the query counts; exact `pct_cyclic`/`avg_largest_scc` values already reproduced in `papers/JDIQ_2026/FIGURE_SPECIFICATIONS.md` F02's data table |
| CI / significance | N/A — descriptive statistic over the full query set, not an inferential comparison |
| Placement | Main text + Table (structural metrics table, `MANUSCRIPT_OUTLINE.md` Table 4) + Figure 2 (`fig_cyclicity_and_scc.png`, already referenced in `main.tex` §5, out of this task's scope to rewrite) |
| Caveat | BRIGHT's residual 6.0% cyclicity under `ms1_drop_mutual` (vs. exactly 0% for the other three datasets) should be noted as a mild exception, not an inconsistency |
| Reviewer concern | R7 (dataset breadth/protocol) — this result is the backbone of the "regime is the dominant driver, not repair" claim |

---

## R2. Does repair improve structural quality?

| Field | Value |
|---|---|
| Claim ID | R2-C1 |
| Exact claim | Under `ms1` (the only regime with material cyclicity), FAS repair reduces mean backward-edge weight (BEW) and pairwise inconsistency count (PIC) relative to relevance-judgment-derived reference rankings, on all four datasets. |
| Source file | `outputs/pub_vote_cmp_all4/paper_package/tables/table_consistency_qrels_bew.csv` |
| Table/row/field | 4 `ms1` rows; fields `mean_bew_pre`/`mean_bew_post`/`mean_delta_bew`, `mean_pic_pre`/`mean_pic_post`/`mean_delta_pic`, `mean_fas_weight_removed` |
| Dataset/regime | All four × `ms1` only (ms2/ms1\_drop\_mutual are near-acyclic, so repair removes ≈0 weight and this comparison is degenerate there by construction) |
| Method comparison | Copeland hybrid, pre- vs. post-repair (same Eq.~\eqref{eq:hybrid} formula, graph only) |
| Sample size | Same per-dataset `ms1` counts as R1 (120/120/52/50) |
| Point estimate | ΔPIC ranges 0.5 (HotpotQA) to 6.2 (FiQA); ΔBEW is smaller in magnitude throughout (already summarized in `FIGURE_SPECIFICATIONS.md` F03's data table) |
| CI / significance | N/A — descriptive pre/post means, not bootstrapped in the canonical package |
| Placement | Main text + Table 4 (structural metrics) + Figure 3 (`fig_graph_qrels_bew_pre_post.png`) |
| Caveat | **Mandatory**, already anticipated in `main.tex` §3.3 (Eq.~\eqref{eq:bew}/\eqref{eq:pic} paragraph): BEW/PIC are computed against the same relevance judgments used for nDCG, a circularity that must be disclosed in the same breath as this claim, not deferred silently to Threats to Validity |
| Reviewer concern | R12 (BEW/PIC self-referential) |

---

## R3. Does structural improvement translate into retrieval improvement?

| Field | Value |
|---|---|
| Claim ID | R3-C1 (the central decoupling claim) |
| Exact claim | Of 24 dataset×regime×pair cells (Copeland and balance hybrids, repaired vs. unrepaired), 20 show exactly zero bootstrap mean ΔnDCG (CI = [0,0]); of the 4 active `ms1`/Copeland cells, 3 have CIs that straddle zero (SciDocs, FiQA, BRIGHT) and 1 (HotpotQA) has a CI bounded away from negative (mean +0.0167, CI [0, 0.0405]) — the only cell in the table with a reliable non-null effect. |
| Source file | `outputs/pub_vote_cmp_all4/paper_package/tables/table_bootstrap_delta_ndcg.csv`; already extracted, quality-checked, and re-derived (join only, no new statistics) in `papers/JDIQ_2026/figure4_evidence/figure4_bootstrap_data.csv` |
| Table/row/field | All 24 rows (excludes `*_scc_high`/`*_scc_low` sub-strata, which belong in a supplementary figure per `FIGURE_SPECIFICATIONS.md` SF05); fields `mean_delta_ndcg`, `ci95_low`, `ci95_high`, plus the derived `ci_relation_to_zero` classification |
| Dataset/regime | All four × all three, × {Copeland, balance} |
| Method comparison | Repaired vs. unrepaired hybrid (Eq.~\eqref{eq:hybrid}), same component, same $\alpha=0.3$ |
| Sample size | Per-cell `n_queries` matches Table 2 exactly (verified in the earlier Figure 4 evidence task) |
| Point estimate / CI | See `figure4_bootstrap_data.csv` for all 24 rows verbatim; headline row: HotpotQA/`ms1`/Copeland, mean $+0.0167$, CI $[0, 0.0405]$ |
| Placement | Main text (central claim) + Table 5 (bootstrap deltas) + **Figure 4** (see `FIGURE4_FINAL_DECISION.md`, this same task) |
| Caveat | The HotpotQA CI's lower bound is exactly $0.0$, not strictly positive — describe as "does not cross zero below," not "excludes zero" (see `figure4_evidence/FINAL_REPORT.md`'s zero-boundary convention discussion). HotpotQA is also the dataset with the *lowest* `ms1` cyclicity (51.9%) of the four, undercutting a naive "more cyclicity → more repair benefit" reading. |
| Reviewer concern | R1 (novelty), R14 (HotpotQA underpowered, n=52 — must be stated explicitly here, not only in Threats) |

---

## R4. How does the proposed pipeline compare with strong baselines?

| Field | Value |
|---|---|
| Claim ID | R4-C1 |
| Exact claim | Pooled over 1,020 query×regime records, CombSUM (mean nDCG 0.4622) and RRF (0.4587) outperform the repaired Copeland hybrid (0.4387) and the proposed hybrid (0.4549); prior-only (0.4571) also exceeds repaired Copeland. |
| Source file | `experiments/final_method_gap_audit_20260711_221113/task3/final_baseline_comparison.csv` |
| Table/row/field | `scope=pooled` rows (12 methods); fields `mean_ndcg`, `ci95_low`, `ci95_high` |
| Dataset/regime | Pooled across all four datasets and all three regimes (failure-mining protocol, **not** the vote-suite protocol — see R1–R3's source) |
| Method comparison | `combsum`, `rrf`, `borda`, `score_sum`, `prior_only`, `copeland_unrepaired`/`repaired`, `markov_unrepaired`/`repaired`, `balance`, `proposed_hybrid`, `best_stronger_repair` |
| Sample size | n=1,020 pooled; per-dataset breakdown available (`scope` ∈ {scidocs, fiqa, hotpotqa, bright}) for a supplementary per-dataset figure (SF01) |
| Point estimate / CI | CombSUM 0.462 [0.438, 0.487]; RRF 0.459 [0.434, 0.483]; proposed\_hybrid 0.455 [0.431, 0.479]; copeland\_repaired 0.439 [0.415, 0.463] |
| Placement | Main text + Table 6 (pooled baseline comparison) + Figure 5/6 (`fig_mean_ndcg_hybrids.png`, flagged in `main.tex` as a partial asset needing extension to the full 12-method grid) |
| Caveat | **Mandatory protocol footnote**: this is the failure-mining pooled protocol, a different query population from the vote-suite package used in R1–R3 (already disclosed in `main.tex` §4.3's protocol-separation paragraph — Results must repeat this footnote, not assume the reader remembers §4). CombSUM's own count (n=1,020, sum of 360+359+156+145) is not a clean multiple of 3 per dataset for FiQA/BRIGHT — see the regime-invariance caveat below (R4-C2). |
| Reviewer concern | R8 (too few baselines) — resolved; R9 (overclaiming) — must not omit that CombSUM/RRF beat every graph-based method including the proposed hybrid |

| Field | Value |
|---|---|
| Claim ID | R4-C2 (regime-invariance accounting note) |
| Exact claim | CombSUM, RRF, Borda, and the prior ranking are regime-invariant by construction (score depends only on ranker score files, not the graph); their pooled `n` therefore reflects corpus completeness, not independent regime-level observations. FiQA and BRIGHT are missing exactly one query's `ms2` record each (FiQA: 1 query; BRIGHT: 5 queries; both specifically missing `ms2`, not `ms1` or `ms1_drop_mutual`), which is why their pooled counts (359, 145) are not clean multiples of 3 the way SciDocs (360) and HotpotQA (156) are. |
| Source file | `experiments/failure_class_audit_20260711_212157/analysis/canonical_query_records.jsonl` (regime-count histogram computed directly this session); `integrity_audit/combsum_protocol_alignment.csv` |
| Table/row/field | N/A (derived from a direct query over the JSONL, not a single canonical table cell) |
| Placement | A short methodological footnote near Table 6, not its own paragraph — "do not overemphasize," per this task's instruction |
| Caveat | Root cause of *why* `ms2` specifically drops these six query records (rather than `ms1`/`ms1_drop_mutual`) was not traced further — plausibly `ms2`'s stricter retention thresholds occasionally yield a graph too sparse for the downstream pipeline to record, but this is a plausible mechanism, not a confirmed one |
| Reviewer concern | R9 (overclaiming) — a footnote here pre-empts a reviewer computing $360+359+156+145$ and asking why it isn't a clean $4\times$ multiple of the per-dataset base query count |

---

## R5. Does stronger repair improve retrieval?

| Field | Value |
|---|---|
| Claim ID | R5-C1 |
| Exact claim | Exact-for-small-components repair (exact on SCCs ≤10 nodes, greedy fallback above) removes more structural weight than greedy on average (mean removed weight 0.546 vs. 0.547 — effectively tied) but does not improve pooled Copeland nDCG (0.4387 vs. 0.4387 for greedy; paired delta $-3.58\times10^{-5}$, 95% CI $[-1.07\times10^{-4}, 0.0]$). |
| Source file | `experiments/final_method_gap_audit_20260711_221113/task2/repair_comparison_real.csv` and `repair_comparison_per_query.csv` |
| Table/row/field | Rows `greedy` and `exact_small_greedy_hybrid`; fields `mean_ndcg_copeland`, `vs_greedy_mean_delta_copeland`, `vs_greedy_ci95_low`/`ci95_high` |
| Dataset/regime | Pooled, full canonical 1,020-record corpus (**not** a bounded/capped sample — this is the fully in-repository, fully reproducible comparison per the Table 4 patch applied this session) |
| Sample size | n=1,020 for both methods |
| Point estimate / CI | See above; also `exact_vs_greedy_real.csv`'s per-query rows (harm=1, help=2 out of 1,120 query-method pairs where exact and greedy disagree, per `REPAIR_COMPARISON_FINAL_REPORT.md` §3) |
| Placement | Main text + Table 4 (repair variants, already patched in `main.tex`) + a sentence in Results explicitly stating this is the full evidentiary basis for the "stronger repair does not change the conclusion" claim |
| Caveat | Per the integrity audit and this session's Table 4 patch: **do not** reintroduce the four external-package-dependent methods (`exact_scc_dp20`, `lrta_external`, `wmsf_external`, `ipsns_external`) by name in Results; if their bounded-sample outcome is mentioned at all, use the same anonymized qualitative phrasing already in `main.tex` §4.4 |
| Reviewer concern | R6 (greedy FAS lacked stronger comparisons) — resolved with a fully in-repository, non-anonymity-risking comparison |

---

## R6. When and why is repair inactive or harmful?

| Field | Value |
|---|---|
| Claim ID | R6-C1 |
| Exact claim | Across 1,020 query×regime records, repair is retrieval-inactive in 63.9% of cases (652), a tail-only ranking change in 20.6% (210), metric-neutral in 5.3% (54), extraction-insensitive in 2.5% (26), wrong-direction (harmful) in 5.4% (55, mean ΔnDCG $-0.0341$), and unknown/mixed in 2.3% (23). |
| Source file | `experiments/failure_class_audit_20260711_212157/phase_reports/manual_failure_summary.csv` |
| Table/row/field | All 6 rows; fields `count`, `pct`, `mean_delta`, `mean_scc`, `mean_top10_intersection` |
| Dataset/regime | Pooled (failure-mining corpus, same population as R4) |
| Sample size | n=1,020 |
| Point estimate | See table above; `wrong_direction_repair` is the only class with materially negative mean ΔnDCG |
| CI / significance | N/A — categorical frequency table, not an inferential comparison |
| Placement | Main text + Table 7 (failure taxonomy) + Figure 7 (failure-class distribution, not yet generated — `main.tex` has a placeholder) |
| Caveat | This 1,020-record corpus is the same pooled/failure-mining population as R4, not the vote-suite population of R1–R3 — repeat the protocol footnote |
| Reviewer concern | R1 (novelty — this taxonomy is a primary source of new contribution beyond the rejected IJCS version), R2 (actionable criterion — this is diagnostic, not predictive; do not overclaim a decision rule) |

---

## R7. Does fusion suppress graph-level changes?

| Field | Value |
|---|---|
| Claim ID | R7-C1 |
| Exact claim | For the Copeland component under RRF-style fusion (matching the main paper's $\alpha=0.3$ hybrid), fusion suppresses the graph-level ranking change in 14.7% of query-method comparisons where repair changed the raw graph ranking but the fused hybrid ranking was unchanged; the rate is higher for some other component/fusion-mode combinations (e.g., Rank Centrality/confidence-weighted: 26.4%) and lower for others (e.g., balance/rrf: 4.8%). |
| Source file | `experiments/final_method_gap_audit_20260711_221113/task1/extraction_fusion_complete.csv`; definition verified directly against `run_final_method_gap_audit.py` (a comparison counts as "suppressed" iff the graph-only ranking changed after repair **and** the fused hybrid ranking did not) |
| Table/row/field | Row `hybrid_repaired_copeland_a0p3_rrf` (and others); field `fusion_suppression_rate` |
| Dataset/regime | Pooled (failure-mining corpus) |
| Sample size | n=1,020 per row (`n_hybrid_comparisons` in the underlying aggregation) |
| Point estimate | 0.147 (Copeland/rrf, $\alpha=0.3$); see `EXTRACTION_FUSION_FINAL_REPORT.md` "Fusion suppression" section for the five highest-suppression component/mode combinations |
| CI / significance | N/A — descriptive rate, not bootstrapped |
| Placement | Supplement (SF02, per `FIGURE_SPECIFICATIONS.md`) rather than main text, given page budget; a single sentence in Results/Discussion citing the 14.7% figure is sufficient for the main paper |
| Caveat | This is diagnostic evidence for *one* mechanism among six failure classes (R6), not proof that fusion suppression is *the* explanation for null results — claim matrix classification `fusion_suppresses_repair = safe_with_qualification` ("supported diagnostically, not as universal law") must be preserved in wording |
| Reviewer concern | R5 (fusion suppression hypothesis) — directly answers it, with a precise, code-verified metric |

---

## R8. What do the bounded real-LLM pilots show?

| Field | Value |
|---|---|
| Claim ID | R8-C1 |
| Exact claim | SciDocs (50q, real OpenAI pairwise): 92.0% cyclic queries, repaired-vs-unrepaired Copeland ΔnDCG $-0.0010$, 95% CI $[-0.001905, -0.000208]$ (excludes zero, negative direction). HotpotQA (20q): 80.0% cyclic, ΔnDCG $0.0$, CI $[0,0]$ (degenerate/inactive). FiQA (10 processed of a 20-query target): 10.0% cyclic, ΔnDCG $0.0$, CI $[0,0]$. |
| Source file | `outputs/openai_real_llm_cross_dataset_summary.md` |
| Table/row/field | The 3-row summary table (Dataset, Queries done, Cyclic-query rate, Best method, Best nDCG@15, Best MAP@15, Repaired-Unrepaired ΔnDCG, 95% CI) |
| Dataset/regime | SciDocs/HotpotQA/FiQA, real-LLM pairwise judgments (not the mechanical BM25/TF-IDF/MiniLM votes of R1–R6) |
| Sample size | 50 / 20 / 10 (FiQA processed, of a 20-query target) |
| Point estimate / CI | See above table |
| Placement | Main text (brief) + Table 9 (real-LLM cross-dataset summary, placeholder already in `main.tex` §8) |
| Caveat | **Mandatory, already committed to in `main.tex` §4.7**: report as "a bounded check... not independent confirmatory evidence at the same scale." SciDocs's negative CI is the one real-LLM result with a directionally confident (CI excludes zero) effect, and it is *negative* — this must be stated plainly, not softened, per the claim discipline already established in the Introduction (I-3 in `INTRODUCTION_EVIDENCE_MAP.md`). FiQA's "10 processed of a 20-query target" phrasing must be preserved exactly — do not round up to "20 queries." |
| Reviewer concern | R4 (real-LLM too small) — this section is where that limitation must be stated most explicitly, not merely gestured at |

---

## R9. What are the runtime and memory implications?

| Field | Value |
|---|---|
| Claim ID | R9-C1 |
| Exact claim | On the real-data pipeline, greedy repair's measured runtime is effectively instantaneous relative to the timing resolution used (reported as $0.0000$s in the pooled aggregation); exact-for-small-components adds measurable but modest overhead (mean $0.0623$s per query, mean peak RSS $\approx 1646$MB) — a small fraction of a second per query, not a scalability blocker at the sizes tested. |
| Source file | `experiments/final_method_gap_audit_20260711_221113/task2/repair_comparison_real.csv` |
| Table/row/field | Rows `greedy`, `exact_small_greedy_hybrid`; fields `mean_runtime_seconds`, `mean_peak_memory_mb` |
| Dataset/regime | Pooled, full 1,020-record corpus |
| Sample size | n=1,020 |
| Point estimate | See above |
| CI / significance | N/A — mean timing/memory, not bootstrapped |
| Placement | Supplement (Appendix E, per `MANUSCRIPT_OUTLINE.md`), not main text — this is a minor, secondary result relative to R1–R6 |
| Caveat | **Mandatory, already stated in `main.tex` §4.6**: memory is a coarse before/after RSS snapshot, not instrumented peak-memory tracking; measurements are from a single, unbenchmarked local machine, not a controlled hardware configuration. Synthetic runtime figures elsewhere in the repository (`docs/tables/runtime_results.csv`, "49% of runtime at n=10 rising to 97% at n=100") are a **separate, synthetic-only** experiment family and must not be cited as real-pipeline evidence — per `experiments/failure_class_audit_20260711_212157/phase_reports/EFFICIENCY_EVIDENCE_AUDIT.md`, "no committed comparable memory benchmark package was found for the current real-data vote-graph pipeline" beyond what is cited above. |
| Reviewer concern | None of R1–R15 directly targets runtime, but `CANONICAL_PAPER_STORY.md`'s claim matrix classifies `runtime_practical = safe_with_qualification` ("synthetic only; real-pipeline partial") and `memory_practical = unsupported` — Results must not claim more than this partial real-data evidence supports |

---

## Summary table: claim → placement

| Claim | Main text | Table | Figure | Supplement |
|---|---|---|---|---|
| R1 (regime controls cyclicity) | Yes | Table 4 | Figure 2 | — |
| R2 (repair improves structure) | Yes | Table 4 | Figure 3 | — |
| R3 (decoupling, central claim) | Yes | Table 5 | **Figure 4** | SF05 (SCC-stratified) |
| R4 (baseline comparison) | Yes | Table 6 | Figure 5/6 | SF01 (per-dataset) |
| R5 (stronger repair) | Yes | Table 4 | — | — |
| R6 (failure taxonomy) | Yes | Table 7 | Figure 7 | — |
| R7 (fusion suppression) | One sentence | — | — | SF02 |
| R8 (real-LLM) | Brief | Table 9 | — | — |
| R9 (runtime/memory) | — | — | — | Appendix E |
