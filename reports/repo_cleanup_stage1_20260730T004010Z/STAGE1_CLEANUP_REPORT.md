# Repository Cleanup — Stage 1: Safeguards, Canonical Evidence Repair, and Reproducibility Foundations

**Governing plan**: `reports/repo_hygiene_audit_20260729T235053Z/` (all six deliverables reviewed before any edit in this stage).

**Scope actually completed** (matches the six numbered items in the brief exactly; no broad file moves, no archival/deletion beyond one already-declared exception, no manuscript scientific-narrative rewriting):

1. Safeguards and backups
2. Canonical-evidence reference repair
3. Preservation of small canonical artifacts previously excluded by `.gitignore`
4. Regression tests for the two known bugs
5. A generated-results interface for manuscript numbers
6. Evidence-inventory refresh

---

## 1. Safeguards

Recorded in `pre_cleanup_git_state.txt`: branch (`fix/outcome-f-production-operating-point`), HEAD commit (`8761004`), full `git status`, the one pre-existing unrelated modified file (`src/consistency_ranker/baseline_ranking.py` — a HodgeRank scorer from earlier in this session, left untouched throughout this stage), and the pre-existing stash (also untouched). Every file this stage intended to touch was declared up front (see the stage transcript) before any edit began; `modified_files.csv` confirms the final change set matches that declaration exactly, plus one small addition (`papers/JDIQ_2026/README.md`) that was in-scope and is documented. No destructive Git command was used at any point (no `reset --hard`, no force-push, no `checkout --`, no file deletion).

Confirmed no secrets/credentials were introduced: every newly-tracked file was grepped for API-key/token/bearer patterns before `git add` (all clean — the one substring hit was "Secretary" containing "secret," a false positive, in a HotpotQA entity name).

## 2. Canonical-evidence reference repair

Four "highest-risk entry point" documents were corrected, each with **individually reasoned** edits (not a blind global find-replace) distinguishing historical/current/exploratory evidence per the brief's required terminology:

