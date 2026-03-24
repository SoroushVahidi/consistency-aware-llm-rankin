"""
tournament_agg.py
=================
Tournament / graph aggregation baselines over pairwise preferences.

These methods operate on the *same pairwise preference data* as the main
consistency-repair pipeline, but use different aggregation strategies.
This allows a fair comparison: given the same pairwise judgments, how do
different aggregation methods compare to our FAS-repair approach?

Methods
-------
1. **Bradley-Terry MLE** — parametric model fitting (strength parameters)
2. **Copeland score** — wins minus losses (already in baseline_ranking.py,
   re-exposed here for the combined comparison pipeline)
3. **Win-rate ranking** — simple win fraction per document
4. **Markov chain (random walk)** — stationary distribution of a transition
   matrix built from pairwise outcomes
5. **Tournament sort** — merge-sort-style using pairwise outcomes as comparator

Provenance
----------
- Bradley & Terry (1952), "Rank analysis of incomplete block designs"
- Copeland (1951), social choice theory
- Markov chain ranking: Dwork et al. (2001), "Rank aggregation methods for the web"
- Label: "Tier A — well-defined classical algorithms applied to pairwise data"
"""

from __future__ import annotations

import logging
from collections import defaultdict

import networkx as nx
import numpy as np

from rerankers.common import RerankerResult

log = logging.getLogger(__name__)


def copeland_ranking(
    preferences: list[tuple[str, str, float]],
    all_doc_ids: list[str] | None = None,
) -> RerankerResult:
    """Rank by Copeland score: wins - losses.

    Parameters
    ----------
    preferences:
        List of (winner_id, loser_id, weight) tuples.
    all_doc_ids:
        Complete set of document IDs (for documents with no comparisons).
    """
    wins: dict[str, int] = defaultdict(int)
    losses: dict[str, int] = defaultdict(int)
    seen: set[str] = set()
    for winner, loser, _ in preferences:
        wins[winner] += 1
        losses[loser] += 1
        seen.add(winner)
        seen.add(loser)

    ids = list(seen)
    if all_doc_ids:
        ids = list(set(ids) | set(all_doc_ids))

    scores = {d: wins.get(d, 0) - losses.get(d, 0) for d in ids}
    ranked = sorted(scores, key=lambda d: (-scores[d], d))

    return RerankerResult(
        query_id="",
        ranked_doc_ids=ranked,
        scores={d: float(s) for d, s in scores.items()},
        metadata={"method": "copeland"},
    )


def win_rate_ranking(
    preferences: list[tuple[str, str, float]],
    all_doc_ids: list[str] | None = None,
) -> RerankerResult:
    """Rank by win rate: wins / (wins + losses)."""
    wins: dict[str, int] = defaultdict(int)
    total: dict[str, int] = defaultdict(int)
    seen: set[str] = set()
    for winner, loser, _ in preferences:
        wins[winner] += 1
        total[winner] += 1
        total[loser] += 1
        seen.add(winner)
        seen.add(loser)

    ids = list(seen)
    if all_doc_ids:
        ids = list(set(ids) | set(all_doc_ids))

    scores = {d: wins.get(d, 0) / max(total.get(d, 0), 1) for d in ids}
    ranked = sorted(scores, key=lambda d: (-scores[d], d))

    return RerankerResult(
        query_id="",
        ranked_doc_ids=ranked,
        scores=scores,
        metadata={"method": "win_rate"},
    )


def bradley_terry_ranking(
    preferences: list[tuple[str, str, float]],
    all_doc_ids: list[str] | None = None,
    max_iter: int = 100,
    tol: float = 1e-6,
) -> RerankerResult:
    """Rank by Bradley-Terry model MLE.

    Fits strength parameters p_i such that P(i beats j) = p_i / (p_i + p_j).
    Uses iterative scaling (MM algorithm) for the MLE.

    Parameters
    ----------
    preferences:
        List of (winner_id, loser_id, weight) tuples.
    max_iter:
        Maximum iterations for the MM algorithm.
    tol:
        Convergence tolerance.
    """
    seen: set[str] = set()
    win_counts: dict[tuple[str, str], float] = defaultdict(float)
    for winner, loser, weight in preferences:
        win_counts[(winner, loser)] += weight
        seen.add(winner)
        seen.add(loser)

    ids = sorted(seen)
    if all_doc_ids:
        ids = sorted(set(ids) | set(all_doc_ids))

    n = len(ids)
    if n == 0:
        return RerankerResult(query_id="", ranked_doc_ids=[], scores={})

    idx = {d: i for i, d in enumerate(ids)}
    p = np.ones(n) / n

    for iteration in range(max_iter):
        p_new = np.zeros(n)
        denom = np.zeros(n)

        for (winner, loser), count in win_counts.items():
            wi = idx.get(winner)
            li = idx.get(loser)
            if wi is None or li is None:
                continue
            p_new[wi] += count
            total_comparisons = win_counts.get((winner, loser), 0) + win_counts.get(
                (loser, winner), 0
            )
            if total_comparisons > 0 and (p[wi] + p[li]) > 0:
                contrib = total_comparisons / (p[wi] + p[li])
                denom[wi] += contrib
                denom[li] += contrib

        safe_denom = np.where(denom > 0, denom, 1.0)
        p_new = p_new / safe_denom
        p_sum = p_new.sum()
        if p_sum > 0:
            p_new = p_new / p_sum
        else:
            p_new = np.ones(n) / n

        if np.max(np.abs(p_new - p)) < tol:
            p = p_new
            break
        p = p_new

    scores = {ids[i]: float(p[i]) for i in range(n)}
    ranked = sorted(scores, key=lambda d: (-scores[d], d))

    return RerankerResult(
        query_id="",
        ranked_doc_ids=ranked,
        scores=scores,
        metadata={"method": "bradley_terry", "iterations": iteration + 1},
    )


