"""
Reciprocal Rank Fusion (RRF) for merging multiple ranked lists.

Cormack, Clarke, Buettcher (SIGIR 2009).  Standard form::

    RRF(d) = sum_s 1 / (k + rank_s(d))

where *rank_s(d)* is the 1-based rank of document *d* in system *s*, and
missing documents contribute 0 for that system.

This module is used by the real-data pipeline when ``--score-prior-files``
provides multiple ranker runs (e.g. BM25, TF-IDF, MiniLM).
"""

from __future__ import annotations

from typing import Iterable

# Default k matches common practice (Cormack et al.; Anserini/BEIR fusion docs).
DEFAULT_RRF_K = 60.0

# Sentinel for documents that never appear in any system's list (tie-break).
_NO_RANK: int = 10**9


def ranked_list_from_score_entries(entries: list[tuple[str, float]]) -> list[str]:
    """Deduplicate by doc id (max score), then sort by (-score, doc_id).

    Produces a deterministic total order for one ranker's score rows for a query.
    """
    best: dict[str, float] = {}
    for doc_id, score in entries:
        sid = str(doc_id)
        best[sid] = max(best.get(sid, float(score)), float(score))
    return [d for d, _ in sorted(best.items(), key=lambda x: (-x[1], x[0]))]


def rrf_scores_and_best_ranks(
    per_system_ranked_lists: list[list[str]],
    *,
    k: float = DEFAULT_RRF_K,
) -> tuple[dict[str, float], dict[str, int]]:
    """Accumulate RRF scores and best (minimum) rank per doc across systems.

    Returns
    -------
    rrf_score :
        Sum of ``1/(k + rank)`` over systems where the doc appears.
    best_rank :
        Minimum 1-based rank observed across systems; absent if never listed.
    """
    if k <= 0:
        raise ValueError(f"rrf k must be positive, got {k}")
    rrf: dict[str, float] = {}
    best_rank: dict[str, int] = {}
    for ranked in per_system_ranked_lists:
        for rank, doc_id in enumerate(ranked, start=1):
            sid = str(doc_id)
            rrf[sid] = rrf.get(sid, 0.0) + 1.0 / (k + rank)
            prev = best_rank.get(sid, _NO_RANK)
            if rank < prev:
                best_rank[sid] = rank
    return rrf, best_rank


def rrf_ranking(
    per_system_ranked_lists: list[list[str]],
    candidate_doc_ids: Iterable[str],
    *,
    k: float = DEFAULT_RRF_K,
) -> list[str]:
    """RRF ranking over *candidate_doc_ids* with deterministic tie-breaking.

    Order
    -----
    1. Higher RRF score first.
    2. If tied, smaller best rank across systems (better peak position).
    3. If still tied, lexicographic ``doc_id``.
    """
    candidates = list(candidate_doc_ids)
    scores, best_rank = rrf_scores_and_best_ranks(per_system_ranked_lists, k=k)
    return sorted(
        candidates,
        key=lambda d: (
            -scores.get(d, 0.0),
            best_rank.get(d, _NO_RANK),
            d,
        ),
    )


def per_query_rrf_ranking_from_score_maps(
    query_id: str,
    score_maps: list[dict[str, list[tuple[str, float]]]],
    candidate_doc_ids: Iterable[str],
    *,
    k: float = DEFAULT_RRF_K,
) -> list[str]:
    """Build RRF ranking for one query from loaded score JSONL index structures."""
    lists = [
        ranked_list_from_score_entries(sm.get(str(query_id), [])) for sm in score_maps
    ]
    return rrf_ranking(lists, candidate_doc_ids, k=k)
