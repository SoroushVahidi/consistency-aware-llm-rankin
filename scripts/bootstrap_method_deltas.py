"""
bootstrap_method_deltas.py
==========================
Paired bootstrap confidence intervals for method deltas from per-query CSV.

Input CSV format is the output of scripts/run_real_experiment.py:
  <dataset>_per_query.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path


def _load_per_query(path: Path, metric: str) -> dict[str, dict[str, float]]:
    by_query: dict[str, dict[str, float]] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        required = {"query_id", "method", metric}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} missing required columns: {sorted(missing)}")
        for row in reader:
            qid = row["query_id"]
            method = row["method"]
            raw = row.get(metric)
            if raw in {"", None}:
                continue
            try:
                val = float(raw)
            except ValueError:
                continue
            by_query.setdefault(qid, {})[method] = val
    return by_query


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _paired_deltas(
    by_query: dict[str, dict[str, float]],
    method_a: str,
    method_b: str,
) -> tuple[list[str], list[float]]:
    qids: list[str] = []
    deltas: list[float] = []
    for qid, m in by_query.items():
        if method_a not in m or method_b not in m:
            continue
        qids.append(qid)
        deltas.append(m[method_a] - m[method_b])
    return qids, deltas


def _bootstrap_ci(
    deltas: list[float],
    n_bootstrap: int,
    seed: int,
) -> tuple[float, float, float]:
    """Return (mean_delta, ci_low, ci_high)."""
    if not deltas:
        return 0.0, 0.0, 0.0

    rng = random.Random(seed)
    n = len(deltas)
    boots: list[float] = []
    for _ in range(n_bootstrap):
        sample = [deltas[rng.randrange(n)] for _ in range(n)]
        boots.append(_mean(sample))
    boots.sort()
    lo_idx = int(0.025 * (n_bootstrap - 1))
    hi_idx = int(0.975 * (n_bootstrap - 1))
    return _mean(deltas), boots[lo_idx], boots[hi_idx]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute paired bootstrap CIs for method metric deltas.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--per-query-csv", type=Path, required=True)
    parser.add_argument(
        "--metric",
        type=str,
        default="ndcg_at_k",
        choices=["ndcg_at_k", "map_at_k", "pairwise_accuracy"],
    )
    parser.add_argument(
        "--method-a",
        type=str,
        nargs="+",
        required=True,
        help="One or more methods to compare against --method-b.",
    )
    parser.add_argument("--method-b", type=str, required=True)
    parser.add_argument("--n-bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    by_query = _load_per_query(args.per_query_csv, metric=args.metric)
    rows: list[dict] = []
    for method_a in args.method_a:
        qids, deltas = _paired_deltas(by_query, method_a=method_a, method_b=args.method_b)
        mean_delta, ci_low, ci_high = _bootstrap_ci(
            deltas,
            n_bootstrap=args.n_bootstrap,
            seed=args.seed,
        )
        rows.append(
            {
                "metric": args.metric,
                "method_a": method_a,
                "method_b": args.method_b,
                "n_paired_queries": len(qids),
                "mean_delta": mean_delta,
                "ci95_low": ci_low,
                "ci95_high": ci_high,
                "positive_delta": mean_delta > 0.0,
                "ci_excludes_zero": (ci_low > 0.0) or (ci_high < 0.0),
            }
        )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2)
    if args.output_csv is not None:
        args.output_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.output_csv.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else [])
            if rows:
                writer.writeheader()
                writer.writerows(rows)

    print(f"[bootstrap_method_deltas] metric={args.metric}")
    print(f"[bootstrap_method_deltas] method_b={args.method_b}")
    print(f"[bootstrap_method_deltas] compared={len(rows)} methods")
    print(f"[bootstrap_method_deltas] output_json={args.output_json}")
    if args.output_csv is not None:
        print(f"[bootstrap_method_deltas] output_csv={args.output_csv}")
    for row in rows:
        print(
            "[bootstrap_method_deltas] "
            f"{row['method_a']} delta={row['mean_delta']:.6f} "
            f"ci95=[{row['ci95_low']:.6f}, {row['ci95_high']:.6f}] "
            f"paired_queries={row['n_paired_queries']}"
        )


if __name__ == "__main__":
    main()
