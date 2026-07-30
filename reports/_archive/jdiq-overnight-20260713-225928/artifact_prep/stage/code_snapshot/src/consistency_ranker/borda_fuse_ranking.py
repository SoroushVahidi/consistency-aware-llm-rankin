"""
Borda count fusion over multiple retrieval ranked lists (partial-list / runs).

For each query, let :math:`U_q` be the union of document ids appearing in the
provided score-prior files for that query, and :math:`N_q = |U_q|`.  For each
ranker *s*, sort by descending score with ``doc_id`` ascending tie-break
(same convention as RRF / CombSUM).  If document *d* has 1-based rank
:math:`r_s(d)` in *s*, assign

    borda_points_s(d) = N_q - r_s(d)

and **0** if *d* is missing from that ranker's run.  The fused score is

    Borda(d) = sum_s borda_points_s(d)

This is a rank-aggregation baseline over ``--score-prior-files``, **not** the
graph tournament Borda in ``baseline_ranking.borda_ranking`` (out-degree /
Copeland-style on pairwise preferences).

References: Dwork, Kumar, Naor, Sivakumar (WWW 2001); Fox & Shaw (TREC-2).
"""

from __future__ import annotations

from typing import Iterable

from consistency_ranker.rrf_ranking import ranked_list_from_score_entries

# Tie-break: min rank across rankers where the doc appears (smaller = better).
_NO_RANK = 10**9


def _union_docs_for_query(
    query_id: str,
    score_maps: list[dict[str, list[tuple[str, float]]]],
) -> set[str]:
    """Documents appearing in any score-prior file for this query."""
    u: set[str] = set()
    for sm in score_maps:
        for doc_id, _ in sm.get(str(query_id), []):
            u.add(str(doc_id))
    return u


def borda_fuse_scores_and_best_ranks(
    per_system_ranked_lists: list[list[str]],
    *,
    n_q: int,
) -> tuple[dict[str, float], dict[str, int]]:
    """Accumulate Borda scores and best (minimum) rank per doc across systems.

    Parameters
    ----------
    per_system_ranked_lists:
        One total order per ranker (e.g. from ``ranked_list_from_score_entries``).
    n_q:
        Fusion universe size :math:`N_q = |U_q|` for this query.  Must be
        non-negative.  When 0, every per-ranker contribution is 0.
    """
    if n_q < 0:
        raise ValueError(f"n_q must be non-negative, got {n_q}")
    borda: dict[str, float] = {}
    best_rank: dict[str, int] = {}
    for ranked in per_system_ranked_lists:
        for rank, doc_id in enumerate(ranked, start=1):
            sid = str(doc_id)
            pts = float(n_q - rank) if n_q > 0 else 0.0
            borda[sid] = borda.get(sid, 0.0) + pts
            prev = best_rank.get(sid, _NO_RANK)
            if rank < prev:
                best_rank[sid] = rank
    return borda, best_rank


def borda_fuse_scores(
    per_system_ranked_lists: list[list[str]],
    *,
    n_q: int,
) -> dict[str, float]:
    """Per-document Borda fused scores (sum of ``N_q - rank`` contributions)."""
    fused, _ = borda_fuse_scores_and_best_ranks(per_system_ranked_lists, n_q=n_q)
    return fused


def borda_fuse_ranking(
    per_system_ranked_lists: list[list[str]],
    candidate_doc_ids: Iterable[str],
    *,
    n_q: int,
) -> list[str]:
    """Rank *candidate_doc_ids* by Borda fusion with deterministic tie-breaking.

    Order
    -----
    1. Higher Borda score.
    2. Smaller best original rank (among rankers where the doc appears).
    3. ``doc_id`` ascending.
    """
    candidates = list(candidate_doc_ids)
    scores, best_rank = borda_fuse_scores_and_best_ranks(
        per_system_ranked_lists, n_q=n_q
    )
    return sorted(
        candidates,
        key=lambda d: (-scores.get(d, 0.0), best_rank.get(d, _NO_RANK), d),
    )


def per_query_borda_fuse_ranking_from_score_maps(
    query_id: str,
    score_maps: list[dict[str, list[tuple[str, float]]]],
    candidate_doc_ids: Iterable[str],
) -> list[str]:
    """Borda fusion for one query from score JSONL index structures.

    :math:`U_q` and :math:`N_q` are computed from the union of ``doc_id`` values
    in the score maps for *query_id* only (not from the preference graph).
    """
    n_q = len(_union_docs_for_query(query_id, score_maps))
    lists = [
        ranked_list_from_score_entries(sm.get(str(query_id), [])) for sm in score_maps
    ]
    return borda_fuse_ranking(lists, candidate_doc_ids, n_q=n_q)
