#!/usr/bin/env python
"""
Copy publication paper-package plots into figures/manuscript/ and generate
additional manuscript-oriented figures from the aggregate CSV.

Usage (from repo root)::

    python scripts/build_manuscript_assets.py \\
        --pub-root outputs/pub_vote_cmp_all4/paper_package
"""
from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def copy_plots(src_plots: Path, dst: Path) -> list[Path]:
    dst.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for p in sorted(src_plots.glob("*.png")):
        out = dst / p.name
        shutil.copy2(p, out)
        copied.append(out)
    return copied


def plot_ndcg_copeland_ms1(table_csv: Path, out_png: Path) -> None:
    """Bar chart: mean nDCG (unrepaired vs repaired Copeland) for ms1 across datasets."""
    rows: list[dict[str, str]] = []
    with table_csv.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("variant") == "ms1":
                rows.append(row)
    if not rows:
        raise SystemExit(f"No ms1 rows in {table_csv}")

    labels = [r["dataset"] for r in rows]
    uco = [float(r["mean_ndcg_uco"]) for r in rows]
    rco = [float(r["mean_ndcg_rco"]) for r in rows]

    x = range(len(labels))
    w = 0.35
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar([i - w / 2 for i in x], uco, width=w, label="Unrepaired Copeland", color="#8de5a1")
    ax.bar([i + w / 2 for i in x], rco, width=w, label="Repaired Copeland", color="#27ae60")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Mean nDCG@k")
    ax.set_title("Publication vote suite — ms1 — Copeland hybrids (four datasets)")
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--pub-root",
        type=Path,
        default=Path("outputs/pub_vote_cmp_all4/paper_package"),
        help="Path to paper_package directory",
    )
    args = ap.parse_args()
    root = _repo_root()
    pub = (root / args.pub_root).resolve() if not args.pub_root.is_absolute() else args.pub_root
    tables = pub / "tables"
    src_plots = pub / "plots"
    fig_manuscript = root / "figures" / "manuscript"

    table_csv = tables / "table_graph_ndcg_and_consistency.csv"
    if not table_csv.is_file():
        raise SystemExit(f"Missing {table_csv}")

    copied = copy_plots(src_plots, fig_manuscript) if src_plots.is_dir() else []
    extra = root / "figures" / "manuscript" / "fig_ndcg_copeland_ms1_four_datasets.png"
    plot_ndcg_copeland_ms1(table_csv, extra)

    readme = fig_manuscript / "README.md"
    lines = [
        "# Manuscript figures (curated)",
        "",
        "These files are generated or copied by `scripts/build_manuscript_assets.py`.",
        "",
        "## Source",
        "",
        f"- Publication package: `{pub.relative_to(root)}`",
        "",
        "## Files",
        "",
    ]
    for p in sorted(fig_manuscript.glob("*.png")):
        lines.append(f"- `{p.name}`")
    lines.append("")
    readme.write_text("\n".join(lines), encoding="utf-8")
    print(f"[build_manuscript_assets] copied {len(copied)} plots → {fig_manuscript}")
    print(f"[build_manuscript_assets] wrote {extra.relative_to(root)}")


if __name__ == "__main__":
    main()
