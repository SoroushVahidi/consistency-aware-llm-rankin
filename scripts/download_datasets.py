#!/usr/bin/env python
"""
download_datasets.py
====================
Download real benchmark datasets for the consistency-aware ranking project.

Supported datasets
------------------
- ``scidocs``   — BEIR / SciDocs
- ``fiqa``      — BEIR / FiQA-2018
- ``hotpotqa``  — HotpotQA (fullwiki, validation split)
- ``bright``    — BRIGHT (attempts HuggingFace download; prints manual
                   instructions if unavailable)
- ``all``       — download all of the above

Usage
-----
::

    python scripts/download_datasets.py --dataset scidocs
    python scripts/download_datasets.py --dataset fiqa
    python scripts/download_datasets.py --dataset hotpotqa
    python scripts/download_datasets.py --dataset bright
    python scripts/download_datasets.py --dataset all

Options
-------
--dataset       Dataset to download (default: ``all``)
--max-docs      Maximum corpus documents to download (default: unlimited)
--max-queries   Maximum queries to download (default: unlimited)
--bright-task   BRIGHT task/domain (default: ``biology``)
--force         Re-download even if local files exist

Requirements
------------
Install before running::

    pip install datasets huggingface-hub
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure the src package is importable when run directly
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from consistency_ranker.data.dataset_registry import DATASET_NAMES, get_config
from consistency_ranker.data.beir_loader import write_jsonl


def _check_datasets_installed() -> bool:
    try:
        import datasets  # noqa: F401
        return True
    except ImportError:
        return False


def _raw_files_exist(raw_path: Path) -> bool:
    """Return True if corpus/queries files already present."""
    return (
        (raw_path / "queries.jsonl").exists()
        and (raw_path / "documents.jsonl").exists()
    )


def download_beir(name: str, force: bool, max_docs: int | None, max_queries: int | None) -> None:
    """Download a BEIR dataset (scidocs or fiqa)."""
    from consistency_ranker.data.beir_loader import download_beir_dataset

    cfg = get_config(name)
    raw_path = cfg.raw_path
    raw_path.mkdir(parents=True, exist_ok=True)

    if _raw_files_exist(raw_path) and not force:
        print(f"[{name}] Raw files already exist in {raw_path}. Skipping (use --force to re-download).")
        return

    print(f"[{name}] Downloading from HuggingFace …")
    queries, documents, qrels = download_beir_dataset(
        corpus_name=cfg.hf_corpus_name,
        qrels_name=cfg.hf_qrels_name,
        raw_path=raw_path,
        max_docs=max_docs,
    )
    if max_queries is not None:
        queries = queries[:max_queries]

    write_jsonl(queries, raw_path / "queries.jsonl")
    write_jsonl(documents, raw_path / "documents.jsonl")
    write_jsonl(qrels, raw_path / "qrels.jsonl")
    print(
        f"[{name}] Done. "
        f"{len(queries)} queries, {len(documents)} docs, {len(qrels)} qrels "
        f"→ {raw_path}"
    )


def download_hotpotqa(force: bool, max_docs: int | None, max_queries: int | None) -> None:
    """Download HotpotQA (fullwiki validation split)."""
    from consistency_ranker.data.hotpotqa_loader import download_hotpotqa
    from consistency_ranker.data.beir_loader import write_jsonl

    cfg = get_config("hotpotqa")
    raw_path = cfg.raw_path
    raw_path.mkdir(parents=True, exist_ok=True)

    if _raw_files_exist(raw_path) and not force:
        print(f"[hotpotqa] Raw files already exist in {raw_path}. Skipping (use --force to re-download).")
        return

    print("[hotpotqa] Downloading from HuggingFace …")
    queries, documents, qrels = download_hotpotqa(
        raw_path=raw_path,
        split="validation",
        max_examples=max_queries,
    )
    if max_docs is not None:
        documents = documents[:max_docs]

    write_jsonl(queries, raw_path / "queries.jsonl")
    write_jsonl(documents, raw_path / "documents.jsonl")
    write_jsonl(qrels, raw_path / "qrels.jsonl")
    print(
        f"[hotpotqa] Done. "
        f"{len(queries)} queries, {len(documents)} docs, {len(qrels)} qrels "
        f"→ {raw_path}"
    )


def download_bright(
    force: bool,
    max_docs: int | None,
    max_queries: int | None,
    bright_task: str,
) -> None:
    """Attempt to download BRIGHT; create placeholder if unavailable."""
    from consistency_ranker.data.bright_loader import (
        list_available_bright_tasks,
        BrightNotAvailableError,
        download_bright,
    )

    cfg = get_config("bright")
    raw_path = cfg.raw_path
    raw_path.mkdir(parents=True, exist_ok=True)

    if _raw_files_exist(raw_path) and not force:
        print(f"[bright] Raw files already exist in {raw_path}. Skipping (use --force to re-download).")
        return

    available_tasks = list_available_bright_tasks()
    if bright_task not in available_tasks:
        print(
            f"[bright] ERROR: unknown task {bright_task!r}. "
            f"Choose one of: {list(available_tasks)}"
        )
        return

    print(f"[bright] Attempting to download BRIGHT task={bright_task!r} from HuggingFace …")
    try:
        from consistency_ranker.data.beir_loader import write_jsonl
        queries, documents, qrels = download_bright(
            raw_path=raw_path,
            task=bright_task,
            max_examples=max_queries,
        )
        if max_docs is not None:
            documents = documents[:max_docs]
        write_jsonl(queries, raw_path / "queries.jsonl")
        write_jsonl(documents, raw_path / "documents.jsonl")
        write_jsonl(qrels, raw_path / "qrels.jsonl")
        print(
            f"[bright] Done. "
            f"{len(queries)} queries, {len(documents)} docs, {len(qrels)} qrels "
            f"→ {raw_path}"
        )
    except BrightNotAvailableError as exc:
        print(f"\n[bright] ⚠  Could not download automatically:\n  {exc}")
        print(
            f"\n[bright] Manual instructions have been written to:\n"
            f"  {raw_path / 'README.md'}\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download benchmark datasets for consistency-aware ranking.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dataset",
        choices=DATASET_NAMES + ["all"],
        default="all",
        help="Dataset to download (default: all)",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=None,
        help="Maximum number of corpus documents (default: all)",
    )
    parser.add_argument(
        "--max-queries",
        type=int,
        default=None,
        help="Maximum number of queries (default: all)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if local files already exist",
    )
    parser.add_argument(
        "--bright-task",
        type=str,
        default="examples",
        help="BRIGHT task/domain to download (used when --dataset bright or all).",
    )
    args = parser.parse_args()

    if not _check_datasets_installed():
        print(
            "ERROR: The 'datasets' library is not installed.\n"
            "Install it with:  pip install datasets huggingface-hub\n"
            "Then re-run this script."
        )
        sys.exit(1)

    targets = DATASET_NAMES if args.dataset == "all" else [args.dataset]

    for name in targets:
        print(f"\n{'='*60}")
        print(f"  Dataset: {name}")
        print(f"{'='*60}")
        if name in ("scidocs", "fiqa"):
            download_beir(name, args.force, args.max_docs, args.max_queries)
        elif name == "hotpotqa":
            download_hotpotqa(args.force, args.max_docs, args.max_queries)
        elif name == "bright":
            download_bright(args.force, args.max_docs, args.max_queries, args.bright_task)

    print("\nAll requested downloads complete.")


if __name__ == "__main__":
    main()
