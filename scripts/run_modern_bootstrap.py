"""
run_modern_bootstrap.py
=======================
Compute bootstrap confidence intervals for modern baseline comparisons.

Uses the noise-sensitivity per-query CSV as input and computes paired bootstrap
CIs for key method comparisons at a specified noise level.

Usage
-----
::

    python scripts/run_modern_bootstrap.py \\
        --dataset scidocs --flip-prob 0.15 --n-bootstrap 2000

"""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path


def _load_per_query(path: Path, metric: str, flip_prob: float):
    """Load per-query metric values from noise sensitivity CSV."""
    by_query: dict[str, dict[str, float]] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            fp = float(row.get("flip_prob", -1))
            if abs(fp - flip_prob) > 1e-6:
                continue
            qid = row["query_id"]
            method = row["method"]
            raw = row.get(metric)
            if raw in {"", None, "None"}:
                continue
            by_query.setdefault(qid, {})[method] = float(raw)
    return by_query


def _bootstrap_ci(deltas, n_bootstrap, seed):
    if not deltas:
        return 0.0, 0.0, 0.0
    rng = random.Random(seed)
    n = len(deltas)
    boots = []
    for _ in range(n_bootstrap):
        sample = [deltas[rng.randrange(n)] for _ in range(n)]
        boots.append(sum(sample) / n)
    boots.sort()
    lo_idx = int(0.025 * (n_bootstrap - 1))
    hi_idx = int(0.975 * (n_bootstrap - 1))
    return sum(deltas) / n, boots[lo_idx], boots[hi_idx]


COMPARISONS = [
    ("score_sum", "greedy_fas_topological", "score_sum vs FAS topological"),
    ("score_sum", "bt_aggregation", "score_sum vs Bradley-Terry"),
    ("score_sum", "win_rate_aggregation", "score_sum vs win-rate"),
    ("score_sum", "tournament_sort_aggregation", "score_sum vs tournament sort"),
    ("greedy_fas_weighted_balance", "bt_aggregation", "FAS-balance vs BT"),
    ("greedy_fas_weighted_balance", "win_rate_aggregation", "FAS-balance vs win-rate"),
    ("greedy_fas_weighted_balance", "markov_aggregation", "FAS-balance vs Markov"),
    ("greedy_fas_copeland", "copeland_unrepaired", "FAS-copeland vs unrepaired copeland"),
    ("greedy_fas_copeland", "bt_aggregation", "FAS-copeland vs BT"),
    ("borda", "win_rate_aggregation", "Borda vs win-rate"),
]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Bootstrap CIs for modern baseline comparisons.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--dataset", default="scidocs")
    parser.add_argument("--flip-prob", type=float, default=0.15)
    parser.add_argument("--n-bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--metric", default="ndcg_at_k")
    parser.add_argument(
        "--input-dir", type=Path, default=Path("outputs/noise_sensitivity"),
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("outputs/bootstrap_modern"),
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    input_path = (
        args.input_dir / args.dataset
        / f"{args.dataset}_noise_sensitivity_per_query.csv"
    )
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    output_dir = args.output_dir / args.dataset
    output_dir.mkdir(parents=True, exist_ok=True)

    by_query = _load_per_query(input_path, args.metric, args.flip_prob)
    n_queries = len(by_query)
    print(f"Loaded {n_queries} queries at flip_prob={args.flip_prob}")

    results = []
    for method_a, method_b, label in COMPARISONS:
        qids = []
        deltas = []
        for qid, methods in by_query.items():
            if method_a in methods and method_b in methods:
                qids.append(qid)
                deltas.append(methods[method_a] - methods[method_b])

        if not deltas:
            print(f"  {label}: no paired data")
            continue

        mean_delta, ci_lo, ci_hi = _bootstrap_ci(deltas, args.n_bootstrap, args.seed)
        sig = "***" if ci_lo > 0 else ("***" if ci_hi < 0 else "n.s.")

        results.append({
            "dataset": args.dataset,
            "flip_prob": args.flip_prob,
            "method_a": method_a,
            "method_b": method_b,
            "comparison": label,
            "n_paired": len(deltas),
            "mean_delta": round(mean_delta, 6),
            "ci_lo_95": round(ci_lo, 6),
            "ci_hi_95": round(ci_hi, 6),
            "significant": sig,
        })
        print(
            f"  {label}: "
            f"Δ={mean_delta:+.4f} [{ci_lo:+.4f}, {ci_hi:+.4f}] {sig} "
            f"(n={len(deltas)})"
        )

    csv_path = output_dir / f"{args.dataset}_bootstrap_fp{args.flip_prob:.2f}.csv"
    if results:
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(results[0].keys()))
            writer.writeheader()
            writer.writerows(results)
        print(f"\nCSV → {csv_path}")

    latex_lines = [
        r"\begin{table}[ht]",
        r"\centering",
        (
            rf"\caption{{Bootstrap 95\% CIs for method deltas on "
            rf"{args.dataset.upper()} (flip\_prob={args.flip_prob})}}"
        ),
        rf"\label{{tab:bootstrap_{args.dataset}}}",
        r"\begin{tabular}{lrrrl}",
        r"\toprule",
        r"Comparison & $\Delta$ nDCG & CI low & CI high & Sig. \\",
        r"\midrule",
    ]
    for r in results:
        comp = r["comparison"].replace("_", r"\_")
        sig = r["significant"]
        latex_lines.append(
            f"{comp} & {r['mean_delta']:+.4f} & {r['ci_lo_95']:+.4f} "
            f"& {r['ci_hi_95']:+.4f} & {sig} \\\\"
        )
    latex_lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    latex_path = output_dir / f"{args.dataset}_bootstrap_fp{args.flip_prob:.2f}.tex"
    latex_path.write_text("\n".join(latex_lines), encoding="utf-8")
    print(f"LaTeX → {latex_path}")

    md_lines = [
        f"# Bootstrap CIs — {args.dataset.upper()} (flip_prob={args.flip_prob})\n",
        f"n_bootstrap={args.n_bootstrap}, seed={args.seed}, metric={args.metric}\n",
        "| Comparison | Δ nDCG | CI 95% low | CI 95% high | Sig. | n |",
        "|------------|--------|------------|-------------|------|---|",
    ]
    for r in results:
        md_lines.append(
            f"| {r['comparison']} | {r['mean_delta']:+.4f} "
            f"| {r['ci_lo_95']:+.4f} | {r['ci_hi_95']:+.4f} "
            f"| {r['significant']} | {r['n_paired']} |"
        )
    md_path = output_dir / f"{args.dataset}_bootstrap_fp{args.flip_prob:.2f}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Markdown → {md_path}")

    config = {
        "dataset": args.dataset,
        "flip_prob": args.flip_prob,
        "n_bootstrap": args.n_bootstrap,
        "seed": args.seed,
        "metric": args.metric,
        "n_queries": n_queries,
    }
    config_path = output_dir / f"{args.dataset}_bootstrap_config.json"
    with config_path.open("w") as fh:
        json.dump(config, fh, indent=2)


if __name__ == "__main__":
    main()
