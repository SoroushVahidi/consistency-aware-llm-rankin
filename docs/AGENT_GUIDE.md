# Agent Guide

Concise, operational entry point for a future coding/research agent. This
document tells you *what to do*; `docs/CONTRIBUTIONS.md` and
`docs/PROJECT_STATUS.md` tell you *what exists and its status* in more
narrative detail. Read this file first if you are new here; do not treat it
as a second architecture or contribution document -- it links to those
rather than repeating them.

## 1. Read these first, in this order

1. `README.md` -- orientation, research question, current conclusion, how to install/validate.
2. `docs/CONTRIBUTIONS.md` -- every scientific/engineering contribution, its status, and (critically) what this repo does **not** establish.
3. `docs/PROJECT_STATUS.md` -- current subsystem-by-subsystem state and what's unfinished.
4. `docs/claim_evidence_registry.yaml` -- machine-readable per-claim evidence index (use this to check a specific claim programmatically).
5. `docs/ARCHITECTURE.md` -- module layering and terminology, only once you need to touch code.

Everything else (`docs/EXPERIMENTS.md`, `docs/EXPERIMENT_ARTIFACT_POLICY.md`,
the root `PROJECT_STATUS.md`, `docs/READ_ME_FIRST_FOR_AI.md`) is
second-layer detail or historical narrative -- follow links from the five
above rather than reading it cold.

## 2. Canonical vs. must-not-treat-as-canonical

**Canonical** (cite freely, matches the submitted manuscript):
- `reports/full_calibrated_core/` -- the classical multi-ranker-fusion evidence backbone.
- `reports/exact_open_source_ilp_repair_investigation/` -- exact SCIP repair vs. greedy.
- `papers/JDIQ_2026/manuscript/main.tex` -- the actual submitted claims. If any `docs/*.md` disagrees with `main.tex` on a number, trust `main.tex`.

**Must NOT be treated as canonical / manuscript evidence:**
- `outputs/pub_vote_cmp_all4/`, `outputs/pub_vote_cmp_v2/`, `outputs/q1_journal_package/` -- historical, pre-`full_calibrated_core`, zero citations in `main.tex`.
- `reports/gurobi_vs_scip_solver_cross_validation_20260731T162314Z/`, `reports/exact_solver_scaling_study_20260731T162314Z/` -- **internal validation only**. Real, useful, non-secret results (SCIP and Gurobi agree on all 1,025 canonical instances; SCIP becomes intractable around n=40, Gurobi around n=50) -- but never cite these as a manuscript contribution. See `docs/CONTRIBUTIONS.md` §1.6 and `papers/JDIQ_2026/manuscript/integrity_audit/EXTERNAL_SOLVER_MANUSCRIPT_DECISION.md`.
- Row-level statistics from `reports/repair_frontier_20260729T144742Z/`, `reports/extraction_study_20260729T151610Z/`, `reports/repair_diagnostic_20260729T162748Z/` -- point estimates remain valid, but any CI/p-value is superseded by the cluster-aware reanalysis in `reports/real_llm_clustered_reanalysis_20260730T023745Z/` (6 independent queries, not ~120 rows).
- `docs/experiment_inventory.md` / `reports/experiment_inventory.json` -- historical inventory files, corrected in place 2026-07-31 but still secondary to `docs/CONTRIBUTIONS.md`.

## 3. Where things live

- Core graph/ranking algorithms: `src/consistency_ranker/{graph_construction,cycle_detection,greedy_fas,mwfas_solver,baseline_ranking,evaluation}.py`.
- Statistical inference (incl. cluster-aware correction): `src/consistency_ranker/statistical_inference.py`.
- Production safeguards ("Outcome F"): `src/consistency_ranker/policy_selection/production_config.py` + `production_runner.py`. `PolicySelector.__post_init__` raises `ValueError` if learned routing is configured while in production mode -- this is runtime-enforced, not just documented.
- Provenance/reproducibility manifests: `src/consistency_ranker/provenance.py`.
- Solver abstraction: `src/consistency_ranker/mwfas_solver.py` (`solve(graph, method="greedy"|"scip"|"exact"|"ilp"|"gurobi")`).

