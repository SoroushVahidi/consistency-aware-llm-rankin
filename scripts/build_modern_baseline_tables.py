"""
build_modern_baseline_tables.py
===============================
Build unified comparison tables merging modern baselines with existing
pipeline results.

Reads:
- Modern baseline per-query CSVs from outputs/modern_baselines/
- Existing pipeline summary CSVs from outputs/ (configurable)

Produces:
- Unified comparison CSV tables
- LaTeX table fragments (if existing pipeline uses them)
- Markdown summary for manuscript

Usage
-----
::

    python scripts/build_modern_baseline_tables.py \\
        --modern-dir outputs/modern_baselines \\
        --existing-dir outputs/real_full \\
        --out-dir outputs/modern_baseline_comparison

"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def _load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _safe_float(val):
    if val is None or val == "" or val == "None":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _mean(vals):
    clean = [v for v in vals if v is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def load_modern_results(modern_dir: Path, datasets: list[str]) -> list[dict]:
    """Load modern baseline per-query rows for all datasets."""
    all_rows = []
    for ds in datasets:
        path = modern_dir / ds / f"{ds}_modern_baselines_per_query.csv"
        rows = _load_csv(path)
        all_rows.extend(rows)
    return all_rows


def load_existing_results(existing_dir: Path, datasets: list[str]) -> list[dict]:
    """Load existing pipeline per-query rows for all datasets."""
    all_rows = []
    for ds in datasets:
        for pref_source in ("qrels", "qrels_flip", "votes_file"):
            path = existing_dir / ds / pref_source / f"{ds}_per_query.csv"
            rows = _load_csv(path)
            all_rows.extend(rows)
    return all_rows


def build_unified_summary(
    modern_rows: list[dict],
    existing_rows: list[dict],
    datasets: list[str],
) -> list[dict]:
    """Build a unified per-dataset × per-method summary table."""
    all_rows = modern_rows + existing_rows

    grouped = defaultdict(lambda: defaultdict(list))
    for r in all_rows:
        ds = r.get("dataset", "")
        method = r.get("method", "")
        if ds and method:
            grouped[ds][method].append(r)

    summary = []
    for ds in datasets:
        methods_data = grouped.get(ds, {})
        for method, rows in sorted(methods_data.items()):
            ndcg_vals = [_safe_float(r.get("ndcg_at_k")) for r in rows]
            map_vals = [_safe_float(r.get("map_at_k")) for r in rows]
            prec_vals = [_safe_float(r.get("precision_at_k")) for r in rows]
            recall_vals = [_safe_float(r.get("recall_at_k")) for r in rows]
            bew_vals = [_safe_float(r.get("backward_edge_weight")) for r in rows]

            pref_source = rows[0].get("preference_source", "")

            summary.append({
                "dataset": ds,
                "method": method,
                "preference_source": pref_source,
                "n_queries": len(rows),
                "ndcg_mean": round(_mean(ndcg_vals), 4) if _mean(ndcg_vals) is not None else None,
                "map_mean": round(_mean(map_vals), 4) if _mean(map_vals) is not None else None,
                "precision_mean": (
                    round(_mean(prec_vals), 4) if _mean(prec_vals) is not None else None
                ),
                "recall_mean": (
                    round(_mean(recall_vals), 4) if _mean(recall_vals) is not None else None
                ),
                "bew_mean": round(_mean(bew_vals), 4) if _mean(bew_vals) is not None else None,
            })

    return summary


def write_csv(rows, path):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def generate_latex_table(summary: list[dict], dataset: str) -> str:
    """Generate a LaTeX table fragment for one dataset."""
    rows = [r for r in summary if r["dataset"] == dataset]
    if not rows:
        return ""

    lines = [
        r"\begin{table}[ht]",
        r"\centering",
        rf"\caption{{Comparison of reranking methods on {dataset.upper()}}}",
        rf"\label{{tab:modern_baselines_{dataset}}}",
        r"\begin{tabular}{lcccc}",
        r"\toprule",
        r"Method & nDCG@k & MAP@k & Prec@k & BEW \\",
        r"\midrule",
    ]

    for r in sorted(rows, key=lambda x: -(x["ndcg_mean"] or 0)):
        ndcg = f"{r['ndcg_mean']:.4f}" if r["ndcg_mean"] is not None else "--"
        map_k = f"{r['map_mean']:.4f}" if r["map_mean"] is not None else "--"
        prec = f"{r['precision_mean']:.4f}" if r["precision_mean"] is not None else "--"
        bew = f"{r['bew_mean']:.2f}" if r["bew_mean"] is not None else "--"
        method_display = r["method"].replace("_", r"\_")
        lines.append(rf"{method_display} & {ndcg} & {map_k} & {prec} & {bew} \\")

    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def generate_markdown_summary(summary: list[dict], datasets: list[str]) -> str:
    """Generate a markdown comparison summary."""
    lines = ["# Modern Baseline Comparison Results\n"]

    for ds in datasets:
        rows = [r for r in summary if r["dataset"] == ds]
        if not rows:
            continue

        lines.append(f"\n## {ds.upper()}\n")
        lines.append("| Method | Source | nDCG@k | MAP@k | Prec@k | n |")
        lines.append("|--------|--------|--------|-------|--------|---|")

        for r in sorted(rows, key=lambda x: -(x["ndcg_mean"] or 0)):
            ndcg = f"{r['ndcg_mean']:.4f}" if r["ndcg_mean"] is not None else "—"
            map_k = f"{r['map_mean']:.4f}" if r["map_mean"] is not None else "—"
            prec = f"{r['precision_mean']:.4f}" if r["precision_mean"] is not None else "—"
            n_q = r["n_queries"]
            src = r["preference_source"]
            m = r["method"]
            lines.append(f"| {m} | {src} | {ndcg} | {map_k} | {prec} | {n_q} |")

    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Build unified modern baseline comparison tables.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--modern-dir", type=Path, default=Path("outputs/modern_baselines"),
    )
    parser.add_argument(
        "--existing-dir", type=Path, default=Path("outputs/real_full"),
    )
    parser.add_argument(
        "--out-dir", type=Path, default=Path("outputs/modern_baseline_comparison"),
    )
    parser.add_argument(
        "--datasets", nargs="+", default=["scidocs", "fiqa", "hotpotqa", "bright"],
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading modern baseline results from {args.modern_dir}")
    modern_rows = load_modern_results(args.modern_dir, args.datasets)
    print(f"  Found {len(modern_rows)} modern baseline rows")

    print(f"Loading existing pipeline results from {args.existing_dir}")
    existing_rows = load_existing_results(args.existing_dir, args.datasets)
    print(f"  Found {len(existing_rows)} existing pipeline rows")

    summary = build_unified_summary(modern_rows, existing_rows, args.datasets)

    csv_path = args.out_dir / "unified_comparison.csv"
    write_csv(summary, csv_path)
    print(f"Unified CSV → {csv_path}")

    for ds in args.datasets:
        latex = generate_latex_table(summary, ds)
        if latex:
            latex_path = args.out_dir / f"table_{ds}.tex"
            latex_path.write_text(latex, encoding="utf-8")
            print(f"LaTeX table → {latex_path}")

    md = generate_markdown_summary(summary, args.datasets)
    md_path = args.out_dir / "COMPARISON_SUMMARY.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"Markdown summary → {md_path}")


if __name__ == "__main__":
    main()
