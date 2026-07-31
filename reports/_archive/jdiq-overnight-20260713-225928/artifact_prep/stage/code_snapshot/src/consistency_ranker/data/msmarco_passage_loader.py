"""
MS MARCO passage ranking — streaming export to the repo's raw JSONL layout.

Uses the BEIR Hugging Face mirror (``BeIR/msmarco``) by default so the same
column conventions as other BEIR loaders apply.  The full passage corpus is
large (~8.8M documents); this module **streams** the corpus split to disk and
never holds all passages in memory.

After writing ``documents.jsonl`` (first *max_docs* passages from the stream),
qrels are filtered to those documents and to the selected queries.
"""

from __future__ import annotations

import json
from pathlib import Path

from .beir_loader import BeirNotAvailableError, write_jsonl
from .schema import Document, QrelEntry, Query


def download_msmarco_passage_raw(
    raw_path: Path,
    *,
    max_docs: int,
    max_queries: int | None,
    force: bool,
    hf_corpus_name: str = "BeIR/msmarco",
    hf_qrels_name: str = "BeIR/msmarco-qrels",
) -> None:
    """Download MS MARCO passage data into ``raw_path`` as three JSONL files.

    Parameters
    ----------
    raw_path:
        Directory for output ``queries.jsonl``, ``documents.jsonl``, ``qrels.jsonl``.
    max_docs:
        **Required** cap on passages written (streaming stops after this many).
    max_queries:
        Optional cap on training/dev queries loaded.
    force:
        Overwrite existing raw files.
    """
    try:
        from datasets import load_dataset  # type: ignore[import]
    except ImportError as exc:
        raise BeirNotAvailableError(
            "The 'datasets' library is required. Install with: pip install datasets"
        ) from exc

    raw_path = Path(raw_path)
    raw_path.mkdir(parents=True, exist_ok=True)
    q_path = raw_path / "queries.jsonl"
    d_path = raw_path / "documents.jsonl"
    r_path = raw_path / "qrels.jsonl"

    if q_path.exists() and d_path.exists() and r_path.exists() and not force:
        print(
            f"[msmarco_passage] Raw files already exist in {raw_path}. "
            "Skipping (use --force to re-download)."
        )
        return

    cache_dir = str(raw_path)

    # --- Queries (in-memory; split is manageable) ---
    try:
        print(f"  Loading queries from {hf_corpus_name} …")
        queries_ds = load_dataset(hf_corpus_name, "queries", cache_dir=cache_dir)
        qsplit = queries_ds["queries"]
        queries: list[Query] = []
        for row in qsplit:
            queries.append(
                Query(
                    query_id=str(row["_id"]),
                    text=str(row.get("text", "")),
                )
            )
            if max_queries is not None and len(queries) >= max_queries:
                break
    except Exception as exc:
        raise BeirNotAvailableError(
            f"Could not load queries from {hf_corpus_name!r}: {exc}"
        ) from exc

    qid_set = {q.query_id for q in queries}

    # --- Qrels (filter to selected queries; full qrels can be large) ---
    try:
        print(f"  Loading qrels from {hf_qrels_name} …")
        qrels_ds = load_dataset(hf_qrels_name, cache_dir=cache_dir)
        qrels_all: list[QrelEntry] = []
        for split_name in qrels_ds:
            for row in qrels_ds[split_name]:
                qid = str(row["query-id"])
                if qid not in qid_set:
                    continue
                qrels_all.append(
                    QrelEntry(
                        query_id=qid,
                        doc_id=str(row["corpus-id"]),
                        relevance=int(row.get("score", 1)),
                    )
                )
    except Exception as exc:
        raise BeirNotAvailableError(
            f"Could not load qrels from {hf_qrels_name!r}: {exc}"
        ) from exc

    # --- Corpus: stream to JSONL; stop at max_docs ---
    try:
        print(f"  Streaming corpus from {hf_corpus_name} (max_docs={max_docs}) …")
        stream = load_dataset(
            hf_corpus_name,
            "corpus",
            cache_dir=cache_dir,
            split="corpus",
            streaming=True,
        )
    except Exception as exc:
        raise BeirNotAvailableError(
            f"Could not open streaming corpus for {hf_corpus_name!r}: {exc}\n"
            "If streaming fails, check your datasets library version (>=2.18)."
        ) from exc

    d_path.parent.mkdir(parents=True, exist_ok=True)
    n_written = 0
    with d_path.open("w", encoding="utf-8") as fh:
        for row in stream:  # IterableDataset (Hugging Face)
            if n_written >= max_docs:
                break
            doc = Document(
                doc_id=str(row["_id"]),
                text=str(row.get("text", "")),
                title=str(row.get("title", "")),
            )
            fh.write(json.dumps(doc.to_dict()) + "\n")
            n_written += 1

    doc_set: set[str] = set()
    with d_path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                doc_set.add(str(json.loads(line)["doc_id"]))

    qrels = [qr for qr in qrels_all if qr.doc_id in doc_set]

    write_jsonl(queries, q_path)
    write_jsonl(qrels, r_path)

    print(
        f"[msmarco_passage] Wrote {len(queries)} queries, {n_written} docs, "
        f"{len(qrels)} qrels → {raw_path}"
    )
