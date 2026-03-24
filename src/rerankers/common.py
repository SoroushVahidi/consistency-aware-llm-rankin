"""
common.py
=========
Shared utilities for the modern reranking baselines:
- Judgment caching (JSON-lines on disk)
- Budget tracking for LLM-based methods
- Result serialization helpers
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class BudgetTracker:
    """Track LLM call budget and usage."""

    max_calls: int | None = None
    calls_made: int = 0
    tokens_in: int = 0
    tokens_out: int = 0

    def record(self, tokens_in: int = 0, tokens_out: int = 0) -> None:
        self.calls_made += 1
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out

    @property
    def budget_exhausted(self) -> bool:
        if self.max_calls is None:
            return False
        return self.calls_made >= self.max_calls

    def summary(self) -> dict:
        return {
            "calls_made": self.calls_made,
            "max_calls": self.max_calls,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
        }


def _cache_key(
    query_id: str,
    doc_ids: list[str],
    method: str,
    *,
    preserve_doc_order: bool = False,
) -> str:
    """Deterministic cache key from query, docs, and method identifier."""
    payload = json.dumps(
        {
            "q": query_id,
            "d": list(doc_ids) if preserve_doc_order else sorted(doc_ids),
            "m": method,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


class JudgmentCache:
    """Disk-backed cache for LLM / reranker judgments.

    Stores one JSON object per line.  Thread-safe for append-only writes.
    """

    def __init__(
        self,
        cache_dir: Path | str,
        method: str,
        *,
        preserve_doc_order: bool = False,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.method = method
        self.preserve_doc_order = preserve_doc_order
        self._file = self.cache_dir / f"{method}_judgments.jsonl"
        self._index: dict[str, dict] = {}
        self._load_existing()

    def _load_existing(self) -> None:
        if not self._file.exists():
            return
        with self._file.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    key = obj.get("cache_key", "")
                    if key:
                        self._index[key] = obj
                except json.JSONDecodeError:
                    continue
        log.info("Loaded %d cached judgments for %s", len(self._index), self.method)

    def get(self, query_id: str, doc_ids: list[str]) -> dict | None:
        key = _cache_key(
            query_id,
            doc_ids,
            self.method,
            preserve_doc_order=self.preserve_doc_order,
        )
        return self._index.get(key)

    def put(self, query_id: str, doc_ids: list[str], result: dict) -> None:
        key = _cache_key(
            query_id,
            doc_ids,
            self.method,
            preserve_doc_order=self.preserve_doc_order,
        )
        entry = {"cache_key": key, "query_id": query_id, "doc_ids": doc_ids, **result}
        self._index[key] = entry
        with self._file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def __len__(self) -> int:
        return len(self._index)


@dataclass
class RerankerResult:
    """Standardized output from any reranker."""

    query_id: str
    ranked_doc_ids: list[str]
    scores: dict[str, float] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


def load_queries_and_docs(
    dataset_name: str,
) -> tuple[list, list, list]:
    """Load dataset splits via the consistency_ranker unified loader.

    Returns (queries, documents, qrels).
    """
    from consistency_ranker.data.unified_loader import load_dataset_splits

    return load_dataset_splits(dataset_name)


def build_candidate_pool(
    query_id: str,
    qrels_by_query: dict[str, list],
    documents_by_id: dict[str, object],
    top_k: int,
) -> list[tuple[str, str]]:
    """Build (doc_id, doc_text) candidate pool for a query from qrels.

    Returns up to top_k candidates sorted by relevance (descending), then doc_id.
    """
    entries = qrels_by_query.get(query_id, [])
    sorted_entries = sorted(entries, key=lambda e: (-e.relevance, e.doc_id))[:top_k]
    pool = []
    for entry in sorted_entries:
        doc = documents_by_id.get(entry.doc_id)
        if doc is None:
            continue
        text = getattr(doc, "text", "") or getattr(doc, "title", "") or str(doc)
        pool.append((entry.doc_id, text))
    return pool


def get_llm_api_key() -> str | None:
    """Retrieve LLM API key from environment."""
    for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "LLM_API_KEY"):
        key = os.environ.get(var)
        if key:
            return key
    return None


def is_dry_run() -> bool:
    """Check if we should run in dry-run/mock mode (no real LLM calls)."""
    return get_llm_api_key() is None


def write_score_file(
    results: list[RerankerResult],
    output_path: Path,
) -> None:
    """Write reranker results as a score JSONL file compatible with the existing pipeline.

    Format: one JSON object per line with keys: query_id, doc_id, score.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for result in results:
            for rank, doc_id in enumerate(result.ranked_doc_ids):
                score = result.scores.get(doc_id, len(result.ranked_doc_ids) - rank)
                fh.write(
                    json.dumps(
                        {"query_id": result.query_id, "doc_id": doc_id, "score": score}
                    )
                    + "\n"
                )


def write_pairwise_file(
    preferences: dict[str, list[tuple[str, str, float]]],
    output_path: Path,
) -> None:
    """Write pairwise preferences as JSONL compatible with the existing pipeline.

    Format: one JSON object per line with keys: query_id, winner_doc_id, loser_doc_id, weight.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for query_id, pairs in preferences.items():
            for winner, loser, weight in pairs:
                fh.write(
                    json.dumps(
                        {
                            "query_id": query_id,
                            "winner_doc_id": winner,
                            "loser_doc_id": loser,
                            "weight": weight,
                        }
                    )
                    + "\n"
                )
