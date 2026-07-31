"""Deterministic query selection for the frozen micro-pilot."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def select_lexicographic_queries(
    *,
    qrels_path: Path,
    queries_path: Path | None,
    n: int = 2,
) -> list[str]:
    """Select the first *n* query IDs with ≥1 positive qrel (and text if available).

    Selection uses only pre-execution characteristics. Policy/provider outcomes
    must never influence this choice.
    """
    qrels: dict[str, dict[str, int]] = defaultdict(dict)
    with qrels_path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            qrels[str(rec["query_id"])][str(rec["doc_id"])] = int(rec["relevance"])

    qtext: dict[str, str] = {}
    if queries_path is not None and queries_path.exists():
        with queries_path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                qid = str(rec.get("query_id") or rec.get("id"))
                qtext[qid] = str(rec.get("text") or rec.get("query") or "")

    eligible: list[str] = []
    for qid in sorted(qrels):
        if qtext and not qtext.get(qid, "").strip():
            continue
        if any(grade > 0 for grade in qrels[qid].values()):
            eligible.append(qid)
    if not eligible:
        raise ValueError(f"no eligible queries in {qrels_path}")
    return eligible[:n]


def load_frozen_query_ids(config: dict[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for ds, meta in (config.get("datasets") or {}).items():
        out[str(ds)] = list(meta["query_ids"])
    return out
