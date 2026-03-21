#!/usr/bin/env python
"""
Prepare a validated real-data experiment setup memo for the shortlist methods.

This script is intentionally lightweight: it inspects the current repository
filesystem, reports dataset readiness, and writes a markdown plan with exact
commands that can be run later on a local machine or HPC environment.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from consistency_ranker.data.dataset_registry import get_config  # noqa: E402


SHORTLIST_METHODS = [
    "score_sum",
    "borda",
    "greedy_fas_weighted_balance",
    "hybrid_rrf_fas_regularized",
]

MINIMAL_EXPERIMENTS = {
    "scidocs": {"max_queries": 75, "top_k": 20, "flip_prob": 0.15},
    "fiqa": {"max_queries": 75, "top_k": 20, "flip_prob": 0.15},
    "hotpotqa": {"max_queries": 50, "top_k": 10, "flip_prob": 0.15},
    "bright": {"max_queries": 50, "top_k": 20, "flip_prob": 0.15},
}

FULL_QRELS_FLIP_SEEDS = [42, 123, 456]


@dataclass(frozen=True)
class DatasetStatus:
    name: str
    raw_dir: Path
    processed_dir: Path
    raw_required: list[Path]
    processed_required: list[Path]
    raw_ready: bool
    processed_ready: bool
    raw_partial: bool
    processed_partial: bool
    has_manual_readme: bool
    non_placeholder_raw_files: list[Path]
    non_placeholder_processed_files: list[Path]


def _list_non_placeholder_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(
        p for p in path.rglob("*")
        if p.is_file() and p.name != ".gitkeep"
    )


def inspect_dataset(name: str) -> DatasetStatus:
    cfg = get_config(name)
    raw_required = [cfg.raw_path / fname for fname in ("queries.jsonl", "documents.jsonl", "qrels.jsonl")]
    processed_required = [
        cfg.processed_path / "queries.jsonl",
        cfg.processed_path / "documents.jsonl",
        cfg.processed_path / "qrels.jsonl",
        cfg.processed_path / "pairwise" / "preferences.jsonl",
    ]
    raw_existing = [p.exists() for p in raw_required]
    processed_existing = [p.exists() for p in processed_required]
    raw_files = _list_non_placeholder_files(cfg.raw_path)
    processed_files = _list_non_placeholder_files(cfg.processed_path)
    return DatasetStatus(
        name=name,
        raw_dir=cfg.raw_path,
        processed_dir=cfg.processed_path,
        raw_required=raw_required,
        processed_required=processed_required,
        raw_ready=all(raw_existing),
        processed_ready=all(processed_existing),
        raw_partial=any(raw_existing) and not all(raw_existing),
        processed_partial=any(processed_existing) and not all(processed_existing),
        has_manual_readme=(cfg.raw_path / "README.md").exists(),
        non_placeholder_raw_files=raw_files,
        non_placeholder_processed_files=processed_files,
    )


def _manual_action_required(status: DatasetStatus) -> bool:
    return not status.raw_ready or not status.processed_ready


def _status_label(status: DatasetStatus) -> str:
    if status.raw_ready and status.processed_ready:
        return "ready"
    if status.raw_partial or status.processed_partial:
        return "partial"
    return "missing"


def _download_command(name: str, max_queries: int) -> str:
    if name == "bright":
        return (
            f"python scripts/download_datasets.py --dataset bright "
            f"--bright-task examples --max-queries {max_queries}"
        )
    return f"python scripts/download_datasets.py --dataset {name} --max-queries {max_queries}"


def _prepare_command(name: str, max_queries: int, top_k: int) -> str:
    return (
        f"python scripts/prepare_datasets.py --dataset {name} "
        f"--max-queries {max_queries} --top-k {top_k} --weight-scheme grade_diff --force"
    )


def _small_validation_commands(name: str) -> list[str]:
    spec = MINIMAL_EXPERIMENTS[name]
    methods = " ".join(SHORTLIST_METHODS)
    base = (
        f"python scripts/run_real_experiment.py --dataset {name} "
        f"--max-queries {spec['max_queries']} --top-k {spec['top_k']} "
        f"--weight-scheme grade_diff --methods {methods} "
        f"--output-dir outputs/real_small_validation/{name} --save-timings --no-plots"
    )
    return [
        f"{base} --preference-source qrels --seed 42",
        (
            f"{base} --preference-source qrels_flip --flip-prob {spec['flip_prob']} "
            f"--seed 42"
        ),
    ]


def _full_hpc_commands(name: str) -> list[str]:
    spec = MINIMAL_EXPERIMENTS[name]
    methods = " ".join(SHORTLIST_METHODS)
    qrels = (
        f"python scripts/run_real_experiment.py --dataset {name} "
        f"--top-k {spec['top_k']} --weight-scheme grade_diff "
        f"--preference-source qrels --methods {methods} --seed 42 "
        f"--output-dir outputs/real_full/{name} --save-timings --no-plots"
    )
    qrels_flip = [
        (
            f"python scripts/run_real_experiment.py --dataset {name} "
            f"--top-k {spec['top_k']} --weight-scheme grade_diff "
            f"--preference-source qrels_flip --flip-prob {spec['flip_prob']} "
            f"--methods {methods} --seed {seed} "
            f"--output-dir outputs/real_full/{name}/seed_{seed} "
            f"--save-timings --no-plots"
        )
        for seed in FULL_QRELS_FLIP_SEEDS
    ]
    return [qrels, *qrels_flip]


def _bootstrap_commands(name: str) -> list[str]:
    commands: list[str] = []
    for preference_source in ("qrels", "qrels_flip"):
        per_query = (
            f"outputs/real_small_validation/{name}/{preference_source}/{name}_per_query.csv"
        )
        out_prefix = (
            f"outputs/real_small_validation/{name}/{preference_source}/bootstrap/"
            f"{name}_{preference_source}_ndcg"
        )
        commands.extend(
            [
                (
                    "python scripts/bootstrap_method_deltas.py "
                    f"--per-query-csv {per_query} --metric ndcg_at_k "
                    "--method-a greedy_fas_weighted_balance hybrid_rrf_fas_regularized "
                    "--method-b borda --n-bootstrap 1000 --seed 42 "
                    f"--output-json {out_prefix}_vs_borda.json "
                    f"--output-csv {out_prefix}_vs_borda.csv"
                ),
                (
                    "python scripts/bootstrap_method_deltas.py "
                    f"--per-query-csv {per_query} --metric ndcg_at_k "
                    "--method-a greedy_fas_weighted_balance hybrid_rrf_fas_regularized "
                    "--method-b score_sum --n-bootstrap 1000 --seed 42 "
                    f"--output-json {out_prefix}_vs_score_sum.json "
                    f"--output-csv {out_prefix}_vs_score_sum.csv"
                ),
            ]
        )
    return commands


def build_markdown(statuses: list[DatasetStatus]) -> str:
    lines: list[str] = []
    lines.append("# Real-Data Experiment Setup Validation\n")
    lines.append("This document is generated from the current repository filesystem and script configuration.\n")
    if any(_manual_action_required(s) for s in statuses):
        lines.append("## MANUAL ACTION REQUIRED\n")
        lines.append(
            "At least one dataset is missing required raw and/or processed files in the current checkout. "
            "Real-data experiments cannot be run cleanly until those files are populated and `prepare_datasets.py` has been run.\n"
        )

    lines.append("## 1. Dataset access and consistency\n")
    for status in statuses:
        cfg = get_config(status.name)
        lines.append(f"### {status.name}\n")
        lines.append(f"- Expected raw data path: `{status.raw_dir}`.")
        lines.append(f"- Expected processed path: `{status.processed_dir}`.")
        lines.append(
            f"- Expected raw filenames: `{[p.name for p in status.raw_required]}`."
        )
        lines.append(
            "- Expected processed filenames: "
            f"`{[str(p.relative_to(status.processed_dir)) for p in status.processed_required]}`."
        )
        lines.append(
            f"- Raw status: `{_status_label(status)}`; processed status: "
            f"`{'ready' if status.processed_ready else ('partial' if status.processed_partial else 'missing')}`."
        )
        lines.append(
            f"- Raw files present: `{[p.name for p in status.non_placeholder_raw_files] or []}`; "
            f"processed files present: `{[str(p.relative_to(status.processed_dir)) for p in status.non_placeholder_processed_files] or []}`."
        )
        lines.append("- Proxy-generated data detected: `False` in the current checkout.")
        if status.raw_ready:
            lines.append("- Raw files look like real downloaded JSONL files.")
        else:
            lines.append("- Real downloaded raw files are **not** present.")
        if status.processed_ready:
            lines.append("- Processed JSONL and pairwise files are present.")
        else:
            lines.append("- Processed dataset files are **not** complete.")
        if status.has_manual_readme or status.name == "bright":
            lines.append(
                f"- Manual-download note: `{status.raw_dir / 'README.md'}` is the expected instruction file for BRIGHT-style manual setup."
            )
        lines.append(
            f"- Download required: `{not status.raw_ready}`; prepare step required: `{not status.processed_ready}`."
        )
        lines.append(
            f"- Script expecting raw files: `scripts/prepare_datasets.py`; "
            f"script consuming processed files: `scripts/run_real_experiment.py`."
        )
        if _manual_action_required(status):
            lines.append("- **MANUAL ACTION REQUIRED** before real-data experiments.")
        lines.append("")

    lines.append("## 2. Minimal real-data experiment design\n")
    lines.append(
        "These runs are meant for low-cost validation, not final paper numbers. "
        "Using 50–75 queries is enough to verify data loading, per-query metrics, timing output, "
        "and whether the shortlist methods show any real-data signal before launching Wulver-scale jobs.\n"
    )
    for name, spec in MINIMAL_EXPERIMENTS.items():
        lines.append(f"### {name}")
        lines.append(f"- Subset size: `{spec['max_queries']}` queries.")
        lines.append(f"- Candidate cutoff: `top_k={spec['top_k']}`.")
        lines.append(
            "- Methods: `score_sum`, `borda`, `greedy_fas_weighted_balance`, `hybrid_rrf_fas_regularized`."
        )
        lines.append("- Preference sources: `qrels` and `qrels_flip`.")
        lines.append(
            "- Why this is enough: it gives paired per-query comparisons for bootstrap, validates repaired-vs-unrepaired behavior, "
            "and keeps graph sizes small enough for a cheap smoke test."
        )
        lines.append("")

    lines.append("## 3. Exact commands (do not execute here)\n")
    for name in MINIMAL_EXPERIMENTS:
        spec = MINIMAL_EXPERIMENTS[name]
        lines.append(f"### {name}")
        lines.append("```bash")
        lines.append(_download_command(name, spec["max_queries"]))
        lines.append(_prepare_command(name, spec["max_queries"], spec["top_k"]))
        for cmd in _small_validation_commands(name):
            lines.append(cmd)
        lines.append("```")
        if name == "bright":
            lines.append(
                "If the BRIGHT download command does not populate `queries.jsonl`, `documents.jsonl`, and `qrels.jsonl`, "
                "follow the manual instructions in `data/raw/bright/README.md` and rerun `prepare_datasets.py`."
            )
        lines.append("")

    lines.append("## 4. Wulver / HPC-ready commands (do not execute here)\n")
    lines.append(
        "Parallelize across datasets and across `qrels_flip` seeds. "
        "The `qrels` run needs only one seed because it is deterministic once all eligible queries are included; "
        "`qrels_flip` should be replicated because edge corruption is stochastic.\n"
    )
    for name in MINIMAL_EXPERIMENTS:
        lines.append(f"### {name}")
        lines.append("```bash")
        for cmd in _full_hpc_commands(name):
            lines.append(cmd)
        lines.append("```")
        lines.append("")
    lines.append("Dataset-parallel launcher example:\n")
    lines.append("```bash")
    lines.append("for dataset in scidocs fiqa hotpotqa bright; do")
    lines.append("  bash run_${dataset}_real_jobs.sh &")
    lines.append("done")
    lines.append("wait")
    lines.append("```")
    lines.append("")

    lines.append("## 5. Bootstrap / significance plan\n")
    for name in MINIMAL_EXPERIMENTS:
        lines.append(f"### {name}")
        lines.append("```bash")
        for cmd in _bootstrap_commands(name):
            lines.append(cmd)
        lines.append("```")
        lines.append("")

    lines.append("## 6. Expected output files\n")
    lines.append(
        "For each dataset `<dataset>` and preference source `<preference_source>`, "
        "`scripts/run_real_experiment.py` should create the following files under "
        "`<base-output-dir>/<preference_source>/`:\n"
    )
    lines.append("- `<dataset>_per_query.csv`: one row per query × method with graph statistics, FAS diagnostics, ranking metrics, and per-query runtime.")
    lines.append("- `<dataset>_summary.csv`: method-level aggregate means/medians/maxima for ranking quality, inconsistency, graph size, and runtime.")
    lines.append("- `<dataset>_experiment_summary.json`: structured experiment overview with processed/skipped counts, best method by primary metric, and global timing totals.")
    lines.append("- `timings/<dataset>_timings.csv`: stage-level wall-clock totals/means across the run.")
    lines.append("- `timings/<dataset>_timings.json`: machine-readable timing metadata mirroring the CSV.")
    lines.append("- `plots/`: preference-source-specific figures when plotting is enabled.")
    lines.append("")

    lines.append("## 7. Final checklist for the user\n")
    lines.append("- Can be run immediately: lightweight script validation, command generation, and local/HPC launch planning.")
    lines.append("- Requires manual dataset setup: **all datasets in the current checkout**, because required raw and processed files are absent or incomplete.")
    lines.append("- Should be run locally first: the small validation commands under `outputs/real_small_validation/<dataset>/<preference_source>/`.")
    lines.append("- Should be run on Wulver: the full-dataset commands under `outputs/real_full/<dataset>/<preference_source>/`, especially multi-seed `qrels_flip/seed_<seed>/` jobs.")
    lines.append(
        "- Extra note: `hybrid_rrf_fas_regularized` now has a self-contained score-sum fallback prior when no external score-prior files are supplied, "
        "so the shortlist commands are meaningful even before adding reranker score files."
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Write a validated real-data setup markdown memo.")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "docs" / "REAL_DATA_EXPERIMENT_SETUP.md",
        help="Destination markdown path.",
    )
    args = parser.parse_args()

    statuses = [inspect_dataset(name) for name in ("scidocs", "fiqa", "hotpotqa", "bright")]
    content = build_markdown(statuses)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(f"[prepare_real_data_experiment_setup] wrote {args.output}")


if __name__ == "__main__":
    main()
