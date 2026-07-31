# Meta-Audit: A Critical Review of `ir_evidence_audit_20260729T182949Z`

**Purpose**: independently re-examine `reports/ir_evidence_audit_20260729T182949Z/FINAL_IR_EVIDENCE_AUDIT.md` (the "prior audit") and its READY_TO_REWRITE verdict, using only already-computed repository artifacts. No experiments were re-run and no results were recomputed; every number below was either read directly from an existing file or recomputed with a one-line pandas check against the exact source CSV/JSONL the prior audit itself cites, solely to verify a specific claim.

**Scope note**: the prior audit spans two paper tracks (`JDIQ_2026`, the classical multi-ranker fusion backbone with n≈419 real queries across 4 datasets; and this session's three real-multi-provider-LLM-judge studies, `repair_frontier`/`extraction_study`/`repair_diagnostic`). The two evidence bases turned out to warrant very different levels of trust — this is the central finding below.

---

## 1. Verification of the prior audit's major conclusions

| Claim in `FINAL_IR_EVIDENCE_AUDIT.md` | Verified against | Result |
|---|---|---|
| §6: Larger-pool greedy family is 0/110 Holm-significant (40/35/35 by cutoff) | `reports/final_revision_task1_pool_cutoff_20260715/tables/pool_cutoff_statistics.csv`, recomputed independently | **Confirmed exactly.** 110 active-family rows, 0 with `holm_active_ms1_family < 0.05`, split 40/35/35 by cutoff. |
| The `==True` pandas bug (Holm p-value column, not boolean) | Same file, recomputed `(active.holm_active_ms1_family == True).sum()` | **Confirmed real.** 109/110 rows match `== True` (i.e., p-value exactly 1.0), which would have produced a false "highly significant" narrative if read naively — the opposite of the true result. The audit's fix (`< 0.05`) is correct. |
| Exact-ILP-vs-greedy real-data delta, bright/ms1/nDCG@10 = 0.005654 | `reports/exact_open_source_ilp_repair_investigation/tables/retrieval_metric_paired_per_query.csv`, recomputed mean of `ilp_scip - greedy` | **Confirmed exactly** (0.0056537568...). |
| Structure-utility aggregated table is genuinely n=12 (4 datasets × 3 regimes, one protocol only) | `table_primary_graph_structure.csv` | **Confirmed.** The file contains exactly one protocol (`primary_minmax_retention_matched`); the n=12 claim and the "cannot run the per-dataset check, only 3 rows/dataset" limitation are both accurate, not just asserted. |
| Repository-scale headroom, query-level n=419, headroom 0.0025 CI [0.0020,0.0030] | `reports/repository_scale_headroom_analysis/manuscript_tables/table_3_oracle_headroom.csv` | **Confirmed**, and correctly the audit uses the "(query-level, recommended)" row, not the noisier row-level breakdowns (n=5,338–16,790) that pseudo-replicate the same query across many rows — this distinction is handled correctly here. |
| Baseline pool/cutoff/missing-doc-handling alignment (CombSUM/RRF/Prior/Borda) | `qrels_reference.py`, `table_primary_macro_method_comparison.csv` | **Plausible and consistent** with the cited mechanism; not independently re-derived from raw per-query files, but the claimed mechanism (shared `query_method_metrics.csv` row set, single cutoff column) is architecturally sound and nothing found contradicts it. |
| "Prior and Borda fusion are... not separately named in prose" (baseline_verification.csv, §5, §8 item 1) | `papers/JDIQ_2026/manuscript/main.tex:141,280-281` | **Overstated.** Both are explicitly named in prose: "graph-free baselines (Prior, RRF, CombSUM, and Borda)" (line 280) and again in Related Work (line 141). What is actually missing is their *specific nDCG values* in the results-discussion paragraph (lines 421-424 name only CombSUM=0.554 and RRF=0.546). The audit's own §8 recommended fix ("name them in prose") is therefore already half-done; the real remaining gap is narrower than stated — add the two numbers, not the two names. |

**Overall**: every number I re-derived from source matched. The two self-reported bugs are real and the fixes are correct. The one factual slip found (Prior/Borda "not named in prose") is minor and self-correcting (the fix the audit already proposes covers it).

---

## 2. Does the evidence support the stated IR thesis?

> Preference-graph construction materially affects graph structure, but structural consistency is not a reliable surrogate for downstream retrieval effectiveness.

For the **classical multi-ranker backbone** (JDIQ, n=419 queries, 4 datasets): **yes, robustly.** Cutoff-robust (§6), Holm-corrected across every family tested, corroborated by an independent exact-vs-greedy repair check across 5 metrics, and baseline-verified against 4 graph-free fusion methods that are already competitive or superior. This part of the evidence is as strong as the prior audit says.

For the **real multi-provider LLM-judge extension** (`repair_frontier`/`extraction_study`/`repair_diagnostic`, all "n=120 query-graphs"): the qualitative direction (no meaningful headroom, no meaningful extraction gain) is plausibly real and consistent with the backbone, but the prior audit substantially overstates how much independent statistical weight this evidence carries — see §3 and §5 below. The thesis is very likely still *true* under these conditions; the evidence for it, as currently written up, is weaker than presented.

---

## 3. Independent re-verification of the seven required checks

**Cutoff robustness** — Confirmed independently (0/110 at nDCG@5/10/20, 0/56 exact-SCIP larger-pool, |mean delta| ≤ 0.001 across nDCG@5/10/20/MAP/MRR for exact-vs-greedy). No cutoff or metric flips the conclusion. Solid.

**Baseline verification** — Mechanism is sound (shared candidate pool, shared cutoff, uniform missing-doc=0 convention). One wording overstatement found (§1 table above), otherwise fine.

**Structure-vs-utility associations** — Recomputed the aggregated n=12 case's data provenance (confirmed genuinely 12 rows, single protocol) and the per-query n=17,532 case (confirmed 342 real distinct queries feed it, and confirmed 179 of them survive the `std < 1e-9` degenerate-variance filter for the within-query check — a legitimate, symmetric filter, not cherry-picking). Both pooled and within-query correlations are small and same-signed, which is real evidence against a Simpson's-paradox artifact **at this specific granularity**. However, a coarser sign-inconsistency is visible directly in the unified table and *is* partially surfaced (§4 of the prior audit, "aggregation-artifact warning"): among the four dataset × ms1 cells, three are positive (SciDocs +0.011, HotpotQA +0.016) but BRIGHT is the largest-magnitude cell in the entire backbone and is **negative** (−0.014). The prior audit does mention this asymmetry in prose but never states the plain fact that cyclicity's association with the repair effect **flips sign across datasets** — which is precisely what a formal Simpson's-paradox check would have flagged if n≥5/dataset had been available. This is a real, disclosed-but-underlined-too-softly point, not a new discovery — it does not change the conclusion (the pooled effect is still negligible either way) but it does mean the "no aggregation artifact" framing in §3 of the prior audit is doing more work than the data cleanly supports at the aggregated granularity.

**Exact vs. greedy repair** — Confirmed: 0/36 canonical, 0/56 larger-pool exact-SCIP Holm-significant cells, and the real-data exact-vs-greedy comparison I recomputed directly (bright/ms1/nDCG@10 = +0.005654) matches to 15 significant digits. Robust.

**Repair-frontier, extraction-study, repair-diagnostic conclusions** — Directionally reproduced (no meaningful headroom/gain in any of the three), **but see §5: the n=120 figure materially overstates the independent information content of this evidence**, which the prior audit does not disclose or correct for.

---

## 4. Methodological weaknesses found

1. **Dependence between observations / hidden pseudo-replication in the "this session" studies (see §5 — the most serious finding).**
2. **Hidden multiple-comparison issue in the extraction-method comparison.** `extraction_study_20260729T151610Z/FINAL_REPORT.md` reports 8 per-extractor bootstrap 95% CIs (borda, pagerank, rank_centrality, balance_score, hodge_rank, fas_balance_prior_fusion, hybrid_rrf_prior_fusion, copeland) with **no Holm/BH correction across the family**, unlike every other family in this research thread (which is otherwise unusually disciplined about this — see main.tex:273-278's explicit pre-registration language). Two of eight CIs exclude zero (hodge_rank positive, borda negative). The prior audit's proposed manuscript text calls Borda "significantly *worse*" without noting this comparison is uncorrected for testing 8 extractors at once. This is fixable by applying the same Holm procedure already used everywhere else in this codebase (`statistical_inference.py` already has the machinery) — a re-analysis of existing numbers, not a new experiment.
3. **Simpson's-paradox screen not run where it matters most.** Already covered in §3; the aggregated n=12 table cannot support the per-dataset check by the script's own n≥5 threshold, and the one place a sign-flip is visible (BRIGHT ms1) is mentioned but not labeled as what it structurally is.
4. **Survivorship/reporting bias** — checked and **not found**: `failures.jsonl`/`provider_failures.jsonl` are empty across all five real-LLM-call studies (`multi_provider_repair_pilot`, `reviewer_concerns_program`, `repair_frontier`, `extraction_study`, `repair_diagnostic`). No queries or API calls were silently dropped.
5. **Unfair baseline comparisons** — checked and **not found**: pool/cutoff/missing-doc-handling alignment is real (§1).
6. **Leakage between analyses** — the three "this session" studies are not leakage in the sense of using held-out test data during training, but they *are* three different analytical lenses applied to **the exact same underlying sample** (see §5), a fact each individual `FINAL_REPORT.md` states plainly ("identical set used by the repair-frontier and extraction studies") but which the top-level `FINAL_IR_EVIDENCE_AUDIT.md` never restates when it calls them "three independent follow-up studies" in the proposed manuscript text.
7. **Optimistic interpretation of null results** — mostly avoided; the prior audit is unusually careful about saying "no reliable positive evidence" rather than "proven equivalent," and it correctly flags the one nominally-significant graph-density correlation as exploratory/uncorrected. This discipline is good and should be preserved in the rewrite.
8. **Insufficient statistical power** — already well-handled for the classical backbone (MDE=0.0207 vs. observed 0.0036, explicitly discussed). **Not handled** for the real-LLM studies — see §5.

---

## 5. The central finding: the "this session" real-LLM studies are 6 queries, not 120

This is the one issue that materially changes the confidence calculus, and it was not caught by the prior audit.

**What "n=120 query-graphs" actually decomposes to.** I traced the row counts across all three studies plus their two upstream sources:

- `multi_provider_repair_pilot_20260729T032348Z`: 6 unique real queries (3 SciDocs, 3 FiQA) — confirmed via direct query_id enumeration.
- `reviewer_concerns_program_20260729T035320Z` (Branch B): same 6 query_ids, expanded across pool-size/sparsity/variant combinations to 180 rows.
- `repair_frontier_20260729T144742Z`, `extraction_study_20260729T151610Z`, `repair_diagnostic_20260729T162748Z`: each reads `RUN_CONFIG.json["sources"]` = exactly these same two upstream directories, and each produces exactly **120 rows over exactly 6 unique query_ids** (verified by direct enumeration of `extraction_results.jsonl` and `diagnostic_results.jsonl`; `frontier_results.jsonl` has 432 rows, still only 6 unique queries). 120 = 6 queries × 4 providers-plus-aggregate × up to 3 pool-size/sparsity constructions. Each individual `FINAL_REPORT.md` is honest about this in isolated sentences ("Query-graphs evaluated: 120 (identical set used by the repair-frontier and extraction studies)" — `repair_diagnostic/FINAL_REPORT.md:1`), but the fact that "120" means "6 real queries repeated ~20 ways" is never stated as a single sentence anywhere, and is completely absent from `FINAL_IR_EVIDENCE_AUDIT.md`.

**Why this matters statistically, concretely:**
- Every bootstrap CI in these three studies (`bootstrap_mean_interval` in `src/consistency_ranker/statistical_inference.py:239`) resamples the 120 rows **with replacement, i.i.d., row-by-row** — there is no clustering by `query_id`. With only 6 independent underlying queries, this bootstrap is resampling (mostly) *within-query* variation across construction variants and dramatically understates the true uncertainty about the underlying population of queries. The reported CIs (e.g., repair-frontier headroom [0.0029, 0.0084]; Borda [−0.0139, −0.0033]) are almost certainly too narrow.
- The repair-diagnostic feature-association table (`tables/FEATURE_ASSOCIATIONS.csv`) computes Pearson/Spearman p-values treating **n=120** as the sample size for a standard correlation test (`is_cyclic`: raw p=0.000999, Holm p=0.023). With only 6 independent queries feeding those 120 points, this p-value is invalid — it is very likely far more optimistic than the true, cluster-corrected value would be. The prior audit's proposed manuscript text ("repair's rare benefit is not predictable from any of nine categories of pre-repair graph features") is fine as stated (it correctly reports the predictor as UNSUPPORTED due to 1 positive example), but it never surfaces that the one nominally Holm-significant association (`is_cyclic`, `topk_involvement`) rests on a p-value that is itself statistically invalid given the true independent sample size.
- **This was already known and better-stated elsewhere in the repo.** `reports/manuscript_reframing_20260729T174326Z/REFRAMING_ANALYSIS.md` (produced ~45 minutes before the audit, same day) is explicit and repeated about this: "this is a **directional robustness check, not a second large-n study** (6 groups is not enough for a standalone claim)" (line 14); "The real-LLM evidence base... has only 6 underlying queries... do not average away the distinction between the n=419 backbone and the n=6-query robustness check" (§3.8, line 101); it even recommends moving the underpowered Branch B pilot to an appendix (line 121) for exactly this reason. `FINAL_IR_EVIDENCE_AUDIT.md` does not cross-reference this sibling document and does not carry any of this caveat into its own proposed manuscript text, which instead describes "**three independent follow-up studies** using real multi-provider LLM-judge preference graphs (n=120 query-graphs...)" with no mention of the underlying n=6.

**Net effect on the thesis**: the qualitative conclusion (no meaningful headroom/gain from richer repair or from alternative extraction, outside the classical setting) is still probably correct — nothing here suggests a *hidden positive effect*, and if anything a wider, honestly-computed CI would still very plausibly exclude the 0.01 practical-significance threshold for most cells. But statements like "significantly worse than the incumbent" (Borda) and the implicit equal-footing given to n=419-backbone claims and n=120(=6)-follow-up claims in the same proposed Results paragraph are not currently justified by the evidence as computed, and would not survive a competent IR reviewer's scrutiny of the CI methodology.

---

## 6. Ten strongest reviewer criticisms

1. **"Your 'n=120' real-LLM sample is actually 6 queries; every CI and p-value in that evidence base ignores this."** *Valid.* Not addressed in the prior audit (it is addressed, more honestly, in a sibling document — `manuscript_reframing_20260729T174326Z` — that the audit doesn't cite). **Fix**: re-run the existing bootstrap as a cluster/block bootstrap over the 6 `query_id` groups (resample queries, not rows) using data already on disk; state n=6 explicitly everywhere n=120 currently appears in prose; downgrade "significantly worse" language accordingly. No new experiments required.
2. **"The extraction-method comparison tests 8 methods at nominal 95% CIs with no family-wise correction, then singles out one (Borda) as significantly negative."** *Valid.* Not addressed anywhere. **Fix**: apply the same Holm procedure already used throughout the rest of the codebase to the 8-extractor family; report whether Borda survives.
3. **"Your baseline-verification table claims Prior/Borda are 'not named in prose,' which is false — they're named at main.tex:280 — so what else in this hand-authored verification table might be imprecise?"** *Valid but minor.* **Fix**: correct the one cell; the substance (their nDCG values aren't discussed) still stands and the audit's own proposed fix already covers it.
4. **"Structural cyclicity's association with the repair effect flips sign across your four datasets (BRIGHT is negative, SciDocs/HotpotQA positive) — that's a Simpson's-paradox red flag you can see by eye in your own figure, yet you frame the aggregated n=12 result as merely 'not significant' rather than 'sign-inconsistent.'"** *Valid, partially addressed.* The asymmetry is mentioned in §4 of the prior audit but not named as what it is. **Fix**: one added sentence stating the sign-inconsistency explicitly, alongside the existing n<5/dataset caveat.
5. **"Two datasets used for the real-LLM studies (SciDocs, FiQA) vs. four for the classical backbone (+BRIGHT, HotpotQA) — you never tested whether the 'consistent across construction mechanisms' claim holds on the two datasets you didn't re-run with LLM judges."** *Valid, not addressed in the prior audit* (it is stated as a limitation in the sibling reframing document, §7). **Fix**: state the 2-vs-4-dataset scope mismatch explicitly wherever cross-mechanism convergence is claimed.
6. **"Your MEANINGFUL_THRESHOLD = 0.01 is used simultaneously as a practical-significance bound and, informally, as a screening device across ~116 reported cells/tests in the unified table — did you correct for the multiplicity of *magnitude*-based screening the way you did for p-value-based screening?"** *Partially valid, but checked and found not to be a real problem*: the three magnitude-flagged cells (rows 3/21/30) were independently checked against Holm-corrected p-values from the underlying family files and did not survive, which is the right way to triangulate a magnitude screen against a statistical one. No fix needed; worth stating explicitly in the rewrite that this triangulation is why the magnitude screen is safe.
7. **"Zero of your five candidate structural predictors reaches significance at n=12, and you call the one that does (graph density) 'exploratory' — but you didn't report the power of this test at all; is n=12 even capable of detecting a real association here?"** *Valid — not computed anywhere.* An 80%-power Pearson correlation detection floor at n=12 is roughly r≈0.7-0.75 at α=0.05 (rule-of-thumb), meaning this analysis can only rule out very large effects. **Fix**: state this power ceiling once, next to the existing "n<8 → not reported" gate — this is a one-line addition, no new computation.
8. **"You reused the same 6-query, real-LLM-judge sample for three different 'independent' studies (repair-frontier, extraction, diagnostic) that all feed the same headline paragraph — that's not three pieces of evidence, that's one dataset analyzed three ways."** *Valid.* Directly related to #1; **Fix**: describe these three as "three analytical lenses on one small real-LLM pilot sample," not "three independent follow-up studies," in any manuscript language.
9. **"Your repository-scale headroom analysis (n=419) is the strongest single number in the paper, but it lives in a different paper track (`negative_result_2026`) that JDIQ's own `main.tex` never cites — is citing it in this audit's proposed manuscript text actually authorized, or are you drafting text for a paper section that doesn't exist yet?"** *Valid observation, already disclosed by the prior audit itself* (§0 of `FINAL_IR_EVIDENCE_AUDIT.md` states this plainly) — **already addressed**, no further fix needed beyond what's already there.
10. **"Holm correction inside the repair-diagnostic feature-association table is correct arithmetic over p-values that are themselves invalid (see #1) — 'Holm-corrected' is not the same as 'trustworthy' when the input p-values violate the independence assumption the test requires."** *Valid, and a sharper restatement of #1* — worth stating explicitly since "Holm-corrected" reads as a stamp of rigor to a reviewer and could otherwise mask the deeper problem.

---

## 7. Is any additional experiment genuinely required?

**Mandatory (must happen before this can be submitted as currently drafted):**
- None that require new data collection or new API calls. The one mandatory item is **re-analysis of existing data**: recompute the three "this session" studies' CIs/p-values with a query-level cluster/block bootstrap (resample the 6 `query_id` groups, not the 120 rows) instead of, or alongside, the current row-level bootstrap, and apply Holm/BH correction across the 8-extractor family. Both are pure statistics on data already on disk (`extraction_results.jsonl`, `diagnostic_results.jsonl`, `frontier_results.jsonl` all already contain `query_id`), doable with the existing `statistical_inference.py` machinery. This is squarely inside the audit's own "no new experiments" mandate.

**Optional strengthening (would make the paper more convincing but is not required for the core thesis to be defensible):**
- Scaling the real-LLM-judge sample beyond 6 queries (the source reports themselves already recommend this — `reviewer_concerns_program/FINAL_REPORT.md` §9 — but it requires new LLM API calls and is explicitly out of the "no new experiments" scope of both this review and the prior audit).
- Extending the real-LLM studies to BRIGHT/HotpotQA for full 4-dataset parity with the classical backbone.
- A supplementary per-dataset structural-correlation breakdown once more regime/protocol variants exist (already flagged as optional in the prior audit, §8 item 2).

**Purely presentation:**
- Naming Prior/Borda's specific nDCG values in `main.tex` prose (prior audit §8 item 1, corrected scope per §1 above).
- Stating the n=120→6-query decomposition, the 2-vs-4-dataset scope mismatch, and the "three lenses on one sample" framing explicitly in prose (all data-honesty edits, zero new computation).
- Labeling the BRIGHT ms1 sign-flip explicitly as a sign-inconsistency rather than only an "asymmetry."

---

## 8. Readiness reassessment

**READY_TO_REWRITE** — unchanged for the JDIQ classical-fusion backbone (RQ1/RQ2): this evidence base is large, cutoff-robust, Holm-corrected, baseline-verified, and every number I independently re-derived matched exactly.

**For the manuscript as a whole (including the real-LLM follow-up claims as currently drafted in the prior audit's proposed Results/Discussion text): ONE_SMALL_GAP_REMAINS.**

Rationale for not downgrading further to MAJOR_EVIDENCE_GAP: the gap is a **known, well-scoped, statistics-only fix** (cluster-robust re-analysis of data already collected, plus corrected prose framing) that does not require new experiments, new judgments, or new algorithms — it requires exactly the same kind of "re-read what you already have, correctly this time" work this whole research thread has otherwise done well. A more careful sibling document already in the repository (`manuscript_reframing_20260729T174326Z/REFRAMING_ANALYSIS.md`) shows the correct, honest framing was already worked out earlier the same day; the prior audit simply failed to incorporate it. Rationale for not leaving it at READY_TO_REWRITE: as currently proposed, the manuscript text in `FINAL_IR_EVIDENCE_AUDIT.md` §7 would put specific, CI-backed claims ("significantly worse," "reproduce the same qualitative result... n=120 query-graphs") in front of reviewers that do not survive the independence and multiple-comparison scrutiny a competent IR reviewer would apply, for the part of the evidence base built on the real-LLM studies.

---

## Confidence score

**78%** confidence that the current experimental evidence is sufficient for a solid IR paper, *assuming* (a) the manuscript is rewritten well per the prior audit's already-good structure, and (b) the one small gap above (cluster-robust re-analysis and honest n=6 framing of the real-LLM follow-up, plus Holm correction across the 8 extractors) is closed before submission. The classical backbone alone (n=419, 4 datasets) would likely support a solid paper close to 90%+ confidence on its own; the discount reflects that the real-LLM evidence, as currently characterized, would very likely draw the exact criticism in §6 items 1/2/8 from a competent reviewer and needs the stats fix first.

---

## Files in this directory

- This report (`FINAL_META_AUDIT_REVIEW.md`)

No file outside this new report directory was modified. All source files referenced above were read-only.
