# Repository Hygiene Audit

**Status: read-only audit. No file was deleted, moved, renamed, or rewritten in producing this document.** All findings are based on inspecting the repository as it exists on disk plus `git status`/`git log`; no experiment was re-run and no result was recomputed.

**Companion deliverables** (same directory): `repository_inventory.csv` (822 rows), `dependency_map.csv`, `proposed_moves.csv`, `canonical_artifacts.md`, `cleanup_execution_plan.md`.

**Granularity note**: `repository_inventory.csv` is file-level for `src/`, `scripts/`, `tests/`, `configs/`, `schemas/`, `prompts/`, `docs/`, `figures/`, and all top-level loose files, and directory-level (one row per named run/report) for `reports/*` (77 dirs), `experiments/*` (9 dirs), `outputs/*` (55 dirs), and the `papers/JDIQ_2026/submission/` bundle — enumerating every one of the several thousand individual files in those trees (many are per-query JSONL/CSV shards) would not add audit value over a directory-level classification. This is stated explicitly per the task's own instruction to adapt structure to the actual repository.

---

## 1-2. Repository inspection and classification

The repo is a single-codebase, multi-track research project (per `PROJECT_STATUS.md`): a submitted JDIQ_2026 manuscript, a planned `negative_result_2026` companion paper, and an active "consistency-aware pivot." Total size ≈9.5GB, dominated by `reports/` (4.2GB, 77 timestamped experiment/audit directories), `data/` (3.1GB, mostly gitignored raw/processed BEIR-family datasets), and `experiments/` (1.6GB). Only 2,243 files are actually git-tracked; the bulk of the disk footprint is untracked-by-design (raw datasets, per-query intermediates).

Top-level purpose of each major directory:
- `src/consistency_ranker/` — canonical library code (greedy/exact repair, statistical inference, per-study submodules).
- `scripts/` — ~110 driver scripts, one per experiment/pipeline stage; no subdirectory structure (flat).
- `tests/` — 79 test files.
- `configs/` — 9 frozen JSON experiment specs.
- `data/` — raw/processed BEIR-family datasets (mostly gitignored, regenerable via `scripts/download_beir_via_irds.py` etc.).
- `reports/` — 77 timestamped experiment/audit output directories plus a handful of loose root docs/CSVs.
- `experiments/` — 9 older (pre-mid-July) one-off audit workspaces.
- `outputs/` — 55 pipeline-run directories, several from an abandoned March-2026 pipeline (see §7 below).
- `papers/` — `JDIQ_2026/` (submitted manuscript + submission bundles), `negative_result_2026/` (planning docs only), and an accidental empty `papers/papers/` nesting.
- `docs/` — ~35 status/policy/historical documents, several explicitly self-labeled superseded.
- `figures/`, `schemas/`, `prompts/`, `batch/`, `notebooks/` — small, single-purpose.

Full per-item classification (12-category schema from the task brief) is in `repository_inventory.csv`. Summary counts:

| Classification | Count |
|---|---:|
| canonical source code | 395 |
| historical but useful artifact | 111 |
| reproducibility documentation | 102 |
| duplicate | 60 |
| stale or superseded artifact | 48 |
| canonical raw data | 34 |
| canonical experiment configuration | 19 |
| publication-ready figure or table | 17 |
| canonical derived results | 16 |
| unclear and requiring review | 14 |
| generated cache or temporary file | 4 |
| manuscript source | 2 |
| **Total** | **822** |

I verified "old" is not conflated with "obsolete": e.g. `reports/full_calibrated_core/` (2026-07-15, over two weeks old relative to this session) is classified **canonical derived results**, not stale, because it is the direct, load-bearing input to `scripts/run_ir_evidence_audit.py` and the source of the manuscript's own quoted numbers. Conversely, `outputs/pub_vote_cmp_all4/` (2026-03-24, chronologically not much older) is classified **stale** because nothing current depends on it (see §7).

---

## 3. Dependency tracing

