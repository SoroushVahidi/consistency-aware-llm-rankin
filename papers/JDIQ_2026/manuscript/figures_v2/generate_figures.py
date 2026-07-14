#!/usr/bin/env python3
"""Regenerate Figures 2-11 for the JDIQ manuscript with a consistent design
system. Reads only from the existing canonical CSVs under
reports/full_calibrated_core/tables/ (no new experiments, no altered numbers).
Writes .pdf (vector, used by LaTeX) and .png (raster preview) for each figure
into this directory.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from style import (  # noqa: E402
    DATASET_ORDER, DATASET_COLORS, DATASET_LABELS, REGIME_ORDER,
    DIVERGING_NEG, DIVERGING_POS, DIVERGING_NEUTRAL, ROLE_RAW, ROLE_CALIBRATED,
    INK, MUTED_INK, GRID, AXIS, ZERO_LINE, TICK_SIZE, ANNOT_SIZE, BASE_SIZE,
    apply_style, dataset_color, dataset_label, regime_label, sign_color,
    style_axes, panel_label, savefig,
)

TABLES = HERE.parents[3] / "reports" / "full_calibrated_core" / "tables"
PRIMARY = "primary_minmax_retention_matched"
RAW = "ablation_raw_fixed"

apply_style()


def _regime_x():
    return np.arange(len(REGIME_ORDER))


# ---------------------------------------------------------------------------
# Figure 2: BM25 conditional weight share, raw vs calibrated (grouped bars)
# ---------------------------------------------------------------------------
def fig2_bm25_share():
    df = pd.read_csv(TABLES / "full_bm25_weight_share.csv")
    fig, axes = plt.subplots(1, 4, figsize=(7.0, 2.1), sharey=True)
    width = 0.34
    x = _regime_x()
    for i, ds in enumerate(DATASET_ORDER):
        ax = axes[i]
        sub = df[df["dataset"] == ds]
        raw_vals = [sub[(sub.protocol == RAW) & (sub.regime == r)]["bm25_weight_share_conditional"].iloc[0] for r in REGIME_ORDER]
        cal_vals = [sub[(sub.protocol == PRIMARY) & (sub.regime == r)]["bm25_weight_share_conditional"].iloc[0] for r in REGIME_ORDER]
        ax.bar(x - width / 2, raw_vals, width, color=ROLE_RAW, label="Raw" if i == 0 else None)
        ax.bar(x + width / 2, cal_vals, width, color=ROLE_CALIBRATED, label="Normalized" if i == 0 else None)
        ax.set_xticks(x)
        ax.set_xticklabels([regime_label(r, short=True) for r in REGIME_ORDER], fontsize=TICK_SIZE - 1.5)
        ax.set_ylim(0, 1.05)
        style_axes(ax, title=dataset_label(ds))
        if i == 0:
            ax.set_ylabel("Conditional BM25\nweight share")
    fig.legend(loc="upper center", bbox_to_anchor=(0.5, 1.14), ncol=2, frameon=False, fontsize=BASE_SIZE)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    savefig(fig, str(HERE / "fig2_bm25_share"))


# ---------------------------------------------------------------------------
# Figure 3: Calibrated cyclicity by dataset x regime (grouped bars)
# ---------------------------------------------------------------------------
def fig3_cyclicity_primary():
    df = pd.read_csv(TABLES / "full_structural_results.csv")
    sub = df[df["protocol"] == PRIMARY]
    fig, ax = plt.subplots(figsize=(3.35, 2.4))
    width = 0.19
    x = _regime_x()
    for j, ds in enumerate(DATASET_ORDER):
        vals = [sub[(sub.dataset == ds) & (sub.regime == r)]["cyclic_query_pct"].iloc[0] * 100 for r in REGIME_ORDER]
        ax.bar(x + (j - 1.5) * width, vals, width, color=dataset_color(ds), label=dataset_label(ds))
    ax.set_xticks(x)
    ax.set_xticklabels([regime_label(r) for r in REGIME_ORDER], fontsize=TICK_SIZE - 0.5)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Cyclic queries (%)")
    style_axes(ax, title="Cyclicity by regime, primary normalized protocol")
    ax.legend(loc="upper left", ncol=1, fontsize=ANNOT_SIZE - 0.5, handlelength=1.2, borderaxespad=0.3)
    fig.tight_layout()
    savefig(fig, str(HERE / "fig3_cyclicity_primary"))


# ---------------------------------------------------------------------------
# Figure 4: Raw vs calibrated cyclicity, small multiples per dataset
# ---------------------------------------------------------------------------
def fig4_raw_vs_calibrated_structure():
    df = pd.read_csv(TABLES / "full_structural_results.csv")
    fig, axes = plt.subplots(1, 4, figsize=(7.0, 2.1), sharey=True)
    width = 0.34
    x = _regime_x()
    for i, ds in enumerate(DATASET_ORDER):
        ax = axes[i]
        sub = df[df["dataset"] == ds]
        raw_vals = [sub[(sub.protocol == RAW) & (sub.regime == r)]["cyclic_query_pct"].iloc[0] * 100 for r in REGIME_ORDER]
        cal_vals = [sub[(sub.protocol == PRIMARY) & (sub.regime == r)]["cyclic_query_pct"].iloc[0] * 100 for r in REGIME_ORDER]
        ax.bar(x - width / 2, raw_vals, width, color=ROLE_RAW, label="Raw" if i == 0 else None)
        ax.bar(x + width / 2, cal_vals, width, color=ROLE_CALIBRATED, label="Normalized" if i == 0 else None)
        ax.set_xticks(x)
        ax.set_xticklabels([regime_label(r, short=True) for r in REGIME_ORDER], fontsize=TICK_SIZE - 1.5)
        ax.set_ylim(0, 105)
        style_axes(ax, title=dataset_label(ds))
        if i == 0:
            ax.set_ylabel("Cyclic queries (%)")
    fig.legend(loc="upper center", bbox_to_anchor=(0.5, 1.14), ncol=2, frameon=False, fontsize=BASE_SIZE)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    savefig(fig, str(HERE / "fig4_raw_vs_calibrated_structure"))


# ---------------------------------------------------------------------------
# Figure 5: Cyclicity before/after mutual-pair deletion (dumbbell, ms1 only)
# ---------------------------------------------------------------------------
def fig5_cycle_decomposition():
    df = pd.read_csv(TABLES / "full_cycle_decomposition.csv")
    sub = df[(df["protocol"] == PRIMARY) & (df["regime"] == "ms1")]
    fig, ax = plt.subplots(figsize=(3.35, 2.0))
    order = DATASET_ORDER
    ys = np.arange(len(order))
    for y, ds in zip(ys, order):
        row = sub[sub.dataset == ds].iloc[0]
        before = row["cyclic_query_pct"] * 100
        after = row["cyclic_query_pct_after_mutual_deletion"] * 100
        color = dataset_color(ds)
        ax.plot([after, before], [y, y], color=color, lw=2.2, zorder=1, alpha=0.55)
        ax.scatter([before], [y], color=color, s=46, zorder=3, label="Before" if y == 0 else None, marker="o")
        ax.scatter([after], [y], facecolors="white", edgecolors=color, linewidths=1.6, s=46, zorder=3, label="After" if y == 0 else None, marker="o")
        ax.annotate(f"{before:.0f}", (before, y), xytext=(4, 4), textcoords="offset points", fontsize=ANNOT_SIZE, color=color)
        ax.annotate(f"{after:.0f}", (after, y), xytext=(4, -9), textcoords="offset points", fontsize=ANNOT_SIZE, color=color)
    ax.set_yticks(ys)
    ax.set_yticklabels([dataset_label(d) for d in order])
    ax.set_xlim(-3, 105)
    ax.set_xlabel("Cyclic queries (%), one-vote regime")
    style_axes(ax, title="Cyclicity before / after mutual-pair deletion")
    handles = [
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=MUTED_INK, markersize=6, label="Before deletion"),
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor="white", markeredgecolor=MUTED_INK, markersize=6, label="After deletion"),
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=ANNOT_SIZE)
    fig.tight_layout()
    savefig(fig, str(HERE / "fig5_cycle_decomposition"))


# ---------------------------------------------------------------------------
# Figure 6: Normalized FAS weight removed by dataset x regime (grouped bars)
# ---------------------------------------------------------------------------
def fig6_normalized_fas_removed():
    df = pd.read_csv(TABLES / "full_structural_results.csv")
    sub = df[df["protocol"] == PRIMARY]
    fig, ax = plt.subplots(figsize=(3.35, 2.4))
    width = 0.19
    x = _regime_x()
    for j, ds in enumerate(DATASET_ORDER):
        vals = [sub[(sub.dataset == ds) & (sub.regime == r)]["mean_normalized_fas_weight_removed"].iloc[0] for r in REGIME_ORDER]
        ax.bar(x + (j - 1.5) * width, vals, width, color=dataset_color(ds), label=dataset_label(ds))
    ax.set_xticks(x)
    ax.set_xticklabels([regime_label(r) for r in REGIME_ORDER], fontsize=TICK_SIZE - 0.5)
    ax.set_ylim(0, 0.098)
    ax.set_ylabel("Normalized FAS\nweight removed")
    style_axes(ax, title="Repair activity by regime, primary normalized protocol")
    ax.legend(loc="upper left", ncol=1, fontsize=ANNOT_SIZE - 0.5, handlelength=1.2, borderaxespad=0.3)
    fig.tight_layout()
    savefig(fig, str(HERE / "fig6_normalized_fas_removed"))


# ---------------------------------------------------------------------------
# Figure 7: Repaired-minus-unrepaired forest plot, all pairs x regimes,
# faceted by dataset, with a prominent zero line.
# ---------------------------------------------------------------------------
PAIR_LABELS = {
    "copeland_graph": "Copeland graph",
    "copeland_hybrid": "Copeland hybrid",
    "balance_graph": "Balance graph",
    "balance_hybrid": "Balance hybrid",
    "markov_graph": "Markov graph",
}
PAIR_ORDER = ["copeland_graph", "copeland_hybrid", "balance_graph", "balance_hybrid", "markov_graph"]


def _fig7_panel(ax, dsub, rows, ys, row_label_fn, xlabel, title):
    for y, key in zip(ys, rows):
        row = dsub[dsub["_row_key"] == key]
        if row.empty:
            continue
        row = row.iloc[0]
        mean = row["mean_delta_ndcg"]
        lo, hi = row["bootstrap_ci_low"], row["bootstrap_ci_high"]
        color = sign_color(mean)
        ax.plot([lo, hi], [y, y], color=color, lw=1.6, solid_capstyle="round", zorder=2)
        ax.scatter([mean], [y], color=color, s=22, zorder=3)
    ax.axvline(0, color=ZERO_LINE, lw=1.1, zorder=1)
    ax.set_yticks(ys)
    style_axes(ax, title=title, xlabel=xlabel)
    ax.tick_params(axis="x", labelsize=6.3)
    ax.set_xticks([-0.05, 0, 0.05])
    ax.set_xlim(-0.065, 0.065)


def fig7_bootstrap_forest():
    """Main-paper figure: only the active one-vote (ms1) rows, one panel per
    dataset, 5 method pairs each. The zero-effect ms2/ms1_drop_mutual regimes
    are summarized in the surrounding prose and Table 5 rather than plotted
    here (see fig7_bootstrap_forest_full15 for the complete 15-row grid)."""
    df = pd.read_csv(TABLES / "full_statistical_tests.csv")
    sub = df[(df["protocol"] == PRIMARY) & (df["regime"] == "ms1")].copy()
    sub["_row_key"] = sub["pair_name"]
    rows = PAIR_ORDER
    ys = np.arange(len(rows))[::-1]
    fig, axes = plt.subplots(1, 4, figsize=(7.0, 1.9), sharex=True)
    for i, ds in enumerate(DATASET_ORDER):
        ax = axes[i]
        _fig7_panel(ax, sub[sub.dataset == ds], rows, ys, None, "Δ nDCG", dataset_label(ds))
        if i == 0:
            ax.set_yticklabels([PAIR_LABELS[p] for p in rows], fontsize=7.2)
        else:
            ax.set_yticklabels([])
        ax.set_ylim(-1, len(rows))
    fig.suptitle("Repaired − unrepaired ΔnDCG, one-vote regime, 95% bootstrap CI (primary normalized protocol)", x=0.02, ha="left", fontsize=BASE_SIZE, y=1.06)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    savefig(fig, str(HERE / "fig7_bootstrap_forest"))


def fig7_bootstrap_forest_full15():
    """Supplementary artifact: complete 15-row grid (3 regimes x 5 pairs),
    not included in the main paper. Kept for readers who want the full
    zero-effect regimes visualized rather than summarized in prose."""
    df = pd.read_csv(TABLES / "full_statistical_tests.csv")
    sub = df[df["protocol"] == PRIMARY].copy()
    sub["_row_key"] = list(zip(sub["regime"], sub["pair_name"]))
    rows = [(r, p) for r in REGIME_ORDER for p in PAIR_ORDER]
    ys = np.arange(len(rows))[::-1]
    fig, axes = plt.subplots(1, 4, figsize=(7.0, 3.3), sharex=True)
    for i, ds in enumerate(DATASET_ORDER):
        ax = axes[i]
        _fig7_panel(ax, sub[sub.dataset == ds], rows, ys, None, "Δ nDCG", dataset_label(ds))
        if i == 0:
            labels = [f"{PAIR_LABELS[p]} – {regime_label(r, inline=True)}" for r, p in rows]
            ax.set_yticklabels(labels, fontsize=5.6)
        else:
            ax.set_yticklabels([])
        ax.set_ylim(-1, len(rows))
    fig.suptitle("Repaired − unrepaired ΔnDCG, all regimes, 95% bootstrap CI (primary normalized protocol) — supplementary, full 15-row grid", x=0.02, ha="left", fontsize=BASE_SIZE, y=1.02)
    fig.tight_layout()
    savefig(fig, str(HERE / "fig7_bootstrap_forest_full15"))


# ---------------------------------------------------------------------------
# Figure 8: Influence sensitivity, compact side-by-side lollipop/step plot
# ---------------------------------------------------------------------------
def fig8_influence():
    df = pd.read_csv(TABLES / "full_influence_removal_summary.csv")
    sub = df[(df["protocol"] == PRIMARY) & (df["regime"] == "ms1") & (df["pair_name"] == "copeland_hybrid")]
    stats = pd.read_csv(TABLES / "full_statistical_tests.csv")
    stats = stats[(stats["protocol"] == PRIMARY) & (stats["regime"] == "ms1") & (stats["pair_name"] == "copeland_hybrid")]
    fig, axes = plt.subplots(1, 2, figsize=(4.8, 2.1), sharey=False)
    for ax, ds, letter in zip(axes, ["hotpotqa", "scidocs"], "AB"):
        row0_mean = float(stats[stats.dataset == ds]["mean_delta_ndcg"].iloc[0])
        ks = [0] + sub[sub.dataset == ds].sort_values("remove_top_k")["remove_top_k"].tolist()
        means = [row0_mean] + sub[sub.dataset == ds].sort_values("remove_top_k")["remaining_mean_delta_ndcg"].tolist()
        color = dataset_color(ds)
        ax.plot(ks, means, color=color, lw=1.6, zorder=2)
        ax.scatter(ks, means, color=color, s=28, zorder=3)
        ax.axhline(0, color=ZERO_LINE, lw=0.9, zorder=1)
        ax.set_xticks(ks)
        ax.set_xlabel("Top-$k$ influential\nqueries removed")
        if ax is axes[0]:
            ax.set_ylabel("Remaining mean $\\Delta$nDCG")
        style_axes(ax, title=f"({letter}) {dataset_label(ds)}")
        ax.set_ylim(-0.002, 0.019)
        # Exact per-k values are reported in the caption and body text rather
        # than printed on the plot, to avoid label/curve overlap.
    fig.suptitle("Copeland-hybrid, one-vote regime, influence sensitivity", x=0.02, ha="left", fontsize=BASE_SIZE, y=1.14)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    savefig(fig, str(HERE / "fig8_influence"))


# ---------------------------------------------------------------------------
# Figure 9: Raw-vs-calibrated sign-change heatmap (dataset x method-regime)
# ---------------------------------------------------------------------------
def fig9_sign_change_heatmap():
    """Four panels (one per dataset), y = 5 method pairs, x = repaired-minus-
    unrepaired Delta nDCG. One marker for raw, one for normalized, joined by
    a line; named sign flips (Table 8) emphasized in the accent color."""
    raw = pd.read_csv(TABLES / "full_paired_deltas.csv")
    raw = raw[(raw["protocol"] == RAW) & (raw["regime"] == "ms1")]
    raw_agg = raw.groupby(["dataset", "pair_name"])["delta_ndcg"].mean().reset_index()

    cal = pd.read_csv(TABLES / "full_statistical_tests.csv")
    cal = cal[(cal["protocol"] == PRIMARY) & (cal["regime"] == "ms1")]

    # The five cells the manuscript's own Table 8 ("five most consequential
    # sign flips") calls out in prose. Many other cells technically flip sign
    # too, but only at negligible, noise-level magnitude on both sides; this
    # figure highlights exactly the flips the text already discusses rather
    # than re-deriving a new, unstated threshold.
    TABLE8_FLIPS = {
        ("scidocs", "copeland_graph"), ("scidocs", "copeland_hybrid"),
        ("fiqa", "copeland_graph"), ("bright", "copeland_hybrid"),
        ("hotpotqa", "markov_graph"),
    }

    fig, axes = plt.subplots(1, 4, figsize=(7.0, 2.6), sharex=True)
    ys = np.arange(len(PAIR_ORDER))[::-1]
    for i, ds in enumerate(DATASET_ORDER):
        ax = axes[i]
        for y, p in zip(ys, PAIR_ORDER):
            r = raw_agg[(raw_agg.dataset == ds) & (raw_agg.pair_name == p)]
            c = cal[(cal.dataset == ds) & (cal.pair_name == p)]
            rv = float(r["delta_ndcg"].iloc[0]) if not r.empty else np.nan
            cv = float(c["mean_delta_ndcg"].iloc[0]) if not c.empty else np.nan
            flipped = (ds, p) in TABLE8_FLIPS
            line_color = ZERO_LINE if flipped else GRID
            ax.plot([rv, cv], [y, y], color=line_color, lw=2.2 if flipped else 1.3, zorder=2)
            ax.scatter([rv], [y], color=ROLE_RAW, s=24, zorder=3,
                       label="Raw" if (i == 0 and y == ys[0]) else None)
            ax.scatter([cv], [y], color=ROLE_CALIBRATED, s=24, zorder=3,
                       label="Normalized" if (i == 0 and y == ys[0]) else None)
        ax.axvline(0, color=AXIS, lw=1.0, zorder=1)
        ax.set_yticks(ys)
        if i == 0:
            ax.set_yticklabels([PAIR_LABELS[p] for p in PAIR_ORDER], fontsize=7.4)
        else:
            ax.set_yticklabels([])
        ax.set_ylim(-1, len(PAIR_ORDER))
        ax.set_xlim(-0.02, 0.035)
        ax.set_xticks([-0.02, 0, 0.02])
        style_axes(ax, title=dataset_label(ds), xlabel="Δ nDCG")
        ax.tick_params(axis="x", labelsize=6.5)
    fig.legend(loc="upper center", bbox_to_anchor=(0.5, 1.14), ncol=2, frameon=False, fontsize=BASE_SIZE)
    fig.suptitle("Raw versus normalized repaired − unrepaired ΔnDCG (accent line: named sign flip)", x=0.02, ha="left", fontsize=BASE_SIZE, y=1.22)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    savefig(fig, str(HERE / "fig9_sign_change_heatmap"))


# ---------------------------------------------------------------------------
# Figure 10: Per-dataset baseline comparison (grouped bars, ms1 only)
# ---------------------------------------------------------------------------
METHOD_ORDER_FIG10 = [
    "combsum", "rrf", "prior_only", "borda_fuse",
    "hybrid_unrepaired_copeland_a0p3_minmax", "hybrid_repaired_copeland_a0p3_minmax",
    "hybrid_unrepaired_balance_a0p3_minmax", "hybrid_repaired_balance_a0p3_minmax",
    "copeland_graph", "copeland_graph_repaired",
]
METHOD_LABELS_FIG10 = {
    "combsum": "CombSUM", "rrf": "RRF", "prior_only": "Prior", "borda_fuse": "Borda",
    "hybrid_unrepaired_copeland_a0p3_minmax": "Cop. hyb. unrep.",
    "hybrid_repaired_copeland_a0p3_minmax": "Cop. hyb. rep.",
    "hybrid_unrepaired_balance_a0p3_minmax": "Bal. hyb. unrep.",
    "hybrid_repaired_balance_a0p3_minmax": "Bal. hyb. rep.",
    "copeland_graph": "Copeland unrep.", "copeland_graph_repaired": "Copeland rep.",
}
GRAPH_INDEPENDENT = {"combsum", "rrf", "prior_only", "borda_fuse"}


def fig10_baseline_comparison():
    """Horizontal dot plot: method names on the y-axis, mean nDCG@k on the
    x-axis, methods sorted within each dataset panel, no rotated labels.
    Graph-independent baselines use a filled circle; graph-dependent methods
    use an open circle, so the distinction survives grayscale printing."""
    df = pd.read_csv(TABLES / "full_retrieval_results.csv")
    sub = df[(df["protocol"] == PRIMARY) & (df["regime"] == "ms1")]
    fig, axes = plt.subplots(1, 4, figsize=(7.0, 2.7), sharey=False)
    for i, ds in enumerate(DATASET_ORDER):
        ax = axes[i]
        dsub = sub[sub.dataset == ds]
        pairs = [(m, dsub[dsub.method_key == m]["mean_ndcg_at_k"].iloc[0]) for m in METHOD_ORDER_FIG10 if (dsub.method_key == m).any()]
        pairs.sort(key=lambda t: t[1])  # ascending so the best method ends up at the top
        methods_sorted = [m for m, _ in pairs]
        vals = [v for _, v in pairs]
        y = np.arange(len(methods_sorted))
        color = dataset_color(ds)
        for yi, m, v in zip(y, methods_sorted, vals):
            ax.plot([0, v], [yi, yi], color=GRID, lw=1.0, zorder=1)
            if m in GRAPH_INDEPENDENT:
                ax.scatter([v], [yi], color=color, s=32, zorder=3, marker="o")
            else:
                ax.scatter([v], [yi], facecolors="white", edgecolors=color, linewidths=1.5, s=32, zorder=3, marker="o")
        ax.set_yticks(y)
        ax.set_yticklabels([METHOD_LABELS_FIG10[m] for m in methods_sorted], fontsize=6.8)
        vmin = np.nanmin(vals)
        vmax = np.nanmax(vals)
        pad = max(0.01, (vmax - vmin) * 0.15)
        ax.set_xlim(max(0, vmin - pad), vmax + pad)
        style_axes(ax, title=dataset_label(ds), xlabel="Mean nDCG@$k$")
        ax.tick_params(axis="x", labelsize=6.5)
        ax.xaxis.set_major_locator(plt.MaxNLocator(3))
    handles = [
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=MUTED_INK, markersize=6, label="Graph-independent baseline"),
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor="white", markeredgecolor=MUTED_INK, markersize=6, label="Graph-dependent method"),
    ]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 1.16), ncol=2, frameon=False, fontsize=BASE_SIZE)
    fig.suptitle("Per-dataset method comparison, one-vote regime, sorted by mean nDCG@$k$", x=0.02, ha="left", fontsize=BASE_SIZE, y=1.24)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    savefig(fig, str(HERE / "fig10_baseline_comparison"))


# ---------------------------------------------------------------------------
# Figure 11: Alpha sensitivity heatmap (dataset x alpha, Copeland component)
# ---------------------------------------------------------------------------
def fig11_alpha_heatmap():
    df = pd.read_csv(TABLES / "full_alpha_sensitivity.csv")
    sub = df[(df["protocol"] == PRIMARY) & (df["regime"] == "ms1") & (df["component"] == "copeland")]
    alphas = [0.1, 0.3, 0.5, 1.0]
    mat = np.zeros((len(DATASET_ORDER), len(alphas)))
    for i, ds in enumerate(DATASET_ORDER):
        for j, a in enumerate(alphas):
            row = sub[(sub.dataset == ds) & (np.isclose(sub.alpha, a))]
            mat[i, j] = row["mean_delta_ndcg"].iloc[0]

    vmax = np.abs(mat).max()
    fig, ax = plt.subplots(figsize=(3.35, 2.3))
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("puor", [DIVERGING_NEG, DIVERGING_NEUTRAL, DIVERGING_POS])
    im = ax.imshow(mat, cmap=cmap, vmin=-vmax, vmax=vmax, aspect="auto")
    for i in range(len(DATASET_ORDER)):
        for j in range(len(alphas)):
            val = mat[i, j]
            txt_color = "white" if abs(val) > vmax * 0.6 else INK
            ax.text(j, i, f"{val:+.4f}", ha="center", va="center", fontsize=7, color=txt_color)
    ax.set_xticks(range(len(alphas)))
    ax.set_xticklabels([f"$\\alpha={a}$" for a in alphas])
    ax.set_yticks(range(len(DATASET_ORDER)))
    ax.set_yticklabels([dataset_label(d) for d in DATASET_ORDER])
    ax.set_title("Copeland-hybrid $\\alpha$ sensitivity, ms1", loc="left", fontsize=9.5, fontweight="bold", pad=8)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    cbar = fig.colorbar(im, ax=ax, fraction=0.05, pad=0.04)
    cbar.set_label("Repaired − unrepaired $\\Delta$nDCG", fontsize=ANNOT_SIZE)
    cbar.ax.tick_params(labelsize=6.5)
    fig.tight_layout()
    savefig(fig, str(HERE / "fig11_alpha_heatmap"))


if __name__ == "__main__":
    fig2_bm25_share()
    fig3_cyclicity_primary()
    fig4_raw_vs_calibrated_structure()
    fig5_cycle_decomposition()
    fig6_normalized_fas_removed()
    fig7_bootstrap_forest()
    fig7_bootstrap_forest_full15()  # supplementary artifact, not used in main.tex
    fig8_influence()
    fig9_sign_change_heatmap()
    fig10_baseline_comparison()
    fig11_alpha_heatmap()  # kept for reference; not included in main.tex (duplicates Table 10)
    print("All figures written to", HERE)
