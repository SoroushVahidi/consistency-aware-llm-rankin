"""Build clean proxy comparison tables from source-separated real-data outputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _load_summary_rows(outputs_root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(outputs_root.glob("*/*/*_summary.csv")):
        dataset = path.parent.parent.name
        preference_source = path.parent.name
        for row in _read_csv(path):
            row["dataset"] = dataset
            row["preference_source"] = preference_source
            rows.append(row)
    return rows


def _load_bootstrap_rows(*paths: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        if path.exists():
            rows.extend(_read_csv(path))
    return rows


def _best_row(
    rows: list[dict[str, str]],
    metric_col: str,
    prefix: str | None = None,
) -> dict[str, str] | None:
    filtered = rows
    if prefix is not None:
        filtered = [row for row in rows if row["method"].startswith(prefix)]
    if not filtered:
        return None
    return sorted(filtered, key=lambda row: (-float(row[metric_col]), row["method"]))[0]


def _bootstrap_lookup(
    rows: list[dict[str, str]],
) -> dict[tuple[str, str, str, str], dict[str, str]]:
    lookup: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in rows:
        key = (
            row["dataset"],
            row.get("preference_source", ""),
            row["method_a"],
            row["method_b"],
        )
        if row["metric"] == "ndcg":
            lookup[key] = row
    return lookup


def _format_bootstrap(row: dict[str, str] | None) -> str:
    if row is None:
        return "missing"
    direction = "positive" if float(row["mean_diff"]) > 0 else "negative"
    sig = "significant" if row["significant"] == "True" else "not_significant"
    return (
        f"{sig}_{direction};mean={row['mean_diff']};"
        f"ci=[{row['ci_lower']},{row['ci_upper']}];p={row['p_value']}"
    )


def build_tables(
    outputs_root: Path,
    bootstrap_qrels: Path,
    bootstrap_qrels_flip: Path,
    comparison_output: Path,
    combined_bootstrap_output: Path | None,
) -> None:
    summary_rows = _load_summary_rows(outputs_root)
    bootstrap_rows = _load_bootstrap_rows(bootstrap_qrels, bootstrap_qrels_flip)
    bootstrap_by_key = _bootstrap_lookup(bootstrap_rows)

    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in summary_rows:
        grouped.setdefault((row["dataset"], row["preference_source"]), []).append(row)

    comparison_rows: list[dict[str, str]] = []
    for (dataset, preference_source), rows in sorted(grouped.items()):
        best_ndcg = _best_row(rows, "ndcg_mean")
        best_tau = _best_row(rows, "tau_mean")
        best_fas = _best_row(rows, "ndcg_mean", prefix="greedy_fas_")
        if best_ndcg is None or best_tau is None or best_fas is None:
            continue
        key_score_sum = (dataset, preference_source, best_fas["method"], "score_sum")
        key_borda = (dataset, preference_source, best_fas["method"], "borda")
        gap_fas_to_best = float(best_fas["ndcg_mean"]) - float(best_ndcg["ndcg_mean"])
        comparison_rows.append(
            {
                "dataset": dataset,
                "preference_source": preference_source,
                "best_method_ndcg": best_ndcg["method"],
                "best_method_tau": best_tau["method"],
                "best_FAS_method_ndcg": best_fas["method"],
                "gap_FAS_to_best_ndcg": f"{gap_fas_to_best:.6f}",
                "bootstrap_result_vs_score_sum": _format_bootstrap(
                    bootstrap_by_key.get(key_score_sum)
                ),
                "bootstrap_result_vs_borda": _format_bootstrap(bootstrap_by_key.get(key_borda)),
            }
        )

    comparison_output.parent.mkdir(parents=True, exist_ok=True)
    with comparison_output.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "dataset",
                "preference_source",
                "best_method_ndcg",
                "best_method_tau",
                "best_FAS_method_ndcg",
                "gap_FAS_to_best_ndcg",
                "bootstrap_result_vs_score_sum",
                "bootstrap_result_vs_borda",
            ],
        )
        writer.writeheader()
        writer.writerows(comparison_rows)

    if combined_bootstrap_output is not None:
        combined_bootstrap_output.parent.mkdir(parents=True, exist_ok=True)
        with combined_bootstrap_output.open("w", encoding="utf-8", newline="") as fh:
            if bootstrap_rows:
                writer = csv.DictWriter(fh, fieldnames=list(bootstrap_rows[0].keys()))
                writer.writeheader()
                writer.writerows(bootstrap_rows)



def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build clean proxy comparison tables from separated qrels/qrels_flip outputs.",
    )
    parser.add_argument("--outputs-root", type=Path, default=Path("outputs/real_small_validation"))
    parser.add_argument(
        "--bootstrap-qrels",
        type=Path,
        default=Path("docs/tables/bootstrap_results_qrels.csv"),
    )
    parser.add_argument(
        "--bootstrap-qrels-flip",
        type=Path,
        default=Path("docs/tables/bootstrap_results_qrels_flip.csv"),
    )
    parser.add_argument(
        "--comparison-output",
        type=Path,
        default=Path("docs/tables/proxy_real_clean_comparison.csv"),
    )
    parser.add_argument(
        "--combined-bootstrap-output",
        type=Path,
        default=Path("docs/tables/bootstrap_results_combined_summary.csv"),
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    build_tables(
        outputs_root=args.outputs_root,
        bootstrap_qrels=args.bootstrap_qrels,
        bootstrap_qrels_flip=args.bootstrap_qrels_flip,
        comparison_output=args.comparison_output,
        combined_bootstrap_output=args.combined_bootstrap_output,
    )
