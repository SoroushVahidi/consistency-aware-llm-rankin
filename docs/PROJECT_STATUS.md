# Project Status (current `main`)

**Authoritative for:** current state of `main` -- what is complete, active,
canonical, exploratory, superseded, historical, or internal-only, and what to
work on next.

**Not authoritative for:** exact scientific numbers (use
`papers/JDIQ_2026/manuscript/main.tex` + `papers/JDIQ_2026/EVIDENCE_PROVENANCE_20260730.md`),
contribution classification detail (use `docs/CONTRIBUTIONS.md`), module
architecture (use `docs/ARCHITECTURE.md`), or the experiment-family index
(use `docs/EXPERIMENTS.md`). This document links to those rather than
duplicating them.

**Relationship to the root `PROJECT_STATUS.md`:** that file is the detailed
handoff narrative for the `fix/outcome-f-production-operating-point` branch
(28 commits, 2026-07-28 to 2026-07-31), which merged into `main` via PR #44
(`76dd680`, merged 2026-07-31T14:00:09Z). It remains valuable as dated
history/context for that work but no longer describes "the current branch" --
`main` *is* that work now, plus two small follow-up fixes (`d6151d8`,
`4b1e610`) and this repo-hygiene pass. This file is the current snapshot;
that file is the archived narrative that produced it.

---

## Verified state at time of writing

- Branch: `main`. HEAD before this pass: `4b1e610`. Local `main` == `origin/main` (0 ahead / 0 behind) when this pass started.
- GitHub Actions CI has been failing on every run since at least 2026-07-16 due to a **GitHub account billing/spending-limit issue** ("recent account payments have failed or your spending limit needs to be increased"), not a code problem -- every job aborts in ~2-12s before installing anything. **This requires the repository owner to resolve in GitHub billing settings; it cannot be fixed by a commit.** See `docs/RELEASE_READINESS.md`. **Until resolved, `scripts/run_cloud_validation.py` (`make cloud-validate` / `cloud-validate-solver` / `cloud-validate-all`) is the canonical way to validate this repo's state** -- it reproduces both `ci.yml` jobs natively on this machine. See `docs/EXPERIMENTS.md` "Cloud Validation".
- A genuinely fresh clone previously failed/errored on ~64 tests (silent dependency on locally-prepared datasets, plus one gitignored-by-accident source directory). **Fixed this pass** -- see §"Fresh-checkout reproducibility" below.
- Gurobi 13.0.2 with a working academic WLS license became available on this machine for the first time on 2026-07-31, enabling an internal solver cross-validation (see `docs/CONTRIBUTIONS.md` §1.6).

---

## Subsystem status

| Subsystem | Status | Notes / entry point |
|---|---|---|
| Core pairwise-preference and ranking algorithms | **Canonical, stable** | `src/consistency_ranker/{pairwise_prefs,graph_construction,baseline_ranking,evaluation}.py`; see `docs/ARCHITECTURE.md` §2-3 |
| Exact MWFAS repair (SCIP) | **Canonical, complete** | `mwfas_solver.py`; 1,025/1,025 canonical queries proven optimal (`reports/exact_open_source_ilp_repair_investigation/`) |
| Gurobi backend | **Internal validation only, complete** | Optional legacy backend, never used for manuscript results; cross-validated against SCIP 2026-07-31 (perfect agreement, 1,025/1,025) -- see `docs/CONTRIBUTIONS.md` §1.6 and `reports/gurobi_vs_scip_solver_cross_validation_20260731T162314Z/` |
| Repaired-vs-unrepaired evaluation | **Canonical, concluded (negative/conditional)** | The manuscript's central result; see `docs/CONTRIBUTIONS.md` §1.1 |
| Statistical inference (incl. cluster-aware) | **Canonical infra; cluster-aware correction complete** | `src/consistency_ranker/statistical_inference.py`; corrected a real pseudo-replication bug in the real-LLM pilot re-analysis |
| Real-LLM reanalysis | **Complete, canonical for inference on that pilot** | `reports/real_llm_clustered_reanalysis_20260730T023745Z/` |
| Extraction study / repair frontier / repair diagnostic | **Exploratory, row-level; superseded for inference by clustered reanalysis** | `docs/CONTRIBUTIONS.md` §1.3 |
| Repository-scale oracle-headroom (preserve-vs-repair) | **Concluded -- NO-GO** | `reports/repository_scale_headroom_analysis/research_decision.md` |
| Policy selection ("Outcome F") | **Concluded (negative result); production locked to fixed default** | `src/consistency_ranker/policy_selection/production_config.py` |
| Multi-provider evaluation (counterfactual benchmark) | **Engineering, canary stage, paused (not abandoned)** | 3/4 providers pass a clean canary (Cohere blocked); bounded micro-pilot designed but never executed |
| Consistency-aware pivot (active-acquisition / regularized-aggregation / stopping-rule) | **Three real-oracle pilots complete**; not yet a deployment-ready combined contribution | See root `PROJECT_STATUS.md` "Consistency-aware pivot" section for full narrative (unchanged by this pass) |
| Dataset preparation | **Working, but was an implicit, undocumented unit-test prerequisite until this pass** | `scripts/download_datasets.py` (network) + `scripts/prepare_datasets.py`; now cleanly separated into the `real_data` pytest tier -- see `docs/EXPERIMENTS.md` "Test Tiers" |
| Manuscript (`papers/JDIQ_2026/`) | **Submitted, finalized draft** (commit `e873017`, 2026-07-15; unchanged since) | `papers/JDIQ_2026/manuscript/main.tex`; do not use `CANONICAL_PAPER_STORY.md` or `CONTRIBUTION_AUDIT.md` (both one revision behind, self-marked superseded) |
| Packaging / release readiness | **Documented, `make repo-ready` exists** | `docs/RELEASE_READINESS.md`; CI currently non-functional due to the billing issue above, independent of code readiness |
| Raw-provider-transcript archival | **Procedure documented, no destination configured** | `docs/ARTIFACT_POLICY.md` "External Archive Procedure" -- a public-release condition, not a merge blocker |

