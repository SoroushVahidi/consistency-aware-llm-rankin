"""Append-only JSONL store for normalized judgments, keyed by request_hash.

Distinct from ``multi_provider_eval.cache.ProvenanceJudgmentStore`` because the
frozen judgment schema here (A/B/TIE/ABSTAIN + evidence_strength/reason_code)
differs from that store's Choice vocabulary; the on-disk mechanics (rebuild
index from disk, append-only, never rewrite) are intentionally the same
pattern.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


class JudgmentCacheStore:
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
                    key = rec.get("request_hash")
                    if key:
                        self._index[key] = rec

    def get(self, request_hash: str) -> dict[str, Any] | None:
        return self._index.get(request_hash)

    def put(self, record: dict[str, Any]) -> None:
        key = record["request_hash"]
        with self._lock:
            if key in self._index:
                return
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
                f.flush()
            self._index[key] = record

    def __len__(self) -> int:
        return len(self._index)

    def all_records(self) -> list[dict[str, Any]]:
        return list(self._index.values())
