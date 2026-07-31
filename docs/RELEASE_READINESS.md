# Release Readiness

This document is the reader-facing release checklist for the current branch.
It complements `PROJECT_STATUS.md` (scientific status), `docs/ARCHITECTURE.md`
(module/layer map), `docs/EXPERIMENTS.md` (experiment entry points), and
`docs/EXPERIMENT_ARTIFACT_POLICY.md` (what belongs in Git).

## Current Verdict Template

Use this classification before integrating the branch:

| Verdict | Meaning |
|---|---|
| Ready to merge | Clean install, documented smoke workflow, CI-equivalent checks, full exact-solver suite, evidence/link/secret/portability checks, and remote synchronization all pass. |
| Ready to merge with conditions | Checks pass, but a human should review scientific wording, branch scope, or external raw-cache archival policy before merging. |
| Not ready to merge | Any required check fails, the remote branch advanced incompatibly, raw provider content is staged, or an unresolved correctness issue is found. |

For this branch, the recommended path is **pull request with focused human
review**, even when all technical checks pass. The branch name still reflects
the original Outcome F production fix, but the branch now also contains
repository-hygiene, artifact-policy, architecture, and reproducibility work.
A direct fast-forward is technically possible only if `origin/main` remains an
ancestor; a PR is easier to review and rollback.

## CI Contract

| Check | Where it runs | What it guarantees | Notes |
|---|---|---|---|
| `python scripts/check_architecture_boundaries.py` | CI and `make check` | No circular subpackage dependency, including the former `multi_provider_eval` / `multifactor_acquisition` cycle. | Test imports are intentionally outside this layer graph. |
| `python scripts/check_active_portability.py` | CI and `make check-portability` | Active code/docs do not embed machine-specific workspace paths. | Historical reports may preserve original execution paths. |
| `pytest` without `.[exact]` | CI `tests` job and `make test` | Core tests pass in a basic developer install. | Solver-dependent tests may skip in this job. |
| `make verify-env` | CI solver job and local release gate | PySCIPOpt/SCIP exact-solver version matches the canonical result environment. | Requires `python -m pip install -e ".[dev,exact]"`. |
| `make test-full` | CI solver job and local release gate | Full suite passes with zero skips. | This is the pass/fail test contract for merging. |
| `make lint` | Local release gate | Ruff is clean on maintained readiness/provenance/reanalysis paths. | `make lint-full` exposes known historical full-repository Ruff debt; do not treat that debt as introduced by this branch. |
| `python scripts/validate_canonical_evidence_manifest.py` | Local release gate | Canonical evidence inventory points to existing tracked files. | Run through `make validate-evidence` or `make repo-ready`. |
| `python scripts/validate_report_links.py` | Local release gate | Report navigation markdown links resolve. | Run through `make doc-links` or `make repo-ready`. |
| `python scripts/run_secret_scan.py` | Local release gate | Tracked and staged files do not contain obvious secret-shaped values. | Does not inspect ignored raw provider caches. |
| `git diff --check` | Local release gate | No whitespace errors in the working diff. | Run before each commit and before push. |

## Local Release Gate

From a clean checkout of the branch:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e ".[dev,exact]"

python scripts/check_repo_ready.py
make verify-env
make OUTPUTS=/tmp/consistency_ranker_release_smoke synth-smoke
make repo-ready
make test-full
git diff --check
```

For the canonical offline reproduction workflows:

```bash
python scripts/run_offline_validation_workflow.py
```

This workflow writes only to temporary directories and compares deterministic
outputs against committed canonical reports.

## Dependency Notes

- Python `>=3.11` is supported; current local and CI verification uses Python
  3.12.
- The base install currently includes `sentence-transformers`, which pulls in
  PyTorch and can make clean installation large on Linux. This is expected for
  the current package layout; making dense/cross-encoder dependencies optional
  is a medium-term cleanup, not a release blocker.
- Exact MW-FAS validation requires `.[exact]`, which pins `PySCIPOpt==6.2.1`.
- Provider-backed workflows require `.[llm]`, configured credentials, and
  explicit call authorization. They are never part of the no-network release
  gate.
- IR dataset download/evaluation workflows require `.[ir]` and may need
  network access or local licensed data, depending on the collection.

## Integration Recommendation

Preferred:

```bash
git fetch origin
git status --short --branch
git rev-list --left-right --count origin/fix/outcome-f-production-operating-point...HEAD
git merge-base --is-ancestor origin/main HEAD
```

Then open a focused PR from
`fix/outcome-f-production-operating-point` into `main`. Ask reviewers to check:

- The null/negative repaired-versus-unrepaired claim framing.
- The Outcome F production guard and distinction from research gates.
- Raw provider-cache exclusion and external archival policy.
- The branch-scope mismatch caused by later repository-hygiene commits.

If maintainers choose a direct fast-forward after review:

```bash
git checkout main
git pull --ff-only origin main
git merge --ff-only origin/fix/outcome-f-production-operating-point
git push origin main
```

Do not rebase or force-push this branch as part of release preparation.
