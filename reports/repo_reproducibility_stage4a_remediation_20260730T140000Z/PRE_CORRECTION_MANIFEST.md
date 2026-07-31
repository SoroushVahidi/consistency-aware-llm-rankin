# Stage 4A Pre-Correction Manifest

Recorded before any Stage 4A file modification began.

## 0. Governing-evidence discrepancy (must be recorded before anything else)

The Stage 4A task brief instructed use of "the Stage 4 meta-audit report
directory" and named six specific files it should contain:
`claim_verification_matrix.csv`, `newly_discovered_issues.csv`,
`ci_coverage_review.csv`, `documentation_accuracy_review.csv`,
`fresh_clone_verification.md`, `test_quality_review.md`. An exhaustive
search (`find` across the entire working tree, `grep -rn` across all
`*.md`/`*.csv` files, and `git log --all --oneline` for any commit
mentioning these names or "meta-audit"/"verification audit") found **none
of these six files anywhere in the repository or its git history, under
any name.** The only directory matching the brief's other named path,
`reports/repo_reproducibility_stage4_20260730T031306Z/`, exists but
contains a different 8-file set (`canonical_environment_specification.md`,
`canonical_output_protection_report.md`, `dependency_discrepancies.csv`,
`environment_dependency_inventory.csv`, `offline_reproduction_report.md`,
`provenance_metadata_schema.md`, `solver_reproducibility_report.md`,
`workflow_command_inventory.csv`).

The repository does contain an actual, independent meta-audit --
`reports/ir_evidence_audit_review_20260729T235053Z/FINAL_META_AUDIT_REVIEW.md`
-- but it audits a different, earlier artifact (the IR evidence audit,
`reports/ir_evidence_audit_20260729T182949Z/`), not Stage 4's
reproducibility-hardening work, and does not contain a claim-verification
matrix, CI-coverage review, or fresh-clone verification of Stage 4's
claims.

This was surfaced to the user directly before any corrective work began.
The user selected: **treat the Stage 4A task brief's own itemized technical
claims (SCIP CI gap, missing solver-version tests, ad-hoc manifest schema,
missing `ci_validation_report.md`/`modified_files.csv`, etc.) as the
operative "verified discrepancies," confirm each by direct repository
inspection, and record the missing meta-audit directory as a finding** --
which is what this manifest and the rest of Stage 4A's output do. Every
claim acted on below was independently re-confirmed against the actual
repository state before any fix was applied (see the per-section evidence
in `deliverable_reconciliation.csv` and `canonical_artifact_tracking_manifest.csv`).

## 1. Branch and commit

- Branch: `fix/outcome-f-production-operating-point`
- HEAD commit: `8761004cb5749db515a5de9f7fc5fb14c7ee4de3`
- Tracking `origin/fix/outcome-f-production-operating-point`, up to date at session start.

## 2. Git status at session start (before any Stage 4A edit)

Full `git status --porcelain` captured to scratch files before any edit;
counts:

- **480** entries staged (`git status --porcelain` lines matching `^[MADRC]`)
- **228** entries with unstaged modifications/deletions (`^.[MD]`)
- **58** untracked entries (`^??`)
- **219** ignore-matched entries (`--ignored=matching`, `^!!`)

The 480 staged entries are almost entirely a large pre-existing rename/
reorganization from a prior session's Stage 1/2 work (historical root-level
docs and screenshots moved into `docs/historical/` and
`docs/assets/legacy_screenshots/`, `reports/_archive/*` additions, etc.).
**None of this staged diff was touched, unstaged, or reorganized by Stage
4A** -- it is unrelated prior work, explicitly out of scope per "do not
stage unrelated user changes."

The 58 untracked entries included, among others, three canonical report
directories addressed in Section 4 of this stage's work:
`reports/repo_reproducibility_stage4_20260730T031306Z/`,
`reports/ir_evidence_audit_20260729T182949Z/`, and
`reports/ir_evidence_audit_review_20260729T235053Z/` -- see
`canonical_artifact_tracking_manifest.csv` for the full disposition.

The 228 unstaged-modification entries included files this stage went on to
touch: `.gitignore`, `Makefile`, `PROJECT_STATUS.md`, `README.md`,
`docs/EXPERIMENTS.md`, `docs/READ_ME_FIRST_FOR_AI.md`, `pyproject.toml`,
`reports/README.md`, `src/consistency_ranker/baseline_ranking.py`,
`src/consistency_ranker/mwfas_solver.py`,
`src/consistency_ranker/statistical_inference.py`, and many historical
file deletions corresponding to the docs-reorg staged additions above.
Stage 4A touched only `Makefile` (already unstaged-modified going in) --
every other file in this list was left exactly as found.

## 3. Stage 1-4 report directories present

