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
from collections.abc import Iterable, Mapping
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
       ds = load_dataset("xlangai/BRIGHT", "examples")
6. Save the JSONL files to this directory:
       data/raw/bright/
   Expected files:
       queries.jsonl       — one JSON object per line:
                             {query_id|id, text|query|question}
       documents.jsonl     — one JSON object per line:
                             {doc_id|id, text, title?}
       qrels.jsonl         — one JSON object per line:
                             {query_id|query-id, doc_id|corpus-id, relevance|score}

7. Then run:
       python scripts/prepare_datasets.py --dataset bright
"""

_BRIGHT_TASKS_FALLBACK = (
    "examples",
    "documents",
    "long_documents",
    "gpt4_reason",
    "claude-3-opus_reason",
    "llama3-70b_reason",
    "Gemini-1.0_reason",
    "grit_reason",
)
DEFAULT_BRIGHT_TASK = "examples"


class BrightNotAvailableError(RuntimeError):
    """Raised when BRIGHT cannot be downloaded automatically."""


class BrightSchemaError(ValueError):
    """Raised when BRIGHT records cannot be normalized safely."""


def list_available_bright_tasks() -> tuple[str, ...]:
    """Return available BRIGHT config names from HuggingFace.

    Falls back to a static list when config lookup is unavailable.
    """
    try:
        from datasets import get_dataset_config_names  # type: ignore[import]

        configs = get_dataset_config_names("xlangai/BRIGHT")
        if configs:
            return tuple(configs)
    except Exception:  # noqa: BLE001
        pass
    return _BRIGHT_TASKS_FALLBACK


def download_bright(
    raw_path: Path,
    task: str = DEFAULT_BRIGHT_TASK,
    max_examples: int | None = None,
) -> tuple[list[Query], list[Document], list[QrelEntry]]:
    """Attempt to download BRIGHT from HuggingFace.

    Parameters
    ----------
    raw_path:
        Local directory for raw files and HuggingFace cache.
    task:
        BRIGHT config name to load (e.g. ``"examples"``).
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
    available_tasks = list_available_bright_tasks()
    if task not in available_tasks:
        raise ValueError(
            f"Unknown BRIGHT task {task!r}. "
            f"Choose one of: {list(available_tasks)}"
        )

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

    for i, (split_name, row) in enumerate(_iter_rows_with_split(ds, max_examples=max_examples)):
        query, docs_for_query, qrels_for_query = _parse_example_row(
            row,
            row_idx=i,
            split_name=split_name,
        )
        queries.append(query)
        for doc in docs_for_query:
            if doc.doc_id not in doc_map:
                doc_map[doc.doc_id] = doc
        qrels.extend(qrels_for_query)

    _hydrate_missing_documents(
        doc_map=doc_map,
        cache_dir=cache_dir,
    )

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
    return _load_jsonl(path, normalizer=normalize_query_record)


def load_documents_from_jsonl(path: Path) -> list[Document]:
    """Load BRIGHT documents from a local JSONL file."""
    return _load_jsonl(path, normalizer=normalize_document_record)


def load_qrels_from_jsonl(path: Path) -> list[QrelEntry]:
    """Load BRIGHT qrels from a local JSONL file."""
    return _load_jsonl(path, normalizer=normalize_qrel_record)


def load_raw_bright_splits(raw_path: Path) -> tuple[list[Query], list[Document], list[QrelEntry]]:
    """Load and normalize BRIGHT raw JSONL files from ``raw_path``.

    Required files:
    - ``queries.jsonl``
    - ``documents.jsonl``
    - ``qrels.jsonl``
    """
    queries_path = raw_path / "queries.jsonl"
    docs_path = raw_path / "documents.jsonl"
    qrels_path = raw_path / "qrels.jsonl"

    for p in (queries_path, docs_path, qrels_path):
        if not p.exists():
            raise FileNotFoundError(f"Missing BRIGHT raw file: {p}")

    return (
        load_queries_from_jsonl(queries_path),
        load_documents_from_jsonl(docs_path),
        load_qrels_from_jsonl(qrels_path),
    )


