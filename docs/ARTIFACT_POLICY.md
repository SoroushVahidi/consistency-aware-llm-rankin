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
| `reports/final_revision_*`, `reports/final_revision_page_limit_freeze_*`, visual audits | Keep local (large / rendering scratch) |
| `papers/**/anonymous_supplementary/` | Outside Git (hundreds of MB) |
| Untracked Outcome B–D driver scripts under `scripts/run_*_experiment.py` | **Resolved:** canonical drivers live under `scripts/`; see `docs/experiments/OUTCOME_BCD_DRIVERS.md`. Report trees stay local until frozen. |

## `.gitignore` posture

Prefer **narrow, named directory rules** for known local-only trees.
Do **not** add a blanket `reports/**` ignore: that would hide canonical frozen packages.
Do **not** ignore untracked source or tests merely because they are unfinished.
