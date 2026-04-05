#!/usr/bin/env python
"""
download_datasets.py
====================
Download real benchmark datasets for the consistency-aware ranking project.

Supported datasets
------------------
- ``scidocs``, ``fiqa``, ``nfcorpus`` — BEIR mirrors on Hugging Face
- ``msmarco_passage`` — MS MARCO passage (BEIR mirror; **streaming** corpus; needs ``--max-docs``)
- ``trec_dl_passage`` — TREC Deep Learning passage task (requires ``pip install 'consistency-ranker[ir]'``)
- ``robust04`` — TREC Robust 2004 (requires ``ir-datasets``)
- ``hotpotqa``, ``bright`` — as before
- ``all`` — all registered datasets

Usage
-----
::

    python scripts/download_datasets.py --dataset nfcorpus
    python scripts/download_datasets.py --dataset msmarco_passage --max-docs 50000 --max-queries 5000
    python scripts/download_datasets.py --dataset trec_dl_passage --trec-dl-year 2019
    python scripts/download_datasets.py --dataset robust04 --max-queries 250 --max-docs 50000
    python scripts/download_datasets.py --dataset all

Requirements
------------
``datasets`` and ``huggingface-hub``. For TREC DL and Robust04, also::

    pip install 'consistency-ranker[ir]'
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

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
    return (
        (raw_path / "queries.jsonl").exists()
        and (raw_path / "documents.jsonl").exists()
        and (raw_path / "qrels.jsonl").exists()
    )


def download_beir(name: str, force: bool, max_docs: int | None, max_queries: int | None) -> None:
    """Download a BEIR-format dataset from Hugging Face."""
    from consistency_ranker.data.beir_loader import BeirNotAvailableError, download_beir_dataset

    cfg = get_config(name)
    raw_path = cfg.raw_path
    raw_path.mkdir(parents=True, exist_ok=True)

    if _raw_files_exist(raw_path) and not force:
        print(f"[{name}] Raw files already exist in {raw_path}. Skipping (use --force).")
        return

    print(f"[{name}] Downloading from HuggingFace …")
    try:
        queries, documents, qrels = download_beir_dataset(
            corpus_name=cfg.hf_corpus_name,
            qrels_name=cfg.hf_qrels_name,
            raw_path=raw_path,
            max_docs=max_docs,
            max_queries=max_queries,
        )
    except BeirNotAvailableError as exc:
        print(f"\n[{name}] ⚠  Could not download automatically:\n  {exc}\n")
        return

    write_jsonl(queries, raw_path / "queries.jsonl")
    write_jsonl(documents, raw_path / "documents.jsonl")
    write_jsonl(qrels, raw_path / "qrels.jsonl")
    print(
        f"[{name}] Done. {len(queries)} queries, {len(documents)} docs, {len(qrels)} qrels → {raw_path}"
    )


def download_msmarco_passage(
    force: bool,
    max_docs: int | None,
    max_queries: int | None,
) -> None:
    from consistency_ranker.data.beir_loader import BeirNotAvailableError
    from consistency_ranker.data.msmarco_passage_loader import download_msmarco_passage_raw

    cfg = get_config("msmarco_passage")
    raw_path = cfg.raw_path
    effective_max = max_docs
    if effective_max is None:
        effective_max = 100_000
        print(
            "[msmarco_passage] No --max-docs given; using default cap 100_000 passages. "
            "Increase --max-docs for a larger (much slower / larger) export."
        )
    try:
        download_msmarco_passage_raw(
            raw_path,
            max_docs=effective_max,
            max_queries=max_queries,
            force=force,
            hf_corpus_name=cfg.hf_corpus_name,
            hf_qrels_name=cfg.hf_qrels_name,
        )
    except BeirNotAvailableError as exc:
        print(f"\n[msmarco_passage] ⚠  {exc}\n")


def download_trec_dl_passage(
    force: bool,
    max_queries: int | None,
    trec_dl_year: int,
) -> None:
    from consistency_ranker.data.ir_datasets_export import (
        IrDatasetsNotAvailableError,
        export_trec_dl_passage_to_raw,
        ir_datasets_available,
        write_manual_placeholder_readme,
    )

    cfg = get_config("trec_dl_passage")
    raw_path = cfg.raw_path
    ir_subset = f"msmarco-passage/trec-dl-{trec_dl_year}"
    if not ir_datasets_available():
        write_manual_placeholder_readme(
            raw_path,
            "TREC Deep Learning passage (manual / ir-datasets)",
            "Automatic export requires: pip install 'consistency-ranker[ir]'\n\n"
            f"Then run: python scripts/download_datasets.py --dataset trec_dl_passage "
            f"--trec-dl-year {trec_dl_year}\n\n"
            "Or place queries.jsonl, documents.jsonl, and qrels.jsonl here yourself.",
        )
        print(
            "\n[trec_dl_passage] ⚠  ir-datasets is not installed.\n"
            "  pip install 'consistency-ranker[ir]'\n"
            f"  See also: {raw_path / 'README.md'}\n"
        )
        return
    try:
        export_trec_dl_passage_to_raw(
            raw_path,
            ir_subset=ir_subset,
            max_queries=max_queries,
            force=force,
        )
    except IrDatasetsNotAvailableError as exc:
        print(f"\n[trec_dl_passage] ⚠  {exc}\n")


def download_robust04(
    force: bool,
    max_docs: int | None,
    max_queries: int | None,
) -> None:
    from consistency_ranker.data.ir_datasets_export import (
        IrDatasetsNotAvailableError,
        export_robust04_to_raw,
        ir_datasets_available,
        write_manual_placeholder_readme,
    )

    cfg = get_config("robust04")
    raw_path = cfg.raw_path
    if not ir_datasets_available():
        write_manual_placeholder_readme(
            raw_path,
            "TREC Robust 2004",
            "Automatic export requires: pip install 'consistency-ranker[ir]'\n\n"
            "ir-datasets will download corpus shards under its cache; TREC / disk terms apply.\n\n"
            "Alternatively, convert official TREC files to this repo's JSONL layout manually.",
        )
        print(
            "\n[robust04] ⚠  ir-datasets is not installed.\n"
            "  pip install 'consistency-ranker[ir]'\n"
            f"  See: {raw_path / 'README.md'}\n"
        )
        return
    try:
        export_robust04_to_raw(
            raw_path,
            max_queries=max_queries,
            max_docs=max_docs,
            force=force,
        )
    except IrDatasetsNotAvailableError as exc:
        print(f"\n[robust04] ⚠  {exc}\n")


def download_hotpotqa(force: bool, max_docs: int | None, max_queries: int | None) -> None:
    from consistency_ranker.data.hotpotqa_loader import download_hotpotqa

    cfg = get_config("hotpotqa")
    raw_path = cfg.raw_path
    raw_path.mkdir(parents=True, exist_ok=True)

    if _raw_files_exist(raw_path) and not force:
        print(f"[hotpotqa] Raw files already exist in {raw_path}. Skipping (use --force).")
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
        f"[hotpotqa] Done. {len(queries)} queries, {len(documents)} docs, {len(qrels)} qrels → {raw_path}"
    )


def download_bright(
    force: bool,
    max_docs: int | None,
    max_queries: int | None,
    bright_task: str,
) -> None:
    from consistency_ranker.data.bright_loader import (
        BrightNotAvailableError,
        download_bright,
        list_available_bright_tasks,
    )

    cfg = get_config("bright")
    raw_path = cfg.raw_path
    raw_path.mkdir(parents=True, exist_ok=True)

    if _raw_files_exist(raw_path) and not force:
        print(f"[bright] Raw files already exist in {raw_path}. Skipping (use --force).")
        return

    available_tasks = list_available_bright_tasks()
    if bright_task not in available_tasks:
        print(
            f"[bright] ERROR: unknown task {bright_task!r}. Choose one of: {list(available_tasks)}"
        )
        return

    print(f"[bright] Attempting to download BRIGHT task={bright_task!r} from HuggingFace …")
    try:
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
            f"[bright] Done. {len(queries)} queries, {len(documents)} docs, {len(qrels)} qrels → {raw_path}"
        )
    except BrightNotAvailableError as exc:
        print(f"\n[bright] ⚠  Could not download automatically:\n  {exc}")
        print(f"\n[bright] Manual instructions: {raw_path / 'README.md'}\n")


def _dispatch(name: str, args: argparse.Namespace) -> None:
    if name in ("scidocs", "fiqa", "nfcorpus"):
        download_beir(name, args.force, args.max_docs, args.max_queries)
    elif name == "msmarco_passage":
        download_msmarco_passage(args.force, args.max_docs, args.max_queries)
    elif name == "trec_dl_passage":
        download_trec_dl_passage(args.force, args.max_queries, args.trec_dl_year)
    elif name == "robust04":
        download_robust04(args.force, args.max_docs, args.max_queries)
    elif name == "hotpotqa":
        download_hotpotqa(args.force, args.max_docs, args.max_queries)
    elif name == "bright":
        download_bright(args.force, args.max_docs, args.max_queries, args.bright_task)


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
        help="Maximum corpus documents (MS MARCO defaults to 100k if omitted; see docs).",
    )
    parser.add_argument(
        "--max-queries",
        type=int,
        default=None,
        help="Maximum number of queries (where applicable).",
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
        help="BRIGHT task when downloading bright (default: examples).",
    )
    parser.add_argument(
        "--trec-dl-year",
        type=int,
        choices=(2019, 2020),
        default=2019,
        help="TREC DL passage year (msmarco-passage/trec-dl-YYYY).",
    )
    args = parser.parse_args()

    if not _check_datasets_installed():
        print(
            "ERROR: The 'datasets' library is not installed.\n"
            "Install with: pip install datasets huggingface-hub\n"
            "Then re-run this script."
        )
        sys.exit(1)

    targets = DATASET_NAMES if args.dataset == "all" else [args.dataset]

    for name in targets:
        print(f"\n{'='*60}\n  Dataset: {name}\n{'='*60}")
        _dispatch(name, args)

    print("\nAll requested downloads complete.")


if __name__ == "__main__":
    main()
