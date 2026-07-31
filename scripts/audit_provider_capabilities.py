#!/usr/bin/env python3
"""Bounded provider-capability audit (Fireworks / Azure / Vertex / Cohere).

Fail-closed execution modes (exactly one required):
  --cache-only
  --dry-run
  --allow-provider-calls

Hard live caps (defaults match the overnight safety envelope):
  --max-total-live-calls 16
  --max-live-calls-per-provider 4
  --max-estimated-cost-usd 2.0
  --max-input-tokens 100000
  --max-output-tokens 12000

Never prints or stores credential values. Project IDs and endpoints are redacted.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from consistency_ranker.experiment_cli import (
    ensure_output_dir,
    utc_stamp,
    write_run_manifest,
)
from consistency_ranker.provider_capability.audit_engine import (
    render_final_report,
    resolve_mode,
    run_provider_audit,
)
from consistency_ranker.provider_capability.fixture import fixture_hash, prompt_hash
from consistency_ranker.provider_capability.schema import AUDIT_PROVIDERS

REPO_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--providers",
        nargs="+",
        default=list(AUDIT_PROVIDERS),
        choices=list(AUDIT_PROVIDERS),
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--allow-provider-calls", action="store_true")
    parser.add_argument("--max-total-live-calls", type=int, default=16)
    parser.add_argument("--max-live-calls-per-provider", type=int, default=4)
    parser.add_argument("--max-estimated-cost-usd", type=float, default=2.0)
    parser.add_argument("--max-input-tokens", type=int, default=100_000)
    parser.add_argument("--max-output-tokens", type=int, default=12_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Default: reports/provider_capability_audit_<UTC>",
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--allow-optional-call4",
        action="store_true",
        help="Reserved; currently records a skip (no native rerank adapter).",
    )
    args = parser.parse_args(argv)

    mode = resolve_mode(
        allow_provider_calls=args.allow_provider_calls,
        dry_run=args.dry_run,
        cache_only=args.cache_only,
    )
    stamp = utc_stamp()
    out_dir = ensure_output_dir(
        (
            args.output_dir
            or (REPO_ROOT / "reports" / f"provider_capability_audit_{stamp}")
        ).resolve(),
        overwrite=args.overwrite,
    )

    config = {
        "mode": mode,
        "providers": list(args.providers),
        "seed": args.seed,
        "max_total_live_calls": args.max_total_live_calls,
        "max_live_calls_per_provider": args.max_live_calls_per_provider,
        "max_estimated_cost_usd": args.max_estimated_cost_usd,
        "max_input_tokens": args.max_input_tokens,
        "max_output_tokens": args.max_output_tokens,
        "allow_optional_call4": bool(args.allow_optional_call4),
        "fixture_hash": fixture_hash(),
        "prompt_hash": prompt_hash(),
        "paid_api_calls_allowed": mode == "live",
        "timestamp": stamp,
    }
    (out_dir / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    write_run_manifest(
        out_dir,
        script="scripts/audit_provider_capabilities.py",
        config=config,
        repo_root=REPO_ROOT,
    )

    result = run_provider_audit(
        providers=list(args.providers),
        mode=mode,
        out_dir=out_dir,
        seed=args.seed,
        max_total_live_calls=args.max_total_live_calls,
        max_live_calls_per_provider=args.max_live_calls_per_provider,
        max_estimated_cost_usd=args.max_estimated_cost_usd,
        max_input_tokens=args.max_input_tokens,
        max_output_tokens_budget=args.max_output_tokens,
        allow_optional_call4=bool(args.allow_optional_call4),
    )
    (out_dir / "AUDIT_RESULT.json").write_text(
        json.dumps(result, indent=2, default=str) + "\n"
    )
    (out_dir / "FINAL_REPORT.md").write_text(render_final_report(result))

    print(f"Wrote {out_dir}")
    print(f"mode={mode} paid_api_calls={result.get('paid_api_calls')}")
    print(f"live_calls_by_provider={result.get('live_calls_by_provider')}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
