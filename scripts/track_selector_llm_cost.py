#!/usr/bin/env python
"""
track_selector_llm_cost.py
============================
Companion cost-tracking watcher for the selector_llm_extension run. Polls
query_level_full_records.jsonl / llm_call_records.jsonl, and after every
newly-completed query appends a row to cost_tracking.csv with cumulative
token usage, cumulative estimated cost, and a projected final cost
(extrapolated linearly from the per-query rate observed so far).

If cumulative or projected cost reaches the pause threshold (default $4.50),
sends SIGINT to the target tmux session (same mechanism used for the earlier
manual stop -- safe: checkpoints are only written after a query fully
completes, so interrupting mid-query just means redoing that one query's
calls on resume) and exits.

Cost rates are rough estimates based on observed public pricing, not
verified against actual billing -- see reports/selector_llm_extension/
cost_tracking.csv's own numbers for the live estimate.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

COHERE_IN_PER_M = 2.50
COHERE_OUT_PER_M = 10.0
AZURE_IN_PER_M = 0.40
AZURE_OUT_PER_M = 1.60


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def compute_tokens(llm_call_records: list[dict]) -> dict:
    tok = {"cohere": {"prompt": 0, "completion": 0}, "azure": {"prompt": 0, "completion": 0}}
    for d in llm_call_records:
        p = d.get("provider")
        if p not in tok:
            continue
        st = d.get("llm_stats", {})
        tok[p]["prompt"] += st.get("prompt_tokens", 0)
        tok[p]["completion"] += st.get("completion_tokens", 0)
    return tok


def estimate_cost(tok: dict) -> float:
    c = tok["cohere"]
    a = tok["azure"]
    return (
        c["prompt"] / 1e6 * COHERE_IN_PER_M
        + c["completion"] / 1e6 * COHERE_OUT_PER_M
        + a["prompt"] / 1e6 * AZURE_IN_PER_M
        + a["completion"] / 1e6 * AZURE_OUT_PER_M
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--target-queries", type=int, required=True)
    p.add_argument("--pause-threshold", type=float, default=4.50)
    p.add_argument("--hard-cap", type=float, default=5.00)
    p.add_argument("--tmux-session", type=str, default="selector_llm_extension")
    p.add_argument("--poll-seconds", type=float, default=5.0)
    args = p.parse_args()

    records_path = args.output_dir / "query_level_full_records.jsonl"
    calls_path = args.output_dir / "llm_call_records.jsonl"
    csv_path = args.output_dir / "cost_tracking.csv"

    fieldnames = [
        "timestamp", "completed_queries", "cohere_prompt_tokens", "cohere_completion_tokens",
        "azure_prompt_tokens", "azure_completion_tokens", "estimated_cumulative_cost",
        "projected_final_cost", "paused",
    ]
    if not csv_path.exists():
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=fieldnames).writeheader()

    last_n = -1
    print(f"[track_selector_llm_cost] watching {records_path}, writing {csv_path}", flush=True)
    while True:
        recs = _load_jsonl(records_path)
        n = len(recs)
        if n != last_n:
            calls = _load_jsonl(calls_path)
            tok = compute_tokens(calls)
            cum_cost = estimate_cost(tok)
            projected = (cum_cost / n * args.target_queries) if n > 0 else 0.0
            paused = False

            if cum_cost >= args.pause_threshold or projected >= args.pause_threshold:
                print(
                    f"[track_selector_llm_cost] WARNING: cumulative=${cum_cost:.4f} "
                    f"projected=${projected:.4f} >= threshold ${args.pause_threshold} -- "
                    f"pausing tmux session '{args.tmux_session}'",
                    flush=True,
                )
                subprocess.run(["tmux", "send-keys", "-t", args.tmux_session, "C-c"], check=False)
                paused = True

            with csv_path.open("a", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=fieldnames)
                w.writerow(
                    {
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                        "completed_queries": n,
                        "cohere_prompt_tokens": tok["cohere"]["prompt"],
                        "cohere_completion_tokens": tok["cohere"]["completion"],
                        "azure_prompt_tokens": tok["azure"]["prompt"],
                        "azure_completion_tokens": tok["azure"]["completion"],
                        "estimated_cumulative_cost": round(cum_cost, 4),
                        "projected_final_cost": round(projected, 4),
                        "paused": paused,
                    }
                )
            print(
                f"[track_selector_llm_cost] n={n} cumulative=${cum_cost:.4f} projected=${projected:.4f}",
                flush=True,
            )
            last_n = n
            if paused:
                break
            if n >= args.target_queries:
                print("[track_selector_llm_cost] target reached, stopping watcher", flush=True)
                break

        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
