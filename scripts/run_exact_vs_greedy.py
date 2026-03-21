"""
run_exact_vs_greedy.py
======================
Diagnostic study: exact vs greedy FAS repair on small synthetic graphs.

Research question: is the failure of FAS-based ranking in bad regimes
caused by (A) the greedy heuristic being a weak optimizer, or (B) the
FAS objective itself being misaligned with ranking quality?

Approach:
  - For very small n (6, 8), enumerate all n! permutations to find the
    exact minimum-weight feedback arc set.
  - Compare exact-FAS-based rankings against greedy-FAS-based rankings
    and simple baselines (score_sum, borda).
  - If exact FAS substantially beats greedy FAS → problem is (A).
  - If exact FAS ≈ greedy FAS, both failing → problem is (B).

Grid:
  - n_items ∈ {6, 8}
  - noise ∈ {0.05, 0.20, 0.30}
  - weight_scheme ∈ {margin, uniform}
  - seeds ∈ {42, 123, 7}

Outputs:
  - docs/tables/exact_vs_greedy_fas.csv
  - docs/tables/exact_vs_greedy_summary.csv
  - docs/figures/exact_vs_greedy_gap.png

Usage::

    python scripts/run_exact_vs_greedy.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from consistency_ranker.baseline_ranking import (
    borda_ranking,
    borda_scores,
    fas_balance_score_prior_alpha_beta_ranking,
    hybrid_rrf_fas_regularized_ranking,
    score_sum_ranking,
    score_sum_scores,
    weighted_out_minus_in_ranking,
)
from consistency_ranker.evaluation import (
    kendall_tau,
    n_violations,
    pairwise_inconsistency_count,
)
from consistency_ranker.exact_fas import exact_fas
from consistency_ranker.graph_construction import build_graph, graph_summary
from consistency_ranker.greedy_fas import greedy_fas, greedy_fas_total_weight
from consistency_ranker.pairwise_prefs import generate_preferences
from consistency_ranker.synthetic_data import generate_items, ground_truth_ranking, quality_map

# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------
N_ITEMS_LIST = [6, 8]
NOISE_LEVELS = [0.05, 0.20, 0.30]
WEIGHT_SCHEMES = ["margin", "uniform"]
SEEDS = [42, 123, 7]

METHODS = [
    "score_sum",
    "borda",
    "greedy_fas_weighted_balance",
    "hybrid_rrf_fas_regularized",
    "greedy_fas_alpha_beta",
    "exact_fas_weighted_balance",
    "exact_fas_hybrid_rrf",
    "exact_fas_alpha_beta",
]

GREEDY_FAS_METHODS = {
    "greedy_fas_weighted_balance",
    "hybrid_rrf_fas_regularized",
    "greedy_fas_alpha_beta",
}
EXACT_FAS_METHODS = {
    "exact_fas_weighted_balance",
    "exact_fas_hybrid_rrf",
    "exact_fas_alpha_beta",
}
ALL_FAS_METHODS = GREEDY_FAS_METHODS | EXACT_FAS_METHODS

# ---------------------------------------------------------------------------
# nDCG helper
# ---------------------------------------------------------------------------

def _dcg(ranking: list[str], relevance: dict[str, float], k: int) -> float:
    total = 0.0
    for i, item in enumerate(ranking[:k]):
        rel = relevance.get(item, 0.0)
        total += rel / math.log2(i + 2)
    return total


def ndcg_at_k(ranking: list[str], ideal: list[str],
              relevance: dict[str, float], k: int) -> float:
    dcg = _dcg(ranking, relevance, k)
    idcg = _dcg(ideal, relevance, k)
    return dcg / idcg if idcg > 0.0 else 0.0


# ---------------------------------------------------------------------------
# Single experiment
# ---------------------------------------------------------------------------

def run_single(n_items: int, noise: float, weight_scheme: str,
               seed: int) -> list[dict]:
    items = generate_items(n=n_items, seed=seed)
    qmap = quality_map(items)
    gt = ground_truth_ranking(items)

    prefs = generate_preferences(qmap, noise=noise,
                                 weight_scheme=weight_scheme, seed=seed)
    graph = build_graph(prefs)
    g_sum = graph_summary(graph)

    ss_scores = score_sum_scores(graph)
    borda_sc = borda_scores(graph)

    # Greedy FAS repair
    greedy_dag, greedy_removed = greedy_fas(graph)
    greedy_weight = greedy_fas_total_weight(greedy_removed)

    # Exact FAS repair
    exact_dag, exact_removed, exact_objective = exact_fas(graph)
    exact_weight = sum(w for _, _, w in exact_removed)

    # Rankings from greedy DAG
    greedy_rankings = {
        "greedy_fas_weighted_balance": weighted_out_minus_in_ranking(greedy_dag),
        "hybrid_rrf_fas_regularized": hybrid_rrf_fas_regularized_ranking(
            greedy_dag, ss_scores, fas_regularization=0.2),
        "greedy_fas_alpha_beta": fas_balance_score_prior_alpha_beta_ranking(
            greedy_dag, ss_scores, alpha=2.0, beta=1.0),
    }

    # Rankings from exact DAG
    exact_rankings = {
        "exact_fas_weighted_balance": weighted_out_minus_in_ranking(exact_dag),
        "exact_fas_hybrid_rrf": hybrid_rrf_fas_regularized_ranking(
            exact_dag, ss_scores, fas_regularization=0.2),
        "exact_fas_alpha_beta": fas_balance_score_prior_alpha_beta_ranking(
            exact_dag, ss_scores, alpha=2.0, beta=1.0),
    }

    # Baselines
    baseline_rankings = {
        "score_sum": score_sum_ranking(graph),
        "borda": borda_ranking(graph),
    }

    all_rankings = {**baseline_rankings, **greedy_rankings, **exact_rankings}

    incons_before = pairwise_inconsistency_count(graph, gt)
    incons_greedy = pairwise_inconsistency_count(greedy_dag, gt)
    incons_exact = pairwise_inconsistency_count(exact_dag, gt)
    total_pairs = n_items * (n_items - 1) // 2
    k = min(n_items, 10)

    rows = []
    for method in METHODS:
        ranking = all_rankings[method]
        tau = kendall_tau(ranking, gt)
        viols = n_violations(ranking, gt)
        pw_acc = 1.0 - viols / total_pairs if total_pairs > 0 else 1.0
        ndcg = ndcg_at_k(ranking, gt, qmap, k)

        if method in EXACT_FAS_METHODS:
            incons_after = incons_exact
            removed_w = exact_weight
            n_removed = len(exact_removed)
            obj_val = exact_objective
        elif method in GREEDY_FAS_METHODS:
            incons_after = incons_greedy
            removed_w = greedy_weight
            n_removed = len(greedy_removed)
            obj_val = greedy_weight
        else:
            incons_after = incons_before
            removed_w = 0.0
            n_removed = 0
            obj_val = float("nan")

        rows.append({
            "n_items": n_items,
            "noise": noise,
            "weight_scheme": weight_scheme,
            "seed": seed,
            "method": method,
            "kendall_tau": tau,
            "ndcg": ndcg,
            "pairwise_accuracy": pw_acc,
            "n_violations": viols,
            "inconsistency_before": incons_before,
            "inconsistency_after": incons_after,
            "edges_removed": n_removed,
            "removed_weight": removed_w,
            "objective_value": obj_val,
            "greedy_objective": greedy_weight,
            "exact_objective": exact_objective,
            "n_edges": g_sum["n_edges"],
        })
    return rows


# ---------------------------------------------------------------------------
# Grid runner
# ---------------------------------------------------------------------------

def run_grid() -> pd.DataFrame:
    total = len(N_ITEMS_LIST) * len(NOISE_LEVELS) * len(WEIGHT_SCHEMES) * len(SEEDS)
    print(f"Running {total} experiments ({len(METHODS)} methods each) …")

    all_rows: list[dict] = []
    done = 0
    for n_items in N_ITEMS_LIST:
        for noise in NOISE_LEVELS:
            for ws in WEIGHT_SCHEMES:
                for seed in SEEDS:
                    rows = run_single(n_items, noise, ws, seed)
                    all_rows.extend(rows)
                    done += 1
                    if done % 6 == 0 or done == total:
                        print(f"  [{done}/{total}] completed")
    return pd.DataFrame(all_rows)


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate by regime and compute key gaps."""
    group = ["n_items", "noise", "weight_scheme", "method"]
    metrics = ["kendall_tau", "ndcg", "pairwise_accuracy", "n_violations",
               "inconsistency_after", "removed_weight", "objective_value"]
    agg = df.groupby(group)[metrics].agg(["mean", "std"]).reset_index()
    agg.columns = [f"{a}_{b}" if b else a for a, b in agg.columns]

    regime_cols = ["n_items", "noise", "weight_scheme"]
    pivoted = agg.pivot_table(
        index=regime_cols, columns="method",
        values="kendall_tau_mean",
    ).reset_index()

    greedy_methods = [m for m in METHODS if m in GREEDY_FAS_METHODS]
    exact_methods = [m for m in METHODS if m in EXACT_FAS_METHODS]

    pivoted["best_greedy_tau"] = pivoted[greedy_methods].max(axis=1)
    pivoted["best_exact_tau"] = pivoted[exact_methods].max(axis=1)
    pivoted["exact_minus_greedy"] = pivoted["best_exact_tau"] - pivoted["best_greedy_tau"]
    pivoted["exact_minus_score_sum"] = pivoted["best_exact_tau"] - pivoted["score_sum"]
    pivoted["exact_minus_borda"] = pivoted["best_exact_tau"] - pivoted["borda"]
    pivoted["greedy_minus_score_sum"] = pivoted["best_greedy_tau"] - pivoted["score_sum"]
    pivoted["greedy_minus_borda"] = pivoted["best_greedy_tau"] - pivoted["borda"]

    # Also pivot objective values
    obj_pivot = agg[agg["method"].isin(list(GREEDY_FAS_METHODS) + list(EXACT_FAS_METHODS))]
    obj_by_regime = obj_pivot.groupby(regime_cols).agg(
        greedy_removed_weight=("removed_weight_mean", "first"),
    ).reset_index()

    exact_obj = df[df["method"].isin(EXACT_FAS_METHODS)].groupby(
        regime_cols)["exact_objective"].mean().reset_index()
    greedy_obj = df[df["method"].isin(GREEDY_FAS_METHODS)].groupby(
        regime_cols)["greedy_objective"].mean().reset_index()

    pivoted = pivoted.merge(exact_obj, on=regime_cols, how="left")
    pivoted = pivoted.merge(greedy_obj, on=regime_cols, how="left")
    pivoted["objective_gap_pct"] = (
        100 * (pivoted["greedy_objective"] - pivoted["exact_objective"])
        / pivoted["exact_objective"].replace(0, np.nan)
    )

    return agg, pivoted


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def create_plots(pivoted: pd.DataFrame, fig_dir: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dir.mkdir(parents=True, exist_ok=True)

    # --- Plot 1: exact_minus_greedy gap ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for j, ws in enumerate(WEIGHT_SCHEMES):
        ax = axes[j]
        sub = pivoted[pivoted["weight_scheme"] == ws]
        for n_items in N_ITEMS_LIST:
            ns = sub[sub["n_items"] == n_items].sort_values("noise")
            ax.plot(ns["noise"], ns["exact_minus_greedy"], marker="o",
                    linewidth=2, label=f"n={n_items}")
        ax.axhline(0, color="black", linewidth=0.8, linestyle=":")
        ax.set_title(f"Exact − Greedy FAS (Kendall τ), {ws}")
        ax.set_xlabel("Noise")
        ax.set_ylabel("Δ Kendall τ")
        ax.legend()
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(fig_dir / "exact_vs_greedy_gap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- Plot 2: All methods comparison ---
    fig, axes = plt.subplots(len(N_ITEMS_LIST), len(WEIGHT_SCHEMES),
                             figsize=(14, 10), sharey=True)
    method_display = {
        "score_sum": ("score_sum", "-", "o"),
        "borda": ("borda", "-", "^"),
        "greedy_fas_weighted_balance": ("greedy balance", "--", "s"),
        "hybrid_rrf_fas_regularized": ("greedy hybrid", "--", "D"),
        "greedy_fas_alpha_beta": ("greedy α/β", "--", "v"),
        "exact_fas_weighted_balance": ("EXACT balance", "-.", "s"),
        "exact_fas_hybrid_rrf": ("EXACT hybrid", "-.", "D"),
        "exact_fas_alpha_beta": ("EXACT α/β", "-.", "v"),
    }
    for i, n_items in enumerate(N_ITEMS_LIST):
        for j, ws in enumerate(WEIGHT_SCHEMES):
            ax = axes[i][j]
            sub = pivoted[(pivoted["n_items"] == n_items) &
                          (pivoted["weight_scheme"] == ws)].sort_values("noise")
            for method, (label, ls, mk) in method_display.items():
                if method in sub.columns:
                    color = None
                    lw = 2 if "EXACT" in label else 1.5
                    ax.plot(sub["noise"], sub[method], marker=mk,
                            linestyle=ls, label=label, linewidth=lw,
                            markersize=6)
            ax.set_title(f"n={n_items}, {ws}")
            ax.set_xlabel("Noise")
            ax.set_ylabel("Kendall τ")
            ax.grid(True, alpha=0.3)
            if i == 0 and j == 0:
                ax.legend(fontsize=6, loc="lower left", ncol=2)
    fig.suptitle("Exact vs Greedy FAS: All Methods", fontsize=14, y=1.01)
    fig.tight_layout()
    fig.savefig(fig_dir / "exact_vs_greedy_all_methods.png",
                dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- Plot 3: Objective gap (greedy excess weight %) ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for j, ws in enumerate(WEIGHT_SCHEMES):
        ax = axes[j]
        sub = pivoted[pivoted["weight_scheme"] == ws]
        for n_items in N_ITEMS_LIST:
            ns = sub[sub["n_items"] == n_items].sort_values("noise")
            ax.plot(ns["noise"], ns["objective_gap_pct"], marker="o",
                    linewidth=2, label=f"n={n_items}")
        ax.axhline(0, color="black", linewidth=0.8, linestyle=":")
        ax.set_title(f"Greedy excess removed weight (%), {ws}")
        ax.set_xlabel("Noise")
        ax.set_ylabel("(Greedy − Exact) / Exact × 100%")
        ax.legend()
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(fig_dir / "exact_vs_greedy_objective_gap.png",
                dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"  Plots saved to {fig_dir}/")


# ---------------------------------------------------------------------------
# Analysis report
# ---------------------------------------------------------------------------

def print_analysis(pivoted: pd.DataFrame) -> str:
    lines: list[str] = []
    lines.append("\n" + "=" * 70)
    lines.append("  EXACT vs GREEDY FAS DIAGNOSTIC")
    lines.append("=" * 70)

    # Exact vs greedy gap
    lines.append("\n--- Exact − Greedy FAS gap (Kendall τ) per regime ---")
    for _, row in pivoted.sort_values(["n_items", "weight_scheme", "noise"]).iterrows():
        regime = (f"n={int(row['n_items'])}, noise={row['noise']:.2f}, "
                  f"ws={row['weight_scheme']}")
        gap = row["exact_minus_greedy"]
        obj_gap = row.get("objective_gap_pct", float("nan"))
        marker = "▲" if gap > 0.01 else ("▼" if gap < -0.01 else "≈")
        lines.append(
            f"  {marker} {regime}: Δτ = {gap:+.4f}  "
            f"(obj gap: {obj_gap:+.1f}%)"
        )

    avg_gap = pivoted["exact_minus_greedy"].mean()
    max_gap = pivoted["exact_minus_greedy"].max()
    min_gap = pivoted["exact_minus_greedy"].min()
    lines.append(f"\n  Mean exact−greedy gap:   {avg_gap:+.4f}")
    lines.append(f"  Max gap (exact better):  {max_gap:+.4f}")
    lines.append(f"  Min gap (greedy better): {min_gap:+.4f}")

    # Objective quality
    lines.append("\n--- Greedy MWFAS objective quality ---")
    avg_obj_gap = pivoted["objective_gap_pct"].mean()
    max_obj_gap = pivoted["objective_gap_pct"].max()
    lines.append(f"  Mean excess removed weight: {avg_obj_gap:+.1f}%")
    lines.append(f"  Worst excess removed weight: {max_obj_gap:+.1f}%")

    # Does exact FAS close the gap to baselines?
    lines.append("\n--- Does exact FAS close the gap to baselines? ---")
    for _, row in pivoted.sort_values(["n_items", "weight_scheme", "noise"]).iterrows():
        regime = (f"n={int(row['n_items'])}, noise={row['noise']:.2f}, "
                  f"ws={row['weight_scheme']}")
        ex_ss = row["exact_minus_score_sum"]
        ex_b = row["exact_minus_borda"]
        gr_ss = row["greedy_minus_score_sum"]
        gr_b = row["greedy_minus_borda"]
        lines.append(
            f"  {regime}:\n"
            f"    exact vs ss: {ex_ss:+.4f}  |  exact vs borda: {ex_b:+.4f}\n"
            f"    greedy vs ss: {gr_ss:+.4f}  |  greedy vs borda: {gr_b:+.4f}"
        )

    # Count regimes where exact FAS beats baselines but greedy doesn't
    n_exact_rescues_ss = 0
    n_exact_rescues_borda = 0
    total = len(pivoted)
    for _, row in pivoted.iterrows():
        if row["exact_minus_score_sum"] > 0.001 and row["greedy_minus_score_sum"] <= 0.001:
            n_exact_rescues_ss += 1
        if row["exact_minus_borda"] > 0.001 and row["greedy_minus_borda"] <= 0.001:
            n_exact_rescues_borda += 1

    lines.append(f"\n  Regimes where exact rescues FAS vs score_sum "
                 f"(exact wins, greedy doesn't): {n_exact_rescues_ss}/{total}")
    lines.append(f"  Regimes where exact rescues FAS vs borda "
                 f"(exact wins, greedy doesn't): {n_exact_rescues_borda}/{total}")

    # Diagnosis
    lines.append("\n--- DIAGNOSIS ---")
    if avg_gap < 0.02:
        lines.append("  The exact-vs-greedy gap is SMALL (mean < 0.02 τ).")
        lines.append("  → The greedy heuristic is NOT the main problem.")
        lines.append("  → The issue is likely OBJECTIVE MISALIGNMENT:")
        lines.append("    minimizing removed weight does not directly")
        lines.append("    maximise ranking quality (Kendall τ).")
    else:
        lines.append("  The exact-vs-greedy gap is SUBSTANTIAL (mean ≥ 0.02 τ).")
        lines.append("  → Improving the optimizer could materially help.")

    exact_beats_ss = (pivoted["exact_minus_score_sum"] > 0.001).sum()
    exact_beats_borda = (pivoted["exact_minus_borda"] > 0.001).sum()
    lines.append(f"\n  Even with exact MWFAS:")
    lines.append(f"    Beats score_sum in {exact_beats_ss}/{total} regimes")
    lines.append(f"    Beats borda in {exact_beats_borda}/{total} regimes")

    lines.append("\n" + "=" * 70)
    report = "\n".join(lines)
    print(report)
    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    table_dir = Path("docs/tables")
    fig_dir = Path("docs/figures")
    table_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    df = run_grid()

    raw_path = table_dir / "exact_vs_greedy_fas.csv"
    df.to_csv(raw_path, index=False)
    print(f"\nRaw results saved to {raw_path}")

    agg, pivoted = build_summary(df)
    summary_path = table_dir / "exact_vs_greedy_summary.csv"
    pivoted.to_csv(summary_path, index=False)
    print(f"Summary saved to {summary_path}")

    create_plots(pivoted, fig_dir)

    report = print_analysis(pivoted)
    report_path = table_dir / "exact_vs_greedy_report.txt"
    report_path.write_text(report)
    print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    main()
