"""
Shared query-id selection and file IO utilities.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

from .schema import QrelEntry

MIN_JUDGED_DOCS = 2


def has_usable_eval_labels(qrels_for_query: list[QrelEntry]) -> bool:
    """Return True when qrels support evaluation ranking comparisons.

    Two cases are accepted:

    1. **Explicit multi-grade qrels** (classic): at least ``MIN_JUDGED_DOCS``
       distinct judged documents and at least two distinct relevance values
       on those judgments.

    2. **Shallow / positive-only qrels** (common for BEIR-style exports):
       at least one judged document with strictly positive relevance.
       Documents that appear in the evaluation candidate pool but are absent
       from qrels are treated as relevance **0** when metrics are computed
       in the real-data experiment pipeline (candidate-aligned qrels).
       This matches pooled retrieval evaluation where only positives (or a
       sparse judgment file) are listed.

    Queries with no positive judgments remain ineligible.
    """
    if not qrels_for_query:
        return False
    unique_docs = {e.doc_id for e in qrels_for_query}
    n_distinct_grades = len({e.relevance for e in qrels_for_query})
    if len(unique_docs) >= MIN_JUDGED_DOCS and n_distinct_grades >= 2:
        return True
    if len(unique_docs) >= 1 and any(e.relevance > 0 for e in qrels_for_query):
        return True
    return False


def eligible_query_ids(qrels: list[QrelEntry]) -> list[str]:
    """Return sorted query ids with usable evaluation labels."""
    by_query: dict[str, list[QrelEntry]] = defaultdict(list)
    for entry in qrels:
        by_query[entry.query_id].append(entry)
    return sorted(qid for qid, entries in by_query.items() if has_usable_eval_labels(entries))


def sample_query_ids(
    eligible_qids: list[str],
    max_queries: int,
    seed: int,
) -> list[str]:
    """Deterministically sample up to max_queries query ids."""
    qids = list(eligible_qids)
    rng = random.Random(seed)
    rng.shuffle(qids)
    return qids[:max_queries]


def load_query_ids_file(path: Path) -> list[str]:
    """Load query ids from TXT or JSONL.

    TXT format: one query id per line.
    JSONL format: either {"query_id": "..."} or {"id": "..."} per line.
    """
    if not path.exists():
        raise FileNotFoundError(f"Query-id file not found: {path}")

    query_ids: list[str] = []
    if path.suffix.lower() == ".jsonl":
        with path.open(encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                qid = row.get("query_id", row.get("id"))
                if qid is None:
                    raise ValueError(
                        f"{path}:{lineno} missing query_id/id key in JSONL record."
                    )
                query_ids.append(str(qid))
    else:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                qid = line.strip()
                if qid:
                    query_ids.append(qid)
    return query_ids


def save_query_ids_file(query_ids: list[str], path: Path) -> Path:
    """Write query ids as one-per-line TXT."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for qid in query_ids:
            fh.write(f"{qid}\n")
    return path
