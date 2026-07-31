# Repository Preparation — Stage 1 (Corrected Scope)

**Governing plan**: `reports/repo_hygiene_audit_20260729T235053Z/` (reviewed before any edit).

**Relationship to the prior attempt**: an earlier run this session (`reports/repo_cleanup_stage1_20260730T004010Z/`) implemented a version of Stage 1 that included a manuscript LaTeX macro interface. This corrected instruction set explicitly excludes that work. Before doing anything else, that work was **fully reverted**:

- `papers/JDIQ_2026/manuscript/main.tex` restored to `HEAD` via `git restore --staged --worktree` — confirmed `git diff HEAD --stat` on this file is empty (zero content difference from before any stage touched it).
- `papers/JDIQ_2026/manuscript/generated_macros.tex`, `scripts/generate_manuscript_macros.py`, `scripts/check_manuscript_macro_drift.py`, `tests/test_manuscript_macro_drift.py` deleted and unstaged (none existed at `HEAD`, so this fully removes them).
- Full test suite re-run after the revert: 1237 passed, 23 skipped, 0 failed (down from 1238 in the prior attempt, exactly matching the removal of the one macro-drift test).
- The prior report directory (`reports/repo_cleanup_stage1_20260730T004010Z/`) was **not** deleted or archived (out of scope for this stage per its own explicit instructions), but its `manuscript_results_interface.md` and `STAGE1_CLEANUP_REPORT.md` now describe work that has since been reverted — this is stated here explicitly so nobody is misled by that directory's contents into thinking `generated_macros.tex` etc. still exist.
- Everything else from the prior attempt — the canonical-evidence documentation fixes, the `.gitignore` carve-out and 59 newly-tracked files, the two bug-regression test files, the `statistical_inference.py` additions, `papers/JDIQ_2026/EVIDENCE_PROVENANCE_20260730.md` — remains in place and is still in-scope for (and re-verified by) this corrected run.

Full detail of the revert in `pre_change_git_state.txt`.

---

## Scope completed (exactly the seven numbered items, nothing more)

### 1. Repository safeguards

`pre_change_git_state.txt` (branch, commit, full `git status`, explicit unrelated-change detection for `src/consistency_ranker/baseline_ranking.py`, the revert record above) and `pre_change_manifest.csv` (103-row machine-readable listing of every file's git state and whether it belongs to this stage). No destructive Git command was used. No unrelated local change was overwritten — confirmed `baseline_ranking.py`'s diff is byte-identical to its state before any stage began. No credentials/tokens/private endpoints were introduced — every newly-tracked file was grepped for secret-shaped patterns (clean).

### 2. Canonical-evidence reference correction

`README.md`, `docs/READ_ME_FIRST_FOR_AI.md`, `reports/README.md`, `PROJECT_STATUS.md`, `papers/JDIQ_2026/README.md` (narrow edit) corrected with individually-reasoned edits, not a blind replace. `papers/JDIQ_2026/MASTER_EVIDENCE_INVENTORY.csv`/`SECTION_EVIDENCE_MAP.csv` reviewed and left content-unedited (historical provenance preserved) but marked stale via pointers. Every correction classified against the brief's required 9-category scheme in `canonical_reference_changes.csv` (17 rows), including entries for files reviewed-and-deliberately-left-alone with explicit rationale (e.g. `CANONICAL_PAPER_STORY.md`'s one citation, a narrative-strategy judgment call out of scope here).

The repository documentation now answers, unambiguously, all six questions the brief poses — see `papers/JDIQ_2026/EVIDENCE_PROVENANCE_20260730.md` (the single file that maps every category to source/script/report) and this stage's own `canonical_evidence_inventory.csv` (the more granular companion).

### 3. Fresh-clone reproducibility

Traced the exact minimal file set `scripts/run_ir_evidence_audit.py` requires via direct `grep` of its `pd.read_csv` calls; added a surgical `.gitignore` carve-out (negate the blanket `reports/final_revision_*/` exclusion for the two required directories, re-exclude only the genuinely bulky non-required pieces). 59 files newly tracked. Every exception documented with per-file rationale in `gitignore_exception_manifest.csv`. **Verified, not just claimed**: re-ran `scripts/run_ir_evidence_audit.py` and diffed all four output CSVs against the committed report — byte-identical, confirmed three times across this session.

**Explicitly not claimed**: full fresh-clone reproducibility of the repository as a whole. `reproducibility_status.md` states precisely which studies remain non-reproducible without external LLM API credentials (the real-LLM raw data collection step, by design) or external dataset downloads (raw BEIR/BRIGHT/HotpotQA data, by design) — both documented rather than glossed over.

### 4. Regression tests for both known bugs

`tests/test_holm_pvalue_boolean_regression.py` (15 tests) and `tests/test_numeric_threshold_parsing_regression.py` (20 tests), backed by two new centralized pure functions in `src/consistency_ranker/statistical_inference.py` (`is_significant_pvalue()`, `parse_numeric_threshold()`). Full requirement-by-requirement coverage table in `regression_test_report.md`, including the specific dtypes named in this corrected brief (Python `bool`, NumPy `bool_`, pandas nullable `BooleanDtype`, missing values, `"True"`/`"False"` strings, integers `0`/`1`, and the exact filtering logic `scripts/run_ir_evidence_audit.py` actually uses) and the numeric-parsing edge cases (`.05`, `0.05`, `5e-2`, negative decimals, malformed expressions, the forbidden `df.attr.05` attribute-access form — verified via `ast.parse` to be a hard `SyntaxError`, not a silent bug — and the valid threshold values already used in this codebase). All 35 tests pass; the former failure mode is reproduced directly (`test_naive_equals_true_is_the_bug_not_the_fix`) and shown fixed.

