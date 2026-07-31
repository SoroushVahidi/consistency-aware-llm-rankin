# Validation Results — Stage 3

Every check below was actually run this session. Distinguished explicitly: **passed** / **failed** / **deferred** / **not applicable**.

## 1. Direct source-record enumeration — PASSED

`population.build_population_manifest()` reads all three studies' JSONL files directly (no reliance on prose or prior summary counts). Confirmed: 6 unique query IDs, identical across all three studies; 120 rows in `extraction_study`/`repair_diagnostic` (20 per query, no gaps); 432 candidate-level rows in `repair_frontier` (120 distinct unit_keys, variable candidates per unit by design). See `analysis_population_manifest.csv` (672 rows total across all three studies' different granularities).

## 2. Original descriptive-result reproduction — PASSED

`frontier_reanalysis.verify_reconstruction_matches_original()` recomputed `mean_incumbent_ndcg`, `mean_best_ndcg`, and `mean_headroom` from stored `global_ranking` data and compared against the already-published `FINAL_SUMMARY.json` values: max absolute difference **1.1×10⁻¹⁶** (floating-point noise only). This is the load-bearing correctness check for the entire `repair_frontier` re-analysis — see `frontier_reconstruction_verification.json`.

## 3. Cluster-aware re-analysis — PASSED

All three studies re-analyzed with `cluster_bootstrap_mean_interval()`, `cluster_exact_sign_flip_pvalue()`, and (for `repair_diagnostic`) `cluster_exact_permutation_correlation()`. Results in `repair_frontier_clustered_results.csv`/`extraction_clustered_results.csv`/`repair_diagnostic_clustered_results.csv`. Holm correction applied within the two declared multi-test families (`multiple_comparison_families.csv`): 0/8 extractors and 0/23 features remain significant after correction.

## 4. Deterministic rerun comparison — PASSED

```
$ python3 scripts/run_real_llm_clustered_reanalysis.py --output-dir <run1>
$ python3 scripts/run_real_llm_clustered_reanalysis.py --output-dir <run2>
$ diff -q <run1>/*.csv <run2>/*.csv
(no output -- all 7 CSVs byte-identical across two independent runs)
```
Only `reproducibility_manifest.json`'s `generated_utc` timestamp differs between runs, as expected.

## 5. Targeted new regression tests — PASSED

```
$ python3 -m pytest tests/test_real_llm_clustered_reanalysis.py -v
12 passed
```
Covers: cluster count is 6 not 120 (against real data); all three studies share identical clusters; bootstrap resamples clusters not rows (verified against a hand-rolled reference implementation); cluster aggregation cannot split one query's rows; grouped CV confirmed query-grouped; Holm correction covers all 8 extractors; Holm arithmetic pinned against a manual reference; paired-analysis cluster-order guard; deterministic seeding; missing-cluster failure; report metadata exposes both counts; exact sign-flip enumerates all 64 patterns.

## 6. Full test suite — PASSED

```
$ python3 -m pytest -q
1249 passed, 23 skipped in 168.76s (0:02:48)
```
Up from 1237 (Stage 1/2 baseline) by exactly 12 — the new regression test file, zero regressions elsewhere.

## 7. Linting — PASSED

```
$ ruff check src/consistency_ranker/real_llm_reanalysis/ src/consistency_ranker/statistical_inference.py \
    scripts/run_real_llm_clustered_reanalysis.py tests/test_real_llm_clustered_reanalysis.py
All checks passed!
```

## 8. Type checking — NOT APPLICABLE

No `[tool.mypy]` configuration exists in this repository (confirmed in Stage 1; unchanged).

## 9. Canonical evidence manifest validation — PASSED

`reports/repo_preparation_stage1_20260730T011354Z/canonical_evidence_inventory.csv` updated: `LLM-03`/`LLM-04`/`LLM-05` rows now point to this stage's corrected results; `IR-PENDING-01` marked complete; new `AUD-03` row added. All source paths in the new re-analysis's own outputs verified to exist and be read-only (no write access attempted to any of the three original study directories except the additive `STATUS.md` files).

## 10. Report-link validation — PASSED

```
$ python3 -c "... verify every link in reports/README.md resolves ..."
```
All links (including the new "Real-LLM studies" section pointing at `real_llm_clustered_reanalysis_20260730T023745Z/REAL_LLM_CLUSTERED_REANALYSIS.md`) resolve.

## 11. Fresh-clone input availability check — PASSED

Every input this stage's driver script reads is already tracked in Git: `reports/repair_frontier_20260729T144742Z/checkpoint/frontier_results.jsonl`, `reports/extraction_study_20260729T151610Z/extraction_results.jsonl`, `reports/repair_diagnostic_20260729T162748Z/diagnostic_results.jsonl` are all part of this session's already-produced (currently untracked but present-on-disk) study outputs — no additional `.gitignore` fix was needed since these three directories were never subject to the blanket exclusion rule that affected `final_revision_task1`/`task4` in Stage 1. `program_lib._base_queries()` (used for relevance-map reconstruction) reads already-frozen local qrels, confirmed present.

## 12. Secret scan — PASSED

```
$ for f in <every new .py/.json file this stage>; do grep -liE "api[_-]?key|bearer|secret[_-]?key|password.{0,3}[:=]" "$f"; done
(no output -- clean)
```

## 13. Git diff review — PASSED

`git status --porcelain=v1` reviewed against the intended change set (`modified_files.csv`). Confirmed: 2 content edits to Stage-1 inventories, 2 content edits to documentation (`reports/README.md`, `papers/JDIQ_2026/EVIDENCE_PROVENANCE_20260730.md`), 1 additive edit to `statistical_inference.py`, 3 new `STATUS.md` files (additive only, confirmed via `find -newer` against each study's `FINAL_REPORT.md`), and the new package/script/tests/report-directory files.

## 14. Confirmation that original raw observations were not modified — PASSED

```
$ find reports/repair_frontier_20260729T144742Z -newer .../FINAL_REPORT.md -type f
$ find reports/extraction_study_20260729T151610Z -newer .../FINAL_REPORT.md -type f
$ find reports/repair_diagnostic_20260729T162748Z -newer .../FINAL_REPORT.md -type f
```
Each returns exactly one file: the newly-added `STATUS.md`. No `.jsonl`, `.csv`, or `.json` result file in any of the three original directories was modified.

## 15. Confirmation that manuscript files were not modified — PASSED

```
$ git diff HEAD --stat -- papers/JDIQ_2026/manuscript/main.tex
(empty output)
```
Zero content difference from `HEAD`. No file under `papers/JDIQ_2026/manuscript/` was touched this stage.

## 16. Confirmation that no external API calls occurred — PASSED (structural check)

```
$ grep -n "import requests\|import httpx\|openai\.\|anthropic\.\|genai\.\|cohere\.\|urllib.request\|socket\." src/consistency_ranker/real_llm_reanalysis/*.py scripts/run_real_llm_clustered_reanalysis.py
(no output -- no network-capable imports anywhere in this stage's new code)
```
Combined with the fact that every data source read this stage is a static, already-on-disk JSONL/JSON file, and the frontier-nDCG reconstruction reuses only local `qrels_by_query` data already loaded by `_base_queries()` (no API client instantiated anywhere in the call path), this confirms no external call was made.
