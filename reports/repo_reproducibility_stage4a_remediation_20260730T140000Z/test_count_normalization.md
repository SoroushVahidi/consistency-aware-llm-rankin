# Test-Count Normalization

## The problem

Stage 4's own artifacts report at least four different full-suite pass
counts, all produced within the same stage: **1272 passed**
(`solver_reproducibility_report.md`, `canonical_environment_specification.md`,
`dependency_discrepancies.csv`), **1308 passed**
(`workflow_command_inventory.csv`), and **1285 passed**
(`offline_reproduction_report.md`). Separately, `docs/REPRODUCTION_CANONICAL.md`
(an evergreen reproduction guide, not a dated stage report) hard-coded
**"550 passed (as of this guide)"** — a number roughly a third of any of
the Stage 4 counts and last true around 2026-07-14.

None of these numbers were wrong when written; the suite genuinely grows as
new studies and regression tests are added within the same working
session, so counts measured minutes apart can legitimately differ. The
defect is treating any single count as a durable fact worth hard-coding
into a document that outlives the session that measured it.

## What Stage 4A verified directly (authoritative as of this stage's validation)

Run in the repository's own `.venv` (PySCIPOpt 6.2.1 installed, matching
`CANONICAL_PYSCIPOPT_VERSION`):

| Command | Result |
|---|---|
| `.venv/bin/python -m pytest -q` (full suite, before adding this stage's own tests) | **1301 passed, 0 skipped** |
| `.venv/bin/python -m pytest tests/test_solver_version_gate.py -q` (new this stage) | **14 passed** |
| `.venv/bin/python -m pytest -q` (full suite, after adding this stage's own tests) | **1315 passed, 0 skipped** (1301 + 14, confirming the new file is additive and nothing else regressed) |
| `.venv/bin/python -m pytest tests/test_provenance.py -q` | **13 passed** (matches `provenance_metadata_schema.md`'s claim) |
| `make test-full` | **exits 0, "test-full: OK (0 skipped)"** |

**1315 passed, 0 skipped, 0 failed** is the count **at the Stage 4A
validation commit** (`8761004cb5749db515a5de9f7fc5fb14c7ee4de3`, plus this
stage's uncommitted working-tree changes) -- it is expected to change
again as soon as another test is added, and that is fine.

## Policy applied this stage

1. **Dated stage reports** (`reports/*/FINAL_REPORT.md`,
   `reports/repo_reproducibility_stage4_20260730T031306Z/*`, etc.) may
   continue to record the exact count observed at the time they were
   written -- these are historical logs of a specific measurement, not
   evergreen claims, and rewriting them after the fact would falsify the
   historical record rather than correct an error. None of Stage 4's four
   counts were edited by Stage 4A for this reason.
2. **Evergreen documentation** (guides intended to stay accurate
   indefinitely: `docs/REPRODUCTION_CANONICAL.md`, `README.md`,
   `docs/READ_ME_FIRST_FOR_AI.md`, `Makefile` help text) must not hard-code
   a single pass count. `docs/REPRODUCTION_CANONICAL.md:28` was the one
   violation found (`pytest -q  # expect: 550 passed (as of this guide)`,
   also missing the `[exact]` install extra needed for the SCIP-dependent
   results the guide covers) and was corrected this stage to:
   `make test-full  # expect: 0 skipped (fails otherwise)`, i.e. "run the
   suite and require zero failures / zero skips," per this stage's
   instructions, rather than a fixed number. `README.md`,
   `docs/READ_ME_FIRST_FOR_AI.md`, `PROJECT_STATUS.md`, and `Makefile` were
   grep-checked for a similar pattern (`\d+ passed`, `\d+ skipped`,
   `\d+ tests\b`) and contained none needing correction --
   `PROJECT_STATUS.md`'s two hits (1127/1038 passed) are dated session-log
   entries under the same "historical record, not evergreen claim" policy
   as (1) above, and `Makefile`'s `test-full` target already used dynamic
   wording ("test-full: OK (0 skipped)") rather than a hard-coded count.
3. **`make test-full`** (pre-existing, added in Stage 4, unmodified by
   Stage 4A) is the correct enforcement mechanism going forward: it fails
   the build on any nonzero skip count without needing a maintained
   expected total, which is exactly the "require zero failures" pattern
   this policy recommends over a hard-coded number.