## 4. How to validate changes

GitHub Actions is **not currently authoritative** -- every `ci.yml` run has
failed since at least 2026-07-16 due to a GitHub account billing issue, not
a code problem. Use instead:

```bash
python scripts/run_cloud_validation.py --tier core     # mirrors ci.yml's `tests` job
python scripts/run_cloud_validation.py --tier solver   # mirrors ci.yml's `tests-solver-enabled` job
```

Expected result for `solver` (and the repo's default `pytest -q` with
`[exact]` installed): **1362 passed, 64 deselected, 0 skipped, 0 failed**
(as of commit `2cd71ce` -- the exact count grows over time; re-run rather
than trusting this number).
`core` tolerates some SCIP-related skips (no `[exact]` extra there) by
design. See `docs/EXPERIMENTS.md` "Cloud Validation" and "Test Tiers" for
full detail, and `docs/PROJECT_STATUS.md` for the current exact numbers if
they've since changed.

Before merging anything: both `core` and `solver` tiers must report
`overall_status: PASS` from a clean (non-dirty) worktree.

## 5. Long-running jobs: use tmux

Anything expected to exceed ~5 minutes (the `solver`/`real-data`/`all`
cloud-validation tiers, dataset preparation, large experiment sweeps) must
run under tmux, non-interactively, with output logged to a file and the
exit code captured. Get the exact recommended command for a cloud-validation
tier with:

```bash
python scripts/run_cloud_validation.py --print-tmux-command --tier all
```

For anything else, use a descriptive, timestamped session name
(`tmux new-session -d -s <name>_<UTC-timestamp> "... 2>&1 | tee <log>; echo EXIT_CODE=$? >> <log>"`)
so the job survives disconnection and its result is auditable afterward.

## 6. How experiment artifacts are classified

See `docs/EXPERIMENT_ARTIFACT_POLICY.md` for the full decision matrix. In
short: track compact, sanitized evidence needed to verify or recompute a
committed claim (`FINAL_REPORT.md`/`FINDINGS.md`, manifests, seeds, summary
tables, reproduction scripts); never track raw provider transcripts, large
regenerable intermediates, or anything that could contain a secret or a
prompt/completion payload. Every new `reports/<family>_<timestamp>/`
directory should classify itself (canonical / exploratory / superseded /
historical / internal-validation) in its own `FINDINGS.md` or `STATUS.md`.

## 7. What must never be committed

