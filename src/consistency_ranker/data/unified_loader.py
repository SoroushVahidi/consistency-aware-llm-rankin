"""
unified_loader.py
=================
Unified interface for loading any registered dataset and converting
relevance labels or model scores into pairwise preferences.

Main entry points
-----------------
:func:`load_dataset_splits`
    Load (queries, documents, qrels) for a named dataset from local JSONL
    files produced by ``prepare_datasets.py``.

:func:`preferences_from_qrels`
    Derive :class:`~consistency_ranker.data.schema.PairwisePreference`
    objects from a list of :class:`~consistency_ranker.data.schema.QrelEntry`
    objects.

:func:`preferences_from_scores`
    Derive :class:`~consistency_ranker.data.schema.PairwisePreference`
    objects from per-query candidate ids and scalar scores (e.g. from a
    reranker or cross-encoder).

:func:`load_score_rankings`
    Load per-query candidate scores from a JSONL file (e.g. from BM25,
    dense retriever, or cross-encoder).

:func:`preferences_from_multiple_score_rankings`
    Aggregate rankings from multiple scorers into pairwise preferences.
    Disagreement between scorers can create cycles.

:func:`load_multi_scorer_rankings`
    Load score rankings from multiple scorer files into a nested structure.

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
from .schema import CandidateRanking, Document, PairwisePreference, QrelEntry, Query

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


# ---------------------------------------------------------------------------
# Pairwise preferences from model scores
# ---------------------------------------------------------------------------

# Minimum edge weight to avoid zero-weight edges (e.g. for downstream solvers).
_MIN_SCORE_WEIGHT = 1e-6


def preferences_from_scores(
    query_id: str,
    candidates: list[tuple[str, float]],
    weight_scheme: str = "absolute_margin",
    min_margin: float | None = None,
) -> list[PairwisePreference]:
    """Derive pairwise document preferences from per-query candidate scores.

    For each pair (i, j) where score[i] > score[j], yields a preference
    i > j with a weight determined by *weight_scheme*.

    Parameters
    ----------
    query_id:
        Unique identifier for the query.
    candidates:
        List of (doc_id, score) tuples. Higher score means more preferred.
    weight_scheme:
        How to assign edge weights:

        - ``"binary"``: weight = 1.0 for all preferences.
        - ``"absolute_margin"``: weight = |score_i - score_j|.
        - ``"normalized_margin"``: weight = (score_i - score_j) / (max - min)
          over the candidate set, clamped to [0, 1]. Uses ``_MIN_SCORE_WEIGHT``
          when the score range is zero.

    min_margin:
        If set, pairs whose score difference is strictly below this threshold
        are ignored (no preference edge is created). Applied to the absolute
        score difference before any weighting.

    Returns
    -------
    list[PairwisePreference]
        Preferences suitable for :func:`build_graph` (after conversion to
        :class:`~consistency_ranker.pairwise_prefs.Preference`) or
        :func:`save_pairwise_preferences`.

    Raises
    ------
    ValueError
        If *weight_scheme* is not recognised.
    """
    if weight_scheme not in {"binary", "absolute_margin", "normalized_margin"}:
        raise ValueError(
            f"Unknown weight_scheme {weight_scheme!r}. "
            "Choose 'binary', 'absolute_margin', or 'normalized_margin'."
        )

    if len(candidates) < 2:
        return []

    scores = [s for _, s in candidates]
    score_min = min(scores)
    score_max = max(scores)
    score_range = score_max - score_min

    preferences: list[PairwisePreference] = []

    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            doc_a, score_a = candidates[i]
            doc_b, score_b = candidates[j]

            if score_a == score_b:
                continue

            winner_id, loser_id = (doc_a, doc_b) if score_a > score_b else (doc_b, doc_a)
            margin = abs(score_a - score_b)

            if min_margin is not None and margin < min_margin:
                continue

            w = _weight_from_scores(
                score_winner=max(score_a, score_b),
                score_loser=min(score_a, score_b),
                score_range=score_range,
                scheme=weight_scheme,
            )
            preferences.append(
                PairwisePreference(
                    query_id=query_id,
                    winner_doc_id=winner_id,
                    loser_doc_id=loser_id,
                    weight=w,
                )
            )

    return preferences


# ---------------------------------------------------------------------------
# Pairwise preferences from multiple scorers
# ---------------------------------------------------------------------------


def preferences_from_multiple_score_rankings(
    query_id: str,
    scorer_rankings: dict[str, list[tuple[str, float]]],
    weight_mode: str = "vote_plus_margin",
    min_margin: float | None = None,
) -> list[PairwisePreference]:
    """Derive pairwise preferences by aggregating multiple scorer rankings.

    When scorers disagree on pair (i, j), the aggregated graph can contain
    cycles (e.g. BM25 says A>B, dense says B>C, cross-encoder says C>A).

    Parameters
    ----------
    query_id:
        Unique identifier for the query.
    scorer_rankings:
        Mapping scorer_name → [(doc_id, score), ...] for this query.
        Each list is in descending score order. Higher score = more preferred.
    weight_mode:
        How to aggregate across scorers:

        - ``"majority_vote"``: Each scorer votes on (i, j). Edge direction
          follows majority. Weight = number of votes for winner.
        - ``"summed_margin"``: For each pair, sum signed (score_i - score_j)
          across scorers. Direction from sign. Weight = absolute summed value.
        - ``"vote_plus_margin"``: Direction from majority vote. Weight =
          votes_for_winner + mean of (score_winner - score_loser) over
          scorers that agree with majority.

    min_margin:
        If set, pairs whose aggregate margin is below this threshold are
        skipped. For majority_vote: skip ties (votes equal). For summed_margin:
        skip when |sum| < min_margin. For vote_plus_margin: skip when mean
        margin from agreeing scorers < min_margin.

    Returns
    -------
    list[PairwisePreference]
        Preferences suitable for :func:`build_graph` (after conversion to
        :class:`~consistency_ranker.pairwise_prefs.Preference`).

    Note
    ----
    **Missing docs:** The candidate set is the **union** of doc_ids across
    scorers. For each pair (i, j), only scorers that contain **both** docs
    contribute. If a scorer lacks one or both docs, it is skipped for that pair.
    """
    if weight_mode not in {"majority_vote", "summed_margin", "vote_plus_margin"}:
        raise ValueError(
            f"Unknown weight_mode {weight_mode!r}. "
            "Choose 'majority_vote', 'summed_margin', or 'vote_plus_margin'."
        )

    # Union of candidates across scorers
    all_doc_ids: set[str] = set()
    for candidates in scorer_rankings.values():
        all_doc_ids.update(doc_id for doc_id, _ in candidates)

    # Build doc_id -> score for each scorer
    scorer_scores: dict[str, dict[str, float]] = {}
    for name, candidates in scorer_rankings.items():
        scorer_scores[name] = {doc_id: score for doc_id, score in candidates}

    doc_list = sorted(all_doc_ids)
    preferences: list[PairwisePreference] = []

    for i in range(len(doc_list)):
        for j in range(i + 1, len(doc_list)):
            doc_a, doc_b = doc_list[i], doc_list[j]

            # Scorers that have both docs
            votes_a_wins: list[str] = []
            votes_b_wins: list[str] = []
            margins_a_wins: list[float] = []
            margins_b_wins: list[float] = []
            signed_diffs: list[float] = []

            for name, scores in scorer_scores.items():
                if doc_a not in scores or doc_b not in scores:
                    continue
                sa, sb = scores[doc_a], scores[doc_b]
                if sa == sb:
                    continue
                diff = sa - sb
                if diff > 0:
                    votes_a_wins.append(name)
                    margins_a_wins.append(diff)
                    signed_diffs.append(diff)
                else:
                    votes_b_wins.append(name)
                    margins_b_wins.append(-diff)
                    signed_diffs.append(diff)

            if not votes_a_wins and not votes_b_wins:
                continue

            # Determine direction and weight
            if weight_mode == "majority_vote":
                n_a, n_b = len(votes_a_wins), len(votes_b_wins)
                if n_a == n_b:
                    continue
                if n_a > n_b:
                    winner_id, loser_id = doc_a, doc_b
                    w = float(n_a)
                    vote_margin = n_a - n_b
                else:
                    winner_id, loser_id = doc_b, doc_a
                    w = float(n_b)
                    vote_margin = n_b - n_a
                if min_margin is not None and vote_margin < min_margin:
                    continue

            elif weight_mode == "summed_margin":
                total = sum(signed_diffs)
                if abs(total) < (_MIN_SCORE_WEIGHT if min_margin is None else min_margin):
                    continue
                if total > 0:
                    winner_id, loser_id = doc_a, doc_b
                    w = total
                else:
                    winner_id, loser_id = doc_b, doc_a
                    w = -total
                w = max(w, _MIN_SCORE_WEIGHT)

            else:  # vote_plus_margin
                n_a, n_b = len(votes_a_wins), len(votes_b_wins)
                if n_a == n_b:
                    continue
                if n_a > n_b:
                    winner_id, loser_id = doc_a, doc_b
                    votes = n_a
                    margins = margins_a_wins
                else:
                    winner_id, loser_id = doc_b, doc_a
                    votes = n_b
                    margins = margins_b_wins
                mean_margin = sum(margins) / len(margins) if margins else 0.0
                w = float(votes) + mean_margin
                w = max(w, _MIN_SCORE_WEIGHT)
                if min_margin is not None and mean_margin < min_margin:
                    continue

            preferences.append(
                PairwisePreference(
                    query_id=query_id,
                    winner_doc_id=winner_id,
                    loser_doc_id=loser_id,
                    weight=w,
                )
            )

    return preferences


def load_multi_scorer_rankings(
    scorer_paths: dict[str, Path],
) -> dict[str, dict[str, list[tuple[str, float]]]]:
    """Load score rankings from multiple scorer files.

    Parameters
    ----------
    scorer_paths:
        Mapping scorer_name → path to JSONL file. Each file has the same
        format as :func:`load_score_rankings` expects.

    Returns
    -------
    dict[str, dict[str, list[tuple[str, float]]]]
        Mapping scorer_name → {query_id: [(doc_id, score), ...]}.
        Scorers that fail to load are omitted (no exception raised).

    Example
    -------
    ::

        paths = {
            "bm25": Path("data/processed/fiqa/scores/bm25.jsonl"),
            "dense": Path("data/processed/fiqa/scores/dense.jsonl"),
        }
        multi = load_multi_scorer_rankings(paths)
        # multi["bm25"]["q1"] = [(d1, 0.9), (d2, 0.5), ...]
    """
    result: dict[str, dict[str, list[tuple[str, float]]]] = {}
    for name, path in scorer_paths.items():
        if not path.exists():
            continue
        try:
            result[name] = load_score_rankings(path)
        except (ValueError, OSError):
            continue
    return result


# ---------------------------------------------------------------------------
# Load score rankings from JSONL
# ---------------------------------------------------------------------------


def save_score_rankings(
    rankings: dict[str, list[tuple[str, float]]],
    output_path: Path,
) -> Path:
    """Write per-query score rankings to a JSONL file.

    Parameters
    ----------
    rankings:
        Mapping query_id → [(doc_id, score), ...].
    output_path:
        Output file path (parent dirs created if needed).

    Returns
    -------
    Path
        The written file path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for qid, candidates in sorted(rankings.items()):
            doc_ids = [c[0] for c in candidates]
            scores = [c[1] for c in candidates]
            rec = CandidateRanking(query_id=qid, ranked_doc_ids=doc_ids, scores=scores)
            fh.write(json.dumps(rec.to_dict()) + "\n")
    return output_path


