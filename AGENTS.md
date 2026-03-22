# AGENTS.md

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
| Tests | `pytest` (~275 tests after `pip install -e .`; use `PYTHONPATH=src` if package not installed) |
| Synthetic experiment | `python scripts/run_synthetic.py --n-items 20 --noise 0.2 --seed 42` |

### Notes

- Python 3.11+ is required (`pyproject.toml` specifies `requires-python = ">=3.11"`). The VM has Python 3.12.
- `python3.12-venv` must be installed via apt for venv creation to work (`sudo apt-get install -y python3.12-venv`). The snapshot handles this.
- Ruff is configured in `pyproject.toml` (`line-length = 100`, `target-version = "py311"`, lint rules `E, F, W, I`).
- The `sentence-transformers` dependency pulls in PyTorch — initial install takes ~2 minutes.
- Real-data experiments require downloading datasets from HuggingFace (network-dependent). Synthetic experiments work fully offline.
- Pre-computed experiment outputs are in the `outputs/` directory.
