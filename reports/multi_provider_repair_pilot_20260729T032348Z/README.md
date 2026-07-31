# Multi-Provider Repair Pilot Artifacts

Status: exploratory source evidence for the real-LLM repair studies.

This directory contains compact, tracked evidence from the 2026-07-29
multi-provider pilot:

- `ANALYSIS.json`
- `ESTIMATE_main.json`
- `PROVIDER_MODELS.json`
- `checkpoint/`
- `cache/*/llm_pairwise_judgments.jsonl`
- `provider_usage.jsonl`
- `provider_failures.jsonl`

The tracked `cache/*/llm_pairwise_judgments.jsonl` files contain parsed
judgments used by downstream analysis. Raw request/response transcripts under
`raw_calls/` and transient logs under `logs/` are intentionally excluded from
Git by narrow `.gitignore` rules. They were preserved in a local byte-for-byte
archive during the 2026-07-31 content cleanup and should be stored externally
under a restricted archival policy if exact provider transcripts are needed.

Regenerating this directory from scratch requires live provider calls and
therefore explicit user authorization with a provider/query/call ceiling.
