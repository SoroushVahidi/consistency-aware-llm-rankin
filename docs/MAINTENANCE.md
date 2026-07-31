# Maintenance

Compact reference for recurring maintenance concerns. Most of these are
already covered in depth elsewhere — this file exists for the two angles
that weren't (periodic-check cadence, document ownership) and links out
for everything else rather than duplicating it.

## Canonical validation commands

See `docs/EXPERIMENTS.md` "Cloud Validation" — `scripts/run_cloud_validation.py`
`--tier core`/`--tier solver`. Not repeated here.

## Periodic checks

No fixed schedule is enforced (this is a research repository, not a
production service) — but the following should be re-run whenever their
trigger condition occurs, not left to drift:

| Check | Trigger | Command |
|---|---|---|
| Full cloud validation | Before any merge to `main`; before any release | `python scripts/run_cloud_validation.py --tier core` / `--tier solver` |
| Fresh-checkout reproducibility | After any change to `.gitignore`, `pyproject.toml`, or `tests/conftest.py` | `python scripts/run_cloud_validation.py --tier all` from a genuinely fresh clone |
| Claim registry consistency | After any change to `docs/claim_evidence_registry.yaml` or a canonical evidence path | `python scripts/validate_claim_evidence_registry.py` |
| Repository clarity | After any change to a document in `docs/PROJECT_STATUS.md`'s authority-hierarchy table | `python scripts/validate_repo_clarity.py` |
| GitHub Actions billing status | Periodically, until resolved | `gh run list --limit 5` — look for a real (non-billing-aborted) run |
| Open issue accuracy | When closing/updating any tracked item | Cross-check against `docs/PROJECT_STATUS.md`'s "Prioritized remaining work" |

## Version-sensitive dependencies

- **PySCIPOpt** is pinned to exactly `6.2.1` in `pyproject.toml`'s `exact`
  extra, and `mwfas_solver.verify_canonical_solver_version()` enforces this
  at runtime for canonical reproduction — see `docs/REPRODUCTION_CANONICAL.md`.
  A newer SCIP version may return a different (still optimal) solution when
  ties exist, which would not byte-match committed canonical output.
- **Gurobi** has no version pin (it's an optional, never-required backend);
  `reports/gurobi_vs_scip_solver_cross_validation_20260731T162314Z/` records
  the exact version (13.0.2) used for the one validation that exists.
- **`requirements-lock.txt`** is a full pip-freeze snapshot of a
  known-good environment (not a canonical requirement) — see its own header
  comment for regeneration instructions.

## Raw-cache / dataset handling

See `docs/EXPERIMENT_ARTIFACT_POLICY.md` (raw provider transcripts) and
`docs/EXPERIMENTS.md` "Test Tiers" (BEIR/HotpotQA/BRIGHT datasets,
`data/raw/`/`data/processed/`). Not repeated here.

## Archival expectations

See `docs/ARTIFACT_POLICY.md` "External Archive Procedure" and issue #46
(no destination currently configured). Not repeated here.

## GitHub Actions limitation

See `docs/PROJECT_STATUS.md` "Verified state" and issue #45. Not repeated
here.

## Release cadence

None assumed. This repository does not follow a fixed release schedule —
see `docs/RELEASE_CHECKLIST.md` for the conditions that would trigger a
release decision (none currently met; no release exists as of `d613d3e`).

## Ownership of canonical documents

No per-document owner is tracked by name (this is a small, single-maintainer
research repository as of this writing) — but each canonical document has a
clear *scope* owner by convention, meaning: whoever last substantively
edited it is expected to have verified its claims against current code/data
at that time, and any future edit should do the same rather than assume the
existing content is still accurate.

| Document | What "keeping it current" means |
|---|---|
| `docs/CONTRIBUTIONS.md` | Re-verify each contribution's status against `main.tex` and tests when either changes |
| `docs/PROJECT_STATUS.md` | Update the subsystem table and "Exact next action" whenever a tracked item's state changes |
| `docs/claim_evidence_registry.yaml` | Add/update a claim whenever a canonical or internal-validation result is produced; run the validator |
| `docs/EXPERIMENTS.md` | Add a family row whenever a new experiment directory becomes canonical, exploratory, or internal-validation |
| `docs/AGENT_GUIDE.md` | Update when the validation/workflow commands themselves change, not when their *results* change |

If you substantively edit one of these, you have implicitly taken on this
responsibility for that edit — re-verify, don't just append.