def markov_chain_ranking(
    preferences: list[tuple[str, str, float]],
    all_doc_ids: list[str] | None = None,
    damping: float = 0.85,
    max_iter: int = 100,
    tol: float = 1e-6,
) -> RerankerResult:
    """Rank by stationary distribution of a Markov chain over pairwise outcomes.

    The transition matrix T[i][j] is the probability of transitioning from
    state i to state j, proportional to the number of times j beat i.
    This is equivalent to a PageRank-style computation on the preference graph.
    """
    seen: set[str] = set()
    wins_over: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for winner, loser, weight in preferences:
        wins_over[winner][loser] += weight
        seen.add(winner)
        seen.add(loser)

    ids = sorted(seen)
    if all_doc_ids:
        ids = sorted(set(ids) | set(all_doc_ids))

    n = len(ids)
    if n == 0:
        return RerankerResult(query_id="", ranked_doc_ids=[], scores={})

    graph = nx.DiGraph()
    graph.add_nodes_from(ids)
    for winner, losers in wins_over.items():
        for loser, weight in losers.items():
            graph.add_edge(winner, loser, weight=weight)

    try:
        pr = nx.pagerank(
            graph.reverse(copy=True),
            alpha=damping,
            weight="weight",
            max_iter=max_iter,
            tol=tol,
        )
    except nx.PowerIterationFailedConvergence:
        pr = {d: 1.0 / n for d in ids}

    ranked = sorted(pr, key=lambda d: (-pr[d], d))

    return RerankerResult(
        query_id="",
        ranked_doc_ids=ranked,
        scores={d: float(pr[d]) for d in ids},
        metadata={"method": "markov_chain", "damping": damping},
    )


def tournament_sort_ranking(
    preferences: list[tuple[str, str, float]],
    all_doc_ids: list[str] | None = None,
    seed: int = 42,
) -> RerankerResult:
    """Rank by tournament-style sorting using pairwise outcomes as a comparator.

    Uses merge-sort with O(n log n) comparisons. When a comparison is not
    available in the preference data, falls back to lexicographic doc_id order.
    """
    import random as _random

    seen: set[str] = set()
    result_map: dict[tuple[str, str], str] = {}
    for winner, loser, weight in preferences:
        seen.add(winner)
        seen.add(loser)
        key = tuple(sorted([winner, loser]))
        existing = result_map.get(key)
        if existing is None:
            result_map[key] = winner
        elif existing != winner:
            result_map[key] = winner

    ids = sorted(seen)
    if all_doc_ids:
        ids = sorted(set(ids) | set(all_doc_ids))

    rng = _random.Random(seed)
    rng.shuffle(ids)

    def _compare(a: str, b: str) -> int:
        key = tuple(sorted([a, b]))
        winner = result_map.get(key)
        if winner == a:
            return -1
        if winner == b:
            return 1
        return -1 if a < b else (1 if a > b else 0)

    import functools

    ranked = sorted(ids, key=functools.cmp_to_key(_compare))

    n = len(ranked)
    scores = {doc_id: float(n - rank) for rank, doc_id in enumerate(ranked)}

    return RerankerResult(
        query_id="",
        ranked_doc_ids=ranked,
        scores=scores,
        metadata={"method": "tournament_sort"},
    )


AGGREGATION_METHODS = {
    "copeland": copeland_ranking,
    "win_rate": win_rate_ranking,
    "bradley_terry": bradley_terry_ranking,
    "markov_chain": markov_chain_ranking,
    "tournament_sort": tournament_sort_ranking,
}


def aggregate_preferences(
    method: str,
    preferences: list[tuple[str, str, float]],
    all_doc_ids: list[str] | None = None,
    **kwargs,
) -> RerankerResult:
    """Run a named aggregation method over pairwise preferences.

    Parameters
    ----------
    method:
        One of: copeland, win_rate, bradley_terry, markov_chain, tournament_sort
    preferences:
        List of (winner_id, loser_id, weight) tuples.
    all_doc_ids:
        Complete set of document IDs.
    """
    if method not in AGGREGATION_METHODS:
        raise ValueError(
            f"Unknown aggregation method {method!r}. "
            f"Available: {list(AGGREGATION_METHODS.keys())}"
        )
    func = AGGREGATION_METHODS[method]
    return func(preferences, all_doc_ids=all_doc_ids, **kwargs)
