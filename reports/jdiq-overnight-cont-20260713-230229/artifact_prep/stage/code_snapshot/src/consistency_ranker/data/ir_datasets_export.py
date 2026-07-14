"""
Export TREC-style benchmarks via the optional ``ir-datasets`` library.

These datasets are **not** fetched through Hugging Face ``datasets`` alone.
Install with::

    pip install 'consistency-ranker[ir]'

or ``pip install ir-datasets``.

The first use may download large corpora under ir-datasets' cache; TREC and
disk redistribution terms apply (see each dataset's documentation).
"""

from __future__ import annotations

from pathlib import Path

from .beir_loader import write_jsonl
from .schema import Document, QrelEntry, Query


class IrDatasetsNotAvailableError(RuntimeError):
    """Raised when ``ir-datasets`` is not installed or export fails."""


def ir_datasets_available() -> bool:
    try:
        import ir_datasets  # noqa: F401
    except ImportError:
        return False
    return True


def _require_ir_datasets():
    try:
        import ir_datasets  # type: ignore[import]
    except ImportError as exc:
        raise IrDatasetsNotAvailableError(
            "The 'ir-datasets' package is required for this dataset. "
            "Install with: pip install 'consistency-ranker[ir]'"
        ) from exc
    return ir_datasets


def export_trec_dl_passage_to_raw(
    raw_path: Path,
    *,
    ir_subset: str,
    max_queries: int | None,
    force: bool,
) -> None:
    """Write TREC DL passage queries, judged qrels, and passage texts to JSONL.

    *ir_subset* examples: ``"msmarco-passage/trec-dl-2019"``,
    ``"msmarco-passage/trec-dl-2020"``.

    Passage bodies are resolved through the MS MARCO passage collection inside
    ir-datasets (no dependency on a separate local msmarco_passage export).
    """
    ir_datasets = _require_ir_datasets()
    raw_path = Path(raw_path)
    q_path = raw_path / "queries.jsonl"
    d_path = raw_path / "documents.jsonl"
    r_path = raw_path / "qrels.jsonl"

    if q_path.exists() and d_path.exists() and r_path.exists() and not force:
        print(
            f"[trec_dl_passage] Raw files already exist in {raw_path}. "
            "Skipping (use --force)."
        )
        return

    try:
        ds = ir_datasets.load(ir_subset)
    except Exception as exc:
        raise IrDatasetsNotAvailableError(
            f"ir_datasets.load({ir_subset!r}) failed: {exc}"
        ) from exc

    queries: list[Query] = []
    for q in ds.queries_iter():
        queries.append(Query(query_id=str(q.query_id), text=str(q.text)))
        if max_queries is not None and len(queries) >= max_queries:
            break

    qid_set = {q.query_id for q in queries}
    qrels: list[QrelEntry] = []
    for qr in ds.qrels_iter():
        if str(qr.query_id) not in qid_set:
            continue
        qrels.append(
            QrelEntry(
                query_id=str(qr.query_id),
                doc_id=str(qr.doc_id),
                relevance=int(qr.relevance),
            )
        )

    doc_ids = {qr.doc_id for qr in qrels}
    try:
        mcp = ir_datasets.load("msmarco-passage")
        store = mcp.docs_store()
    except Exception as exc:
        raise IrDatasetsNotAvailableError(
            f"Could not open msmarco-passage doc store for passage text: {exc}"
        ) from exc

    documents: list[Document] = []
    missing: list[str] = []
    for did in sorted(doc_ids):
        try:
            doc = store.get(did)
        except Exception:
            missing.append(did)
            continue
        if doc is None:
            missing.append(did)
            continue
        text = getattr(doc, "text", None) or ""
        title = getattr(doc, "title", None) or ""
        documents.append(
            Document(doc_id=str(did), text=str(text), title=str(title or ""))
        )

    if missing:
        print(
            f"[trec_dl_passage] Warning: could not resolve {len(missing)} / "
            f"{len(doc_ids)} passage ids (showing up to 5): {missing[:5]}"
        )

    raw_path.mkdir(parents=True, exist_ok=True)
    write_jsonl(queries, q_path)
    write_jsonl(documents, d_path)
    write_jsonl(qrels, r_path)
    print(
        f"[trec_dl_passage] Wrote {len(queries)} queries, {len(documents)} docs, "
        f"{len(qrels)} qrels → {raw_path}"
    )


def export_robust04_to_raw(
    raw_path: Path,
    *,
    max_queries: int | None,
    max_docs: int | None,
    force: bool,
) -> None:
    """Export TREC Robust 2004 to unified JSONL via ir-datasets."""
    ir_datasets = _require_ir_datasets()
    raw_path = Path(raw_path)
    q_path = raw_path / "queries.jsonl"
    d_path = raw_path / "documents.jsonl"
    r_path = raw_path / "qrels.jsonl"

    if q_path.exists() and d_path.exists() and r_path.exists() and not force:
        print(
            f"[robust04] Raw files already exist in {raw_path}. Skipping (use --force)."
        )
        return

    ds = None
    last_err: Exception | None = None
    for name in ("robust04", "trec-robust-2004"):
        try:
            ds = ir_datasets.load(name)
            break
        except Exception as exc:
            last_err = exc
            ds = None
    if ds is None:
        raise IrDatasetsNotAvailableError(
            f"Could not load Robust04 from ir-datasets (tried robust04, trec-robust-2004): {last_err}"
        )

    queries: list[Query] = []
    for q in ds.queries_iter():
        queries.append(Query(query_id=str(q.query_id), text=str(q.text)))
        if max_queries is not None and len(queries) >= max_queries:
            break

    qid_set = {q.query_id for q in queries}
    qrels: list[QrelEntry] = []
    for qr in ds.qrels_iter():
        if str(qr.query_id) not in qid_set:
            continue
        qrels.append(
            QrelEntry(
                query_id=str(qr.query_id),
                doc_id=str(qr.doc_id),
                relevance=int(qr.relevance),
            )
        )

    doc_ids = {qr.doc_id for qr in qrels}
    sorted_ids = sorted(doc_ids, key=str)
    if max_docs is not None:
        sorted_ids = sorted_ids[:max_docs]
    kept = set(sorted_ids)
    qrels = [qr for qr in qrels if qr.doc_id in kept]

    documents: list[Document] = []
    store = ds.docs_store()
    for did in sorted(kept, key=str):
        try:
            doc = store.get(did)
        except Exception:
            continue
        if doc is None:
            continue
        text = getattr(doc, "text", None) or ""
        title = getattr(doc, "title", None) or ""
        documents.append(
            Document(doc_id=str(did), text=str(text), title=str(title or ""))
        )

    raw_path.mkdir(parents=True, exist_ok=True)
    write_jsonl(queries, q_path)
    write_jsonl(documents, d_path)
    write_jsonl(qrels, r_path)
    print(
        f"[robust04] Wrote {len(queries)} queries, {len(documents)} docs, "
        f"{len(qrels)} qrels → {raw_path}"
    )


def write_manual_placeholder_readme(raw_path: Path, title: str, body: str) -> None:
    """Write a README for manual-only acquisition (idempotent)."""
    raw_path = Path(raw_path)
    raw_path.mkdir(parents=True, exist_ok=True)
    readme = raw_path / "README.md"
    if readme.exists():
        return
    readme.write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
