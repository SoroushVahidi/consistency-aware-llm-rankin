"""
run_bootstrap.py
================

Run paired bootstrap significance testing over per-query experiment outputs.

The script loads one or more ``*_per_query.csv`` files produced by
``scripts/run_real_experiment.py``, identifies the strongest non-hybrid FAS
method and the strongest hybrid method for each dataset, and compares them
against ``score_sum`` and ``borda`` using paired bootstrap resampling.

Outputs are written to ``docs/tables/bootstrap_results.csv`` by default.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_OUTPUT = Path("docs/tables/bootstrap_results.csv")
DEFAULT_METRICS = ("ndcg", "kendall_tau", "pairwise_accuracy")
METRIC_ALIASES = {
    "ndcg": "ndcg_at_k",
    "ndcg_at_k": "ndcg_at_k",
    "kendall_tau": "kendall_tau",
    "pairwise_accuracy": "pairwise_accuracy",
}
BASELINE_METHODS = ("score_sum", "borda")


@dataclass(frozen=True)
class BootstrapResult:
    dataset: str
    preference_source: str | None
    method_a: str
    method_b: str
    metric: str
    mean_diff: float
    ci_lower: float
    ci_upper: float
    p_value: float
    significant: bool
    n_queries: int


@dataclass(frozen=True)
class ValidatedRun:
    dataset: str
    path: Path
    rows: list[dict[str, str]]
    preference_source: str | None
    warnings: tuple[str, ...]


def _warn(message: str) -> None:
    print(f"[run_bootstrap] WARNING: {message}", file=sys.stderr)


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = q * (len(sorted_values) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return sorted_values[lo]
    weight = pos - lo
    return sorted_values[lo] * (1.0 - weight) + sorted_values[hi] * weight


def _canonical_metric(metric: str) -> str:
    try:
        return METRIC_ALIASES[metric]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported metric '{metric}'. Supported metrics: {sorted(METRIC_ALIASES)}"
        ) from exc


def _discover_inputs(paths: list[Path] | None) -> list[Path]:
    if paths:
        return sorted(dict.fromkeys(p.resolve() for p in paths))
    return sorted(Path("outputs").glob("**/*_per_query.csv"))


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader)


def _load_summary_json(path: Path) -> dict | None:
    summary_path = path.with_name(path.name.replace("_per_query.csv", "_experiment_summary.json"))
    if not summary_path.exists():
        return None
    return json.loads(summary_path.read_text(encoding="utf-8"))


def _validate_run(path: Path) -> ValidatedRun | None:
    rows = _load_csv_rows(path)
    if not rows:
        _warn(f"Skipping empty per-query file: {path}")
        return None

    required = {"dataset", "query_id", "method"}
    missing = required - set(rows[0])
    if missing:
        _warn(f"Skipping {path}: missing required columns {sorted(missing)}")
        return None

    datasets = {row.get("dataset", "").strip() for row in rows if row.get("dataset", "").strip()}
    dataset = next(iter(datasets), path.stem.replace("_per_query", ""))
    if len(datasets) > 1:
        _warn(f"Skipping {path}: multiple datasets detected {sorted(datasets)}")
        return None

    warnings: list[str] = []
    preference_source = None
    if "preference_source" in rows[0]:
        sources = {
            row.get("preference_source", "").strip()
            for row in rows
            if row.get("preference_source", "").strip()
        }
        if len(sources) > 1:
            _warn(
                f"Skipping {path}: mixed preference_source values detected {sorted(sources)}; "
                "comparisons would be invalid."
            )
            return None
        preference_source = next(iter(sources), None)

    summary = _load_summary_json(path)
    if summary is not None:
        summary_source = summary.get("preference_source")
        if preference_source and summary_source and summary_source != preference_source:
            _warn(
                f"Skipping {path}: per-query source '{preference_source}' disagrees with "
                f"experiment summary source '{summary_source}'."
            )
            return None
        if summary_source == "qrels_flip" and "qrels_flip" not in path.as_posix():
            warnings.append(
                "Detected qrels_flip results stored in a source-agnostic file name; "
                "this suggests earlier qrels outputs may have been overwritten."
            )

    return ValidatedRun(
        dataset=dataset,
        path=path,
        rows=rows,
        preference_source=preference_source,
        warnings=tuple(warnings),
    )


def _extract_metric_values(
    rows: list[dict[str, str]],
    metric: str,
) -> dict[str, dict[str, float]]:
    by_query: dict[str, dict[str, float]] = {}
    for row in rows:
        raw = row.get(metric)
        if raw in {None, ""}:
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        by_query.setdefault(row["query_id"], {})[row["method"]] = value
    return by_query


def _method_means(by_query: dict[str, dict[str, float]]) -> dict[str, float]:
    acc: dict[str, list[float]] = {}
    for query_metrics in by_query.values():
        for method, value in query_metrics.items():
            acc.setdefault(method, []).append(value)
    return {method: _mean(values) for method, values in acc.items() if values}


def _pick_best_method(method_means: dict[str, float], prefix: str | None) -> str | None:
    candidates = [
        method
        for method in method_means
        if (method.startswith(prefix) if prefix is not None else True)
    ]
    if prefix is None:
        raise ValueError("prefix must be provided")
    if prefix == "greedy_fas_":
        candidates = [m for m in candidates if not m.startswith("hybrid_")]
    if not candidates:
        return None
    return sorted(candidates, key=lambda method: (-method_means[method], method))[0]


def _paired_differences(
    by_query: dict[str, dict[str, float]],
    method_a: str,
    method_b: str,
) -> list[float]:
    diffs: list[float] = []
    for method_values in by_query.values():
        if method_a not in method_values or method_b not in method_values:
            continue
        diffs.append(method_values[method_a] - method_values[method_b])
    return diffs


def _bootstrap_summary(
    deltas: list[float],
    n_bootstrap: int,
    seed: int,
) -> tuple[float, float, float, float]:
    if not deltas:
        return 0.0, 0.0, 0.0, 1.0
    rng = random.Random(seed)
    n = len(deltas)
    observed = _mean(deltas)
    bootstrap_means: list[float] = []
    for _ in range(n_bootstrap):
        sample = [deltas[rng.randrange(n)] for _ in range(n)]
        bootstrap_means.append(_mean(sample))
    bootstrap_means.sort()
    ci_low = _quantile(bootstrap_means, 0.025)
    ci_high = _quantile(bootstrap_means, 0.975)
    p_left = sum(1 for value in bootstrap_means if value <= 0.0) / n_bootstrap
    p_right = sum(1 for value in bootstrap_means if value >= 0.0) / n_bootstrap
    p_value = min(1.0, 2.0 * min(p_left, p_right))
    return observed, ci_low, ci_high, p_value


def _run_bootstrap_for_file(
    validated: ValidatedRun,
    metrics: list[str],
    n_bootstrap: int,
    seed: int,
) -> list[BootstrapResult]:
    results: list[BootstrapResult] = []
    for metric_name in metrics:
        metric = _canonical_metric(metric_name)
        by_query = _extract_metric_values(validated.rows, metric=metric)
        if not by_query:
            _warn(f"Skipping metric '{metric_name}' for {validated.path}: no usable values found")
            continue

        method_means = _method_means(by_query)
        best_fas = _pick_best_method(method_means, prefix="greedy_fas_")
        best_hybrid = _pick_best_method(method_means, prefix="hybrid_")
        comparisons = [
            (best_fas, "score_sum"),
            (best_fas, "borda"),
            (best_hybrid, "score_sum"),
            (best_hybrid, "borda"),
        ]
        seen_pairs: set[tuple[str, str, str]] = set()
        for method_a, method_b in comparisons:
            if method_a is None:
                continue
            if method_b not in method_means:
                _warn(
                    f"Skipping comparison for {validated.dataset} ({metric_name}): "
                    f"baseline method '{method_b}' is missing"
                )
                continue
            dedupe_key = (metric_name, method_a, method_b)
            if dedupe_key in seen_pairs:
                continue
            seen_pairs.add(dedupe_key)
            deltas = _paired_differences(by_query, method_a=method_a, method_b=method_b)
            if not deltas:
                _warn(
                    f"Skipping comparison for {validated.dataset} ({metric_name}): "
                    f"no paired queries for {method_a} vs {method_b}"
                )
                continue
            mean_diff, ci_low, ci_high, p_value = _bootstrap_summary(
                deltas,
                n_bootstrap=n_bootstrap,
                seed=seed,
            )
            results.append(
                BootstrapResult(
                    dataset=validated.dataset,
                    preference_source=validated.preference_source,
                    method_a=method_a,
                    method_b=method_b,
                    metric=metric_name,
                    mean_diff=mean_diff,
                    ci_lower=ci_low,
                    ci_upper=ci_high,
                    p_value=p_value,
                    significant=(ci_low > 0.0) or (ci_high < 0.0),
                    n_queries=len(deltas),
                )
            )
    return results


def _write_results(path: Path, results: list[BootstrapResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "dataset",
        "preference_source",
        "method_a",
        "method_b",
        "metric",
        "mean_diff",
        "ci_lower",
        "ci_upper",
        "p_value",
        "significant",
        "n_queries",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "dataset": result.dataset,
                    "preference_source": result.preference_source or "",
                    "method_a": result.method_a,
                    "method_b": result.method_b,
                    "metric": result.metric,
                    "mean_diff": f"{result.mean_diff:.6f}",
                    "ci_lower": f"{result.ci_lower:.6f}",
                    "ci_upper": f"{result.ci_upper:.6f}",
                    "p_value": f"{result.p_value:.6f}",
                    "significant": str(result.significant),
                    "n_queries": result.n_queries,
                }
            )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run paired bootstrap significance testing over per-query outputs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input",
        type=Path,
        nargs="+",
        help=(
            "One or more *_per_query.csv files. If omitted, scan "
            "outputs/** for per-query files."
        ),
    )
    parser.add_argument(
        "--metrics",
        nargs="+",
        default=list(DEFAULT_METRICS),
        help="Metrics to evaluate. Supported: ndcg, kendall_tau, pairwise_accuracy.",
    )
    parser.add_argument("--n-bootstrap", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--preference-source",
        nargs="*",
        default=None,
        help="Optional preference_source value(s) to keep when scanning multiple inputs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> list[BootstrapResult]:
    args = parse_args(argv)
    inputs = _discover_inputs(args.input)
    if not inputs:
        raise SystemExit("No *_per_query.csv inputs found.")

    validated_runs: list[ValidatedRun] = []
    source_filter = set(args.preference_source or [])
    for path in inputs:
        validated = _validate_run(path)
        if validated is None:
            continue
        if source_filter and validated.preference_source not in source_filter:
            continue
        for message in validated.warnings:
            _warn(f"{validated.path}: {message}")
        validated_runs.append(validated)

    if not validated_runs:
        raise SystemExit("No valid per-query inputs remained after validation.")

    all_results: list[BootstrapResult] = []
    for validated in validated_runs:
        all_results.extend(
            _run_bootstrap_for_file(
                validated,
                metrics=args.metrics,
                n_bootstrap=args.n_bootstrap,
                seed=args.seed,
            )
        )

    all_results.sort(key=lambda row: (row.dataset, row.metric, row.method_b, row.method_a))
    _write_results(args.output, all_results)
    print(f"[run_bootstrap] inputs={len(validated_runs)}")
    print(f"[run_bootstrap] rows={len(all_results)}")
    print(f"[run_bootstrap] output={args.output}")
    return all_results


if __name__ == "__main__":
    main()
