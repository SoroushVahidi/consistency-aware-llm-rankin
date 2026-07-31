<!--
Keep this concise. "N/A" is a valid answer for any section that doesn't
apply to this change (e.g. a typo-fix PR doesn't need a cloud-validation
run) -- do not pad irrelevant sections just to fill them in.
-->

## Purpose

<!-- What does this PR do, and why? -->

## Scope

<!-- Files/subsystems touched. Keep PRs focused -- split unrelated changes. -->

## Scientific classification

- [ ] This PR does not change any scientific claim or result.
- [ ] This PR affects a claim in `docs/claim_evidence_registry.yaml` (list claim ID(s) below) -- I updated the registry and it still validates (`python scripts/validate_claim_evidence_registry.py`).
- [ ] This PR affects `docs/CONTRIBUTIONS.md` and I updated it.

Affected claim ID(s) / canonical evidence path(s):

## Validation

- [ ] Focused tests pass for the changed code (`pytest -q <path>`).
- [ ] `python scripts/run_cloud_validation.py --tier core` run and passed, **or** not applicable (state why):
- [ ] `python scripts/run_cloud_validation.py --tier solver` run and passed, **or** not applicable:
- [ ] This PR touches dataset loaders / candidate-pool construction and I also ran the `real_data` tier, **or** not applicable.
- [ ] This PR touches a solver backend (SCIP/Gurobi) and I confirmed both still agree, **or** not applicable.
- [ ] Any job expected to exceed ~5 minutes was run under tmux (descriptive, timestamped session name; logged output; captured exit code).

## Documentation

- [ ] `docs/PROJECT_STATUS.md` updated if this PR changes completion state of a tracked item.
- [ ] Relevant GitHub issue updated/linked if this closes or affects one.
- [ ] `docs/EXPERIMENTS.md` updated if this adds/changes an experiment family.

## Artifact policy

- [ ] No raw LLM provider transcript committed (`docs/EXPERIMENT_ARTIFACT_POLICY.md`).
- [ ] No Gurobi license file or WLS credential value committed.
- [ ] No generated dataset (`data/raw/`, `data/processed/`) committed.
- [ ] No machine-specific local path introduced (`python scripts/check_active_portability.py` passes).
- [ ] `python scripts/run_secret_scan.py` passes.

## Manuscript impact

- [ ] No manuscript impact.
- [ ] This PR affects `papers/JDIQ_2026/manuscript/main.tex` -- see `docs/AGENT_GUIDE.md` section 9 for the inclusion decision rule (never a commercial-solver or non-public identity-linked result in double-blind material).

## Backward compatibility

- [ ] No breaking change to a public script/module interface.
- [ ] Breaking change (describe migration path below).

## Acceptance criteria

<!-- What does "done" mean for this specific PR? -->
