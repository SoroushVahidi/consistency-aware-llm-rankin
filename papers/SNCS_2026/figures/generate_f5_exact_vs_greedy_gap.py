#!/usr/bin/env python3
"""F5 (appendix): exact-vs-greedy structural gap (mean feedback-arc weight
removed), per dataset, on the cyclic-query subset only.

Data source (read directly, not hand-copied):
reports/exact_open_source_ilp_repair_investigation/tables/structural_per_query.csv,
filtered to is_cyclic_pre_repair == True and pooled across all three
vote-construction regimes (matching the scope of
reports/exact_open_source_ilp_repair_investigation/FINDINGS.md's own
per-dataset structural-gap table -- verified by reproducing FINDINGS.md's
reported per-dataset n and mean-weight-removed values before generating
this figure; see papers/SNCS_2026/RESULTS_CROSS_CHECK.md item on F5).
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from style import apply_style, DATASET_ORDER, DATASET_LABELS, DATASET_COLORS, INK, MUTED_INK, savefig  # noqa: E402

apply_style()

SRC = (
    REPO_ROOT
    / "reports"
    / "exact_open_source_ilp_repair_investigation"
    / "tables"
    / "structural_per_query.csv"
)

df = pd.read_csv(SRC)
cyc = df[df["is_cyclic_pre_repair"] == True]  # noqa: E712

rows = []
for ds in DATASET_ORDER:
    sub = cyc[cyc["dataset"] == ds]
    rows.append(
        {
            "dataset": ds,
            "n": len(sub),
            "greedy": sub["greedy_weight_removed"].mean(),
            "exact": sub["ilp_weight_removed"].mean(),
        }
    )
summary = pd.DataFrame(rows)
print(summary.to_string(index=False))

fig, ax = plt.subplots(figsize=(5.0, 2.9))

x = np.arange(len(DATASET_ORDER))
width = 0.32

for i, ds in enumerate(DATASET_ORDER):
    row = summary.iloc[i]
    color = DATASET_COLORS[ds]
    ax.bar(
        x[i] - width / 2, row["greedy"], width,
        color=color, alpha=0.55, edgecolor=INK, linewidth=0.6,
        hatch="//", label="Greedy" if i == 0 else None,
    )
    ax.bar(
        x[i] + width / 2, row["exact"], width,
        color=color, alpha=0.95, edgecolor=INK, linewidth=0.6,
        label="Exact (SCIP)" if i == 0 else None,
    )

ax.set_xticks(x)
ax.set_xticklabels([DATASET_LABELS[d] for d in DATASET_ORDER])
ax.set_ylabel("Mean feedback-arc\nweight removed\n(cyclic queries only)")
ax.legend(loc="upper right", ncol=1)

for i, ds in enumerate(DATASET_ORDER):
    row = summary.iloc[i]
    pct_less = (1 - row["exact"] / row["greedy"]) * 100
    ax.text(
        x[i], max(row["greedy"], row["exact"]) + 0.35,
        f"-{pct_less:.0f}%", ha="center", va="bottom", fontsize=6.8, color=MUTED_INK,
    )

ax.set_ylim(0, summary[["greedy", "exact"]].to_numpy().max() * 1.28)

fig.text(
    0.02, -0.02,
    "Exact repair consistently removes less total weight than greedy on the same graphs;\n"
    "both reach the same retrieval-level conclusion (no repaired-vs-unrepaired nDCG gain\n"
    "survives Holm correction under either repair method).",
    ha="left", va="top", fontsize=6.6, color=MUTED_INK, style="italic", linespacing=1.3,
)

fig.tight_layout(rect=(0, 0.08, 1, 1))
savefig(fig, str(HERE / "f5_exact_vs_greedy_gap"))
print("F5 written")
