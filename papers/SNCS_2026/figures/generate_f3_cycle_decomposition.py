#!/usr/bin/env python3
"""F3: structural inconsistency chart (ms1 cyclic before/after mutual deletion).

Values must match the manuscript structural-outcomes table.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from style import (  # noqa: E402
    COL_WIDTH_IN,
    DATASET_LABELS,
    DATASET_ORDER,
    INK,
    apply_style,
    savefig,
    style_axes,
)

apply_style()

MS1_CYCLIC = {
    "scidocs": 99.2,
    "fiqa": 98.3,
    "hotpotqa": 63.5,
    "bright": 92.0,
}
MS1_POST = {
    "scidocs": 10.8,
    "fiqa": 30.8,
    "hotpotqa": 1.9,
    "bright": 22.0,
}

C_BEFORE = "#4C78A8"
C_AFTER = "#D0D0D0"

fig, ax = plt.subplots(figsize=(COL_WIDTH_IN, 2.20))
x = np.arange(len(DATASET_ORDER))
w = 0.34
before = [MS1_CYCLIC[d] for d in DATASET_ORDER]
after = [MS1_POST[d] for d in DATASET_ORDER]

b1 = ax.bar(x - w / 2, before, width=w, color=C_BEFORE, edgecolor="none", label="Before mutual deletion", zorder=3)
b2 = ax.bar(
    x + w / 2,
    after,
    width=w,
    color=C_AFTER,
    edgecolor="#888888",
    linewidth=0.6,
    label="After mutual deletion",
    zorder=3,
)

for bars in (b1, b2):
    for rect in bars:
        h = rect.get_height()
        ax.text(
            rect.get_x() + rect.get_width() / 2,
            h + 1.2,
            f"{h:.1f}",
            ha="center",
            va="bottom",
            fontsize=6.4,
            color=INK,
        )

ax.set_xticks(x)
ax.set_xticklabels([DATASET_LABELS[d] for d in DATASET_ORDER])
ax.set_ylabel("Cyclic queries (%)")
ax.set_ylim(0, 115)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.18), ncol=2, frameon=False, fontsize=6.6)
style_axes(ax)
ax.grid(axis="y", color="#EEEEEE", linewidth=0.55)
ax.grid(axis="x", visible=False)
ax.set_axisbelow(True)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

savefig(fig, str(HERE / "f3_cycle_decomposition"))
print("F3 written")
