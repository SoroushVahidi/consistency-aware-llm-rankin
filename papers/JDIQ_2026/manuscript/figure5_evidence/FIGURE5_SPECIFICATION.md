# Figure 5 Specification

**Prepared:** 2026-07-12
**Scope:** Canonical plotting package for Figure 5 (pooled mean nDCG@$k$ by ranking method). No image generated in this task.

---

## Design decision

**Selected: Option B — pooled baseline comparison**, matching the comparison already reported in `main.tex` Table 6 (`tab:pooled-baseline`), sourced from `experiments/final_method_gap_audit_20260711_221113/task3/final_baseline_comparison.csv` (`scope=pooled`, 12 methods, $n=1{,}020$ query$\times$regime records).

**Why not Option A (canonical per-dataset comparison):** a per-dataset breakdown of the same 12 methods would require four sub-panels (one per dataset) and roughly 4$\times$ the visual real estate for a claim that Table 6's pooled summary already establishes clearly (CombSUM and RRF outperform every graph-based method); a per-dataset figure is better suited to the supplementary material (already planned as SF01 in `FIGURE_SPECIFICATIONS.md`) than to the main-text Figure 5 slot, on page-efficiency grounds.

**Why not Option C (table instead of figure):** Table 6 already exists and reports the exact same numbers. A bar chart adds genuine value here specifically because a sorted, CI-annotated bar chart makes the ranking among 12 methods and the size of the gap between CombSUM/RRF and the graph-repair methods visually immediate in a way a 12-row table does not — this is the clearest single instance in the paper where a figure communicates the finding better than a table alone, which is why Figure 5 was planned in the first place. We keep Table 6 as the numerical source of record and add Figure 5 as its visual complement, consistent with how Figure 4 and Table 5 already coexist for the bootstrap comparison.

---

## Data provenance and integrity notes

- All 12 rows are the `scope=pooled` rows of `final_baseline_comparison.csv`, re-verified against the canonical file in this session (`grep '^pooled,' final_baseline_comparison.csv`) — not carried over from any earlier, possibly stale, extraction.
- **No illustrative or prototype values are used.** The previously existing `fig_mean_ndcg_hybrids.png` asset (see `FIGURE_STATUS_AUDIT.md`) is a real canonical figure but for a *different* comparison (the 4-method vote-suite hybrid family, not this 12-method pooled grid) and is not used as a source for any value in this package.
- Method names are neutral: the pooled-file's own internal label `proposed_hybrid` is renamed **"Repair-based hybrid (RRF, $\alpha=0.3$)"** and `best_stronger_repair` is renamed **"Exact-for-small-components hybrid"** in the plotting CSV, consistent with `main.tex`'s own established neutral terminology (see the footnote already attached to Table 6 explaining the `proposed_hybrid` label is inherited from the data file, not a claim of novelty). Neither method is labeled "ours" anywhere in the plotting package.
- **Regime-duplication handling:** the pooled corpus (`final_baseline_comparison.csv`) is already a single pooled aggregate across all datasets and regimes — there is no regime column to duplicate in this specific comparison (unlike Figure 4's per-regime breakdown). The `regime_or_pool` field is therefore uniformly `"pooled"` for all 12 rows, which is the correct, non-duplicated representation; no additional collapsing was needed here. (The regime-invariance caveat that matters for Figure 4/Table 5 does not apply to this pooled-file comparison, which was already computed once per method over the full corpus, not once per regime.)

## CI values (for the eventual plot's error bars; not part of the required CSV schema, provided here for completeness)

| Method | Mean nDCG | 95% CI |
|---|---|---|
| CombSUM | 0.4622 | $[0.4383, 0.4868]$ |
| Reciprocal rank fusion | 0.4587 | $[0.4345, 0.4831]$ |
| Prior only | 0.4571 | $[0.4333, 0.4817]$ |
| Repair-based hybrid (RRF, $\alpha=0.3$) | 0.4549 | $[0.4309, 0.4795]$ |
| Exact-for-small-components hybrid | 0.4549 | $[0.4309, 0.4794]$ |
| Borda-count fusion | 0.4393 | $[0.4155, 0.4632]$ |
| Copeland unrepaired | 0.4389 | $[0.4150, 0.4627]$ |
| Copeland repaired | 0.4387 | $[0.4147, 0.4628]$ |
| Markov repaired | 0.4350 | $[0.4111, 0.4584]$ |
| Markov unrepaired | 0.4344 | $[0.4100, 0.4577]$ |
| Balance hybrid | 0.4344 | $[0.4106, 0.4584]$ |
| Score-sum (graph) | 0.4334 | $[0.4097, 0.4573]$ |

---

## Axis and layout specification

- **Type:** Horizontal bar chart, sorted descending by mean nDCG (already reflected in `plot_order`).
- **$x$-axis:** Mean nDCG@$k$, with 95% CI whiskers (values above).
- **$y$-axis:** Method name (neutral labels as in the CSV/table above), ordered by `plot_order`.
- **Color:** Group visually by `graph_dependent` (e.g., one color for graph-independent methods: CombSUM, RRF, Prior only, Borda-count; another for graph-dependent methods: the remaining eight) so the central finding — the top three methods are all graph-independent — is visible at a glance without reading labels closely.
- **Annotation:** Optionally bracket the gap between CombSUM (top) and Copeland repaired (a natural point of reference given its role in Figure 4/Table 5), consistent with the gap already called out in Table 6's own caption in `main.tex`.
- **Size:** 1.5-column width (matches Table 6 and Figure 4's sizing conventions already used elsewhere in the manuscript).

## What must not appear in the image

- No method labeled "ours," "proposed," or "our method" (the neutral renamings above must be used verbatim).
- No p-values or significance stars beyond the CI whiskers themselves (consistent with the manuscript's stated preference for percentile CIs over significance stars, §4.5).
- No values from `fig_mean_ndcg_hybrids.png` (the stale 4-method vote-suite asset).
