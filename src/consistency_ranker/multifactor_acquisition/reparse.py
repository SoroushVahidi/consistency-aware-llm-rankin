"""Offline reparse of persisted RAW_RESPONSES without modifying the raw file."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from consistency_ranker.multi_provider_eval.parsing import (
    PARSER_VERSION,
    classify_raw_response,
    parse_pairwise_response_detailed,
)
from consistency_ranker.multi_provider_eval.prompts import get_prompt


def reparse_raw_responses(
    raw_path: Path,
    *,
    provider: str | None = "azure",
    out_path: Path | None = None,
) -> dict[str, Any]:
    """Reparse RAW_RESPONSES.jsonl into a versioned artifact (raw file untouched)."""
    rows_out: list[dict[str, Any]] = []
    cats: Counter[str] = Counter()
    recoverable = 0
    unusable = 0
    examined = 0
    newly_valid = 0
    if not raw_path.exists():
        raise FileNotFoundError(raw_path)
    with raw_path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            if provider and row.get("provider") != provider:
                continue
            examined += 1
            raw = row.get("raw_response") or ""
            prompt_version = str(row.get("prompt_version") or "legacy_v1")
            try:
                spec = get_prompt(prompt_version)
                allow_tie = spec.allows_tie
                structured = spec.structured_json
            except KeyError:
                allow_tie = False
                structured = False
            ct = row.get("completion_tokens")
            mt = row.get("max_tokens")
            cat = classify_raw_response(
                str(raw),
                completion_tokens=int(ct) if ct is not None else None,
                max_tokens=int(mt) if mt is not None else None,
            )
            cats[cat] += 1
            choice, conf, note, fmt = parse_pairwise_response_detailed(
                str(raw),
                allow_tie=allow_tie,
                structured_json=structured,
                completion_tokens=int(ct) if ct is not None else None,
                max_tokens=int(mt) if mt is not None else None,
            )
            valid = choice in {"A", "B", "TIE", "INSUFFICIENT_INFORMATION"}
            was_valid = bool(row.get("valid"))
            if valid and not was_valid:
                newly_valid += 1
            if valid:
                recoverable += 1
            else:
                unusable += 1
            rows_out.append(
                {
                    "cell_identity": row.get("cell_identity"),
                    "cache_key": row.get("cache_key"),
                    "provider": row.get("provider"),
                    "model": row.get("model"),
                    "query_id": row.get("query_id"),
                    "prompt_version": prompt_version,
                    "displayed_orientation": row.get("displayed_orientation"),
                    "raw_response_ref": {
                        "cache_key": row.get("cache_key"),
                        "timestamp_utc": row.get("timestamp_utc"),
                        "completion_tokens": ct,
                        "max_tokens": mt,
                    },
                    "parser_version": PARSER_VERSION,
                    "output_format_category": fmt,
                    "classify_category": cat,
                    "parsed_choice": choice,
                    "confidence_category": conf,
                    "parse_note": note,
                    "valid": valid,
                    "was_valid_original": was_valid,
                    "canonical_result": choice if valid else None,
                }
            )
    out_path = out_path or (raw_path.parent / f"REPARSED_JUDGMENTS_{PARSER_VERSION}.jsonl")
    with out_path.open("w", encoding="utf-8") as fh:
        for r in rows_out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = {
        "provider_filter": provider,
        "examined": examined,
        "category_counts": dict(cats),
        "valid_after_reparse": recoverable,
        "unusable": unusable,
        "newly_valid_vs_original": newly_valid,
        "parser_version": PARSER_VERSION,
        "artifact": str(out_path),
        "raw_untouched": True,
    }
    (out_path.parent / f"REPARSE_SUMMARY_{PARSER_VERSION}.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary
