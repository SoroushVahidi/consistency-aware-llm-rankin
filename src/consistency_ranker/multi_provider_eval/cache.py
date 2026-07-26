"""Provenance-rich judgment cache with full cache keys."""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any

from consistency_ranker.multi_provider_eval.schema import JudgmentRecord


def make_cache_key(
    *,
    provider: str,
    model: str,
    prompt_version: str,
    query_id: str,
    doc_a_id: str,
    doc_b_id: str,
    orientation: str,
    temperature: float,
    top_p: float | None,
    max_tokens: int,
    seed: int | None,
    code_version: str = "multi_provider_eval_v1",
    repeat_index: int = 0,
) -> str:
    """Cache key includes every setting that can change the response."""
    payload = {
        "provider": provider,
        "model": model,
        "prompt_version": prompt_version,
        "query_id": query_id,
        "doc_a_id": doc_a_id,
        "doc_b_id": doc_b_id,
        "orientation": orientation,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "seed": seed,
        "code_version": code_version,
        "repeat_index": repeat_index,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def canonical_pair_id(query_id: str, doc_x: str, doc_y: str) -> str:
    a, b = sorted([doc_x, doc_y])
    return f"{query_id}::{a}::{b}"


class ProvenanceJudgmentStore:
    """Append-only JSONL store keyed by full provenance cache keys.

    Never deletes or rewrites existing lines.  In-memory index is rebuilt from
    disk on init for resume safety.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._index: dict[str, dict[str, Any]] = {}
        if self.path.exists():
            with self.path.open(encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    key = rec.get("cache_key")
                    if key:
                        self._index[key] = rec

    def get(self, cache_key: str) -> dict[str, Any] | None:
        return self._index.get(cache_key)

    def put(self, record: JudgmentRecord) -> None:
        data = record.to_dict()
        key = data["cache_key"]
        with self._lock:
            if key in self._index:
                return
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
                f.flush()
            self._index[key] = data

    def __len__(self) -> int:
        return len(self._index)

    def all_records(self) -> list[dict[str, Any]]:
        return list(self._index.values())