def normalize_query_record(record: dict) -> Query:
    """Normalize a BRIGHT query record to :class:`Query`.

    Accepted id keys: ``query_id``, ``id``, ``qid``, ``query-id``.
    Accepted text keys: ``text``, ``query``, ``question``.
    """
    qid = _first_non_null(record, ("query_id", "id", "qid", "query-id"))
    text = _first_non_null(record, ("text", "query", "question"))
    if qid is None:
        raise BrightSchemaError(
            "BRIGHT query record is missing id. "
            "Expected one of: query_id, id, qid, query-id."
        )
    if text is None:
        raise BrightSchemaError(
            "BRIGHT query record is missing text. "
            "Expected one of: text, query, question."
        )

    qid_s = str(qid).strip()
    text_s = str(text).strip()
    if not qid_s:
        raise BrightSchemaError("BRIGHT query id must be non-empty.")
    if not text_s:
        raise BrightSchemaError(f"BRIGHT query {qid_s!r} has empty text.")

    return Query(query_id=qid_s, text=text_s)


def normalize_document_record(record: dict) -> Document:
    """Normalize a BRIGHT document record to :class:`Document`.

    Accepted id keys: ``doc_id``, ``id``, ``corpus_id``, ``corpus-id``.
    Accepted text keys: ``text``, ``contents``, ``body``.
    Optional title keys: ``title``, ``doc_title``.
    """
    doc_id = _first_non_null(record, ("doc_id", "id", "corpus_id", "corpus-id"))
    text = _first_non_null(record, ("text", "contents", "body"))
    title = _first_non_null(record, ("title", "doc_title"), default="")

    if doc_id is None:
        raise BrightSchemaError(
            "BRIGHT document record is missing id. "
            "Expected one of: doc_id, id, corpus_id, corpus-id."
        )

    doc_id_s = str(doc_id).strip()
    text_s = "" if text is None else str(text).strip()
    title_s = str(title).strip()
    if not doc_id_s:
        raise BrightSchemaError("BRIGHT document id must be non-empty.")
    if not text_s and not title_s:
        raise BrightSchemaError(
            f"BRIGHT document {doc_id_s!r} must include text or title."
        )

    return Document(doc_id=doc_id_s, text=text_s, title=title_s)


def normalize_qrel_record(record: dict) -> QrelEntry:
    """Normalize a BRIGHT qrel record to :class:`QrelEntry`.

    Accepted query-id keys: ``query_id``, ``query-id``, ``qid``.
    Accepted doc-id keys: ``doc_id``, ``corpus-id``, ``corpus_id``, ``docid``.
    Accepted relevance keys: ``relevance``, ``score``, ``label``.
    """
    query_id = _first_non_null(record, ("query_id", "query-id", "qid"))
    doc_id = _first_non_null(record, ("doc_id", "corpus-id", "corpus_id", "docid"))
    relevance = _first_non_null(record, ("relevance", "score", "label"))

    if query_id is None:
        raise BrightSchemaError(
            "BRIGHT qrel record is missing query id "
            "(query_id | query-id | qid)."
        )
    if doc_id is None:
        raise BrightSchemaError(
            "BRIGHT qrel record is missing doc id "
            "(doc_id | corpus-id | corpus_id | docid)."
        )
    if relevance is None:
        raise BrightSchemaError(
            "BRIGHT qrel record is missing relevance "
            "(relevance | score | label)."
        )

    query_id_s = str(query_id).strip()
    doc_id_s = str(doc_id).strip()
    if not query_id_s or not doc_id_s:
        raise BrightSchemaError("BRIGHT qrel query_id/doc_id must be non-empty.")
    try:
        rel_i = int(relevance)
    except (TypeError, ValueError) as exc:
        raise BrightSchemaError(
            f"BRIGHT qrel relevance must be an integer, got {relevance!r}."
        ) from exc

    return QrelEntry(query_id=query_id_s, doc_id=doc_id_s, relevance=rel_i)


def _iter_rows_with_split(ds: object, max_examples: int | None = None):
    """Yield ``(split_name, row)`` pairs from a HuggingFace dataset object."""
    yielded = 0
    if isinstance(ds, Mapping):
        for split_name in ds.keys():
            split_rows = ds[split_name]
            for row in split_rows:
                yield str(split_name), row
                yielded += 1
                if max_examples is not None and yielded >= max_examples:
                    return
        return

    if isinstance(ds, Iterable):
        for row in ds:
            yield "default", row
            yielded += 1
            if max_examples is not None and yielded >= max_examples:
                return
        return

    raise BrightSchemaError(
        f"Unsupported BRIGHT dataset container type: {type(ds).__name__}"
    )


