"""
dataset_registry.py
===================
Central registry of dataset configurations for this project.

Each entry maps a short dataset name to a :class:`DatasetConfig` object
that encodes default paths, preprocessing parameters, and HuggingFace
dataset identifiers.

Usage
-----
::

    from consistency_ranker.data.dataset_registry import get_config, REGISTRY

    cfg = get_config("scidocs")
    print(cfg.raw_path, cfg.processed_path)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

def _find_repo_root() -> Path:
    """Walk up from this file until we find pyproject.toml (repo marker)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    # Fallback: four levels up (src/consistency_ranker/data/ → repo root)
    return here.parent.parent.parent.parent


# Repository root resolved via pyproject.toml marker file
_REPO_ROOT = _find_repo_root()


@dataclass
class DatasetConfig:
    """Configuration for a single dataset."""

    name: str
    """Short dataset identifier used in CLI commands."""

    hf_corpus_name: str
    """HuggingFace dataset id for the document corpus."""

    hf_queries_name: str
    """HuggingFace dataset id for the queries split."""

    hf_qrels_name: str
    """HuggingFace dataset id for qrels (relevance judgements)."""

    raw_path: Path
    """Local directory for raw (downloaded) files."""

    processed_path: Path
    """Local directory for processed JSONL outputs."""

    top_k: int = 100
    """Maximum number of candidate documents per query for preference generation."""

    max_queries: int = 500
    """Maximum number of queries to process (for fast experiments)."""

    seed: int = 42
    """Random seed for reproducible subsampling."""

    loader_type: str = "beir"
    """Which loader to use: ``'beir'``, ``'hotpotqa'``, or ``'bright'``."""

    notes: str = ""
    """Any extra notes, e.g. manual download instructions."""

    hf_kwargs: dict = field(default_factory=dict)
    """Extra keyword arguments passed to ``datasets.load_dataset``."""


def _p(rel: str) -> Path:
    """Resolve a path relative to the repository root."""
    return _REPO_ROOT / rel


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

REGISTRY: dict[str, DatasetConfig] = {
    "scidocs": DatasetConfig(
        name="scidocs",
        hf_corpus_name="BeIR/scidocs",
        hf_queries_name="BeIR/scidocs",
        hf_qrels_name="BeIR/scidocs-qrels",
        raw_path=_p("data/raw/beir/scidocs"),
        processed_path=_p("data/processed/beir/scidocs"),
        top_k=100,
        max_queries=500,
        seed=42,
        loader_type="beir",
    ),
    "fiqa": DatasetConfig(
        name="fiqa",
        hf_corpus_name="BeIR/fiqa",
        hf_queries_name="BeIR/fiqa",
        hf_qrels_name="BeIR/fiqa-qrels",
        raw_path=_p("data/raw/beir/fiqa"),
        processed_path=_p("data/processed/beir/fiqa"),
        top_k=100,
        max_queries=500,
        seed=42,
        loader_type="beir",
    ),
    "hotpotqa": DatasetConfig(
        name="hotpotqa",
        hf_corpus_name="hotpot_qa",
        hf_queries_name="hotpot_qa",
        hf_qrels_name="hotpot_qa",
        raw_path=_p("data/raw/hotpotqa"),
        processed_path=_p("data/processed/hotpotqa"),
        top_k=10,
        max_queries=500,
        seed=42,
        loader_type="hotpotqa",
        hf_kwargs={"name": "fullwiki"},
    ),
    "bright": DatasetConfig(
        name="bright",
        hf_corpus_name="xlangai/BRIGHT",
        hf_queries_name="xlangai/BRIGHT",
        hf_qrels_name="xlangai/BRIGHT",
        raw_path=_p("data/raw/bright"),
        processed_path=_p("data/processed/bright"),
        top_k=100,
        max_queries=500,
        seed=42,
        loader_type="bright",
        notes=(
            "BRIGHT may require manual download. "
            "See data/raw/bright/README.md for instructions."
        ),
    ),
}

DATASET_NAMES = list(REGISTRY.keys())


def get_config(name: str) -> DatasetConfig:
    """Return the :class:`DatasetConfig` for *name*.

    Parameters
    ----------
    name:
        Dataset short name, e.g. ``"scidocs"``, ``"fiqa"``,
        ``"hotpotqa"``, or ``"bright"``.

    Raises
    ------
    KeyError
        If *name* is not in the registry.
    """
    if name not in REGISTRY:
        raise KeyError(
            f"Unknown dataset {name!r}. "
            f"Available datasets: {DATASET_NAMES}"
        )
    return REGISTRY[name]
