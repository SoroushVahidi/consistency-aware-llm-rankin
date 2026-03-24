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
from matplotlib import patches  # noqa: E402

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
    order = ["scidocs-qrels", "scidocs-llm_pairwise", "scidocs-publication_votes_ms1", "hotpotqa-qrels", "hotpotqa-llm_pairwise", "hotpotqa-publication_votes_ms1"]
    labels = []
    vals = []
    for key in order:
        ds, regime = key.split("-", 1)
        row = next((r for r in cyc_rows if r["dataset"] == ds and r["regime"] == regime), None)
        if row is None:
            continue
        labels.append(f"{ds}\n{regime}")
        vals.append(float(row["pct_cyclic_queries"]))
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(labels, vals, color=["#94a3b8", "#2563eb", "#7c3aed", "#94a3b8", "#2563eb", "#7c3aed"][: len(vals)])
    ax.set_ylabel("% cyclic queries")
    ax.set_ylim(0, 105)
    ax.set_title("Cyclicity comparison across tracked regimes")
    fig.tight_layout()
    _save_figure(fig, "figure_2_cyclicity_comparison")

    # Figure 3: repair effect on nDCG
    delta_rows = _read_csv(TABLE_DIR / "table_2_repair_deltas.csv")
    labels = [f"{r['dataset']}\n{r['comparison']}" for r in delta_rows]
    vals = [float(r["delta_ndcg_repaired_minus_unrepaired"]) for r in delta_rows]
    fig, ax = plt.subplots(figsize=(6.5, 4))
    colors = ["#dc2626" if v < 0 else "#16a34a" for v in vals]
    ax.bar(labels, vals, color=colors)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_ylabel(r"$\Delta$ nDCG (repaired - unrepaired)")
    ax.set_title("Repair effect on nDCG from tracked real pairwise runs")
    fig.tight_layout()
    _save_figure(fig, "figure_3_repair_effect_ndcg")

    # Figure 4: structural vs retrieval tradeoff
    pair_sc = _read_csv(REPO_ROOT / "outputs/openai_scidocs_real_run_q20_k15/openai_summary.csv")
    pair_hp = _read_csv(REPO_ROOT / "outputs/openai_hotpotqa_real_run_q10_k15/openai_summary.csv")
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for rows, dataset, marker in [(pair_sc, "SciDocs", "o"), (pair_hp, "HotpotQA", "s")]:
        for repaired, unrepaired, color in [
            ("hybrid_rrf_repaired_copeland_a03", "hybrid_rrf_unrepaired_copeland_a03", "#16a34a"),
            ("hybrid_rrf_repaired_balance_a03", "hybrid_rrf_unrepaired_balance_a03", "#dc2626"),
        ]:
            rr = next(r for r in rows if r["method"] == repaired)
            uu = next(r for r in rows if r["method"] == unrepaired)
            ax.scatter(float(uu["bew_mean"]), float(uu["ndcg_mean"]), marker=marker, color=color, alpha=0.45)
            ax.scatter(float(rr["bew_mean"]), float(rr["ndcg_mean"]), marker=marker, edgecolors="black", facecolors=color)
            ax.annotate("", xy=(float(rr["bew_mean"]), float(rr["ndcg_mean"])), xytext=(float(uu["bew_mean"]), float(uu["ndcg_mean"])), arrowprops=dict(arrowstyle="->", color=color, lw=1))
    ax.set_xlabel("BEW")
    ax.set_ylabel("nDCG")
    ax.set_title("Structural vs retrieval tradeoff (tracked real pairwise runs)")
    fig.tight_layout()
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
