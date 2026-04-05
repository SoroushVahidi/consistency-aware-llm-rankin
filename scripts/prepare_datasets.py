#!/usr/bin/env python
"""
prepare_datasets.py
===================
Convert downloaded raw dataset files into the unified internal format
used by this repository.

For each dataset, this script writes three JSONL files under
``data/processed/<dataset>/``:

- ``queries.jsonl``    — one :class:`Query` per line
- ``documents.jsonl``  — one :class:`Document` per line
- ``qrels.jsonl``      — one :class:`QrelEntry` per line

It then generates pairwise preferences and saves them to
``data/processed/<dataset>/pairwise/preferences.jsonl``.

Usage
-----
::

    python scripts/prepare_datasets.py --dataset scidocs
    python scripts/prepare_datasets.py --dataset fiqa
    python scripts/prepare_datasets.py --dataset nfcorpus
    python scripts/prepare_datasets.py --dataset msmarco_passage
    python scripts/prepare_datasets.py --dataset trec_dl_passage
    python scripts/prepare_datasets.py --dataset robust04
    python scripts/prepare_datasets.py --dataset hotpotqa
    python scripts/prepare_datasets.py --dataset bright
    python scripts/prepare_datasets.py --dataset all

Options
-------
--dataset       Dataset to prepare (default: ``all``)
--top-k         Max candidate docs per query for preferences (default: from registry)
--max-queries   Max queries to process (default: from registry)
--seed          Random seed (default: from registry)
--weight-scheme Preference weight scheme: ``grade_diff`` or ``binary`` (default: grade_diff)
--force         Re-write output files even if they already exist

Requirements
------------
Raw files must already exist in ``data/raw/<dataset>/``.
Run ``python scripts/download_datasets.py`` first.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from consistency_ranker.data.dataset_registry import DATASET_NAMES, get_config
from consistency_ranker.data.bright_loader import BrightSchemaError, load_raw_bright_splits
from consistency_ranker.data.schema import Document, QrelEntry, Query
from consistency_ranker.data.unified_loader import (
    preferences_from_qrels,
    save_pairwise_preferences,
)


# ---------------------------------------------------------------------------
# Generic JSONL I/O helpers
# ---------------------------------------------------------------------------

def _write_jsonl(records, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r.to_dict()) + "\n")
    print(f"    Wrote {len(records)} records → {path}")


def _read_jsonl_raw(path: Path) -> list[dict]:
    """Read a JSONL file into a list of plain dicts."""
    records = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _processed_files_exist(processed_path: Path) -> bool:
    return (
        (processed_path / "queries.jsonl").exists()
        and (processed_path / "documents.jsonl").exists()
        and (processed_path / "qrels.jsonl").exists()
    )


# ---------------------------------------------------------------------------
# Per-dataset prepare functions
# ---------------------------------------------------------------------------

# Datasets that ship raw data as three JSONL files (queries, documents, qrels).
_STANDARD_RAW_JSONL = frozenset(
    {
        "scidocs",
        "fiqa",
        "nfcorpus",
        "msmarco_passage",
        "trec_dl_passage",
        "robust04",
    }
)


def prepare_standard_jsonl_raw(name: str, args: argparse.Namespace) -> None:
    """Prepare from raw ``queries.jsonl`` / ``documents.jsonl`` / ``qrels.jsonl``."""
    cfg = get_config(name)
    raw = cfg.raw_path
    out = cfg.processed_path

    # Check raw files exist
    for fname in ("queries.jsonl", "documents.jsonl", "qrels.jsonl"):
        if not (raw / fname).exists():
            print(
                f"[{name}] ERROR: {raw / fname} not found.\n"
                f"  Run: python scripts/download_datasets.py --dataset {name}"
            )
            return

    if _processed_files_exist(out) and not args.force:
        print(f"[{name}] Processed files already exist in {out}. Skipping (use --force).")
    else:
        print(f"[{name}] Reading raw files from {raw} …")
        raw_queries = _read_jsonl_raw(raw / "queries.jsonl")
        raw_docs = _read_jsonl_raw(raw / "documents.jsonl")
        raw_qrels = _read_jsonl_raw(raw / "qrels.jsonl")

        queries = [Query.from_dict(q) for q in raw_queries]
        documents = [Document.from_dict(d) for d in raw_docs]
        qrels = [QrelEntry.from_dict(q) for q in raw_qrels]

        print(f"[{name}] Writing processed files …")
        _write_jsonl(queries, out / "queries.jsonl")
        _write_jsonl(documents, out / "documents.jsonl")
        _write_jsonl(qrels, out / "qrels.jsonl")

    _generate_preferences(name, out, args)


def prepare_beir(name: str, args: argparse.Namespace) -> None:
    """Backward-compatible alias for BEIR-style raw JSONL."""
    prepare_standard_jsonl_raw(name, args)


def prepare_hotpotqa(args: argparse.Namespace) -> None:
    """Prepare HotpotQA."""
    cfg = get_config("hotpotqa")
    raw = cfg.raw_path
    out = cfg.processed_path

    for fname in ("queries.jsonl", "documents.jsonl", "qrels.jsonl"):
        if not (raw / fname).exists():
            print(
                f"[hotpotqa] ERROR: {raw / fname} not found.\n"
                "  Run: python scripts/download_datasets.py --dataset hotpotqa"
            )
            return

    if _processed_files_exist(out) and not args.force:
        print(f"[hotpotqa] Processed files already exist in {out}. Skipping (use --force).")
    else:
        print(f"[hotpotqa] Reading raw files from {raw} …")
        raw_queries = _read_jsonl_raw(raw / "queries.jsonl")
        raw_docs = _read_jsonl_raw(raw / "documents.jsonl")
        raw_qrels = _read_jsonl_raw(raw / "qrels.jsonl")

        queries = [Query.from_dict(q) for q in raw_queries]
        documents = [Document.from_dict(d) for d in raw_docs]
        qrels = [QrelEntry.from_dict(q) for q in raw_qrels]

        print("[hotpotqa] Writing processed files …")
        _write_jsonl(queries, out / "queries.jsonl")
        _write_jsonl(documents, out / "documents.jsonl")
        _write_jsonl(qrels, out / "qrels.jsonl")

    _generate_preferences("hotpotqa", out, args)


def prepare_bright(args: argparse.Namespace) -> None:
    """Prepare BRIGHT (requires manual download if not available)."""
    cfg = get_config("bright")
    raw = cfg.raw_path
    out = cfg.processed_path

    for fname in ("queries.jsonl", "documents.jsonl", "qrels.jsonl"):
        if not (raw / fname).exists():
            print(
                f"[bright] Raw file not found: {raw / fname}\n"
                f"  BRIGHT requires manual download.\n"
                f"  See: {raw / 'README.md'}\n"
                f"  Or run: python scripts/download_datasets.py --dataset bright"
            )
            return

    if _processed_files_exist(out) and not args.force:
        print(f"[bright] Processed files already exist in {out}. Skipping (use --force).")
    else:
        print(f"[bright] Reading raw files from {raw} …")
        try:
            queries, documents, qrels = load_raw_bright_splits(raw)
        except BrightSchemaError as exc:
            print(f"[bright] ERROR: invalid BRIGHT raw format: {exc}")
            return

        print("[bright] Writing processed files …")
        _write_jsonl(queries, out / "queries.jsonl")
        _write_jsonl(documents, out / "documents.jsonl")
        _write_jsonl(qrels, out / "qrels.jsonl")

    _generate_preferences("bright", out, args)


def _generate_preferences(name: str, processed_path: Path, args: argparse.Namespace) -> None:
    """Generate pairwise preferences and write to pairwise/preferences.jsonl."""
    cfg = get_config(name)
    top_k = args.top_k if args.top_k is not None else cfg.top_k
    max_queries = args.max_queries if args.max_queries is not None else cfg.max_queries
    seed = args.seed if args.seed is not None else cfg.seed
    weight_scheme = args.weight_scheme

    pairwise_dir = processed_path / "pairwise"
    pref_path = pairwise_dir / "preferences.jsonl"

    if pref_path.exists() and not args.force:
        print(f"[{name}] Pairwise file already exists: {pref_path}. Skipping (use --force).")
        return

    qrels_path = processed_path / "qrels.jsonl"
    if not qrels_path.exists():
        print(f"[{name}] qrels.jsonl not found; skipping preference generation.")
        return

    qrels = [QrelEntry.from_dict(r) for r in _read_jsonl_raw(qrels_path)]
    print(f"[{name}] Generating pairwise preferences (top_k={top_k}, max_queries={max_queries}) …")
    prefs = preferences_from_qrels(
        qrels,
        top_k=top_k,
        max_queries=max_queries,
        seed=seed,
        weight_scheme=weight_scheme,
    )
    out_path = save_pairwise_preferences(prefs, pairwise_dir)
    print(f"[{name}] {len(prefs)} preferences → {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare benchmark datasets into unified JSONL format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dataset",
        choices=DATASET_NAMES + ["all"],
        default="all",
        help="Dataset to prepare (default: all)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Max candidate docs per query for preference generation (default: from registry)",
    )
    parser.add_argument(
        "--max-queries",
        type=int,
        default=None,
        help="Max queries to process (default: from registry)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed (default: from registry)",
    )
    parser.add_argument(
        "--weight-scheme",
        choices=["grade_diff", "binary"],
        default="grade_diff",
        help="Preference weight scheme (default: grade_diff)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-write output files even if they already exist",
    )
    args = parser.parse_args()

    targets = DATASET_NAMES if args.dataset == "all" else [args.dataset]

    for name in targets:
        print(f"\n{'='*60}")
        print(f"  Preparing: {name}")
        print(f"{'='*60}")
        if name in _STANDARD_RAW_JSONL:
            prepare_standard_jsonl_raw(name, args)
        elif name == "hotpotqa":
            prepare_hotpotqa(args)
        elif name == "bright":
            prepare_bright(args)

    print("\nAll requested preparations complete.")


if __name__ == "__main__":
    main()
