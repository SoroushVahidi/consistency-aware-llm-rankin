"""
plot_timings.py
===============
Generate timing visualizations from profiling data saved by ``run_synthetic.py``.

Reads ``outputs/timings/synthetic_timings.json`` (or a path you specify) and
saves four plots under ``outputs/plots/``:

1. ``runtime_by_stage.png``    — bar chart of total runtime per stage
2. ``runtime_vs_n_items.png``  — line chart: runtime vs. graph node count
   (requires multiple JSON files from runs with different ``n_items``)
3. ``runtime_breakdown_pie.png`` — pie chart of time spent per stage
4. ``runtime_by_method.png``   — bar chart comparing ranking methods only

Usage
-----
::

    # Plot from a single timing JSON file
    python scripts/plot_timings.py

    # Plot from a specific file
    python scripts/plot_timings.py --input outputs/timings/synthetic_timings.json

    # Specify output directory
    python scripts/plot_timings.py --output-dir outputs/plots

    # Scale experiment: run multiple sizes, then plot runtime vs n_items
    for n in 10 20 50 100; do
        python scripts/run_synthetic.py --n-items $n --save-timings \\
            --output-dir outputs/scale_$n
    done
    python scripts/plot_timings.py --scale-dirs outputs/scale_10 outputs/scale_20 \\
        outputs/scale_50 outputs/scale_100
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running as `python scripts/plot_timings.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

_RANKING_STAGES = {"ranking_score_sum", "ranking_borda", "ranking_topological"}


def _load_timing_json(path: Path) -> dict:
    with path.open() as fh:
        return json.load(fh)


def plot_stage_bar(timing_data: dict, output_dir: Path) -> Path:
    """Bar chart: total runtime (s) per pipeline stage.

    Parameters
    ----------
    timing_data:
        Parsed JSON from ``synthetic_timings.json``.
    output_dir:
        Directory where the plot will be saved.

    Returns
    -------
    Path
        Path to the saved image.

    Notes
    -----
    O(S) where S = number of stages; plotting overhead is negligible.
    """
    import matplotlib.pyplot as plt

    summary = timing_data.get("summary", [])
    # Exclude the outer total_experiment stage from the breakdown
    stages = [r["stage"] for r in summary if r["stage"] != "total_experiment"]
    totals = [r["total_s"] for r in summary if r["stage"] != "total_experiment"]

    if not stages:
        print("  [plot_timings] No stage data to plot.")
        return output_dir / "runtime_by_stage.png"

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#4C72B0" if s not in _RANKING_STAGES else "#DD8452" for s in stages]
    bars = ax.barh(stages, totals, color=colors)
    ax.bar_label(bars, fmt="%.4f s", padding=3, fontsize=8)
    ax.set_xlabel("Total time (s)")
    ax.set_title("Pipeline runtime by stage")
    ax.invert_yaxis()
    fig.tight_layout()

    out = output_dir / "runtime_by_stage.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  [plot_timings] Saved {out}")
    return out


def plot_stage_pie(timing_data: dict, output_dir: Path) -> Path:
    """Pie chart: proportion of time spent per pipeline stage.

    Parameters
    ----------
    timing_data:
        Parsed JSON from ``synthetic_timings.json``.
    output_dir:
        Directory where the plot will be saved.

    Returns
    -------
    Path
    """
    import matplotlib.pyplot as plt

    summary = timing_data.get("summary", [])
    stages = [r["stage"] for r in summary if r["stage"] != "total_experiment"]
    totals = [r["total_s"] for r in summary if r["stage"] != "total_experiment"]

    if not stages or sum(totals) == 0:
        print("  [plot_timings] No data for pie chart.")
        return output_dir / "runtime_breakdown_pie.png"

    fig, ax = plt.subplots(figsize=(8, 8))
    wedges, texts, autotexts = ax.pie(
        totals, labels=stages, autopct="%1.1f%%", startangle=140
    )
    for at in autotexts:
        at.set_fontsize(8)
    ax.set_title("Runtime breakdown by stage")
    fig.tight_layout()

    out = output_dir / "runtime_breakdown_pie.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  [plot_timings] Saved {out}")
    return out


def plot_method_bar(timing_data: dict, output_dir: Path) -> Path:
    """Bar chart: total runtime for ranking methods only.

    Parameters
    ----------
    timing_data:
        Parsed JSON from ``synthetic_timings.json``.
    output_dir:
        Directory where the plot will be saved.

    Returns
    -------
    Path
    """
    import matplotlib.pyplot as plt

    summary = timing_data.get("summary", [])
    method_rows = [r for r in summary if r["stage"] in _RANKING_STAGES | {"greedy_fas_solver"}]
    if not method_rows:
        print("  [plot_timings] No ranking/solver stage data found.")
        return output_dir / "runtime_by_method.png"

    stages = [r["stage"] for r in method_rows]
    totals = [r["total_s"] for r in method_rows]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(stages, totals, color="#55A868")
    ax.set_ylabel("Total time (s)")
    ax.set_title("Runtime: ranking methods & solver")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()

    out = output_dir / "runtime_by_method.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  [plot_timings] Saved {out}")
    return out


def plot_runtime_vs_n_items(scale_dirs: list[Path], output_dir: Path) -> Path:
    """Line chart: total experiment runtime vs. number of items.

    Reads ``timings/synthetic_timings.json`` from each scale directory and
    extracts ``metadata.n_items`` and the ``total_experiment`` stage total.

    Parameters
    ----------
    scale_dirs:
        List of output directories, one per ``n_items`` value.
    output_dir:
        Directory where the plot will be saved.

    Returns
    -------
    Path

    Notes
    -----
    This plot helps identify super-linear scaling (e.g. in cycle detection
    or the greedy FAS heuristic), both of which are O(C · E) in the worst
    case where C = cycles found, E = edges per cycle.
    """
    import matplotlib.pyplot as plt

    records = []
    for d in scale_dirs:
        p = Path(d) / "timings" / "synthetic_timings.json"
        if not p.exists():
            print(f"  [plot_timings] Skipping {d} — timings file not found.")
            continue
        data = _load_timing_json(p)
        n_items = data.get("metadata", {}).get("n_items")
        summary_map = {r["stage"]: r for r in data.get("summary", [])}
        total = summary_map.get("total_experiment", {}).get("total_s")
        if n_items is not None and total is not None:
            records.append((int(n_items), float(total)))

    if len(records) < 2:
        print("  [plot_timings] Need at least 2 scale dirs to plot runtime vs n_items.")
        out = output_dir / "runtime_vs_n_items.png"
        return out

    records.sort(key=lambda x: x[0])
    xs = [r[0] for r in records]
    ys = [r[1] for r in records]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(xs, ys, marker="o", color="#C44E52", linewidth=2)
    ax.set_xlabel("Number of items (n)")
    ax.set_ylabel("Total experiment runtime (s)")
    ax.set_title("Runtime vs. number of items")
    ax.grid(True, linestyle="--", alpha=0.5)
    fig.tight_layout()

    out = output_dir / "runtime_vs_n_items.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  [plot_timings] Saved {out}")
    return out


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate timing plots from profiling JSON files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("outputs/timings/synthetic_timings.json"),
        help="Path to a synthetic_timings.json file",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/plots"),
        help="Directory to save plots",
    )
    parser.add_argument(
        "--scale-dirs",
        type=Path,
        nargs="*",
        default=[],
        help="List of output dirs from scale experiments (for runtime-vs-n_items plot)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    args = parse_args(argv)

    try:
        import matplotlib  # noqa: F401
    except ImportError:
        print(
            "ERROR: matplotlib is required for plotting.\n"
            "Install it with: pip install matplotlib"
        )
        sys.exit(1)

    output_dir = args.output_dir

    if args.input.exists():
        timing_data = _load_timing_json(args.input)
        plot_stage_bar(timing_data, output_dir)
        plot_stage_pie(timing_data, output_dir)
        plot_method_bar(timing_data, output_dir)
    else:
        print(f"  [plot_timings] Input file not found: {args.input}")
        print("  Run first: python scripts/run_synthetic.py --save-timings")

    if args.scale_dirs:
        plot_runtime_vs_n_items(args.scale_dirs, output_dir)


if __name__ == "__main__":
    main()
