"""
CombSUM score fusion across multiple ranker runs (Fox & Shaw–style combination).

For each query, fuse ranker outputs with::

    CombSUM(d) = sum_s normalized_score_s(d)

where *normalized_score_s(d)* is the contribution from ranker *s*.  Missing
documents in a ranker contribute **0** for that ranker.

Default normalization is **min–max per (query, ranker)** to [0, 1] so BM25,
TF-IDF, and neural scores on different scales can be summed meaningfully.

This is distinct from the graph method ``score_sum`` in ``baseline_ranking.py``,
which sums **edge weights** on a pairwise preference graph.
"""

from __future__ import annotations

from typing import Iterable

# Normalization modes for CLI / experiments
COMBSUM_NORM_MINMAX = "minmax"
COMBSUM_NORM_NONE = "none"
COMBSUM_NORMALIZATIONS = (COMBSUM_NORM_MINMAX, COMBSUM_NORM_NONE)

# Tie-break: min rank across rankers where the doc appears (smaller = better).
_NO_RANK = 10**9

# Treat scores as constant within numerical tolerance (matches baseline_ranking).
_SCORE_TIE_EPS = 1.0e-12


def dedupe_best_scores(entries: list[tuple[str, float]]) -> dict[str, float]:
    """Per ranker, keep max score per ``doc_id`` (same convention as RRF)."""
    best: dict[str, float] = {}
    for doc_id, score in entries:
        sid = str(doc_id)
        best[sid] = max(best.get(sid, float(score)), float(score))
    return best


def _ranks_from_best(best: dict[str, float]) -> dict[str, int]:
    """1-based ranks after sorting by (-score, doc_id)."""
    ordered = sorted(best.items(), key=lambda x: (-x[1], x[0]))
    return {doc_id: rank for rank, (doc_id, _) in enumerate(ordered, start=1)}


def _minmax_normalize_query_ranker(best: dict[str, float]) -> dict[str, float]:
    """Min–max to [0, 1] for one ranker on one query.

    If all scores are equal (within ``_SCORE_TIE_EPS``), every normalized value
    is **0.0** so that ranker adds no discriminative signal for CombSUM (the
    run is flat).
    """
    if not best:
        return {}
    vals = list(best.values())
    lo, hi = min(vals), max(vals)
    if hi - lo <= _SCORE_TIE_EPS:
        return {d: 0.0 for d in best}
    return {d: (best[d] - lo) / (hi - lo) for d in best}


def _combsum_fused_and_best_ranks(
    per_system_best_scores: list[dict[str, float]],
    *,
    normalization: str,
) -> tuple[dict[str, float], dict[str, int]]:
    if normalization not in COMBSUM_NORMALIZATIONS:
        raise ValueError(
            f"normalization must be one of {COMBSUM_NORMALIZATIONS}, got {normalization!r}"
        )
    fused: dict[str, float] = {}
    best_rank: dict[str, int] = {}
    for best in per_system_best_scores:
        if not best:
            continue
        if normalization == COMBSUM_NORM_MINMAX:
            contrib = _minmax_normalize_query_ranker(best)
        else:
            contrib = dict(best)
        ranks = _ranks_from_best(best)
        for d, w in contrib.items():
            fused[d] = fused.get(d, 0.0) + float(w)
            r = ranks[d]
            prev = best_rank.get(d, _NO_RANK)
            if r < prev:
                best_rank[d] = r
    return fused, best_rank


def combsum_scores(
    per_system_best_scores: list[dict[str, float]],
    *,
    normalization: str = COMBSUM_NORM_MINMAX,
) -> dict[str, float]:
    """Fused CombSUM scores (sum of per-ranker contributions) per document."""
    fused, _ = _combsum_fused_and_best_ranks(
        per_system_best_scores, normalization=normalization
    )
    return fused


def combsum_ranking(
    per_system_best_scores: list[dict[str, float]],
    candidate_doc_ids: Iterable[str],
    *,
    normalization: str = COMBSUM_NORM_MINMAX,
) -> list[str]:
    """Rank *candidate_doc_ids* by CombSUM with deterministic tie-breaking.

    Order
    -----
    1. Higher CombSUM score.
    2. Smaller best original rank (among rankers where the doc appears).
    3. ``doc_id`` ascending.
    """
    fused, best_rank = _combsum_fused_and_best_ranks(
        per_system_best_scores, normalization=normalization
    )
    candidates = list(candidate_doc_ids)
    return sorted(
        candidates,
        key=lambda d: (-fused.get(d, 0.0), best_rank.get(d, _NO_RANK), d),
    )


def per_query_combsum_ranking_from_score_maps(
    query_id: str,
    score_maps: list[dict[str, list[tuple[str, float]]]],
    candidate_doc_ids: Iterable[str],
    *,
    normalization: str = COMBSUM_NORM_MINMAX,
) -> list[str]:
    """CombSUM ranking for one query from score JSONL index structures."""
    per_system = [dedupe_best_scores(sm.get(str(query_id), [])) for sm in score_maps]
    return combsum_ranking(per_system, candidate_doc_ids, normalization=normalization)
