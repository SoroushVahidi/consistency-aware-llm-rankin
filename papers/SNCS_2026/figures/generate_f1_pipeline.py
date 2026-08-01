#!/usr/bin/env python3
"""F1: pipeline/audit schematic with a dual (greedy + exact) repair branch.

Adapts papers/JDIQ_2026/manuscript/figures_v2/generate_figure1.py's single
"Optional greedy repair" box into two parallel, co-equal boxes (greedy and
exact SCIP repair), per papers/SNCS_2026/figure_prompts/f1_pipeline_dual_repair.md.
Purely schematic; no underlying data table.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from style import apply_style, INK, MUTED_INK, savefig  # noqa: E402

apply_style()

DATA_COLOR = "#0072B2"
PROCESS_COLOR = "#009E73"
EVAL_COLOR = "#E69F00"
ABLATION_COLOR = "#8A8A8A"

# Linear stages before and after the repair branch point.
PRE_STAGES = [
    ("Stored ranker\nscores", DATA_COLOR),
    ("Per-query,\nper-ranker\nnormalization", PROCESS_COLOR),
    ("Pairwise vote\nextraction &\nthresholding", PROCESS_COLOR),
    ("Preference\ngraph $G_q$\n(regime $r$)", DATA_COLOR),
    ("Mutual-pair,\nSCC & FAS\ndiagnostics", EVAL_COLOR),
]
POST_STAGES = [
    ("Ranking\nextraction", PROCESS_COLOR),
    ("nDCG\nevaluation &\npaired tests", EVAL_COLOR),
]
REPAIR_BRANCHES = [
    "Greedy repair\n(cycle-peeling)",
    "Exact repair\n(SCIP MWFAS)",
]

BOX_W = 1.28
BOX_H = 1.05
GAP = 0.30
BRANCH_GAP_Y = 0.28
X0 = 0.2
Y0 = 1.55

n_pre = len(PRE_STAGES)
n_post = len(POST_STAGES)

fig, ax = plt.subplots(figsize=(6.2, 3.0))

xs_pre = [X0 + i * (BOX_W + GAP) for i in range(n_pre)]
x_repair = xs_pre[-1] + BOX_W + GAP
xs_post = [x_repair + BOX_W + GAP + i * (BOX_W + GAP) for i in range(n_post)]

total_w = xs_post[-1] + BOX_W + X0
ax.set_xlim(0, total_w)
ax.set_ylim(0.05, 3.55)
ax.axis("off")


def draw_box(x, y, label, color):
    box = FancyBboxPatch(
        (x, y), BOX_W, BOX_H,
        boxstyle="round,pad=0.02,rounding_size=0.09",
        linewidth=1.3, edgecolor=color, facecolor=color, alpha=0.14,
        mutation_aspect=1,
    )
    ax.add_patch(box)
    accent = FancyBboxPatch(
        (x, y + BOX_H - 0.11), BOX_W, 0.11,
        boxstyle="round,pad=0.0,rounding_size=0.06",
        linewidth=0, facecolor=color, alpha=0.95,
    )
    ax.add_patch(accent)
    ax.text(x + BOX_W / 2, y + BOX_H / 2 - 0.05, label, ha="center", va="center",
            fontsize=7.3, color=INK, linespacing=1.35)


def draw_arrow(x_from, y_from, x_to, y_to):
    arrow = FancyArrowPatch(
        (x_from, y_from), (x_to, y_to),
        arrowstyle="-|>", mutation_scale=11, linewidth=1.3, color=MUTED_INK,
        shrinkA=1, shrinkB=1,
    )
    ax.add_patch(arrow)


# Pre-repair linear stages.
for i, (label, color) in enumerate(PRE_STAGES):
    x = xs_pre[i]
    draw_box(x, Y0, label, color)
    if i < n_pre - 1:
        draw_arrow(x + BOX_W, Y0 + BOX_H / 2, x + BOX_W + GAP, Y0 + BOX_H / 2)

# Branch point: diagnostics box feeds both repair boxes.
y_greedy = Y0 + (BOX_H + BRANCH_GAP_Y) / 2
y_exact = Y0 - (BOX_H + BRANCH_GAP_Y) / 2
last_pre_x = xs_pre[-1]
draw_box(x_repair, y_greedy, REPAIR_BRANCHES[0], PROCESS_COLOR)
draw_box(x_repair, y_exact, REPAIR_BRANCHES[1], PROCESS_COLOR)
draw_arrow(last_pre_x + BOX_W, Y0 + BOX_H / 2, x_repair, y_greedy + BOX_H / 2)
draw_arrow(last_pre_x + BOX_W, Y0 + BOX_H / 2, x_repair, y_exact + BOX_H / 2)

# Both branches converge back into the extraction stage.
for y_branch in (y_greedy, y_exact):
    draw_arrow(x_repair + BOX_W, y_branch + BOX_H / 2, xs_post[0], Y0 + BOX_H / 2)

# Post-repair linear stages.
for i, (label, color) in enumerate(POST_STAGES):
    x = xs_post[i]
    draw_box(x, Y0, label, color)
    if i < n_post - 1:
        draw_arrow(x + BOX_W, Y0 + BOX_H / 2, x + BOX_W + GAP, Y0 + BOX_H / 2)

# Legend.
legend_items = [
    ("Data / artifact", DATA_COLOR),
    ("Processing step", PROCESS_COLOR),
    ("Diagnostic / evaluation", EVAL_COLOR),
]
lx = X0
ly = 3.30
for label, color in legend_items:
    ax.add_patch(plt.Rectangle((lx, ly - 0.07), 0.22, 0.16, facecolor=color, alpha=0.85, edgecolor="none"))
    ax.text(lx + 0.30, ly + 0.01, label, fontsize=7.6, va="center", color=INK)
    lx += 0.24 + 0.13 * len(label) + 0.35

# Diagnostic-control note next to the two repair boxes.
ax.text(
    x_repair + BOX_W / 2, y_exact - 0.22,
    "Exact repair is a diagnostic control on greedy repair,\nnot a proposed replacement.",
    ha="center", va="top", fontsize=6.8, color=ABLATION_COLOR, style="italic", linespacing=1.3,
)

# Raw-margin ablation annotation (unchanged from the original figure).
ax.annotate(
    "", xy=(xs_pre[2] + BOX_W * 0.15, Y0 - 0.02), xytext=(xs_pre[0] + BOX_W * 0.85, Y0 - 0.02),
    arrowprops=dict(arrowstyle="-|>", linestyle=(0, (4, 2)), color=ABLATION_COLOR, lw=1.3,
                    connectionstyle="arc3,rad=-0.25"),
)
ax.text(
    (xs_pre[0] + xs_pre[2]) / 2 + BOX_W / 2, Y0 - 0.20,
    "Raw-margin ablation: skips per-ranker normalization,\nuses fixed historical thresholds — identical pipeline otherwise.",
    ha="center", va="top", fontsize=6.8, color=ABLATION_COLOR, style="italic", linespacing=1.3,
)

fig.tight_layout()
savefig(fig, str(HERE / "f1_pipeline"))
print("F1 written")
