# Results Section Plan

**Prepared:** 2026-07-12
**Scope:** A structural plan for the Results content, not prose. Written to read as an archival journal article's section plan, not an audit report.

---

## Recommended structure: four sections, not one

The task's suggested outline (a single "5. Results" section with subsections 5.1–5.7) is a reasonable default, but `main.tex` already scaffolds this material as **four separate top-level sections** — §5 Structural Data Quality Results, §6 Downstream Quality Results: Repair vs. Retrieval, §7 Failure Taxonomy and Diagnostic Analysis, §8 Bounded Real-LLM Validation — each already carrying a `\label`, forward-referenced repeatedly from §1–§4 (e.g., "Section~\ref{sec:downstream-results} (forward reference)" appears seven times across the completed sections), and each matching `MANUSCRIPT_OUTLINE.md`'s existing page budget (§5 ≈2.5pg, §6 ≈3pg, §7 ≈2.5pg, §8 ≈1–1.5pg). Collapsing these into subsections of one mega-section would require renumbering every existing forward reference and every downstream section (§9 CARB through §13 Data Availability), for no corresponding gain in clarity — JDIQ technical papers routinely run one experimental result family per top-level section at this page count. **Recommendation: keep the four-section structure**, organized internally as follows.

---

## §5 Structural Data Quality Results

- **Central question:** Does vote-construction regime, more than repair itself, determine preference-graph inconsistency — and does repair measurably reduce that inconsistency when it is present?
- **Main findings (2–3):**
  1. `ms2` and `ms1_drop_mutual` are near-acyclic on all four datasets (0–6% cyclic); `ms1` is substantially cyclic (52–95%), with proportionally larger strongly connected components (R1).
  2. FAS repair reduces graph–reference backward-edge weight and pairwise inconsistency count on all four datasets under `ms1`, the only regime where there is meaningful inconsistency to repair (R2).
  3. (Brief, one sentence) The BEW/PIC circularity caveat — these structural diagnostics use the same relevance judgments as the nDCG metric reported in §6 — must be stated here, at first use, not deferred.
- **Canonical table(s):** Table 4 (structural metrics by dataset/regime, `table_graph_ndcg_and_consistency.csv`); Table 4b or an inline BEW/PIC table (`table_consistency_qrels_bew.csv`).
- **Figure(s):** Figure 2 (cyclicity and SCC by regime, `fig_cyclicity_and_scc.png`); Figure 3 (BEW/PIC pre/post, `fig_graph_qrels_bew_pre_post.png`) — both already referenced as placeholders in `main.tex`.
- **Supplement:** None — this is core main-text material.
- **Reviewer concern addressed:** R12 (BEW/PIC circularity, stated at first use); R7 (dataset breadth — four datasets, not two).
- **Target word count:** ≈600–750 words (matches the ≈2.5-page budget at ACM manuscript-format density).

---

## §6 Downstream Quality Results: Repair vs. Retrieval

- **Central question:** Does the structural improvement from §5 translate into a retrieval-quality (nDCG) improvement — and how does the resulting pipeline compare against strong, repair-free aggregation baselines?
- **Main findings (3–4):**
  1. The central decoupling result: 20 of 24 dataset×regime×pair cells show exactly zero bootstrap ΔnDCG; among the four active `ms1`/Copeland cells, three have CIs straddling zero and one (HotpotQA) has a CI bounded away from negative — the only reliable non-null effect in the table, and notably not the most cyclic dataset (R3).
  2. Pooled over the failure-mining corpus, CombSUM and RRF outperform the repaired Copeland hybrid and the proposed hybrid; the proposed hybrid does not close this gap (R4).
  3. A fully in-repository exact-for-small-components repair procedure removes at least as much structural weight as greedy but does not change the retrieval conclusion — this is the complete evidentiary basis for the "stronger repair doesn't help" claim, and the only such basis reported in the main paper (R5).
  4. One sentence bridging to §7: fusion suppression is one candidate mechanism for some null results, quantified at 14.7% for the Copeland/RRF combination used in the main hybrid, with a pointer to the supplement and to §7's fuller taxonomy (R7, abbreviated).
