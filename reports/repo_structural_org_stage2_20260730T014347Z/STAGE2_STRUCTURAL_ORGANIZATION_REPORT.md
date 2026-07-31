# Repository Preparation — Stage 2: Safe Structural Organization and Path Normalization

**Governing sources**: `reports/repo_hygiene_audit_20260729T235053Z/`, `reports/repo_preparation_stage1_20260730T011354Z/` (including `deferred_cleanup_items.csv`), and the Stage 1 canonical evidence/provenance inventories — all reviewed before any edit.

**Scope completed**: pre-move baseline, taxonomy review, naming-convention documentation, execution of approved low/medium-risk moves with reference repair, canonical/generated/historical artifact separation, path/import repair, duplicate-directory-hazard resolution, inventory/documentation updates, and full validation. No manuscript content was touched, no new experiments were added, no scientific conclusion was modified, and no file was deleted beyond one empty, unreferenced directory.

---

## 1. Pre-move baseline

`pre_move_git_state.txt` records branch (`fix/outcome-f-production-operating-point`), HEAD commit, full `git status`, and an explicit check that the one pre-existing unrelated modification (`src/consistency_ranker/baseline_ranking.py`, from earlier in this session) remained untouched. No destructive Git operation was used; every tracked move used `git mv` (the two exceptions — `papers/papers/` and the untracked `reports/exact_ilp_repair_investigation/` — used plain `mv`/`rm` because there was no Git history to preserve). Every source path was verified to exist and every destination checked for conflicts before moving (see the transcript; `docs/historical/` already existed with 2 unrelated files, confirmed non-conflicting).

## 2. Repository taxonomy

Reviewed against the requested `src/scripts/configs/data/results/reports/figures/tables/tests/docs/papers` separation. **No `results/` directory was introduced.** The existing `reports/<study>/tables/` pattern already couples canonical machine-readable results to the human-readable report and reproduction script that produced them; introducing a parallel top-level `results/` would duplicate that coupling without adding clarity, so this stage did not force it — documented explicitly in `docs/REPOSITORY_LAYOUT.md`'s "Where canonical results live" section, per the brief's own instruction not to force a taxonomy where it adds indirection.

## 3. Naming-convention documentation

