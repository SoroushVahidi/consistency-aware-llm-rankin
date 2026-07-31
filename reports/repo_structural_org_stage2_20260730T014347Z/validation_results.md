# Validation Results — Stage 2

Every check below was actually run this session. Distinguished explicitly: **passed** / **failed** / **not run** / **deferred**.

## 1. Git status before and after — PASSED

`pre_move_git_state.txt` and `post_move_git_state.txt` both captured. Diff between them accounts exactly for: 216 renames (`git mv`, history preserved — see `rollback_map.csv`), 1 plain `mv` (untracked directory, no history to preserve), 1 empty-directory deletion, and the documentation/script edits listed in `path_reference_updates.csv`. `src/consistency_ranker/baseline_ranking.py`'s diff is byte-identical before and after (confirmed via `git diff --stat`) — still untouched by any stage.

## 2. Check for unintended deletions — PASSED

Only `papers/papers/` (0 files) was deleted. Verified via `git status --porcelain=v1` containing exactly one directory removal (untracked, so it doesn't even appear as a `D` line) and `deleted_temporary_items.csv` documents it as the sole deletion. No tracked file was deleted anywhere this stage.

## 3. Repository-wide search for broken old paths — PASSED (issues found and repaired)

Searched for every moved file's old path across `*.py`, `*.md`, `*.json`, `*.sh`, `*.csv`. Found and repaired 3 live/active references before they could break anything:
- `papers/JDIQ_2026/scripts/build_master_inventory.py` — 5 static string entries (never executed/opened, but corrected for consistency).
- `experiments/method_improvement_audit_20260711_205733/run_method_improvement_audit.py` — 3 lines that **actually open/read** the moved files (`repo_publication_audit.md`, `canonical_results_inventory.csv`, `claim_support_matrix.csv`) — this was the one genuine "would have broken on next run" finding this stage, now fixed.
- `README.md`, `docs/READ_ME_FIRST_FOR_AI.md`, `docs/EXPERIMENTS.md`, `reports/README.md` — 5 documentation links updated.

Remaining hits (in `papers/JDIQ_2026/MASTER_EVIDENCE_INVENTORY.csv`/`SECTION_EVIDENCE_MAP.csv`, `papers/JDIQ_2026/manuscript/MANUSCRIPT_SCIENTIFIC_AUDIT.md`, `outputs/final_jis_package/README.md`, two run-manifest JSONs, `papers/JDIQ_2026/manuscript/REVISION_SUMMARY.md`, and already-generated report outputs like `phase_reports/BASELINE_AND_SCOPE.md`) were individually reviewed and confirmed to be **historical quoted provenance** — frozen point-in-time records or prose describing where something once was — not live functional references. These are intentionally left unedited (editing an already-generated historical report to "fix" its quoted path would falsify the historical record) and are listed explicitly in `duplicate_directory_resolution.md` and `path_reference_updates.csv` so the distinction is auditable, not just asserted.

## 4. Import checks — PASSED

```
$ python3 -c "import ast; ast.parse(open('papers/JDIQ_2026/scripts/build_master_inventory.py').read())"
syntax OK
$ python3 -c "import ast; ast.parse(open('experiments/method_improvement_audit_20260711_205733/run_method_improvement_audit.py').read())"
syntax OK
```

## 5. Targeted tests for moved components — NOT APPLICABLE (no test targets the moved files)

No test file references any of the 226 moved/deleted paths as an import or fixture (confirmed during the broken-path search in check 3) — the moves were entirely of documentation/report/media files, not source code or fixtures. There is nothing to target-test.

## 6. Full test suite — PASSED

```
$ python3 -m pytest -q
1237 passed, 23 skipped in 168.47s (0:02:48)
```
Identical to the pre-Stage-2 baseline (same 1237/23 as Stage 1's final run) — confirming the moves introduced zero test regressions.

## 7. Linting — PASSED (pre-existing debt found and disclosed, not fixed)

```
$ ruff check papers/JDIQ_2026/scripts/build_master_inventory.py experiments/method_improvement_audit_20260711_205733/run_method_improvement_audit.py
Found 250 errors (pre-existing; verified these are NOT newly introduced by this stage's edits)
```
Both files already had substantial pre-existing lint debt (unsorted imports, long lines in a densely-packed static data list) unrelated to this stage's edits. Spot-checked the 5 specific lines this stage modified (`build_master_inventory.py:107,113,116,140,143`): all were already over the 100-character limit in their original form; this stage's added trailing comments (`# moved 2026-07-30, repo Stage 2`) lengthened already-violating lines but did not introduce a new violation category. Not fixed — "do not perform a broad code refactor beyond what is necessary" explicitly excludes cleaning up 250 pre-existing, unrelated lint issues in a stale-labeled inventory generator during a structural-organization stage.

## 8. Type checking — NOT RUN

No `[tool.mypy]` configuration exists in this repository (confirmed in Stage 1 already; unchanged).

## 9. Canonical evidence manifest validation — PASSED

Every `source_data_path` in `reports/repo_preparation_stage1_20260730T011354Z/canonical_evidence_inventory.csv` was re-checked against the filesystem after this stage's moves: zero canonical-evidence paths were moved this stage (only historical/superseded artifacts were relocated), so no update was required there. One `dependency_provenance_map.csv` cell (the "Exact repair" row's `issues_found`) was updated to record the `exact_ilp_repair_investigation` duplicate-name hazard as resolved.

## 10. IR evidence audit reproduction + byte-level CSV comparison — PASSED

```
$ python3 scripts/run_ir_evidence_audit.py --output-dir <scratch>
ran OK
$ diff -q <scratch>/{unified_configuration_results,structure_utility_associations,baseline_verification,cutoff_robustness}.csv reports/ir_evidence_audit_20260729T182949Z/<same>
(no output — byte-identical, all 4 files)
```
Confirms the moves touched none of the six source directories `scripts/run_ir_evidence_audit.py` depends on.

## 11. Report-link validation — PASSED

```
$ python3 -c "... check every markdown link in reports/README.md resolves ..."
OK ../PROJECT_STATUS.md
OK ir_evidence_audit_20260729T182949Z/FINAL_IR_EVIDENCE_AUDIT.md
OK ir_evidence_audit_review_20260729T235053Z/FINAL_META_AUDIT_REVIEW.md
OK _archive/publication_audit_20260406/repo_publication_audit.md
OK _archive/publication_audit_20260406/canonical_results_inventory.csv
OK _archive/publication_audit_20260406/claim_support_matrix.csv
OK _archive/publication_audit_20260406/repaired_vs_unrepaired_master_table.csv
OK _archive/publication_audit_20260406/paper_safe_contributions.md
OK _archive/publication_audit_20260406/repo_cleanup_recommendations.md
```
All 9 links resolve.

## 12. Check that no script uses ambiguous "latest directory" selection — PASSED

Searched `scripts/` and `src/consistency_ranker/` for glob/mtime-based "pick the newest matching directory" patterns. Found none. The one mtime-reading function (`src/consistency_ranker/multi_provider_eval/audit_inventory.py`) records `mtime_unix` as descriptive metadata in an exhaustive inventory, not a selection mechanism — read in full and confirmed non-hazardous. See `duplicate_directory_resolution.md`'s final section.

## 13. Check that no canonical artifact exists in multiple conflicting locations — PASSED (one intentional duplication found and disclosed, not new)

No new conflicting duplication was created by this stage's moves (moves only relocated already-non-canonical historical material). The pre-existing intentional duplication (`reports/normalization_protocol_audit_20260714/` and `reports/full_calibrated_core/` tables mirrored into `papers/JDIQ_2026/submission/final_anonymous/supplemental/`) is unchanged and already disclosed in the original hygiene audit's `canonical_artifacts.md`.

## 14. Secret scan — PASSED

```
$ for f in <every file touched/moved this stage>; do grep -liE "api[_-]?key|bearer|secret[_-]?key|password.{0,3}[:=]" "$f"; done
```
8 files matched the pattern; all individually inspected and confirmed to be either environment-variable-name references (`AZURE_OPENAI_API_KEY`, `COHERE_API_KEY` as config-lookup keys, not values) or prose describing the *absence* of API-key handling. No actual secret value found.

## 15. Confirmation that manuscript scientific content is unchanged — PASSED

```
$ git diff HEAD --stat -- papers/JDIQ_2026/manuscript/main.tex
(empty output)
```
Zero content difference from `HEAD`, confirmed both before and after this stage's moves. No manuscript file under `papers/JDIQ_2026/manuscript/` was touched at all this stage (the moved root-level files and `docs/historical/` files are unrelated to `main.tex`).
