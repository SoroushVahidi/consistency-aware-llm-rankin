# CANARY — INSTRUMENTATION ONLY

Mode: `cache_only`  |  Canary: `True`

## This report does NOT establish:

- provider superiority
- policy superiority
- noninferiority
- oracle opportunity
- production readiness
- statistical significance

## Summary

```json
{
  "mode": "cache_only",
  "queries_loaded": 1,
  "pool_sizes": {
    "scidocs:01273bd34dacfe9ef887b320f36934d2f9fa9b34": 10
  },
  "initial_request_count": 4,
  "reserved_followup_calls": 0,
  "reserve_scheduled": 0,
  "reserve_skipped": 4,
  "hard_max_live_calls": 4,
  "paid_api_calls": 0,
  "successful": 3,
  "failed_after_inference": 1,
  "failed_before_inference": 0,
  "call_accounting_note": "successful + failed_after_inference == total inference attempts (calls that reached, or tried to reach, a provider). failed_before_inference (missing credentials, or blocked by an already-exhausted cap) is the documented exception: those cells never attempted a provider call and, in live mode, do not consume network/billing exposure.",
  "failures": 0,
  "missing_cells": []
}
```

## Canary scope

This run is an instrumentation-only canary. It lacks the complete frozen presentation and repeat protocol of the micro-pilot and **must not** be merged into micro-pilot benchmark data.
