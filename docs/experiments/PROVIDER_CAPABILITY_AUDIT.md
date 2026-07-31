# Provider capability audit

Entry point: `scripts/audit_provider_capabilities.py`

Offline cost planner: `scripts/estimate_counterfactual_benchmark_cost.py`

Benchmark design (not executed here):
`docs/benchmarks/REAL_COUNTERFACTUAL_BENCHMARK_SPEC.md`

## Modes

Exactly one required:

- `--cache-only` — inventory only
- `--dry-run` — synthetic structured responses, zero network
- `--allow-provider-calls` — live, ledger-capped

Defaults refuse provider contact.

## Live caps

| Cap | Default |
|---|---|
| Total live calls | 16 |
| Per provider | 4 |
| Estimated USD | 2.00 (enforced only when costs are known) |
| Input tokens | 100000 |
| Output tokens | 12000 |
| Retries / request | 1 |

## Outputs (local / gitignored)

`reports/provider_capability_audit_<UTC>/` containing:

- `config.json`, `run_manifest.json`
- `capabilities.json`, `comparison.json`
- `judgments.jsonl` (normalized; response hashes only)
- `live_call_ledger.jsonl`
- `FINAL_REPORT.md`

Credential values, project IDs, and raw provider payloads are redacted or omitted.

## Scientific scope

Connectivity and instrumentation only. Not ranking-quality evidence.
Not Outcome F production evidence.
Does **not** establish calibration, determinism, or provider superiority.
Four providers do not automatically imply four fully independent model families;
exact backend revisions may be opaque.

## Provider identity fields

Record separately where known: provider, endpoint/deployment, underlying family,
exact model identifier, and version if exposed.
