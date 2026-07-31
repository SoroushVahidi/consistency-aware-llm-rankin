# Multifactor production_uht evaluation invalidation

**Date:** 2026-07-26

**Branch:** `fix/outcome-f-production-operating-point`

**Safety tag/branch:** `backup/pre-multifactor-eval-fix-20260726`

## Invalid report (keep local; do not cite)

| Field | Value |
|---|---|
| Path | `reports/real_query_multifactor_acquisition_20260726T044254Z/` |
| Status | **Scientifically invalid for production_uht ranking quality** |
| Git | Ignored via `.gitignore` (`reports/real_query_multifactor_acquisition_*/`) — remain on disk for provenance |

### Why it is invalid

1. **Empty nDCG on all ~720 `production_uht` rows.** The harness discarded the qrels-based `eval_ranking` outcome and wrote `prod.outcome` instead. That outcome has no `extra["ndcg_at_k"]`, so `CELL_SUMMARY.csv` stored blank nDCG.
2. **`topk_jaccard ≡ 1.0` for every `production_uht` row.** `true_ranking` was set to `ranking_from_prior(prior)`, and `run_production_uht` scored Jaccard against that prior. Prior agreement was mislabeled as quality.
3. **Safety-floor metadata was not execution-complete.** Designed outsider-probe pairs often missed the shared cache; the probe did not fall back to the full insider–outsider frontier. Across 720 rows, `outsider_probe_executed` and `final_challenger_executed` were always false in the invalid report — configuration was recorded, not validated execution.
4. **Verdict logic was CHALLENGER-only** (`NO CURRENT CRITERION BEATS ALWAYS-UHT`), ignoring HYBRID / ROBUST_COMBINED and conflating utility/call savings with ranking quality.

Affected claims: any statement that the multifactor package validated production-UHT nDCG, safety-floor execution, or a deployable criterion against always-UHT.

## Replacement (corrected offline replay)

| Field | Value |
|---|---|
| Generator | `scripts/reevaluate_multifactor_offline.py` |
| Path | `reports/real_query_multifactor_acquisition_corrected_20260727T030457Z/` |
| Compact summary (trackable) | `docs/multifactor_production_uht_corrected_summary_20260727.json` |
| Mode | Cache-only production path + re-score of live `POLICY_TRACES`; **zero paid API calls** |
| Evaluation | Shared qrels contract in `multifactor_acquisition/evaluation_contract.py` |
| Prior agreement | `prior_kendall_tau` (informative); `prior_topk_jaccard` is full-pool membership when `k == pool_size` and is marked uninformative |

Full corrected timestamped trees stay local per `docs/ARTIFACT_POLICY.md`.

### Policy name glossary

| Serialized id | Meaning |
|---|---|
| `production_uht` | `run_production_uht` with safety floor (comparison baseline) |
| `plain_uht` | Named UHT engine without production safeguards |
| `UHT` | Factorial acquisition arm after the shared mixed diagnostic probe |

## What remains valid from the old report

- Factorial coverage geometry (queries × providers × prompts × orientations × budgets).
- Cached `PARSED_JUDGMENTS.jsonl` / spend ledger as raw evidence of provider calls already paid.
- Non-`production_uht` policy nDCG columns that were computed via `eval_ranking(..., qrels=...)` (still re-checked under the corrected contract offline).
- The interim **always-UHT production default** decision from Outcome F (synthetic) — multifactor does not overturn it unless the corrected comparison shows a matched-nDCG win.

## Reproduction

```bash
source .venv/bin/activate
PYTHONPATH=src python scripts/reevaluate_multifactor_offline.py \
  --source-dir reports/real_query_multifactor_acquisition_20260726T044254Z \
  --output-dir reports/real_query_multifactor_acquisition_corrected_$(date -u +%Y%m%dT%H%M%SZ)
```
