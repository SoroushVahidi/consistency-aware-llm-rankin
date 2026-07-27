#!/usr/bin/env python3
"""CLI for the fail-closed counterfactual micro-pilot / canary collector.

Exactly one mode is required: --dry-run, --cache-only, or --allow-provider-calls.
There is no default live mode. See docs/benchmarks/COUNTERFACTUAL_PILOT_FREEZE_V1.md.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from consistency_ranker.counterfactual_benchmark.collector import run_collection
from consistency_ranker.experiment_cli import assert_offline_or_allowed, utc_stamp

REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--config", type=Path, required=True, help="Path to a frozen collector config JSON."
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: reports/<benchmark_version>_<UTC>/).",
    )
    p.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Directory containing an existing normalized_judgments.jsonl to replay "
        "(cache-only mode). Defaults to --output-dir.",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--cache-only", action="store_true")
    p.add_argument("--allow-provider-calls", action="store_true")
    p.add_argument("--canary", action="store_true", help="Label outputs as a canary run.")
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow writing into a non-empty --output-dir (needed to resume a prior run).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    mode = assert_offline_or_allowed(
        allow_provider_calls=args.allow_provider_calls,
        dry_run=args.dry_run,
        cache_only=args.cache_only,
    )

    config_path: Path = args.config
    if not config_path.is_absolute():
        config_path = (REPO_ROOT / config_path).resolve()

    output_dir = args.output_dir
    if output_dir is None:
        stem = config_path.stem
        output_dir = REPO_ROOT / "reports" / f"{stem}_{utc_stamp()}"

    summary = run_collection(
        config_path=config_path,
        output_dir=output_dir,
        mode=mode,
        repo_root=REPO_ROOT,
        is_canary=args.canary,
        overwrite=args.overwrite,
        cache_dir=args.cache_dir,
    )

    print(f"Output directory: {output_dir}")
    for key, value in summary.items():
        if key != "missing_cells":
            print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
