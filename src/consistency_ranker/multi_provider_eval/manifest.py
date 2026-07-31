"""Deterministic sampling manifests for multi-provider experiments."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any


def _stable_rng(seed: int, *parts: str) -> random.Random:
    h = hashlib.sha256(f"{seed}::{'::'.join(parts)}".encode()).hexdigest()
    return random.Random(int(h[:16], 16))


def build_pilot_manifest(
    *,
    dataset: str,
    queries: list[dict[str, Any]],
    candidates_by_query: dict[str, list[dict[str, Any]]],
    n_queries: int = 2,
    n_docs: int = 4,
    seed: int = 42,
    max_doc_chars: int = 1200,
) -> dict[str, Any]:
    """Fixed small pilot: identical pairs for every provider.

    ``queries`` items need ``query_id`` and ``text``.
    Candidate docs need ``doc_id`` and ``text``.
    """
    rng = _stable_rng(seed, dataset, "pilot")
    qids = sorted(candidates_by_query.keys())
    if len(qids) > n_queries:
        qids = rng.sample(qids, n_queries)
    else:
        qids = qids[:n_queries]
    qmap = {str(q["query_id"]): q for q in queries}
    items = []
    for qid in sorted(qids):
        q = qmap[qid]
        docs = list(candidates_by_query[qid])
        rng_q = _stable_rng(seed, dataset, qid)
        if len(docs) > n_docs:
            docs = rng_q.sample(docs, n_docs)
        docs = sorted(docs, key=lambda d: str(d["doc_id"]))
        # All unordered pairs.
        pairs = []
        for i in range(len(docs)):
            for j in range(i + 1, len(docs)):
                pairs.append(
                    {
                        "doc_a_id": str(docs[i]["doc_id"]),
                        "doc_b_id": str(docs[j]["doc_id"]),
                    }
                )
        items.append(
            {
                "dataset": dataset,
                "query_id": qid,
                "query_text": str(q.get("text") or q.get("query") or ""),
                "documents": [
                    {
                        "doc_id": str(d["doc_id"]),
                        "text": str(d.get("text") or d.get("contents") or "")[
                            :max_doc_chars
                        ],
                        "truncated": len(str(d.get("text") or d.get("contents") or ""))
                        > max_doc_chars,
                    }
                    for d in docs
                ],
                "pairs": pairs,
            }
        )
    n_pairs = sum(len(it["pairs"]) for it in items)
    return {
        "manifest_version": "pilot_v1",
        "seed": seed,
        "dataset": dataset,
        "n_queries": len(items),
        "n_docs_per_query": n_docs,
        "n_unordered_pairs": n_pairs,
        "max_doc_chars": max_doc_chars,
        "items": items,
    }


def estimate_call_budget(
    manifest: dict[str, Any],
    *,
    n_providers: int,
    n_prompts: int,
    orientations: int = 2,
    repeats: int = 1,
    n_models_per_provider: int = 1,
) -> dict[str, int]:
    n_pairs = int(manifest["n_unordered_pairs"])
    per_cell = n_pairs * orientations * repeats
    total = per_cell * n_providers * n_prompts * n_models_per_provider
    return {
        "n_unordered_pairs": n_pairs,
        "orientations": orientations,
        "repeats": repeats,
        "n_providers": n_providers,
        "n_prompts": n_prompts,
        "n_models_per_provider": n_models_per_provider,
        "estimated_max_calls": total,
    }


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
