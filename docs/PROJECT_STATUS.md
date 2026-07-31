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

## Document authority hierarchy

One document is authoritative for each concern below. If two documents ever
disagree, trust the one listed here, not the other.

| Question type | Authoritative document |
|---|---|
| Orientation, how to install/validate, where to look | `README.md` |
| What this repo contributes and does not contribute | `docs/CONTRIBUTIONS.md` |
| Current state, what's unfinished, subsystem status | `docs/PROJECT_STATUS.md` (this file) |
| Concise operational guide for an agent | `docs/AGENT_GUIDE.md` |
| Module layering, canonical implementations, terminology | `docs/ARCHITECTURE.md` |
| Experiment families, entry points, test tiers, evidence inventory | `docs/EXPERIMENTS.md` |
| Machine-readable per-claim evidence/status | `docs/claim_evidence_registry.yaml` |
| What belongs in Git vs. local/external archive | `docs/EXPERIMENT_ARTIFACT_POLICY.md` (specifics), `docs/ARTIFACT_POLICY.md` (broad policy) |
| Operational validation contract (what must pass before merge) | `docs/RELEASE_READINESS.md` + `docs/EXPERIMENTS.md` "Cloud Validation" |
| Merge vs. public-release requirements | `docs/RELEASE_CHECKLIST.md` |
| How to contribute (setup, PR expectations, wording rules) | `CONTRIBUTING.md` |
| Tracked open work (issues, labels) | [GitHub issues](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/issues) -- textual context always lives in this file too, not only in issue numbers |
| Exact scientific numbers | `papers/JDIQ_2026/manuscript/main.tex` (+ `papers/JDIQ_2026/EVIDENCE_PROVENANCE_20260730.md` for provenance) |
| Detailed pre-merge branch history | root `PROJECT_STATUS.md` (historical narrative, not current state) |

Any document not listed here (including single-purpose historical files
under `docs/`) is secondary detail reachable by following links from the
table above, not a competing source of truth.

---

## Verified state at time of writing

- Branch: `main`. HEAD before this pass: `4b1e610`. Local `main` == `origin/main` (0 ahead / 0 behind) when this pass started.
- GitHub Actions CI has been failing on every run since at least 2026-07-16 due to a **GitHub account billing/spending-limit issue** ("recent account payments have failed or your spending limit needs to be increased"), not a code problem -- every job aborts in ~2-12s before installing anything. **This requires the repository owner to resolve in GitHub billing settings; it cannot be fixed by a commit.** See `docs/RELEASE_READINESS.md`. **Until resolved, `scripts/run_cloud_validation.py` (`make cloud-validate` / `cloud-validate-solver` / `cloud-validate-all`) is the canonical way to validate this repo's state** -- it reproduces both `ci.yml` jobs natively on this machine. See `docs/EXPERIMENTS.md` "Cloud Validation".
- A genuinely fresh clone previously failed/errored on ~64 tests (silent dependency on locally-prepared datasets, plus one gitignored-by-accident source directory). **Fixed this pass** -- see §"Fresh-checkout reproducibility" below.
- Gurobi 13.0.2 with a working academic WLS license became available on this machine for the first time on 2026-07-31, enabling an internal solver cross-validation (see `docs/CONTRIBUTIONS.md` §1.6).

---

## Handoff snapshot (last verified 2026-07-31)

A quick-glance summary for an agent arriving with no prior context. This
section is a pointer to current facts, not a substitute for the sections
below it -- if anything here ever looks stale, trust a fresh check over
this text (`git fetch origin && git status --short --branch`, `gh issue
list --state open`, `gh repo view --json isPrivate,visibility`).

- **Sync:** `main` == `origin/main`, no open PRs, no local uncommitted
  changes, as of the commit that most recently touched this file.
- **Visibility / release:** repository is private; no Git tag and no
  GitHub release exists; package version is pre-1.0 (`pyproject.toml`).
  See `docs/RELEASE_CHECKLIST.md` for what would need to be true before
  either changes.
