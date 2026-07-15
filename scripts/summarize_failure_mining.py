#!/usr/bin/env python
"""
summarize_failure_mining.py
============================
Rebuild the aggregate failure-mining outputs (query_level_metrics.csv,
table_*.csv, failure_mining_summary.md) from whatever query-level full
records currently exist in an output directory.

This is safe to run at any time, including while
scripts/run_failure_mining.py is still writing to the same directory in
another process/tmux pane: it only reads query_level_full_records.jsonl
(each line is appended atomically) and (re)writes the aggregate files. It
never touches the raw per-query JSONL files or the resume checkpoint, so it
cannot cause a partial run to skip or duplicate work.

Usage
-----
    python scripts/summarize_failure_mining.py --input-dir reports/failure_mining_llm_v2

    # write the rebuilt tables/summary somewhere else instead of in place
    python scripts/summarize_failure_mining.py \\
        --input-dir reports/failure_mining_llm_v2 \\
        --output-dir /tmp/failure_mining_llm_v2_preview
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))

from consistency_ranker.failure_mining.analysis import (
    OUR_REPAIRED_METHOD,
    build_summary_markdown,
    write_aggregate_tables,
)


def _load_records(input_dir: Path) -> list[dict]:
    path = input_dir / "query_level_full_records.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"No query_level_full_records.jsonl found in {input_dir}")
    records: list[dict] = []
    bad_lines = 0
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                # A line can be truncated if this script runs mid-write of
                # the very last record; skip it rather than fail the rebuild.
                bad_lines += 1
    if bad_lines:
        print(f"[summarize_failure_mining] skipped {bad_lines} incomplete/corrupt line(s)")
    return records


def _coverage_report(records: list[dict]) -> str:
    total = Counter()
    llm_covered = Counter()
    for r in records:
        qm = r.get("query_metadata", {})
        key = (qm.get("dataset"), qm.get("vote_regime"))
        total[key] += 1
        if any(k.startswith("llm_") for k in r.get("method_outputs", {})):
            llm_covered[key] += 1
    lines = ["dataset,vote_regime,n_records,n_with_real_llm_coverage"]
    for key in sorted(total):
        ds, regime = key
        lines.append(f"{ds},{regime},{total[key]},{llm_covered.get(key, 0)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing query_level_full_records.jsonl (a failure-mining output-dir).",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Where to write rebuilt tables/summary. Defaults to --input-dir (in place).",
    )
    args = p.parse_args(argv)

    output_dir = args.output_dir or args.input_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    records = _load_records(args.input_dir)
    print(f"[summarize_failure_mining] loaded {len(records)} query-level records from {args.input_dir}")

    coverage = _coverage_report(records)
    (output_dir / "dataset_regime_coverage.csv").write_text(coverage + "\n", encoding="utf-8")
    print(coverage)

    write_aggregate_tables(output_dir, records)
    run_meta = {
        "status": "partial-rebuild",
        "n_records_total": len(records),
        "source_dir": str(args.input_dir),
        "our_method": OUR_REPAIRED_METHOD,
    }
    build_summary_markdown(output_dir, records, run_meta)
    print(f"[summarize_failure_mining] rebuilt aggregate tables + summary in {output_dir}")


if __name__ == "__main__":
    main()
