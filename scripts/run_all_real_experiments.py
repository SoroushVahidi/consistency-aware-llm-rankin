#!/usr/bin/env python
"""
run_all_real_experiments.py
============================
Master orchestration script: download (or generate proxy) data for all four
supported datasets, prepare them, run the full ranking pipeline with multiple
preference sources, and save publication-quality outputs to
``outputs/real_full/``.

Pipeline stages (per dataset)
------------------------------
1. **Acquire data** — try HuggingFace download; fall back to proxy generation
   when offline.
2. **Prepare** — convert raw JSONL files to processed format + pairwise
   preferences (``prepare_datasets.py``).
3. **Run experiments** — ``run_real_experiment.py`` with:
   - ``qrels``       (oracle label–derived preferences)
   - ``qrels_flip``  (controlled synthetic corruption, flip_prob=0.15)

Outputs
-------
Each preference source gets its own sub-directory to prevent overwriting:
``outputs/real_full/<dataset>/<preference_source>/``:

- ``<dataset>_per_query.csv``           per-query × per-method metrics
- ``<dataset>_summary.csv``             aggregate per-method statistics
- ``<dataset>_experiment_summary.json`` high-level experiment metadata
- ``timings/<dataset>_timings.csv``     per-stage timing data
- ``timings/<dataset>_timings.json``    timing data (JSON)

Usage
-----
::

    # Run everything end-to-end
    python scripts/run_all_real_experiments.py

    # Single dataset, full queries
    python scripts/run_all_real_experiments.py --dataset scidocs

    # Override top-k candidates per query
    python scripts/run_all_real_experiments.py --top-k 30

    # Skip preference sources you don't need
    python scripts/run_all_real_experiments.py --sources qrels

    # Force re-run even if output files exist
    python scripts/run_all_real_experiments.py --force

Options
-------
--dataset          Dataset or "all" (default: all)
--sources          Space-separated preference sources to run (default: qrels qrels_flip)
--top-k            Max candidates per query (default: 20)
--max-queries      Cap queries per dataset — omit or 0 for dataset default
--flip-prob        Edge-flip probability for qrels_flip source (default: 0.15)
--seed             Random seed (default: 42)
--output-dir       Root output directory (default: outputs/real_full)
--force            Re-run even if output files already exist
--no-proxy         Raise an error instead of falling back to proxy generation
--save-timings     Save timing CSVs/JSONs (enabled by default)
--profile          Print per-stage timing table to stdout
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from consistency_ranker.data.dataset_registry import DATASET_NAMES, get_config

_SCRIPTS = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raw_files_exist(name: str) -> bool:
    cfg = get_config(name)
    p = cfg.raw_path
    return (
        (p / "queries.jsonl").exists()
        and (p / "documents.jsonl").exists()
        and (p / "qrels.jsonl").exists()
    )


def _processed_files_exist(name: str) -> bool:
    cfg = get_config(name)
    p = cfg.processed_path
    return (
        (p / "queries.jsonl").exists()
        and (p / "documents.jsonl").exists()
        and (p / "qrels.jsonl").exists()
    )


def _experiment_output_exists(name: str, source: str, output_dir: Path) -> bool:
    ds_dir = output_dir / name / source
    return (ds_dir / f"{name}_experiment_summary.json").exists()


def _run(cmd: list[str], *, label: str) -> int:
    """Run a subprocess, streaming output to stdout.  Returns exit code."""
    print(f"\n>>> {label}")
    print("    " + " ".join(str(c) for c in cmd))
    t0 = time.perf_counter()
    result = subprocess.run(cmd, cwd=_REPO_ROOT)
    elapsed = time.perf_counter() - t0
    print(f"    [exit={result.returncode}  elapsed={elapsed:.1f}s]")
    return result.returncode


def _acquire_data(name: str, *, force: bool, no_proxy: bool, seed: int) -> bool:
    """Ensure raw data exists; return True on success."""
    if _raw_files_exist(name) and not force:
        print(f"[{name}] Raw data already present — skipping acquisition.")
        return True

    # Try real download first
    rc = _run(
        [
            sys.executable,
            str(_SCRIPTS / "download_datasets.py"),
            "--dataset", name,
            *(["--force"] if force else []),
        ],
        label=f"Download {name}",
    )
    if rc == 0 and _raw_files_exist(name):
        return True

    if no_proxy:
        print(f"[{name}] ERROR: download failed and --no-proxy is set.")
        return False

    print(
        f"\n[{name}] ⚠  Download failed or data unavailable — "
        "falling back to proxy generation."
    )
    rc = _run(
        [
            sys.executable,
            str(_SCRIPTS / "generate_proxy_datasets.py"),
            "--dataset", name,
            "--seed", str(seed),
            *(["--force"] if force else []),
        ],
        label=f"Generate proxy data for {name}",
    )
    if rc == 0 and _raw_files_exist(name):
        return True

    print(f"[{name}] ERROR: proxy generation also failed.")
    return False


def _prepare_data(name: str, *, force: bool) -> bool:
    """Run prepare_datasets.py for *name*."""
    if _processed_files_exist(name) and not force:
        print(f"[{name}] Processed data already present — skipping prepare.")
        return True

    rc = _run(
        [
            sys.executable,
            str(_SCRIPTS / "prepare_datasets.py"),
            "--dataset", name,
            *(["--force"] if force else []),
        ],
        label=f"Prepare {name}",
    )
    return rc == 0 and _processed_files_exist(name)


def _run_experiment(
    name: str,
    *,
    source: str,
    top_k: int,
    max_queries: int | None,
    flip_prob: float,
    seed: int,
    output_dir: Path,
    force: bool,
    save_timings: bool,
    profile: bool,
) -> bool:
    """Run run_real_experiment.py for *name* and *source*."""
    ds_out = output_dir / name / source
    summary_path = ds_out / f"{name}_experiment_summary.json"

    if summary_path.exists() and not force:
        print(
            f"[{name}/{source}] Output already exists at {summary_path} — "
            "skipping (use --force to re-run)."
        )
        return True

    cmd: list[str] = [
        sys.executable,
        str(_SCRIPTS / "run_real_experiment.py"),
        "--dataset", name,
        "--preference-source", source,
        "--top-k", str(top_k),
        "--seed", str(seed),
        "--output-dir", str(ds_out),
    ]
    if max_queries:
        cmd += ["--max-queries", str(max_queries)]
    if source == "qrels_flip":
        cmd += ["--flip-prob", str(flip_prob)]
    if save_timings:
        cmd.append("--save-timings")
    if profile:
        cmd.append("--profile")

    rc = _run(cmd, label=f"Experiment {name} / {source}")
    return rc == 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="End-to-end orchestrator for all real-data ranking experiments.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dataset",
        choices=DATASET_NAMES + ["all"],
        default="all",
        help="Dataset to run (default: all)",
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=["qrels", "qrels_flip", "score_file", "votes_file"],
        default=["qrels", "qrels_flip"],
        help="Preference sources to evaluate (default: qrels qrels_flip)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=20,
        help="Max candidate documents per query (default: 20)",
    )
    parser.add_argument(
        "--max-queries",
        type=int,
        default=None,
        help=(
            "Cap the number of queries per dataset.  "
            "Omit (or pass 0) to use the dataset's full default."
        ),
    )
    parser.add_argument(
        "--flip-prob",
        type=float,
        default=0.15,
        help="Edge-flip probability for qrels_flip source (default: 0.15)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/real_full"),
        help="Root output directory (default: outputs/real_full)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run stages even if output files already exist",
    )
    parser.add_argument(
        "--no-proxy",
        action="store_true",
        help="Raise an error instead of falling back to proxy data generation",
    )
    parser.add_argument(
        "--save-timings",
        action="store_true",
        default=True,
        help="Save per-stage timing files (enabled by default)",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Print per-stage timing table to stdout",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)

    datasets = DATASET_NAMES if args.dataset == "all" else [args.dataset]
    max_queries = args.max_queries if args.max_queries and args.max_queries > 0 else None

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, dict] = {}

    wall_start = time.perf_counter()

    for name in datasets:
        print(f"\n{'#'*70}")
        print(f"#  Dataset: {name.upper()}")
        print(f"{'#'*70}")

        ds_results: dict[str, bool] = {}

        # 1. Acquire raw data
        ok = _acquire_data(name, force=args.force, no_proxy=args.no_proxy, seed=args.seed)
        ds_results["acquire"] = ok
        if not ok:
            print(f"[{name}] Skipping remaining stages — data acquisition failed.")
            results[name] = ds_results
            continue

        # 2. Prepare processed data
        ok = _prepare_data(name, force=args.force)
        ds_results["prepare"] = ok
        if not ok:
            print(f"[{name}] Skipping experiment — data preparation failed.")
            results[name] = ds_results
            continue

        # 3. Run experiments for each preference source
        for source in args.sources:
            ok = _run_experiment(
                name,
                source=source,
                top_k=args.top_k,
                max_queries=max_queries,
                flip_prob=args.flip_prob,
                seed=args.seed,
                output_dir=output_dir,
                force=args.force,
                save_timings=args.save_timings,
                profile=args.profile,
            )
            ds_results[f"experiment_{source}"] = ok

        results[name] = ds_results

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    wall_elapsed = time.perf_counter() - wall_start
    print(f"\n\n{'='*70}")
    print("  ORCHESTRATION SUMMARY")
    print(f"{'='*70}")
    all_ok = True
    for name, ds_results in results.items():
        stage_str = "  ".join(
            f"{k}={'✓' if v else '✗'}" for k, v in ds_results.items()
        )
        print(f"  {name:<12} {stage_str}")
        if not all(ds_results.values()):
            all_ok = False

    print(f"\n  Total wall time: {wall_elapsed:.1f}s")
    print(f"  Output directory: {output_dir.resolve()}")
    print(f"{'='*70}\n")

    # Write run manifest
    manifest_path = output_dir / "run_manifest.json"
    with manifest_path.open("w") as fh:
        json.dump(
            {
                "datasets": datasets,
                "sources": args.sources,
                "top_k": args.top_k,
                "max_queries": max_queries,
                "flip_prob": args.flip_prob,
                "seed": args.seed,
                "wall_time_s": round(wall_elapsed, 2),
                "results": results,
            },
            fh,
            indent=2,
        )
    print(f"  Run manifest → {manifest_path}")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
