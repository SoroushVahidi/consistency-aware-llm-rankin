#!/usr/bin/env python3
"""
Offline cost–accuracy analysis from committed outputs (no API calls).

Loads baseline ranking summaries, cross-encoder runtimes, and cached OpenAI pilot
summaries. Writes plots and CSV tables under outputs/analysis/.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ANALYSIS = ROOT / "outputs" / "analysis"

# --- Primary baseline package (qrels, full method grid) ---
REF_SUMMARY_GLOBS = {
    "scidocs": ROOT
    / "outputs"
    / "final_modern_baselines_reference"
    / "scidocs"
    / "qrels"
    / "scidocs_summary.csv",
    "hotpotqa": ROOT
    / "outputs"
    / "final_modern_baselines_reference"
    / "hotpotqa"
    / "qrels"
    / "hotpotqa_summary.csv",
    "bright": ROOT
    / "outputs"
    / "final_modern_baselines_reference"
    / "bright"
    / "qrels"
    / "bright_summary.csv",
    "fiqa": ROOT / "outputs" / "real_full" / "fiqa" / "qrels" / "fiqa_summary.csv",
}

# Cross-encoder accuracy + BEW (no wall-clock in this file for FiQA mock rows)
MODERN_BASELINE_SUMMARY = {
    "scidocs": ROOT
    / "outputs"
    / "final_modern_baselines"
    / "scidocs"
    / "scidocs_modern_baselines_summary.csv",
    "hotpotqa": ROOT
    / "outputs"
    / "final_modern_baselines"
    / "hotpotqa"
    / "hotpotqa_modern_baselines_summary.csv",
    "bright": ROOT
    / "outputs" / "final_modern_baselines" / "bright" / "bright_modern_baselines_summary.csv",
    "fiqa": ROOT
    / "outputs"
    / "modern_baselines"
    / "fiqa"
    / "fiqa_modern_baselines_summary.csv",
}

OPENAI_PILOTS = [
    {
        "dataset": "scidocs",
        "summary": ROOT
        / "outputs"
        / "openai_scidocs_real_run_q20_k15"
        / "openai_summary.csv",
        "config": ROOT / "outputs" / "openai_scidocs_real_run_q20_k15" / "config.json",
    },
    {
        "dataset": "hotpotqa",
        "summary": ROOT
        / "outputs"
        / "openai_hotpotqa_real_run_q10_k15"
        / "openai_summary.csv",
        "config": ROOT / "outputs" / "openai_hotpotqa_real_run_q10_k15" / "config.json",
    },
]

REQUESTED_REASONING = (
    "reasoning_greedy",
    "self_consistency_3",
    "self_consistency_5",
    "direct_plus_revise",
    "reasoning_then_revise",
)

LAMBDAS = (0.10, 0.25)
BUDGET_MULTIPLIERS = (1.1, 1.3, 1.5, float("inf"))


def _load_json(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def load_ref_blockers() -> tuple[list[str], list[Path]]:
    """Return (messages, missing paths)."""
    missing: list[Path] = []
    msgs: list[str] = []
    for ds, p in REF_SUMMARY_GLOBS.items():
        if not p.is_file():
            missing.append(p)
            msgs.append(
                f"Missing baseline summary for {ds}: {p} "
                "(final_modern_baselines_reference / real_full)"
            )
    return msgs, missing


def load_cross_encoder_blockers() -> tuple[list[str], list[Path]]:
    missing: list[Path] = []
    msgs: list[str] = []
    for ds, p in MODERN_BASELINE_SUMMARY.items():
        if not p.is_file():
            missing.append(p)
            msgs.append(f"Missing modern baseline summary for {ds}: {p}")
    return msgs, missing


def load_openai_blockers() -> tuple[list[str], list[Path]]:
    missing: list[Path] = []
    msgs: list[str] = []
    for row in OPENAI_PILOTS:
        for key in ("summary", "config"):
            p = row[key]
            if not p.is_file():
                missing.append(p)
                msgs.append(f"Missing OpenAI pilot {key}: {p}")
    return msgs, missing


def build_baseline_frame_v2() -> pd.DataFrame:
    """Load reference summaries and merge cross-encoder rows with accurate runtimes."""
    parts: list[pd.DataFrame] = []
    for dataset, path in REF_SUMMARY_GLOBS.items():
        df = pd.read_csv(path)
        df.insert(0, "dataset", dataset)
        df["source"] = "baseline_qrels_summary"
        df["preference_source"] = "qrels"
        parts.append(df)
    base = pd.concat(parts, ignore_index=True)
    base = base.rename(columns={"runtime_mean_s": "avg_cost", "ndcg_mean": "accuracy"})
    base = base[
        [
            "dataset",
            "method",
            "accuracy",
            "avg_cost",
            "source",
            "preference_source",
        ]
    ]

    ce_rows = []
    for dataset, path in MODERN_BASELINE_SUMMARY.items():
        mb = pd.read_csv(path)
        ce = mb[mb["method"] == "cross_encoder"]
        if ce.empty:
            continue
        rt_match = base[(base["dataset"] == dataset) & (base["method"] == "cross_encoder")]
        if len(rt_match):
            rt = float(rt_match["avg_cost"].iloc[0])
        else:
            ss = (base["dataset"] == dataset) & (base["method"] == "score_sum")
            rt = float(base.loc[ss, "avg_cost"].iloc[0])
        ce_rows.append(
            {
                "dataset": dataset,
                "method": "cross_encoder",
                "accuracy": float(ce.iloc[0]["ndcg_mean"]),
                "avg_cost": rt,
                "source": "modern_baselines_cross_encoder",
                "preference_source": "cross_encoder",
            }
        )
    if ce_rows:
        base = base[~base["method"].eq("cross_encoder")]
        base = pd.concat([base, pd.DataFrame(ce_rows)], ignore_index=True)
    return base


def load_openai_pilots() -> pd.DataFrame:
    rows: list[dict] = []
    for spec in OPENAI_PILOTS:
        ds = spec["dataset"]
        cfg = _load_json(spec["config"])
        cost = float(cfg["cost_estimate_usd"])
        summary = pd.read_csv(spec["summary"])
        for _, r in summary.iterrows():
            rows.append(
                {
                    "dataset": ds,
                    "method": str(r["method"]) + "_openai_pilot",
                    "accuracy": float(r["ndcg_mean"]),
                    "avg_cost": cost,
                    "source": "openai_pairwise_pilot",
                    "preference_source": "llm_pairwise_cached",
                    "pilot_cost_usd_shared": cost,
                }
            )
    return pd.DataFrame(rows)


def attach_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["revise_rate"] = np.nan
    out["extra_compute_rate"] = np.nan
    for ds in out["dataset"].unique():
        m = out["dataset"] == ds
        sub = out.loc[m, "avg_cost"]
        base = float(sub.min())
        if base > 0 and np.isfinite(base):
            out.loc[m, "extra_compute_rate"] = out.loc[m, "avg_cost"] / base
    return out


def oracle_accuracy_per_dataset(df: pd.DataFrame) -> dict[str, float]:
    orch = {}
    for ds in df["dataset"].unique():
        sub = df[df["dataset"] == ds]
        orch[ds] = float(sub["accuracy"].max())
    return orch


def pareto_frontier(df: pd.DataFrame) -> pd.DataFrame:
    """One row per method with frontier flag and optional dominator list."""
    all_rows: list[dict] = []
    for ds in df["dataset"].unique():
        sub = df[df["dataset"] == ds].copy()
        methods = sub.to_dict("records")
        for row in methods:
            a, c, m = row["accuracy"], row["avg_cost"], row["method"]
            dominated = False
            dominators: list[str] = []
            for other in methods:
                if other["method"] == m:
                    continue
                if other["accuracy"] >= a and other["avg_cost"] <= c:
                    if other["accuracy"] > a or other["avg_cost"] < c:
                        dominated = True
                        dominators.append(other["method"])
            all_rows.append(
                {
                    "dataset": ds,
                    "method": m,
                    "accuracy": a,
                    "avg_cost": c,
                    "on_pareto_frontier": not dominated,
                    "dominated_by": ";".join(sorted(set(dominators))) if dominators else "",
                }
            )
    return pd.DataFrame(all_rows)


def regret_tables(
    df: pd.DataFrame, oracle: dict[str, float], lambdas: tuple[float, ...]
) -> pd.DataFrame:
    rows: list[dict] = []
    for ds in df["dataset"].unique():
        sub = df[df["dataset"] == ds]
        cmax = float(sub["avg_cost"].max())
        oacc = oracle[ds]
        for _, r in sub.iterrows():
            acc = float(r["accuracy"])
            cost = float(r["avg_cost"])
            cn = cost / cmax if cmax > 0 else 0.0
            row = {
                "dataset": ds,
                "method": r["method"],
                "accuracy": acc,
                "avg_cost": cost,
                "oracle_accuracy": oacc,
                "regret_accuracy": oacc - acc,
            }
            for lam in lambdas:
                u_o = oacc - lam * cn
                u_m = acc - lam * cn
                row[f"oracle_utility_lambda_{lam:.2f}"] = u_o
                row[f"method_utility_lambda_{lam:.2f}"] = u_m
                row[f"regret_utility_lambda_{lam:.2f}"] = u_o - u_m
            rows.append(row)
    return pd.DataFrame(rows)


def decision_table(df: pd.DataFrame, oracle: dict[str, float]) -> pd.DataFrame:
    rows: list[dict] = []
    for ds in df["dataset"].unique():
        sub = df[df["dataset"] == ds].copy()
        base_cost = float(sub["avg_cost"].min())
        for cap in BUDGET_MULTIPLIERS:
            if np.isfinite(cap):
                eligible = sub[sub["avg_cost"] <= base_cost * cap]
                label = f"budget_le_{cap:.2f}x_min_runtime"
            else:
                eligible = sub
                label = "budget_unconstrained"
            if eligible.empty:
                best_method = None
                best_acc = float("nan")
            else:
                idx = eligible["accuracy"].idxmax()
                best_method = eligible.loc[idx, "method"]
                best_acc = float(eligible.loc[idx, "accuracy"])
            rows.append(
                {
                    "dataset": ds,
                    "budget_rule": label,
                    "baseline_cost_min_runtime_s": base_cost,
                    "budget_cap_multiplier": cap if np.isfinite(cap) else "inf",
                    "best_method_by_accuracy": best_method,
                    "best_accuracy": best_acc,
                    "oracle_accuracy": oracle[ds],
                    "gap_to_oracle": (
                        oracle[ds] - best_acc if np.isfinite(best_acc) else float("nan")
                    ),
                }
            )
    return pd.DataFrame(rows)


def _plot_subset(ds: str, df: pd.DataFrame, oracle_acc: float, out_path: Path, note: str) -> None:
    sub = df[df["dataset"] == ds].sort_values("avg_cost")
    sub = sub[np.isfinite(sub["avg_cost"]) & np.isfinite(sub["accuracy"])]
    plt.figure(figsize=(8, 5))
    colors = plt.cm.tab20(np.linspace(0, 1, max(len(sub), 2)))
    for i, (_, r) in enumerate(sub.iterrows()):
        plt.scatter(
            r["avg_cost"],
            r["accuracy"],
            s=80,
            color=colors[i % len(colors)],
            edgecolors="black",
            linewidths=0.3,
            zorder=3,
        )
        plt.annotate(
            r["method"],
            (r["avg_cost"], r["accuracy"]),
            textcoords="offset points",
            xytext=(4, 4),
            fontsize=7,
            alpha=0.85,
        )
    plt.axhline(
        oracle_acc,
        color="crimson",
        linestyle="--",
        linewidth=1,
        label="oracle (max nDCG)",
        zorder=1,
    )
    plt.plot(
        sub["avg_cost"].values,
        sub["accuracy"].values,
        color="gray",
        alpha=0.35,
        linewidth=1,
        zorder=2,
    )
    plt.xlabel("Cost proxy (wall time s for baselines; USD for OpenAI pilot)")
    plt.ylabel("Accuracy (nDCG@k mean)")
    plt.title(f"{ds}: cost vs accuracy{note}")
    plt.legend(loc="lower right")
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150)
    plt.close()


def plot_cost_accuracy(ds: str, df: pd.DataFrame, oracle_acc: float, out_path: Path) -> None:
    """Prefer methods below the qrels nDCG ceiling plus LLM pilots (informative tradeoffs)."""
    full = df[df["dataset"] == ds]
    disc = full[
        (full["accuracy"] < 0.9999)
        | full["method"].str.contains("openai", case=False, na=False)
        | (full["method"] == "cross_encoder")
    ]
    if len(disc) >= 2:
        _plot_subset(ds, disc, oracle_acc, out_path, " (sub-oracle / LLM-relevant methods)")
    else:
        _plot_subset(ds, full, oracle_acc, out_path, " (all methods)")


def cross_dataset_summary(df: pd.DataFrame, oracle: dict[str, float]) -> pd.DataFrame:
    rows = []
    for ds in sorted(df["dataset"].unique()):
        sub = df[df["dataset"] == ds]
        cheap = sub.loc[sub["avg_cost"].idxmin()]
        hi = sub.loc[sub["accuracy"].idxmax()]
        # Cost sensitivity: accuracy range / log-spread of cost
        costs = sub["avg_cost"].values
        costs = costs[np.isfinite(costs) & (costs > 0)]
        acc_spread = float(sub["accuracy"].max() - sub["accuracy"].min())
        cost_spread_ratio = (
            float(np.max(costs) / np.min(costs)) if len(costs) >= 2 else float("nan")
        )
        rows.append(
            {
                "dataset": ds,
                "oracle_accuracy": oracle[ds],
                "best_accuracy_method": hi["method"],
                "best_accuracy": float(hi["accuracy"]),
                "cheapest_method": cheap["method"],
                "cheapest_cost": float(cheap["avg_cost"]),
                "accuracy_spread_ndcg": acc_spread,
                "cost_ratio_max_over_min": cost_spread_ratio,
                "revise_helpful_rate": np.nan,
                "notes": "revise_helpful_rate not logged in these outputs",
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    blockers: list[str] = []
    missing_paths: list[Path] = []

    m1, p1 = load_ref_blockers()
    blockers.extend(m1)
    missing_paths.extend(p1)
    m2, p2 = load_cross_encoder_blockers()
    blockers.extend(m2)
    missing_paths.extend(p2)
    m3, p3 = load_openai_blockers()
    blockers.extend(m3)
    missing_paths.extend(p3)

    if missing_paths:
        print("BLOCKER: missing input files:", file=sys.stderr)
        for p in missing_paths:
            print(f"  {p}", file=sys.stderr)

    baseline = build_baseline_frame_v2()
    pilots = load_openai_pilots()
    unified = pd.concat([baseline, pilots], ignore_index=True)
    unified = attach_derived_columns(unified)

    # Requested reasoning-routing experiment tree (not in this repository snapshot)
    for name in REQUESTED_REASONING:
        blockers.append(
            f"Expected reasoning/routing method '{name}' not found in outputs/ or data/. "
            "Depends on experiment: real_policy_eval / multi_action_models (not present)."
        )

    oracle = oracle_accuracy_per_dataset(unified)
    unified["oracle_accuracy"] = unified["dataset"].map(oracle)

    OUTPUT_ANALYSIS.mkdir(parents=True, exist_ok=True)
    unified.to_csv(OUTPUT_ANALYSIS / "unified_results.csv", index=False)

    pareto = pareto_frontier(unified)
    regrets = regret_tables(unified, oracle, LAMBDAS)
    decisions = decision_table(unified, oracle)
    cross = cross_dataset_summary(unified, oracle)

    for ds in sorted(unified["dataset"].unique()):
        pareto[pareto["dataset"] == ds].to_csv(OUTPUT_ANALYSIS / f"{ds}_pareto.csv", index=False)
        regrets[regrets["dataset"] == ds].to_csv(
            OUTPUT_ANALYSIS / f"{ds}_regret.csv", index=False
        )
        decisions[decisions["dataset"] == ds].to_csv(
            OUTPUT_ANALYSIS / f"{ds}_decision_table.csv", index=False
        )
        plot_cost_accuracy(
            ds,
            unified,
            oracle[ds],
            OUTPUT_ANALYSIS / f"{ds}_cost_accuracy_curve.png",
        )

    cross.to_csv(OUTPUT_ANALYSIS / "cross_dataset_insights.csv", index=False)

    blocker_path = OUTPUT_ANALYSIS / "blocker_report.txt"
    with blocker_path.open("w") as f:
        msg = "\n".join(blockers) if blockers else "No file blockers detected for loaded inputs.\n"
        f.write(msg)
        f.write("\n\nMissing paths:\n")
        f.write("\n".join(str(p) for p in sorted(set(missing_paths), key=str)) or "(none)\n")
        f.write("\n\nNote: GSM8K / MATH500 / Hard GSM8K not present under outputs/ or data/.\n")
        f.write(
            "OpenAI pilot rows share one cost_estimate_usd per run "
            "(not per-method marginal cost).\n"
        )

    print(f"Wrote analysis bundle under {OUTPUT_ANALYSIS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
