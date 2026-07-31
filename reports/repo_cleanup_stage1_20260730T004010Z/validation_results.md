# Validation Results — Stage 1

Every check below was actually executed during this stage; none are claimed without having been run. Where a check could not be run (e.g. no LaTeX engine installed), that is stated explicitly rather than omitted.

## 1. Repository-wide search for stale canonical-package language

```
$ grep -n "canonical" README.md docs/READ_ME_FIRST_FOR_AI.md reports/README.md PROJECT_STATUS.md | grep -i "pub_vote_cmp_all4"
```
Result: every remaining co-occurrence of "canonical" and `pub_vote_cmp_all4` in these four files is explicitly qualified as historical/superseded (5 hits, all correctly framed — see the exact lines in `validation_results.md`'s companion terminal output, reproduced in this stage's transcript). No unqualified "X is canonical" claim about `pub_vote_cmp_all4` remains in these four files.

A broader repo-wide grep (`grep -rln "pub_vote_cmp_all4" --include="*.md" .`) found ~40 additional files with the string, almost all dated audit/planning documents (`experiments/*/`, `outputs/*/README.md`, `docs/research/*`, `papers/JDIQ_2026/manuscript/*_AUDIT.md`, etc.) that were **deliberately not touched** in this stage — see `canonical_reference_changes.csv` for the specific files checked and the rationale for leaving each alone (mostly: already self-banners as historical, e.g. `papers/JDIQ_2026/README.md`'s existing top-of-file SUPERSEDED note; or out of the "highest-risk entry point" scope this stage targeted).

## 2. Targeted tests for both known bugs

```
$ python3 -m pytest tests/test_holm_pvalue_boolean_regression.py tests/test_numeric_threshold_parsing_regression.py -v
35 passed in 0.74s
```
(15 + 20 tests; see `regression_test_report.md` for the requirement-by-requirement mapping.)

## 3. Full test suite

```
$ python3 -m pytest -q
1238 passed, 23 skipped in 168.65s (0:02:48)
```
Run twice (once immediately after adding the two bug-regression files: 1237 passed/23 skipped; once after adding the macro-drift test and the ruff-driven line-length fixes: 1238 passed/23 skipped — the +1 is exactly the new `test_manuscript_macro_drift.py`). Zero failures in either run.

## 4. Linting

```
$ ruff check src/consistency_ranker/statistical_inference.py scripts/generate_manuscript_macros.py \
    scripts/check_manuscript_macro_drift.py tests/test_holm_pvalue_boolean_regression.py \
    tests/test_numeric_threshold_parsing_regression.py tests/test_manuscript_macro_drift.py
All checks passed!
```
(Ran on every file this stage created or modified in `src/`, `scripts/`, and `tests/`; 6 issues found and fixed in the first pass — 3× line-too-long, 1× unsorted-import, plus a cleanup of an awkward `.replace()` chain in the macro-name generator — all confirmed fixed by the final clean run above.)

## 5. Type checking

**Not run.** `pyproject.toml` has no `[tool.mypy]` section and no other type-checker configuration was found; this repository does not appear to run one in CI. Not fabricating a mypy pass.

## 6. IR audit dependency-resolution check (fresh-clone reproducibility)

```
$ python3 scripts/run_ir_evidence_audit.py --output-dir <scratch-dir>
{"n_unified_rows": 96, "n_association_rows": 7, "n_baseline_rows": 4, "n_cutoff_rows": 9}

$ diff -q <scratch-dir>/{unified_configuration_results,structure_utility_associations,baseline_verification,cutoff_robustness}.csv \
          reports/ir_evidence_audit_20260729T182949Z/<same file>
IDENTICAL (all 4 files)
```
Confirmed twice: once immediately after `git add`-ing the newly-tracked files, and once again in the final validation pass. Both runs produced byte-identical output to the original (pre-Stage-1) committed report. This directly demonstrates the fresh-clone reproducibility gap identified in the hygiene audit is now closed — `scripts/run_ir_evidence_audit.py` no longer depends on any untracked file. (Caveat: this was verified by re-running the script against the now-tracked working tree, not by an actual `git clone` into a new directory and rerun there; the effect is the same since the working tree now contains everything `git ls-files` would export, but a true `git clone --no-local` round-trip was not additionally performed.)

## 7. Manuscript generated-value drift check

```
$ python3 scripts/check_manuscript_macro_drift.py
No drift detected: generated_macros.tex matches the canonical source tables, and main.tex correctly \inputs it.
(exit code 0)
```
Additionally verified the check actually *detects* drift, not just passes trivially: temporarily edited `generated_macros.tex` (changed `0.554` to `0.999`), reran the check, confirmed it failed with exit code 1 and a specific "STALE" message; restored the file from a backup and confirmed the check passed again. See `manuscript_results_interface.md` for the full transcript.

## 8. Manuscript build / LaTeX syntax validation

- **Full compile: NOT run.** No LaTeX engine (`pdflatex`/`xelatex`/`lualatex`) is installed in this environment (`which pdflatex xelatex lualatex` returned nothing); `latexmk` is present but is a non-functional shim ("no .tex file found" on invocation) and could not actually typeset. This is stated explicitly rather than claimed as a pass.
- **What was checked instead**: brace-balance across the full `main.tex` (`depth == 0` at EOF, confirmed via a small Python scanner); every macro used in `main.tex` (`\NDatasets`, `\NQueriesSciDocs/FiQA/HotpotQA/Bright`, `\CombSumNDCGTen`, `\RRFNDCGTen`, `\LargerPoolActiveCells`, `\LargerPoolHolmSignificant`) is defined exactly once in `generated_macros.tex` and there are zero duplicate `\newcommand` definitions (confirmed via `grep`/`comm`, reproduced in `manuscript_results_interface.md`).
- **Recommended follow-up** (not performed here): `latexmk -pdf main.tex` in an environment with a real TeX install before treating this migration as submission-ready.

## 9. Git diff review / untouched-file confirmation

```
$ git status --porcelain=v1
```
Reviewed line-by-line against the pre-change baseline (`pre_cleanup_git_state.txt`) and the up-front file declaration made before any edit (recorded in this stage's transcript). Result: exactly the files declared in advance were touched (7 content edits, 2 additive code files, 3 new test files, 2 new manuscript-workspace files, 1 `.gitignore` edit, 59 newly-tracked files under the two `final_revision_*` directories, plus this stage's own report directory). `src/consistency_ranker/baseline_ranking.py` remains modified exactly as it was before this stage started (diff unchanged) — confirmed not touched. No file under `reports/*/raw_calls/`, `data/raw/`, or any other provider-transcript path was staged. No secrets were introduced (re-confirmed via the same grep patterns used in the original hygiene audit against every newly-tracked file, all clean).
