# Multi-Provider Repair Pilot Smoke Artifacts

Status: smoke/status evidence, not canonical paper evidence.

Tracked files are limited to the human-readable smoke report, aggregate JSON,
provider usage/failure ledgers, and the estimate file:

- `SMOKE_TEST_REPORT.md`
- `ANALYSIS.json`
- `ESTIMATE_smoke.json`
- `provider_usage.jsonl`
- `provider_failures.jsonl`

Raw calls, parsed caches, checkpoints, and logs are ignored because the smoke
report already records the relevant pass/fail conclusion and provider identity.
Regenerating the smoke run requires live provider calls unless the local caches
are still present, so it still requires explicit user authorization before any
API call.
