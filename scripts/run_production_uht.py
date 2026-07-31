#!/usr/bin/env python3
"""Production entry point for the interim operating point: always UHT + safety floor.

Executes exactly one policy (UHT) with the approved non-routing safeguards. It
cannot load a calibration model, cannot select challenger/hybrid, and rejects
``--mode experimental_gate``. Judgments come from local synthetic judges, so the
command never issues a billed external call.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from consistency_ranker.policy_selection.execution_mode import ExecutionMode
from consistency_ranker.policy_selection.policy_benchmark import build_world
from consistency_ranker.policy_selection.production_config import (
    PRODUCTION_OPERATING_POINT,
    ProductionPolicyConfig,
)
from consistency_ranker.policy_selection.production_runner import run_production_uht

PRODUCTION_MODES = (ExecutionMode.PRODUCTION_UHT.value, ExecutionMode.DIAGNOSTIC.value)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=(
            "Run the production operating point: always UHT plus the approved safety "
            "floor (mandatory outsider probe, no weak-evidence stop, final challenger "
            "check). Learned gates are EXPERIMENTAL and are not reachable from here."
        ),
        epilog=(
            "Diagnostic mode records gate features and a recommendation for analysis; "
            "it does NOT alter routing. The executed policy is UHT in every mode."
        ),
    )
    ap.add_argument(
        "--mode",
        default=ExecutionMode.PRODUCTION_UHT.value,
        choices=list(PRODUCTION_MODES),
        help=(
            "production_uht (default): UHT + safety floor, no diagnostics. "
            "diagnostic: additionally runs the fixed 3-call mixed_diagnostic probe and "
            "records a non-routing recommendation."
        ),
    )
    ap.add_argument("--prior-regime", default="outsider_buried")
    ap.add_argument("--judge-regime", default="clean")
    ap.add_argument("--n-items", type=int, default=8)
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--budget", type=int, default=16)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--record-diagnostics",
        action="store_true",
        help="Record diagnostic probe output in production mode (still non-routing).",
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    # Environment variables must never influence routing; this is the only place
    # the environment is consulted and it is refused.
    for var in os.environ:
        if var.startswith("CONSISTENCY_RANKER_GATE"):
            ap.error(
                f"Environment variable {var} cannot configure policy routing. "
                "Experimental gates require an explicit request to the research runner."
            )
    mode = ExecutionMode(args.mode)
    cfg = ProductionPolicyConfig(record_diagnostics=bool(args.record_diagnostics))

    world = build_world(
        prior_regime=args.prior_regime,
        judge_regime=args.judge_regime,
        seed=args.seed,
        n_items=args.n_items,
        top_k=args.top_k,
    )
    result = run_production_uht(
        world=world,
        budget=args.budget,
        top_k=args.top_k,
        seed=args.seed,
        config=cfg,
        execution_mode=mode,
    )
    print(
        json.dumps(
            {
                "resolved_execution_mode": mode.value,
                "executed_primary_policy": result.executed_policy,
                "diagnostic_recommendation": result.diagnostic_recommendation,
                "experimental_policy": result.experimental_policy,
                "learned_gate_active": False,
                "operating_point": PRODUCTION_OPERATING_POINT.to_dict(),
                "resolved_config": cfg.to_dict(),
                "safeguards": result.safeguards.to_dict(),
                "n_calls": result.n_calls,
                "topk_jaccard": result.outcome.topk_jaccard,
                "utility": result.utility,
                "ranking": result.ranking,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
