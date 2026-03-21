"""
run_regime_analysis.py
======================
Regime analysis: WHEN does FAS-based ranking beat simple baselines?

Runs a grid of synthetic experiments over:
  - noise ∈ {0.05, 0.10, 0.15, 0.20, 0.25, 0.30}
  - n_items ∈ {10, 20, 50}
  - weight_scheme ∈ {margin, uniform}
  - seeds ∈ {42, 123, 7}

Methods compared (shortlist):
  - score_sum
  - borda
  - greedy_fas_weighted_balance
  - hybrid_rrf_fas_regularized
  - fas_balance_score_prior_alpha_beta  (α=2.0, β=1.0)

Metrics per run:
  - kendall_tau
  - ndcg@k  (quality-based relevance)
  - pairwise_accuracy
  - inconsistency_before / inconsistency_after repair

Outputs:
  - docs/tables/regime_analysis.csv      (per-run rows)
  - docs/tables/regime_summary.csv       (aggregated by regime)
  - docs/figures/regime_analysis_*.png   (performance & gap plots)

Usage::

    python scripts/run_regime_analysis.py
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
from consistency_ranker.graph_construction import build_graph, graph_summary
from consistency_ranker.greedy_fas import greedy_fas
from consistency_ranker.pairwise_prefs import generate_preferences
from consistency_ranker.synthetic_data import generate_items, ground_truth_ranking, quality_map

# ---------------------------------------------------------------------------
# Grid parameters
# ---------------------------------------------------------------------------
NOISE_LEVELS = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
N_ITEMS_LIST = [10, 20, 50]
WEIGHT_SCHEMES = ["margin", "uniform"]
SEEDS = [42, 123, 7]

METHODS = [
    "score_sum",
    "borda",
    "greedy_fas_weighted_balance",
    "hybrid_rrf_fas_regularized",
    "fas_balance_score_prior_alpha_beta",
]

FAS_METHODS = {
    "greedy_fas_weighted_balance",
    "hybrid_rrf_fas_regularized",
    "fas_balance_score_prior_alpha_beta",
}

# ---------------------------------------------------------------------------
# nDCG helper (using quality scores as graded relevance)
# ---------------------------------------------------------------------------

def _dcg(ranking: list[str], relevance: dict[str, float], k: int) -> float:
    """Discounted Cumulative Gain at rank *k*."""
    total = 0.0
    for i, item in enumerate(ranking[:k]):
        rel = relevance.get(item, 0.0)
        total += rel / math.log2(i + 2)  # i+2 because rank is 1-indexed
    return total


def ndcg_at_k(ranking: list[str], ideal: list[str],
              relevance: dict[str, float], k: int) -> float:
    """Normalised DCG at *k*."""
    dcg = _dcg(ranking, relevance, k)
    idcg = _dcg(ideal, relevance, k)
    if idcg == 0.0:
        return 0.0
    return dcg / idcg


# ---------------------------------------------------------------------------
# Single experiment runner
# ---------------------------------------------------------------------------

def run_single(n_items: int, noise: float, weight_scheme: str,
               seed: int) -> list[dict]:
    """Run one experiment and return a list of per-method result dicts."""
    items = generate_items(n=n_items, seed=seed)
    qmap = quality_map(items)
    gt = ground_truth_ranking(items)

    prefs = generate_preferences(qmap, noise=noise,
                                 weight_scheme=weight_scheme, seed=seed)
    graph = build_graph(prefs)
    g_sum = graph_summary(graph)

    dag, removed_edges = greedy_fas(graph)
    ss_scores = score_sum_scores(graph)
    borda_sc = borda_scores(graph)

    rankings = {
        "score_sum": score_sum_ranking(graph),
        "borda": borda_ranking(graph),
        "greedy_fas_weighted_balance": weighted_out_minus_in_ranking(dag),
        "hybrid_rrf_fas_regularized": hybrid_rrf_fas_regularized_ranking(
            dag, ss_scores, fas_regularization=0.2),
        "fas_balance_score_prior_alpha_beta":
            fas_balance_score_prior_alpha_beta_ranking(
                dag, ss_scores, alpha=2.0, beta=1.0),
    }

    incons_before = pairwise_inconsistency_count(graph, gt)
    incons_after = pairwise_inconsistency_count(dag, gt)
    total_pairs = n_items * (n_items - 1) // 2
    k = min(10, n_items)

    rows = []
    for method in METHODS:
        ranking = rankings[method]
        tau = kendall_tau(ranking, gt)
        viols = n_violations(ranking, gt)
        pw_acc = 1.0 - viols / total_pairs if total_pairs > 0 else 1.0
        ndcg = ndcg_at_k(ranking, gt, qmap, k)

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
            "inconsistency_after": incons_after if method in FAS_METHODS
                                   else incons_before,
            "edges_removed": len(removed_edges) if method in FAS_METHODS
                             else 0,
            "n_edges": g_sum["n_edges"],
            "is_dag": g_sum["is_dag"],
        })
    return rows


# ---------------------------------------------------------------------------
# Full grid runner
# ---------------------------------------------------------------------------

def run_grid() -> pd.DataFrame:
    """Execute the full regime grid and return raw results."""
    total = (len(NOISE_LEVELS) * len(N_ITEMS_LIST) * len(WEIGHT_SCHEMES)
             * len(SEEDS))
    print(f"Running {total} experiments "
          f"({len(METHODS)} methods each) …")

    all_rows: list[dict] = []
    done = 0
    for n_items in N_ITEMS_LIST:
        for noise in NOISE_LEVELS:
            for ws in WEIGHT_SCHEMES:
                for seed in SEEDS:
                    rows = run_single(n_items, noise, ws, seed)
                    all_rows.extend(rows)
                    done += 1
                    if done % 18 == 0 or done == total:
                        print(f"  [{done}/{total}] completed")

    return pd.DataFrame(all_rows)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate raw results by regime (n_items, noise, weight_scheme, method)."""
    group_cols = ["n_items", "noise", "weight_scheme", "method"]
    metric_cols = ["kendall_tau", "ndcg", "pairwise_accuracy",
                   "n_violations", "inconsistency_before",
                   "inconsistency_after", "edges_removed"]
    agg = df.groupby(group_cols)[metric_cols].agg(["mean", "std"]).reset_index()
    agg.columns = [
        f"{c[0]}_{c[1]}" if c[1] else c[0]
        for c in agg.columns
    ]
    return agg


