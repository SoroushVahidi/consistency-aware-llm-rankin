"""
bright_loader.py
================
Loader for the BRIGHT (Benchmarking Retrieval on Implicit Grounded Tasks)
benchmark.

BRIGHT is a challenging retrieval benchmark where relevant documents require
genuine reasoning to identify.  The dataset is hosted on HuggingFace at
``xlangai/BRIGHT``.

This loader attempts to download BRIGHT programmatically.  If that fails
(e.g. authentication required, dataset not yet public, or network
unavailable) it:

1. Creates the expected directory structure under ``data/raw/bright/``.
2. Writes a ``README.md`` with manual download instructions.
3. Raises a :class:`BrightNotAvailableError` with a human-readable message.

After manual download, place files in ``data/raw/bright/`` and re-run
``scripts/prepare_datasets.py --dataset bright``.

References
----------
- https://brightbenchmark.github.io/
- https://huggingface.co/datasets/xlangai/BRIGHT
"""

from __future__ import annotations

import json
from pathlib import Path

from .schema import Document, QrelEntry, Query

_BRIGHT_MANUAL_INSTRUCTIONS = """\
# BRIGHT — Manual Download Instructions

BRIGHT could not be downloaded automatically. Follow these steps:

1. Visit https://huggingface.co/datasets/xlangai/BRIGHT
2. Accept any required licence / access terms.
3. Install the `datasets` library if not already installed:
       pip install datasets huggingface-hub
4. Log in to HuggingFace CLI (if the dataset is gated):
       huggingface-cli login
5. Download using Python:
       from datasets import load_dataset
       ds = load_dataset("xlangai/BRIGHT")
6. Save the JSONL files to this directory:
       data/raw/bright/
   Expected files:
       queries.jsonl       — one JSON object per line: {id, text}
       documents.jsonl     — one JSON object per line: {id, text, title}
       qrels.jsonl         — one JSON object per line: {query_id, doc_id, relevance}

7. Then run:
       python scripts/prepare_datasets.py --dataset bright
"""

_BRIGHT_TASKS = [
    "biology",
    "earth_science",
    "economics",
    "psychology",
    "robotics",
    "stackoverflow",
    "sustainable_living",
    "leetcode",
    "pony",
    "aops",
    "theoremqa_theorems",
    "theoremqa_questions",
]


class BrightNotAvailableError(RuntimeError):
    """Raised when BRIGHT cannot be downloaded automatically."""


def download_bright(
    raw_path: Path,
    task: str = "biology",
    max_examples: int | None = None,
) -> tuple[list[Query], list[Document], list[QrelEntry]]:
    """Attempt to download BRIGHT from HuggingFace.

    Parameters
    ----------
    raw_path:
        Local directory for raw files and HuggingFace cache.
    task:
        BRIGHT task/domain to load.  See :data:`_BRIGHT_TASKS` for options.
    max_examples:
        Optional cap on examples loaded.

    Returns
    -------
    tuple[list[Query], list[Document], list[QrelEntry]]

    Raises
    ------
    BrightNotAvailableError
        If the dataset cannot be downloaded automatically.
    ImportError
        If the ``datasets`` library is not installed.
    """
    try:
        from datasets import load_dataset  # type: ignore[import]
    except ImportError as exc:
        _write_readme(raw_path)
        raise BrightNotAvailableError(
            "The 'datasets' library is not installed. "
            "Install it with: pip install datasets\n"
            f"Manual instructions written to {raw_path / 'README.md'}"
        ) from exc

    cache_dir = str(raw_path)
    print(f"  Attempting to load BRIGHT task={task!r} from HuggingFace …")

    try:
        ds = load_dataset("xlangai/BRIGHT", task, cache_dir=cache_dir)
    except (OSError, ValueError, ConnectionError) as exc:
        _write_readme(raw_path)
        raise BrightNotAvailableError(
            f"Could not download BRIGHT automatically: {exc}\n"
            f"Manual instructions written to {raw_path / 'README.md'}"
        ) from exc
    except Exception as exc:  # noqa: BLE001 — catch-all for any HuggingFace/network error
        _write_readme(raw_path)
        raise BrightNotAvailableError(
            f"Unexpected error downloading BRIGHT ({type(exc).__name__}): {exc}\n"
            f"Manual instructions written to {raw_path / 'README.md'}"
        ) from exc

    queries: list[Query] = []
    doc_map: dict[str, Document] = {}
    qrels: list[QrelEntry] = []

    # BRIGHT dataset structure may vary; attempt a best-effort parse
    examples_split = ds.get("examples") or ds.get("test") or list(ds.values())[0]

    for i, row in enumerate(examples_split):
        if max_examples is not None and i >= max_examples:
            break

        qid = str(row.get("id", i))
        queries.append(
            Query(query_id=qid, text=str(row.get("query", row.get("question", ""))))
        )

        for doc_id, doc_text in (row.get("positive_docs") or {}).items():
            doc_id = str(doc_id)
            if doc_id not in doc_map:
                doc_map[doc_id] = Document(doc_id=doc_id, text=str(doc_text))
            qrels.append(QrelEntry(query_id=qid, doc_id=doc_id, relevance=1))

        for doc_id, doc_text in (row.get("negative_docs") or {}).items():
            doc_id = str(doc_id)
            if doc_id not in doc_map:
                doc_map[doc_id] = Document(doc_id=doc_id, text=str(doc_text))
            qrels.append(QrelEntry(query_id=qid, doc_id=doc_id, relevance=0))

    return queries, list(doc_map.values()), qrels


def _write_readme(raw_path: Path) -> None:
    """Write manual download instructions to raw_path/README.md."""
    raw_path.mkdir(parents=True, exist_ok=True)
    readme = raw_path / "README.md"
    if not readme.exists():
        readme.write_text(_BRIGHT_MANUAL_INSTRUCTIONS, encoding="utf-8")
        print(f"  Manual instructions written to {readme}")


# ---------------------------------------------------------------------------
# Load from local JSONL (after manual download + prepare step)
# ---------------------------------------------------------------------------

def load_queries_from_jsonl(path: Path) -> list[Query]:
    """Load BRIGHT queries from a local JSONL file."""
    queries: list[Query] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                queries.append(Query.from_dict(json.loads(line)))
    return queries


def load_documents_from_jsonl(path: Path) -> list[Document]:
    """Load BRIGHT documents from a local JSONL file."""
    docs: list[Document] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                docs.append(Document.from_dict(json.loads(line)))
    return docs


def load_qrels_from_jsonl(path: Path) -> list[QrelEntry]:
    """Load BRIGHT qrels from a local JSONL file."""
    qrels: list[QrelEntry] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                qrels.append(QrelEntry.from_dict(json.loads(line)))
    return qrels
