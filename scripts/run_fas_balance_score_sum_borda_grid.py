"""
run_fas_balance_score_sum_borda_grid.py
=======================================
Focused low-cost sweep for Borda-aware hybrid:
fas_balance_score_sum_borda_hybrid.

Outputs:
- docs/tables/fas_balance_score_sum_borda_grid.csv
- docs/tables/fas_balance_score_sum_borda_summary.csv
- docs/figures/fas_balance_score_sum_borda_heatmap_noise025.png
- docs/figures/fas_balance_score_sum_borda_heatmap_noise030.png
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

# Allow running as `python scripts/run_fas_balance_score_sum_borda_grid.py`
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


def _noise_label(noise: float) -> str:
    return f"{int(round(noise * 100)):03d}"


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run focused Borda-aware hybrid sweep.")
    p.add_argument("--n-items", type=int, default=20)
    p.add_argument("--noises", type=str, default="0.25,0.30")
    p.add_argument("--seeds", type=str, default="42,123,456,789,1234")
    p.add_argument("--betas", type=str, default="0.05,0.1,0.25")
    p.add_argument("--alpha-s-values", type=str, default="0.5,1.0")
    p.add_argument("--alpha-b-values", type=str, default="0.5,1.0,2.0")
    p.add_argument("--weight-scheme", choices=["uniform", "margin"], default="margin")
    p.add_argument(
        "--prev-alpha-beta-alpha",
        type=float,
        default=1.0,
        help="Fixed alpha for previous fas_balance_score_prior_alpha_beta baseline.",
    )
    p.add_argument(
        "--prev-alpha-beta-beta",
        type=float,
        default=0.1,
        help="Fixed beta for previous fas_balance_score_prior_alpha_beta baseline.",
    )
    p.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/fas_balance_score_sum_borda_grid"),
    )
    p.add_argument("--tables-dir", type=Path, default=Path("docs/tables"))
    p.add_argument("--figures-dir", type=Path, default=Path("docs/figures"))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    noises = _parse_float_csv(args.noises)
    seeds = _parse_int_csv(args.seeds)
    betas = _parse_float_csv(args.betas)
    alpha_s_values = _parse_float_csv(args.alpha_s_values)
    alpha_b_values = _parse_float_csv(args.alpha_b_values)
    if not noises:
        raise ValueError("No noises provided.")
    if not seeds:
        raise ValueError("No seeds provided.")
    if not betas:
        raise ValueError("No betas provided.")
    if not alpha_s_values:
        raise ValueError("No alpha_s values provided.")
    if not alpha_b_values:
        raise ValueError("No alpha_b values provided.")

    methods = [
        "borda",
        "score_sum",
        "fas_weighted_balance",
        "hybrid_rrf_fas_regularized",
        "fas_balance_score_prior_alpha_beta",
        "fas_balance_score_sum_borda_hybrid",
    ]

    rows: list[dict] = []
    for noise in noises:
        for alpha_s in alpha_s_values:
            for alpha_b in alpha_b_values:
                for beta in betas:
                    for seed in seeds:
                        out_dir = (
                            args.output_root
                            / f"noise_{_token(noise)}"
                            / f"as_{_token(alpha_s)}_ab_{_token(alpha_b)}_b_{_token(beta)}"
                            / f"seed_{seed}"
                        )
                        res = run_experiment(
                            n_items=args.n_items,
                            noise=noise,
                            seed=seed,
                            weight_scheme=args.weight_scheme,
                            fas_balance_alpha_beta_alpha=args.prev_alpha_beta_alpha,
                            fas_balance_alpha_beta_beta=args.prev_alpha_beta_beta,
                            fas_balance_ss_borda_alpha_s=alpha_s,
                            fas_balance_ss_borda_alpha_b=alpha_b,
                            fas_balance_ss_borda_beta=beta,
                            output_dir=out_dir,
                            save_timings=False,
                            profile=False,
                        )
                        tau = res["evaluation"]["kendall_tau"]
                        tau_borda = float(tau["borda"])
                        tau_score_sum = float(tau["score_sum"])
                        tau_hybrid = float(tau["hybrid_rrf_fas_regularized"])
                        tau_prev = float(tau["fas_balance_score_prior_alpha_beta"])
                        for method in methods:
                            k = float(tau[method])
                            rows.append(
                                {
                                    "noise": f"{noise:.2f}",
                                    "seed": seed,
                                    "alpha_s": alpha_s,
                                    "alpha_b": alpha_b,
                                    "beta": beta,
                                    "method": method,
                                    "kendall_tau": round(k, 6),
                                    "gap_to_borda": round(k - tau_borda, 6),
                                    "gap_to_score_sum": round(k - tau_score_sum, 6),
                                    "gap_to_hybrid_rrf_fas_regularized": round(
                                        k - tau_hybrid,
                                        6,
                                    ),
                                    "gap_to_fas_balance_score_prior_alpha_beta": round(
                                        k - tau_prev,
                                        6,
                                    ),
                                }
                            )
    rows.sort(
        key=lambda r: (
            float(r["noise"]),
            float(r["alpha_s"]),
            float(r["alpha_b"]),
            float(r["beta"]),
            int(r["seed"]),
            r["method"],
        )
    )
    table_a = args.tables_dir / "fas_balance_score_sum_borda_grid.csv"
    _write_csv(
        table_a,
        [
            "noise",
            "seed",
            "alpha_s",
            "alpha_b",
            "beta",
            "method",
            "kendall_tau",
            "gap_to_borda",
            "gap_to_score_sum",
            "gap_to_hybrid_rrf_fas_regularized",
            "gap_to_fas_balance_score_prior_alpha_beta",
        ],
        rows,
    )

    # Summary for the new Borda-aware method only.
    summary_rows: list[dict] = []
    for noise in noises:
        for alpha_s in alpha_s_values:
            for alpha_b in alpha_b_values:
                for beta in betas:
                    subset = [
                        r
                        for r in rows
                        if float(r["noise"]) == float(noise)
                        and float(r["alpha_s"]) == float(alpha_s)
                        and float(r["alpha_b"]) == float(alpha_b)
                        and float(r["beta"]) == float(beta)
                        and r["method"] == "fas_balance_score_sum_borda_hybrid"
                    ]
                    taus = np.array([float(r["kendall_tau"]) for r in subset], dtype=float)
                    gap_borda = np.array([float(r["gap_to_borda"]) for r in subset], dtype=float)
                    gap_ss = np.array([float(r["gap_to_score_sum"]) for r in subset], dtype=float)
                    gap_h = np.array(
                        [float(r["gap_to_hybrid_rrf_fas_regularized"]) for r in subset],
                        dtype=float,
                    )
                    gap_prev = np.array(
                        [float(r["gap_to_fas_balance_score_prior_alpha_beta"]) for r in subset],
                        dtype=float,
                    )
                    summary_rows.append(
                        {
                            "noise": f"{noise:.2f}",
                            "alpha_s": alpha_s,
                            "alpha_b": alpha_b,
                            "beta": beta,
                            "mean_tau": round(float(np.mean(taus)), 6),
                            "std_tau": round(
                                float(np.std(taus, ddof=1)) if len(taus) > 1 else 0.0,
                                6,
                            ),
                            "mean_gap_to_borda": round(float(np.mean(gap_borda)), 6),
                            "mean_gap_to_score_sum": round(float(np.mean(gap_ss)), 6),
                            "mean_gap_to_hybrid_rrf_fas_regularized": round(float(np.mean(gap_h)), 6),
                            "mean_gap_to_fas_balance_score_prior_alpha_beta": round(
                                float(np.mean(gap_prev)),
                                6,
                            ),
                        }
                    )
    summary_rows.sort(
        key=lambda r: (
            float(r["noise"]),
            float(r["alpha_s"]),
            float(r["alpha_b"]),
            float(r["beta"]),
        )
    )
    table_b = args.tables_dir / "fas_balance_score_sum_borda_summary.csv"
    _write_csv(
        table_b,
        [
            "noise",
            "alpha_s",
            "alpha_b",
            "beta",
            "mean_tau",
            "std_tau",
            "mean_gap_to_borda",
            "mean_gap_to_score_sum",
            "mean_gap_to_hybrid_rrf_fas_regularized",
            "mean_gap_to_fas_balance_score_prior_alpha_beta",
        ],
        summary_rows,
    )

    # Heatmaps per noise: rows=beta, cols=alpha_b; one panel per alpha_s.
    args.figures_dir.mkdir(parents=True, exist_ok=True)
    for noise in noises:
        fig_path = args.figures_dir / f"fas_balance_score_sum_borda_heatmap_noise{_noise_label(noise)}.png"
        fig, axes = plt.subplots(1, len(alpha_s_values), figsize=(5.5 * len(alpha_s_values), 4.6))
        if len(alpha_s_values) == 1:
            axes = [axes]
        vmin = min(
            float(r["mean_tau"]) for r in summary_rows if float(r["noise"]) == float(noise)
        )
        vmax = max(
            float(r["mean_tau"]) for r in summary_rows if float(r["noise"]) == float(noise)
        )
        for ax, alpha_s in zip(axes, alpha_s_values):
            z = np.zeros((len(betas), len(alpha_b_values)), dtype=float)
            for i, beta in enumerate(betas):
                for j, alpha_b in enumerate(alpha_b_values):
                    row = next(
                        r
                        for r in summary_rows
                        if float(r["noise"]) == float(noise)
                        and float(r["alpha_s"]) == float(alpha_s)
                        and float(r["alpha_b"]) == float(alpha_b)
                        and float(r["beta"]) == float(beta)
                    )
                    z[i, j] = float(row["mean_tau"])
            im = ax.imshow(z, aspect="auto", cmap="viridis", vmin=vmin, vmax=vmax)
            ax.set_xticks(range(len(alpha_b_values)))
            ax.set_xticklabels([str(v) for v in alpha_b_values])
            ax.set_yticks(range(len(betas)))
            ax.set_yticklabels([str(v) for v in betas])
            ax.set_xlabel("alpha_b")
            ax.set_ylabel("beta")
            ax.set_title(f"noise={noise:.2f}, alpha_s={alpha_s}")
            for i in range(len(betas)):
                for j in range(len(alpha_b_values)):
                    ax.text(j, i, f"{z[i, j]:.3f}", ha="center", va="center", color="white", fontsize=8)
        fig.colorbar(im, ax=axes, label="mean Kendall tau", shrink=0.9)
        fig.suptitle("fas_balance_score_sum_borda_hybrid sweep", y=1.02)
        fig.tight_layout()
        fig.savefig(fig_path, dpi=180, bbox_inches="tight")
        plt.close(fig)

    print(f"Wrote: {table_a}")
    print(f"Wrote: {table_b}")
    for noise in noises:
        print(
            f"Wrote: "
            f"{args.figures_dir / f'fas_balance_score_sum_borda_heatmap_noise{_noise_label(noise)}.png'}"
        )


if __name__ == "__main__":
    main()
