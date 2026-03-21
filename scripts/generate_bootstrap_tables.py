"""
generate_bootstrap_tables.py
============================
Generate paired bootstrap confidence-interval tables for all datasets and
preference sources produced by ``run_all_real_experiments.py``.

For each (dataset, preference_source) pair, this script computes paired
bootstrap deltas comparing every method in ``--method-a`` against
``--method-b`` (default: ``score_sum``) using the ``ndcg_at_k`` metric (or
any metric passed via ``--metric``).

Outputs are written under ``<output-root>/<dataset>/<source>/bootstrap/``:
  - ``<dataset>_<source>_bootstrap_<metric>.json``
  - ``<dataset>_<source>_bootstrap_<metric>.csv``

Usage
-----
::

    # Default: all datasets, qrels + qrels_flip, compare shortlist vs score_sum
    python scripts/generate_bootstrap_tables.py

    # Custom root and metric
    python scripts/generate_bootstrap_tables.py \\
        --output-root outputs/real_full \\
        --metric map_at_k

    # Specific datasets / sources
    python scripts/generate_bootstrap_tables.py \\
        --datasets scidocs fiqa \\
        --sources qrels

Options
-------
--output-root   Root directory containing per-dataset/per-source outputs
                (default: outputs/real_full)
--datasets      One or more dataset names (default: all four)
--sources       One or more preference sources (default: qrels qrels_flip)
--method-b      Baseline method to compare against (default: score_sum)
--method-a      Methods to compare; defaults to the standard shortlist
--metric        Metric column name (default: ndcg_at_k)
--n-bootstrap   Number of bootstrap resamples (default: 2000)
--seed          Random seed (default: 42)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = Path(__file__).resolve().parent

# Default shortlist of methods to evaluate (the strongest subset requested by
# the problem statement). ``fas_balance_score_prior_alpha_beta`` is now wired
# into the real pipeline; it is included here for completeness.
DEFAULT_METHOD_A = [
    "borda",
    "greedy_fas_weighted_balance",
    "hybrid_rrf_fas_regularized",
    "fas_balance_score_prior_alpha_beta",
]

ALL_DATASETS = ["scidocs", "fiqa", "hotpotqa", "bright"]
ALL_SOURCES = ["qrels", "qrels_flip"]


def _per_query_csv(output_root: Path, dataset: str, source: str) -> Path:
    return output_root / dataset / source / f"{dataset}_per_query.csv"


def _bootstrap_dir(output_root: Path, dataset: str, source: str) -> Path:
    return output_root / dataset / source / "bootstrap"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate bootstrap CI tables for all datasets and sources.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/real_full"),
        help="Root directory containing experiment outputs (default: outputs/real_full)",
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=ALL_DATASETS,
        choices=ALL_DATASETS,
        help="Datasets to process (default: all four)",
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        default=ALL_SOURCES,
        choices=ALL_SOURCES,
        help="Preference sources to process (default: qrels qrels_flip)",
    )
    parser.add_argument(
        "--method-b",
        type=str,
        default="score_sum",
        help="Baseline method to compare against (default: score_sum)",
    )
    parser.add_argument(
        "--method-a",
        nargs="+",
        default=DEFAULT_METHOD_A,
        help=(
            "Methods to compare against --method-b "
            f"(default: {' '.join(DEFAULT_METHOD_A)})"
        ),
    )
    parser.add_argument(
        "--metric",
        type=str,
        default="ndcg_at_k",
        choices=["ndcg_at_k", "map_at_k", "pairwise_accuracy"],
        help="Metric to compute deltas for (default: ndcg_at_k)",
    )
    parser.add_argument(
        "--n-bootstrap",
        type=int,
        default=2000,
        help="Number of bootstrap resamples (default: 2000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    output_root: Path = args.output_root.resolve()

    results: list[dict] = []

    for dataset in args.datasets:
        for source in args.sources:
            csv_path = _per_query_csv(output_root, dataset, source)
            if not csv_path.exists():
                print(
                    f"[SKIP] {dataset}/{source}: per-query CSV not found at {csv_path}"
                )
                results.append(
                    {"dataset": dataset, "source": source, "status": "skipped"}
                )
                continue

            bootstrap_dir = _bootstrap_dir(output_root, dataset, source)
            bootstrap_dir.mkdir(parents=True, exist_ok=True)

            out_json = bootstrap_dir / f"{dataset}_{source}_bootstrap_{args.metric}.json"
            out_csv = bootstrap_dir / f"{dataset}_{source}_bootstrap_{args.metric}.csv"

            cmd = [
                sys.executable,
                str(_SCRIPTS / "bootstrap_method_deltas.py"),
                "--per-query-csv", str(csv_path),
                "--metric", args.metric,
                "--method-a", *args.method_a,
                "--method-b", args.method_b,
                "--n-bootstrap", str(args.n_bootstrap),
                "--seed", str(args.seed),
                "--output-json", str(out_json),
                "--output-csv", str(out_csv),
            ]

            print(f"\n>>> Bootstrap: {dataset}/{source} ({args.metric} vs {args.method_b})")
            result = subprocess.run(cmd, cwd=_REPO_ROOT, capture_output=True, text=True)
            if result.stdout:
                print(result.stdout.rstrip())
            if result.stderr:
                print(result.stderr.rstrip(), file=sys.stderr)

            if result.returncode == 0:
                print(f"    ✓  {out_json.relative_to(_REPO_ROOT)}")
                print(f"    ✓  {out_csv.relative_to(_REPO_ROOT)}")
                results.append(
                    {
                        "dataset": dataset,
                        "source": source,
                        "status": "ok",
                        "json": str(out_json),
                        "csv": str(out_csv),
                    }
                )
            else:
                print(
                    f"[ERROR] bootstrap failed for {dataset}/{source} "
                    f"(exit={result.returncode})"
                )
                results.append(
                    {"dataset": dataset, "source": source, "status": "error"}
                )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print(f"\n{'='*60}")
    print("  BOOTSTRAP GENERATION SUMMARY")
    print(f"{'='*60}")
    for r in results:
        status_icon = "✓" if r["status"] == "ok" else ("?" if r["status"] == "skipped" else "✗")
        print(f"  {status_icon}  {r['dataset']}/{r['source']}  [{r['status']}]")
    ok_count = sum(1 for r in results if r["status"] == "ok")
    print(f"\n  Completed: {ok_count}/{len(results)} pairs")
    print(f"{'='*60}\n")

    if any(r["status"] == "error" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