- `gurobi.lic` or any WLS credential value (the real license lives outside this repo, at `~/gurobi.lic`; only Gurobi's own non-secret startup banner text -- parameter *names* and a public license ID number -- is safe to log).
- Raw LLM provider request/response transcripts (may contain prompts/completions; excluded per `docs/EXPERIMENT_ARTIFACT_POLICY.md`).
- API keys or any `.env`-style secret.
- `data/raw/` or `data/processed/` (multi-GB, network-fetched, gitignored by design -- see the `real_data` pytest tier in `docs/EXPERIMENTS.md`).
- Machine-specific absolute paths in active code/docs (checked by `scripts/check_active_portability.py`).

Run `python scripts/run_secret_scan.py` before every commit if you're unsure.

## 8. How to add a new experiment or claim

1. Create `reports/<family>_<UTC-timestamp>/` (or `experiments/...` for a bounded audit) with its own entry-point script and a `FINDINGS.md`/`FINAL_REPORT.md` that states its classification up front.
2. Decide what to track vs. exclude per `docs/EXPERIMENT_ARTIFACT_POLICY.md` before `git add`.
3. If the result supports (or rejects) a claim worth tracking long-term, add a row to `docs/claim_evidence_registry.yaml` (stable ID, status, evidence paths, limitations) and run `python scripts/validate_claim_evidence_registry.py`.
4. Add a row to `docs/CONTRIBUTIONS.md` (§1 if scientific, §2 if engineering, or §3 if it's a claim you're explicitly rejecting) and, if relevant, `docs/EXPERIMENTS.md`'s family table.
5. Run `make repo-ready` (or `python scripts/run_cloud_validation.py --tier core`) before committing.

## 9. Does a result belong in the manuscript?

Only if it (a) is cited by `papers/JDIQ_2026/manuscript/main.tex` already, or
(b) you have explicit authorization to draft new manuscript text and the
result does not depend on a non-public, identity-linked external package or
a commercial solver (see `papers/JDIQ_2026/manuscript/integrity_audit/EXTERNAL_SOLVER_MANUSCRIPT_DECISION.md`
for the reasoning behind that constraint -- it's a double-blind-review
anonymity concern, not a quality judgment). When in doubt, classify a new
result as `internal_validation` or `exploratory` in the claim registry
rather than `canonical`, and leave `manuscript_applicable: false`.

## 10. Highest-priority open items (check `docs/PROJECT_STATUS.md` for current state)

All tracked as GitHub issues (labels: `priority: blocking`/`high`/`medium`/`low`).
See `docs/PROJECT_STATUS.md` "Prioritized remaining work" for the full,
textually-robust list (issue links there are a convenience, not the source
of truth).

1. GitHub Actions billing block ([#45](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/issues/45)) -- external, requires the repository owner to act in GitHub's billing settings; not fixable by a commit.
2. Once resolved, cross-check an actual `ci.yml` run against `scripts/run_cloud_validation.py --tier core`/`--tier solver` on the same commit ([#47](https://github.com/SoroushVahidi/consistency-aware-llm-rankin/issues/47)) to close the "verified on a live runner" gap.
3. Everything else currently active is tracked in `docs/PROJECT_STATUS.md`'s subsystem table and "Exact next action" section -- check there rather than assuming this list is exhaustive or current.

## 11. Maintainer/agent workflow

**When investigating:**
- Read the canonical docs (§1 above) before anything else.
- Check `docs/claim_evidence_registry.yaml` for the current status of any
  claim you're touching (`python scripts/validate_claim_evidence_registry.py`
  to confirm it's internally consistent first).
- Verify current `main` yourself (`git fetch origin && git status --short
  --branch && git rev-parse HEAD`) -- do not trust a hash in any status
  document once new commits exist.
- Do not rely on `/tmp` reports or prior-session artifacts as ground truth
  -- if a finding matters, it should already be (or should become) a
  tracked file in this repository, not a local scratch file.

**When changing code:**
- Identify which claim (if any) or component the change affects.
- Run the relevant focused tests, then the applicable cloud-validation
  tier (§4).
- Update `docs/PROJECT_STATUS.md`/`docs/CONTRIBUTIONS.md`/the claim
  registry if the change affects what they describe -- see §8.

**When running experiments:**
- Classify canonical vs. exploratory vs. internal-validation **before**
  execution, not after seeing results (§9, and the "Scientific experiment
  proposal" issue template enforces this ordering).
- Use provenance (`consistency_ranker.provenance.collect_provenance()` or
  `experiment_cli.write_run_manifest()`).
- Use tmux for anything expected to exceed ~5 minutes (§5).
- Follow `docs/EXPERIMENT_ARTIFACT_POLICY.md` for what gets tracked.

**When reporting completion** (to a user, in a PR description, or in an
issue comment), state explicitly:
- The exact commit.
- The exact commands run.
- Exact test totals (e.g. "1362 passed, 64 deselected, 0 skipped, 0
  failed") -- never a vague "tests pass".
- Artifact paths produced.
- Which claim(s), if any, are affected.
- Remaining limitations, stated plainly, not omitted.
- Push/PR state (pushed to `main`? PR opened? still local?).

**When updating GitHub:**
- Update the relevant issue (comment with progress, or close with a link
  to the merged commit/PR that resolved it).
- Update `docs/PROJECT_STATUS.md` if the change affects tracked completion
  state.
- Close an issue only with objective evidence (a merged PR, a passing
  validation run) -- never close an issue merely because it looks old.
- **Never mark a GitHub Actions/infrastructure failure as a test
  failure.** If a job fails before installing anything (billing, quota, a
  platform outage), that's an infrastructure issue (`type: infrastructure`
  / `status: external blocker` labels) -- file or update the infrastructure
  issue, don't file a bug report against the code.
