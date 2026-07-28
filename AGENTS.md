# AGENTS.md

## Start here

Before doing anything else in this repository:

1. Read [`PROJECT_STATUS.md`](PROJECT_STATUS.md) — canonical scientific and
   engineering status.
2. Read [`docs/handoff/CURRENT_BRANCH_HANDOFF.md`](docs/handoff/CURRENT_BRANCH_HANDOFF.md)
   — current branch's commit history, staged work, and exact next task.
3. Inspect [`docs/handoff/state_snapshot.json`](docs/handoff/state_snapshot.json)
   — machine-readable snapshot of the same.
4. Reconfirm Git state before editing anything (`git fetch origin &&
   git status --short --branch && git rev-parse HEAD`) — the documents above
   are a point-in-time snapshot, not a live source of truth.
5. Never assume a report under `reports/` is citable evidence just because
   it exists on disk — check its classification in `PROJECT_STATUS.md` /
   `docs/ARTIFACT_POLICY.md` first.
6. Never run a provider (LLM API) call without explicit, scoped
   authorization from the user (exact query/pair/provider and a stated call
   ceiling).
7. Never expose secrets, API keys, endpoints, project IDs, or raw provider
   responses in output, commits, or documentation.
8. Never change a frozen protocol artifact (a prompt, schema, or pool
   protocol already marked "frozen") in place — add a new version and a
   migration note instead.
9. Never treat a cost-only utility signal (fewer calls, lower latency) as a
   retrieval-quality gain — they are tracked as separate metrics throughout
   this repository.
10. Never treat an LLM provider's judgment as ground truth — qrels are the
    only evaluation truth; every provider (including Azure) is a noisy
    judge.

## Cursor Cloud specific instructions

This is a pure Python research library (no web servers, databases, or Docker).
The virtual environment lives at `/workspace/.venv`. Always activate it before
running any commands:

```bash
source /workspace/.venv/bin/activate
```

### Quick reference

| Task | Command |
|------|---------|
| Install deps | `pip install -r requirements.txt && pip install -e ".[dev]"` |
| Lint | `ruff check .` |
| Tests | `pytest` (test count and skip/fail counts are environment-dependent — e.g. exact-repair tests skip without PySCIPOpt, provider tests need `pip install -e ".[llm]"`; run it and read the summary line rather than trusting a cached number; see `PROJECT_STATUS.md`'s "Current validation status" for the last verified count. Use `PYTHONPATH=src` if package not installed) |
| Synthetic experiment | `python scripts/run_synthetic.py --n-items 20 --noise 0.2 --seed 42` |

### Notes

- Python 3.11+ is required (`pyproject.toml` specifies `requires-python = ">=3.11"`). The VM has Python 3.12.
- `python3.12-venv` must be installed via apt for venv creation to work (`sudo apt-get install -y python3.12-venv`). The update script handles this.
- Ruff is configured in `pyproject.toml` (`line-length = 100`, `target-version = "py311"`, lint rules `E, F, W, I`).
- The `sentence-transformers` dependency pulls in PyTorch — initial install takes ~2 minutes.
- Real-data experiments require downloading datasets from HuggingFace (network-dependent). Synthetic experiments work fully offline.
- Pre-computed experiment outputs are in the `outputs/` directory.
- When re-running synthetic experiments to an existing `outputs/` directory, pass `--overwrite-existing` or use a different `--output-dir` to avoid a non-zero exit code from the script refusing to overwrite.