def _parse_example_row(
    row: object,
    row_idx: int,
    split_name: str = "",
) -> tuple[Query, list[Document], list[QrelEntry]]:
    """Parse one BRIGHT dataset row into Query, Documents, and Qrels."""
    if not isinstance(row, Mapping):
        raise BrightSchemaError(
            f"BRIGHT row at index {row_idx} must be a mapping/dict, got {type(row).__name__}."
        )

    raw_query_id = _first_non_null(row, ("id", "query_id", "qid"), default=str(row_idx))
    query_text = _first_non_null(row, ("query", "question", "text"))
    if query_text is None:
        raise BrightSchemaError(
            f"BRIGHT row {row_idx} is missing query text "
            "(expected query | question | text). Keys: {sorted(row.keys())}"
        )
    query_id = f"{split_name}:{raw_query_id}" if split_name else str(raw_query_id)
    query = Query(query_id=str(query_id), text=str(query_text))

    docs_by_id: dict[str, Document] = {}
    rel_by_doc: dict[str, int] = {}

    positive = _first_non_null(row, ("positive_docs", "positives", "relevant_docs"))
    negative = _first_non_null(row, ("negative_docs", "negatives", "irrelevant_docs"))

    pos_docs, pos_rel = _parse_labeled_docs(
        value=positive,
        default_relevance=1,
        field_name="positive_docs",
        row_idx=row_idx,
    )
    neg_docs, neg_rel = _parse_labeled_docs(
        value=negative,
        default_relevance=0,
        field_name="negative_docs",
        row_idx=row_idx,
    )

    for doc in pos_docs + neg_docs:
        docs_by_id[doc.doc_id] = doc
    for doc_id, rel in list(pos_rel.items()) + list(neg_rel.items()):
        rel_by_doc[doc_id] = max(rel_by_doc.get(doc_id, rel), rel)

    # BRIGHT "examples" rows commonly provide gold/excluded ids, not full doc payloads.
    if not docs_by_id:
        positive_ids = _to_str_id_list(row.get("gold_ids")) + _to_str_id_list(row.get("gold_ids_long"))
        negative_ids = _to_str_id_list(row.get("excluded_ids"))
        negative_ids = [doc_id for doc_id in negative_ids if doc_id.upper() != "N/A"]

        for doc_id in positive_ids:
            docs_by_id[doc_id] = Document(doc_id=doc_id, text="")
            rel_by_doc[doc_id] = max(rel_by_doc.get(doc_id, 1), 1)
        for doc_id in negative_ids:
            docs_by_id.setdefault(doc_id, Document(doc_id=doc_id, text=""))
            rel_by_doc[doc_id] = max(rel_by_doc.get(doc_id, 0), 0)

    if not docs_by_id:
        raise BrightSchemaError(
            f"BRIGHT row {row_idx} produced no documents. "
            "Expected positive_docs/negative_docs or gold_ids/excluded_ids."
        )

    qrels = [
        QrelEntry(query_id=query.query_id, doc_id=doc_id, relevance=rel)
        for doc_id, rel in rel_by_doc.items()
    ]
    return query, list(docs_by_id.values()), qrels


def _parse_labeled_docs(
    value: object,
    default_relevance: int,
    field_name: str,
    row_idx: int,
) -> tuple[list[Document], dict[str, int]]:
    """Parse BRIGHT doc containers into documents and relevance labels."""
    if value is None:
        return [], {}

    docs: dict[str, Document] = {}
    relevance: dict[str, int] = {}

    if isinstance(value, Mapping):
        for raw_doc_id, payload in value.items():
            doc = _document_from_payload(
                raw_doc_id=raw_doc_id,
                payload=payload,
                field_name=field_name,
                row_idx=row_idx,
            )
            docs[doc.doc_id] = doc
            relevance[doc.doc_id] = default_relevance
        return list(docs.values()), relevance

    if isinstance(value, list):
        for entry in value:
            if isinstance(entry, Mapping):
                doc = normalize_document_record(dict(entry))
                rel = _first_non_null(entry, ("relevance", "score", "label"), default=default_relevance)
                try:
                    rel_i = int(rel)
                except (TypeError, ValueError) as exc:
                    raise BrightSchemaError(
                        f"Invalid relevance value {rel!r} in {field_name} at row {row_idx}."
                    ) from exc
                docs[doc.doc_id] = doc
                relevance[doc.doc_id] = rel_i
            else:
                raise BrightSchemaError(
                    f"{field_name} at row {row_idx} contains unsupported list entry "
                    f"type {type(entry).__name__}; expected object/dict entries."
                )
        return list(docs.values()), relevance

    raise BrightSchemaError(
        f"{field_name} at row {row_idx} must be a mapping or list, got {type(value).__name__}."
    )


