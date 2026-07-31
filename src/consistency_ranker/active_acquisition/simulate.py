"""Sequential offline acquisition simulation for one query.

At each step the chosen algorithm picks one currently-unrevealed pair; its
cached judgment is revealed from the offline oracle (no live call, no
qrels); the Copeland tally is updated; and at each requested budget
checkpoint the current extraction ranking is recorded together with the
wall-clock time spent making that one acquisition decision.

Two conditions are *not* separately simulated because they are exact,
not approximate, consequences of using an order-invariant extraction rule
(Copeland aggregation depends only on the *set* of revealed edges, not the
order they were revealed in):

* ``initial`` (budget = 0) is identical for every algorithm: the BM25-only
  ranking, since no edges are revealed yet.
* ``exhaustive`` (budget = 100%) is identical for every algorithm: the
  full-oracle Copeland ranking, since all C(n, 2) edges end up revealed
  regardless of acquisition order.

Both are computed once per query in :func:`reference_rankings` instead of
being re-derived once per algorithm.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from consistency_ranker.active_acquisition.oracle import QueryOracle
from consistency_ranker.active_acquisition.scoring import (
    StepContext,
    normalize_bm25,
    rank_from_copeland,
)
from consistency_ranker.active_acquisition.strategies import pick_next_pair


@dataclass(frozen=True)
class Checkpoint:
    budget: int
    ranking: list[str]
    decision_runtime_s: float  # runtime of the single decision made at this step


def reference_rankings(oracle_entry: QueryOracle, seed: int = 0) -> tuple[list[str], list[str]]:
    """Return (initial_ranking, exhaustive_ranking) — both exact, not simulated."""
    candidates = oracle_entry.candidates
    bm25_norm = normalize_bm25(candidates, oracle_entry.bm25_scores)
    zero_copeland = {d: 0.0 for d in candidates}
    initial_ranking = rank_from_copeland(candidates, zero_copeland, bm25_norm)

    full_copeland = {d: 0.0 for d in candidates}
    for pair, winner in oracle_entry.oracle.items():
        loser = next(d for d in pair if d != winner)
        full_copeland[winner] += 1.0
        full_copeland[loser] -= 1.0
    exhaustive_ranking = rank_from_copeland(candidates, full_copeland, bm25_norm)
    return initial_ranking, exhaustive_ranking


def _static_order(candidates: tuple[str, ...], bm25: dict[str, float]) -> list[frozenset]:
    bm25_norm = normalize_bm25(candidates, bm25)
    initial_ranking = rank_from_copeland(candidates, {d: 0.0 for d in candidates}, bm25_norm)
    rank_pos = {d: i for i, d in enumerate(initial_ranking)}
    all_pairs = [
        frozenset((candidates[a], candidates[b]))
        for a in range(len(candidates))
        for b in range(a + 1, len(candidates))
    ]

    def sort_key(pair: frozenset):
        i, j = sorted(pair)
        dist = abs(rank_pos[i] - rank_pos[j])
        return (dist, min(rank_pos[i], rank_pos[j]), i, j)

    return sorted(all_pairs, key=sort_key)


def simulate_trajectory(
    oracle_entry: QueryOracle,
    algorithm: str,
    budgets: list[int],
    k: int,
    seed: int,
) -> list[Checkpoint]:
    """Run one algorithm's full sequential acquisition trajectory for one query.

    Returns one :class:`Checkpoint` per requested budget in ``budgets``
    (each strictly between 0 and the exhaustive budget; use
    :func:`reference_rankings` for the 0% / 100% endpoints).
    """
    candidates = oracle_entry.candidates
    bm25_norm = normalize_bm25(candidates, oracle_entry.bm25_scores)
    all_pairs = [
        frozenset((candidates[a], candidates[b]))
        for a in range(len(candidates))
        for b in range(a + 1, len(candidates))
    ]
    max_budget = len(all_pairs)
    checkpoint_set = {b for b in budgets if 0 < b < max_budget}

    static_order = (
        _static_order(candidates, oracle_entry.bm25_scores)
        if algorithm == "static_adjacent"
        else None
    )

    rng = __import__("random").Random(seed)
    remaining = list(all_pairs)
    revealed: list[tuple[str, str]] = []
    copeland = {d: 0.0 for d in candidates}

    checkpoints: list[Checkpoint] = []
    step = 0
    while remaining and len(checkpoints) < len(checkpoint_set):
        t0 = time.perf_counter()
        ctx = StepContext.build(candidates, revealed, copeland, bm25_norm, k)
        pair = pick_next_pair(algorithm, ctx, remaining, static_order, rng)
        i, j = sorted(pair)
        winner, loser = oracle_entry.reveal(i, j)
        dt = time.perf_counter() - t0

        copeland[winner] += 1.0
        copeland[loser] -= 1.0
        revealed.append((winner, loser))
        remaining.remove(pair)
        step += 1

        if step in checkpoint_set:
            ranking = rank_from_copeland(candidates, copeland, bm25_norm)
            checkpoints.append(Checkpoint(budget=step, ranking=ranking, decision_runtime_s=dt))

    return checkpoints


__all__ = ["Checkpoint", "reference_rankings", "simulate_trajectory"]