- **Open GitHub issues:** exactly six, [#45](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/issues/45)-[#50](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/issues/50).
  Each maps to one bucket in "Prioritized remaining work" below; if a new
  issue exists that isn't #45-#50, or one of these is closed, trust
  `gh issue list` over this file.
- **CI:** GitHub Actions is not authoritative (billing block, [#45](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/issues/45));
  `scripts/run_cloud_validation.py` is canonical instead -- see "Public
  release readiness" row below for the last full-tier PASS commit.
- **Governance surface:** `CONTRIBUTING.md`, `.github/pull_request_template.md`,
  four `.github/ISSUE_TEMPLATE/*.yml` forms + `config.yml`, and
  `docs/RELEASE_CHECKLIST.md` are all present and were spot-checked for
  mutual consistency during the pass that added this section.
- **Where to resume:** "Exact next action" below, or whichever open issue
  matches the work you intend to do -- do not start new, untracked work
  without either updating an existing issue or filing a new one.

## Subsystem status

| Area | Status | Canonical implementation | Canonical evidence | Validation | Remaining work |
|---|---|---|---|---|---|
| Core ranking / graph construction | Canonical, stable | `src/consistency_ranker/{pairwise_prefs,graph_construction,baseline_ranking,evaluation}.py` | `reports/full_calibrated_core/` | `tests/test_graph_and_solver.py`, `tests/test_baseline_ranking.py` | None |
| Exact repair -- SCIP | Canonical, complete | `mwfas_solver.py` (`method="scip"/"exact"/"ilp"`) | `reports/exact_open_source_ilp_repair_investigation/` (1,025/1,025 proven optimal) | `tests/test_exact_mwfas_scip.py` | None |
| Exact repair -- Gurobi | Internal validation only, complete | `mwfas_solver.py` (`method="gurobi"`, optional legacy) | `reports/gurobi_vs_scip_solver_cross_validation_20260731T162314Z/` (0 mismatches vs. SCIP on all 1,025), `reports/exact_solver_scaling_study_20260731T162314Z/` (scaling frontier) | `tests/test_mwfas_solver.py` | Never becomes a manuscript claim -- internal-only by design |
| Repaired-vs-unrepaired evaluation | Canonical, concluded (negative/conditional) | evaluation pipeline in `reports/full_calibrated_core/scripts/full_calibration_utils.py` | `reports/full_calibrated_core/`, `reports/normalization_protocol_audit_20260714/` | `main.tex` Table 3-4 | None -- this is the manuscript's settled thesis |
| Statistical inference (incl. cluster-aware) | Canonical infra, complete | `src/consistency_ranker/statistical_inference.py` | `reports/real_llm_clustered_reanalysis_20260730T023745Z/` | `tests/test_statistical_inference.py` | None |
| Real-LLM pilot + reanalysis | Exploratory pilot; clustered reanalysis canonical for its own inference | `src/consistency_ranker/real_llm_reanalysis/` | `reports/real_llm_clustered_reanalysis_20260730T023745Z/` | `tests/test_real_llm_clustered_reanalysis.py` | n=6 queries only -- no cross-dataset generalization evidence |
| Extraction study / repair frontier / repair diagnostic | Exploratory, row-level; superseded for inference | `src/consistency_ranker/{extraction_study,repair_frontier,repair_diagnostic}/` | row-level reports, but see clustered reanalysis for CIs | `tests/test_extraction_study.py` etc. | None planned -- concluded exploratory |
| Repository-scale oracle-headroom | Concluded -- NO-GO | `scripts/run_repository_scale_headroom_analysis.py` | `reports/repository_scale_headroom_analysis/research_decision.md` | `tests/test_repository_scale_headroom_analysis.py` | None -- direction stopped |
| Policy selection ("Outcome F") | Concluded (negative result); production locked to fixed default | `src/consistency_ranker/policy_selection/production_config.py` | `reports/policy_selection_20260726T030500Z/` | `tests/test_policy_selection.py`, `tests/test_production_operating_point.py` | None -- concluded |
| Multi-provider evaluation (counterfactual benchmark) | Engineering, canary stage, paused (not abandoned) | `src/consistency_ranker/counterfactual_benchmark/` | `reports/counterfactual_collector_canary_v2_20260727T161921Z/` | canary-only, no benchmark-scale run | Cohere transport wiring; bounded micro-pilot never executed |
| Consistency-aware pivot | Three real-oracle pilots complete; not yet deployment-ready combined | `src/consistency_ranker/active_acquisition/` | `reports/offline_active_acquisition_pilot_20260728T142414Z/`, `reports/regularized_aggregation_pilot_20260728T164943Z/`, `reports/stopping_rule_pilot_20260728T190000Z/` | pilot-specific tests | Better-calibrated stopping statistic (see root `PROJECT_STATUS.md`) |
| Dataset preparation / `real_data` test tier | Working, cleanly separated | `scripts/download_datasets.py` + `scripts/prepare_datasets.py` | -- | `tests/test_fresh_checkout_reproducibility.py` | None -- fixed 2026-07-31 |
| Packaging | Verified working | `pyproject.toml`, `python -m build` | `.cloud_validation_runs/*/` (sdist+wheel build + wheel-install smoke) | `scripts/run_cloud_validation.py --tier core` | None |
| Fresh-clone / cloud validation | Canonical replacement for blocked GitHub Actions | `scripts/run_cloud_validation.py` | `.cloud_validation_runs/<run_id>/summary.json` (gitignored, local) | `tests/test_cloud_validation.py` (31 tests) | Cross-check against a live GitHub runner once billing is resolved |
| Manuscript (`papers/JDIQ_2026/`) | Submitted, finalized draft (commit `e873017`, 2026-07-15; unchanged since) | -- | `papers/JDIQ_2026/manuscript/main.tex` | `papers/JDIQ_2026/EVIDENCE_PROVENANCE_20260730.md` | None -- do not use `CANONICAL_PAPER_STORY.md`/`CONTRIBUTION_AUDIT.md` (self-marked superseded) |
| Raw-provider-transcript archival | Procedure documented, no destination configured | -- | `docs/EXPERIMENT_ARTIFACT_POLICY.md` "External Archive Procedure" | -- | Select a durable external archive destination -- a public-release condition, not a merge blocker |
| Public release readiness | Blocked only on GitHub Actions billing (external) | -- | this file + `docs/RELEASE_READINESS.md` | `scripts/run_cloud_validation.py --tier core`/`--tier solver`/`--tier real-data`, all three PASS as of `2a5d2b4` | Repository owner resolves GitHub billing; everything else already passes |

## Fresh-checkout reproducibility (this pass, 2026-07-31)

Reproduced in an isolated clone (not this working directory): `pytest -q`
gave **52 failed, 1290 passed, 1 skipped, 12 errors** -- 64 non-passing tests,
matching a user-reported "approximately 64" exactly. Root causes:

1. **~63 tests** silently depended on `data/processed/{beir/scidocs,beir/fiqa,hotpotqa,bright}/*.jsonl` -- multi-GB, network-fetched (`scripts/download_datasets.py` + `scripts/prepare_datasets.py`), gitignored by design, present only because this developer's machine had run them before. Fixed by introducing a `real_data` pytest marker (`pyproject.toml`), deselected by default (`addopts = "... -m \"not real_data\""`), with a graceful skip-with-instructions fallback (`tests/conftest.py`) for anyone who explicitly opts into `make test-real-data` without preparing data first.
2. **1 test** (`test_task3_ranker_dependence.py`) failed to even *collect* because `reports/final_revision_task3_ranker_dependence_20260715/scripts/` (244KB of pure Python source, needed at module-import time) was accidentally caught by the blanket `reports/final_revision_*/` `.gitignore` rule -- unlike its siblings (`task1`, `task4`), it had no negation carve-out. Fixed by adding the same carve-out pattern already used for `task1`/`task4` (track everything except the genuinely bulky `outputs/`).

Verified fix in a second, independent fresh clone: `pytest -q` -> **1306
passed, 0 skipped, 0 failed, 64 deselected**; `make test-full` -> `OK (0
skipped)`. Regression guard: `tests/test_fresh_checkout_reproducibility.py`.

**Update (same day, after the cloud-validation pass below):** the total grew
to **1338 passed, 64 deselected, 0 skipped, 0 failed** with the addition of
31 tests for `scripts/run_cloud_validation.py`. Independently re-verified
via `python scripts/run_cloud_validation.py --tier all` (commit `9e1472c`):
all three tiers (`core`, `solver`, `real-data`) PASS. If this number and the
one above ever disagree with a fresh `pytest -q` run, trust the fresh run,
not either cached number here.

**Update (2026-07-31, GitHub repository polish pass):** the total grew again
to **1362 passed, 64 deselected, 0 skipped, 0 failed** as of commit
`2cd71ce`, with the addition of the claim-registry-validator and
repo-clarity-validator regression tests. Same caveat applies: trust a fresh
`pytest -q` run over any number in this file.

## Known blockers (not fixable by a commit)

- **GitHub Actions billing.** See "Verified state" above. Action: repository owner must resolve in GitHub billing settings. Tracked: [issue #45](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/issues/45).
- **Cohere structured-output enforcement** for the counterfactual benchmark (unrelated to the above) -- see root `PROJECT_STATUS.md` for full detail; unchanged by this pass. Tracked: [issue #48](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/issues/48) (native-transport wiring).

## Prioritized remaining work

Every item below is tracked as a GitHub issue (see `docs/RELEASE_CHECKLIST.md`
for how these map to the merge/release bar) — the issue links are a
convenience, not the source of truth; if an issue number is ever wrong or
an issue is closed, trust the prose here and `docs/RELEASE_CHECKLIST.md`
over a stale link.

- **Required before ordinary development:** nothing -- `pytest -q` is green on a fresh clone, `docs/CONTRIBUTIONS.md`/this file describe current state accurately.
- **Required before public release:** resolve the GitHub Actions billing block (external, repository-owner action, [#45](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/issues/45)); select a durable external archive destination for raw provider transcripts (`docs/EXPERIMENT_ARTIFACT_POLICY.md`, not currently a merge blocker but is a release condition, [#46](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/issues/46)). Full bar: `docs/RELEASE_CHECKLIST.md`.
- **Optional research extensions:** a better-calibrated stopping statistic for the consistency-aware pivot ([#49](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/issues/49), see also root `PROJECT_STATUS.md`); Cohere native-transport wiring for the counterfactual benchmark ([#48](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/issues/48)); cross-dataset generalization evidence for the real-LLM pilot ([#50](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/issues/50)).
- **External infrastructure limitations (not fixable in this repo):** GitHub Actions billing ([#45](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/issues/45)); any future need for a durable raw-transcript archive destination ([#46](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/issues/46)).
- **Deferred, blocked on the above:** cross-check cloud-validation tiers against a live GitHub Actions runner once billing is restored ([#47](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/issues/47), blocked by #45).

## Exact next action

1. Repository owner resolves the GitHub Actions billing block ([#45](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/issues/45)) so CI can run at all again (currently the single highest-priority item -- no amount of code correctness is visible to CI until this is fixed).
2. Once CI runs, confirm the fresh-checkout fix holds on an actual GitHub Actions runner ([#47](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/issues/47); this pass validated it in a local isolated clone only).
3. For the mature program: no further action recommended -- it is a complete, submitted manuscript. For the consistency-aware pivot: see root `PROJECT_STATUS.md`'s own "Exact next action" (unchanged, still current), and issues [#49](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/issues/49)/[#50](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/issues/50) for the specific optional follow-ons.

## How to resume safely

1. Read `docs/CONTRIBUTIONS.md` first (what exists and its status), then this file (what's active/unfinished), then root `PROJECT_STATUS.md` if branch-level historical narrative is needed.
2. Re-run `git fetch origin && git status --short --branch && git rev-parse HEAD` -- do not trust any hash in any status document once new commits exist.
3. Run `pytest -q` (should be green with 64 deselected on any machine) before assuming anything is broken; only run `make test-real-data` if you have prepared datasets and specifically need to test that tier.
