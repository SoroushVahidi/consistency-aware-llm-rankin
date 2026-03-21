"""
run_variant_followup.py
=======================
Follow-up synthetic experiment focused on post-repair FAS extraction variants.

This script runs:
1) A noise sweep at fixed seed (default seed=42, noise in 0.05..0.30).
2) A multi-seed check at fixed noise (default noise=0.20, 5 seeds).

It writes three tables to ``docs/tables/``:
- variant_followup_main_results.csv
- variant_followup_summary.csv
- variant_followup_win_counts.csv
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from scripts.run_synthetic import run_experiment


BASE_METHODS = [
    "score_sum",
    "borda",
    "greedy_fas_topological",
    "priority_topological_score_sum",
    "fas_weighted_balance",
]


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


def _regime_output_dir(
    output_root: Path,
    *,
    noise: float,
    seed: int,
    noise_seed: int,
    noise_values: set[float],
) -> Path:
    if seed == noise_seed and noise in noise_values:
        return output_root / f"noise_sweep_n{noise:.2f}"
    return output_root / f"multi_seed_noise{noise:.2f}_seed{seed}"


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run follow-up synthetic FAS variant study and write summary tables."
    )
    p.add_argument("--n-items", type=int, default=20)
    p.add_argument("--noise-values", type=str, default="0.05,0.10,0.15,0.20,0.25,0.30")
    p.add_argument("--noise-seed", type=int, default=42)
    p.add_argument("--multi-noise", type=float, default=0.20)
    p.add_argument("--multi-seeds", type=str, default="42,123,456,789,1234")
    p.add_argument("--weight-scheme", choices=["uniform", "margin"], default="margin")
    p.add_argument("--output-root", type=Path, default=Path("outputs/variant_followup"))
    p.add_argument("--tables-dir", type=Path, default=Path("docs/tables"))
    p.add_argument("--include-fas-copeland", action="store_true", default=False)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    noise_values = _parse_float_csv(args.noise_values)
    multi_seeds = _parse_int_csv(args.multi_seeds)
    if not noise_values:
        raise ValueError("No noise values were provided.")
    if not multi_seeds:
        raise ValueError("No multi-seed values were provided.")

    methods = list(BASE_METHODS)
    if args.include_fas_copeland:
        methods.append("fas_copeland")

    # Union of regimes from both requested analyses (deduplicated).
    regime_set: set[tuple[int, float, int]] = set()
    for noise in noise_values:
        regime_set.add((args.noise_seed, noise, args.n_items))
    for seed in multi_seeds:
        regime_set.add((seed, args.multi_noise, args.n_items))
    regimes = sorted(regime_set, key=lambda t: (t[1], t[0], t[2]))

    main_rows: list[dict] = []
    by_regime_method: dict[tuple[int, float, int], dict[str, float]] = {}
    by_method_taus: dict[str, list[float]] = defaultdict(list)

    for seed, noise, n_items in regimes:
        out_dir = _regime_output_dir(
            args.output_root,
            noise=noise,
            seed=seed,
            noise_seed=args.noise_seed,
            noise_values=set(noise_values),
        )
        res = run_experiment(
            n_items=n_items,
            noise=noise,
            seed=seed,
            weight_scheme=args.weight_scheme,
            output_dir=out_dir,
            save_timings=True,
            profile=False,
        )

        taus = res["evaluation"]["kendall_tau"]
        metrics = res.get("method_metrics", {})

        regime_key = (seed, noise, n_items)
        by_regime_method[regime_key] = {}
        for method in methods:
            if method not in taus:
                continue
            mm = metrics.get(method, {})
            tau = float(taus[method])
            row = {
                "seed": seed,
                "noise": f"{noise:.2f}",
                "n_items": n_items,
                "method": method,
                "kendall_tau": round(tau, 6),
                "inconsistency_before": int(mm.get("inconsistency_before", 0)),
                "inconsistency_after": int(mm.get("inconsistency_after", 0)),
                "removed_edges": int(mm.get("removed_edges", 0)),
                "removed_weight": round(float(mm.get("removed_weight", 0.0)), 6),
                "runtime_total_s": round(float(mm.get("runtime_total_s", 0.0)), 6),
                "runtime_repair_s": round(float(mm.get("runtime_repair_s", 0.0)), 6),
            }
            main_rows.append(row)
            by_regime_method[regime_key][method] = tau
            by_method_taus[method].append(tau)

    main_rows.sort(key=lambda r: (float(r["noise"]), int(r["seed"]), r["method"]))

    main_path = args.tables_dir / "variant_followup_main_results.csv"
    _write_csv(
        main_path,
        [
            "seed",
            "noise",
            "n_items",
            "method",
            "kendall_tau",
            "inconsistency_before",
            "inconsistency_after",
            "removed_edges",
            "removed_weight",
            "runtime_total_s",
            "runtime_repair_s",
        ],
        main_rows,
    )

    mean_tau: dict[str, float] = {}
    std_tau: dict[str, float] = {}
    for method, vals in by_method_taus.items():
        if not vals:
            continue
        mu = sum(vals) / len(vals)
        mean_tau[method] = mu
        if len(vals) <= 1:
            std_tau[method] = 0.0
        else:
            var = sum((v - mu) ** 2 for v in vals) / (len(vals) - 1)
            std_tau[method] = var**0.5

    best_method = max(mean_tau, key=lambda m: mean_tau[m]) if mean_tau else ""
    borda_mu = mean_tau.get("borda", 0.0)
    score_sum_mu = mean_tau.get("score_sum", 0.0)
    summary_rows: list[dict] = []
    for method in sorted(mean_tau):
        summary_rows.append(
            {
                "method": method,
                "mean_tau": round(mean_tau[method], 6),
                "std_tau": round(std_tau.get(method, 0.0), 6),
                "best_method": best_method,
                "gap_to_borda": round(mean_tau[method] - borda_mu, 6),
                "gap_to_score_sum": round(mean_tau[method] - score_sum_mu, 6),
            }
        )
    summary_path = args.tables_dir / "variant_followup_summary.csv"
    _write_csv(
        summary_path,
        ["method", "mean_tau", "std_tau", "best_method", "gap_to_borda", "gap_to_score_sum"],
        summary_rows,
    )

    win_counts = {m: 0 for m in by_method_taus}
    beats_borda = {m: 0 for m in by_method_taus}
    beats_score_sum = {m: 0 for m in by_method_taus}
    for method_scores in by_regime_method.values():
        if not method_scores:
            continue
        best_tau = max(method_scores.values())
        for method, tau in method_scores.items():
            if tau >= best_tau - 1e-12:
                win_counts[method] += 1
            if "borda" in method_scores and tau > method_scores["borda"]:
                beats_borda[method] += 1
            if "score_sum" in method_scores and tau > method_scores["score_sum"]:
                beats_score_sum[method] += 1

    win_rows = []
    for method in sorted(by_method_taus):
        win_rows.append(
            {
                "method": method,
                "n_regimes_won": win_counts.get(method, 0),
                "n_times_beats_borda": beats_borda.get(method, 0),
                "n_times_beats_score_sum": beats_score_sum.get(method, 0),
            }
        )
    wins_path = args.tables_dir / "variant_followup_win_counts.csv"
    _write_csv(
        wins_path,
        ["method", "n_regimes_won", "n_times_beats_borda", "n_times_beats_score_sum"],
        win_rows,
    )

    print(f"Wrote: {main_path}")
    print(f"Wrote: {summary_path}")
    print(f"Wrote: {wins_path}")


if __name__ == "__main__":
    main()
