"""
run_fas_balance_alpha_beta_grid.py
==================================
Focused low-cost grid sweep for fas_balance_score_prior_alpha_beta.

Outputs:
- docs/tables/fas_balance_alpha_beta_grid.csv
- docs/tables/fas_balance_alpha_beta_summary.csv
- docs/figures/fas_balance_alpha_beta_grid.png
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

# Allow running as `python scripts/run_fas_balance_alpha_beta_grid.py` from repo root
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


def _token(v: float) -> str:
    txt = f"{v:.3f}".rstrip("0").rstrip(".")
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
    p = argparse.ArgumentParser(description="Run focused alpha/beta grid for fas-balance hybrid.")
    p.add_argument("--n-items", type=int, default=20)
    p.add_argument("--noise", type=float, default=0.20)
    p.add_argument("--seeds", type=str, default="42,123,456,789,1234")
    p.add_argument("--alphas", type=str, default="0.5,1.0,2.0,4.0")
    p.add_argument("--betas", type=str, default="0.1,0.25,0.5,1.0")
    p.add_argument(
        "--prior-alpha-reference",
        type=float,
        default=2.0,
        help="Reference alpha for fas_balance_score_prior_alpha baseline method.",
    )
    p.add_argument("--weight-scheme", choices=["uniform", "margin"], default="margin")
    p.add_argument("--output-root", type=Path, default=Path("outputs/fas_balance_alpha_beta_grid"))
    p.add_argument("--tables-dir", type=Path, default=Path("docs/tables"))
    p.add_argument("--figures-dir", type=Path, default=Path("docs/figures"))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    seeds = _parse_int_csv(args.seeds)
    alphas = _parse_float_csv(args.alphas)
    betas = _parse_float_csv(args.betas)
    if not seeds:
        raise ValueError("No seeds provided.")
    if not alphas:
        raise ValueError("No alphas provided.")
    if not betas:
        raise ValueError("No betas provided.")

    methods = [
        "score_sum",
        "borda",
        "fas_weighted_balance",
        "hybrid_rrf_fas_regularized",
        "fas_balance_score_prior_alpha",
        "fas_balance_score_prior_alpha_beta",
    ]

    rows: list[dict] = []
    for alpha in alphas:
        for beta in betas:
            for seed in seeds:
                out_dir = (
                    args.output_root
                    / f"alpha_{_token(alpha)}_beta_{_token(beta)}_seed_{seed}"
                )
                res = run_experiment(
                    n_items=args.n_items,
                    noise=args.noise,
                    seed=seed,
                    weight_scheme=args.weight_scheme,
                    fas_balance_alpha=args.prior_alpha_reference,
                    fas_balance_alpha_beta_alpha=alpha,
                    fas_balance_alpha_beta_beta=beta,
                    output_dir=out_dir,
                    save_timings=False,
                    profile=False,
                )
                tau = res["evaluation"]["kendall_tau"]
                tau_borda = float(tau["borda"])
                tau_score_sum = float(tau["score_sum"])
                tau_hybrid = float(tau["hybrid_rrf_fas_regularized"])
                for method in methods:
                    k = float(tau[method])
                    rows.append(
                        {
                            "seed": seed,
                            "alpha": alpha,
                            "beta": beta,
                            "method": method,
                            "kendall_tau": round(k, 6),
                            "gap_to_borda": round(k - tau_borda, 6),
                            "gap_to_score_sum": round(k - tau_score_sum, 6),
                            "gap_to_hybrid_rrf_fas_regularized": round(k - tau_hybrid, 6),
                        }
                    )

    rows.sort(key=lambda r: (float(r["alpha"]), float(r["beta"]), int(r["seed"]), r["method"]))
    grid_table = args.tables_dir / "fas_balance_alpha_beta_grid.csv"
    _write_csv(
        grid_table,
        [
            "seed",
            "alpha",
            "beta",
            "method",
            "kendall_tau",
            "gap_to_borda",
            "gap_to_score_sum",
            "gap_to_hybrid_rrf_fas_regularized",
        ],
        rows,
    )

    summary_rows: list[dict] = []
    for alpha in alphas:
        for beta in betas:
            subset = [
                r
                for r in rows
                if float(r["alpha"]) == float(alpha)
                and float(r["beta"]) == float(beta)
                and r["method"] == "fas_balance_score_prior_alpha_beta"
            ]
            tau_vals = np.array([float(r["kendall_tau"]) for r in subset], dtype=float)
            gap_borda_vals = np.array([float(r["gap_to_borda"]) for r in subset], dtype=float)
            gap_ss_vals = np.array([float(r["gap_to_score_sum"]) for r in subset], dtype=float)
            gap_hybrid_vals = np.array(
                [float(r["gap_to_hybrid_rrf_fas_regularized"]) for r in subset],
                dtype=float,
            )
            summary_rows.append(
                {
                    "alpha": alpha,
                    "beta": beta,
                    "mean_tau": round(float(np.mean(tau_vals)), 6),
                    "std_tau": round(float(np.std(tau_vals, ddof=1)) if len(tau_vals) > 1 else 0.0, 6),
                    "mean_gap_to_borda": round(float(np.mean(gap_borda_vals)), 6),
                    "mean_gap_to_score_sum": round(float(np.mean(gap_ss_vals)), 6),
                    "mean_gap_to_hybrid_rrf_fas_regularized": round(
                        float(np.mean(gap_hybrid_vals)),
                        6,
                    ),
                }
            )
    summary_rows.sort(key=lambda r: (float(r["alpha"]), float(r["beta"])))
    summary_table = args.tables_dir / "fas_balance_alpha_beta_summary.csv"
    _write_csv(
        summary_table,
        [
            "alpha",
            "beta",
            "mean_tau",
            "std_tau",
            "mean_gap_to_borda",
            "mean_gap_to_score_sum",
            "mean_gap_to_hybrid_rrf_fas_regularized",
        ],
        summary_rows,
    )

    # Heatmap figure for mean tau of new method across (alpha, beta).
    args.figures_dir.mkdir(parents=True, exist_ok=True)
    fig_path = args.figures_dir / "fas_balance_alpha_beta_grid.png"
    alpha_sorted = sorted(alphas)
    beta_sorted = sorted(betas)
    z = np.zeros((len(alpha_sorted), len(beta_sorted)), dtype=float)
    for i, alpha in enumerate(alpha_sorted):
        for j, beta in enumerate(beta_sorted):
            row = next(
                r
                for r in summary_rows
                if float(r["alpha"]) == float(alpha) and float(r["beta"]) == float(beta)
            )
            z[i, j] = float(row["mean_tau"])

    plt.figure(figsize=(7.5, 5.5))
    im = plt.imshow(z, aspect="auto", cmap="viridis")
    plt.colorbar(im, label="mean Kendall tau")
    plt.xticks(range(len(beta_sorted)), [str(b) for b in beta_sorted])
    plt.yticks(range(len(alpha_sorted)), [str(a) for a in alpha_sorted])
    plt.xlabel("beta (repaired balance weight)")
    plt.ylabel("alpha (score_sum prior weight)")
    plt.title("fas_balance_score_prior_alpha_beta mean tau")
    for i in range(len(alpha_sorted)):
        for j in range(len(beta_sorted)):
            plt.text(j, i, f"{z[i, j]:.3f}", ha="center", va="center", color="white", fontsize=8)
    plt.tight_layout()
    plt.savefig(fig_path, dpi=180)
    plt.close()

    print(f"Wrote: {grid_table}")
    print(f"Wrote: {summary_table}")
    print(f"Wrote: {fig_path}")


if __name__ == "__main__":
    main()
