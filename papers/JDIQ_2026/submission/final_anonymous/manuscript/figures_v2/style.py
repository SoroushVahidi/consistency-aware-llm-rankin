"""Shared design system for all regenerated JDIQ manuscript figures.

Palette validated with the dataviz skill's validate_palette.js (categorical
4-slot passes lightness/chroma/CVD-separation/contrast checks; diverging
2-slot passes all checks including contrast). Colors are assigned to
entities (datasets) in a fixed order, never cycled or re-mapped.
"""
from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Categorical palette: one color per dataset, fixed order, used everywhere.
# ---------------------------------------------------------------------------
DATASET_ORDER = ["scidocs", "fiqa", "hotpotqa", "bright"]
DATASET_LABELS = {"scidocs": "SciDocs", "fiqa": "FiQA", "hotpotqa": "HotpotQA", "bright": "BRIGHT"}
DATASET_COLORS = {
    "scidocs": "#0072B2",   # blue
    "fiqa": "#E69F00",      # orange
    "hotpotqa": "#009E73",  # bluish green
    "bright": "#CC79A7",    # reddish purple
}

REGIME_ORDER = ["ms2", "ms1", "ms1_drop_mutual"]
REGIME_LABELS = {
    "ms2": "Two-vote",
    "ms1": "One-vote",
    "ms1_drop_mutual": "One-vote,\nmutual pairs\nremoved",
}
REGIME_LABELS_INLINE = {
    "ms2": "Two-vote",
    "ms1": "One-vote",
    "ms1_drop_mutual": "One-vote, mutual pairs removed",
}
# Compact variant for narrow small-multiple panels (4 datasets sharing one
# figure width), where the full wrapped label does not fit per tick.
REGIME_LABELS_SHORT = {
    "ms2": "2-vote",
    "ms1": "1-vote",
    "ms1_drop_mutual": "1-vote,\nno mutual",
}

# Diverging pair for signed deltas (repaired-minus-unrepaired, raw-vs-calibrated
# sign changes). Orange = negative, purple = positive; a neutral gray sits at
# the midpoint. Colorblind-safe (ColorBrewer PuOr family), validated.
DIVERGING_NEG = "#E66101"
DIVERGING_POS = "#5E3C99"
DIVERGING_NEUTRAL = "#F0F0F0"

# Role colors (not entity colors): used only for repaired/unrepaired or
# raw/calibrated role-pairs within a single-entity panel, never mixed with
# the dataset categorical palette in the same encoding channel.
ROLE_RAW = "#999999"
ROLE_CALIBRATED = "#0072B2"
ROLE_UNREPAIRED = "#999999"
ROLE_REPAIRED = "#0072B2"

INK = "#1A1A1A"
MUTED_INK = "#5A5A5A"
GRID = "#E3E3E3"
AXIS = "#8A8A8A"
ZERO_LINE = "#B33F00"

FONT_FAMILY = "DejaVu Sans"
BASE_SIZE = 8.5
TITLE_SIZE = 9.5
TICK_SIZE = 7.5
ANNOT_SIZE = 7.0
LEGEND_SIZE = 7.5

# Single-column figure width for acmart 'manuscript' class (~3.35in text column).
COL_WIDTH_IN = 3.35
PAGE_WIDTH_IN = 6.9  # full text width, for figures that must span both columns' worth


def apply_style() -> None:
    mpl.rcParams.update({
        "font.family": FONT_FAMILY,
        "font.size": BASE_SIZE,
        "axes.titlesize": TITLE_SIZE,
        "axes.titleweight": "bold",
        "axes.labelsize": BASE_SIZE,
        "axes.labelcolor": INK,
        "axes.edgecolor": AXIS,
        "axes.linewidth": 0.8,
        "xtick.labelsize": TICK_SIZE,
        "ytick.labelsize": TICK_SIZE,
        "xtick.color": MUTED_INK,
        "ytick.color": MUTED_INK,
        "legend.fontsize": LEGEND_SIZE,
        "legend.frameon": False,
        "text.color": INK,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def dataset_color(ds: str) -> str:
    return DATASET_COLORS[ds]


def dataset_label(ds: str) -> str:
    return DATASET_LABELS.get(ds, ds)


def regime_label(r: str, inline: bool = False, short: bool = False) -> str:
    table = REGIME_LABELS_SHORT if short else (REGIME_LABELS_INLINE if inline else REGIME_LABELS)
    return table.get(r, r)


def sign_color(value: float) -> str:
    return DIVERGING_POS if value >= 0 else DIVERGING_NEG


def style_axes(ax, title=None, xlabel=None, ylabel=None):
    if title:
        ax.set_title(title, loc="left", pad=6)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(AXIS)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(length=3, width=0.6)
    return ax


def panel_label(ax, letter: str) -> None:
    ax.text(
        -0.08, 1.10, f"({letter})", transform=ax.transAxes,
        fontsize=TITLE_SIZE, fontweight="bold", va="top", ha="left", color=INK,
    )


def savefig(fig, path_no_ext: str) -> None:
    # pad_inches is deliberately more generous than matplotlib's computed
    # tight bbox: italic mathtext glyphs (e.g. the "$k$" in "nDCG@$k$") can
    # render slightly wider than the bbox matplotlib estimates for them,
    # which clips the trailing character at 0.08in padding on some panels.
    fig.savefig(path_no_ext + ".pdf", bbox_inches="tight", pad_inches=0.15)
    fig.savefig(path_no_ext + ".png", bbox_inches="tight", pad_inches=0.15, dpi=300)
    plt.close(fig)
