# Multi-Provider Repair Pilot — Smoke Test Report

**Directory:** `reports/multi_provider_repair_pilot_smoke_20260729T032209Z/`
**Config:** `configs/multi_provider_repair_pilot_v1.json` (smoke sub-block: 1 dataset, 1 query, pool_size=3)
**Command:** `.venv/bin/python scripts/run_multi_provider_repair_pilot.py --mode smoke --output-dir reports/multi_provider_repair_pilot_smoke_20260729T032209Z`

## Verdict: PASS (one interpreter defect found and fixed before the main pilot)

## What was exercised

- All 4 providers (Azure OpenAI gpt-4.1-mini, Vertex AI gemini-2.5-flash,
  Cohere command-r-plus-08-2024, Fireworks gpt-oss-120b) on the same
  1 query x 3-document pool (3 pairs x 2 debias directions = 6 calls each,
  24 calls total).
- Real API calls, response parsing, graph construction (per-provider +
  aggregate), MWFAS repair (greedy **and** exact/SCIP), nDCG evaluation,
  disk checkpointing, and resume behavior.

## Defect found and fixed

The **first** smoke run used the system default `python`, from an ambient
environment that did not have `pyscipopt` installed. All 24 live API calls
succeeded and were fully cached; graph
construction and the `greedy` repair for the first (dataset, query,
provider) unit completed; the run then crashed with `ModuleNotFoundError:
No module named 'pyscipopt'` when it reached the `exact` repair method.
`pyscipopt` **is** installed in the repository's own virtualenv
(`.venv/bin/python`, version 6.2.1, confirmed importable). Re-running the
identical command with `.venv/bin/python` resumed cleanly: 0 new API calls
(all 4 providers' judgments loaded from cache), and all 10 remaining
analysis units (5 graphs x 2 repair methods) completed instantly.

**Fix applied:** the main pilot tmux command explicitly uses
`.venv/bin/python`.

## Idempotency / resume verification (explicit, 3 runs)

| Run | New API calls | Units completed | Notes |
|---|---|---|---|
| 1 (`python`, wrong interpreter) | 24/24 (all providers succeeded) | 1/10 | Crashed on `exact` repair (pyscipopt missing) |
| 2 (`.venv/bin/python`) | **0** (all 4 providers loaded from cache) | 10/10 | Resumed cleanly, completed all remaining units |
| 3 (`.venv/bin/python`, repeat) | **0** | 10/10 (already complete) | Confirms full idempotency — no work repeated |

## Provider identity consistency

Each provider's `raw_calls/<provider>_calls.jsonl` contains exactly one
`provider` value and one `model` value across all records — no
cross-provider contamination:

| Provider | Model recorded |
|---|---|
| azure | `gpt-4.1-mini` |
| gemini | `gemini-2.5-flash` |
| cohere | `command-r-plus-08-2024` |
| fireworks | `accounts/fireworks/models/gpt-oss-120b` |

## Fireworks content check (explicit requirement)

All 6 Fireworks calls returned **non-empty, parseable** content, producing
valid `A`/`B` labels and consuming 52–98 of the 512-token budget (well within
budget, no `finish_reason="length"` empty-content failures). Full provider
responses are excluded from Git under the experiment-artifact policy.

## Graph / repair sanity check

Individual-provider graphs (3 pairs, transitive in this smoke sample) were
already acyclic (`is_dag_pre_repair=True`, `repair_activated=False`). The
**multi-provider aggregate graph** (union of all 4 providers' single votes)
became **cyclic** (`n_edges=4` vs. 3 for any single provider,
`is_dag_pre_repair=False`, `repair_activated=True`) — a clean, expected
illustration of aggregation-induced cyclicity on real LLM judgments, and
confirms `build_graph(aggregation="sum")` over the pooled per-provider
`Preference` lists behaves as intended.

## Analyze-mode check

`--mode analyze` ran end-to-end on the smoke output and produced a
well-formed `ANALYSIS.json` (query-level headroom = 0.0 for this
single-query, pool-size-3 sample, as expected — no repair-induced ranking
change occurred at this trivial scale). Confirms the full
estimate → run → analyze pipeline is wired correctly before spending the
larger main-pilot budget.

## Cost (smoke)

24 calls total, estimated **$0.004–$0.024** (rough, unverified against live
pricing — see `ESTIMATE_smoke.json`).