Full table in `dependency_map.csv`, covering: original construction, classical retrieval evaluation, greedy repair, exact repair, larger-pool analysis, repair-frontier, extraction study, repair-diagnostic, the final IR evidence audit, the meta-audit, and the (not-yet-existing) query-clustered re-analysis.

Headline findings:
- **Two of the six source families behind `scripts/run_ir_evidence_audit.py` are not reproducible from a fresh clone.** `reports/final_revision_task1_pool_cutoff_20260715/` and `reports/final_revision_task4_exact_baseline_fairness_20260715/` are entirely excluded by a blanket `.gitignore` rule (`reports/final_revision_*/`, line 351) — including their small canonical summary tables (`pool_cutoff_statistics.csv` is 250KB; the whole `task4/tables/` directory is 1.7MB), not just the legitimately-bulky 1.6GB `outputs/` scratch subdirectory sitting alongside them. Every other structurally-similar report family in this repo (`offline_active_acquisition_pilot_20260728T142414Z/`, `policy_selection_20260726T030500Z/`) has a **surgical** carve-out per `docs/ARTIFACT_POLICY.md`'s own stated criteria ("track... tabular per-checkpoint CSVs needed for independent recomputation, but keep the two bulky raw event logs local"); this pair never got the same treatment.
- **The three "this-session" real-LLM studies (`repair_frontier`, `extraction_study`, `repair_diagnostic`) are three analyses of one shared 6-real-query sample**, not three independent data collections — each source `FINAL_REPORT.md` states this plainly ("identical set used by the repair-frontier and extraction studies") but it is easy to miss reading any single report in isolation. See the meta-audit for the statistical consequences.
- **No canonical file yet implements the query-clustered re-analysis** the meta-audit recommends (cluster/block bootstrap over the 6 `query_id` groups instead of the 120 rows). This is a genuine, currently-open gap in the dependency chain, not an oversight in this hygiene audit — it is called out explicitly in `dependency_map.csv`'s final row.
- **Manuscript numbers are hand-typed, not generated.** `papers/JDIQ_2026/manuscript/main.tex` contains zero `\input{}` statements pulling in any generated `.tex` table fragment; every cited statistic (e.g. "$0.554$" for CombSUM) is a literal typed into the source. I independently confirmed this specific number matches `table_primary_macro_method_comparison.csv` to 13 significant digits, so the numbers are currently *correct*, but there is no automated check preventing future drift between the tables and the prose.

---

## 4. Reproducibility risks

