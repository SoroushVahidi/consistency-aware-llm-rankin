#!/usr/bin/env python3
"""Figure 1: a professionally designed pipeline diagram (vector), replacing
the old boxed-text figure. Purely schematic -- no underlying data table."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from style import apply_style, INK, MUTED_INK, savefig  # noqa: E402

apply_style()

DATA_COLOR = "#0072B2"
PROCESS_COLOR = "#009E73"
EVAL_COLOR = "#E69F00"
ABLATION_COLOR = "#8A8A8A"

STAGES = [
    ("Stored ranker\nscores", DATA_COLOR, "data"),
    ("Per-query,\nper-ranker\nnormalization", PROCESS_COLOR, "process"),
    ("Pairwise vote\nextraction &\nthresholding", PROCESS_COLOR, "process"),
    ("Preference\ngraph $G_q$\n(regime $r$)", DATA_COLOR, "data"),
    ("Mutual-pair,\nSCC & FAS\ndiagnostics", EVAL_COLOR, "diagnostic"),
    ("Optional\ngreedy\nrepair", PROCESS_COLOR, "process"),
    ("Ranking\nextraction &\nhybrid fusion", PROCESS_COLOR, "process"),
    ("nDCG\nevaluation &\npaired tests", EVAL_COLOR, "eval"),
]

N = len(STAGES)
BOX_W = 1.28
BOX_H = 1.05
GAP = 0.30
X0 = 0.2
Y0 = 1.55

fig, ax = plt.subplots(figsize=(7.0, 2.05))
ax.set_xlim(0, X0 * 2 + N * BOX_W + (N - 1) * GAP)
ax.set_ylim(0.55, 3.35)
ax.axis("off")

xs = []
for i, (label, color, kind) in enumerate(STAGES):
    x = X0 + i * (BOX_W + GAP)
    xs.append(x)
    box = FancyBboxPatch(
        (x, Y0), BOX_W, BOX_H,
        boxstyle="round,pad=0.02,rounding_size=0.09",
        linewidth=1.3, edgecolor=color, facecolor=color, alpha=0.14,
        mutation_aspect=1,
    )
    ax.add_patch(box)
    # top accent bar to reinforce category color without relying on fill alone
    accent = FancyBboxPatch(
        (x, Y0 + BOX_H - 0.11), BOX_W, 0.11,
        boxstyle="round,pad=0.0,rounding_size=0.06",
        linewidth=0, facecolor=color, alpha=0.95,
    )
    ax.add_patch(accent)
    ax.text(x + BOX_W / 2, Y0 + BOX_H / 2 - 0.05, label, ha="center", va="center",
            fontsize=7.3, color=INK, linespacing=1.35)
    if i < N - 1:
        arrow = FancyArrowPatch(
            (x + BOX_W, Y0 + BOX_H / 2), (x + BOX_W + GAP, Y0 + BOX_H / 2),
            arrowstyle="-|>", mutation_scale=11, linewidth=1.3, color=MUTED_INK,
            shrinkA=1, shrinkB=1,
        )
        ax.add_patch(arrow)

# Legend for category colors
legend_items = [
    ("Data / artifact", DATA_COLOR),
    ("Processing step", PROCESS_COLOR),
    ("Diagnostic / evaluation", EVAL_COLOR),
]
lx = X0
ly = 2.95
for label, color in legend_items:
    ax.add_patch(plt.Rectangle((lx, ly - 0.07), 0.22, 0.16, facecolor=color, alpha=0.85, edgecolor="none"))
    ax.text(lx + 0.30, ly + 0.01, label, fontsize=7.6, va="center", color=INK)
    lx += 0.24 + 0.13 * len(label) + 0.35

# Raw-margin ablation annotation: dashed alternate path bypassing normalization
ax.annotate(
    "", xy=(xs[2] + BOX_W * 0.15, Y0 - 0.02), xytext=(xs[0] + BOX_W * 0.85, Y0 - 0.02),
    arrowprops=dict(arrowstyle="-|>", linestyle=(0, (4, 2)), color=ABLATION_COLOR, lw=1.3,
                    connectionstyle="arc3,rad=-0.25"),
)
ax.text(
    (xs[0] + xs[2]) / 2 + BOX_W / 2, Y0 - 0.62,
    "Raw-margin ablation: skips per-ranker normalization,\nuses fixed historical thresholds — identical pipeline otherwise.",
    ha="center", va="top", fontsize=6.8, color=ABLATION_COLOR, style="italic", linespacing=1.3,
)

fig.tight_layout()
savefig(fig, str(HERE / "fig1_pipeline"))
print("Figure 1 written")
