"""Shared fixtures for the `real_data` pytest marker.

Tests marked `@pytest.mark.real_data` depend on real, prepared BEIR/HotpotQA/
BRIGHT dataset files under `data/processed/` -- multi-GB, network-fetched via
`scripts/download_datasets.py` + `scripts/prepare_datasets.py`, and gitignored
by design (see `docs/EXPERIMENT_ARTIFACT_POLICY.md`). They are excluded from
the default `pytest`/`make test`/`make test-full`/CI run via the
`-m "not real_data"` default in `pyproject.toml`'s `addopts`.

This autouse fixture is a second line of defense: if `real_data` tests are
explicitly selected (`make test-real-data`, i.e. `pytest -m real_data`)
without the datasets prepared, it converts what would otherwise be a raw
`FileNotFoundError`/`AssertionError` deep in a fixture into a clear,
actionable skip.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DATASETS = ("scidocs", "fiqa", "hotpotqa", "bright")


def _processed_dir(name: str) -> Path:
    if name in ("scidocs", "fiqa"):
        return _REPO_ROOT / "data" / "processed" / "beir" / name
    return _REPO_ROOT / "data" / "processed" / name


def _dataset_prepared(name: str) -> bool:
    base = _processed_dir(name)
    return (base / "queries.jsonl").exists() and (base / "documents.jsonl").exists()


@pytest.fixture(autouse=True)
def _skip_real_data_without_prepared_datasets(request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("real_data") is None:
        return
    missing = [d for d in _DATASETS if not _dataset_prepared(d)]
    if missing:
        pytest.skip(
            f"real_data: prepared dataset(s) missing under data/processed/: {missing}. "
            "Run `python scripts/download_datasets.py` then "
            "`python scripts/prepare_datasets.py --dataset all` (requires network access). "
            "See docs/EXPERIMENTS.md."
        )
