"""Deterministic, qrels-blind shared pair selection.

Produces one shared pair set per query (used by every provider, so
cross-provider comparisons are paired and directly interpretable). Uses only
prior ranks, cross-prior disagreement, cutoff proximity, and a deterministic
frozen seed -- never qrels.
"""

from __future__ import annotations

import hashlib
import itertools
import random
from typing import Iterable

from consistency_ranker.counterfactual_benchmark.models import CandidatePoolRecord, PairRecord
from consistency_ranker.multi_provider_eval.cache import canonical_pair_id


def _orientation_for_pair(pair_id: str, seed: int) -> str:
    digest = hashlib.sha256(f"{pair_id}:{seed}".encode("utf-8")).hexdigest()
    return "ab" if int(digest, 16) % 2 == 0 else "ba"


def _rank_order(candidate_ids: Iterable[str], prior: dict[str, float]) -> list[str]:
    return sorted(candidate_ids, key=lambda d: (-prior[d], d))


def select_shared_pairs(
    pool: CandidatePoolRecord,
    *,
    eval_k: int,
    n_pairs: int,
    seed: int,
) -> list[PairRecord]:
    candidate_ids = list(pool.candidate_ids)
    if len(candidate_ids) < 2:
        raise ValueError("need at least 2 candidates to form a pair")

    primary_rank = _rank_order(candidate_ids, pool.prior_scores_primary)
    secondary_rank = _rank_order(candidate_ids, pool.prior_scores_secondary)
    primary_index = {d: i for i, d in enumerate(primary_rank)}
    secondary_index = {d: i for i, d in enumerate(secondary_rank)}

    selected: dict[frozenset[str], str] = {}  # frozenset({a,b}) -> reason

    def add(a: str, b: str, reason: str) -> None:
        key = frozenset({a, b})
        if key not in selected and len(selected) < n_pairs:
            selected[key] = reason

    # 1. Top-ranked pair.
    if len(primary_rank) >= 2:
        add(primary_rank[0], primary_rank[1], "top_ranked")

    # 2. Cutoff-boundary pair (last-in vs first-out of the evaluation cutoff).
    if 0 < eval_k < len(primary_rank):
        add(primary_rank[eval_k - 1], primary_rank[eval_k], "cutoff_boundary")

    # 3. High ranker-disagreement pair: largest rank-order reversal between
    #    the two independent qrels-blind priors.
    best_pair: tuple[str, str] | None = None
    best_disagreement = -1
    for a, b in itertools.combinations(candidate_ids, 2):
        primary_says_a_first = primary_index[a] < primary_index[b]
        secondary_says_a_first = secondary_index[a] < secondary_index[b]
        if primary_says_a_first == secondary_says_a_first:
            continue  # priors agree on order for this pair
        disagreement = abs(primary_index[a] - primary_index[b]) + abs(
            secondary_index[a] - secondary_index[b]
        )
        if disagreement > best_disagreement:
            best_disagreement = disagreement
            best_pair = (a, b)
    if best_pair is not None:
        add(best_pair[0], best_pair[1], "high_ranker_disagreement")

    # 4. Near-tie prior pair: adjacent-in-primary-rank candidates with the
    #    smallest score gap.
    best_tie_pair: tuple[str, str] | None = None
    best_gap = float("inf")
    for i in range(len(primary_rank) - 1):
        a, b = primary_rank[i], primary_rank[i + 1]
        gap = abs(pool.prior_scores_primary[a] - pool.prior_scores_primary[b])
        if gap < best_gap:
            best_gap = gap
            best_tie_pair = (a, b)
    if best_tie_pair is not None:
        add(best_tie_pair[0], best_tie_pair[1], "near_tie_prior")

    # 5. Top-versus-lower candidate pair.
    if len(primary_rank) >= 2:
        add(primary_rank[0], primary_rank[-1], "top_versus_lower")

    # 6. Deterministic coverage pairs: fill remaining slots from a seeded,
    #    reproducible shuffle of all remaining unordered pairs.
    remaining = [
        (a, b)
        for a, b in itertools.combinations(candidate_ids, 2)
        if frozenset({a, b}) not in selected
    ]
    remaining.sort()  # deterministic base order before shuffling
    rng = random.Random(seed)
    rng.shuffle(remaining)
    for a, b in remaining:
        if len(selected) >= n_pairs:
            break
        add(a, b, "deterministic_coverage")

    if len(selected) < n_pairs:
        raise ValueError(
            f"could not select {n_pairs} distinct pairs from a pool of "
            f"{len(candidate_ids)} candidates (max possible = "
            f"{len(candidate_ids) * (len(candidate_ids) - 1) // 2})"
        )

    records: list[PairRecord] = []
    for key, reason in selected.items():
        a, b = sorted(key)
        pair_id = canonical_pair_id(pool.query_id, a, b)
        records.append(
            PairRecord(
                dataset=pool.dataset,
                query_id=pool.query_id,
                doc_a_id=a,
                doc_b_id=b,
                pair_id=pair_id,
                reason=reason,
                initial_presentation_order=_orientation_for_pair(pair_id, seed),
            )
        )
    records.sort(key=lambda r: r.pair_id)
    return records
