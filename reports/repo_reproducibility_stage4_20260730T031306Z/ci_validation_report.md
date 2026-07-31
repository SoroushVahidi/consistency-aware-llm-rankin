# CI Validation Report

## Provenance note (important)

This file did not exist when Stage 4 (this directory) was originally
produced, even though `dependency_discrepancies.csv` and
`workflow_command_inventory.csv` both reference it as if it already existed
("See `ci_validation_report.md` -- added a second CI step/job installing
`.[exact]`..."). Direct inspection of `.github/workflows/ci.yml` at the
start of Stage 4A confirmed the referenced fix had **not** actually been
made: the workflow still had a single `tests` job installing only
`.[dev]`, exactly as it did before Stage 4. This is exactly the kind of
claimed-vs-actual discrepancy Stage 4A exists to correct. This file is
written by Stage 4A, using Stage 4A's own changes (not retroactively
describing work Stage 4 never did).

## What was wrong (confirmed by direct inspection)

`.github/workflows/ci.yml`'s only job (`tests`) ran:
```
pip install -r requirements.txt
pip install -e ".[dev]"
pytest
```
`.[dev]` does not include the `[exact]` extra (`PySCIPOpt==6.2.1`), so every
SCIP-gated test in the repository skipped silently on every CI run to date.
This is not limited to the 16 tests in `tests/test_exact_mwfas_scip.py` --
`tests/test_mwfas_solver.py`, `tests/test_repair_frontier.py`, and
`tests/test_task4_exact_baseline_fairness.py` also contain
`@pytest.mark.skipif(not is_scip_available(), ...)`-gated tests. The exact
skip count under a clean `.[dev]`-only install was not re-measured this
stage (doing so would require either a second, from-scratch venv or
temporarily removing PySCIPOpt from the repository's own `.venv`, both
avoided to keep this stage's local validation non-destructive to the
existing environment) -- but the CI fix below does not depend on knowing
that number in advance, since `make test-full` fails on *any* nonzero skip
count regardless of which tests produced it.

## What Stage 4A changed

`.github/workflows/ci.yml` now defines two jobs:

1. **`tests`** (unchanged install behavior: `.[dev]` only) -- kept as a
   fast, lightweight job. Its job-level comment now states explicitly that
   solver tests are *expected* to skip here and that this job's skip count
   must not be read as "everything ran."
2. **`tests-solver-enabled`** (new, required) --
   - Installs `.[dev,exact]` (so `PySCIPOpt==6.2.1` is present).
   - Runs a step that imports `pyscipopt` and prints both
     `pyscipopt.__version__` (the wrapper version) and
     `pyscipopt.Model().version()` (the underlying SCIP version) --
     satisfying the "clearly reports installed SCIP and PySCIPOpt versions"
     requirement.
   - Runs `make verify-env`, which calls
     `verify_canonical_solver_version()` with its default
     `allow_mismatch=False`. This raises `UnsupportedSolverVersionError`
     (and therefore fails the step, and the job) if the installed
     PySCIPOpt is missing or does not exactly match
     `CANONICAL_PYSCIPOPT_VERSION` ("6.2.1") -- i.e. an unsupported solver
     version now fails the build visibly, not silently.
   - Runs `make test-full`, which fails the build if `pytest -q`'s summary
     line reports any nonzero skip count. This is the mechanism that
     guarantees the solver-enabled job cannot silently accumulate skips
     (solver-related or otherwise) into a general "some tests skipped, no
     one noticed" state.

`Makefile`'s `verify-env` target was also extended this stage to print the
underlying SCIP version (`pyscipopt.Model().version()`) in addition to the
PySCIPOpt wrapper version it already printed, so a contributor running
`make verify-env` locally sees the same two version strings CI reports.

## Local validation performed this stage (what was and was not run)

| Check | Method | Result |
|---|---|---|
| YAML syntax validity of the edited `.github/workflows/ci.yml` | `yaml.safe_load()` in `.venv` | Parses without error; two jobs (`tests`, `tests-solver-enabled`) present |
| `python -c "import pyscipopt; ..."` version-report step | Run directly in `.venv` (which has PySCIPOpt 6.2.1 installed, matching the canonical pin) | `PySCIPOpt version: 6.2.1`; `Underlying SCIP version: 10.0` |
| `make verify-env` | Run directly in `.venv` | Prints Python 3.12.3, `PySCIPOpt 6.2.1`, `SCIP (underlying) 10.0`; exits 0 (`verify-env: OK`) |
| `make test-full` | Run directly in `.venv` | See result recorded in `reports/repo_reproducibility_stage4a_remediation_20260730T140000Z/test_count_normalization.md` |

**What was not run: actual GitHub-hosted execution of either CI job.**
This stage validated the workflow's YAML and the exact shell commands it
invokes, run locally against the repository's own `.venv` (which mirrors
the `tests-solver-enabled` job's intended installed state, since it already
has `.[dev,exact]` installed). It did **not** push to GitHub or trigger an
Actions run, and this report does not claim GitHub-hosted execution
occurred. **Remote execution on GitHub Actions remains pending** the next
push/PR against this branch; a human reviewer should confirm the
`tests-solver-enabled` job actually appears and passes in the Actions tab
before treating this CI gap as fully closed end-to-end.

## Why a from-scratch `.[dev]`-only re-run was not performed locally

Reproducing the `tests` job's exact install sequence
(`pip install -r requirements.txt && pip install -e ".[dev]"`) from a truly
clean environment would require either network access to PyPI in a fresh
virtualenv (parallel, disposable environment) or mutating the repository's
own `.venv` by uninstalling PySCIPOpt from it -- the latter risks leaving
the shared canonical environment in a different state than every other
Stage 4/4A check assumes. Neither was done. The commands themselves
(`pip install -r requirements.txt`, `pip install -e ".[dev]"`, `pytest`)
are unchanged from the pre-existing `tests` job and were not modified by
this stage, so their correctness is inherited from prior CI runs of the
same commands, not re-validated here.
