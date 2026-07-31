# AGENTS.md

## Start here

Before doing anything else in this repository:

1. Read [`docs/CONTRIBUTIONS.md`](docs/CONTRIBUTIONS.md) — what this
   repository actually contributes, and what it does not support.
2. Read [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) — current state
   of `main`, subsystem status, unfinished work.
3. Read [`docs/AGENT_GUIDE.md`](docs/AGENT_GUIDE.md) — concise operational
   guide (validation, tmux, artifact rules, how to add a claim).
4. The root [`PROJECT_STATUS.md`](PROJECT_STATUS.md) and
   [`docs/handoff/CURRENT_BRANCH_HANDOFF.md`](docs/handoff/CURRENT_BRANCH_HANDOFF.md)
   /
   [`docs/handoff/state_snapshot.json`](docs/handoff/state_snapshot.json)
   are the detailed historical handoff narrative for the branch that merged
   into `main` via PR #44 — read them only if you need that history; they
   no longer describe current state (see the banner at the top of the root
   `PROJECT_STATUS.md`).
5. Reconfirm Git state before editing anything (`git fetch origin &&
   git status --short --branch && git rev-parse HEAD`) — the documents above
   are a point-in-time snapshot, not a live source of truth.
6. Never assume a report under `reports/` is citable evidence just because
   it exists on disk — check its classification in
   [`docs/CONTRIBUTIONS.md`](docs/CONTRIBUTIONS.md) /
   [`docs/EXPERIMENT_ARTIFACT_POLICY.md`](docs/EXPERIMENT_ARTIFACT_POLICY.md)
   first. In particular, the two Gurobi-solver validation report directories
   (`reports/gurobi_vs_scip_solver_cross_validation_20260731T162314Z/`,
   `reports/exact_solver_scaling_study_20260731T162314Z/`) are internal
   validation only and must never be cited as manuscript evidence.
7. Never run a provider (LLM API) call without explicit, scoped
   authorization from the user (exact query/pair/provider and a stated call
   ceiling).
8. Never expose secrets, API keys, endpoints, project IDs, or raw provider
   responses in output, commits, or documentation.
9. Never change a frozen protocol artifact (a prompt, schema, or pool
   protocol already marked "frozen") in place — add a new version and a
   migration note instead.
10. Never treat a cost-only utility signal (fewer calls, lower latency) as a
    retrieval-quality gain — they are tracked as separate metrics throughout
    this repository.
11. Never treat an LLM provider's judgment as ground truth — qrels are the
    only evaluation truth; every provider (including Azure) is a noisy
    judge.

## Cursor Cloud specific instructions

This is a pure Python research library (no web servers, databases, or Docker).
Activate the project virtual environment before running commands. Prefer
`$VENV_PATH` when set; otherwise use the repository-local `.venv`:

```bash
source "${VENV_PATH:-.venv}/bin/activate"
```

### Quick reference

| Task | Command |
|------|---------|
| Install deps | `pip install -r requirements.txt && pip install -e ".[dev]"` |
| Lint | `ruff check .` |
| Tests | `pytest -q` (real_data-tier tests are deselected by default — see `docs/EXPERIMENTS.md` "Test Tiers"; test counts grow over time, run it and read the summary line rather than trusting a cached number; see `docs/PROJECT_STATUS.md` for the last verified count. Use `PYTHONPATH=src` if package not installed) |
| Cloud validation | `python scripts/run_cloud_validation.py --tier core` (see `docs/EXPERIMENTS.md` "Cloud Validation" — the canonical alternative while GitHub Actions is blocked by a billing issue) |
| Synthetic experiment | `python scripts/run_synthetic.py --n-items 20 --noise 0.2 --seed 42` |

### Notes

- Python 3.11+ is required (`pyproject.toml` specifies `requires-python = ">=3.11"`). The VM has Python 3.12.
- `python3.12-venv` must be installed via apt for venv creation to work (`sudo apt-get install -y python3.12-venv`). The update script handles this.
- Ruff is configured in `pyproject.toml` (`line-length = 100`, `target-version = "py311"`, lint rules `E, F, W, I`).
- The `sentence-transformers` dependency pulls in PyTorch — initial install takes ~2 minutes.
- Real-data experiments require downloading datasets from HuggingFace (network-dependent). Synthetic experiments work fully offline.
- Pre-computed experiment outputs are in the `outputs/` directory.
- When re-running synthetic experiments to an existing `outputs/` directory, pass `--overwrite-existing` or use a different `--output-dir` to avoid a non-zero exit code from the script refusing to overwrite.
