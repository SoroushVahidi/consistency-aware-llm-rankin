# Contributing

This is a research repository. This document explains how to work in it
without duplicating the canonical documents it links to — read those for
detail, this file for the workflow.

## 1. Reading order

1. `README.md` — orientation.
2. `docs/CONTRIBUTIONS.md` — what this repo contributes, and what it does not.
3. `docs/PROJECT_STATUS.md` — current state, subsystem status, unfinished work.
4. `docs/AGENT_GUIDE.md` — concise operational guide (this document assumes you've read it).
5. `docs/claim_evidence_registry.yaml` — machine-readable per-claim evidence index.

## 2. Environment setup

```bash
git clone https://github.com/SoroushVahidi/consistency-aware-llm-rankin.git
cd consistency-aware-llm-rankin
python -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt && python -m pip install -e ".[dev]"
```

For the exact-solver tier: `python -m pip install -e ".[dev,exact]"`. See
`README.md` "Getting started" for the full command block.

## 3. Validation (GitHub Actions is not currently authoritative)

GitHub Actions has been blocked by an account billing issue since at least
2026-07-16 (tracked in issue #45) — do not rely on it. Instead:

```bash
python scripts/run_cloud_validation.py --tier core     # mirrors ci.yml's `tests` job
python scripts/run_cloud_validation.py --tier solver   # mirrors ci.yml's `tests-solver-enabled` job
```

Both must report `overall_status: PASS` before a PR is mergeable. See
`docs/EXPERIMENTS.md` "Cloud Validation" for tier detail and
`docs/RELEASE_CHECKLIST.md` for the full merge/release bar.

**Real-data tier:** ~64 tests require prepared BEIR/HotpotQA/BRIGHT datasets
(network, ~3GB). Not required for ordinary changes; required if you touch
dataset loaders or candidate-pool construction:

```bash
python scripts/download_datasets.py && python scripts/prepare_datasets.py --dataset all
make test-real-data
```

**Gurobi is entirely optional.** SCIP (`pip install "consistency-ranker[exact]"`,
no license) is the fully supported open-source exact-solver path — every
test, reproduction, and manuscript result depends only on SCIP. Install
`gurobipy` only if you already have a Gurobi license and want to exercise
the optional legacy backend or the internal-only validation studies
(`docs/CONTRIBUTIONS.md` §1.6) — never required.

## 4. Long-running jobs: use tmux

Anything expected to exceed ~5 minutes (the `solver`/`real-data`/`all`
cloud-validation tiers, dataset preparation, large experiment sweeps) must
run under tmux, non-interactively, with output logged and the exit code
captured:

```bash
python scripts/run_cloud_validation.py --print-tmux-command --tier all
```

prints the exact command for cloud-validation tiers; for anything else, use
a descriptive, timestamped session name and `tee` the output to a log file.

## 5. Proposing an experiment

Open an issue using the **Scientific experiment proposal** template (states
the research question, hypothesis, relationship to existing claims,
statistical unit, correction method, expected artifacts, canonical vs.
exploratory classification up front, network/cost requirements, manuscript
relevance, and acceptance criteria — classify *before* running, not after
seeing results).

## 6. Adding a claim or evidence

1. Run the experiment; classify its output per
   `docs/EXPERIMENT_ARTIFACT_POLICY.md` (what's tracked vs. excluded) before
   `git add`.
2. If the result is worth tracking long-term, add a row to
   `docs/claim_evidence_registry.yaml` (stable ID, status, evidence paths,
   limitations) and run `python scripts/validate_claim_evidence_registry.py`.
3. Add a row to `docs/CONTRIBUTIONS.md` (§1 scientific, §2 engineering, or
   §3 if you're explicitly rejecting a claim).
4. Use the **Experiment-result intake** issue template if you want a
   second pair of eyes on the classification before it lands.

## 7. Branch, commit, and PR expectations

- Create commits that are individually coherent (see this repo's own
  history for the convention: one logical change per commit, a "why", not
  just a "what", in the message body).
- Never force-push, rewrite published history, or skip hooks without
  explicit justification.
- Open a PR using the template at `.github/pull_request_template.md` — it
  has checkboxes for exactly the things reviewers here care about (claim
  registry impact, validation tier run, artifact policy, secrets, manuscript
  impact). "N/A" is a valid answer for sections that don't apply.
- Link the PR to any GitHub issue it resolves or is blocked by.

## 8. Scientific wording rules

- Never state or imply that graph repair generally improves retrieval
  quality — the validated result is conditional/negative
  (`docs/CONTRIBUTIONS.md` §1.1, §3).
- Never present row-level statistics from the real-LLM pilot as if the
  ~120 rows were independent samples — there are 6 independent queries
  (`docs/CONTRIBUTIONS.md` §1.2).
- Never present the Gurobi-vs-SCIP validation or the exact-solver scaling
  study as a manuscript contribution — internal validation only, never
  cited in `main.tex` or anonymized submission material
  (`docs/CONTRIBUTIONS.md` §1.6).
- Never present the learned policy selector ("Outcome F") as
  production-approved — production is locked to a fixed default
  (`docs/CONTRIBUTIONS.md` §1.7).
- See `docs/CONTRIBUTIONS.md` §3 for the complete list.

## 9. What must never be committed

- `gurobi.lic` or any WLS credential value.
- Raw LLM provider request/response transcripts.
- API keys or any `.env`-style secret.
- `data/raw/` or `data/processed/` (gitignored by design).
- Machine-specific absolute paths in active code/docs.

Run `python scripts/run_secret_scan.py` before committing if unsure. See
`docs/AGENT_GUIDE.md` §7 for the full list with rationale.
