"""
run_diagnostic_experiments.py
=============================
Focused diagnostics for understanding why score_sum / borda outperform FAS
pipelines on current synthetic settings.

Outputs:
- docs/tables/diagnostic_method_properties.csv
- docs/tables/diagnostic_regime_breakdown.csv
- docs/tables/diagnostic_run_level.csv
- docs/figures/diagnostic_gap_vs_noise.png
- docs/figures/diagnostic_agreement_vs_tau.png
- docs/figures/diagnostic_topo_ambiguity.png
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

# Allow running as `python scripts/run_diagnostic_experiments.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from consistency_ranker.baseline_ranking import (  # noqa: E402
    borda_ranking,
    copeland_ranking,
    priority_topological_ranking,
    score_sum_ranking,
    topological_ranking,
    weighted_out_minus_in_ranking,
)
from consistency_ranker.evaluation import kendall_tau  # noqa: E402
from consistency_ranker.graph_construction import build_graph  # noqa: E402
from consistency_ranker.greedy_fas import greedy_fas, greedy_fas_total_weight  # noqa: E402
from consistency_ranker.pairwise_prefs import generate_preferences  # noqa: E402
from consistency_ranker.synthetic_data import (  # noqa: E402
    generate_items,
    ground_truth_ranking,
    quality_map,
)


def _parse_float_csv(raw: str) -> list[float]:
    vals: list[float] = []
    for tok in raw.split(","):
        t = tok.strip()
        if not t:
            continue
        vals.append(float(t))
    return vals


def _parse_int_csv(raw: str) -> list[int]:
    vals: list[int] = []
    for tok in raw.split(","):
        t = tok.strip()
        if not t:
            continue
        vals.append(int(t))
    return vals


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _weighted_edge_agreement(graph: nx.DiGraph, ranking: list[str]) -> tuple[float, float]:
    pos = {n: i for i, n in enumerate(ranking)}
    total_w = 0.0
    agree_w = 0.0
    total_n = 0
    agree_n = 0
    for u, v, data in graph.edges(data=True):
        w = float(data.get("weight", 1.0))
        total_w += w
        total_n += 1
        if pos[u] < pos[v]:
            agree_w += w
            agree_n += 1
    w_agree = (agree_w / total_w) if total_w > 0 else 0.0
    uw_agree = (agree_n / total_n) if total_n > 0 else 0.0
    return w_agree, uw_agree


def _score_sum_priority(graph: nx.DiGraph) -> dict[str, float]:
    pri = {n: 0.0 for n in graph.nodes()}
    for u, _, data in graph.edges(data=True):
        pri[u] += float(data.get("weight", 1.0))
    return pri


def _dag_ambiguity_metrics(dag: nx.DiGraph) -> dict[str, float]:
    n = dag.number_of_nodes()
    total_pairs = n * (n - 1) // 2

    tc = nx.transitive_closure_dag(dag)
    nodes = list(dag.nodes())
    incomparable = 0
    for i in range(n):
        a = nodes[i]
        for j in range(i + 1, n):
            b = nodes[j]
            if not tc.has_edge(a, b) and not tc.has_edge(b, a):
                incomparable += 1
    incomparable_ratio = (incomparable / total_pairs) if total_pairs > 0 else 0.0

    in_deg = {node: dag.in_degree(node) for node in dag.nodes()}
    available = [node for node, d in in_deg.items() if d == 0]
    k_values: list[int] = []
    multi_steps = 0
    processed = 0
    while available:
        k = len(available)
        k_values.append(k)
        if k > 1:
            multi_steps += 1
        best = min(available)
        available.remove(best)
        processed += 1
        for child in dag.successors(best):
            in_deg[child] -= 1
            if in_deg[child] == 0:
                available.append(child)
    if processed != n:
        raise RuntimeError("DAG ambiguity computation failed to process all nodes.")

    mean_available = (sum(k_values) / len(k_values)) if k_values else 0.0
    max_available = max(k_values) if k_values else 0
    mean_log2_choices = (
        sum(math.log2(max(k, 1)) for k in k_values) / len(k_values) if k_values else 0.0
    )
    multi_step_ratio = (multi_steps / len(k_values)) if k_values else 0.0

    return {
        "topo_incomparable_ratio": incomparable_ratio,
        "topo_mean_available_sources": mean_available,
        "topo_max_available_sources": float(max_available),
        "topo_mean_log2_choices": mean_log2_choices,
        "topo_multi_source_step_ratio": multi_step_ratio,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run synthetic diagnostics for FAS vs baselines.")
    p.add_argument("--n-items", type=int, default=20)
    p.add_argument("--noise-values", type=str, default="0.05,0.10,0.15,0.20,0.25,0.30")
    p.add_argument("--seeds", type=str, default="42,123,456,789,1234")
    p.add_argument("--weight-scheme", choices=["uniform", "margin"], default="margin")
    p.add_argument("--tables-dir", type=Path, default=Path("docs/tables"))
    p.add_argument("--figures-dir", type=Path, default=Path("docs/figures"))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    noise_values = _parse_float_csv(args.noise_values)
    seeds = _parse_int_csv(args.seeds)
    if not noise_values:
        raise ValueError("No noise values provided.")
    if not seeds:
        raise ValueError("No seeds provided.")

    methods = [
        "score_sum",
        "borda",
        "score_sum_repaired_dag",
        "borda_repaired_dag",
        "greedy_fas_topological",
        "priority_topological_score_sum",
        "fas_weighted_balance",
        "fas_copeland",
    ]

    run_rows: list[dict] = []
    method_rows: list[dict] = []

    for noise in noise_values:
        for seed in seeds:
            items = generate_items(n=args.n_items, seed=seed)
            qmap = quality_map(items)
            gt = ground_truth_ranking(items)
            prefs = generate_preferences(
                qmap,
                noise=noise,
                weight_scheme=args.weight_scheme,
                seed=seed,
            )
            graph = build_graph(prefs)
            dag, removed_edges = greedy_fas(graph)
            removed_weight = greedy_fas_total_weight(removed_edges)

            pri = _score_sum_priority(graph)

            rankings = {
                "score_sum": score_sum_ranking(graph),
                "borda": borda_ranking(graph),
                "score_sum_repaired_dag": score_sum_ranking(dag),
                "borda_repaired_dag": borda_ranking(dag),
                "greedy_fas_topological": topological_ranking(dag),
                "priority_topological_score_sum": priority_topological_ranking(dag, pri),
                "fas_weighted_balance": weighted_out_minus_in_ranking(dag),
                "fas_copeland": copeland_ranking(dag),
            }

            ambiguity = _dag_ambiguity_metrics(dag)
            base_score_sum = rankings["score_sum"]
            base_borda = rankings["borda"]

            regime_method_tau: dict[str, float] = {}
            for method, ranking in rankings.items():
                tau_truth = kendall_tau(ranking, gt)
                tau_to_ss = kendall_tau(ranking, base_score_sum)
                tau_to_borda = kendall_tau(ranking, base_borda)
                w_agree_orig, uw_agree_orig = _weighted_edge_agreement(graph, ranking)
                w_agree_dag, uw_agree_dag = _weighted_edge_agreement(dag, ranking)

                row = {
                    "seed": seed,
                    "noise": round(noise, 4),
                    "n_items": args.n_items,
                    "method": method,
                    "kendall_tau": round(tau_truth, 6),
                    "tau_to_score_sum": round(tau_to_ss, 6),
                    "tau_to_borda": round(tau_to_borda, 6),
                    "weighted_agreement_original": round(w_agree_orig, 6),
                    "unweighted_agreement_original": round(uw_agree_orig, 6),
                    "weighted_agreement_repaired_dag": round(w_agree_dag, 6),
                    "unweighted_agreement_repaired_dag": round(uw_agree_dag, 6),
                    "removed_edges": len(removed_edges),
                    "removed_weight": round(removed_weight, 6),
                    "topo_incomparable_ratio": round(ambiguity["topo_incomparable_ratio"], 6),
                    "topo_mean_available_sources": round(
                        ambiguity["topo_mean_available_sources"], 6
                    ),
                    "topo_max_available_sources": round(ambiguity["topo_max_available_sources"], 6),
                    "topo_mean_log2_choices": round(ambiguity["topo_mean_log2_choices"], 6),
                    "topo_multi_source_step_ratio": round(
                        ambiguity["topo_multi_source_step_ratio"], 6
                    ),
                }
                method_rows.append(row)
                regime_method_tau[method] = tau_truth

            run_rows.append(
                {
                    "seed": seed,
                    "noise": round(noise, 4),
                    "n_items": args.n_items,
                    "removed_edges": len(removed_edges),
                    "removed_weight": round(removed_weight, 6),
                    "topo_incomparable_ratio": round(ambiguity["topo_incomparable_ratio"], 6),
                    "topo_mean_available_sources": round(
                        ambiguity["topo_mean_available_sources"], 6
                    ),
                    "topo_max_available_sources": round(ambiguity["topo_max_available_sources"], 6),
                    "topo_mean_log2_choices": round(ambiguity["topo_mean_log2_choices"], 6),
                    "topo_multi_source_step_ratio": round(
                        ambiguity["topo_multi_source_step_ratio"], 6
                    ),
                    "tau_score_sum": round(regime_method_tau["score_sum"], 6),
                    "tau_borda": round(regime_method_tau["borda"], 6),
                    "tau_score_sum_repaired_dag": round(
                        regime_method_tau["score_sum_repaired_dag"], 6
                    ),
                    "tau_greedy_fas_topological": round(
                        regime_method_tau["greedy_fas_topological"], 6
                    ),
                    "tau_priority_topological_score_sum": round(
                        regime_method_tau["priority_topological_score_sum"], 6
                    ),
                    "tau_fas_weighted_balance": round(regime_method_tau["fas_weighted_balance"], 6),
                    "gap_score_sum_minus_fas_weighted_balance": round(
                        regime_method_tau["score_sum"] - regime_method_tau["fas_weighted_balance"], 6
                    ),
                    "gap_borda_minus_fas_weighted_balance": round(
                        regime_method_tau["borda"] - regime_method_tau["fas_weighted_balance"], 6
                    ),
                    "gap_score_sum_minus_greedy_topo": round(
                        regime_method_tau["score_sum"]
                        - regime_method_tau["greedy_fas_topological"],
                        6,
                    ),
                    "repair_loss_score_sum": round(
                        regime_method_tau["score_sum"] - regime_method_tau["score_sum_repaired_dag"],
                        6,
                    ),
                    "extraction_loss_topo_from_repaired_score_sum": round(
                        regime_method_tau["score_sum_repaired_dag"]
                        - regime_method_tau["greedy_fas_topological"],
                        6,
                    ),
                    "extraction_loss_priority_from_repaired_score_sum": round(
                        regime_method_tau["score_sum_repaired_dag"]
                        - regime_method_tau["priority_topological_score_sum"],
                        6,
                    ),
                }
            )

    method_path = args.tables_dir / "diagnostic_method_properties.csv"
    method_run_path = args.tables_dir / "diagnostic_method_run_level.csv"
    regime_path = args.tables_dir / "diagnostic_regime_breakdown.csv"
    run_path = args.tables_dir / "diagnostic_run_level.csv"

    _write_csv(
        method_run_path,
        [
            "seed",
            "noise",
            "n_items",
            "method",
            "kendall_tau",
            "tau_to_score_sum",
            "tau_to_borda",
            "weighted_agreement_original",
            "unweighted_agreement_original",
            "weighted_agreement_repaired_dag",
            "unweighted_agreement_repaired_dag",
            "removed_edges",
            "removed_weight",
            "topo_incomparable_ratio",
            "topo_mean_available_sources",
            "topo_max_available_sources",
            "topo_mean_log2_choices",
            "topo_multi_source_step_ratio",
        ],
        sorted(method_rows, key=lambda r: (r["noise"], r["seed"], r["method"])),
    )

    _write_csv(
        run_path,
        [
            "seed",
            "noise",
            "n_items",
            "removed_edges",
            "removed_weight",
            "topo_incomparable_ratio",
            "topo_mean_available_sources",
            "topo_max_available_sources",
            "topo_mean_log2_choices",
            "topo_multi_source_step_ratio",
            "tau_score_sum",
            "tau_borda",
            "tau_score_sum_repaired_dag",
            "tau_greedy_fas_topological",
            "tau_priority_topological_score_sum",
            "tau_fas_weighted_balance",
            "gap_score_sum_minus_fas_weighted_balance",
            "gap_borda_minus_fas_weighted_balance",
            "gap_score_sum_minus_greedy_topo",
            "repair_loss_score_sum",
            "extraction_loss_topo_from_repaired_score_sum",
            "extraction_loss_priority_from_repaired_score_sum",
        ],
        sorted(run_rows, key=lambda r: (r["noise"], r["seed"])),
    )

    by_method: dict[str, list[dict]] = defaultdict(list)
    for row in method_rows:
        by_method[row["method"]].append(row)
    run_index = {(float(r["noise"]), int(r["seed"])): r for r in run_rows}

    method_summary_rows: list[dict] = []
    for method in methods:
        rows = by_method.get(method, [])
        if not rows:
            continue
        tau_vals = [float(r["kendall_tau"]) for r in rows]
        ss_vals = [float(r["tau_to_score_sum"]) for r in rows]
        borda_vals = [float(r["tau_to_borda"]) for r in rows]
        wagr_vals = [float(r["weighted_agreement_original"]) for r in rows]
        uwagr_vals = [float(r["unweighted_agreement_original"]) for r in rows]
        wagr_dag_vals = [float(r["weighted_agreement_repaired_dag"]) for r in rows]
        gaps_vs_score_sum = []
        gaps_vs_borda = []
        for r in rows:
            regime = run_index[(float(r["noise"]), int(r["seed"]))]
            gaps_vs_score_sum.append(float(r["kendall_tau"]) - float(regime["tau_score_sum"]))
            gaps_vs_borda.append(float(r["kendall_tau"]) - float(regime["tau_borda"]))
        method_summary_rows.append(
            {
                "method": method,
                "n_runs": len(rows),
                "mean_tau": round(float(np.mean(tau_vals)), 6),
                "std_tau": round(float(np.std(tau_vals, ddof=1)) if len(tau_vals) > 1 else 0.0, 6),
                "mean_tau_to_score_sum": round(float(np.mean(ss_vals)), 6),
                "mean_tau_to_borda": round(float(np.mean(borda_vals)), 6),
                "mean_weighted_agreement_original": round(float(np.mean(wagr_vals)), 6),
                "mean_unweighted_agreement_original": round(float(np.mean(uwagr_vals)), 6),
                "mean_weighted_agreement_repaired_dag": round(float(np.mean(wagr_dag_vals)), 6),
                "mean_gap_vs_score_sum": round(float(np.mean(gaps_vs_score_sum)), 6),
                "mean_gap_vs_borda": round(float(np.mean(gaps_vs_borda)), 6),
            }
        )
    _write_csv(
        method_path,
        [
            "method",
            "n_runs",
            "mean_tau",
            "std_tau",
            "mean_tau_to_score_sum",
            "mean_tau_to_borda",
            "mean_weighted_agreement_original",
            "mean_unweighted_agreement_original",
            "mean_weighted_agreement_repaired_dag",
            "mean_gap_vs_score_sum",
            "mean_gap_vs_borda",
        ],
        method_summary_rows,
    )

    # Noise-level regime breakdown.
    by_noise: dict[float, list[dict]] = defaultdict(list)
    for row in run_rows:
        by_noise[float(row["noise"])].append(row)
    regime_rows: list[dict] = []
    for noise in sorted(by_noise):
        rows = by_noise[noise]
        regime_rows.append(
            {
                "noise": round(noise, 4),
                "n_runs": len(rows),
                "mean_tau_score_sum": round(float(np.mean([r["tau_score_sum"] for r in rows])), 6),
                "mean_tau_borda": round(float(np.mean([r["tau_borda"] for r in rows])), 6),
                "mean_tau_score_sum_repaired_dag": round(
                    float(np.mean([r["tau_score_sum_repaired_dag"] for r in rows])), 6
                ),
                "mean_tau_greedy_fas_topological": round(
                    float(np.mean([r["tau_greedy_fas_topological"] for r in rows])), 6
                ),
                "mean_tau_priority_topological_score_sum": round(
                    float(np.mean([r["tau_priority_topological_score_sum"] for r in rows])), 6
                ),
                "mean_tau_fas_weighted_balance": round(
                    float(np.mean([r["tau_fas_weighted_balance"] for r in rows])), 6
                ),
                "mean_gap_score_sum_minus_fas_weighted_balance": round(
                    float(np.mean([r["gap_score_sum_minus_fas_weighted_balance"] for r in rows])),
                    6,
                ),
                "mean_gap_borda_minus_fas_weighted_balance": round(
                    float(np.mean([r["gap_borda_minus_fas_weighted_balance"] for r in rows])),
                    6,
                ),
                "mean_gap_score_sum_minus_greedy_topo": round(
                    float(np.mean([r["gap_score_sum_minus_greedy_topo"] for r in rows])),
                    6,
                ),
                "mean_repair_loss_score_sum": round(
                    float(np.mean([r["repair_loss_score_sum"] for r in rows])), 6
                ),
                "mean_extraction_loss_topo_from_repaired_score_sum": round(
                    float(np.mean([r["extraction_loss_topo_from_repaired_score_sum"] for r in rows])),
                    6,
                ),
                "mean_extraction_loss_priority_from_repaired_score_sum": round(
                    float(
                        np.mean([r["extraction_loss_priority_from_repaired_score_sum"] for r in rows])
                    ),
                    6,
                ),
                "mean_topo_incomparable_ratio": round(
                    float(np.mean([r["topo_incomparable_ratio"] for r in rows])), 6
                ),
                "mean_topo_mean_log2_choices": round(
                    float(np.mean([r["topo_mean_log2_choices"] for r in rows])), 6
                ),
                "mean_removed_weight": round(float(np.mean([r["removed_weight"] for r in rows])), 6),
                "mean_removed_edges": round(float(np.mean([r["removed_edges"] for r in rows])), 6),
            }
        )
    _write_csv(
        regime_path,
        [
            "noise",
            "n_runs",
            "mean_tau_score_sum",
            "mean_tau_borda",
            "mean_tau_score_sum_repaired_dag",
            "mean_tau_greedy_fas_topological",
            "mean_tau_priority_topological_score_sum",
            "mean_tau_fas_weighted_balance",
            "mean_gap_score_sum_minus_fas_weighted_balance",
            "mean_gap_borda_minus_fas_weighted_balance",
            "mean_gap_score_sum_minus_greedy_topo",
            "mean_repair_loss_score_sum",
            "mean_extraction_loss_topo_from_repaired_score_sum",
            "mean_extraction_loss_priority_from_repaired_score_sum",
            "mean_topo_incomparable_ratio",
            "mean_topo_mean_log2_choices",
            "mean_removed_weight",
            "mean_removed_edges",
        ],
        regime_rows,
    )

    args.figures_dir.mkdir(parents=True, exist_ok=True)

    # Figure 1: tau curves vs noise.
    xs = [r["noise"] for r in regime_rows]
    plt.figure(figsize=(8, 5))
    plt.plot(xs, [r["mean_tau_score_sum"] for r in regime_rows], marker="o", label="score_sum")
    plt.plot(xs, [r["mean_tau_borda"] for r in regime_rows], marker="o", label="borda")
    plt.plot(
        xs,
        [r["mean_tau_greedy_fas_topological"] for r in regime_rows],
        marker="o",
        label="greedy_fas_topological",
    )
    plt.plot(
        xs,
        [r["mean_tau_priority_topological_score_sum"] for r in regime_rows],
        marker="o",
        label="priority_topological_score_sum",
    )
    plt.plot(
        xs,
        [r["mean_tau_fas_weighted_balance"] for r in regime_rows],
        marker="o",
        label="fas_weighted_balance",
    )
    plt.xlabel("Noise")
    plt.ylabel("Mean Kendall tau")
    plt.title("Diagnostic: tau vs noise")
    plt.grid(alpha=0.3)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(args.figures_dir / "diagnostic_gap_vs_noise.png", dpi=160)
    plt.close()

    # Figure 2: weighted agreement vs tau.
    plt.figure(figsize=(8, 5))
    for method in methods:
        rows = by_method.get(method, [])
        if not rows:
            continue
        plt.scatter(
            [r["weighted_agreement_original"] for r in rows],
            [r["kendall_tau"] for r in rows],
            s=20,
            alpha=0.7,
            label=method,
        )
    plt.xlabel("Weighted agreement with original preference graph")
    plt.ylabel("Kendall tau vs ground truth")
    plt.title("Diagnostic: agreement with graph vs ranking quality")
    plt.grid(alpha=0.3)
    plt.legend(fontsize=7, ncol=2)
    plt.tight_layout()
    plt.savefig(args.figures_dir / "diagnostic_agreement_vs_tau.png", dpi=160)
    plt.close()

    # Figure 3: topological ambiguity vs FAS gap.
    x = np.array([r["topo_mean_log2_choices"] for r in run_rows], dtype=float)
    y1 = np.array([r["gap_score_sum_minus_greedy_topo"] for r in run_rows], dtype=float)
    y2 = np.array([r["gap_score_sum_minus_fas_weighted_balance"] for r in run_rows], dtype=float)
    plt.figure(figsize=(8, 5))
    plt.scatter(x, y1, alpha=0.75, s=24, label="score_sum - greedy_fas_topological")
    plt.scatter(x, y2, alpha=0.75, s=24, label="score_sum - fas_weighted_balance")
    if len(x) >= 2:
        m1, b1 = np.polyfit(x, y1, 1)
        m2, b2 = np.polyfit(x, y2, 1)
        xr = np.linspace(float(x.min()), float(x.max()), 100)
        plt.plot(xr, m1 * xr + b1, linewidth=1.5)
        plt.plot(xr, m2 * xr + b2, linewidth=1.5)
    plt.xlabel("Topological ambiguity (mean log2 available sources)")
    plt.ylabel("Tau gap vs score_sum")
    plt.title("Diagnostic: ambiguity in repaired DAG vs FAS tau gap")
    plt.grid(alpha=0.3)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(args.figures_dir / "diagnostic_topo_ambiguity.png", dpi=160)
    plt.close()

    print(f"Wrote: {method_path}")
    print(f"Wrote: {method_run_path}")
    print(f"Wrote: {regime_path}")
    print(f"Wrote: {run_path}")
    print(f"Wrote: {args.figures_dir / 'diagnostic_gap_vs_noise.png'}")
    print(f"Wrote: {args.figures_dir / 'diagnostic_agreement_vs_tau.png'}")
    print(f"Wrote: {args.figures_dir / 'diagnostic_topo_ambiguity.png'}")


if __name__ == "__main__":
    main()
