# Repository Artifact Policy

**Audience:** contributors deciding what belongs in Git on this repository.
**Related:** `.gitignore`, `docs/REPRODUCTION_CANONICAL.md`, Outcome F package README under `reports/policy_selection_20260726T030500Z/`.

---

## Track in Git

- Library source under `src/` and experiment/driver scripts under `scripts/` that the branch intends to ship.
- Tests and small fixtures under `tests/`.
- Small **frozen evidence packages** that directly support a committed scientific or engineering claim (typically well under a few MB), including:
  - final human-readable `FINAL_REPORT.md` / README;
  - manifests, hashes, configuration snapshots;
  - lowest-level tables needed for independent recomputation (e.g. `gate_rows.json`);
  - reproduction scripts (`REPRODUCE.sh`).
- Documentation that describes **current** behaviour (or clearly dated historical archives under `docs/historical/`).

Canonical example on this branch: `reports/policy_selection_20260726T030500Z/`.

## Do **not** track

- Provider caches, raw API transcripts, or judgment stores that may contain prompts, completions, or credentials.
- Large datasets under `data/raw/` / `data/processed/` (already ignored where appropriate).
- Large anonymous supplementary bundles (e.g. `papers/**/anonymous_supplementary/`).
- Rendered manuscript page images / contact sheets from visual audits.
- Temporary, superseded, or repeated timestamped experiment directories that are not the frozen canonical package.
- Virtual environments, tool caches (`.venv`, `.mypy_cache`, `.ruff_cache`, `.pytest_cache`).
- Machine-absolute paths, PID locks, tmux logs, and local `STOP.sh` / `RESUME.sh` wrappers bound to one host.
- Checkpoints that can be regenerated and are not cited as frozen evidence.

## Decision checklist before `git add` on a report directory

1. Does a **committed claim** depend on it?
2. Can another machine **reproduce** or at least **recompute headlines** from the tracked lowest-level files?
3. Is it free of secrets, personal paths, and provider payloads?
4. Is it small enough for Git (prefer ≪ 10 MB; avoid hundreds of MB)?
5. Is it the **canonical** run, not a superseded timestamp?
6. Is it free of known broken metrics (if broken, keep local and document the defect)?

If any answer is no, keep the artifact local (or archive outside Git) and document the path in a report README instead of committing it.

## Examples on `fix/outcome-f-production-operating-point`

| Path | Policy |
|---|---|
| `reports/policy_selection_20260726T030500Z/` | **Track minimal set** (see package README: `gate_rows.json`, population, decision/summary, prose, `REPRODUCE.sh`). Calibrators/plots/replays stay local/gitignored. |
| `reports/policy_selection_20260726T025426Z/` | Keep local / ignore (superseded smoke) |
| `reports/real_query_policy_replay_20260726T042025Z/` | **Track** (already committed; offline replay) |
| `reports/real_query_multifactor_acquisition_20260726T044254Z/` | Keep local (broken `production_uht` metrics; absolute paths; large). See `docs/MULTIFACTOR_PRODUCTION_UHT_EVAL_INVALIDATION.md`. |
| `reports/real_query_multifactor_acquisition_corrected_*/` | Keep local full trees; may track a compact `CORRECTED_SUMMARY.json` / hashes only if frozen |
| `reports/adaptive_acquisition_*`, `prior_robust_*`, `reliability_aware_repair_*`, `linear_extension_extraction_*`, `multi_provider_llm_robustness_*` | Keep local until explicitly frozen |
| `reports/provider_capability_audit_*`, `counterfactual_cost_plan_*` | Keep local (may contain sanitized smoke evidence; do not commit raw responses) |
| `docs/benchmarks/COUNTERFACTUAL_PILOT_FREEZE_V1.md`, `configs/counterfactual_micro_pilot_v1.json` | Track freeze contracts; do not stage micro-pilot live outputs |
| `reports/final_revision_*`, `reports/final_revision_page_limit_freeze_*`, visual audits | Keep local (large / rendering scratch) |
| `papers/**/anonymous_supplementary/` | Outside Git (hundreds of MB) |
| Untracked Outcome B–D driver scripts under `scripts/run_*_experiment.py` | **Resolved:** canonical drivers live under `scripts/`; see `docs/experiments/OUTCOME_BCD_DRIVERS.md`. Report trees stay local until frozen. |
| `reports/cohere_normalization_diagnostic_20260727T183000Z/`, `reports/cohere_json_schema_confirmation_20260727T200000Z/`, `reports/cohere_native_v2_confirmation_20260727T210000Z/`, `reports/cohere_native_v2_schema_projection_confirmation_20260728T000000Z/`, `reports/cohere_native_v2_schema_projection_v2_confirmation_20260728T010224Z/`, `reports/cohere_native_v2_schema_projection_v3_confirmation_20260728T011703Z/` | **Track** (2026-07-28 classification). Each is a single sanitized confirmation/diagnostic record (`*_record.json` + `normalized_judgments.jsonl`, ~12KB each): request hashes, model/schema/protocol identity, token counts, parse outcome. Individually inspected — none contain raw prompt/completion text or credentials. Each is directly cited by exact `request_hash` in the already-committed `docs/benchmarks/COUNTERFACTUAL_PILOT_FREEZE_V1.md` findings 4–13 (which serves as the human-readable narrative/README for this evidence trail) and in `docs/handoff/state_snapshot.json`. The superseded ones (unprojected, v1-projection, v2-projection, both compat-path attempts) are kept deliberately, mirroring `cohere_schema_projection.py`'s own `SCHEMA_PROJECTION_PROTOCOL_VERSION_V1`/`_V2` named-historical-reference constants — they are the evidence that the fix was found through a live-evidence-driven sequential process, not guessed. |
| `reports/counterfactual_collector_canary_v1_20260727T145126Z/`, `reports/counterfactual_collector_canary_v2_20260727T161921Z/` | **Track** (2026-07-28 classification). 76–80KB each; contains a `FINAL_REPORT.md` (self-labeled "CANARY — INSTRUMENTATION ONLY", explicitly lists what it does not establish), request/reserve/trajectory ledgers, and a validation report — all doc-ID- and hash-keyed, no raw document or judgment text, no credentials. Directly cited (exact pass/fail counts per provider) in `PROJECT_STATUS.md`'s evidence registry. Do not merge either into `counterfactual_micro_pilot_v2` benchmark data — both remain canary/diagnostic-only regardless of being tracked in Git. |

## `.gitignore` posture

Prefer **narrow, named directory rules** for known local-only trees.
Do **not** add a blanket `reports/**` ignore: that would hide canonical frozen packages.
Do **not** ignore untracked source or tests merely because they are unfinished.
