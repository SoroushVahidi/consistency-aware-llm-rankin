# Stage 4A: Verification-Failure Remediation and Reproducibility Closure

## Scope note (read first)

The task brief for this stage referenced "the independent Stage 4
verification audit" and a "Stage 4 meta-audit report directory" containing
six specifically-named files. None of those six files exist anywhere in
this repository or its git history -- see `PRE_CORRECTION_MANIFEST.md`
Section 0 for the exhaustive search performed and the user's explicit
direction on how to proceed once this was surfaced. This stage therefore
treated the task brief's own itemized technical claims as the operative
findings, independently re-confirmed each by direct repository inspection
before acting, and recorded the missing meta-audit as a finding rather than
fabricating or assuming its contents.

This stage did not redesign the repository, begin paper writing, run new
scientific experiments, or make external API calls. No commit or push was
made; all changes are in the working tree for the user to review.

## What was found and fixed

1. **CI never installed the SCIP solver extra** (`.github/workflows/ci.yml`
   installed only `.[dev]`). Confirmed by direct inspection -- the fix
   `dependency_discrepancies.csv`/`workflow_command_inventory.csv` claimed
   had been made (via a promised `ci_validation_report.md`) had not
   actually happened. Fixed: added a required `tests-solver-enabled` job
   that installs `.[dev,exact]`, prints the installed PySCIPOpt and
   underlying SCIP versions, runs `make verify-env` (fails visibly on an
   unsupported solver version), and runs `make test-full` (fails on any
   nonzero skip count). See `reports/repo_reproducibility_stage4_20260730T031306Z/ci_validation_report.md`
   for full detail, including what was and was not validated locally vs.
   remotely.

2. **`verify_canonical_solver_version()`/`UnsupportedSolverVersionError` had
   zero test coverage.** Confirmed by grep. Fixed: added
   `tests/test_solver_version_gate.py` (14 tests) covering missing
   PySCIPOpt, missing version metadata, an explicit version mismatch, the
   documented `allow_mismatch` override, canonical-vs-exploratory-mode
   defaults, and the real installed `.venv` environment (skipped, not
   faked, when the `[exact]` extra is absent). All 14 pass locally.

3. **Three canonical report directories were untracked, though not
   `.gitignore`-blocked.** Confirmed via `git check-ignore -v` (no match)
   and `git status --ignored=matching` (no `!!` entries) for all six
   in-scope canonical packages. Fixed: staged the three that were
   untracked (`repo_reproducibility_stage4_20260730T031306Z`,
   `ir_evidence_audit_20260729T182949Z`,
   `ir_evidence_audit_review_20260729T235053Z`) via a narrow, targeted
   `git add` limited to those three directories only -- no `.gitignore`
   edit was needed since no ignore rule was blocking them. See
   `canonical_artifact_tracking_manifest.csv`.

4. **The real-LLM reproducibility manifest used a superseded, partial
   schema.** Confirmed: the committed `reproducibility_manifest.json`
   lacked `schema_version`, `git` metadata, `dependency_versions`,
   `solver_version`, `input_file_hashes`, and `output_file_hashes`, even
   though the generating script already called the full
   `collect_provenance()` implementation -- the committed artifact simply
   predated that wiring and was never regenerated. Fixed: regenerated the
   manifest in place (calling the same functions the script itself calls,
   not by re-running the full pipeline), verified all 7 sibling result
   files are byte-identical before/after, and documented a stable-vs-
   volatile field comparison policy so this is not miscategorized as "just
   a timestamp difference" in the future. See `manifest_comparison_policy.md`.

5. **Two Stage 4 deliverables referenced by name were missing.**
   `ci_validation_report.md` and `modified_files.csv` did not exist in
   `reports/repo_reproducibility_stage4_20260730T031306Z/` despite being
   referenced as if they did. Both created this stage from actual git
   evidence (diffs, `git status`, direct code inspection) -- not
   retrospectively fabricated results. See `deliverable_reconciliation.csv`
   for the full requested-vs-actual comparison, including the one stale
   row in `workflow_command_inventory.csv` (the `make secret-scan` row,
   now superseded by the script's actual presence).

6. **Test counts were reported inconsistently and one evergreen doc
   hard-coded a badly stale count.** Stage 4's own artifacts report 1272,
   1308, and 1285 passed at different points within the same stage
   (expected -- the suite grew during the stage); `docs/REPRODUCTION_CANONICAL.md`
   hard-coded "550 passed (as of this guide)", stale since 2026-07-14, and
   also omitted the `[exact]` extra needed for the SCIP-dependent results
   it documents. Fixed: corrected `docs/REPRODUCTION_CANONICAL.md` to
   install `.[dev,exact]` and to require `make test-full`'s "0 skipped"
   condition rather than a fixed pass count; left Stage 4's own historical
   counts unedited (they are point-in-time records, not evergreen claims).
   Authoritative count at the Stage 4A validation commit: **1315 passed,
   0 skipped** (full suite, `.venv`, including this stage's own 14 new
   solver-version-gate tests). See `test_count_normalization.md`.

## What was deliberately not touched

- The ~480-entry pre-existing staged diff from a prior session's Stage 1/2
  documentation reorganization (unrelated to this stage's remit).
- `src/consistency_ranker/baseline_ranking.py` and
  `src/consistency_ranker/statistical_inference.py` (pre-existing
  uncommitted changes from earlier work, out of this stage's scope).
- Any scientific result file's numeric content.
- Git history: no commit, amend, or push.

## File index for this stage's own deliverables

- `PRE_CORRECTION_MANIFEST.md` -- Section 1 of the task brief.
- `canonical_artifact_tracking_manifest.csv` -- Section 4.
- `manifest_comparison_policy.md` -- Section 5.
- `deliverable_reconciliation.csv` -- Section 6.
- `test_count_normalization.md` -- Section 7.
- This file -- overall summary.

Sections 2 and 3 of the task brief (the CI fix and the solver-version-gate
tests) produced their evidence directly in
`reports/repo_reproducibility_stage4_20260730T031306Z/ci_validation_report.md`
and `tests/test_solver_version_gate.py` respectively, rather than in this
directory, since they are retroactive completions of Stage 4's own
deliverables (see `deliverable_reconciliation.csv` for why).
