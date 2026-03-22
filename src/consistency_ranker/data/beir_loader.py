"""
beir_loader.py
==============
Loader for BEIR-format datasets (SciDocs, FiQA-2018, and others).

BEIR datasets are hosted on HuggingFace under the ``BeIR/`` namespace.
This module loads corpus, queries, and qrels from either:

- Local JSONL files produced by :mod:`prepare_datasets` (fast, offline).
- HuggingFace ``datasets`` library (requires internet on first use).

The HuggingFace layout for a BEIR dataset is::

    BeIR/<name>          corpus split  → id, text, title
                         queries split → id, text
    BeIR/<name>-qrels    test split    → query-id, corpus-id, score

References
----------
- https://github.com/beir-cellar/beir
- https://huggingface.co/BeIR
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema import Document, QrelEntry, Query


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class BeirNotAvailableError(RuntimeError):
    """Raised when a BEIR dataset cannot be downloaded automatically.

    This mirrors :class:`~consistency_ranker.data.bright_loader.BrightNotAvailableError`
    so callers can handle both gracefully with a single except clause.
    """


# ---------------------------------------------------------------------------
# Load from local JSONL files
# ---------------------------------------------------------------------------

def load_queries_from_jsonl(path: Path) -> list[Query]:
    """Load queries from a local ``queries.jsonl`` file.

    Parameters
    ----------
    path:
        Path to the JSONL file.

    Returns
    -------
    list[Query]
    """
    queries: list[Query] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                queries.append(Query.from_dict(json.loads(line)))
    return queries


def load_documents_from_jsonl(path: Path) -> list[Document]:
    """Load documents from a local ``documents.jsonl`` file.

    Parameters
    ----------
    path:
        Path to the JSONL file.

    Returns
    -------
    list[Document]
    """
    docs: list[Document] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                docs.append(Document.from_dict(json.loads(line)))
    return docs


def load_qrels_from_jsonl(path: Path) -> list[QrelEntry]:
    """Load relevance judgements from a local ``qrels.jsonl`` file.

    Parameters
    ----------
    path:
        Path to the JSONL file.

    Returns
    -------
    list[QrelEntry]
    """
    qrels: list[QrelEntry] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                qrels.append(QrelEntry.from_dict(json.loads(line)))
    return qrels


# ---------------------------------------------------------------------------
# Download / load from HuggingFace
# ---------------------------------------------------------------------------

def download_beir_dataset(
    corpus_name: str,
    qrels_name: str,
    raw_path: Path,
    max_docs: int | None = None,
) -> tuple[list[Query], list[Document], list[QrelEntry]]:
    """Download a BEIR dataset from HuggingFace and return structured objects.

    Parameters
    ----------
    corpus_name:
        HuggingFace dataset id for corpus + queries, e.g. ``"BeIR/scidocs"``.
    qrels_name:
        HuggingFace dataset id for qrels, e.g. ``"BeIR/scidocs-qrels"``.
    raw_path:
        Local directory where the HuggingFace cache will be placed.
    max_docs:
        Optional limit on the number of documents loaded (for fast testing).

    Returns
    -------
    tuple[list[Query], list[Document], list[QrelEntry]]

    Raises
    ------
    ImportError
        If the ``datasets`` library is not installed.
    """
    try:
        from datasets import load_dataset  # type: ignore[import]
    except ImportError as exc:
        raise BeirNotAvailableError(
            "The 'datasets' library is required to download BEIR datasets. "
            "Install it with: pip install datasets"
        ) from exc

    cache_dir = str(raw_path)

    try:
        # --- Corpus ---
        print(f"  Loading corpus from {corpus_name} …")
        corpus_ds = load_dataset(corpus_name, "corpus", cache_dir=cache_dir)
        corpus_split = corpus_ds["corpus"]
        documents: list[Document] = []
        for i, row in enumerate(corpus_split):
            if max_docs is not None and i >= max_docs:
                break
            documents.append(
                Document(
                    doc_id=str(row["_id"]),
                    text=str(row.get("text", "")),
                    title=str(row.get("title", "")),
                )
            )

        # --- Queries ---
        print(f"  Loading queries from {corpus_name} …")
        queries_ds = load_dataset(corpus_name, "queries", cache_dir=cache_dir)
        queries_split = queries_ds["queries"]
        queries: list[Query] = []
        for row in queries_split:
            queries.append(
                Query(
                    query_id=str(row["_id"]),
                    text=str(row.get("text", "")),
                )
            )

        # --- QRels ---
        print(f"  Loading qrels from {qrels_name} …")
        qrels_ds = load_dataset(qrels_name, cache_dir=cache_dir)
        qrels: list[QrelEntry] = []
        for split_name in qrels_ds:
            for row in qrels_ds[split_name]:
                qrels.append(
                    QrelEntry(
                        query_id=str(row["query-id"]),
                        doc_id=str(row["corpus-id"]),
                        relevance=int(row.get("score", 1)),
                    )
                )

    except (OSError, ConnectionError, ValueError) as exc:
        raise BeirNotAvailableError(
            f"Could not download {corpus_name!r} automatically: {exc}\n"
            "Check your internet connection and that 'huggingface.co' is reachable.\n"
            "If the network is unavailable, place the JSONL files manually in the "
            "expected raw directory and re-run prepare_datasets.py."
        ) from exc
    except Exception as exc:  # noqa: BLE001 — catch-all for any HuggingFace/network error
        raise BeirNotAvailableError(
            f"Unexpected error downloading {corpus_name!r} ({type(exc).__name__}): {exc}\n"
            "Check your internet connection and that 'huggingface.co' is reachable."
        ) from exc

    return queries, documents, qrels


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_jsonl(records: list[Any], path: Path) -> None:
    """Write a list of dataclass instances to a JSONL file.

    Parameters
    ----------
    records:
        Objects with a ``.to_dict()`` method.
    path:
        Destination path (created or overwritten).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r.to_dict()) + "\n")