- **Canonical table(s):** Table 5 (bootstrap deltas, `table_bootstrap_delta_ndcg.csv` / `figure4_bootstrap_data.csv`); Table 6 (pooled baseline comparison, `final_baseline_comparison.csv`); Table 4's second row reused for the stronger-repair comparison (`repair_comparison_real.csv`, `greedy` vs. `exact_small_greedy_hybrid` only — no external-package rows, per the Table 4 patch already applied).
- **Figure(s):** **Figure 4** (bootstrap ΔnDCG forest plot — see `FIGURE4_FINAL_DECISION.md`); Figure 5/6 (pooled baseline comparison bar chart, extending the existing partial `fig_mean_ndcg_hybrids.png` asset to the full 12-method grid).
- **Supplement:** SF01 (per-dataset baseline breakdown); SF02 (fusion suppression rates, full component×mode grid); SF05 (HotpotQA SCC-stratified bootstrap detail).
- **Reviewer concern addressed:** R1 (novelty — this is the paper's central quantitative claim), R6 (stronger repair, now fully in-repository), R8 (baseline breadth), R9 (overclaiming — CombSUM/RRF beating the proposed hybrid must be stated plainly).
- **Target word count:** ≈750–900 words (largest section; ≈3-page budget).

---

## §7 Failure Taxonomy and Diagnostic Analysis

- **Central question:** When repair does not improve retrieval, why not — what specific, interpretable mechanisms explain the null and negative results from §6?
- **Main findings (2–3):**
  1. Six-class taxonomy over 1,020 records: repair-inactive (63.9%), tail-only change (20.6%), metric-neutral (5.3%), extraction-insensitive (2.5%), wrong-direction/harmful (5.4%, mean ΔnDCG $-0.034$), unknown/mixed (2.3%) (R6).
  2. Wrong-direction repair is the only class with materially negative mean ΔnDCG, and is a minority (5.4%) of cases — most "failures" are inactivity or tail-only changes, not harm (R6).
  3. One paragraph on fusion suppression as a contributing mechanism for a subset of null results, with the precise 14.7% figure and a pointer to SF02 for the full grid (R7, main-text detail level).
- **Canonical table(s):** Table 7 (failure class taxonomy, `manual_failure_summary.csv`).
- **Figure(s):** Figure 7 (failure class distribution — not yet generated; script `papers/JDIQ_2026/scripts/fig06_failure_classes.py` still needs to be written, out of this task's scope).
- **Supplement:** SF02 (fusion suppression, full grid); SF04 (regret decomposition by failure class, if page budget allows); SF06 (minimal-intervention summary for harmful cases).
- **Reviewer concern addressed:** R2 (actionable criterion — candidly diagnostic, not predictive, per `REVIEWER_CONCERN_COVERAGE.md`'s existing honest framing), R5 (fusion suppression, detailed here).
- **Target word count:** ≈600–750 words (≈2.5-page budget).

---

## §8 Bounded Real-LLM Validation

- **Central question:** Does the regime-conditional structural/retrieval decoupling pattern from §5–§6 persist under genuine LLM pairwise preferences, not just mechanical BM25/TF-IDF/MiniLM votes?
- **Main findings (2):**
  1. Cyclicity is regime-sensitive under real LLM judgments too: SciDocs 92.0% cyclic (50q), HotpotQA 80.0% (20q), FiQA 10.0% (10 of 20 processed) (R8).
  2. Repaired-vs-unrepaired ΔnDCG is small and dataset-dependent: SciDocs shows a small *negative* effect with a CI excluding zero ($-0.0010$, $[-0.0019, -0.0002]$); HotpotQA and FiQA are both degenerate at zero (R8).
- **Canonical table(s):** Table 9 (real-LLM cross-dataset summary, `outputs/openai_real_llm_cross_dataset_summary.md`).
- **Figure(s):** None planned (a small summary bar chart is optional per `MANUSCRIPT_OUTLINE.md`, not required).
- **Supplement:** None additional — this section is already a bounded/secondary result by design.
- **Mandatory limitations paragraph (per `MANUSCRIPT_OUTLINE.md` and `RESULTS_EVIDENCE_MAP.md` R8):** N ≤ 50 per dataset, single LLM provider for the primary results, FiQA's 10-of-20 processing must be stated exactly, not rounded — report as a supporting check, not confirmatory evidence at the same evidentiary standard as §5–§7.
- **Reviewer concern addressed:** R3 (ranker set too narrow — this section is the main partial answer), R4 (real-LLM too small — stated explicitly here, not softened).
- **Target word count:** ≈350–450 words (shortest results section; ≈1–1.5-page budget).

---

## Where R9 (runtime/memory) goes

Not a main Results section. Per the evidence map, R9's evidence is thin (one real-data comparison point: greedy vs. exact-for-small-components timing/memory) and the claim-support matrix already classifies `runtime_practical` as only `safe_with_qualification` and `memory_practical` as `unsupported`. Recommend a short paragraph in Discussion (§10, out of this task's scope) or Appendix E, not a Results subsection — giving it a full subsection would overstate its evidentiary weight relative to R1–R8.

---

## Cross-cutting drafting rules for Results (carried from the standing manuscript constraints)

1. Every dataset/regime/method-comparison sentence must cite its source table by number, matching `RESULTS_EVIDENCE_MAP.md` exactly — no new computation, no rounding beyond what the canonical CSVs already report.
2. Repeat the vote-suite vs. pooled failure-mining protocol footnote at least once per section that uses either corpus (§5–§6 use the vote-suite corpus; §6's baseline comparison and §7 use the pooled corpus) — do not assume the reader retains §4.3's disclosure across sections.
3. Do not name or link the external solver package anywhere in Results, per the integrity audit; if the bounded stronger-repair robustness check is mentioned again in Results (beyond its one qualitative sentence already in §4.4), use the same anonymized phrasing.
4. Every table/figure reference must resolve to a label that exists — verify with the same programmatic check used for §1–§4 (`grep -o '\label{...}'` vs. `\ref`/`\eqref` cross-check) before considering Results complete.
5. Total Results word budget across all four sections: **≈2,300–2,850 words**, consistent with the ≈9–10 page combined budget in `MANUSCRIPT_OUTLINE.md`.