def _document_from_payload(
    raw_doc_id: object,
    payload: object,
    field_name: str,
    row_idx: int,
) -> Document:
    """Build a :class:`Document` from a mapping entry payload."""
    doc_id_s = str(raw_doc_id).strip()
    if not doc_id_s:
        raise BrightSchemaError(
            f"Empty document id in {field_name} at row {row_idx}."
        )

    if isinstance(payload, Mapping):
        record = dict(payload)
        record.setdefault("doc_id", doc_id_s)
        return normalize_document_record(record)

    if isinstance(payload, str):
        return normalize_document_record({"doc_id": doc_id_s, "text": payload})

    raise BrightSchemaError(
        f"Unsupported payload type in {field_name} for doc {doc_id_s!r}: "
        f"{type(payload).__name__}."
    )


def _hydrate_missing_documents(doc_map: dict[str, Document], cache_dir: str) -> None:
    """Fill missing document text by loading the BRIGHT ``documents`` config."""
    missing = {
        doc_id
        for doc_id, doc in doc_map.items()
        if not str(doc.text).strip() and not str(doc.title).strip()
    }
    if not missing:
        return

    try:
        from datasets import load_dataset  # type: ignore[import]
    except ImportError as exc:
        raise BrightSchemaError(
            "The 'datasets' library is required to resolve BRIGHT document ids "
            "from the 'documents' config."
        ) from exc

    for cfg_name in ("documents", "long_documents"):
        if not missing:
            break
        try:
            docs_ds = load_dataset("xlangai/BRIGHT", cfg_name, cache_dir=cache_dir)
        except Exception:  # noqa: BLE001
            continue

        for _split_name, row in _iter_rows_with_split(docs_ds, max_examples=None):
            if not isinstance(row, Mapping):
                continue
            doc_id = _first_non_null(row, ("id", "doc_id", "corpus_id", "corpus-id"))
            if doc_id is None:
                continue
            doc_id_s = str(doc_id).strip()
            if doc_id_s not in missing:
                continue
            text = _first_non_null(row, ("content", "text", "contents", "body"), default="")
            title = _first_non_null(row, ("title", "doc_title"), default="")
            doc_map[doc_id_s] = Document(
                doc_id=doc_id_s,
                text=str(text),
                title=str(title),
            )
            missing.remove(doc_id_s)
            if not missing:
                break

    if missing:
        sample = sorted(missing)[:5]
        raise BrightSchemaError(
            f"Could not resolve {len(missing)} BRIGHT document ids from the "
            f"'documents'/'long_documents' configs. Sample: {sample}"
        )


def _load_jsonl(path: Path, normalizer):
    records = []
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise BrightSchemaError(
                    f"Invalid JSON in {path} at line {lineno}: {exc.msg}"
                ) from exc
            if not isinstance(raw, dict):
                raise BrightSchemaError(
                    f"Expected a JSON object in {path} at line {lineno}, "
                    f"got {type(raw).__name__}."
                )
            try:
                records.append(normalizer(raw))
            except BrightSchemaError as exc:
                raise BrightSchemaError(
                    f"{path} line {lineno}: {exc}"
                ) from exc
    return records


def _first_non_null(record: Mapping, keys: tuple[str, ...], default=None):
    for key in keys:
        if key in record and record[key] is not None:
            return record[key]
    return default


def _to_str_id_list(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        s = str(item).strip()
        if s and s.upper() != "N/A":
            result.append(s)
    return result
