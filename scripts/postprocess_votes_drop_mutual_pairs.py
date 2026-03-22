#!/usr/bin/env python
"""
Drop vote rows that belong to **mutually contradictory** document pairs.

For each query, if both directed edges ``a → b`` and ``b → a`` appear (possibly
from different rankers), **all** rows for that unordered pair ``{a,b}`` are
removed. This is a middle ground between ``min_support=2`` (majority collapse)
and raw ``min_support=1`` (full disagreement): pairwise ties/conflicts are
treated as **unresolved** rather than keeping opposing arcs that create 2-cycles.

Input / output: same JSONL schema as ``build_votes_file.py``.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def _mutual_unordered_pairs(rows: list[dict]) -> set[frozenset[str]]:
    directed: set[tuple[str, str]] = set()
    for row in rows:
        w = str(row.get("winner_doc_id", row.get("winner", "")))
        ell = str(row.get("loser_doc_id", row.get("loser", "")))
        if w and ell and w != ell:
            directed.add((w, ell))
    mutual: set[frozenset[str]] = set()
    for a, b in directed:
        if (b, a) in directed:
            mutual.add(frozenset({a, b}))
    return mutual


def _filter_rows(rows: list[dict], mutual: set[frozenset[str]]) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        w = str(row.get("winner_doc_id", row.get("winner", "")))
        ell = str(row.get("loser_doc_id", row.get("loser", "")))
        if w and ell and frozenset({w, ell}) in mutual:
            continue
        out.append(row)
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()

    by_q: dict[str, list[dict]] = defaultdict(list)
    with args.input.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            by_q[str(row["query_id"])].append(row)

    n_in = sum(len(v) for v in by_q.values())
    n_out = 0
    n_mutual_pairs = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        for qid in sorted(by_q.keys()):
            rows = by_q[qid]
            mutual = _mutual_unordered_pairs(rows)
            n_mutual_pairs += len(mutual)
            kept = _filter_rows(rows, mutual)
            n_out += len(kept)
            for row in kept:
                fh.write(json.dumps(row) + "\n")

    print(
        f"[postprocess_votes_drop_mutual_pairs] queries={len(by_q)} "
        f"rows_in={n_in} rows_out={n_out} "
        f"unordered_mutual_pairs_total={n_mutual_pairs}"
    )
    print(f"[postprocess_votes_drop_mutual_pairs] wrote {args.output}")


if __name__ == "__main__":
    main()
