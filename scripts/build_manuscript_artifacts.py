#!/usr/bin/env python
"""
Build manuscript-ready tables, figures, and graphical abstract from tracked outputs.

This script is intentionally conservative:
- it only reads output artifacts that are committed/tracked by git
- it never runs experiments
- it writes a clean package under outputs/manuscript_artifacts/
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import patches, ticker as mticker  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_ROOT = REPO_ROOT / "outputs" / "manuscript_artifacts"
FIG_DIR = ARTIFACT_ROOT / "figures"
TABLE_DIR = ARTIFACT_ROOT / "tables"
GA_DIR = ARTIFACT_ROOT / "graphical_abstract"


def _tracked_paths() -> set[str]:
    out = subprocess.check_output(["git", "ls-files", "outputs/**"], cwd=REPO_ROOT, text=True)
    return {line.strip() for line in out.splitlines() if line.strip()}


def _is_tracked(path: Path, tracked: set[str]) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    return rel in tracked


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _to_float(value) -> float | None:
    try:
        val = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(val):
        return None
    return val


def _fmt(value, ndigits: int = 4) -> str:
    val = _to_float(value)
    if val is None:
        return "--"
    return f"{val:.{ndigits}f}"


def _latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("_", r"\_")
        .replace("%", r"\%")
        .replace("&", r"\&")
    )


def _write_latex_table(
    path: Path,
    caption: str,
    label: str,
    columns: list[str],
    rows: list[list[str]],
    align: str,
) -> None:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        rf"\caption{{{caption}}}",
        rf"\label{{{label}}}",
        rf"\begin{{tabular}}{{{align}}}",
        r"\toprule",
        " & ".join(columns) + r" \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(row) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _save_figure(fig, stem: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{stem}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def _main_performance_sources(tracked: set[str]) -> dict:
    paths = {
        "scidocs_cross": REPO_ROOT / "outputs/final_modern_baselines/scidocs/scidocs_modern_baselines_summary.csv",
        "hotpot_cross": REPO_ROOT / "outputs/final_modern_baselines/hotpotqa/hotpotqa_modern_baselines_summary.csv",
        "scidocs_pair": REPO_ROOT / "outputs/openai_scidocs_real_run_q20_k15/openai_summary.csv",
        "hotpot_pair": REPO_ROOT / "outputs/openai_hotpotqa_real_run_q10_k15/openai_summary.csv",
        "scidocs_mock": REPO_ROOT / "outputs/modern_baselines/scidocs/scidocs_modern_baselines_summary.csv",
    }
    for name, path in paths.items():
        if not _is_tracked(path, tracked):
            raise FileNotFoundError(f"Required tracked artifact missing: {name} -> {path}")
    return {k: _read_csv(v) for k, v in paths.items()}


def build_table_1(tracked: set[str]) -> None:
    src = _main_performance_sources(tracked)
    method_lookup = {
        ("scidocs", "cross-encoder"): next(r for r in src["scidocs_cross"] if r["method"] == "cross_encoder"),
        ("hotpotqa", "cross-encoder"): next(r for r in src["hotpot_cross"] if r["method"] == "cross_encoder"),
        ("scidocs", "pointwise_llm"): next(r for r in src["scidocs_mock"] if r["method"] == "llm_pointwise_mock"),
        ("scidocs", "listwise_llm"): next(r for r in src["scidocs_mock"] if r["method"] == "llm_listwise_mock"),
        ("scidocs", "pairwise_llm"): next(r for r in src["scidocs_pair"] if r["method"] == "llm_pairwise_copeland"),
        ("hotpotqa", "pairwise_llm"): next(r for r in src["hotpot_pair"] if r["method"] == "llm_pairwise_copeland"),
        ("scidocs", "bt"): next(r for r in src["scidocs_cross"] if r["method"] == "bt_from_qrels"),
        ("hotpotqa", "bt"): next(r for r in src["hotpot_cross"] if r["method"] == "bt_from_qrels"),
        ("scidocs", "win_rate"): next(r for r in src["scidocs_cross"] if r["method"] == "win_rate_from_qrels"),
        ("hotpotqa", "win_rate"): next(r for r in src["hotpot_cross"] if r["method"] == "win_rate_from_qrels"),
        ("scidocs", "markov"): next(r for r in src["scidocs_cross"] if r["method"] == "markov_from_qrels"),
        ("hotpotqa", "markov"): next(r for r in src["hotpot_cross"] if r["method"] == "markov_from_qrels"),
        ("scidocs", "tournament_sort"): next(r for r in src["scidocs_cross"] if r["method"] == "tournament_sort_from_qrels"),
        ("hotpotqa", "tournament_sort"): next(r for r in src["hotpot_cross"] if r["method"] == "tournament_sort_from_qrels"),
        ("scidocs", "repaired"): next(r for r in src["scidocs_pair"] if r["method"] == "hybrid_rrf_repaired_copeland_a03"),
        ("hotpotqa", "repaired"): next(r for r in src["hotpot_pair"] if r["method"] == "hybrid_rrf_repaired_copeland_a03"),
        ("scidocs", "unrepaired"): next(r for r in src["scidocs_pair"] if r["method"] == "hybrid_rrf_unrepaired_copeland_a03"),
        ("hotpotqa", "unrepaired"): next(r for r in src["hotpot_pair"] if r["method"] == "hybrid_rrf_unrepaired_copeland_a03"),
    }
    methods = [
        ("cross-encoder", "Cross-encoder"),
        ("pointwise_llm", "Pointwise LLM"),
        ("pairwise_llm", "Pairwise LLM"),
        ("listwise_llm", "Listwise LLM"),
        ("bt", "Bradley-Terry"),
        ("win_rate", "Win-rate"),
        ("markov", "Markov"),
        ("tournament_sort", "Tournament sort"),
        ("unrepaired", "Hybrid unrepaired"),
        ("repaired", "Hybrid repaired"),
    ]

    csv_rows = []
    latex_rows = []
    for key, label in methods:
        sc = method_lookup.get(("scidocs", key))
        hp = method_lookup.get(("hotpotqa", key))
        sc_ndcg = _fmt(sc["ndcg_mean"]) if sc else "--"
        sc_map = _fmt(sc["map_mean"]) if sc else "--"
        hp_ndcg = _fmt(hp["ndcg_mean"]) if hp else "--"
        hp_map = _fmt(hp["map_mean"]) if hp else "--"
        note = ""
        if key in {"pointwise_llm", "listwise_llm"}:
            note = "tracked mock only"
        csv_rows.append(
            {
                "method": label,
                "scidocs_ndcg": sc_ndcg,
                "scidocs_map": sc_map,
                "hotpotqa_ndcg": hp_ndcg,
                "hotpotqa_map": hp_map,
                "note": note,
            }
        )
        latex_rows.append(
            [
                _latex_escape(label),
                sc_ndcg,
                sc_map,
                hp_ndcg,
                hp_map,
                _latex_escape(note) if note else "--",
            ]
        )

    csv_path = TABLE_DIR / "table_1_main_performance.csv"
    tex_path = TABLE_DIR / "table_1_main_performance.tex"
    _write_csv(
        csv_path,
        csv_rows,
        ["method", "scidocs_ndcg", "scidocs_map", "hotpotqa_ndcg", "hotpotqa_map", "note"],
    )
    _write_latex_table(
        tex_path,
        "Main performance comparison from tracked output artifacts.",
        "tab:main_performance",
        ["Method", "SciDocs nDCG", "SciDocs MAP", "HotpotQA nDCG", "HotpotQA MAP", "Note"],
        latex_rows,
        "lccccc",
    )


def build_table_2(tracked: set[str]) -> None:
    pair_paths = [
        REPO_ROOT / "outputs/openai_scidocs_real_run_q20_k15/openai_summary.csv",
        REPO_ROOT / "outputs/openai_hotpotqa_real_run_q10_k15/openai_summary.csv",
    ]
    rows = []
    latex_rows = []
    for path in pair_paths:
        if not _is_tracked(path, tracked):
            continue
        summary = {r["method"]: r for r in _read_csv(path)}
        dataset = "scidocs" if "scidocs" in path.as_posix() else "hotpotqa"
        for suffix, label in [("copeland", "Copeland"), ("balance", "Balance")]:
            rep = summary[f"hybrid_rrf_repaired_{suffix}_a03"]
            unrep = summary[f"hybrid_rrf_unrepaired_{suffix}_a03"]
            d_ndcg = _to_float(rep["ndcg_mean"]) - _to_float(unrep["ndcg_mean"])
            d_bew = _to_float(unrep["bew_mean"]) - _to_float(rep["bew_mean"])
            d_pic = _to_float(unrep["pic_mean"]) - _to_float(rep["pic_mean"])
            row = {
                "dataset": dataset,
                "comparison": label,
                "delta_ndcg_repaired_minus_unrepaired": f"{d_ndcg:+.4f}",
                "delta_bew_unrepaired_minus_repaired": f"{d_bew:+.2f}",
                "delta_pic_unrepaired_minus_repaired": f"{d_pic:+.2f}",
            }
            rows.append(row)
            latex_rows.append(
                [
                    dataset,
                    label,
                    row["delta_ndcg_repaired_minus_unrepaired"],
                    row["delta_bew_unrepaired_minus_repaired"],
                    row["delta_pic_unrepaired_minus_repaired"],
                ]
            )
    _write_csv(
        TABLE_DIR / "table_2_repair_deltas.csv",
        rows,
        [
            "dataset",
            "comparison",
            "delta_ndcg_repaired_minus_unrepaired",
            "delta_bew_unrepaired_minus_repaired",
            "delta_pic_unrepaired_minus_repaired",
        ],
    )
    _write_latex_table(
        TABLE_DIR / "table_2_repair_deltas.tex",
        "Repaired vs unrepaired deltas from tracked real pairwise runs.",
        "tab:repair_deltas",
        ["Dataset", "Comparison", "$\\Delta$ nDCG", "$\\Delta$ BEW", "$\\Delta$ PIC"],
        latex_rows,
        "llccc",
    )


def build_table_3(tracked: set[str]) -> None:
    rows = []
    latex_rows = []
    qrels_paths = {
        "scidocs": REPO_ROOT / "outputs/real_full/scidocs/qrels/scidocs_experiment_summary.json",
        "hotpotqa": REPO_ROOT / "outputs/real_full/hotpotqa/qrels/hotpotqa_experiment_summary.json",
    }
    pair_md_paths = {
        "scidocs": REPO_ROOT / "outputs/openai_scidocs_real_run_q20_k15/OPENAI_RUN_SUMMARY.md",
        "hotpotqa": REPO_ROOT / "outputs/openai_hotpotqa_real_run_q10_k15/OPENAI_RUN_SUMMARY.md",
    }
    vote_path = REPO_ROOT / "outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv"

    for dataset, path in qrels_paths.items():
        if _is_tracked(path, tracked):
            payload = _read_json(path)
            row = {
                "dataset": dataset,
                "regime": "qrels",
                "pct_cyclic_queries": f"{payload['pct_cyclic_graphs']:.2f}",
                "avg_largest_scc": f"{payload['avg_largest_scc']:.3f}",
                "avg_fas_edges_removed": f"{payload['avg_fas_removed_weight']:.3f}",
            }
            rows.append(row)
            latex_rows.append([dataset, "qrels", row["pct_cyclic_queries"], row["avg_largest_scc"], row["avg_fas_edges_removed"]])

    for dataset, path in pair_md_paths.items():
        if _is_tracked(path, tracked):
            text = path.read_text(encoding="utf-8")
            cyc_line = next(line for line in text.splitlines() if line.startswith("- Cyclic queries:"))
            fas_line = next(line for line in text.splitlines() if line.startswith("- Avg FAS edges removed:"))
            pct = cyc_line.split("(")[-1].rstrip("%)")
            fas = fas_line.split(":")[-1].strip()
            row = {
                "dataset": dataset,
                "regime": "llm_pairwise",
                "pct_cyclic_queries": pct,
                "avg_largest_scc": "--",
                "avg_fas_edges_removed": fas,
            }
            rows.append(row)
            latex_rows.append([dataset, "llm-pairwise", pct, "--", fas])

    if _is_tracked(vote_path, tracked):
        for r in _read_csv(vote_path):
            if r["dataset"] not in {"scidocs", "hotpotqa"} or r["variant"] != "ms1":
                continue
            row = {
                "dataset": r["dataset"],
                "regime": "publication_votes_ms1",
                "pct_cyclic_queries": _fmt(r["pct_cyclic"], 2),
                "avg_largest_scc": _fmt(r["avg_largest_scc"], 3),
                "avg_fas_edges_removed": _fmt(r["mean_fas_weight_removed"], 3),
            }
            rows.append(row)
            latex_rows.append(
                [
                    r["dataset"],
                    "publication-votes-ms1",
                    row["pct_cyclic_queries"],
                    row["avg_largest_scc"],
                    row["avg_fas_edges_removed"],
                ]
            )

    _write_csv(
        TABLE_DIR / "table_3_cyclicity_statistics.csv",
        rows,
        ["dataset", "regime", "pct_cyclic_queries", "avg_largest_scc", "avg_fas_edges_removed"],
    )
    _write_latex_table(
        TABLE_DIR / "table_3_cyclicity_statistics.tex",
        "Cyclicity statistics across tracked preference regimes.",
        "tab:cyclicity_stats",
        ["Dataset", "Regime", "\\% cyclic", "Avg SCC", "Avg FAS removed"],
        latex_rows,
        "llccc",
    )


def build_table_4(tracked: set[str]) -> None:
    rows = []
    latex_rows = []
    sc_mock = REPO_ROOT / "outputs/modern_baselines/scidocs/scidocs_modern_baselines_summary.csv"
    sc_pair = REPO_ROOT / "outputs/openai_scidocs_real_run_q20_k15/openai_summary.csv"
    sc_pair_cfg = REPO_ROOT / "outputs/openai_scidocs_real_run_q20_k15/config.json"
    if not (_is_tracked(sc_mock, tracked) and _is_tracked(sc_pair, tracked) and _is_tracked(sc_pair_cfg, tracked)):
        return

    mock_rows = {r["method"]: r for r in _read_csv(sc_mock)}
    pair_rows = {r["method"]: r for r in _read_csv(sc_pair)}
    pair_cfg = _read_json(sc_pair_cfg)
    pair_calls = pair_cfg["api_stats"]["api_calls"]
    pair_cost = pair_cfg["cost_estimate_usd"]
    pair_runtime = pair_cfg["wall_time_s"]

    entries = [
        ("Pointwise", mock_rows["llm_pointwise_mock"], "mock", "--", "--", "--"),
        ("Pairwise", pair_rows["llm_pairwise_copeland"], "real", str(pair_calls), f"{pair_cost:.4f}", f"{pair_runtime:.1f}"),
        ("Listwise", mock_rows["llm_listwise_mock"], "mock", "--", "--", "--"),
    ]
    for label, row, status, calls, cost, runtime in entries:
        out = {
            "paradigm": label,
            "scidocs_ndcg": _fmt(row["ndcg_mean"]),
            "scidocs_map": _fmt(row["map_mean"]),
            "evidence_status": status,
            "api_calls": calls,
            "cost_usd": cost,
            "runtime_s": runtime,
        }
        rows.append(out)
        latex_rows.append(
            [
                label,
                out["scidocs_ndcg"],
                out["scidocs_map"],
                status,
                calls,
                cost,
                runtime,
            ]
        )

    _write_csv(
        TABLE_DIR / "table_4_llm_paradigm_comparison.csv",
        rows,
        ["paradigm", "scidocs_ndcg", "scidocs_map", "evidence_status", "api_calls", "cost_usd", "runtime_s"],
    )
    _write_latex_table(
        TABLE_DIR / "table_4_llm_paradigm_comparison.tex",
        "LLM paradigm comparison on SciDocs from tracked artifacts.",
        "tab:llm_paradigms",
        ["Paradigm", "nDCG", "MAP", "Status", "API calls", "Cost", "Runtime (s)"],
        latex_rows,
        "lcccccc",
    )


def build_figures(tracked: set[str]) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    dataset_display = {"scidocs": "SciDocs", "hotpotqa": "HotpotQA"}

    # Figure 1: pipeline diagram
    fig, ax = plt.subplots(figsize=(9, 3))
    ax.axis("off")
    x_positions = [0.03, 0.20, 0.40, 0.58, 0.75, 0.90]
    labels = ["Query", "Candidate set", "Preferences", "Graph", "Repair", "Ranking"]
    colors = ["#dbeafe", "#dbeafe", "#ede9fe", "#fee2e2", "#dcfce7", "#fef3c7"]
    for x, label, color in zip(x_positions, labels, colors):
        rect = patches.FancyBboxPatch(
            (x, 0.38), 0.12, 0.22, boxstyle="round,pad=0.02", fc=color, ec="#334155"
        )
        ax.add_patch(rect)
        ax.text(x + 0.06, 0.49, label, ha="center", va="center", fontsize=10)
    for i in range(len(x_positions) - 1):
        ax.annotate("", xy=(x_positions[i + 1] - 0.01, 0.49), xytext=(x_positions[i] + 0.12, 0.49), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.text(0.40, 0.73, "LLM path: pointwise / pairwise / listwise", ha="center", fontsize=10, color="#1d4ed8")
    ax.text(0.40, 0.25, "Non-LLM path: qrels / cross-encoder / tournament aggregation", ha="center", fontsize=10, color="#166534")
    ax.text(0.58, 0.12, "Repair applied only when cyclic preferences are present", ha="center", fontsize=9)
    _save_figure(fig, "figure_1_pipeline_diagram")

    # Figure 2: cyclicity comparison
    cyc_rows = _read_csv(TABLE_DIR / "table_3_cyclicity_statistics.csv")
    order = [
        ("scidocs", "qrels", 0.0),
        ("scidocs", "llm_pairwise", 1.15),
        ("scidocs", "publication_votes_ms1", 2.3),
        ("hotpotqa", "qrels", 4.1),
        ("hotpotqa", "llm_pairwise", 5.25),
        ("hotpotqa", "publication_votes_ms1", 6.4),
    ]
    label_map = {
        "qrels": "Qrels",
        "llm_pairwise": "Pairwise\nLLM",
        "publication_votes_ms1": "Publication\nvotes\n(ms1)",
    }
    color_map = {
        "qrels": "#94a3b8",
        "llm_pairwise": "#2563eb",
        "publication_votes_ms1": "#7c3aed",
    }
    x_positions: list[float] = []
    labels: list[str] = []
    vals: list[float] = []
    colors: list[str] = []
    for ds, regime, xpos in order:
        row = next((r for r in cyc_rows if r["dataset"] == ds and r["regime"] == regime), None)
        if row is None:
            continue
        x_positions.append(xpos)
        labels.append(label_map[regime])
        vals.append(float(row["pct_cyclic_queries"]))
        colors.append(color_map[regime])
    fig, ax = plt.subplots(figsize=(9.1, 4.8))
    ax.bar(
        x_positions,
        vals,
        width=0.8,
        color=colors,
        edgecolor="#475569",
        linewidth=0.5,
    )
    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels, fontsize=9)
    ax.tick_params(axis="x", pad=8)
    ax.set_ylabel("% cyclic queries")
    ax.set_ylim(0, 105)
    ax.set_xlim(-0.7, 7.1)
    ax.set_title("Cyclicity comparison across tracked regimes", fontsize=11, pad=10)
    ax.yaxis.grid(True, linestyle=":", linewidth=0.8, alpha=0.4)
    ax.set_axisbelow(True)
    ax.axvline(3.25, color="#cbd5e1", linewidth=1.0)
    ax.text(
        1.15,
        -0.24,
        dataset_display["scidocs"],
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="top",
        fontsize=10,
        fontweight="bold",
    )
    ax.text(
        5.25,
        -0.24,
        dataset_display["hotpotqa"],
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="top",
        fontsize=10,
        fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0.08, 1, 0.97])
    _save_figure(fig, "figure_2_cyclicity_comparison")

    # Figure 3: repair effect on nDCG
    delta_rows = _read_csv(TABLE_DIR / "table_2_repair_deltas.csv")
    delta_positions = [0.0, 1.1, 3.0, 4.1]
    tick_labels = [r["comparison"] for r in delta_rows]
    vals = [float(r["delta_ndcg_repaired_minus_unrepaired"]) for r in delta_rows]
    datasets = [r["dataset"] for r in delta_rows]
    colors = [
        "#fca5a5" if dataset == "scidocs" else "#dc2626"
        for dataset in datasets
    ]
    hatches = ["", "//", "", "//"]
    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    bars = ax.bar(
        delta_positions,
        vals,
        width=0.78,
        color=colors,
        edgecolor="#7f1d1d",
        linewidth=0.6,
    )
    for bar, hatch in zip(bars, hatches):
        bar.set_hatch(hatch)
    ax.set_xticks(delta_positions)
    ax.set_xticklabels(tick_labels, fontsize=9)
    ax.tick_params(axis="x", pad=8)
    ax.axhline(0, color="#0f172a", lw=1.0, linestyle="--", zorder=3)
    ax.set_ylabel(r"$\Delta$ nDCG (repaired - unrepaired)")
    ax.set_title("Repair effect on nDCG from tracked real pairwise runs", fontsize=11, pad=10)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.4f"))
    ax.yaxis.grid(True, linestyle=":", linewidth=0.8, alpha=0.4)
    ax.set_axisbelow(True)
    ymin = min(vals)
    ymax = max(vals)
    ax.set_ylim(ymin - 0.0012, max(0.0015, ymax + 0.0010))
    ax.set_xlim(-0.7, 4.8)
    ax.text(
        0.55,
        -0.18,
        dataset_display["scidocs"],
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="top",
        fontsize=10,
        fontweight="bold",
    )
    ax.text(
        3.55,
        -0.18,
        dataset_display["hotpotqa"],
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="top",
        fontsize=10,
        fontweight="bold",
    )
    for xpos, val in zip(delta_positions, vals):
        ax.text(
            xpos,
            val - 0.00025,
            f"{val:+.4f}",
            ha="center",
            va="top",
            fontsize=8.5,
            color="#7f1d1d",
        )
    fig.tight_layout(rect=[0, 0.06, 1, 0.97])
    _save_figure(fig, "figure_3_repair_effect_ndcg")

    # Figure 4: structural vs retrieval tradeoff
    pair_sc = _read_csv(REPO_ROOT / "outputs/openai_scidocs_real_run_q20_k15/openai_summary.csv")
    pair_hp = _read_csv(REPO_ROOT / "outputs/openai_hotpotqa_real_run_q10_k15/openai_summary.csv")
    fig, ax = plt.subplots(figsize=(7.1, 4.8))
    dataset_styles = {
        "SciDocs": {"marker": "o"},
        "HotpotQA": {"marker": "s"},
    }
    comparison_styles = {
        "Copeland": {
            "repaired": "hybrid_rrf_repaired_copeland_a03",
            "unrepaired": "hybrid_rrf_unrepaired_copeland_a03",
            "color": "#16a34a",
            "rad": 0.14,
            "s_unrepaired": 100,
            "s_repaired": 72,
        },
        "Balance": {
            "repaired": "hybrid_rrf_repaired_balance_a03",
            "unrepaired": "hybrid_rrf_unrepaired_balance_a03",
            "color": "#dc2626",
            "rad": -0.14,
            "s_unrepaired": 138,
            "s_repaired": 104,
        },
    }
    arrow_offsets = {
        ("SciDocs", "Copeland"): (-16, 18),
        ("SciDocs", "Balance"): (-18, -20),
        ("HotpotQA", "Copeland"): (18, 14),
        ("HotpotQA", "Balance"): (20, -18),
    }
    all_x: list[float] = []
    all_y: list[float] = []
    for rows, dataset in [(pair_sc, "SciDocs"), (pair_hp, "HotpotQA")]:
        marker = dataset_styles[dataset]["marker"]
        for comparison, cfg in comparison_styles.items():
            repaired = next(r for r in rows if r["method"] == cfg["repaired"])
            unrepaired = next(r for r in rows if r["method"] == cfg["unrepaired"])
            ux = float(unrepaired["bew_mean"])
            uy = float(unrepaired["ndcg_mean"])
            rx = float(repaired["bew_mean"])
            ry = float(repaired["ndcg_mean"])
            all_x.extend([ux, rx])
            all_y.extend([uy, ry])
            ax.scatter(
                ux,
                uy,
                marker=marker,
                s=cfg["s_unrepaired"],
                facecolors="white",
                edgecolors=cfg["color"],
                linewidths=1.5,
                zorder=3,
            )
            ax.scatter(
                rx,
                ry,
                marker=marker,
                s=cfg["s_repaired"],
                facecolors=cfg["color"],
                edgecolors="black",
                linewidths=0.8,
                zorder=4,
            )
            ax.annotate(
                "",
                xy=(rx, ry),
                xytext=(ux, uy),
                arrowprops=dict(
                    arrowstyle="->",
                    color=cfg["color"],
                    lw=1.2,
                    connectionstyle=f"arc3,rad={cfg['rad']}",
                ),
                zorder=2,
            )
            mx = (ux + rx) / 2
            my = (uy + ry) / 2
            ax.annotate(
                f"{dataset} {comparison}",
                xy=(mx, my),
                xytext=arrow_offsets[(dataset, comparison)],
                textcoords="offset points",
                ha="center",
                va="center",
                fontsize=8.5,
                color=cfg["color"],
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85),
            )
    ax.set_xlabel("Mean backward-edge weight (BEW)")
    ax.set_ylabel("nDCG")
    ax.set_title("Structural vs retrieval tradeoff (tracked real pairwise runs)", fontsize=11, pad=10)
    ax.grid(True, linestyle=":", linewidth=0.8, alpha=0.35)
    ax.set_axisbelow(True)
    x_pad = max(0.15, (max(all_x) - min(all_x)) * 0.18)
    y_pad = max(0.004, (max(all_y) - min(all_y)) * 0.18)
    ax.set_xlim(min(all_x) - x_pad, max(all_x) + x_pad)
    ax.set_ylim(min(all_y) - y_pad, max(all_y) + y_pad)
    dataset_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor="#94a3b8",
            markeredgecolor="#334155",
            markersize=7,
            label="SciDocs",
        ),
        Line2D(
            [0],
            [0],
            marker="s",
            color="none",
            markerfacecolor="#94a3b8",
            markeredgecolor="#334155",
            markersize=7,
            label="HotpotQA",
        ),
    ]
    encoding_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor="white",
            markeredgecolor="#475569",
            markersize=7,
            label="Unrepaired",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor="#94a3b8",
            markeredgecolor="black",
            markersize=7,
            label="Repaired",
        ),
        Line2D([0, 1], [0, 0], color="#16a34a", lw=1.5, label="Copeland"),
        Line2D([0, 1], [0, 0], color="#dc2626", lw=1.5, label="Balance"),
    ]
    legend1 = ax.legend(
        handles=dataset_handles,
        loc="upper left",
        frameon=False,
        fontsize=8,
        title="Dataset",
        title_fontsize=9,
    )
    ax.add_artist(legend1)
    ax.legend(
        handles=encoding_handles,
        loc="lower right",
        frameon=False,
        fontsize=8,
        title="Encoding",
        title_fontsize=9,
    )
    fig.tight_layout(rect=[0, 0.02, 1, 0.97])
    _save_figure(fig, "figure_4_structural_retrieval_tradeoff")

    # Figure 5: LLM paradigm comparison
    tab4 = _read_csv(TABLE_DIR / "table_4_llm_paradigm_comparison.csv")
    fig, ax = plt.subplots(figsize=(5.8, 4))
    labels = [r["paradigm"] for r in tab4]
    vals = [float(r["scidocs_ndcg"]) for r in tab4]
    colors = ["#94a3b8" if r["evidence_status"] != "real" else "#2563eb" for r in tab4]
    ax.bar(labels, vals, color=colors)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("SciDocs nDCG")
    ax.set_title("LLM paradigm comparison (tracked artifacts)")
    fig.tight_layout()
    _save_figure(fig, "figure_5_llm_paradigm_comparison")


def build_graphical_abstract() -> None:
    GA_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 2.8))
    ax.axis("off")
    boxes = [
        (0.04, "LLM preferences", "#dbeafe"),
        (0.31, "Cyclic graph", "#fee2e2"),
        (0.56, "FAS repair", "#dcfce7"),
        (0.78, "Ranking outcome", "#fef3c7"),
    ]
    for x, label, color in boxes:
        rect = patches.FancyBboxPatch((x, 0.38), 0.16, 0.24, boxstyle="round,pad=0.02", fc=color, ec="#334155")
        ax.add_patch(rect)
        ax.text(x + 0.08, 0.50, label, ha="center", va="center", fontsize=11)
    for i in range(len(boxes) - 1):
        ax.annotate("", xy=(boxes[i + 1][0] - 0.01, 0.50), xytext=(boxes[i][0] + 0.16, 0.50), arrowprops=dict(arrowstyle="->", lw=1.6))
    ax.text(0.50, 0.16, "Key finding: repair improves structure but not nDCG", ha="center", fontsize=12, weight="bold", color="#991b1b")
    fig.tight_layout()
    fig.savefig(GA_DIR / "graphical_abstract.pdf", bbox_inches="tight")
    fig.savefig(GA_DIR / "graphical_abstract.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def safe_cleanup_duplicates() -> list[dict[str, str]]:
    # Conservative: perform no deletions unless exact duplicates are explicitly proven.
    return []


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Build manuscript-ready artifacts from tracked outputs.")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/manuscript_artifacts"),
        help="Destination root for manuscript artifacts.",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    global ARTIFACT_ROOT, FIG_DIR, TABLE_DIR, GA_DIR
    ARTIFACT_ROOT = (REPO_ROOT / args.output_root).resolve()
    FIG_DIR = ARTIFACT_ROOT / "figures"
    TABLE_DIR = ARTIFACT_ROOT / "tables"
    GA_DIR = ARTIFACT_ROOT / "graphical_abstract"
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    GA_DIR.mkdir(parents=True, exist_ok=True)

    tracked = _tracked_paths()
    build_table_1(tracked)
    build_table_2(tracked)
    build_table_3(tracked)
    build_table_4(tracked)
    build_figures(tracked)
    build_graphical_abstract()

    manifest = {
        "figures": sorted(p.name for p in FIG_DIR.iterdir()),
        "tables": sorted(p.name for p in TABLE_DIR.iterdir()),
        "graphical_abstract": sorted(p.name for p in GA_DIR.iterdir()),
        "deletions": safe_cleanup_duplicates(),
    }
    (ARTIFACT_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[build_manuscript_artifacts] output_root={ARTIFACT_ROOT}")
    print(f"[build_manuscript_artifacts] figures={len(manifest['figures'])}")
    print(f"[build_manuscript_artifacts] tables={len(manifest['tables'])}")
    print(f"[build_manuscript_artifacts] graphical_abstract={len(manifest['graphical_abstract'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