- `README.md`, `docs/READ_ME_FIRST_FOR_AI.md`, `reports/README.md`, `PROJECT_STATUS.md` — see `canonical_reference_changes.csv` for the exact disposition of every file checked, including several reviewed-and-deliberately-left-alone (e.g. `papers/JDIQ_2026/README.md`'s existing SUPERSEDED banner already covers its one `pub_vote_cmp_all4` line; `CANONICAL_PAPER_STORY.md`'s citation is one data point in a narrative-strategy document, out of this stage's scope to edit).

The repository no longer claims, in any of its four primary entry-point documents, that `outputs/pub_vote_cmp_all4/` is the current canonical evidence package. It is now consistently described as a **historical evidence package** (last regenerated 2026-03-24, zero references in the submitted `main.tex`); `reports/full_calibrated_core/` is now consistently named as the **current classical-study canonical evidence**; the real-LLM studies are consistently named as **exploratory** with their 6-underlying-query caveat stated inline, not just in the meta-audit.

## 3. Fresh-clone reproducibility

Traced the exact minimal file set `scripts/run_ir_evidence_audit.py` requires (4 specific CSVs, via direct `grep` of the script's `pd.read_csv` calls) and added a **surgical** `.gitignore` carve-out — negate the blanket `reports/final_revision_*/` exclusion for the two specific directories, then re-exclude only the genuinely bulky, non-required pieces (`outputs/` 1.6GB, one 254MB and one 6.7MB CSV not read by the script). Verified the carve-out behaves exactly as intended with `git check-ignore -v` on both the included and excluded paths before staging anything. 59 files newly tracked (`git add`), full manifest with per-file rationale in `gitignore_exception_manifest.csv`.

**Verified, not just claimed**: ran `scripts/run_ir_evidence_audit.py` against a scratch output directory and diffed all four output CSVs against the already-committed `reports/ir_evidence_audit_20260729T182949Z/` — byte-identical. This is the concrete evidence that the reproducibility gap is closed, not just that files exist.

## 4. Regression tests

`tests/test_holm_pvalue_boolean_regression.py` (15 tests) and `tests/test_numeric_threshold_parsing_regression.py` (20 tests), backed by two new centralized helpers in `src/consistency_ranker/statistical_inference.py` (`is_significant_pvalue()`, `parse_numeric_threshold()`). Full requirement-by-requirement mapping in `regression_test_report.md`. All 35 new tests pass; the full 1238-test suite passes with zero failures after these additions.

## 5. Manuscript-results generated interface

`scripts/generate_manuscript_macros.py` generates `papers/JDIQ_2026/manuscript/generated_macros.tex` (a `\newcommand` list, each macro tagged with its exact source file) from the canonical tables, deterministically, with fail-loud assertions on every reader function. Six representative categories wired into `main.tex` via `\input{generated_macros}`, replacing hand-typed literals in place with **zero value changes** (verified: the macro-rendered values are identical to what was previously typed). Three further categories (exact-vs-greedy bound, structure-utility correlation, real-LLM sample size) are generated but deliberately not wired into prose, since `main.tex` has no existing sentence discussing them yet and adding one would be new scientific narrative, out of this stage's scope — `scripts/check_manuscript_macro_drift.py` prints their current values every run so a future author has a ready-made, already-tested macro instead of hand-copying a number again. The drift checker was verified to actually detect drift (tamper-and-restore test performed, both directions confirmed) and is wired into `pytest` via `tests/test_manuscript_macro_drift.py`. Full detail, including the honest LaTeX-compile-unavailable caveat, in `manuscript_results_interface.md`.

## 6. Evidence-inventory refresh

New `papers/JDIQ_2026/EVIDENCE_PROVENANCE_20260730.md` maps six categories (historical pipeline / current classical-study canonical evidence / real-LLM exploratory studies / integrated evidence audit / meta-audit / the still-pending query-clustered re-analysis) to source file, generating script, and manuscript section. `MASTER_EVIDENCE_INVENTORY.csv`/`SECTION_EVIDENCE_MAP.csv` were **not** modified (historical provenance preserved byte-for-byte) but are now marked stale-with-pointer from both `papers/JDIQ_2026/README.md` and `PROJECT_STATUS.md`'s documentation-authority map. Detail in `updated_evidence_provenance.md`.

## Validation

Every check in `validation_results.md` was actually executed (full pytest run twice, targeted regression tests, ruff, the fresh-clone-equivalent reproducibility diff, the drift-detector tamper test, brace-balance/macro-consistency checks on `main.tex`, and a full `git status`/diff review against the pre-change baseline). Two checks were explicitly **not** run and are stated as such rather than assumed: `mypy` (not configured in this repository) and a real LaTeX compile (no TeX engine installed in this environment).

## Exact accounting

- **Files modified**: 7 (`.gitignore`, `PROJECT_STATUS.md`, `README.md`, `docs/READ_ME_FIRST_FOR_AI.md`, `reports/README.md`, `papers/JDIQ_2026/README.md`, `papers/JDIQ_2026/manuscript/main.tex`) + 1 additive code change (`src/consistency_ranker/statistical_inference.py`).
- **Files newly tracked**: 59 (under the two `final_revision_*` directories).
- **New files**: 2 manuscript-workspace docs, 2 generator/checker scripts, 1 generated `.tex` file, 3 test files, this stage's own 9-file report directory.
- **Tests added**: 36 (35 bug-regression + 1 macro-drift wrapper).
- **Stale references retained intentionally**: `outputs/pub_vote_cmp_all4/`, `outputs/pub_vote_cmp_v2/`, `outputs/q1_journal_package/` (still-functional script defaults; not moved/deleted per this stage's explicit "no moves/deletion yet" scope); `MASTER_EVIDENCE_INVENTORY.csv`/`SECTION_EVIDENCE_MAP.csv` content (historical provenance, marked stale via pointers, not edited); `CANONICAL_PAPER_STORY.md`'s S3 citation (narrative-strategy judgment call, deferred); `docs/REPRODUCTION_CANONICAL.md`'s pipeline map (now itself slightly incomplete relative to the 2026-07-15 evidence families, flagged but not extended in this stage); ~40 other `pub_vote_cmp_all4`-mentioning files not individually reviewed (listed at the grep level in `canonical_reference_changes.csv`).
- **Unresolved issues deferred to later stages**: the 35 proposed file moves/renames and all archival/deletion (Stage 2+ per `reports/repo_hygiene_audit_20260729T235053Z/cleanup_execution_plan.md`); the pending query-clustered real-LLM re-analysis (a statistics task, tracked in `papers/JDIQ_2026/EVIDENCE_PROVENANCE_20260730.md` §5, not attempted here); extending `docs/REPRODUCTION_CANONICAL.md` with the 2026-07-15 evidence families; reviewing the ~40 remaining `pub_vote_cmp_all4`-mentioning files individually; an actual LaTeX compile once a TeX toolchain is available; broader macro migration beyond the six demonstrated categories.