## Fresh-checkout reproducibility (this pass, 2026-07-31)

Reproduced in an isolated clone (not this working directory): `pytest -q`
gave **52 failed, 1290 passed, 1 skipped, 12 errors** -- 64 non-passing tests,
matching a user-reported "approximately 64" exactly. Root causes:

1. **~63 tests** silently depended on `data/processed/{beir/scidocs,beir/fiqa,hotpotqa,bright}/*.jsonl` -- multi-GB, network-fetched (`scripts/download_datasets.py` + `scripts/prepare_datasets.py`), gitignored by design, present only because this developer's machine had run them before. Fixed by introducing a `real_data` pytest marker (`pyproject.toml`), deselected by default (`addopts = "... -m \"not real_data\""`), with a graceful skip-with-instructions fallback (`tests/conftest.py`) for anyone who explicitly opts into `make test-real-data` without preparing data first.
2. **1 test** (`test_task3_ranker_dependence.py`) failed to even *collect* because `reports/final_revision_task3_ranker_dependence_20260715/scripts/` (244KB of pure Python source, needed at module-import time) was accidentally caught by the blanket `reports/final_revision_*/` `.gitignore` rule -- unlike its siblings (`task1`, `task4`), it had no negation carve-out. Fixed by adding the same carve-out pattern already used for `task1`/`task4` (track everything except the genuinely bulky `outputs/`).

Verified fix in a second, independent fresh clone: `pytest -q` -> **1306
passed, 0 skipped, 0 failed, 64 deselected**; `make test-full` -> `OK (0
skipped)`. Regression guard: `tests/test_fresh_checkout_reproducibility.py`.

## Known blockers (not fixable by a commit)

- **GitHub Actions billing.** See "Verified state" above. Action: repository owner must resolve in GitHub billing settings.
- **Cohere structured-output enforcement** for the counterfactual benchmark (unrelated to the above) -- see root `PROJECT_STATUS.md` for full detail; unchanged by this pass.

## Exact next action

1. Repository owner resolves the GitHub Actions billing block so CI can run at all again (currently the single highest-priority item -- no amount of code correctness is visible to CI until this is fixed).
2. Once CI runs, confirm the fresh-checkout fix holds on an actual GitHub Actions runner (this pass validated it in a local isolated clone only).
3. For the mature program: no further action recommended -- it is a complete, submitted manuscript. For the consistency-aware pivot: see root `PROJECT_STATUS.md`'s own "Exact next action" (unchanged, still current).

## How to resume safely

1. Read `docs/CONTRIBUTIONS.md` first (what exists and its status), then this file (what's active/unfinished), then root `PROJECT_STATUS.md` if branch-level historical narrative is needed.
2. Re-run `git fetch origin && git status --short --branch && git rev-parse HEAD` -- do not trust any hash in any status document once new commits exist.
3. Run `pytest -q` (should be green with 64 deselected on any machine) before assuming anything is broken; only run `make test-real-data` if you have prepared datasets and specifically need to test that tier.
