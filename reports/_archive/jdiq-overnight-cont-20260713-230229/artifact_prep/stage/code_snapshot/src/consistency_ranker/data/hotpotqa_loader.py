"""
hotpotqa_loader.py
==================
Loader for the HotpotQA multi-hop QA dataset.

HotpotQA is a multi-hop question-answering dataset.  For our ranking
experiments we treat it as a retrieval task:

- Each question is a **query**.
- Each supporting passage (title + sentences) is a **document**.
- Ground-truth supporting facts determine **relevance**: a document is
  relevant (score=1) if its title appears in the gold supporting facts.

We use the ``fullwiki`` configuration from HuggingFace (``hotpot_qa``),
which provides the open-domain / full-wiki retrieval setting.

References
----------
- https://hotpotqa.github.io/
- https://huggingface.co/datasets/hotpot_qa
"""

from __future__ import annotations

import json
from pathlib import Path

from .schema import Document, QrelEntry, Query


def download_hotpotqa(
    raw_path: Path,
    split: str = "validation",
    max_examples: int | None = None,
) -> tuple[list[Query], list[Document], list[QrelEntry]]:
    """Download HotpotQA from HuggingFace and convert to unified schema.

    Each example produces:
    - One :class:`~consistency_ranker.data.schema.Query` (the question).
    - Multiple :class:`~consistency_ranker.data.schema.Document` objects
      (one passage per query/title pair, matching the downstream HotpotQA
      scorers that build a per-query document pool).
    - One :class:`~consistency_ranker.data.schema.QrelEntry` per
      (question, passage) pair.

    Parameters
    ----------
    raw_path:
        Local directory used as HuggingFace cache directory.
    split:
        HuggingFace split to load.  Use ``"validation"`` for fast experiments;
        ``"train"`` for full-scale.
    max_examples:
        Optional cap on examples loaded.

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
        raise ImportError(
            "The 'datasets' library is required to download HotpotQA. "
            "Install it with: pip install datasets"
        ) from exc

    cache_dir = str(raw_path)
    print(f"  Loading HotpotQA ({split}) from HuggingFace …")
    ds = load_dataset("hotpot_qa", "fullwiki", split=split, cache_dir=cache_dir)

    queries: list[Query] = []
    documents: list[Document] = []
    qrels: list[QrelEntry] = []

    for i, ex in enumerate(ds):
        if max_examples is not None and i >= max_examples:
            break

        qid = str(ex["id"])
        queries.append(Query(query_id=qid, text=str(ex["question"])))

        # supporting_facts is a dict with keys "title" and "sent_id"
        relevant_titles: set[str] = set(ex.get("supporting_facts", {}).get("title", []))

        # context is a dict with keys "title" and "sentences"
        context_titles = ex.get("context", {}).get("title", [])
        context_sentences = ex.get("context", {}).get("sentences", [])

        for title, sents in zip(context_titles, context_sentences):
            doc_id = f"{qid}::{title}"
            documents.append(Document(
                doc_id=doc_id,
                text=" ".join(sents),
                title=title,
                metadata={"query_id": qid},
            ))
            rel = 1 if title in relevant_titles else 0
            qrels.append(QrelEntry(query_id=qid, doc_id=doc_id, relevance=rel))

    return queries, documents, qrels


# ---------------------------------------------------------------------------
# Load from local JSONL (after prepare_datasets.py has run)
# ---------------------------------------------------------------------------

def load_queries_from_jsonl(path: Path) -> list[Query]:
    """Load HotpotQA queries from a local JSONL file."""
    queries: list[Query] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                queries.append(Query.from_dict(json.loads(line)))
    return queries


def load_documents_from_jsonl(path: Path) -> list[Document]:
    """Load HotpotQA documents from a local JSONL file."""
    docs: list[Document] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                docs.append(Document.from_dict(json.loads(line)))
    return docs


def load_qrels_from_jsonl(path: Path) -> list[QrelEntry]:
    """Load HotpotQA qrels from a local JSONL file."""
    qrels: list[QrelEntry] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                qrels.append(QrelEntry.from_dict(json.loads(line)))
    return qrels