### 5. Authoritative evidence inventory

`canonical_evidence_inventory.csv` (17 rows: 9 classical-backbone results `CB-01`..`CB-09`, 5 real-LLM exploratory results `LLM-01`..`LLM-05`, 2 audits `AUD-01`/`AUD-02`, 1 explicitly-pending item `IR-PENDING-01`), each row carrying the full schema the brief specifies (result identifier, description, population/unit of analysis, sample size, metric, source data path, generating script, report path, status, canonical/superseded designation, limitations, reproducibility status). Internal population/sample-size language is precise about the real-LLM studies' actual unit of analysis — every `LLM-*` row states both "120 rows" and "6 unique queries" side by side, and the resulting statistical limitation, so this cannot be silently misread as 120 independent observations by a future reader.

### 6. Dependency and provenance map

`dependency_provenance_map.csv` (11 rows, covering all 11 named studies: original construction, classical retrieval evaluation, larger-pool study, greedy repair, exact repair, exact-baseline-fairness study, repair frontier, extraction study, repair diagnostic, final IR evidence audit, meta-audit), each mapping configuration → raw/source input → preprocessing script → analysis script → result files → figures/tables → report → tests → downstream consumers, with an explicit `issues_found` column surfacing: the fresh-clone reproducibility gap (now fixed, noted as fixed); the duplicate-directory-naming hazard (`exact_ilp_repair_investigation` vs. `exact_open_source_ilp_repair_investigation`); the zero-`\input{}` manually-copied-values situation in `main.tex`; the overwrite-without-guard behavior of `run_ir_evidence_audit.py`'s `run()` function; and the two real-LLM-study statistical issues (pseudo-replication, missing multiple-comparison correction). Low-priority items were **not** all fixed here — deferred to `deferred_cleanup_items.csv` (10 items, each with a priority and recommended next step) rather than expanded into out-of-scope work.

### 7. Documentation update

Achieved through items 2, 5, and 6 above — no separate manuscript-facing documentation was created (per the explicit exclusion). A future maintainer or paper-writing session can now determine, from tracked files alone: repository purpose and current branch status (`PROJECT_STATUS.md`, unchanged in substance, corrected in one bullet); canonical evidence locations (`EVIDENCE_PROVENANCE_20260730.md`, `canonical_evidence_inventory.csv`); completed vs. exploratory vs. pending studies (both of those files, explicitly); how to reproduce each major analysis (`docs/REPRODUCTION_CANONICAL.md`, with its own now-documented gap in `deferred_cleanup_items.csv`); known methodological limitations (`canonical_evidence_inventory.csv`'s `limitations` column, `reproducibility_status.md`); historical packages not to treat as canonical (all four primary entry-point documents, consistently); where new experiments/reports should be stored (the existing `reports/<timestamp>/` convention, unchanged, not restructured).

---

## Validation

Every check in `validation_results.md` was actually executed this session (stale-reference search, both regression-test files, the full 1237-test suite, `ruff`, the fresh-clone-equivalent audit-reproduction diff, a secrets scan, a `git diff`/`git status` review, and an explicit content-level confirmation that `main.tex` has zero diff from `HEAD`). Two checks are marked **not run** rather than fabricated: `mypy` (not configured in this repository) and a real LaTeX compile (not applicable — no manuscript content was touched this stage at all, and no TeX engine is installed regardless). One additional check not in the original brief was added and is disclosed: a CSV structural-validity sweep, which found and fixed genuine formatting defects (unescaped commas producing ragged rows) in several of this session's own hand-authored CSV deliverables, across both this stage and the two prior report directories.

---

## Exact accounting

- **Files modified this stage (content)**: none beyond what the prior attempt already modified and this stage re-verified as still correct (`.gitignore`, `PROJECT_STATUS.md`, `README.md`, `docs/READ_ME_FIRST_FOR_AI.md`, `reports/README.md`, `papers/JDIQ_2026/README.md`, `src/consistency_ranker/statistical_inference.py`) — plus the CSV-repair fixes to `canonical_reference_changes.csv`/`gitignore_exception_manifest.csv` in the prior stage's directory and `proposed_moves.csv` in the original hygiene-audit directory (formatting-only, no content change).
- **Files reverted this stage**: `papers/JDIQ_2026/manuscript/main.tex` (restored to `HEAD`).
- **Files removed this stage**: `papers/JDIQ_2026/manuscript/generated_macros.tex`, `scripts/generate_manuscript_macros.py`, `scripts/check_manuscript_macro_drift.py`, `tests/test_manuscript_macro_drift.py` (all created-then-removed within this session; net effect on the pre-session repository is zero).
- **Files newly tracked**: 59 (unchanged from the prior attempt, under the two `final_revision_*` directories).
- **New files this stage**: 8 report deliverables in `reports/repo_preparation_stage1_20260730T011354Z/`.
- **Tests**: 35 regression tests (unchanged from the prior attempt, minus the removed macro-drift test); full suite 1237 passed / 23 skipped / 0 failed.
- **Unresolved provenance/reproducibility issues**: 10, itemized with priority in `deferred_cleanup_items.csv`.
- **Manuscript scientific content rewritten**: none — confirmed via `git diff HEAD --stat -- papers/JDIQ_2026/manuscript/main.tex` returning empty.
- **Broad file moves/deletions/archives**: none — confirmed via `git status --porcelain=v1` containing no `R` or `D ` entries.
