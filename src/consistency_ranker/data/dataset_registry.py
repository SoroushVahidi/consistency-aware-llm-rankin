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
    """Which loader to use (see ``download_datasets.py`` / ``prepare_datasets.py``)."""

    notes: str = ""
    """Any extra notes, e.g. manual download instructions."""

    hf_kwargs: dict = field(default_factory=dict)
    """Extra keyword arguments passed to ``datasets.load_dataset``."""

    corpus_dependency: str | None = None
    """If set, another dataset id whose raw ``documents.jsonl`` may be reused (e.g. TREC DL + MS MARCO)."""

    ir_dataset_name: str | None = None
    """If set, ``ir_datasets.load(name)`` id used by the optional ``ir-datasets`` export path."""


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
    # --- Additional manuscript / IR benchmarks ---
    "nfcorpus": DatasetConfig(
        name="nfcorpus",
        hf_corpus_name="BeIR/nfcorpus",
        hf_queries_name="BeIR/nfcorpus",
        hf_qrels_name="BeIR/nfcorpus-qrels",
        raw_path=_p("data/raw/beir/nfcorpus"),
        processed_path=_p("data/processed/beir/nfcorpus"),
        top_k=100,
        max_queries=500,
        seed=42,
        loader_type="beir",
        notes="NFCorpus (BEIR): biomedical queries and narrative documents. Hugging Face mirrors.",
    ),
    "msmarco_passage": DatasetConfig(
        name="msmarco_passage",
        hf_corpus_name="BeIR/msmarco",
        hf_queries_name="BeIR/msmarco",
        hf_qrels_name="BeIR/msmarco-qrels",
        raw_path=_p("data/raw/msmarco_passage"),
        processed_path=_p("data/processed/msmarco_passage"),
        top_k=50,
        max_queries=5000,
        seed=42,
        loader_type="msmarco_passage",
        notes=(
            "MS MARCO passage ranking (BEIR mirror on Hugging Face). Full corpus is ~8.8M passages; "
            "download streams to JSONL. Always pass --max-docs (and optionally --max-queries) unless "
            "you intentionally want the full export. See data/raw/msmarco_passage/README.md."
        ),
    ),
    "trec_dl_passage": DatasetConfig(
        name="trec_dl_passage",
        hf_corpus_name="",
        hf_queries_name="",
        hf_qrels_name="",
        raw_path=_p("data/raw/trec_dl_passage"),
        processed_path=_p("data/processed/trec_dl_passage"),
        top_k=50,
        max_queries=500,
        seed=42,
        loader_type="trec_dl_passage",
        corpus_dependency="msmarco_passage",
        ir_dataset_name="msmarco-passage/trec-dl-2019",
        notes=(
            "TREC 2019 Deep Learning track passage task (judged qrels over MS MARCO passages). "
            "Requires: pip install 'consistency-ranker[ir]' (ir-datasets). "
            "Documents are MS MARCO passage texts for judged doc ids (not the full corpus). "
            "Optional: reuse documents from msmarco_passage raw JSONL via --trec-dl-docs-from-msmarco. "
            "See data/raw/trec_dl_passage/README.md."
        ),
    ),
    "robust04": DatasetConfig(
        name="robust04",
        hf_corpus_name="",
        hf_queries_name="",
        hf_qrels_name="",
        raw_path=_p("data/raw/robust04"),
        processed_path=_p("data/processed/robust04"),
        top_k=100,
        max_queries=500,
        seed=42,
        loader_type="robust04",
        ir_dataset_name="robust04",
        notes=(
            "TREC Robust 2004 ad hoc corpus. Requires ir-datasets (pip install 'consistency-ranker[ir]'); "
            "first run triggers ir-datasets downloads (TREC redistribution terms apply). "
            "See data/raw/robust04/README.md for manual alternatives."
        ),
    ),
}

DATASET_NAMES = list(REGISTRY.keys())


def get_config(name: str) -> DatasetConfig:
    """Return the :class:`DatasetConfig` for *name*.

    Parameters
    ----------
    name:
        Dataset short name registered in :data:`REGISTRY` (see ``DATASET_NAMES``).

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


def processed_queries_jsonl(name: str) -> Path:
    """Path to ``queries.jsonl`` under the dataset's processed directory."""
    return get_config(name).processed_path / "queries.jsonl"