# ---------------------------------------------------------------------------
# Comparative analysis: where FAS wins
# ---------------------------------------------------------------------------

def compute_deltas(summary: pd.DataFrame) -> pd.DataFrame:
    """For each regime, compute FAS method gap vs score_sum and borda."""
    regime_cols = ["n_items", "noise", "weight_scheme"]

    pivoted = summary.pivot_table(
        index=regime_cols,
        columns="method",
        values="kendall_tau_mean",
    ).reset_index()

    fas_methods_list = [m for m in METHODS if m in FAS_METHODS]
    for fm in fas_methods_list:
        pivoted[f"{fm}_vs_score_sum"] = pivoted[fm] - pivoted["score_sum"]
        pivoted[f"{fm}_vs_borda"] = pivoted[fm] - pivoted["borda"]

    return pivoted


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def create_plots(summary: pd.DataFrame, deltas: pd.DataFrame,
                 fig_dir: Path) -> None:
    """Generate all regime analysis plots."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dir.mkdir(parents=True, exist_ok=True)

    # --- Plot 1: Kendall τ vs noise, faceted by n_items & weight_scheme ---
    fig, axes = plt.subplots(len(N_ITEMS_LIST), len(WEIGHT_SCHEMES),
                             figsize=(14, 12), sharey=True)
    for i, n_items in enumerate(N_ITEMS_LIST):
        for j, ws in enumerate(WEIGHT_SCHEMES):
            ax = axes[i][j] if len(N_ITEMS_LIST) > 1 else axes[j]
            sub = summary[(summary["n_items"] == n_items) &
                          (summary["weight_scheme"] == ws)]
            for method in METHODS:
                m_data = sub[sub["method"] == method].sort_values("noise")
                style = "--" if method in FAS_METHODS else "-"
                marker = "o" if method not in FAS_METHODS else "s"
                ax.errorbar(m_data["noise"], m_data["kendall_tau_mean"],
                            yerr=m_data["kendall_tau_std"],
                            label=method.replace("_", " "),
                            linestyle=style, marker=marker, capsize=3,
                            markersize=5)
            ax.set_title(f"n={n_items}, {ws}")
            ax.set_xlabel("Noise")
            ax.set_ylabel("Kendall τ")
            ax.grid(True, alpha=0.3)
            if i == 0 and j == 0:
                ax.legend(fontsize=7, loc="lower left")
    fig.suptitle("Kendall τ vs Noise by Regime", fontsize=14, y=1.01)
    fig.tight_layout()
    fig.savefig(fig_dir / "regime_analysis_kendall_tau.png",
                dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- Plot 2: Gap to score_sum (best FAS method) ---
    fig, axes = plt.subplots(1, len(WEIGHT_SCHEMES), figsize=(14, 5),
                             sharey=True)
    fas_list = [m for m in METHODS if m in FAS_METHODS]
    for j, ws in enumerate(WEIGHT_SCHEMES):
        ax = axes[j]
        sub = deltas[deltas["weight_scheme"] == ws]
        for n_items in N_ITEMS_LIST:
            ns = sub[sub["n_items"] == n_items].sort_values("noise")
            best_gap = ns[[f"{fm}_vs_score_sum" for fm in fas_list]].max(axis=1)
            ax.plot(ns["noise"], best_gap, marker="o",
                    label=f"n={n_items}")
        ax.axhline(0, color="black", linewidth=0.8, linestyle=":")
        ax.set_title(f"Best FAS gap vs score_sum ({ws})")
        ax.set_xlabel("Noise")
        ax.set_ylabel("Δ Kendall τ (FAS − score_sum)")
        ax.legend()
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(fig_dir / "regime_analysis_gap_to_score_sum.png",
                dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- Plot 3: Gap to borda (best FAS method) ---
    fig, axes = plt.subplots(1, len(WEIGHT_SCHEMES), figsize=(14, 5),
                             sharey=True)
    for j, ws in enumerate(WEIGHT_SCHEMES):
        ax = axes[j]
        sub = deltas[deltas["weight_scheme"] == ws]
        for n_items in N_ITEMS_LIST:
            ns = sub[sub["n_items"] == n_items].sort_values("noise")
            best_gap = ns[[f"{fm}_vs_borda" for fm in fas_list]].max(axis=1)
            ax.plot(ns["noise"], best_gap, marker="o",
                    label=f"n={n_items}")
        ax.axhline(0, color="black", linewidth=0.8, linestyle=":")
        ax.set_title(f"Best FAS gap vs borda ({ws})")
        ax.set_xlabel("Noise")
        ax.set_ylabel("Δ Kendall τ (FAS − borda)")
        ax.legend()
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(fig_dir / "regime_analysis_gap_to_borda.png",
                dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- Plot 4: nDCG vs noise ---
    fig, axes = plt.subplots(len(N_ITEMS_LIST), len(WEIGHT_SCHEMES),
                             figsize=(14, 12), sharey=True)
    for i, n_items in enumerate(N_ITEMS_LIST):
        for j, ws in enumerate(WEIGHT_SCHEMES):
            ax = axes[i][j] if len(N_ITEMS_LIST) > 1 else axes[j]
            sub = summary[(summary["n_items"] == n_items) &
                          (summary["weight_scheme"] == ws)]
            for method in METHODS:
                m_data = sub[sub["method"] == method].sort_values("noise")
                style = "--" if method in FAS_METHODS else "-"
                marker = "o" if method not in FAS_METHODS else "s"
                ax.errorbar(m_data["noise"], m_data["ndcg_mean"],
                            yerr=m_data["ndcg_std"],
                            label=method.replace("_", " "),
                            linestyle=style, marker=marker, capsize=3,
                            markersize=5)
            ax.set_title(f"n={n_items}, {ws}")
            ax.set_xlabel("Noise")
            ax.set_ylabel("nDCG@k")
            ax.grid(True, alpha=0.3)
            if i == 0 and j == 0:
                ax.legend(fontsize=7, loc="lower left")
    fig.suptitle("nDCG vs Noise by Regime", fontsize=14, y=1.01)
    fig.tight_layout()
    fig.savefig(fig_dir / "regime_analysis_ndcg.png",
                dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- Plot 5: Pairwise accuracy vs noise ---
    fig, axes = plt.subplots(1, len(WEIGHT_SCHEMES), figsize=(14, 5),
                             sharey=True)
    for j, ws in enumerate(WEIGHT_SCHEMES):
        ax = axes[j]
        sub = summary[summary["weight_scheme"] == ws]
        for method in METHODS:
            m_data = sub[sub["method"] == method]
            agg = m_data.groupby("noise")["pairwise_accuracy_mean"].mean()
            style = "--" if method in FAS_METHODS else "-"
            ax.plot(agg.index, agg.values,
                    label=method.replace("_", " "),
                    linestyle=style, marker="o", markersize=5)
        ax.set_title(f"Pairwise accuracy ({ws})")
        ax.set_xlabel("Noise")
        ax.set_ylabel("Pairwise Accuracy")
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(fig_dir / "regime_analysis_pairwise_accuracy.png",
                dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"  Plots saved to {fig_dir}/")


# ---------------------------------------------------------------------------
# Analysis report
# ---------------------------------------------------------------------------

def print_analysis(summary: pd.DataFrame, deltas: pd.DataFrame) -> str:
    """Print and return a text analysis of where FAS wins/loses."""
    lines: list[str] = []
    lines.append("\n" + "=" * 70)
    lines.append("  REGIME ANALYSIS RESULTS")
    lines.append("=" * 70)

    fas_list = [m for m in METHODS if m in FAS_METHODS]
    regime_cols = ["n_items", "noise", "weight_scheme"]

    # Where FAS beats score_sum
    lines.append("\n--- Regimes where best FAS beats score_sum (Kendall τ) ---")
    wins_ss = 0
    total_regimes = 0
    best_gain_ss = -999.0
    best_gain_ss_regime = ""
    worst_loss_ss = 999.0
    worst_loss_ss_regime = ""

    for _, row in deltas.iterrows():
        total_regimes += 1
        gaps = [row[f"{fm}_vs_score_sum"] for fm in fas_list]
        best_gap = max(gaps)
        best_method = fas_list[int(np.argmax(gaps))]
        regime_str = (f"n={int(row['n_items'])}, noise={row['noise']:.2f}, "
                      f"ws={row['weight_scheme']}")
        if best_gap > 0.001:
            wins_ss += 1
            lines.append(f"  ✓ {regime_str}: +{best_gap:.4f} "
                         f"({best_method})")
        if best_gap > best_gain_ss:
            best_gain_ss = best_gap
            best_gain_ss_regime = regime_str
        if best_gap < worst_loss_ss:
            worst_loss_ss = best_gap
            worst_loss_ss_regime = regime_str

    lines.append(f"\n  FAS beats score_sum in {wins_ss}/{total_regimes} "
                 f"regimes ({100*wins_ss/total_regimes:.0f}%)")
    lines.append(f"  Largest gain:  {best_gain_ss:+.4f} at {best_gain_ss_regime}")
    lines.append(f"  Largest loss:  {worst_loss_ss:+.4f} at {worst_loss_ss_regime}")

    # Where FAS beats borda
    lines.append("\n--- Regimes where best FAS beats borda (Kendall τ) ---")
    wins_borda = 0
    best_gain_borda = -999.0
    best_gain_borda_regime = ""
    worst_loss_borda = 999.0
    worst_loss_borda_regime = ""

    for _, row in deltas.iterrows():
        gaps = [row[f"{fm}_vs_borda"] for fm in fas_list]
        best_gap = max(gaps)
        best_method = fas_list[int(np.argmax(gaps))]
        regime_str = (f"n={int(row['n_items'])}, noise={row['noise']:.2f}, "
                      f"ws={row['weight_scheme']}")
        if best_gap > 0.001:
            wins_borda += 1
            lines.append(f"  ✓ {regime_str}: +{best_gap:.4f} "
                         f"({best_method})")
        if best_gap > best_gain_borda:
            best_gain_borda = best_gap
            best_gain_borda_regime = regime_str
        if best_gap < worst_loss_borda:
            worst_loss_borda = best_gap
            worst_loss_borda_regime = regime_str

    lines.append(f"\n  FAS beats borda in {wins_borda}/{total_regimes} "
                 f"regimes ({100*wins_borda/total_regimes:.0f}%)")
    lines.append(f"  Largest gain:  {best_gain_borda:+.4f} at "
                 f"{best_gain_borda_regime}")
    lines.append(f"  Largest loss:  {worst_loss_borda:+.4f} at "
                 f"{worst_loss_borda_regime}")

    # Competitive regimes (within ±0.02)
    lines.append("\n--- Regimes where FAS is competitive with both "
                 "(|Δ| < 0.02) ---")
    competitive = 0
    for _, row in deltas.iterrows():
        gaps_ss = [row[f"{fm}_vs_score_sum"] for fm in fas_list]
        gaps_b = [row[f"{fm}_vs_borda"] for fm in fas_list]
        best_ss = max(gaps_ss)
        best_b = max(gaps_b)
        if abs(best_ss) < 0.02 and abs(best_b) < 0.02:
            competitive += 1
            regime_str = (f"n={int(row['n_items'])}, noise={row['noise']:.2f}, "
                          f"ws={row['weight_scheme']}")
            lines.append(f"  ≈ {regime_str}: "
                         f"vs_ss={best_ss:+.4f}, vs_borda={best_b:+.4f}")
    lines.append(f"\n  Competitive in {competitive}/{total_regimes} regimes")

    # Inconsistency reduction
    lines.append("\n--- Inconsistency reduction by FAS ---")
    fas_summary = summary[summary["method"].isin(FAS_METHODS)]
    if "inconsistency_before_mean" in fas_summary.columns:
        grp = fas_summary.groupby(["n_items", "noise", "weight_scheme"]).agg(
            incons_before=("inconsistency_before_mean", "first"),
            incons_after=("inconsistency_after_mean", "min"),
        ).reset_index()
        grp["reduction_pct"] = (
            100 * (grp["incons_before"] - grp["incons_after"]) /
            grp["incons_before"].replace(0, np.nan)
        )
        avg_reduction = grp["reduction_pct"].mean()
        lines.append(f"  Average inconsistency reduction: {avg_reduction:.1f}%")
        best_row = grp.loc[grp["reduction_pct"].idxmax()]
        lines.append(
            f"  Best reduction: {best_row['reduction_pct']:.1f}% "
            f"at n={int(best_row['n_items'])}, "
            f"noise={best_row['noise']:.2f}, "
            f"ws={best_row['weight_scheme']}"
        )

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

    # 1. Run grid
    df = run_grid()

    # 2. Save raw results
    raw_path = table_dir / "regime_analysis.csv"
    df.to_csv(raw_path, index=False)
    print(f"\nRaw results saved to {raw_path}")

    # 3. Build summary
    summary = build_summary(df)
    summary_path = table_dir / "regime_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"Summary saved to {summary_path}")

    # 4. Compute deltas
    deltas = compute_deltas(summary)
    deltas_path = table_dir / "regime_deltas.csv"
    deltas.to_csv(deltas_path, index=False)
    print(f"Deltas saved to {deltas_path}")

    # 5. Plots
    create_plots(summary, deltas, fig_dir)

    # 6. Analysis report
    report = print_analysis(summary, deltas)
    report_path = table_dir / "regime_report.txt"
    report_path.write_text(report)
    print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    main()