- **Scripts that overwrite previous outputs**: `scripts/run_ir_evidence_audit.py`'s `run(output_dir)` calls `output_dir.mkdir(parents=True, exist_ok=True)` and unconditionally overwrites every file inside — safe only because the convention in this repo is a fresh timestamped directory per invocation; there is no built-in guard against accidentally re-pointing it at an existing directory.
- **Deterministic seeds**: `src/consistency_ranker/statistical_inference.py`'s `bootstrap_mean_interval` takes an explicit `seed: int = 13` default — good practice, present everywhere it's used.
- **Missing environment/dependency specs**: `requirements.txt` exists at root; SCIP (used by `reports/exact_open_source_ilp_repair_investigation/`) is an external solver dependency not pinned there — `docs/READ_ME_FIRST_FOR_AI.md:39` notes it's "free and open-source... `pip install`" but the exact package/version isn't in `requirements.txt` or `pyproject.toml`.
- **Inconsistent naming conventions**: two near-identical directory names for the same concept (`exact_ilp_repair_investigation` vs. `exact_open_source_ilp_repair_investigation`) coexist, one stale.
- **Timestamped reports with unclear provenance**: none found to be missing a `FINAL_REPORT.md`/`RUN_CONFIG.json`/`FINAL_SUMMARY.json` triple in the ones inspected — provenance is generally good within each directory; the problem found is cross-directory (which one is current), not within-directory.
- **Results that cannot be regenerated**: the two `final_revision_task1`/`task4` directories above (untracked); the real-LLM raw provider transcripts (correctly, deliberately untracked per `docs/ARTIFACT_POLICY.md` — this is not a defect, it's policy, but it does mean the six real queries' raw judgments are single-machine-local and not backed up in Git).
- **Manuscript numbers copied manually**: confirmed above (§3).
- **Figures with no source script**: the 8 loose root-level PDFs (`figure1_preference_graph_pipeline.pdf` etc.) have no co-located generator script at repo root; the current figure set (`papers/JDIQ_2026/manuscript/figures_v2/generate_figures.py`) does have one. The root PDFs are pre-JDIQ_2026 era and likely predate the current figure-generation convention entirely.
- **Duplicated statistical utilities**: none found — `statistical_inference.py` appears to be the single shared module; no second bootstrap/Holm implementation turned up in a repo-wide grep.
- **Inconsistent definitions of "independent observation"**: this is the meta-audit's central finding, reprised here because it is also a repo-hygiene/provenance issue, not just a statistics issue — `extraction_results.jsonl`/`diagnostic_results.jsonl`/`frontier_results.jsonl` each carry a `query_id` column (6 distinct values, 120 rows), but nothing in the file, the `FINAL_SUMMARY.json`, or `FINAL_IR_EVIDENCE_AUDIT.md` computes or states the effective/clustered sample size next to the raw row count.
- **Code that treats repeated configurations as independent queries**: confirmed directly — `bootstrap_mean_interval` in `discovery.py`/`evaluation.py` resamples all 120 rows i.i.d. with no `query_id`-aware clustering; `repair_diagnostic`'s `FEATURE_ASSOCIATIONS.csv` computes Pearson/Spearman p-values with `n=120` for the same reason.
- **Known bug fixes not protected by tests**: confirmed — grepping `tests/` for `holm_active_ms1_family` or `holm_significant_at_0` returns zero matches; `scripts/run_ir_evidence_audit.py` (which contains both the docstring-documented fix and the mechanism that could regress) is imported by zero test files. See `cleanup_execution_plan.md` Stage 8 for a concrete minimal regression test.

---

## 5. Git hygiene

- **Large generated files tracked unnecessarily**: several large CSVs (5-19MB) and two submission zips (28MB, 12MB) plus two more zip/tar.gz pairs (~6.5MB each ×2) are tracked, and multiple of these are **byte-level duplicates** of already-tracked content — e.g. `reports/normalization_protocol_audit_20260714/tables/independent_protocol_paired_deltas.csv` (19.2MB) is duplicated verbatim at `papers/JDIQ_2026/submission/final_anonymous/supplemental/tables/normalization_protocol_audit/independent_protocol_paired_deltas.csv` (19.1MB); similarly for `full_calibrated_core/tables/full_paired_deltas.csv` and its supplemental-bundle copy. This looks like an intentional "frozen submission snapshot" pattern (defensible for anonymous-review reproducibility) rather than accidental drift, but it roughly doubles Git's stored size for these files and is worth documenting as intentional in `canonical_artifacts.md` (done) rather than leaving implicit.
- **Missing small result files**: none found — the opposite problem (§4) is more prominent here (small canonical files excluded by an over-broad `.gitignore` rule).
- **Secrets/tokens/credentials**: checked directly — grepped all tracked files for API-key-shaped patterns and grepped every `raw_calls/*.jsonl`/`provider_usage.jsonl` file (untracked, but content-scanned) for literal key prefixes (`sk-`, `AIzaSy`, `AKIA`) and `Authorization`/`Bearer` header values. **No real secrets found** — the only substring hits were false positives (e.g. "dis**k-**resident" containing `sk-`). No `.env` files are tracked. No `.pem`/credentials JSON files found anywhere in the tree.
- **Machine-specific paths**: `/home/soroush/` appears hardcoded in ~12 tracked files, all inside historical `reports/*/scripts/` snapshots or `experiments/` one-offs (e.g. `reports/jdiq-overnight-cont-20260713-230229/scripts/phase02_fix_path_leak.py` — ironically a script *about* fixing a path leak) — none are in the live `src/`/`scripts/`/`tests/` trees that would affect current reproducibility.
- **Editor/OS files**: none found (no `.DS_Store`, `Thumbs.db`).
- **Python caches**: none tracked (`__pycache__`, `*.pyc` all correctly gitignored and absent from `git ls-files`).
- **Temporary LaTeX files**: correctly gitignored (`.aux`, `.log`, `.fls`, `.fdb_latexmk`, `.blg`, `.out`, `.synctex.gz`, `.xdv` all listed for `papers/JDIQ_2026/manuscript/`).
- **Duplicated PDFs**: the 8 root-level legacy figure PDFs vs. the current `figures_v2/` set (different content, not byte-duplicates, but likely superseded renders of the same underlying findings — see `proposed_moves.csv`).
- **Report directories that should be retained but documented**: `outputs/pub_vote_cmp_all4/`, `outputs/pub_vote_cmp_v2/`, `outputs/q1_journal_package/` — do not delete or move (still-functional script defaults depend on them), but need an in-place "historical, not canonical" banner (see `cleanup_execution_plan.md` Stage 6).
- **Files that belong in `.gitignore`**: the inverse problem is the real finding here — see §4/`proposed_moves.csv` last row.
- **Accidental empty directory**: `papers/papers/JDIQ_2026/submission/final_anonymous/` — a fully empty, untracked, unreferenced nested duplicate of the `papers/JDIQ_2026/submission/final_anonymous/` path, almost certainly created by a stray `mkdir -p`/`cp -r` run from inside `papers/` instead of the repo root. Zero-risk deletion candidate.

