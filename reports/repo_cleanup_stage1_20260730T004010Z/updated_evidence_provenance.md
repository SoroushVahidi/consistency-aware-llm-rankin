# Evidence Provenance Update — Stage 1.6 Summary

**Full detail lives in `papers/JDIQ_2026/EVIDENCE_PROVENANCE_20260730.md`** (a new file in the manuscript workspace itself, since that is where `MASTER_EVIDENCE_INVENTORY.csv`/`SECTION_EVIDENCE_MAP.csv` — the two files it supersedes for lookups — already live, and where a future author will actually look). This file summarizes what changed and why.

## What was found

`papers/JDIQ_2026/MASTER_EVIDENCE_INVENTORY.csv` and `SECTION_EVIDENCE_MAP.csv` are dated 2026-07-12/14 and still list `outputs/pub_vote_cmp_all4/` as the canonical package in their own `canonical` column. `reports/full_calibrated_core/` (2026-07-15) — the pipeline that actually backs every number in `papers/JDIQ_2026/manuscript/main.tex` that this stage cross-checked — postdates both files by about three days and is mentioned in neither.

## What was changed (and what was not)

- **Not modified**: the two CSVs themselves, byte-for-byte. Historical provenance is preserved exactly as it was produced.
- **Modified**: `papers/JDIQ_2026/README.md`'s file-index table, marking both rows `STALE (2026-07-30)` with a pointer to the new file (see `modified_files.csv` for the exact diff description).
- **Modified**: `PROJECT_STATUS.md`'s documentation-authority map, adding a new row for evidence-to-claim mapping that points to the new file and explicitly demotes the two CSVs (kept, not deleted, marked superseded in place — same pattern `PROJECT_STATUS.md` already uses elsewhere for `papers/JDIQ_2026/PROJECT_STATUS_SUPERSEDED_20260712.md`).
- **New**: `papers/JDIQ_2026/EVIDENCE_PROVENANCE_20260730.md`, mapping six categories (historical pipeline / current classical-study canonical evidence / real-LLM exploratory studies / IR evidence audit / meta-audit / pending query-clustered re-analysis) each to source result file, generating script, and manuscript section, per the task brief's exact requirement.

## The "pending query-clustered re-analysis" is explicitly tracked, not silently dropped

Per the brief's requirement to cover this in the refreshed inventory: §5 of `EVIDENCE_PROVENANCE_20260730.md` states plainly that no canonical file yet implements the cluster-robust re-analysis the meta-audit recommends (`reports/ir_evidence_audit_review_20260729T235053Z/FINAL_META_AUDIT_REVIEW.md` §5-6), names the exact statistical gap (bootstrap CIs computed over 120 rows instead of 6 `query_id` clusters), and notes that `is_significant_pvalue()`/the existing `bootstrap_mean_interval()` machinery added/already present in `statistical_inference.py` this stage are available building blocks for whoever picks that work up — without this stage attempting the re-analysis itself (a statistics task, out of scope here).

## Every central manuscript claim maps to source → script → report → section

Confirmed directly in `EVIDENCE_PROVENANCE_20260730.md` §2 (the current canonical evidence table) — every row has all four columns filled in, cross-checked against `main.tex` line numbers where the claim is quoted (e.g. "CombSUM=0.554, RRF=0.546" → §4.2-4.3).
