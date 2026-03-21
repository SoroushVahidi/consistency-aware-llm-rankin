"""
run_fas_balance_alpha_sweep.py
==============================
Low-cost synthetic alpha sweep for fas_balance_score_prior_alpha.

Outputs:
- docs/tables/fas_balance_alpha_sweep.csv
- docs/tables/fas_balance_alpha_summary.csv
- docs/figures/fas_balance_alpha_sweep.png
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

# Allow running as `python scripts/run_fas_balance_alpha_sweep.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_synthetic import run_experiment


def _parse_float_csv(raw: str) -> list[float]:
    vals: list[float] = []
    for tok in raw.split(","):
        t = tok.strip()
        if not t:
            continue
        vals.append(float(t))
    return vals


def _parse_int_csv(raw: str) -> list[int]:
    vals: list[int] = []
    for tok in raw.split(","):
        t = tok.strip()
        if not t:
            continue
        vals.append(int(t))
    return vals


def _alpha_token(alpha: float) -> str:
    txt = f"{alpha:.3f}".rstrip("0").rstrip(".")
    if "." not in txt:
        txt = f"{txt}.0"
    return txt.replace(".", "p")


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run low-cost alpha sweep for fas_balance hybrid.")
    p.add_argument("--n-items", type=int, default=20)
    p.add_argument("--noise", type=float, default=0.20)
    p.add_argument("--seeds", type=str, default="42,123,456,789,1234")
    p.add_argument("--alphas", type=str, default="0.0,0.25,0.5,1.0,2.0")
    p.add_argument("--weight-scheme", choices=["uniform", "margin"], default="margin")
    p.add_argument("--output-root", type=Path, default=Path("outputs/fas_balance_alpha_sweep"))
    p.add_argument("--tables-dir", type=Path, default=Path("docs/tables"))
    p.add_argument("--figures-dir", type=Path, default=Path("docs/figures"))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    seeds = _parse_int_csv(args.seeds)
    alphas = _parse_float_csv(args.alphas)
    if not seeds:
        raise ValueError("No seeds provided.")
    if not alphas:
        raise ValueError("No alpha values provided.")

    methods = [
        "score_sum",
        "borda",
        "fas_weighted_balance",
        "hybrid_rrf_fas_regularized",
        "fas_balance_score_prior_alpha",
    ]

    rows: list[dict] = []
    for alpha in alphas:
        for seed in seeds:
            out_dir = args.output_root / f"alpha_{_alpha_token(alpha)}_seed_{seed}"
            res = run_experiment(
                n_items=args.n_items,
                noise=args.noise,
                seed=seed,
                weight_scheme=args.weight_scheme,
                fas_balance_alpha=alpha,
                output_dir=out_dir,
                save_timings=False,
                profile=False,
            )
            tau = res["evaluation"]["kendall_tau"]
            tau_borda = float(tau["borda"])
            tau_score_sum = float(tau["score_sum"])
            for method in methods:
                k = float(tau[method])
                rows.append(
                    {
                        "seed": seed,
                        "alpha": alpha,
                        "method": method,
                        "kendall_tau": round(k, 6),
                        "gap_to_borda": round(k - tau_borda, 6),
                        "gap_to_score_sum": round(k - tau_score_sum, 6),
                    }
                )

    rows.sort(key=lambda r: (float(r["alpha"]), int(r["seed"]), r["method"]))
    table_a = args.tables_dir / "fas_balance_alpha_sweep.csv"
    _write_csv(
        table_a,
        ["seed", "alpha", "method", "kendall_tau", "gap_to_borda", "gap_to_score_sum"],
        rows,
    )

    summary_rows: list[dict] = []
    for alpha in alphas:
        alpha_rows = [
            r
            for r in rows
            if float(r["alpha"]) == float(alpha)
            and r["method"] == "fas_balance_score_prior_alpha"
        ]
        tau_vals = np.array([float(r["kendall_tau"]) for r in alpha_rows], dtype=float)
        gap_borda_vals = np.array([float(r["gap_to_borda"]) for r in alpha_rows], dtype=float)
        gap_ss_vals = np.array([float(r["gap_to_score_sum"]) for r in alpha_rows], dtype=float)
        summary_rows.append(
            {
                "alpha": alpha,
                "mean_tau": round(float(np.mean(tau_vals)), 6),
                "std_tau": round(float(np.std(tau_vals, ddof=1)) if len(tau_vals) > 1 else 0.0, 6),
                "mean_gap_to_borda": round(float(np.mean(gap_borda_vals)), 6),
                "mean_gap_to_score_sum": round(float(np.mean(gap_ss_vals)), 6),
            }
        )
    summary_rows.sort(key=lambda r: float(r["alpha"]))
    table_b = args.tables_dir / "fas_balance_alpha_summary.csv"
    _write_csv(
        table_b,
        ["alpha", "mean_tau", "std_tau", "mean_gap_to_borda", "mean_gap_to_score_sum"],
        summary_rows,
    )

    # Plot alpha performance for new method, plus horizontal baseline references.
    fig_path = args.figures_dir / "fas_balance_alpha_sweep.png"
    args.figures_dir.mkdir(parents=True, exist_ok=True)
    x = [float(r["alpha"]) for r in summary_rows]
    y = [float(r["mean_tau"]) for r in summary_rows]
    yerr = [float(r["std_tau"]) for r in summary_rows]

    # Use first alpha slice for baseline/hybrid references (they are alpha-invariant).
    first_alpha = alphas[0]
    ref_rows = [r for r in rows if float(r["alpha"]) == float(first_alpha)]
    def _mean_for(method: str) -> float:
        vals = [float(r["kendall_tau"]) for r in ref_rows if r["method"] == method]
        return float(np.mean(np.array(vals, dtype=float)))

    plt.figure(figsize=(8, 5))
    plt.errorbar(
        x,
        y,
        yerr=yerr,
        marker="o",
        linewidth=2,
        capsize=4,
        label="fas_balance_score_prior_alpha",
    )
    plt.axhline(_mean_for("fas_weighted_balance"), linestyle="--", linewidth=1.4, label="fas_weighted_balance")
    plt.axhline(
        _mean_for("hybrid_rrf_fas_regularized"),
        linestyle="--",
        linewidth=1.4,
        label="hybrid_rrf_fas_regularized",
    )
    plt.axhline(_mean_for("score_sum"), linestyle=":", linewidth=1.4, label="score_sum")
    plt.axhline(_mean_for("borda"), linestyle=":", linewidth=1.4, label="borda")
    plt.xlabel("alpha")
    plt.ylabel("Mean Kendall tau (5 seeds)")
    plt.title("fas_balance_score_prior_alpha: tau vs alpha")
    plt.grid(alpha=0.3)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(fig_path, dpi=170)
    plt.close()

    print(f"Wrote: {table_a}")
    print(f"Wrote: {table_b}")
    print(f"Wrote: {fig_path}")


if __name__ == "__main__":
    main()
