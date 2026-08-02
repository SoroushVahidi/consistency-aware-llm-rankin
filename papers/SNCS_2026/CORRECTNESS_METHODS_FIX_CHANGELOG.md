# Correctness / Methods Fix Changelog (post-independent review)

**Branch:** `papers/sncs-2026-foundation`  
**Date:** 2026-08-01  
**Scope:** Factual contradictions and methodological reproducibility only.
No new experiments (beyond reading canonical CSVs / one empty-graph
verification), no new scientific claims, no figure redesign, no PR/tag/DOI.

## Discrepancy resolutions

### A. SciDocs 10.8% vs 11.7%

| Quantity | Value | Source |
|---|---|---|
| `ms1` cyclic after mutual (diagnostic) | 10.8% = 13/120 | `table_primary_graph_structure.csv` column `cyclic_query_pct_after_mutual_deletion` |
| `ms1_drop_mutual` cyclic | 11.7% = 14/120 | same CSV, `cyclic_query_pct` |

**Cause:** Not stale rounding. Two different operations on related but
non-identical graphs:

1. **Post-mutual diagnostic** (`mutual_removed_stats`): take the already
   aggregated `ms1` digraph and delete every reciprocal edge pair
   (`full_calibration_utils.py`, mutual-removed copy).
2. **`ms1_drop_mutual` construction**: drop contested pairs during vote
   construction (`drop_mutual=True` in `_vote_rows_from_direction_maps`)
   and apply a **regime-specific** retention-matched aggregate threshold
   (SciDocs: agg=0 for drop_mutual vs 0.01076 for `ms1`).

They coincide on FiQA / HotpotQA / BRIGHT but **not** SciDocs. The single
disagreeing query is `19115f66f6ac1c02568bbb38eceedfa3521a8cc2`
(`ms1` after-mutual acyclic; `ms1_drop_mutual` still cyclic, largest SCC 3).

**Manuscript action:** Removed the false “matches exactly … every dataset”
claim; stated the relationship explicitly; corrected the structural-figure
caption (diagnostic is post-aggregation, not “before aggregation”).
Table numeric cells were already correct and were **not** forced to agree.

### B. 1,025 vs 1,026 exact solves

Nominal combinations: 120+120+52+50 = 342 queries × 3 regimes = **1,026**.
Canonical `structural_per_query.csv` / `ilp_solver_status_per_query.csv`
have **1,025** rows, all proven optimal.

**Missing instance:** BRIGHT / `ms2` / `biology:0`.

**Reason:** Under `ms2` (min_support=2), that query’s vote rows are empty
(`raw_edges=[]`, `n_edges=0` in
`protocol_runs/.../bright/ms2/query_records.jsonl`). The exact study skips
`if not artifacts["rows"]: continue`
(`run_exact_open_ilp_study.py`). Nodes exist (20 candidates); no directed
pair meets two-ranker support.

**Manuscript action:** Explain 1,026→1,025 wherever 1,025 is reported;
keep 1,025/1,025 as the correct denominator for solved instances.

## Other methodology clarifications

- Acyclicity vs transitivity wording (Related Work + Background).
- MWFAS ≡ linear-ordering / backward-edge objective (cite existing refs).
- Retention-matched threshold table (`tab:thresholds`) with scope and rule.
- Extraction-parameter table (`tab:extraction-params`) matching code
  (including hybrid `h = prior̂ + α·grapĥ` with RRF prior, not `(1-α)p+αg`).
- Min–max zero-range → all zeros; missing scores excluded from range.
- Holm-family definition table (`tab:holm-families`).
- Softened “effectively tied”, over-strong “rules out”, Conclusion
  preserves limited equivalence + small effects possible.

## Final compile

- Toolchain: staged build + `tectonic -X compile main.tex`
- Pages: **40**
- Abstract word count: **247**
- PDF SHA-256: `8b73d4094a971aca868c3ebb42ce7211c22bdb14033cb4876f7bd5b18f31c382`

## Files touched

- `papers/SNCS_2026/manuscript/main.tex` (+ regenerated `main.pdf`)
- `papers/SNCS_2026/EVIDENCE_MAP.md`
- `papers/SNCS_2026/RESULTS_CROSS_CHECK.md`
- `papers/SNCS_2026/result_claims.yaml`
- this changelog