`reports/repo_preparation_stage1_20260730T011354Z/`,
`reports/repo_structural_org_stage2_20260730T014347Z/`,
`reports/repo_reproducibility_stage4_20260730T031306Z/` (no directory named
`..._stage3_...` exists; Stage 3's work appears to be
`reports/real_llm_clustered_reanalysis_20260730T023745Z/`, per its own
`REAL_LLM_CLUSTERED_REANALYSIS.md` header referencing "Repo Stage 3").

## 4. Canonical report package tracked/staged/untracked/ignored status

See `canonical_artifact_tracking_manifest.csv` for the full table. Summary:
6 canonical packages were in scope; 3 were already fully staged from a
prior session (`real_llm_clustered_reanalysis_20260730T023745Z`,
`repo_preparation_stage1_20260730T011354Z`,
`repo_structural_org_stage2_20260730T014347Z`); 3 were untracked and were
staged this stage (`repo_reproducibility_stage4_20260730T031306Z`,
`ir_evidence_audit_20260729T182949Z`,
`ir_evidence_audit_review_20260729T235053Z`). **None were blocked by any
`.gitignore` rule** -- `git check-ignore -v` returned no match for any of
the six directories, confirmed both at the directory level and via
`git status --ignored=matching` at the file level. No `.gitignore` edit
was needed or made.

## 5. Files Stage 4 claimed to create vs. what exists

Per `dependency_discrepancies.csv` and `workflow_command_inventory.csv`,
Stage 4 claimed or implied it would produce/fix:

| Claimed | Existed at start of Stage 4A? |
|---|---|
| `ci_validation_report.md` | **No** -- referenced by name in two other Stage 4 files, did not exist |
| A CI job installing `.[exact]` in `.github/workflows/ci.yml` | **No** -- direct inspection showed the single `tests` job still installed only `.[dev]` |
| `requirements-lock.txt` | Yes |
| `src/consistency_ranker/provenance.py` | Yes |
| `verify_canonical_solver_version()` / `UnsupportedSolverVersionError` in `mwfas_solver.py` | Yes (code present) |
| Tests for the above | **No** -- zero references anywhere under `tests/` |
| `modified_files.csv` (referenced implicitly by "see modified_files.csv for this stage" in `offline_reproduction_report.md`) | **No** |
| `scripts/run_secret_scan.py` / `make secret-scan` | Listed as "NOT YET CREATED" in `workflow_command_inventory.csv`, but **did exist on disk** at the start of Stage 4A (created sometime between Stage 4's report being written and Stage 4A beginning) |

## 6. Hashes of files modified by Stage 4A

Recorded before editing, or reconstructed from `git show HEAD:<path>` for
files confirmed clean (unmodified relative to HEAD) at the start of Stage
4A:

| File | Before (SHA-256) | State before Stage 4A |
|---|---|---|
| `.github/workflows/ci.yml` | `87c4f9c974d55921fa051c56b5a570addc563c23d6042d0d47d7c61ed8a856df` | Clean (= HEAD); confirmed via `git status`/`git diff HEAD` showing no prior diff |
| `docs/REPRODUCTION_CANONICAL.md` | `c9b1a0cc4b41c0af637b2a66d4e993d1dab4a6c94c5217a2a0d37bdb05681d04` | Clean (= HEAD) |
| `Makefile` | not separately captured; already unstaged-modified by Stage 4 before Stage 4A began (adds `test-full`/`verify-env`/etc. targets vs. HEAD) | Dirty relative to HEAD; Stage 4A's own edit is the single added `SCIP (underlying)` echo line in `verify-env`, applied via a scoped `Edit` (old/new string shown in this session's tool-call log), not a full-file rewrite |
| `reports/real_llm_clustered_reanalysis_20260730T023745Z/reproducibility_manifest.json` | `c73618534efefd93f0fa8d23479a90a906bccc2078cb01e04d1701af78fb3958` | Staged (part of the prior session's Stage 3 commit-in-progress) |

Post-edit hashes and the full rationale for each change are in
`ci_validation_report.md` (CI), `manifest_comparison_policy.md`
(reproducibility manifest), and `test_count_normalization.md`
(`docs/REPRODUCTION_CANONICAL.md`).

## 7. Constraints observed

No destructive git commands were run (`git status`, `git diff`,
`git check-ignore`, `git show HEAD:<path>`, and `git add` on three
specifically-named new/untracked canonical directories only). No commit or
push was made. No unrelated staged/unstaged change from the prior
session's Stage 1/2 work was touched, staged, or reorganized. No external
API call was made. No scientific result file's numeric content was
changed -- the one file with regenerated content
(`reproducibility_manifest.json`) had its 7 sibling result files verified
byte-identical before and after (see `manifest_comparison_policy.md`).
