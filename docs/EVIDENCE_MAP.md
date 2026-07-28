# Evidence Map

> **SUPERSEDED (as of 2026-07-28).** Written 2026-04-06, before
> `papers/JDIQ_2026/`. Every "Supporting output files" row below points at
> `outputs/pub_vote_cmp_v2/`, explicitly marked `do_not_use`/stale in
> `papers/JDIQ_2026/MASTER_EVIDENCE_INVENTORY.csv` and numerically
> inconsistent with the current canonical `outputs/pub_vote_cmp_all4/`
> package for at least one of the claims mapped here. Use
> `papers/JDIQ_2026/SECTION_EVIDENCE_MAP.csv` for current claim-to-evidence
> mapping instead.

> Maps each major claim to supporting scripts, output files, report files, and
> an honest assessment of support strength.  All evidence cited is committed to
> the repository; no projected or invented results are included.

---

## Claim E1 — Vote construction controls graph cyclicity

**Statement:** The choice of vote aggregation strategy (ms2 vs ms1 vs ms1_drop_mutual) is the
dominant factor determining cycle prevalence in multi-ranker preference graphs.

| Field | Detail |
|---|---|
| Support level | **Strong** |
| Supporting scripts | `scripts/run_publication_vote_suite.py`, `scripts/diagnose_vote_graph_cycles.py` |
| Supporting output files | `outputs/pub_vote_cmp_v2/paper_package/tables/table_graph_ndcg_and_consistency.csv` |
| Supporting report files | `outputs/pub_vote_cmp_v2/paper_package/MANUSCRIPT_SUMMARY.md` |
| Key numbers | SciDocs: ms2 → 1.68% cyclic; ms1 → 97.5% cyclic; ms1_drop_mutual → 9.17% cyclic |
| What would upgrade it | Replicate on FiQA and BRIGHT datasets (REAL-3, REAL-4) |

---

## Claim E2 — FAS repair reduces label-aligned structural inconsistency

**Statement:** Greedy MWFAS repair reduces backward-edge weight (BEW) and pairwise
inconsistency count (PIC) measured against a qrels-derived reference ranking, under
high-cyclicity constructions.

| Field | Detail |
|---|---|
| Support level | **Strong** |
| Supporting scripts | `scripts/build_paper_evidence_package.py`, `src/consistency_ranker/greedy_fas.py` |
| Supporting output files | `outputs/pub_vote_cmp_v2/paper_package/tables/table_consistency_qrels_bew.csv`, `outputs/pub_vote_cmp_v2/paper_package/tables/table_graph_ndcg_and_consistency.csv` |
| Supporting report files | `outputs/pub_vote_cmp_v2/paper_package/MANUSCRIPT_SUMMARY.md` |
| Key numbers | SciDocs ms1: BEW pre/post 309.09→307.96 (Δ1.13); PIC pre/post 99.84→88.08 (Δ11.76) |
| Important caveat | BEW/PIC are measured against qrels-derived reference, not an independent ground truth |
| What would upgrade it | Independent graph-theoretic measure (SCC diameter, topological ambiguity); replicate on FiQA/BRIGHT |

---

## Claim E3 — FAS repair harms nDCG under high-cyclicity vote construction (SciDocs ms1)

**Statement:** Under ms1 vote construction on SciDocs, repaired Copeland hybrid has mean per-query
ΔnDCG = −0.0091 (repaired − unrepaired), with bootstrap 95% CI [−0.017, −0.003] strictly below zero.

| Field | Detail |
|---|---|
| Support level | **Strong** |
| Supporting scripts | `scripts/analyze_publication_vote_deltas.py`, `scripts/bootstrap_method_deltas.py` |
| Supporting output files | `outputs/pub_vote_cmp_v2/paper_package/tables/table_bootstrap_delta_ndcg.csv` (row: scidocs/ms1/copeland) |
| Supporting report files | `outputs/pub_vote_cmp_v2/paper_package/MANUSCRIPT_SUMMARY.md`, `docs/Q1_POSITIONING_AND_CLAIMS.md` |
| Key numbers | mean_delta_ndcg = −0.00912, ci95_low = −0.01669, ci95_high = −0.00290, n=120 queries, 2000 bootstrap reps |
| What would upgrade it | Replicate on FiQA and BRIGHT; add multiple-comparisons correction; increase n_queries |

---

## Claim E4 — Harm concentrates in high-SCC queries

**Statement:** On SciDocs ms1, queries with largest SCC ≥ median show ΔnDCG = −0.015
[CI −0.027, −0.006] while queries below median show ΔnDCG ≈ 0 [−0.005, +0.004].

| Field | Detail |
|---|---|
| Support level | **Strong** |
| Supporting scripts | `scripts/analyze_publication_vote_deltas.py` |
| Supporting output files | `outputs/pub_vote_cmp_v2/paper_package/tables/table_bootstrap_delta_ndcg.csv` (rows: copeland_scc_high / copeland_scc_low) |
| Supporting report files | `docs/Q1_POSITIONING_AND_CLAIMS.md` (Claim S4) |
| Key numbers | SCC_high n=70: mean −0.0151, CI [−0.0271, −0.00574]; SCC_low n=50: mean −0.000705, CI [−0.00541, +0.00412] |
| What would upgrade it | Replicate stratification on FiQA/BRIGHT; use continuous SCC size as regressor |

