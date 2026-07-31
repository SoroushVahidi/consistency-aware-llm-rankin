# Repository Layout

**Purpose**: a technical, internal reference for where things live and how new work should be organized. Not paper prose. Last updated 2026-07-30 (repository organization Stage 2, `reports/repo_structural_org_stage2_20260730T014347Z/`).

If this document and `PROJECT_STATUS.md` ever disagree on canonical evidence location, trust `PROJECT_STATUS.md` (it self-declares as the canonical entry point) and re-verify against Git/code directly.

## Top-level directories

| Directory | Purpose |
|---|---|
| `src/consistency_ranker/` | Reusable library code: graph construction, repair (`greedy_fas.py`, `mwfas_solver.py`), evaluation (`qrels_reference.py`, `evaluation.py`), statistical primitives (`statistical_inference.py`), and one submodule per major study family (`repair_frontier/`, `extraction_study/`, `repair_diagnostic/`, `policy_selection/`, etc.). |
| `scripts/` | Executable entry points — one script per experiment/analysis/audit/maintenance task. Flat namespace (no subdirectories); see naming convention below. |
| `configs/` | Frozen JSON experiment specifications (e.g. `preserve_repair_experiment_spec_v1.json`). |
| `data/` | Raw/processed BEIR-family datasets. Mostly gitignored by design (see "What must not be stored" below); regenerate via `scripts/download_beir_via_irds.py`, `scripts/prepare_hotpotqa.py`, etc. |
| `reports/` | Human-readable experiment/audit reports, one directory per run — see "Timestamped reports" below. This is also where canonical machine-readable result *tables* live (nested under each report's own `tables/`), since results and the report describing them are tightly coupled and should not be separated. |
| `figures/` | Curated, publication-oriented figures with provenance (`figures/manuscript/`, `figures/graphical_abstract/`); `figures/legacy/` holds pre-JDIQ_2026 renders (moved here in Stage 2, no longer at repo root). |
| `tests/` | Automated tests, one file per module/feature area, `pytest`-discovered. |
| `docs/` | Technical documentation and repository guidance — status docs, reproduction guides, policy documents (`ARTIFACT_POLICY.md`), and `docs/historical/` for superseded root-level docs (see below). |
| `papers/` | Manuscript workspaces, one per paper track (`JDIQ_2026/`, `negative_result_2026/`). Scientific content is out of scope for repository-organization work — this document does not describe or prescribe manuscript structure. `papers/_archive/` holds non-scientific historical artifacts (e.g. an early rejected-venue draft zip). |
| `outputs/` | Legacy per-pipeline result trees, mostly predating the `reports/<study>/` convention. Several (`pub_vote_cmp_all4/`, `pub_vote_cmp_v2/`, `q1_journal_package/`) are historical and now carry an in-place `HISTORICAL.md` marker (Stage 2) rather than being moved, because multiple scripts still default to these exact paths. |
| `experiments/` | Older (pre-mid-July) one-off audit workspaces, predating the `reports/<study>_<timestamp>/` convention. Not actively added to; new work belongs under `reports/`. |
| `.claude/`, `.github/` | Tooling/CI configuration, not experiment content. |

## Where canonical results live

There is no single `results/` directory in this repository (the existing `reports/<study>/tables/` pattern already serves that role, tightly coupled to each study's own report and reproduction script — introducing a separate top-level `results/` would duplicate that coupling, not clarify it, so this stage did not force one). The **current classical-study canonical numeric backbone** is:

```
reports/full_calibrated_core/outputs/calibrated_all4/paper_package/tables/
```

extended by `reports/normalization_protocol_audit_20260714/`, `reports/candidate_pool_conditional_audit_20260714/`, `reports/final_revision_task1_pool_cutoff_20260715/`, `reports/final_revision_task4_exact_baseline_fairness_20260715/`, and `reports/exact_open_source_ilp_repair_investigation/`. See `docs/REPRODUCTION_CANONICAL.md` for the exact pipeline map and `papers/JDIQ_2026/EVIDENCE_PROVENANCE_20260730.md` / `reports/repo_preparation_stage1_20260730T011354Z/canonical_evidence_inventory.csv` for the full evidence-to-claim mapping, including the real-LLM exploratory studies and pending re-analysis.

**Historical/superseded evidence packages** (`outputs/pub_vote_cmp_all4/`, `outputs/pub_vote_cmp_v2/`, `outputs/q1_journal_package/`) are marked in place with `HISTORICAL.md` files — kept, not deleted, because reproduction scripts still default to them.

## Where timestamped reports live

Convention (already followed by most of `reports/`, confirmed and not changed this stage):

```
reports/<study_name>_YYYYMMDDTHHMMSSZ/
```

e.g. `reports/ir_evidence_audit_20260729T182949Z/`, `reports/repair_frontier_20260729T144742Z/`. Each such directory should contain, at minimum, a human-readable `FINAL_REPORT.md` (or equivalently-named top-level summary) and, where the study produces one, `RUN_CONFIG.json`/`FINAL_SUMMARY.json` for machine-readable provenance. Stable multi-task studies that don't fit the single-timestamp pattern (e.g. `reports/final_revision_task1_pool_cutoff_20260715/`) use a `task<N>_<description>_YYYYMMDD` variant — acceptable, not renamed this stage (renaming would break the `.gitignore` carve-out and `scripts/run_ir_evidence_audit.py`'s hardcoded path constants for zero clarity gain).

## How historical artifacts are labeled

Two mechanisms, used depending on whether the artifact can move safely:

1. **In-place marker** (`HISTORICAL.md` in the directory) — used when downstream scripts still depend on the exact path (e.g. `outputs/pub_vote_cmp_all4/HISTORICAL.md`).
2. **Move to an `_archive/` subdirectory** (`reports/_archive/`, `papers/_archive/`) — used when no active script/test depends on the exact path, verified by repository-wide search before moving. See `reports/repo_structural_org_stage2_20260730T014347Z/duplicate_directory_resolution.md` for the specific families resolved this way (`exact_ilp_repair_investigation`, the `jdiq-overnight-*` pair, the `repo_publication_audit.md` family, `docs/historical/` for 15 root-level docs).

Prior reports that quote an old path in prose (e.g. "prepared under `reports/jdiq-overnight-.../artifact_prep/`") are **left unedited** — they are accurate historical statements, not live references, and editing them would falsify the historical record. Do not "fix" a quoted path inside an already-generated report.

## How new experiments should be named

- **Timestamped report directory**: `reports/<study_name>_YYYYMMDDTHHMMSSZ/` (UTC, `date -u +%Y%m%dT%H%M%SZ`).
- **Scripts**:
  - `run_<study>.py` — executes an experiment/pipeline stage.
  - `analyze_<study>.py` / `summarize_<study>.py` — post-processes already-collected results.
  - `audit_<scope>.py` — reviews existing evidence without new data collection.
  - `validate_<scope>.py` / `verify_<scope>.py` — checks outputs against expected invariants.
- Avoid ambiguous qualifiers (`final`, `new`, `latest`, `complete`) as the *only* distinguishing part of a name — if two directories differ only by such a word, add the date/timestamp instead (this repo already does this correctly almost everywhere; the one confusing pair found this stage, `exact_ilp_repair_investigation` vs. `exact_open_source_ilp_repair_investigation`, has been resolved — see `duplicate_directory_resolution.md`).
- Do not rely on "the most recently modified directory matching a pattern" to mean "the canonical one" — always use an explicit, hardcoded path or a documented pointer (`PROJECT_STATUS.md`'s evidence-registry section, `EVIDENCE_PROVENANCE_20260730.md`). Confirmed this stage: no script in `scripts/` or `src/consistency_ranker/` currently selects a "latest" directory by glob/mtime ordering (see `duplicate_directory_resolution.md`'s final section) — keep it that way.

## How scripts should refer to repository-relative paths

Every script that needs the repo root computes it the same way: `_REPO_ROOT = Path(__file__).resolve().parent.parent` (or `.parent.parent.parent` depending on nesting depth), then builds all other paths by joining onto that. This pattern is already used consistently (e.g. `scripts/run_ir_evidence_audit.py`) and should be followed for any new script rather than using a hardcoded user-specific absolute path or a bare relative path that only works from one particular working directory. A handful of older, one-off scripts under `reports/*/scripts/` and `experiments/*/` still hardcode absolute paths — these are historical/frozen and were not rewritten this stage (rewriting a frozen, already-executed report's generator script changes nothing about its already-produced output and risks introducing new bugs into dead code).

## What must not be stored in the repository

Per `docs/ARTIFACT_POLICY.md` (unchanged, not duplicated here): provider API caches/raw transcripts/judgment stores that may contain prompts, completions, or credentials; large third-party datasets under `data/raw/`/`data/processed/` (regenerate instead); large anonymous-supplementary bundles; rendered manuscript page images/contact sheets; virtual environments and tool caches (`.venv/`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`); machine-absolute paths, PID locks, host-bound wrapper scripts; regenerable checkpoints not cited as frozen evidence.
