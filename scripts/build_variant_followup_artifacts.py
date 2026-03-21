#!/usr/bin/env python
"""Build tables and figures for the repaired-graph variant follow-up study."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = REPO_ROOT / "outputs"
TABLES = REPO_ROOT / "docs" / "tables"
FIGURES = REPO_ROOT / "docs" / "figures"

METHODS = [
    "score_sum",
    "borda",
    "greedy_fas_topological",
    "priority_topological_score_sum",
    "fas_weighted_balance",
    "fas_copeland",
    "hybrid_rrf_fas_regularized",
]

METHOD_LABELS = {
    "score_sum": "score_sum",
    "borda": "borda",
    "greedy_fas_topological": "greedy_fas_topological",
    "priority_topological_score_sum": "priority_topological_score_sum",
    "fas_weighted_balance": "fas_weighted_balance",
    "fas_copeland": "fas_copeland",
    "hybrid_rrf_fas_regularized": "hybrid_rrf_fas_regularized",
}

FAMILY_ORDER = {
    "noise_sweep_variant_followup": 0,
    "variant_multiseed_n20_noise0.20": 1,
}


def _load_run(path: Path, family: str, regime_id: str) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    config = data["config"]
    tau = data["evaluation"]["kendall_tau"]
    violations = data["evaluation"]["n_violations"]
    incons = data["evaluation"]["pairwise_inconsistency_count"]
    fas = data["fas"]
    timings = data["timings"]
    total_runtime = timings["total_experiment"]["total_s"]
    repair_runtime = timings["greedy_fas_solver"]["total_s"]

    rows: list[dict] = []
    for method in METHODS:
        rows.append(
            {
                "experiment_family": family,
                "regime_id": regime_id,
                "seed": int(config["seed"]),
                "noise": float(config["noise"]),
                "n_items": int(config["n_items"]),
                "weight_scheme": config["weight_scheme"],
                "method": method,
                "kendall_tau": float(tau[method]),
                "n_violations": int(violations[method]),
                "pairwise_inconsistency_before": int(incons["original_graph"]),
                "pairwise_inconsistency_after": int(incons["after_fas_dag"]),
                "fas_removed_edges": int(fas["n_removed_edges"]),
                "fas_removed_weight": float(fas["total_removed_weight"]),
                "runtime_total_s": float(total_runtime),
                "runtime_repair_s": float(repair_runtime),
                "result_path": str(path.relative_to(REPO_ROOT)),
            }
        )
    return rows


def _discover_rows() -> list[dict]:
    rows: list[dict] = []
    for path in sorted((OUTPUTS / "noise_sweep_variant_followup").glob("noise_*/synthetic_results.json")):
        noise_token = path.parent.name.split("_", 1)[1]
        rows.extend(_load_run(path, "noise_sweep_variant_followup", f"noise={noise_token}"))
    for path in sorted(
        (OUTPUTS / "variant_multiseed_n20_noise0.20").glob("seed_*/synthetic_results.json")
    ):
        seed_token = path.parent.name.split("_", 1)[1]
        rows.extend(
            _load_run(
                path,
                "variant_multiseed_n20_noise0.20",
                f"noise=0.20|seed={seed_token}",
            )
        )
    rows.sort(
        key=lambda row: (
            FAMILY_ORDER[row["experiment_family"]],
            row["noise"],
            row["seed"],
            METHODS.index(row["method"]),
        )
    )
    return rows


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _group(rows: list[dict], *keys: str) -> dict[tuple, list[dict]]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    return groups


def _summary_rows(rows: list[dict]) -> list[dict]:
    summaries: list[dict] = []
    grouped = _group(rows, "experiment_family", "noise", "n_items", "method")
    per_regime_scores = _group(rows, "experiment_family", "noise", "n_items", "seed")
    regime_best: dict[tuple, tuple[str, float]] = {}
    for regime_key, regime_rows in per_regime_scores.items():
        best_row = max(regime_rows, key=lambda row: row["kendall_tau"])
        regime_best[regime_key] = (best_row["method"], best_row["kendall_tau"])

    for (family, noise, n_items, method), subset in sorted(grouped.items()):
        borda_subset = [
            row["kendall_tau"]
            for row in rows
            if row["experiment_family"] == family
            and row["noise"] == noise
            and row["n_items"] == n_items
            and row["method"] == "borda"
        ]
        score_sum_subset = [
            row["kendall_tau"]
            for row in rows
            if row["experiment_family"] == family
            and row["noise"] == noise
            and row["n_items"] == n_items
            and row["method"] == "score_sum"
        ]
        best_methods = [
            regime_best[(family, noise, n_items, row["seed"])][0]
            for row in subset
        ]
        summaries.append(
            {
                "experiment_family": family,
                "noise": noise,
                "n_items": n_items,
                "method": method,
                "n_runs": len(subset),
                "mean_tau": mean(row["kendall_tau"] for row in subset),
                "std_tau": pstdev(row["kendall_tau"] for row in subset)
                if len(subset) > 1
                else 0.0,
                "mean_n_violations": mean(row["n_violations"] for row in subset),
                "mean_pairwise_inconsistency_before": mean(
                    row["pairwise_inconsistency_before"] for row in subset
                ),
                "mean_pairwise_inconsistency_after": mean(
                    row["pairwise_inconsistency_after"] for row in subset
                ),
                "mean_fas_removed_edges": mean(row["fas_removed_edges"] for row in subset),
                "mean_fas_removed_weight": mean(row["fas_removed_weight"] for row in subset),
                "mean_runtime_total_s": mean(row["runtime_total_s"] for row in subset),
                "mean_runtime_repair_s": mean(row["runtime_repair_s"] for row in subset),
                "best_method_by_regime": max(set(best_methods), key=best_methods.count),
                "gap_to_borda": mean(row["kendall_tau"] for row in subset) - mean(borda_subset),
                "gap_to_score_sum": mean(row["kendall_tau"] for row in subset)
                - mean(score_sum_subset),
            }
        )
    summaries.sort(
        key=lambda row: (
            FAMILY_ORDER[row["experiment_family"]],
            row["noise"],
            METHODS.index(row["method"]),
        )
    )
    return summaries


def _win_count_rows(rows: list[dict]) -> list[dict]:
    grouped = _group(rows, "experiment_family", "noise", "n_items", "method")
    per_run = _group(rows, "experiment_family", "noise", "n_items", "seed")
    run_best: dict[tuple, float] = {}
    run_method_scores: dict[tuple, dict[str, float]] = {}
    for key, subset in per_run.items():
        run_best[key] = max(row["kendall_tau"] for row in subset)
        run_method_scores[key] = {row["method"]: row["kendall_tau"] for row in subset}

    out: list[dict] = []
    for (family, noise, n_items, method), subset in sorted(grouped.items()):
        wins = 0
        beats_borda = 0
        beats_score_sum = 0
        for row in subset:
            run_key = (family, noise, n_items, row["seed"])
            if row["kendall_tau"] >= run_best[run_key] - 1.0e-12:
                wins += 1
            if row["kendall_tau"] > run_method_scores[run_key]["borda"]:
                beats_borda += 1
            if row["kendall_tau"] > run_method_scores[run_key]["score_sum"]:
                beats_score_sum += 1
        out.append(
            {
                "experiment_family": family,
                "noise": noise,
                "n_items": n_items,
                "method": method,
                "n_runs": len(subset),
                "n_wins": wins,
                "n_beats_borda": beats_borda,
                "n_beats_score_sum": beats_score_sum,
            }
        )
    out.sort(
        key=lambda row: (
            FAMILY_ORDER[row["experiment_family"]],
            row["noise"],
            METHODS.index(row["method"]),
        )
    )
    return out


def _plot_noise_sweep(rows: list[dict]) -> None:
    noise_rows = [row for row in rows if row["experiment_family"] == "noise_sweep_variant_followup"]
    grouped = _group(noise_rows, "noise", "method")
    noises = sorted({row["noise"] for row in noise_rows})
    plt.figure(figsize=(9, 5))
    for method in METHODS:
        ys = [mean(row["kendall_tau"] for row in grouped[(noise, method)]) for noise in noises]
        plt.plot(noises, ys, marker="o", label=METHOD_LABELS[method])
    plt.xlabel("Noise")
    plt.ylabel("Kendall tau")
    plt.title("Synthetic follow-up: Kendall tau vs noise")
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8, ncol=2)
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(FIGURES / "variant_followup_kendall_tau_vs_noise.png", dpi=200)
    plt.close()


def _plot_multiseed(rows: list[dict]) -> None:
    multi_rows = [row for row in rows if row["experiment_family"] == "variant_multiseed_n20_noise0.20"]
    grouped = _group(multi_rows, "method")
    data = [sorted(row["kendall_tau"] for row in grouped[(method,)]) for method in METHODS]
    plt.figure(figsize=(10, 5))
    plt.boxplot(data, tick_labels=[METHOD_LABELS[m] for m in METHODS], patch_artist=True)
    plt.ylabel("Kendall tau")
    plt.title("5-seed robustness check at n_items=20, noise=0.20")
    plt.xticks(rotation=20, ha="right")
    plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIGURES / "variant_followup_multiseed_boxplot.png", dpi=200)
    plt.close()


def _plot_gap(rows: list[dict], baseline: str, filename: str, title: str) -> None:
    noise_rows = [row for row in rows if row["experiment_family"] == "noise_sweep_variant_followup"]
    grouped = _group(noise_rows, "noise", "method")
    noises = sorted({row["noise"] for row in noise_rows})
    plt.figure(figsize=(9, 5))
    for method in METHODS:
        if method == baseline:
            continue
        ys = []
        for noise in noises:
            method_mean = mean(row["kendall_tau"] for row in grouped[(noise, method)])
            baseline_mean = mean(row["kendall_tau"] for row in grouped[(noise, baseline)])
            ys.append(method_mean - baseline_mean)
        plt.plot(noises, ys, marker="o", label=METHOD_LABELS[method])
    plt.axhline(0.0, color="black", linewidth=1, linestyle="--")
    plt.xlabel("Noise")
    plt.ylabel(f"Kendall tau gap vs {baseline}")
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8, ncol=2)
    plt.tight_layout()
    plt.savefig(FIGURES / filename, dpi=200)
    plt.close()


def main() -> None:
    rows = _discover_rows()
    if not rows:
        raise SystemExit("No variant follow-up outputs found.")
    TABLES.mkdir(parents=True, exist_ok=True)
    _write_csv(TABLES / "variant_followup_main_results.csv", rows)
    _write_csv(TABLES / "variant_followup_summary.csv", _summary_rows(rows))
    _write_csv(TABLES / "variant_followup_win_counts.csv", _win_count_rows(rows))
    _plot_noise_sweep(rows)
    _plot_multiseed(rows)
    _plot_gap(
        rows,
        baseline="borda",
        filename="variant_followup_gap_to_borda.png",
        title="Synthetic follow-up: Kendall tau gap to borda",
    )
    _plot_gap(
        rows,
        baseline="score_sum",
        filename="variant_followup_gap_to_score_sum.png",
        title="Synthetic follow-up: Kendall tau gap to score_sum",
    )


if __name__ == "__main__":
    main()