---

## 6. Target repository structure

The existing `src/ scripts/ configs/ data/ reports/ figures/ tests/ docs/` skeleton is already sound and matches the requested target structure reasonably well; this repo does **not** need a wholesale re-architecture. The specific, minimal adaptations proposed (all detailed with reason/references/risk in `proposed_moves.csv`):

- Introduce `reports/_archive/`, `papers/_archive/`, `figures/legacy/`, `docs/assets/legacy_screenshots/` as landing spots for the stale/historical items identified above — a light, additive convention, not a restructuring of the 77 live report directories.
- No changes proposed to `src/`, `scripts/`, `tests/`, or `configs/` internal structure — these are already flat, single-purpose, and consistently named (aside from the one `exact_ilp_repair_investigation` naming collision noted above, which lives under `reports/`, not `src/`/`scripts/`).
- `manuscript/` already exists correctly nested under `papers/JDIQ_2026/`; no change proposed.
- `tables/`/`figures/` as *manuscript-adjacent* artifacts already live correctly under each report/paper directory (e.g. `reports/ir_evidence_audit_20260729T182949Z/tables/`); no separate top-level consolidation is proposed, since these are already tightly coupled to their generating report and moving them would break that coupling for no benefit.

---

## 7. Canonical artifacts and conflicts

Full detail in `canonical_artifacts.md`. The single most important finding: **`README.md`, `docs/READ_ME_FIRST_FOR_AI.md`, `reports/README.md`, and even `PROJECT_STATUS.md` (in one line) all still name `outputs/pub_vote_cmp_all4/paper_package/` as "the canonical evidence package."** This pipeline was last touched 2026-03-24 and is referenced nowhere in the actually-submitted `papers/JDIQ_2026/manuscript/main.tex`. The manuscript's real, verified-matching numeric backbone is `reports/full_calibrated_core/outputs/calibrated_all4/paper_package/tables/` (2026-07-15) — a fact none of the four "start here" documents currently reflect. `papers/JDIQ_2026/MASTER_EVIDENCE_INVENTORY.csv`/`SECTION_EVIDENCE_MAP.csv`, which `PROJECT_STATUS.md` cites as authoritative for evidence-to-claim mapping, predate `full_calibrated_core` by ~3 days and have the identical staleness. This is a genuine conflicting-source-of-truth problem, not a hypothetical one — I verified it by direct number-matching (§3), not by trusting either document's self-description.

---

## 8. Staged cleanup plan

See `cleanup_execution_plan.md` for the full 9-stage plan with validation commands and rollback steps for each stage (safeguards → ignore rules → directory normalization → moves/renames → path repairs → report consolidation → documentation updates → tests/reproducibility verification → final diff review). No stage has been executed.

---

## Final response

See below.