def load_score_rankings(path: Path) -> dict[str, list[tuple[str, float]]]:
    """Load per-query candidate scores from a JSONL file.

    Expected format (one JSON object per line, matching :class:`CandidateRanking`)::

        {"query_id": "q1", "ranked_doc_ids": ["d1", "d2", "d3"], "scores": [0.92, 0.71, 0.45]}

    Parameters
    ----------
    path:
        Path to the JSONL file.

    Returns
    -------
    dict[str, list[tuple[str, float]]]
        Mapping query_id → [(doc_id, score), ...]. Scores are in descending
        order (best first) as in the file.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    """
    result: dict[str, list[tuple[str, float]]] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = CandidateRanking.from_dict(json.loads(line))
            doc_ids = rec.ranked_doc_ids
            scores = rec.scores
            if scores is None:
                scores = [1.0] * len(doc_ids)  # fallback: uniform
            if len(scores) != len(doc_ids):
                raise ValueError(
                    f"query_id={rec.query_id}: len(ranked_doc_ids)={len(doc_ids)} "
                    f"!= len(scores)={len(scores)}"
                )
            result[rec.query_id] = list(zip(doc_ids, scores, strict=True))
    return result


def _weight_from_scores(
    score_winner: float,
    score_loser: float,
    score_range: float,
    scheme: str,
) -> float:
    """Compute preference weight from score pair."""
    if scheme == "binary":
        return 1.0
    if scheme == "absolute_margin":
        w = score_winner - score_loser
        return max(w, _MIN_SCORE_WEIGHT)
    # normalized_margin
    if score_range <= 0:
        return _MIN_SCORE_WEIGHT
    w = (score_winner - score_loser) / score_range
    return max(w, _MIN_SCORE_WEIGHT)


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
