#!/usr/bin/env python
"""
build_llm_bootstrap_summaries.py
================================
Compute bootstrap confidence intervals for real LLM runs.

For each run directory, this script:
  - loads the run's per-query CSV
  - computes a bootstrap CI for the method's nDCG@k
  - computes bootstrap CIs for repaired-vs-unrepaired deltas when those methods exist
  - writes <stem>_bootstrap_summary.csv
  - writes BOOTSTRAP_SUMMARY.md
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from pathlib import Path


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _bootstrap_ci(values: list[float], n_bootstrap: int, seed: int) -> tuple[float, float, float]:
    if not values:
        return 0.0, 0.0, 0.0
    rng = random.Random(seed)
    n = len(values)
    boots: list[float] = []
    for _ in range(n_bootstrap):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        boots.append(_mean(sample))
    boots.sort()
    lo_idx = int(0.025 * (n_bootstrap - 1))
    hi_idx = int(0.975 * (n_bootstrap - 1))
    return _mean(values), boots[lo_idx], boots[hi_idx]


def _ndcg_bootstrap_rows(rows: list[dict[str, str]], method: str, n_bootstrap: int, seed: int) -> dict:
    vals = []
    for row in rows:
        if row.get("method") != method:
            continue
        raw = row.get("ndcg_at_k")
        if raw in {"", None}:
            continue
        vals.append(float(raw))
    mean_val, lo, hi = _bootstrap_ci(vals, n_bootstrap=n_bootstrap, seed=seed)
    return {
        "analysis_type": "ndcg_ci",
        "method_a": method,
        "method_b": "",
        "n_paired_queries": len(vals),
        "mean_value": round(mean_val, 6),
        "mean_delta": "",
        "ci95_low": round(lo, 6),
        "ci95_high": round(hi, 6),
        "direction": "",
        "ci_excludes_zero": "",
    }


def _delta_rows(
    rows: list[dict[str, str]],
    method_a: str,
    method_b: str,
    n_bootstrap: int,
    seed: int,
) -> dict | None:
    by_query: dict[str, dict[str, float]] = {}
    for row in rows:
        qid = row.get("query_id", "")
        method = row.get("method", "")
        raw = row.get("ndcg_at_k")
        if not qid or not method or raw in {"", None}:
            continue
        by_query.setdefault(qid, {})[method] = float(raw)

    deltas = []
    for qid, methods in by_query.items():
        if method_a in methods and method_b in methods:
            deltas.append(methods[method_a] - methods[method_b])
    if not deltas:
        return None

    mean_delta, lo, hi = _bootstrap_ci(deltas, n_bootstrap=n_bootstrap, seed=seed)
    if mean_delta > 0:
        direction = "positive"
    elif mean_delta < 0:
        direction = "negative"
    else:
        direction = "neutral"
    return {
        "analysis_type": "delta_ci",
        "method_a": method_a,
        "method_b": method_b,
        "n_paired_queries": len(deltas),
        "mean_value": "",
        "mean_delta": round(mean_delta, 6),
        "ci95_low": round(lo, 6),
        "ci95_high": round(hi, 6),
        "direction": direction,
        "ci_excludes_zero": (lo > 0.0) or (hi < 0.0),
    }


def _methods_present(rows: list[dict[str, str]]) -> list[str]:
    seen = []
    seen_set = set()
    for row in rows:
        method = row.get("method", "")
        if method and method not in seen_set:
            seen.append(method)
            seen_set.add(method)
    return seen


def _per_query_csv_for_dir(run_dir: Path) -> Path:
    candidates = sorted(run_dir.glob("*_per_query.csv"))
    if not candidates:
        raise FileNotFoundError(f"No per-query CSV found under {run_dir}")
    return candidates[0]


def _summary_stem(per_query_csv: Path) -> str:
    name = per_query_csv.name
    return name.replace("_per_query.csv", "")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Bootstrap summaries for real LLM run directories.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        nargs="+",
        required=True,
        help="One or more run directories containing *_per_query.csv files.",
    )
    parser.add_argument("--n-bootstrap", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    for run_dir in args.run_dir:
        per_query_csv = _per_query_csv_for_dir(run_dir)
        rows = _read_rows(per_query_csv)
        methods = _methods_present(rows)
        if not methods:
            raise ValueError(f"No methods found in {per_query_csv}")

        summary_rows = []
        primary_method = methods[0]
        summary_rows.append(
            _ndcg_bootstrap_rows(
                rows,
                method=primary_method,
                n_bootstrap=args.n_bootstrap,
                seed=args.seed,
            )
        )

        for repaired, unrepaired in [
            ("hybrid_rrf_repaired_copeland_a03", "hybrid_rrf_unrepaired_copeland_a03"),
            ("hybrid_rrf_repaired_balance_a03", "hybrid_rrf_unrepaired_balance_a03"),
        ]:
            delta_row = _delta_rows(
                rows,
                method_a=repaired,
                method_b=unrepaired,
                n_bootstrap=args.n_bootstrap,
                seed=args.seed,
            )
            if delta_row is not None:
                summary_rows.append(delta_row)

        stem = _summary_stem(per_query_csv)
        csv_path = run_dir / f"{stem}_bootstrap_summary.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(summary_rows[0].keys()))
            writer.writeheader()
            writer.writerows(summary_rows)

        md = [
            f"# Bootstrap Summary — {run_dir.name}",
            "",
            f"n_bootstrap={args.n_bootstrap}, seed={args.seed}",
            "",
            "| Analysis | Method A | Method B | n | Mean | CI low | CI high | Direction | CI excludes 0 |",
            "|----------|----------|----------|---|------|--------|---------|-----------|---------------|",
        ]
        for row in summary_rows:
            mean_field = (
                f"{float(row['mean_value']):.6f}"
                if row["mean_value"] not in {"", None}
                else f"{float(row['mean_delta']):+.6f}"
            )
            md.append(
                "| "
                + f"{row['analysis_type']} | {row['method_a']} | {row['method_b'] or '—'} | "
                + f"{row['n_paired_queries']} | {mean_field} | {row['ci95_low']:.6f} | "
                + f"{row['ci95_high']:.6f} | {row['direction'] or '—'} | "
                + f"{row['ci_excludes_zero'] if row['ci_excludes_zero'] != '' else '—'} |"
            )

        md_path = run_dir / "BOOTSTRAP_SUMMARY.md"
        md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
        print(f"[build_llm_bootstrap_summaries] run_dir={run_dir}")
        print(f"[build_llm_bootstrap_summaries] csv={csv_path}")
        print(f"[build_llm_bootstrap_summaries] md={md_path}")


if __name__ == "__main__":
    main()
