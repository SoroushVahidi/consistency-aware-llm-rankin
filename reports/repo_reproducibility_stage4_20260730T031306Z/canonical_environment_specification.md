# Canonical Environment Specification

This document is the single authoritative description of "the environment this
repository's canonical results were produced in and are validated against." It
exists because this stage discovered that prior validation runs in this
session were silently executed against the wrong environment (see
`dependency_discrepancies.csv`'s environment-ambiguity row and
`solver_reproducibility_report.md`), producing 23 spurious test skips that were
never noticed as spurious.

## Two distinct specs, not one

| | Minimum-supported spec | Tested canonical spec |
|---|---|---|
| **Where declared** | `pyproject.toml` (`dependencies`, `[project.optional-dependencies]`) | `requirements-lock.txt` (repo root) |
| **What it means** | The loosest version bounds the code is written against | The exact package set + versions the currently-committed canonical results (`reports/`, `outputs/pub_vote_cmp_all4/`, etc.) were actually generated and re-verified against this stage |
| **Use it for** | Packaging, `pip install -e .`, contributor floors | Exact reproduction, debugging a discrepancy, CI |
| **Regenerate via** | Manual edits when a real floor changes | `.venv/bin/pip freeze --exclude-editable > requirements-lock.txt`, only after confirming `.venv` passes the full test suite |

Both files must be consulted together: `pyproject.toml` alone does not pin
enough to guarantee byte-identical reproduction (e.g. it does not pin
`numpy`/`scipy`/`torch`/`transformers` at all); `requirements-lock.txt` alone
does not communicate which floors are load-bearing versus incidental.

## Canonical values

- **Python**: 3.12.3 (`requires-python = ">=3.11"` in `pyproject.toml` is the
  floor; 3.12.3 is the exact version the repository's own `.venv` uses and the
  version every currently-committed canonical result was validated against
  this stage).
- **OS**: Linux (development/CI environment observed this stage: Linux
  6.17.0-35-generic). No macOS/Windows-specific canonical results exist.
- **Exact-repair solver**: PySCIPOpt `==6.2.1` exactly (see
  `solver_reproducibility_report.md` for full recovery/verification detail).
  Enforced at runtime by
  `consistency_ranker.mwfas_solver.verify_canonical_solver_version()`.
- **Legacy solver backend**: `gurobipy` (13.0.2 in `requirements-lock.txt`) is
  present in the tested environment but is **not** a project dependency in
  `pyproject.toml`/`requirements.txt` and is documented elsewhere
  (`docs/READ_ME_FIRST_FOR_AI.md`) as never required — its presence in
  `requirements-lock.txt` reflects what happened to be installed in `.venv`,
  not a canonical requirement. A contributor without a Gurobi license can
  ignore it entirely.
- **Package manager**: plain `pip` + `venv` (no `poetry`/`conda`/`uv` lock
  files exist in this repository).

## How to obtain the canonical environment

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-lock.txt
.venv/bin/pip install -e . --no-deps
```

`--no-deps` on the second install avoids re-resolving dependencies against
`pyproject.toml`'s looser floors after the exact lock file has already been
installed. For day-to-day development where exact byte-reproduction is not
required, `make setup` (installs `.[dev,exact]` against `requirements.txt`,
i.e. the minimum-supported spec) is sufficient and simpler.

## Verifying you have the canonical environment

```bash
make verify-env
```

Runs two checks: Python version (printed, not enforced by exit code — 3.11.x
is expected to also work per `pyproject.toml`'s floor, though only 3.12.3 has
been validated this stage) and `verify_canonical_solver_version()` (enforced —
raises `UnsupportedSolverVersionError` if PySCIPOpt is missing or
version-mismatched).

```bash
make test-full
```

Fails (nonzero exit) if any test is skipped. This is the strongest single
signal that the current environment matches what canonical results require:
0 skipped out of 1272 in the repository's own `.venv`, versus 23 skipped in
the ambient/unrelated environment this session initially and mistakenly used
for earlier validation runs.

## typecheck

No `mypy` (or other type checker) configuration exists anywhere in this
repository (`pyproject.toml` has no `[tool.mypy]` section; no `mypy.ini` or
`setup.cfg` exists). `make typecheck` is therefore a documented no-op, not an
oversight or a broken target — introducing type checking as a new gate is out
of scope for this stage (repository engineering/reproducibility hardening of
*existing* workflows, not a new tooling adoption decision).

## Known non-canonical environment (do not use for validation)

This session's shell previously ran commands against an ambient virtualenv
(referred to in this stage's artifacts as the "modal-venv") that lacks
`PySCIPOpt` and `gurobipy` entirely. It is not tracked anywhere in this
repository, is not `.venv/`, and should not be used to validate canonical
results — doing so silently skips all 16 exact-repair SCIP tests plus a
further 7 tests, producing a false impression of a fully-passing suite. Every
Makefile target in this repository invokes `$(VENV)/bin/python` /
`$(VENV)/bin/pytest` (defaulting `VENV := .venv`) specifically to prevent this
class of mistake going forward; do not run repository validation commands
with a bare `python3`/`pytest` from an arbitrary shell environment.
