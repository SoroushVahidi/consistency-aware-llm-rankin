# Solver Reproducibility Report (SCIP / PySCIPOpt)

## Access path

The repository uses SCIP exclusively **through PySCIPOpt** (`import pyscipopt; from pyscipopt import Model` in `src/consistency_ranker/mwfas_solver.py`), never a raw SCIP binary/CLI and never through another MILP wrapper (`highspy`, `pulp`, `mip` were evaluated and rejected in favor of PySCIPOpt per `reports/exact_open_source_ilp_repair_investigation/COMMANDS_EXECUTED.md:51-65`). A second, legacy backend (`gurobipy`) exists in the same module but is explicitly documented as "never required" (`docs/READ_ME_FIRST_FOR_AI.md`) and is not declared in `pyproject.toml`/`requirements.txt` at all.

## Which completed results depend on SCIP

- `reports/exact_open_source_ilp_repair_investigation/` (the primary exact-vs-greedy comparison; 1,025/1,025 nonempty graphs solved to proven optimality per `main.tex`).
- `reports/final_revision_task4_exact_baseline_fairness_20260715/` (larger-pool exact repair, 0/56 Holm-significant).
- `tests/test_exact_mwfas_scip.py` (16 tests).
- Indirectly, `scripts/run_ir_evidence_audit.py`'s `build_from_exact_ilp()`/`build_from_baseline_fairness()` sections of the IR evidence audit (Stage prior to this one), which read the already-computed CSVs from the two report directories above rather than re-invoking SCIP.

## Solver version originally used (recovered, not guessed)

**PySCIPOpt 6.2.1**, recovered from three independent sources this stage:
1. `reports/exact_open_source_ilp_repair_investigation/COMMANDS_EXECUTED.md:65`: `"pip install pyscipopt # installed PySCIPOpt-6.2.1 into .venv only"`.
2. `reports/reviewer_concerns_program_20260729T035320Z/ENVIRONMENT_pip_freeze.txt`: `PySCIPOpt==6.2.1`.
3. `reports/repair_frontier_20260729T144742Z/ENVIRONMENT_pip_freeze.txt`: `PySCIPOpt==6.2.1`.

This exactly matches `docs/REPRODUCTION_CANONICAL.md`'s existing narrative claim ("pyscipopt 6.2.1") — that claim is now independently confirmed from logs/metadata, not merely repeated.

## Is the repository's own `.venv` the environment these results were generated in?

**Yes, confirmed this stage.** `.venv/bin/pip freeze` shows `PySCIPOpt==6.2.1` exactly. Running the exact-repair test suite against `.venv` (`". venv/bin/python3 -m pytest tests/test_exact_mwfas_scip.py -v`) gives **16 passed, 0 skipped**. Running the **full** suite against `.venv` gives **1272 passed, 0 skipped** — compared to **1249 passed, 23 skipped** when accidentally run against an unrelated ambient environment (see `dependency_discrepancies.csv`'s environment-ambiguity row — this was discovered as a direct byproduct of this stage's audit, not assumed).

## Are exact-repair results invariant under the currently-installed version?

They are invariant **because** the currently-installed version (in `.venv`) is identical to the originally-used version (6.2.1), not because the code is version-insensitive in general. SCIP is a MILP solver; presolve, cut selection, and heuristic ordering can differ across versions in ways that do not affect *whether* a solution is proven optimal, but *can* affect *which* optimal solution is returned when multiple exist (a real risk here, since MWFAS ties are common on small graphs). This was **not** empirically re-tested against a different SCIP version this stage (would require installing a second, different PySCIPOpt version — a nontrivial, `.venv`-disrupting action outside this stage's "no new experiments" scope) — instead, the risk is documented and **guarded against structurally**: `verify_canonical_solver_version()` (see below) refuses to silently proceed with a mismatched version for canonical reproduction.

## Deterministic solver settings

Reviewed `src/consistency_ranker/mwfas_solver.py`'s SCIP invocation: `model.hideOutput()` (quiet mode, cosmetic only), `model.setParam("limits/time", ...)` (a time limit, which could in principle affect whether a *proof* of optimality is reached, but every tracked result reports `proven_optimal=True`, i.e. no run hit the time limit). No explicit thread-count parameter is set (SCIP defaults to single-threaded unless configured otherwise, which is deterministic); no explicit random-seed parameter is passed to SCIP itself (SCIP's internal tie-breaking can depend on its own default seed, which is a further reason version-pinning matters more than seed-pinning here). No custom presolve/heuristic/cutting-plane parameters are set beyond the time limit — the code relies on SCIP's shipped defaults for the pinned version.

## What was fixed this stage

1. `pyproject.toml`'s `[exact]` extra: `PySCIPOpt>=6.2.1` → `PySCIPOpt==6.2.1` (exact pin, with an explanatory comment).
2. `src/consistency_ranker/mwfas_solver.py`: added `CANONICAL_PYSCIPOPT_VERSION = "6.2.1"`, `UnsupportedSolverVersionError`, and `verify_canonical_solver_version(allow_mismatch=False)` — raises a clear, actionable error if PySCIPOpt is missing or version-mismatched, with a documented `allow_mismatch=True` override for exploratory (non-canonical-reproduction) use. Verified directly: raises under the ambient/wrong environment, returns `"6.2.1"` under `.venv`.
3. `requirements-lock.txt` (new, repo root): full `.venv` pip freeze, so a fresh clone can install the exact tested environment including the exact SCIP version, not just the floor.
4. This function is wired into the offline reproduction workflow (`offline_reproduction_report.md`) as its first solver-specific check.

## Documented override for exploratory use

`verify_canonical_solver_version(allow_mismatch=True)` is the sanctioned escape hatch — intended for a contributor experimenting with a newer SCIP release who understands their output may not byte-match the committed canonical CSVs. It is never called with `allow_mismatch=True` from any canonical workflow added this stage.