`docs/REPOSITORY_LAYOUT.md` (new) defines the timestamped-report form (`<study_name>_YYYYMMDDTHHMMSSZ`, already the repo's dominant convention, unchanged), the script-naming convention (`run_/analyze_/audit_/validate_<scope>.py`), and explicitly states the "no ambiguous latest-directory selection" rule verified in section 7 below. No widely-referenced file was renamed for aesthetic reasons alone — the two files that were renamed (`Consistency_Aware_Reranking_...IJCS.zip` → `IJCS_early_draft.zip`) had exactly one reference, repaired in the same change.

## 4. Executed moves

`approved_moves.csv` (11 candidate families, each risk-classified) → `executed_moves.csv` (10 executed) and `deferred_moves.csv` (6 deferred, with reasons). Per-move dependency verification was performed via repository-wide `grep` before every move (transcript preserved in this session; summarized in `path_reference_updates.csv`). One genuinely load-bearing reference was found and repaired: `experiments/method_improvement_audit_20260711_205733/run_method_improvement_audit.py` actually opens three of the moved files at runtime — this is the one case where skipping the reference repair would have introduced a real (if gracefully-caught) failure. Everything else was either a documentation link (updated) or historical prose (left unedited, per "preserve historical references where they describe the original location").

No move was executed where provenance was unclear, two artifacts conflicted, a canonical numerical result could change, a downstream dependency could not be confidently updated, or an old report would become misleading — see `deferred_moves.csv` for the specific cases excluded on these grounds (most notably `outputs/pub_vote_cmp_all4/`, kept in place because four scripts/tests still default to it).

## 5. Canonical / generated / historical separation

`canonical_location_changes.csv` records the disposition of every affected family. Two mechanisms used, matching the brief's two allowed strategies: **in-place `HISTORICAL.md` markers** (for `outputs/pub_vote_cmp_all4/`, `pub_vote_cmp_v2/`, `q1_journal_package/` — moving these would break still-functional script defaults) and **moves to a documented `_archive/` location** (for everything else, where no active reference existed or all active references could be confidently repaired).

**Generated caches/temporary artifacts**: removed only `papers/papers/` (confirmed empty — 0 files — untracked, unreferenced; this satisfies "reproducible" trivially since there is nothing to reproduce, "not referenced" via repo-wide grep, and "not the sole copy of any result" since it contains no result at all). The second candidate the hygiene audit had flagged (`experiments/real_llm_integrity_audit_20260712_232154_SUPERSEDED_originmain_only/`) was **independently re-verified and NOT deleted** — see section 8.

## 6. Path and import repair

3 Python files edited (2 static-string-only fixes in a stale-labeled inventory generator, 1 genuine live-reference fix), 5 documentation files updated with corrected links (`README.md` ×3 locations, `docs/READ_ME_FIRST_FOR_AI.md`, `docs/EXPERIMENTS.md`, `reports/README.md`). No Makefile, task-runner config, or test fixture referenced any moved path (confirmed via the same repository-wide search). No broad code refactor was performed — the pre-existing repo-root-relative path pattern (`_REPO_ROOT = Path(__file__).resolve().parent.parent`) was already consistent across current scripts and was not changed; only the specific broken/stale literal path strings were corrected.

## 7. Duplicate-directory-naming hazard

Full investigation in `duplicate_directory_resolution.md`, covering all four families the brief named: `exact_ilp_repair_investigation` vs. `exact_open_source_ilp_repair_investigation` (resolved — moved the historical one, confirmed the apparent code reference was only an internal label already pointing at the correct current directory); the `jdiq-overnight-*` pair (resolved — both archived, 6 historical references confirmed non-functional and left as accurate history); `outputs/pub_vote_cmp_all4/`/`v2`/`q1_journal_package` (documented in place, not moved, with an explicit confirmation that neither consuming script uses ambiguous glob/mtime selection — both take an explicit, hardcoded/CLI-argument path); and the `final_revision_task1`/`task4` pair (already resolved in Stage 1, not re-touched). A repository-wide search for ambiguous "latest directory" selection logic in `scripts/` and `src/consistency_ranker/` found none.

## 8. The second deletion candidate was NOT deleted — an explicit, reasoned deferral

The brief authorized removing "only the two deletion candidates already classified as safe by the hygiene audit," conditioned on independently confirming reproducibility, non-reference, and non-sole-copy status first. On independent investigation this stage:

- `papers/papers/` — confirmed empty (0 files), untracked, unreferenced. **Deleted.**
- `experiments/real_llm_integrity_audit_20260712_232154_SUPERSEDED_originmain_only/` — the *original* hygiene audit's own classification for this item was **"archive OR delete"** at **medium** confidence (not the unambiguous "delete... zero risk... high confidence" verdict given to `papers/papers/`). Independent re-verification this stage found it contains 30+ substantive analysis files (not a scaffold), and this stage could not confirm within scope that a same-day successor directory (`experiments/real_llm_integrity_audit_20260713_034713/`) fully duplicates its content. **This does not clear the bar the brief itself set** ("only after independently confirming... not the sole copy of any result"). It was left untouched and recorded as deferred in `deferred_moves.csv`, not deleted.

This means exactly **one** deletion occurred this stage (an empty directory, 0 files), not two — reported precisely rather than rounding up to match the brief's framing.

## 9. Inventories and documentation updated

- `docs/REPOSITORY_LAYOUT.md` — new, per the brief.
- `reports/repo_preparation_stage1_20260730T011354Z/dependency_provenance_map.csv` — one cell updated (the `exact_ilp_repair_investigation` hazard marked resolved).
- `reports/repo_preparation_stage1_20260730T011354Z/deferred_cleanup_items.csv` — one item marked resolved, two new items added (a duplicate-`votes_ms1` note and a note on the now-repaired-but-untested `run_method_improvement_audit.py` path fix).
- `reports/README.md` — historical-document table links updated (already-executed as part of the move itself, not a separate pass).
- `canonical_evidence_inventory.csv` — checked, required **no changes** (none of the six canonical-evidence source directories were moved this stage).
- `docs/REPRODUCTION_CANONICAL.md` — checked, required **no changes** (does not reference any moved path); its own incompleteness relative to the 2026-07-15 evidence families (noted in Stage 1) remains open and unaddressed by this stage, since extending it is a documentation-content task, not a structural-organization task.

## Validation

All 15 checks in `validation_results.md` were actually run this session: git status before/after, unintended-deletion check, repo-wide broken-path search (with fixes), import/syntax checks, full 1237-test suite (identical to the pre-Stage-2 baseline), linting (pre-existing debt disclosed, not fixed), canonical-evidence-manifest validation, IR-evidence-audit byte-level reproduction, report-link validation, ambiguous-latest-directory-selection check, conflicting-canonical-artifact check, secrets scan, and manuscript-content-unchanged confirmation. Two items are marked **not run**/**not applicable** rather than fabricated: `mypy` (not configured in this repository) and targeted tests for moved components (no test references any moved path, so there is nothing to target).

## Exact accounting

- **Moves proposed**: 11 (in `approved_moves.csv`, counting each row as one family/decision).
- **Moves executed**: 10 families, comprising 226 individual file-level relocations (216 via `git mv` per `rollback_map.csv`, plus the untracked `exact_ilp_repair_investigation` directory via plain `mv`) — see `executed_moves.csv`.
- **Moves deferred**: 6 (in `deferred_moves.csv`), each with an explicit reason.
- **Files deleted**: 0 files (one empty, 0-file directory tree removed — `papers/papers/`). The second originally-flagged candidate was independently re-verified and **not** deleted (see section 8).
- **Active path references repaired**: 3 Python files, 5 documentation files (11 individual reference updates — see `path_reference_updates.csv`).
- **Full test suite**: 1237 passed, 23 skipped, 0 failed — identical to the pre-Stage-2 baseline.
- **IR evidence audit reproduction**: byte-identical, confirmed after all moves.
- **Manuscript content**: unchanged — confirmed via `git diff HEAD --stat -- papers/JDIQ_2026/manuscript/main.tex` returning empty, both before and after this stage.
- **Rollback**: every executed move has an explicit inverse command in `rollback_map.csv`.
