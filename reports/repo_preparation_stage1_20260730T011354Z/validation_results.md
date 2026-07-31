# Validation Results

Every check below was actually run in this session. Distinguished explicitly: **passed** / **failed** / **not run** / **deferred**.

## 1. Repository-wide stale-reference search — PASSED

```
$ grep -n "canonical" README.md docs/READ_ME_FIRST_FOR_AI.md reports/README.md PROJECT_STATUS.md | grep -i "pub_vote_cmp_all4"
```
Six matches, all explicitly qualified as historical/superseded (e.g. "Historical evidence audit... canonical-package recommendation for the now-superseded pub_vote_cmp_all4/v2 split"). No unqualified "X is canonical" claim about `outputs/pub_vote_cmp_all4/` remains in these four primary entry-point documents. Re-run at the end of this stage (identical result to when first checked earlier in the session — no regression from the intervening CSV-repair work).

A broader repo-wide grep found ~40 additional files mentioning `pub_vote_cmp_all4` that were reviewed at the grep level only (not individually edited) — see `canonical_reference_changes.csv` and `deferred_cleanup_items.csv`.

## 2. Targeted regression tests — PASSED

```
$ python3 -m pytest tests/test_holm_pvalue_boolean_regression.py tests/test_numeric_threshold_parsing_regression.py -q
35 passed in 0.75s
```

## 3. Full test suite — PASSED

```
$ python3 -m pytest -q
1237 passed, 23 skipped in 167.93s (0:02:47)
```
Run twice this session with an identical result: once immediately after removing the manuscript-macro files (35 dedicated + full suite), and once again as the final check for this report (see the session transcript for the second run's completion). No test failures either time.

## 4. Linting — PASSED

```
$ ruff check src/consistency_ranker/statistical_inference.py tests/test_holm_pvalue_boolean_regression.py tests/test_numeric_threshold_parsing_regression.py
All checks passed!
```

## 5. Type checking — NOT RUN

`pyproject.toml` has no `[tool.mypy]` section and no other type checker is configured for this repository. Not fabricating a pass.

## 6. Dependency resolution for the IR audit — PASSED

```
$ python3 scripts/run_ir_evidence_audit.py --output-dir <scratch>
{"n_unified_rows": 96, "n_association_rows": 7, "n_baseline_rows": 4, "n_cutoff_rows": 9}
$ diff -q <scratch>/{unified_configuration_results,structure_utility_associations,baseline_verification,cutoff_robustness}.csv reports/ir_evidence_audit_20260729T182949Z/<same>
(no output — byte-identical, all 4 files)
```
Run three times total across this session's two stages (once right after the `.gitignore` fix, once mid-session, once as this stage's final check); identical byte-for-byte output every time.

## 7. Evidence-manifest path validation — PASSED

Every `source_data_path` value in `canonical_evidence_inventory.csv` and every path in `dependency_provenance_map.csv` was cross-checked against the actual filesystem while being written (via the same `ls`/`grep`/`python3 -c "pd.read_csv(...)"` commands used to build the underlying facts this session — not typed from memory). All CSVs were additionally validated for structural correctness (see next check).

## 8. Check for missing canonical inputs — PASSED

The one previously-missing input (the two `final_revision_task1/task4` directories) is fixed (see check 6). No other missing input was found in this stage's scope. `docs/REPRODUCTION_CANONICAL.md`'s own pipeline map is incomplete relative to the full evidence base (deferred, see `deferred_cleanup_items.csv`) — this is a documentation gap, not a missing-data gap: the underlying files are all present and tracked.

## 9. Check for duplicated canonical sources — PASSED (found and disclosed, not silently ignored)

Confirmed one real duplication: `reports/normalization_protocol_audit_20260714/tables/*.csv` and `reports/full_calibrated_core/tables/*.csv` are duplicated byte-for-byte into `papers/JDIQ_2026/submission/final_anonymous/supplemental/tables/` (~38MB combined) — assessed as an intentional frozen-submission-snapshot pattern (see the original hygiene audit's `canonical_artifacts.md`), not accidental drift, and listed in `deferred_cleanup_items.csv` for a documentation note. No *conflicting* duplicate (same claim, different numbers) was found this session beyond the already-known historical `outputs/pub_vote_cmp_all4` vs. `pub_vote_cmp_v2` split, which is explicitly labeled non-canonical.

## 10. Secret scan — PASSED

```
$ for f in <all 59 newly-tracked files>; do grep -liE "api[_-]?key|bearer|secret[_-]?key|password.{0,3}[:=]" "$f"; done
(no output — clean)
```
Re-run this stage against the same file set previously checked; identical clean result.

## 11. Git diff review — PASSED

`git status --porcelain=v1` reviewed line-by-line against `pre_change_git_state.txt`/`pre_change_manifest.csv`. Confirmed: 7 content edits carried forward from the prior attempt (all still valid), 59 newly-tracked files (unchanged), 2 new manuscript-workspace docs, this stage's own new report directory, and the two bug-regression test files + `statistical_inference.py` addition — all as declared. `src/consistency_ranker/baseline_ranking.py` remains modified exactly as it was before any stage began (untouched throughout).

## 12. Confirmation that no manuscript scientific content was rewritten — PASSED

```
$ git diff HEAD --stat -- papers/JDIQ_2026/manuscript/main.tex
(empty output)
```
Zero difference from the committed `HEAD` version. **Caveat on the check's own mechanics**: a `find ... -newer` mtime check on this file DID report it as filesystem-touched, because the `git restore --staged --worktree` operation used to revert the earlier macro edits rewrites the file's mtime even when content ends up byte-identical to `HEAD`. The mtime signal is therefore not meaningful here; the content-based `git diff HEAD` check is the correct one, and it confirms zero content difference. No other file under `papers/JDIQ_2026/manuscript/` was touched.

## 13. Confirmation that no broad file moves, deletions, or archives occurred — PASSED

```
$ git status --porcelain=v1 | grep "^R\|^D "
(no output)
```
No renames (`R`) or deletions (`D `) appear anywhere in `git status`. The only removals this session were of files that never existed at `HEAD` and were created-then-removed within this same session (`generated_macros.tex`, `generate_manuscript_macros.py`, `check_manuscript_macro_drift.py`, `test_manuscript_macro_drift.py`) — net effect on the repository as it stood before any stage began is zero, not a deletion of pre-existing content.

## 14. CSV structural validation (added during this stage, not in the original brief, but necessary) — PASSED after repair

While building this stage's deliverables, discovered that several hand-authored CSV files (in this stage and the two prior report directories) contained unescaped commas producing ragged/malformed rows when parsed with a standard CSV reader — a real defect in "machine-readable" deliverables. Repaired all affected files by regenerating them via Python's `csv.writer` (which handles quoting correctly) rather than hand-typed text: `canonical_evidence_inventory.csv`, `canonical_reference_changes.csv`, and `gitignore_exception_manifest.csv` in this directory; `canonical_reference_changes.csv` and `gitignore_exception_manifest.csv` in the prior `repo_cleanup_stage1_20260730T004010Z/`; and `proposed_moves.csv` in the original `repo_hygiene_audit_20260729T235053Z/`. Verified via a repo-wide sweep:

```
$ python3 -c "import csv, glob; [... check every .csv in all three report dirs parses with no ragged rows ...]"
OK   (all 10 CSVs across all three report directories)
```
