"""
run_fas_balance_alpha_beta_generalization.py
============================================
Focused generalization check for:
fas_balance_score_prior_alpha_beta(alpha=1.0, beta=0.1)

Outputs:
- docs/tables/fas_balance_alpha_beta_generalization.csv
- docs/tables/fas_balance_alpha_beta_generalization_summary.csv
- docs/figures/fas_balance_alpha_beta_generalization_vs_noise.png
- docs/figures/fas_balance_alpha_beta_multiseed_promising_noises.png
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

# Allow running as `python scripts/run_fas_balance_alpha_beta_generalization.py`
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


def _noise_token(noise: float) -> str:
    return f"{noise:.2f}".replace(".", "p")


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generalization check for tuned alpha-beta FAS hybrid.")
    p.add_argument("--n-items", type=int, default=20)
    p.add_argument("--noise-values", type=str, default="0.05,0.10,0.15,0.20,0.25,0.30")
    p.add_argument("--sweep-seed", type=int, default=42)
    p.add_argument("--multi-seeds", type=str, default="42,123,456,789,1234")
    p.add_argument("--alpha", type=float, default=1.0)
    p.add_argument("--beta", type=float, default=0.1)
    p.add_argument("--weight-scheme", choices=["uniform", "margin"], default="margin")
    p.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/fas_balance_alpha_beta_generalization"),
    )
    p.add_argument("--tables-dir", type=Path, default=Path("docs/tables"))
    p.add_argument("--figures-dir", type=Path, default=Path("docs/figures"))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    noises = _parse_float_csv(args.noise_values)
    multi_seeds = _parse_int_csv(args.multi_seeds)
    if not noises:
        raise ValueError("No noise values provided.")
    if not multi_seeds:
        raise ValueError("No multi-seeds provided.")

    methods = [
        "borda",
        "score_sum",
        "fas_weighted_balance",
        "hybrid_rrf_fas_regularized",
        "fas_balance_score_prior_alpha_beta",
    ]

    # Step 1: noise sweep with single seed
    sweep_taus: dict[float, dict[str, float]] = {}
    for noise in noises:
        out_dir = args.output_root / f"sweep_noise_{_noise_token(noise)}_seed_{args.sweep_seed}"
        res = run_experiment(
            n_items=args.n_items,
            noise=noise,
            seed=args.sweep_seed,
            weight_scheme=args.weight_scheme,
            fas_balance_alpha_beta_alpha=args.alpha,
            fas_balance_alpha_beta_beta=args.beta,
            output_dir=out_dir,
            save_timings=False,
            profile=False,
        )
        tau = res["evaluation"]["kendall_tau"]
        sweep_taus[noise] = {m: float(tau[m]) for m in methods}

    # Pick two most promising noises based on mean gap to the three baseline comparators.
    noise_scores: list[tuple[float, float]] = []
    for noise in noises:
        new_tau = sweep_taus[noise]["fas_balance_score_prior_alpha_beta"]
        score = np.mean(
            [
                new_tau - sweep_taus[noise]["borda"],
                new_tau - sweep_taus[noise]["score_sum"],
                new_tau - sweep_taus[noise]["hybrid_rrf_fas_regularized"],
            ]
        )
        noise_scores.append((noise, float(score)))
    noise_scores.sort(key=lambda x: x[1], reverse=True)
    promising_noises = [noise_scores[0][0], noise_scores[1][0]]

    # Step 2: add multi-seed checks on promising noises (union with sweep runs).
    regimes: set[tuple[float, int]] = {(noise, args.sweep_seed) for noise in noises}
    for noise in promising_noises:
        for seed in multi_seeds:
            regimes.add((noise, seed))

    rows: list[dict] = []
    taus_by_regime: dict[tuple[float, int], dict[str, float]] = {}
    for noise, seed in sorted(regimes, key=lambda t: (t[0], t[1])):
        # Reuse sweep result when possible.
        if seed == args.sweep_seed and noise in sweep_taus:
            tau_map = sweep_taus[noise]
        else:
            out_dir = args.output_root / f"multi_noise_{_noise_token(noise)}_seed_{seed}"
            res = run_experiment(
                n_items=args.n_items,
                noise=noise,
                seed=seed,
                weight_scheme=args.weight_scheme,
                fas_balance_alpha_beta_alpha=args.alpha,
                fas_balance_alpha_beta_beta=args.beta,
                output_dir=out_dir,
                save_timings=False,
                profile=False,
            )
            tau = res["evaluation"]["kendall_tau"]
            tau_map = {m: float(tau[m]) for m in methods}
        taus_by_regime[(noise, seed)] = tau_map
        for method in methods:
            k = tau_map[method]
            rows.append(
                {
                    "noise": f"{noise:.2f}",
                    "seed": seed,
                    "method": method,
                    "kendall_tau": round(k, 6),
                    "gap_to_borda": round(k - tau_map["borda"], 6),
                    "gap_to_score_sum": round(k - tau_map["score_sum"], 6),
                    "gap_to_hybrid_rrf_fas_regularized": round(
                        k - tau_map["hybrid_rrf_fas_regularized"],
                        6,
                    ),
                }
            )
    rows.sort(key=lambda r: (float(r["noise"]), int(r["seed"]), r["method"]))

    table_a = args.tables_dir / "fas_balance_alpha_beta_generalization.csv"
    _write_csv(
        table_a,
        [
            "noise",
            "seed",
            "method",
            "kendall_tau",
            "gap_to_borda",
            "gap_to_score_sum",
            "gap_to_hybrid_rrf_fas_regularized",
        ],
        rows,
    )

    # Summary by noise/method
    grouped: dict[tuple[float, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(float(row["noise"]), row["method"])].append(row)

    summary_rows: list[dict] = []
    for (noise, method), g in sorted(grouped.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        vals = np.array([float(r["kendall_tau"]) for r in g], dtype=float)
        win_borda = sum(1 for r in g if float(r["gap_to_borda"]) > 0.0)
        win_ss = sum(1 for r in g if float(r["gap_to_score_sum"]) > 0.0)
        win_h = sum(1 for r in g if float(r["gap_to_hybrid_rrf_fas_regularized"]) > 0.0)
        summary_rows.append(
            {
                "noise": f"{noise:.2f}",
                "method": method,
                "mean_tau": round(float(np.mean(vals)), 6),
                "std_tau": round(float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0, 6),
                "win_count_vs_borda": win_borda,
                "win_count_vs_score_sum": win_ss,
                "win_count_vs_hybrid_rrf_fas_regularized": win_h,
            }
        )
    table_b = args.tables_dir / "fas_balance_alpha_beta_generalization_summary.csv"
    _write_csv(
        table_b,
        [
            "noise",
            "method",
            "mean_tau",
            "std_tau",
            "win_count_vs_borda",
            "win_count_vs_score_sum",
            "win_count_vs_hybrid_rrf_fas_regularized",
        ],
        summary_rows,
    )

    # Figure 1: mean tau vs noise
    args.figures_dir.mkdir(parents=True, exist_ok=True)
    fig1 = args.figures_dir / "fas_balance_alpha_beta_generalization_vs_noise.png"
    method_order = methods
    plt.figure(figsize=(8, 5))
    for method in method_order:
        mrows = [r for r in summary_rows if r["method"] == method]
        mrows.sort(key=lambda r: float(r["noise"]))
        xs = [float(r["noise"]) for r in mrows]
        ys = [float(r["mean_tau"]) for r in mrows]
        plt.plot(xs, ys, marker="o", label=method)
    plt.xlabel("noise")
    plt.ylabel("mean Kendall tau")
    plt.title("Generalization: tuned alpha-beta method vs noise")
    plt.grid(alpha=0.3)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(fig1, dpi=170)
    plt.close()

    # Figure 2: multi-seed focused view for promising noises
    fig2 = args.figures_dir / "fas_balance_alpha_beta_multiseed_promising_noises.png"
    prom_rows = [r for r in summary_rows if float(r["noise"]) in set(promising_noises)]
    prom_noises_sorted = sorted(set(float(r["noise"]) for r in prom_rows))
    # only methods we compare
    methods_plot = method_order
    x = np.arange(len(prom_noises_sorted))
    width = 0.15
    plt.figure(figsize=(10, 5))
    for i, method in enumerate(methods_plot):
        vals = []
        errs = []
        for n in prom_noises_sorted:
            row = next(r for r in prom_rows if float(r["noise"]) == n and r["method"] == method)
            vals.append(float(row["mean_tau"]))
            errs.append(float(row["std_tau"]))
        offset = (i - (len(methods_plot) - 1) / 2) * width
        plt.bar(x + offset, vals, width=width, label=method, yerr=errs, capsize=3)
    plt.xticks(x, [f"{n:.2f}" for n in prom_noises_sorted])
    plt.xlabel("promising noise levels")
    plt.ylabel("mean Kendall tau")
    plt.title("Multi-seed check on promising noises")
    plt.grid(axis="y", alpha=0.3)
    plt.legend(fontsize=8, ncol=2)
    plt.tight_layout()
    plt.savefig(fig2, dpi=170)
    plt.close()

    print(f"Promising noises selected from sweep: {', '.join(f'{n:.2f}' for n in promising_noises)}")
    print(f"Wrote: {table_a}")
    print(f"Wrote: {table_b}")
    print(f"Wrote: {fig1}")
    print(f"Wrote: {fig2}")


if __name__ == "__main__":
    main()