---

## Claim E5 — Repair is inactive under near-acyclic vote constructions

**Statement:** Under ms2 and ms1_drop_mutual on both SciDocs and HotpotQA, repaired and unrepaired
rankings are identical for all method pairs (ΔnDCG = 0, CI [0, 0]).

| Field | Detail |
|---|---|
| Support level | **Strong** |
| Supporting scripts | `scripts/analyze_publication_vote_deltas.py` |
| Supporting output files | `outputs/pub_vote_cmp_v2/paper_package/tables/table_bootstrap_delta_ndcg.csv` (all ms2 and ms1_drop_mutual rows) |
| Key numbers | All ms2 and ms1_drop_mutual rows: mean_delta_ndcg = 0.0, ci = [0.0, 0.0] |
| What would upgrade it | Confirmation on additional datasets |

---

## Claim E6 — Balance hybrids are repair-neutral

**Statement:** Repaired vs unrepaired balance hybrids show no meaningful ΔnDCG under any vote
construction or dataset tested (CI always includes 0, |Δ| < 0.0001).

| Field | Detail |
|---|---|
| Support level | **Strong** |
| Supporting scripts | `scripts/analyze_publication_vote_deltas.py` |
| Supporting output files | `outputs/pub_vote_cmp_v2/paper_package/tables/table_bootstrap_delta_ndcg.csv` (all balance rows) |
| Key numbers | All balance rows: max |mean_delta_ndcg| ≈ 2.5×10⁻⁵ |
| What would upgrade it | Confirmation on FiQA/BRIGHT |

---

## Claim E7 — HotpotQA ms1: marginal harm, not benefit

**Statement:** Under ms1 on HotpotQA, Copeland ΔnDCG mean = −0.00087 [CI −0.00218, 0], n=52 queries.
Evidence of marginal harm; CI touches zero.

| Field | Detail |
|---|---|
| Support level | **Moderate** |
| Supporting output files | `outputs/pub_vote_cmp_v2/paper_package/tables/table_bootstrap_delta_ndcg.csv` (row: hotpotqa/ms1/copeland) |
| Key numbers | mean = −0.000868, ci_low = −0.00218, ci_high = 0.0 (CI includes 0) |
| Limitation | Small sample n=52; CI touches zero |
| What would upgrade it | Larger HotpotQA query set; replicate on BRIGHT |

---

## Claim E8 — Synthetic: Borda dominates greedy FAS topological

**Statement:** Across all synthetic noise levels (0.05–0.30) and scale points (n=10–100),
Borda or score_sum achieves higher Kendall τ than greedy_fas_topological. The gap is
largest under uniform edge weights.

| Field | Detail |
|---|---|
| Support level | **Strong** |
| Supporting scripts | `scripts/run_synthetic.py`, `scripts/build_results_audit_artifacts.py` |
| Supporting output files | Individual `outputs/*/synthetic_results.json` files |
| Supporting report files | `docs/tables/main_results.csv` |
| Key numbers | Scale sweep n=100: borda τ=0.932, score_sum τ=0.896, greedy_fas_topological τ=0.549 |
| Limitation | Synthetic only; no corresponding real-data Kendall τ |
| What would upgrade it | Report Kendall τ for real-data rankings vs qrels-derived reference |

---

## Claim E9 — Greedy FAS runtime scales sub-quadratically in practice

**Statement:** Greedy FAS solver dominates total runtime; n=100 items → ~1.2 s total.
FAS time share rises from ~49% (n=10) to ~97% (n=100).

| Field | Detail |
|---|---|
| Support level | **Strong** |
| Supporting scripts | `scripts/run_synthetic.py --save-timings` |
| Supporting output files | `outputs/scale_sweep_*/timings/synthetic_timings.json` |
| Supporting report files | `docs/tables/runtime_results.csv` |
| Key numbers | n=10: 0.004 s (49% FAS); n=20: 0.014 s (75%); n=50: 0.225 s (94%); n=100: 1.232 s (97%) |
| Limitation | Synthetic graphs; dense pairwise graphs; single seed per scale point |
| What would upgrade it | Real-data timing; sparse graphs; larger n |

---

## Unsupported Claims (for reference)

| Claim | Support Level | Reason |
|---|---|---|
| FAS repair improves nDCG@k unconditionally | **Unsupported** | Bootstrap evidence shows harm or neutrality everywhere tested |
| Method outperforms Borda on IR benchmarks | **Unsupported** | Borda/score_sum dominate in synthetic; not tested as standalone benchmark on real data |
| BEW/PIC improvement predicts retrieval improvement | **Unsupported** | Both measured against qrels-derived reference; not independent of nDCG signal |
| Results generalise to LLM-generated preferences | **Partially supported (bounded)** | Core evidence is score-derived; separate bounded real-LLM runs (SciDocs/HotpotQA/FiQA) support only conservative regime-conditional transfer claims |
| Results generalise to FiQA and BRIGHT | **Unsupported** | Loaders exist but no committed results |
| Exact ILP MWFAS outperforms greedy on real data | **Unsupported** | ILP solver is stubbed; comparison is synthetic only |
