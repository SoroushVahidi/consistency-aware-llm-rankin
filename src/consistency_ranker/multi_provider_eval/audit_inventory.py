"""Inventory existing LLM judgment caches (read-only provenance audit)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


def inventory_judgment_caches(repo_root: Path) -> list[dict[str, Any]]:
    """Scan known locations for llm_pairwise_judgments.jsonl files."""
    patterns = [
        "outputs/**/judgment_cache/llm_pairwise_judgments.jsonl",
        "outputs/**/llm_pairwise_judgments.jsonl",
        "reports/**/llm_cache/**/llm_pairwise_judgments.jsonl",
    ]
    seen: set[Path] = set()
    rows: list[dict[str, Any]] = []
    for pat in patterns:
        for path in repo_root.glob(pat):
            path = path.resolve()
            if path in seen:
                continue
            seen.add(path)
            rows.append(_summarize_cache(path, repo_root))
    rows.sort(key=lambda r: r["path"])
    return rows


def _summarize_cache(path: Path, repo_root: Path) -> dict[str, Any]:
    n = 0
    query_ids: set[str] = set()
    keys = Counter()
    sample = None
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                n += 1
                rec = json.loads(line)
                if sample is None:
                    sample = sorted(rec.keys())
                qid = rec.get("query_id")
                if qid:
                    query_ids.add(str(qid))
                for k in rec:
                    keys[k] += 1
    except OSError as exc:
        return {
            "path": str(path.relative_to(repo_root)),
            "error": str(exc),
            "n_records": 0,
        }
    has_model = "model" in keys or "provider" in keys
    return {
        "path": str(path.relative_to(repo_root)),
        "n_records": n,
        "n_query_ids": len(query_ids),
        "schema_keys": sample or [],
        "has_model_provenance": has_model,
        "mtime_unix": path.stat().st_mtime,
        "risk": (
            "legacy_cache_key_omits_model_prompt_decoding"
            if not has_model
            else "sidecar_or_enriched"
        ),
    }
