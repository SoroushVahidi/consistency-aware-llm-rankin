"""Thin wrapper loading the frozen query ids and their text.

Reuses ``counterfactual_pilot.query_selection`` for the frozen selection rule
rather than re-deriving it; this module only adds text loading.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, NamedTuple


class FrozenQuery(NamedTuple):
    dataset: str
    query_id: str
    query_text: str


def _load_query_text(queries_path: Path, query_id: str) -> str:
    with queries_path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            qid = str(rec.get("query_id") or rec.get("id"))
            if qid == query_id:
                return str(rec.get("text") or rec.get("query") or "")
    raise ValueError(f"query_id {query_id!r} not found in {queries_path}")


def load_frozen_queries(config: dict[str, Any], *, repo_root: Path) -> list[FrozenQuery]:
    """Load frozen (dataset, query_id, query_text) triples in config order."""
    out: list[FrozenQuery] = []
    for dataset, meta in config["datasets"].items():
        queries_path = repo_root / meta["queries_path"]
        for qid in meta["query_ids"]:
            out.append(
                FrozenQuery(
                    dataset=dataset,
                    query_id=str(qid),
                    query_text=_load_query_text(queries_path, str(qid)),
                )
            )
    return out
