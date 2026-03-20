"""
unified_loader.py
=================
Unified interface for loading any registered dataset and converting
relevance labels into pairwise preferences.

Main entry points
-----------------
:func:`load_dataset_splits`
    Load (queries, documents, qrels) for a named dataset from local JSONL
    files produced by ``prepare_datasets.py``.

:func:`preferences_from_qrels`
    Derive :class:`~consistency_ranker.data.schema.PairwisePreference`
    objects from a list of :class:`~consistency_ranker.data.schema.QrelEntry`
    objects.

:func:`save_pairwise_preferences`
    Write pairwise preferences to JSONL under
    ``data/processed/<dataset>/pairwise/``.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Callable, TypeVar

from .dataset_registry import DatasetConfig, get_config
from .schema import Document, PairwisePreference, QrelEntry, Query

_T = TypeVar("_T")


# ---------------------------------------------------------------------------
# Load already-processed JSONL splits
# ---------------------------------------------------------------------------

def load_dataset_splits(
    name_or_config: str | DatasetConfig,
) -> tuple[list[Query], list[Document], list[QrelEntry]]:
    """Load queries, documents, and qrels from local processed JSONL files.

    Files are expected at::

        <processed_path>/queries.jsonl
        <processed_path>/documents.jsonl
        <processed_path>/qrels.jsonl

    Run ``python scripts/prepare_datasets.py --dataset <name>`` first.

    Parameters
    ----------
    name_or_config:
        Dataset short name (``"scidocs"``, ``"fiqa"``, etc.) or a
        :class:`~consistency_ranker.data.dataset_registry.DatasetConfig`.

    Returns
    -------
    tuple[list[Query], list[Document], list[QrelEntry]]

    Raises
    ------
    FileNotFoundError
        If the processed files do not exist yet.
    """
    cfg = _resolve(name_or_config)
    base = cfg.processed_path

    queries_path = base / "queries.jsonl"
    docs_path = base / "documents.jsonl"
    qrels_path = base / "qrels.jsonl"

    for p in (queries_path, docs_path, qrels_path):
        if not p.exists():
            raise FileNotFoundError(
                f"{p} does not exist. "
                f"Run: python scripts/prepare_datasets.py --dataset {cfg.name}"
            )

    queries = _load_jsonl(queries_path, Query.from_dict)
    documents = _load_jsonl(docs_path, Document.from_dict)
    qrels = _load_jsonl(qrels_path, QrelEntry.from_dict)
    return queries, documents, qrels


# ---------------------------------------------------------------------------
# Pairwise preferences from qrels
# ---------------------------------------------------------------------------

def preferences_from_qrels(
    qrels: list[QrelEntry],
    top_k: int = 100,
    max_queries: int | None = None,
    seed: int = 42,
    weight_scheme: str = "grade_diff",
) -> list[PairwisePreference]:
    """Derive pairwise document preferences from relevance judgements.

    For each query, all pairs of judged documents (a, b) where
    ``rel(a) > rel(b)`` yield a preference ``a > b``.

    Parameters
    ----------
    qrels:
        Relevance judgements.
    top_k:
        Maximum number of candidate documents per query.  Documents are
        selected by descending relevance grade; ties broken randomly.
    max_queries:
        If set, only the first *max_queries* unique query ids are processed.
    seed:
        Random seed for reproducible tie-breaking when restricting to top_k.
    weight_scheme:
        How to assign preference weights:

        - ``"grade_diff"``: weight = rel(a) − rel(b)  (0 is clipped to 1e-6)
        - ``"binary"``: weight = 1.0 for all preferences

    Returns
    -------
    list[PairwisePreference]

    Raises
    ------
    ValueError
        If *weight_scheme* is not recognised.
    """
    if weight_scheme not in {"grade_diff", "binary"}:
        raise ValueError(
            f"Unknown weight_scheme {weight_scheme!r}. "
            "Choose 'grade_diff' or 'binary'."
        )

    rng = random.Random(seed)

    # Group by query
    by_query: dict[str, list[QrelEntry]] = defaultdict(list)
    for q in qrels:
        by_query[q.query_id].append(q)

    query_ids = sorted(by_query.keys())
    if max_queries is not None:
        query_ids = query_ids[:max_queries]

    preferences: list[PairwisePreference] = []

    for qid in query_ids:
        entries = by_query[qid]

        # Sort by relevance descending, then shuffle for tie-breaking
        rng.shuffle(entries)
        entries.sort(key=lambda e: e.relevance, reverse=True)

        # Restrict to top_k candidates
        candidates = entries[:top_k]

        # Generate all ordered pairs where rel_a > rel_b
        for i in range(len(candidates)):
            for j in range(i + 1, len(candidates)):
                a = candidates[i]
                b = candidates[j]
                if a.relevance > b.relevance:
                    w = _weight(a.relevance, b.relevance, weight_scheme)
                    preferences.append(
                        PairwisePreference(
                            query_id=qid,
                            winner_doc_id=a.doc_id,
                            loser_doc_id=b.doc_id,
                            weight=w,
                        )
                    )
                # Equal relevance entries are skipped (no preference)

    return preferences


def _weight(rel_a: int, rel_b: int, scheme: str) -> float:
    """Compute preference weight from relevance grades."""
    if scheme == "binary":
        return 1.0
    diff = float(rel_a - rel_b)
    return max(diff, 1e-6)


# ---------------------------------------------------------------------------
# Save pairwise preferences
# ---------------------------------------------------------------------------

def save_pairwise_preferences(
    preferences: list[PairwisePreference],
    output_dir: Path,
    filename: str = "preferences.jsonl",
) -> Path:
    """Write pairwise preferences to a JSONL file.

    Parameters
    ----------
    preferences:
        Preferences to write.
    output_dir:
        Target directory (created if necessary).
    filename:
        Name of the output file.

    Returns
    -------
    Path
        The path to the written file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / filename
    with out_path.open("w", encoding="utf-8") as fh:
        for p in preferences:
            fh.write(json.dumps(p.to_dict()) + "\n")
    return out_path


def load_pairwise_preferences(path: Path) -> list[PairwisePreference]:
    """Load pairwise preferences from a JSONL file.

    Parameters
    ----------
    path:
        Path to the JSONL file.

    Returns
    -------
    list[PairwisePreference]
    """
    prefs: list[PairwisePreference] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                prefs.append(PairwisePreference.from_dict(json.loads(line)))
    return prefs


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve(name_or_config: str | DatasetConfig) -> DatasetConfig:
    if isinstance(name_or_config, str):
        return get_config(name_or_config)
    return name_or_config


def _load_jsonl(path: Path, from_dict: Callable[[dict], _T]) -> list[_T]:
    """Generic JSONL loader."""
    records = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(from_dict(json.loads(line)))
    return records
