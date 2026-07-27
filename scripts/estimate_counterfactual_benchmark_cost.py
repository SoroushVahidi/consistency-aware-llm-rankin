#!/usr/bin/env python3
"""Offline call-count planner for the real counterfactual benchmark.

Performs arithmetic only. Never contacts providers. Never invents prices.
Optional --prices-json may supply blended or per-provider USD/request figures.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from consistency_ranker.experiment_cli import ensure_output_dir, utc_stamp, write_run_manifest
from consistency_ranker.provider_capability.cost_estimate import write_plans

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Default: reports/counterfactual_cost_plan_<UTC>",
    )
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument(
        "--prices-json",
        type=Path,
        default=None,
        help='Optional JSON object, e.g. {"blended": 0.002}. Missing => cost unknown.',
    )
    args = ap.parse_args()
    stamp = utc_stamp()
    out_dir = ensure_output_dir(
        (
            args.output_dir
            or (REPO_ROOT / "reports" / f"counterfactual_cost_plan_{stamp}")
        ).resolve(),
        overwrite=args.overwrite,
    )
    prices = None
    if args.prices_json is not None:
        prices = json.loads(args.prices_json.read_text())
        if not isinstance(prices, dict):
            raise SystemExit("--prices-json must be a JSON object")
    plans = write_plans(out_dir / "cost_plans.json", prices=prices)
    config = {
        "timestamp": stamp,
        "prices_provided": bool(prices),
        "price_keys": sorted(prices) if prices else [],
        "offline": True,
        "paid_api_calls": 0,
    }
    (out_dir / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    write_run_manifest(
        out_dir,
        script="scripts/estimate_counterfactual_benchmark_cost.py",
        config=config,
        repo_root=REPO_ROOT,
    )
    # Human summary
    lines = [
        "# Counterfactual benchmark cost plan (offline)",
        "",
        "No provider requests were made. Monetary cost is unknown unless prices were supplied.",
        "",
    ]
    for name, plan in plans["plans"].items():
        lines += [
            f"## {name}",
            "",
            f"- goal: {plan['goal']}",
            f"- queries: {plan['n_queries_total']}",
            f"- pool_size: {plan['pool_size']} (eval_k={plan['eval_k']})",
            f"- live logged-shell requests: {plan['live_logged_shell_requests']}",
            f"- naive per-policy live replay multiplier: "
            f"{plan['if_naively_repeated_per_policy_live']}",
            f"- complete matrix requests: {plan['complete_matrix_requests']}",
            f"- cost: {plan['cost']}",
            "",
        ]
    (out_dir / "FINAL_REPORT.md").write_text("\n".join(lines))
    print(f"Wrote {out_dir}")
    for name, plan in plans["plans"].items():
        print(
            f"{name}: logged={plan['live_logged_shell_requests']} "
            f"matrix={plan['complete_matrix_requests']}"
        )


if __name__ == "__main__":
    main()
