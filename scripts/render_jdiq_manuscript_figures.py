#!/usr/bin/env python3
"""Render standalone JDIQ manuscript figures 1 and 3 reproducibly.

Figure 1 is a repository-native workflow diagram constructed from the exact
terminology used in the manuscript. Figure 3 is rendered from the canonical
BEW pre/post summary table without reading any existing raster manuscript
figure.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patches


REPO_ROOT = Path(__file__).resolve().parent.parent
FIGURE_DIR = REPO_ROOT / "figures" / "manuscript"
BEW_SOURCE = REPO_ROOT / "outputs" / "pub_vote_cmp_all4" / "paper_package" / "tables" / "table_consistency_qrels_bew.csv"

DATASET_ORDER = ("scidocs", "fiqa", "hotpotqa", "bright")
DATASET_LABELS = {
    "scidocs": "SciDocs",
    "fiqa": "FiQA",
    "hotpotqa": "HotpotQA",
    "bright": "BRIGHT",
}
VARIANT_ORDER = ("ms2", "ms1", "ms1_drop_mutual")
VARIANT_LABELS = {
    "ms2": "ms2",
    "ms1": "ms1",
    "ms1_drop_mutual": "ms1+drop",
}


@dataclass(frozen=True)
class BewRow:
    dataset: str
    variant: str
    mean_bew_pre: float
    mean_bew_post: float


def _configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.labelsize": 11,
            "legend.fontsize": 11,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def _save_all(fig: plt.Figure, stem: str, *, dpi: int = 300) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    for suffix, kwargs in {
        ".svg": {},
        ".pdf": {},
        ".png": {"dpi": dpi},
    }.items():
        fig.savefig(
            FIGURE_DIR / f"{stem}{suffix}",
            bbox_inches="tight",
            pad_inches=0.06,
            facecolor="white",
            **kwargs,
        )
    plt.close(fig)


def _draw_box(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    lines: list[str],
    *,
    facecolor: str,
    edgecolor: str = "#334155",
    fontsize: int = 15,
    line_spacing: float = 0.34,
) -> None:
    ax.add_patch(
        patches.FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.18",
            linewidth=1.7,
            facecolor=facecolor,
            edgecolor=edgecolor,
        )
    )
    total_height = (len(lines) - 1) * line_spacing
    for idx, line in enumerate(lines):
        ax.text(
            x + w / 2,
            y + h / 2 + total_height / 2 - idx * line_spacing,
            line,
            ha="center",
            va="center",
            fontsize=fontsize,
        )


def render_figure1() -> None:
    fig, ax = plt.subplots(figsize=(16.8, 4.8))
    ax.set_xlim(0, 18.1)
    ax.set_ylim(0, 4.6)
    ax.axis("off")

    colors = {
        "warm": "#FFF6D8",
        "lavender": "#F3EEFF",
        "mint": "#EFFAF1",
        "rose": "#FFF0EE",
        "cool": "#F4F8FF",
    }

    boxes = {
        "upstream": (0.45, 2.45, 2.70, 1.35),
        "vote": (3.55, 2.45, 2.70, 1.35),
        "graph": (6.70, 2.45, 2.85, 1.35),
        "repair": (9.95, 2.45, 3.15, 1.35),
        "rank": (13.55, 2.45, 2.95, 1.35),
        "ndcg": (16.75, 2.45, 1.15, 1.35),
        "metrics": (4.55, 0.45, 4.35, 1.28),
    }

    _draw_box(
        ax,
        *boxes["upstream"],
        ["Upstream ranker scores", "(BM25, TF-IDF, MiniLM)"],
        facecolor=colors["warm"],
        fontsize=13,
    )
    _draw_box(
        ax,
        *boxes["vote"],
        ["Vote extraction", r"under regime $r$"],
        facecolor=colors["warm"],
        fontsize=13,
    )
    _draw_box(
        ax,
        *boxes["graph"],
        [r"Preference graph $G_q$"],
        facecolor=colors["lavender"],
        fontsize=13,
    )
    _draw_box(
        ax,
        *boxes["repair"],
        ["Optional FAS repair", r"$G_q \;\rightarrow\; \widetilde{G}_q$"],
        facecolor=colors["mint"],
        fontsize=13,
    )
    _draw_box(
        ax,
        *boxes["rank"],
        ["Ranking extraction", "Copeland / balance /", "hybrid"],
        facecolor=colors["rose"],
        fontsize=13,
        line_spacing=0.30,
    )
    _draw_box(
        ax,
        *boxes["ndcg"],
        ["nDCG", "eval."],
        facecolor=colors["warm"],
        fontsize=13,
    )
    _draw_box(
        ax,
        *boxes["metrics"],
        ["Structural metrics", "cyclicity, SCC, BEW, PIC"],
        facecolor=colors["cool"],
        fontsize=13,
    )

    arrow = dict(arrowstyle="-|>", lw=1.8, color="#334155", shrinkA=0, shrinkB=0, mutation_scale=18)

    def right_center(name: str) -> tuple[float, float]:
        x, y, w, h = boxes[name]
        return x + w, y + h / 2

    def left_center(name: str) -> tuple[float, float]:
        x, y, _, h = boxes[name]
        return x, y + h / 2

    for start, end in [
        ("upstream", "vote"),
        ("vote", "graph"),
        ("graph", "repair"),
        ("repair", "rank"),
        ("rank", "ndcg"),
    ]:
        ax.annotate("", xy=left_center(end), xytext=right_center(start), arrowprops=arrow)

    gx, gy, gw, gh = boxes["graph"]
    mx, my, mw, mh = boxes["metrics"]
    ax.annotate(
        "",
        xy=(mx + mw * 0.42, my + mh),
        xytext=(gx + gw * 0.22, gy),
        arrowprops=arrow,
    )

    # Small preference-cycle illustration inside the graph box.
    cycle_y = gy + 0.34
    ax.text(gx + 0.78, cycle_y, r"$v$", fontsize=16, color="#111827", ha="center", va="center")
    ax.text(gx + 1.92, cycle_y, r"$w$", fontsize=16, color="#111827", ha="center", va="center")
    ax.annotate(
        "",
        xy=(gx + 1.68, cycle_y),
        xytext=(gx + 1.02, cycle_y),
        arrowprops=dict(arrowstyle="<->", lw=1.7, color="#7C3AED", mutation_scale=18),
    )

    # Dashed unrepaired bypass.
    dashed_color = "#475569"
    x0 = gx + gw * 0.83
    y_top = gy
    y_mid = 1.72
    rank_x, rank_y, rank_w, rank_h = boxes["rank"]
    x1 = rank_x + rank_w * 0.32
    ax.plot([x0, x0], [y_top, y_mid], linestyle=(0, (4, 3)), linewidth=1.9, color=dashed_color)
    ax.plot([x0, x1], [y_mid, y_mid], linestyle=(0, (4, 3)), linewidth=1.9, color=dashed_color)
    ax.annotate(
        "",
        xy=(x1, rank_y),
        xytext=(x1, y_mid),
        arrowprops=dict(
            arrowstyle="-|>",
            lw=1.9,
            linestyle=(0, (4, 3)),
            color=dashed_color,
            mutation_scale=18,
            shrinkA=0,
            shrinkB=0,
        ),
    )
    ax.text((x0 + x1) / 2, y_mid - 0.22, "unrepaired path", fontsize=14, color=dashed_color, ha="center", va="top")

    ax.text(
        10.4,
        4.28,
        "Repair is only applied to the graph-dependent path",
        fontsize=15,
        color="#334155",
        ha="center",
    )

    _save_all(fig, "fig_pipeline")


def load_bew_rows() -> list[BewRow]:
    with BEW_SOURCE.open(encoding="utf-8") as fh:
        rows = [
            BewRow(
                dataset=row["dataset"],
                variant=row["variant"],
                mean_bew_pre=float(row["mean_bew_pre"]),
                mean_bew_post=float(row["mean_bew_post"]),
            )
            for row in csv.DictReader(fh)
        ]
    if len(rows) != len(DATASET_ORDER) * len(VARIANT_ORDER):
        raise ValueError(f"Expected 12 BEW rows in {BEW_SOURCE}, found {len(rows)}")
    expected_keys = {(d, v) for d in DATASET_ORDER for v in VARIANT_ORDER}
    actual_keys = {(row.dataset, row.variant) for row in rows}
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)
        raise ValueError(f"Unexpected BEW key set. Missing={missing} extra={extra}")
    return rows


def render_figure3(rows: list[BewRow]) -> None:
    by_key = {(row.dataset, row.variant): row for row in rows}

    fig, axes = plt.subplots(2, 2, figsize=(10.2, 7.0))
    x_positions = [0.0, 1.3, 2.6]
    width = 0.34
    pre_color = "#D24A43"
    post_color = "#7E72B8"
    legend_handles = None

    for ax, dataset in zip(axes.flat, DATASET_ORDER):
        subset = [by_key[(dataset, variant)] for variant in VARIANT_ORDER]
        pre_vals = [row.mean_bew_pre for row in subset]
        post_vals = [row.mean_bew_post for row in subset]
        left = [x - width / 2 for x in x_positions]
        right = [x + width / 2 for x in x_positions]

        bars_pre = ax.bar(left, pre_vals, width=width, color=pre_color, edgecolor=pre_color, label="BEW graph vs qrels (pre-FAS)")
        bars_post = ax.bar(right, post_vals, width=width, color=post_color, edgecolor=post_color, label="BEW DAG vs qrels (post-FAS)")
        if legend_handles is None:
            legend_handles = [bars_pre[0], bars_post[0]]

        ax.set_xticks(x_positions)
        ax.set_xticklabels([VARIANT_LABELS[v] for v in VARIANT_ORDER])
        ax.set_title(DATASET_LABELS[dataset], pad=8, fontweight="semibold")
        ax.set_ylabel("Mean backward-edge weight")
        ax.yaxis.grid(True, linestyle="--", linewidth=0.8, color="#CBD5E1")
        ax.set_axisbelow(True)
        ymax = max(pre_vals + post_vals) * 1.14
        ax.set_ylim(0, ymax)

    fig.suptitle(
        "Consistency vs labels: preference graph vs qrels reference ranking",
        y=0.985,
        fontsize=15,
        fontweight="semibold",
    )
    if legend_handles is not None:
        fig.legend(
            legend_handles,
            ["BEW graph vs qrels (pre-FAS)", "BEW DAG vs qrels (post-FAS)"],
            loc="upper center",
            bbox_to_anchor=(0.5, 0.935),
            ncol=2,
            frameon=True,
        )
    fig.tight_layout(rect=[0.02, 0.02, 1.0, 0.90])
    _save_all(fig, "fig_graph_qrels_bew_pre_post")


def main() -> None:
    _configure_matplotlib()
    render_figure1()
    rows = load_bew_rows()
    render_figure3(rows)
    print(f"Wrote Figure 1 assets to {FIGURE_DIR}")
    print(f"Wrote Figure 3 assets from {BEW_SOURCE}")


if __name__ == "__main__":
    main()
