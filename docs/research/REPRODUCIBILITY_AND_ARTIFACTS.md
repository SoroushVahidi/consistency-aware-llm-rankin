# Reproducibility and Artifacts: Preserve vs. Repair Research Trajectory

*Companion to `docs/research/RESEARCH_TRAJECTORY.md`. Scoped to the
Gate-0 work added in this pass; see `docs/ARTIFACT_POLICY.md` for the
repository-wide artifact policy this document follows, and
`PROJECT_STATUS.md`'s "Evidence and artifact registry" for the
repository-wide list this document's entries should be cross-referenced
from.*

## Cached vs. newly generated data

**Nothing new was collected.** All numbers in this trajectory reuse data
already on disk before this pass began:
- `reports/candidate_pool_conditional_audit_20260714/tables/pool_robustness_paired_deltas.csv`
  — committed, 46,170 rows, produced 2026-07-14 by an earlier task, read
  but never written to by any code added in this pass.
- `outputs/learned_selector/`, `experiments/failure_class_audit_20260711_212157/`
  — pre-existing local artifacts, read (quoted in the trajectory doc) but
  not modified.
- `reports/policy_selection_20260726T030500Z/decision.json` — pre-existing
  committed evidence, read (its exact numbers re-quoted, not re-derived)
  but not modified.

**No live provider/API calls, no new LLM judgments, no network calls** were
made anywhere in this pass. Every script added
(`scripts/run_oracle_headroom_analysis.py`) reads local CSV files only —
verified by grep for `requests|urllib|socket|http.client|aiohttp` across
all new files (zero matches).

## Regenerated analysis outputs

`reports/oracle_headroom_gate0_20260728T230000Z/` — four subdirectories
(one per dataset: scidocs, fiqa, hotpotqa, bright), each containing
`REPORT.md`, `MANIFEST.json` (records the exact input CSV SHA-256, filter
parameters, and full numeric result), `label_sensitivity.json`,
`split_sizes.json`. Generated fresh by
`scripts/run_oracle_headroom_analysis.py` during this pass; reproducible
byte-for-byte from the committed input CSV with the documented seeds
(bootstrap seed 13, split seed 42) — verified by a dedicated test
(`tests/test_oracle_headroom.py::test_write_oracle_headroom_report_is_byte_identical_across_runs`).

## Immutable headline point estimates

No existing headline number anywhere in this repository (JDIQ manuscript
figures/tables, Outcome F decision numbers, the three prior informal
selector attempts' reports) was recomputed, modified, or superseded by
this pass. This pass only reads and re-quotes them (with citations) and
adds a new, clearly-separate Gate-0 analysis on a different slice of
already-existing data. If any number in `docs/research/*.md` disagrees
with its cited source file, the source file is authoritative — this is a
documentation bug to fix, not a re-derivation.

## Statistical interval policy (this trajectory's own work)

Per the same policy already established and fixed elsewhere on this
branch: any binary-outcome rate (e.g. `frac_benefit_from_repair`,
`frac_harmed_by_repair`, a future severe-harm rate for a preserve/repair
policy) MUST use `statistical_inference.proportion_interval` (Wilson by
default), never a nonparametric bootstrap directly on a 0/1 indicator,
which degenerates to a zero-width interval at 0/n or n/n. The
oracle-headroom gap itself is a *difference of means* (or, equivalently, a
mean regret), for which `bootstrap_mean_interval` remains the correct
tool — `oracle_headroom.compute_oracle_headroom` uses it correctly for
exactly this reason; do not "fix" that call to use `proportion_interval`,
which would be a category error (see `statistical_inference.py`'s own
docstring distinguishing the two).

## Run-status semantics

`oracle_headroom.evaluate_go_no_go` returns exactly one of three string
literals (`PROCEED_TO_LABELING`, `NO_HEADROOM_DO_NOT_LEARN`,
`AMBIGUOUS_NEED_MORE_DATA`) plus a human-readable `rationale` string
computed from the same numbers, not a separately-maintained explanation —
so the rationale cannot drift out of sync with the decision. This mirrors
the run-status discipline already established for the (separate)
active-acquisition pivot's stopping-rule pilot (explicit
`n_stopped`/`n_capped`/`n_failed` fields, never inferred only from prose).

## Branch and artifact provenance

- Branch: `fix/outcome-f-production-operating-point` (same branch as the
  JDIQ manuscript freeze and the separate active-acquisition pivot — see
  `PROJECT_STATUS.md` for the full commit lineage).
- This pass's commits (exact hashes recorded in the final report for this
  session, not duplicated here to avoid drift — see `git log`) touch only:
  new files under `src/consistency_ranker/repair_selector_mining/`
  (`oracle_headroom.py`, `label_generation.py`, `grouped_splits.py`),
  `scripts/run_oracle_headroom_analysis.py`, `tests/test_oracle_headroom.py`,
  `configs/preserve_repair_experiment_spec_v1.json`,
  `docs/research/*.md` (new directory), one new report directory
  (`reports/oracle_headroom_gate0_20260728T230000Z/`), and pointer updates
  to `PROJECT_STATUS.md`. No existing file's prior content was altered
  except to add a pointer/summary section.
- Artifact classification for `reports/oracle_headroom_gate0_20260728T230000Z/`:
  **track in full** per `docs/ARTIFACT_POLICY.md`'s checklist — a committed
  claim depends on it (this trajectory doc's §9/§10), it is small
  (~90KB), every number is independently recomputable from the already-
  committed input CSV plus the committed code, it is free of secrets (no
  provider payloads, no credentials — this analysis never touches provider
  data), and it is the canonical (only) run of this analysis, not a
  superseded timestamp.
