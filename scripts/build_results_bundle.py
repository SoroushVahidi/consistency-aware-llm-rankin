#!/usr/bin/env python
"""
Build final results bundle for the paper: tables, examples, plots.

Outputs:
  outputs/manuscript_bundle/
    tables/          CSV and markdown tables
    examples/        qualitative examples (copied/formatted)
    plots/           PNG plots
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

# Use paper_ready outputs as source
PAPER_DIR = REPO / "outputs" / "paper_ready"
BUNDLE_DIR = REPO / "outputs" / "manuscript_bundle"


def load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))


def main():
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
    (BUNDLE_DIR / "tables").mkdir(exist_ok=True)
    (BUNDLE_DIR / "examples").mkdir(exist_ok=True)
    (BUNDLE_DIR / "plots").mkdir(exist_ok=True)

    # --- Tables ---
    datasets = [
        ("fiqa", "bm25_dense"),
        ("fiqa", "bm25_dense_cross_encoder"),
        ("scidocs", "bm25_dense"),
    ]
    all_overall = []
    for dataset, scorers in datasets:
        csv_path = PAPER_DIR / f"{dataset}_paper_k20_{scorers}_n100.csv"
        rows = load_csv(csv_path)
        if not rows:
            continue
        n = len(rows)
        methods = ["bm25_raw", "dense_raw", "rrf_fusion", "greedy_fas_topological", "sel_bew25", "sel_hybrid"]
        row_out = {"dataset": dataset, "scorers": scorers, "n": n}
        for m in methods:
            k = f"ndcg_{m}" if f"ndcg_{m}" in rows[0] else f"ndcg_sel_{m[4:]}" if m.startswith("sel_") else None
            if k and k in rows[0]:
                row_out[m] = round(sum(float(r[k]) for r in rows) / n, 4)
        row_out["pct_cyclic"] = round(100 * sum(1 for r in rows if r.get("cyclic") == "True"), 1)
        row_out["bew_before"] = round(sum(float(r["bew_before"]) for r in rows) / n, 2)
        row_out["bew_after"] = round(sum(float(r["bew_after"]) for r in rows) / n, 2)
        all_overall.append(row_out)

    # Write overall table
    if all_overall:
        out_csv = BUNDLE_DIR / "tables" / "overall_ndcg_by_method_dataset.csv"
        with out_csv.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(all_overall[0].keys()))
            w.writeheader()
            w.writerows(all_overall)
        print(f"Wrote {out_csv}")

        # Markdown
        md = BUNDLE_DIR / "tables" / "overall_ndcg_by_method_dataset.md"
        cols = ["dataset", "scorers", "n"] + [m for m in methods if m in all_overall[0]]
        md.write_text("| " + " | ".join(cols) + " |\n" + "|" + "-" * (len("|".join(cols)) + 2) + "|\n" +
                      "\n".join("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |" for r in all_overall))
        print(f"Wrote {md}")

    # Policy ablation table
    policy_data = []
    for dataset, scorers in datasets:
        csv_path = PAPER_DIR / f"{dataset}_paper_k20_{scorers}_n100.csv"
        rows = load_csv(csv_path)
        if not rows:
            continue
        n = len(rows)
        for policy, col in [
            ("never", "ndcg_never"),
            ("always", "ndcg_always"),
            ("BEW_top25", "ndcg_sel_bew25"),
            ("disagreement_top25", "ndcg_sel_disc25"),
            ("hybrid", "ndcg_sel_hybrid"),
            ("learned", "ndcg_sel_learned"),
        ]:
            if col in rows[0]:
                policy_data.append({
                    "dataset": dataset, "scorers": scorers, "policy": policy,
                    "ndcg_at_10": round(sum(float(r[col]) for r in rows) / n, 4),
                })
    if policy_data:
        out_csv = BUNDLE_DIR / "tables" / "policy_ablation.csv"
        with out_csv.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["dataset", "scorers", "policy", "ndcg_at_10"])
            w.writeheader()
            w.writerows(policy_data)
        print(f"Wrote {out_csv}")

    # --- Examples ---
    for dataset, scorers in datasets:
        ex_src = PAPER_DIR / f"{dataset}_examples_{scorers}.jsonl"
        if ex_src.exists():
            shutil.copy(ex_src, BUNDLE_DIR / "examples" / f"{dataset}_{scorers}_examples.jsonl")
            print(f"Copied examples → {BUNDLE_DIR / 'examples' / f'{dataset}_{scorers}_examples.jsonl'}")

    # --- Plots (matplotlib) ---
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("matplotlib not available; skipping plots")
        return

    # Plot 1: Overall NDCG@10 by method and dataset
    if all_overall:
        fig, ax = plt.subplots(figsize=(8, 4))
        x = np.arange(len(all_overall))
        width = 0.12
        method_cols = [m for m in methods if m in all_overall[0]]
        for i, m in enumerate(method_cols):
            vals = [r.get(m, 0) for r in all_overall]
            ax.bar(x + i * width, vals, width, label=m.replace("_", " "))
        ax.set_xticks(x + width * (len(method_cols) - 1) / 2)
        ax.set_xticklabels([f"{r['dataset']}\n{r['scorers']}" for r in all_overall])
        ax.set_ylabel("NDCG@10")
        ax.set_title("Overall NDCG@10 by Method and Dataset")
        ax.legend(loc="upper right", fontsize=8)
        ax.set_ylim(0, 0.5)
        plt.tight_layout()
        plt.savefig(BUNDLE_DIR / "plots" / "overall_ndcg_by_method_dataset.png", dpi=150)
        plt.close()
        print(f"Wrote {BUNDLE_DIR / 'plots' / 'overall_ndcg_by_method_dataset.png'}")

    # Plot 2: Policy ablation
    if policy_data:
        fig, ax = plt.subplots(figsize=(8, 4))
        policies = list(dict.fromkeys(r["policy"] for r in policy_data))
        datasets_ = list(dict.fromkeys((r["dataset"], r["scorers"]) for r in policy_data))
        x = np.arange(len(policies))
        width = 0.25
        for i, (ds, sc) in enumerate(datasets_):
            vals = [next((r["ndcg_at_10"] for r in policy_data if r["dataset"] == ds and r["scorers"] == sc and r["policy"] == p), 0) for p in policies]
            ax.bar(x + i * width, vals, width, label=f"{ds} {sc}")
        ax.set_xticks(x + width)
        ax.set_xticklabels(policies, rotation=30, ha="right")
        ax.set_ylabel("NDCG@10")
        ax.set_title("Selective-Repair Ablation by Policy")
        ax.legend()
        ax.set_ylim(0, 0.45)
        plt.tight_layout()
        plt.savefig(BUNDLE_DIR / "plots" / "policy_ablation.png", dpi=150)
        plt.close()
        print(f"Wrote {BUNDLE_DIR / 'plots' / 'policy_ablation.png'}")

    # Plot 3: % cyclic and avg BEW by scorer combination
    if all_overall:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
        labels = [f"{r['dataset']}\n{r['scorers']}" for r in all_overall]
        ax1.bar(labels, [r["pct_cyclic"] for r in all_overall], color="steelblue")
        ax1.set_ylabel("% Cyclic")
        ax1.set_title("% Cyclic Graphs by Scorer Combination")
        ax1.set_ylim(0, 110)
        ax2.bar(labels, [r["bew_before"] for r in all_overall], color="coral", alpha=0.7, label="before")
        ax2.bar(labels, [r["bew_after"] for r in all_overall], color="green", alpha=0.5, label="after")
        ax2.set_ylabel("Avg BEW")
        ax2.set_title("BEW Before/After FAS")
        ax2.legend()
        plt.tight_layout()
        plt.savefig(BUNDLE_DIR / "plots" / "cyclic_bew_by_scorers.png", dpi=150)
        plt.close()
        print(f"Wrote {BUNDLE_DIR / 'plots' / 'cyclic_bew_by_scorers.png'}")

    # Plot 4 & 5: Performance vs conflict bucket, win-rate (need per-query data)
    for dataset, scorers in datasets:
        csv_path = PAPER_DIR / f"{dataset}_paper_k20_{scorers}_n100.csv"
        rows = load_csv(csv_path)
        if not rows or len(rows) < 4:
            continue
        bew_vals = sorted([float(r["bew_before"]) for r in rows])
        q1, q2, q3 = bew_vals[len(rows)//4], bew_vals[len(rows)//2], bew_vals[3*len(rows)//4]
        buckets = [
            ("low", [r for r in rows if float(r["bew_before"]) < q2]),
            ("high", [r for r in rows if float(r["bew_before"]) >= q2]),
        ]
        if not buckets[0][1] or not buckets[1][1]:
            continue
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
        names = ["low BEW", "high BEW"]
        rrf_vals = [sum(float(r["ndcg_rrf_fusion"]) for r in b) / len(b) for _, b in buckets]
        fas_vals = [sum(float(r["ndcg_greedy_fas_topological"]) for r in b) / len(b) for _, b in buckets]
        x = np.arange(2)
        ax1.bar(x - 0.2, rrf_vals, 0.4, label="RRF")
        ax1.bar(x + 0.2, fas_vals, 0.4, label="FAS")
        ax1.set_xticks(x)
        ax1.set_xticklabels(names)
        ax1.set_ylabel("NDCG@10")
        ax1.set_title(f"Performance vs Conflict ({dataset} {scorers})")
        ax1.legend()
        win_rates = [100 * sum(1 for r in b if float(r["ndcg_greedy_fas_topological"]) > float(r["ndcg_rrf_fusion"])) / len(b) for _, b in buckets]
        ax2.bar(names, win_rates, color="green", alpha=0.7)
        ax2.set_ylabel("% FAS beats RRF")
        ax2.set_title(f"FAS Win-Rate by Conflict Bucket ({dataset})")
        ax2.set_ylim(0, 60)
        plt.tight_layout()
        plt.savefig(BUNDLE_DIR / "plots" / f"conflict_bucket_{dataset}_{scorers}.png", dpi=150)
        plt.close()
        print(f"Wrote {BUNDLE_DIR / 'plots' / f'conflict_bucket_{dataset}_{scorers}.png'}")

    # Learned selector table (if exists)
    learned_dir = REPO / "outputs" / "learned_selector"
    if learned_dir.exists():
        learned_files = list(learned_dir.glob("*_learned_selector.csv"))
        if learned_files:
            all_learned = []
            for f in learned_files:
                stem = f.stem.replace("_learned_selector", "")
                parts = stem.split("_", 1)
                dataset = parts[0] if len(parts) >= 1 else "unknown"
                scorers = parts[1] if len(parts) >= 2 else ""
                with f.open() as fp:
                    for row in csv.DictReader(fp):
                        row["dataset"] = dataset
                        row["scorers"] = scorers
                        all_learned.append(row)
            if all_learned:
                out_csv = BUNDLE_DIR / "tables" / "learned_selector_ablation.csv"
                fn = ["dataset", "scorers", "policy", "ndcg_at_10"]
                with out_csv.open("w", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=fn, extrasaction="ignore")
                    w.writeheader()
                    w.writerows(all_learned)
                print(f"Wrote {out_csv}")

    print(f"\nBundle complete: {BUNDLE_DIR}")


if __name__ == "__main__":
    main()
