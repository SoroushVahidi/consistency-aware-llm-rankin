# Staged Cleanup Execution Plan

**Status: PLAN ONLY. Nothing in this document has been executed. No file was moved, renamed, deleted, or rewritten as part of producing this audit.**

Each stage is safe to run independently and stop; later stages assume earlier stages completed. Every stage lists a validation command and a rollback.

---

## Stage 1 — Safeguards and backups

- Confirm working tree is clean before starting: `git status --porcelain=v1` (at audit time: one modified tracked file, `src/consistency_ranker/baseline_ranking.py`, plus the untracked new-session artifacts already listed in this audit — resolve/commit those first, per this repo's own git-safety norms, before any bulk reorganization).
- Create a dedicated branch: `git checkout -b chore/repo-hygiene-cleanup-<date>`.
- Tag the pre-cleanup state: `git tag pre-hygiene-cleanup-<date>`.
- **Validation**: `git status --porcelain=v1` empty (or only expected changes); `git tag -l | grep pre-hygiene-cleanup`.
- **Rollback**: `git checkout <previous-branch>`; the tag remains as an anchor if anything on the cleanup branch needs discarding — never force-push or delete the tag without explicit confirmation.

## Stage 2 — Ignore rules and temporary-file cleanup

- Add the surgical `.gitignore` carve-out for `reports/final_revision_task1_pool_cutoff_20260715/` and `.../task4_exact_baseline_fairness_20260715/` (track the small `tables/` summary CSVs identified in `proposed_moves.csv`; keep `outputs/` and `pool_cutoff_method_metrics.csv` excluded).
- Delete `papers/papers/` (confirmed empty, untracked, unreferenced).
- Confirm no `.DS_Store`/`Thumbs.db`/tracked `__pycache__`/tracked cache dirs exist (already verified clean in this audit; re-run as a regression check).
- **Validation**: `find papers/papers 2>&1` reports "No such file or directory"; `git status` shows the two `final_revision_*` table dirs as new tracked files, nothing else changed; `git ls-files | grep -E "__pycache__|\.pyc$|\.mypy_cache|\.ruff_cache|\.pytest_cache"` returns nothing.
- **Rollback**: `git checkout -- .gitignore`; `git rm --cached` the newly-tracked files if the carve-out needs reverting (they were never committed if this is undone before a commit).

## Stage 3 — Directory normalization

- Create `docs/historical/` entries (already an existing convention — confirm it still exists) and `reports/_archive/`, `figures/legacy/`, `docs/assets/legacy_screenshots/`, `papers/_archive/` as needed (some may already exist; check with `ls -d` before creating).
- **Validation**: `ls -d docs/historical reports/_archive figures/legacy docs/assets/legacy_screenshots papers/_archive 2>&1` — all should exist or be freshly created with a one-line `README.md` explaining their purpose.
- **Rollback**: `rm -rf` any freshly-created empty directory (safe pre-move; nothing has been placed in them yet).

## Stage 4 — File moves and renames

- Execute the moves in `proposed_moves.csv` **one row at a time**, using `git mv` (preserves history) rather than `mv` + `git add`.
- Order: loose root images/PDFs/zip first (lowest risk, zero code references confirmed by grep), then root-level historical `.md` files, then the `reports/_archive/` and `experiments/`/`reports/jdiq-overnight-*` moves (medium risk — re-grep for each specific path immediately before moving it, since this plan's grep was run once at audit time and the tree may have changed).
- Do **not** move `outputs/pub_vote_cmp_all4/`, `outputs/pub_vote_cmp_v2/`, or `outputs/q1_journal_package/` — per `proposed_moves.csv`, several still-functional scripts (`generate_q1_tables.py`, `build_paper_evidence_package.py`, `summarize_publication_vote_suite.py`) default to these paths; moving breaks their reproducibility even though the pipeline is no longer canonical for the current manuscript. Add an in-place `HISTORICAL.md` banner instead.
- **Validation**: after each `git mv`, run `git status` to confirm exactly one rename is staged; run `grep -rl "<old-path>"` across `*.py *.tex *.md *.json` to confirm zero remaining references before moving to the next row.
- **Rollback**: `git mv <new-path> <old-path>` (exact inverse) for any single move; `git reset --hard pre-hygiene-cleanup-<date>` only as a last resort for the whole stage, with explicit user confirmation first per this repo's own git-safety norms (never `reset --hard` silently).

## Stage 5 — Import and path repairs

- Re-run the reference grep from Stage 4 across the whole repo (not just the moved paths) to catch anything missed: `grep -rn "<each old path>" --include="*.py" --include="*.tex" --include="*.md" --include="*.json" --include="*.sh" .`
- Pay special attention to `papers/JDIQ_2026/submission/scripts/build_anonymous_supplementary.py`, `build_final_anonymous.py`, and `SOURCE_MANIFEST.md`, which reference `exact_ilp_repair_investigation` (the old, pre-rename directory) — read these three files fully before archiving that directory, since the reference may be intentional (a genuinely separate early investigation) rather than stale.
- **Validation**: `python -c "import ast,glob; [ast.parse(open(f).read(), f) for f in glob.glob('scripts/**/*.py', recursive=True)]"` (syntax-checks all scripts still parse); re-run `pytest --collect-only` to confirm no import errors from any moved module (note: none of the proposed moves touch `src/` or `scripts/*.py` files themselves, only report/data/doc directories, so this should be a no-op check, not a real risk).
- **Rollback**: same as Stage 4 (per-file `git mv` inverse).

## Stage 6 — Report and result consolidation

- Add the `HISTORICAL` banner (per `canonical_artifacts.md`'s recommendation) to `reports/README.md`, `reports/repo_publication_audit.md`, `outputs/pub_vote_cmp_all4/README.md` (or equivalent), and `papers/JDIQ_2026/MASTER_EVIDENCE_INVENTORY.csv`/`SECTION_EVIDENCE_MAP.csv`.
- Update `README.md` and `docs/READ_ME_FIRST_FOR_AI.md`'s canonical-package pointer (content edit, not a move) — this is the one step in this plan that changes a *claim*, not just a *location*; get explicit author sign-off on the replacement wording before committing, since it affects how future readers interpret the paper's own evidence chain.
- Add one new row to `PROJECT_STATUS.md`'s documentation-authority map declaring `full_calibrated_core` the JDIQ_2026 numeric backbone and marking `MASTER_EVIDENCE_INVENTORY.csv`/`SECTION_EVIDENCE_MAP.csv` stale pending regeneration.
- **Validation**: `grep -c "pub_vote_cmp" README.md docs/READ_ME_FIRST_FOR_AI.md` should drop to zero (or be confined to a clearly-labeled historical section); `grep -n "full_calibrated_core" PROJECT_STATUS.md` should show the new authority-map row.
- **Rollback**: `git checkout -- <file>` per edited file (these are content edits on tracked files, trivially revertible).

## Stage 7 — Documentation updates

- Update `reports/README.md`'s table to point "start here" at `PROJECT_STATUS.md` instead of the now-historical `repo_publication_audit.md`.
- Add a short note to `docs/ARTIFACT_POLICY.md` codifying the surgical-carve-out pattern applied in Stage 2, so the next `final_revision_*`-style directory doesn't repeat the same blanket-gitignore mistake.
- **Validation**: manual read-through of the three edited docs for internal consistency (no tool substitutes for this step).
- **Rollback**: `git checkout -- <file>`.

## Stage 8 — Tests and reproducibility verification

- Add a regression test for the two previously-fixed bugs referenced in this audit's brief (`holm_active_ms1_family == True` pandas trap; `.holm_significant_at_0.05` attribute-parsing bug) — currently **zero test coverage** exists for either, and `scripts/run_ir_evidence_audit.py` itself is not imported by any test. A minimal test: construct a tiny DataFrame with a float column containing exactly `1.0`, assert `(col == True).sum() != (col < 0.05).sum()` demonstrates the trap, then assert the audit script's actual filtering logic (`< 0.05` on non-null rows) gives the expected count on a fixture mirroring `pool_cutoff_statistics.csv`'s schema.
- Run the full test suite: `pytest -q`.
- Attempt a fresh-clone reproduction of `scripts/run_ir_evidence_audit.py` in a scratch worktree *after* Stage 2's carve-out is applied, to confirm the FileNotFoundError on `final_revision_task1`/`task4` is actually resolved: `git clone --no-local . /tmp/repro-check && cd /tmp/repro-check && python scripts/run_ir_evidence_audit.py --output-dir /tmp/repro-out`.
- **Validation**: `pytest -q` exits 0; the fresh-clone run above completes without `FileNotFoundError` and produces byte-identical `unified_configuration_results.csv` (diff against the already-committed one).
- **Rollback**: none needed — this stage is additive (new test) and verification-only (no repo mutation beyond the new test file).

## Stage 9 — Final Git-status and diff review

- `git status` (expect only the intended moves/renames/edits/new test, nothing else).
- `git diff --stat pre-hygiene-cleanup-<date>` to review the full change surface before merging.
- `git log --stat -1` per commit if the work was split into multiple commits (recommended: one commit per stage, not one giant commit, so any single stage can be reverted independently later).
- **Validation**: manual review of the full diff stat; confirm no file under `reports/*/raw_calls/`, `data/raw/`, or any provider-transcript path was accidentally staged (secrets-adjacent content should never move without a fresh grep-for-secrets pass, even though none were found in this audit).
- **Rollback**: `git reset --soft pre-hygiene-cleanup-<date>` (keeps working-tree changes, unstages) or `git reset --hard pre-hygiene-cleanup-<date>` (full revert) — **only with explicit user confirmation**, per this repo's own git-safety norms; never as a default action.

---

## Explicit non-goals (do not do these as part of this cleanup)

- Do not reorganize the 77 `reports/*` timestamped directories into a different naming scheme — the existing timestamp-suffix convention is consistent and searchable; only the specific stale/duplicate/superseded ones identified above should move.
- Do not touch `data/raw/`, `data/processed/`, or anything under `.venv/`/`.mypy_cache/`/`.ruff_cache/`/`.pytest_cache/` — already correctly gitignored, zero findings.
- Do not attempt the "pending query-clustered real-LLM re-analysis" as part of a hygiene cleanup — that is a statistics/analysis task (see `dependency_map.csv`'s last row and the meta-audit), not a file-organization task, and is out of scope here.
