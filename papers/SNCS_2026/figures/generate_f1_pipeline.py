#!/usr/bin/env python3
"""F1: publication-quality pipeline schematic (dual repair branches).

Journal-style flow diagram for SN Computer Science single-column width.
Schematic only; no data values.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from style import (  # noqa: E402
    COL_WIDTH_IN,
    INK,
    MUTED_INK,
    apply_style,
    savefig,
)

apply_style()

C_DATA = "#4C78A8"
C_PROC = "#59A14F"
C_DIAG = "#B07AA1"
C_REPAIR = "#C44E52"
C_PANEL = "#F3F3F3"
C_PANEL_EDGE = "#B0B0B0"

PRE = [
    ("Stored\nscores", C_DATA),
    ("Normalize", C_PROC),
    ("Pairwise\nvotes", C_PROC),
    ("Graph\n$G_q$", C_DATA),
    ("Cycle\ndiagnostics", C_DIAG),
]
POST = [
    ("Rank\nextraction", C_PROC),
    ("nDCG &\npaired tests", C_DIAG),
]
REPAIR = [
    ("Greedy\nrepair", C_REPAIR),
    ("Exact SCIP\nrepair", C_REPAIR),
]

W = COL_WIDTH_IN
H = 2.70
BOX_W = 0.52
BOX_H = 0.58
GAP = 0.095
X0 = 0.05
Y_MAIN = 1.45
Y_GREEDY = 1.88
Y_EXACT = 0.88

fig, ax = plt.subplots(figsize=(W, H))
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")


def box(x, y, text, color, *, fs=6.8):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            BOX_W,
            BOX_H,
            boxstyle="square,pad=0.0",
            linewidth=1.0,
            edgecolor=color,
            facecolor="white",
            mutation_aspect=1,
        )
    )
    ax.add_patch(Rectangle((x, y), 0.035, BOX_H, facecolor=color, edgecolor="none"))
    ax.text(
        x + BOX_W / 2 + 0.01,
        y + BOX_H / 2,
        text,
        ha="center",
        va="center",
        fontsize=fs,
        color=INK,
        linespacing=1.2,
    )


def arrow(x0, y0, x1, y1):
    ax.add_patch(
        FancyArrowPatch(
            (x0, y0),
            (x1, y1),
            arrowstyle="-|>",
            mutation_scale=8,
            linewidth=0.9,
            color=MUTED_INK,
            shrinkA=0.4,
            shrinkB=0.4,
        )
    )


xs_pre = [X0 + i * (BOX_W + GAP) for i in range(len(PRE))]
for i, (lab, col) in enumerate(PRE):
    box(xs_pre[i], Y_MAIN, lab, col)
    if i < len(PRE) - 1:
        arrow(xs_pre[i] + BOX_W, Y_MAIN + BOX_H / 2, xs_pre[i + 1], Y_MAIN + BOX_H / 2)

ax.text(
    (xs_pre[0] + xs_pre[-1] + BOX_W) / 2,
    Y_MAIN + BOX_H + 0.12,
    "Shared construction path",
    ha="center",
    va="bottom",
    fontsize=6.8,
    color=MUTED_INK,
)

x_rep = xs_pre[-1] + BOX_W + GAP + 0.03
panel_x = x_rep - 0.05
panel_w = BOX_W + 0.10
panel_y = Y_EXACT - 0.34
panel_h = (Y_GREEDY + BOX_H + 0.10) - panel_y
ax.add_patch(
    FancyBboxPatch(
        (panel_x, panel_y),
        panel_w,
        panel_h,
        boxstyle="square,pad=0.0",
        linewidth=0.8,
        edgecolor=C_PANEL_EDGE,
        facecolor=C_PANEL,
        zorder=0,
    )
)
ax.text(
    panel_x + panel_w / 2,
    Y_GREEDY + BOX_H + 0.05,
    "Repair",
    ha="center",
    va="bottom",
    fontsize=6.8,
    fontweight="bold",
    color=INK,
)

box(x_rep, Y_GREEDY, REPAIR[0][0], C_REPAIR)
box(x_rep, Y_EXACT, REPAIR[1][0], C_REPAIR)

yc = Y_MAIN + BOX_H / 2
arrow(xs_pre[-1] + BOX_W, yc, x_rep, Y_GREEDY + BOX_H / 2)
arrow(xs_pre[-1] + BOX_W, yc, x_rep, Y_EXACT + BOX_H / 2)

ax.text(
    panel_x + panel_w / 2,
    panel_y + 0.05,
    "Exact repair: diagnostic\ncontrol, not a replacement",
    ha="center",
    va="bottom",
    fontsize=5.6,
    color=MUTED_INK,
    linespacing=1.15,
)

xs_post = [x_rep + BOX_W + GAP + 0.04 + i * (BOX_W + GAP) for i in range(len(POST))]
assert xs_post[-1] + BOX_W <= W - 0.03, (xs_post[-1] + BOX_W, W)

for i, (lab, col) in enumerate(POST):
    box(xs_post[i], Y_MAIN, lab, col)
    if i < len(POST) - 1:
        arrow(xs_post[i] + BOX_W, yc, xs_post[i + 1], yc)

arrow(x_rep + BOX_W, Y_GREEDY + BOX_H / 2, xs_post[0], yc)
arrow(x_rep + BOX_W, Y_EXACT + BOX_H / 2, xs_post[0], yc)

ax.text(
    (xs_post[0] + xs_post[-1] + BOX_W) / 2,
    Y_MAIN + BOX_H + 0.12,
    "Shared extraction & evaluation",
    ha="center",
    va="bottom",
    fontsize=6.8,
    color=MUTED_INK,
)

key_y = 0.14
key_x = X0
for lab, col in (
    ("Data", C_DATA),
    ("Process", C_PROC),
    ("Diagnostic", C_DIAG),
    ("Repair", C_REPAIR),
):
    ax.add_patch(Rectangle((key_x, key_y), 0.12, 0.09, facecolor=col, edgecolor="none"))
    ax.text(key_x + 0.16, key_y + 0.045, lab, ha="left", va="center", fontsize=6.2, color=INK)
    key_x += 0.88

savefig(fig, str(HERE / "f1_pipeline"))
print("F1 written; right edge", round(xs_post[-1] + BOX_W, 3))
