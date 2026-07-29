#!/usr/bin/env python
"""
run_oracle_headroom_analysis.py
================================
Gate-0 analysis for the preserve-vs-repair research question: is there
enough per-query heterogeneity in the repair effect (delta_q = M_q(repair)
- M_q(preserve)) to justify attempting a learned preserve-vs-repair
selector at all? See docs/research/RESEARCH_TRAJECTORY.md and
docs/research/EXPERIMENT_ROADMAP.md for the full framing.

Reads an ALREADY-EXISTING per-query preserve/repair outcome CSV (default:
the committed reports/candidate_pool_conditional_audit_20260714/tables/
pool_robustness_paired_deltas.csv, 46,170 rows across 4 datasets). Makes NO
new experiment calls, no LLM calls, no network calls. Computes: oracle
headroom with a bootstrap CI, per-query delta distribution, regression and
three-way labels with an epsilon-sensitivity table, and a leakage-safe
grouped train/validation/test split -- then stops. This script does NOT
train a predictive model; that is deliberately gated behind a separate,
not-yet-implemented step (see the roadmap doc's predictive-signal gate).

Example:
    python scripts/run_oracle_headroom_analysis.py \\
        --dataset scidocs --regime ms1 --pool-id rrf_union_topk \\
        --pair-name copeland_graph \\
        --output-dir reports/oracle_headroom_scidocs_ms1_copeland
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from consistency_ranker.repair_selector_mining.grouped_splits import split_records  # noqa: E402
from consistency_ranker.repair_selector_mining.label_generation import (  # noqa: E402
    label_sensitivity_table,
)
from consistency_ranker.repair_selector_mining.oracle_headroom import (  # noqa: E402
    compute_oracle_headroom,
    evaluate_go_no_go,
    load_paired_delta_records,
    write_oracle_headroom_report,
)

DEFAULT_INPUT_CSV = (
    _REPO_ROOT
    / "reports/candidate_pool_conditional_audit_20260714/tables/pool_robustness_paired_deltas.csv"
)
DEFAULT_EPSILON_GRID = (0.0, 0.0025, 0.005, 0.01, 0.02, 0.05)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--dataset", type=str, default=None, help="e.g. scidocs, fiqa, hotpotqa, bright"
    )
    parser.add_argument("--regime", type=str, default=None, help="e.g. ms1, ms2, ms1_drop_mutual")
    parser.add_argument("--pool-id", type=str, default=None)
    parser.add_argument("--pair-name", type=str, default=None, help="e.g. copeland_graph")
    parser.add_argument("--query-id-col", type=str, default="query_id")
    parser.add_argument("--unrepaired-col", type=str, default="unrepaired_ndcg")
    parser.add_argument("--repaired-col", type=str, default="repaired_ndcg")
    parser.add_argument("--dataset-col", type=str, default="dataset")
    parser.add_argument("--headroom-threshold", type=float, default=0.01)
    parser.add_argument("--min-heterogeneity-fraction", type=float, default=0.05)
    parser.add_argument("--bootstrap-reps", type=int, default=10_000)
    parser.add_argument("--bootstrap-seed", type=int, default=13)
    parser.add_argument("--split-seed", type=int, default=42)
    parser.add_argument(
        "--epsilon-grid",
        type=float,
        nargs="+",
        default=list(DEFAULT_EPSILON_GRID),
        help="Candidate thresholds for the three-way beneficial/neutral/harmful label",
    )
    args = parser.parse_args()

    extra_filters: dict[str, str] = {}
    if args.regime is not None:
        extra_filters["regime"] = args.regime
    if args.pool_id is not None:
        extra_filters["pool_id"] = args.pool_id
    if args.pair_name is not None:
        extra_filters["pair_name"] = args.pair_name

    records = load_paired_delta_records(
        args.input_csv,
        dataset=args.dataset,
        query_id_col=args.query_id_col,
        unrepaired_col=args.unrepaired_col,
        repaired_col=args.repaired_col,
        dataset_col=args.dataset_col,
        extra_filters=extra_filters,
    )
    if not records:
        raise SystemExit(
            f"No records loaded from {args.input_csv} with filters "
            f"dataset={args.dataset!r}, {extra_filters!r} -- check the filter values "
            "against the CSV's actual column values before re-running."
        )
    print(f"Loaded {len(records)} preserve/repair records from {args.input_csv}")

    result = compute_oracle_headroom(
        records, bootstrap_reps=args.bootstrap_reps, bootstrap_seed=args.bootstrap_seed
    )
    decision = evaluate_go_no_go(
        result,
        headroom_threshold=args.headroom_threshold,
        min_heterogeneity_fraction=args.min_heterogeneity_fraction,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_oracle_headroom_report(
        result,
        decision,
        args.output_dir,
        input_csv=args.input_csv,
        filters={**({"dataset": args.dataset} if args.dataset else {}), **extra_filters},
    )

    sensitivity = label_sensitivity_table(records, args.epsilon_grid)
    with (args.output_dir / "label_sensitivity.json").open("w") as f:
        json.dump([row.__dict__ for row in sensitivity], f, indent=2)

    train, val, test = split_records(records, seed=args.split_seed)
    with (args.output_dir / "split_sizes.json").open("w") as f:
        json.dump(
            {
                "seed": args.split_seed,
                "n_train": len(train),
                "n_validation": len(val),
                "n_test": len(test),
                "n_total": len(records),
                "n_unassigned": len(records) - len(train) - len(val) - len(test),
            },
            f,
            indent=2,
        )

    print(f"Gate-0 decision: {decision.decision}")
    print(f"Headroom: {result.headroom_vs_best_baseline:.6f} "
          f"CI=[{result.headroom_ci.lower:.6f}, {result.headroom_ci.upper:.6f}]")
    print(f"Wrote report to {args.output_dir}")


if __name__ == "__main__":
    main()
