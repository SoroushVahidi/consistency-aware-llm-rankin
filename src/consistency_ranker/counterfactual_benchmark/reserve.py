"""Adaptive reserve (follow-up) request scheduling.

Exactly one reserve pass: for each (provider, pair) cell that received an
initial judgment, decide whether a swapped-orientation confirmation call is
warranted, using only frozen trigger conditions -- never qrels. When demand
exceeds the reserve cap, higher-priority triggers are scheduled first and
lower-priority ones are recorded as explicitly skipped, never silently
dropped.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from consistency_ranker.counterfactual_benchmark.models import (
    NormalizedJudgment,
    PairRecord,
    ReserveDecision,
)

# Self-reported confidence is uncalibrated; this is a deliberately inclusive
# midpoint threshold for flagging borderline calls, not a calibrated cutoff.
LOW_CONFIDENCE_THRESHOLD = 0.5

PRIORITY_ORDER: dict[str, int] = {
    "structured_output_retry": 1,
    "cutoff_critical_inconsistency": 2,
    "cross_provider_disagreement_near_cutoff": 3,
    "tie_or_abstain_near_cutoff": 4,
    "low_confidence_near_cutoff": 5,
    "other_position_inconsistency": 6,
}

# The exact rank-k vs rank-(k+1) pair: getting *this specific* pair wrong
# directly flips top-k membership, so it is always confirmed regardless of
# its outcome. Other archetypes below are "near" the cutoff in a softer
# sense (close prior scores, or spanning the pool) and are triaged by the
# severity of their outcome instead of being unconditionally confirmed.
_EXACT_CUTOFF_REASON = "cutoff_boundary"
_SOFT_NEAR_CUTOFF_REASONS = {"near_tie_prior", "top_versus_lower"}


def _swapped(order: str) -> str:
    return "ba" if order == "ab" else "ab"


def derive_reserve_decisions(
    *,
    initial_judgments: list[NormalizedJudgment],
    pairs_by_query: dict[tuple[str, str], list[PairRecord]],
    max_reserve: int,
) -> list[ReserveDecision]:
    pair_lookup: dict[tuple[str, str, str], PairRecord] = {}
    for query_key, records in pairs_by_query.items():
        for rec in records:
            pair_lookup[(query_key[0], query_key[1], rec.pair_id)] = rec

    # Group successful, preference-bearing judgments by pair to detect
    # cross-provider disagreement.
    by_pair: dict[tuple[str, str, str], list[NormalizedJudgment]] = defaultdict(list)
    for j in initial_judgments:
        by_pair[(j.dataset, j.query_id, j.pair_id)].append(j)

    disagreement_pairs: set[tuple[str, str, str]] = set()
    for pair_key, judgs in by_pair.items():
        winners = {
            j.normalized_document_preference
            for j in judgs
            if j.success and j.normalized_document_preference in {j.doc_a_id, j.doc_b_id}
        }
        if len(winners) > 1:
            disagreement_pairs.add(pair_key)

    candidates: list[ReserveDecision] = []
    for j in initial_judgments:
        pair_id = j.pair_id
        pair = pair_lookup.get((j.dataset, j.query_id, pair_id))
        reason = pair.reason if pair else None
        is_exact_cutoff = reason == _EXACT_CUTOFF_REASON
        is_soft_near_cutoff = reason in _SOFT_NEAR_CUTOFF_REASONS
        pair_key = (j.dataset, j.query_id, pair_id)
        has_disagreement = pair_key in disagreement_pairs
        is_tie_or_abstain = j.preference in {"TIE", "ABSTAIN"}
        is_low_confidence = j.confidence is not None and j.confidence < LOW_CONFIDENCE_THRESHOLD

        trigger: str | None = None
        if (not j.success) or j.parse_failed:
            trigger = "structured_output_retry"
        elif is_exact_cutoff:
            # Always confirm the exact top-k boundary pair, regardless of
            # its specific outcome: any error here changes what is in top-k.
            trigger = "cutoff_critical_inconsistency"
        elif is_soft_near_cutoff and has_disagreement:
            trigger = "cross_provider_disagreement_near_cutoff"
        elif is_soft_near_cutoff and is_tie_or_abstain:
            trigger = "tie_or_abstain_near_cutoff"
        elif is_soft_near_cutoff and is_low_confidence:
            trigger = "low_confidence_near_cutoff"
        elif has_disagreement or is_tie_or_abstain or is_low_confidence:
            trigger = "other_position_inconsistency"

        if trigger is None:
            continue

        candidates.append(
            ReserveDecision(
                request_hash=j.request_hash,
                dataset=j.dataset,
                query_id=j.query_id,
                provider=j.provider,
                pair_id=pair_id,
                trigger=trigger,
                priority=PRIORITY_ORDER[trigger],
                scheduled=False,
            )
        )

    # Deterministic order: priority ascending, then stable by request_hash.
    candidates.sort(key=lambda c: (c.priority, c.request_hash))
    for i, c in enumerate(candidates):
        if i < max_reserve:
            c.scheduled = True
        else:
            c.scheduled = False
            c.skip_reason = "reserve_exhausted"
    return candidates


def build_reserve_request(
    *,
    decision: ReserveDecision,
    original_pair: PairRecord,
    config: dict[str, Any],
    pool_hash: str,
    text_hash_a: str,
    text_hash_b: str,
    model_id: str,
) -> tuple[str, str]:
    """Return (request_hash, presentation_order) for a reserve repeat.

    ``structured_output_retry`` resends the *same* orientation (it is a retry
    of the failed call, not a position-consistency probe); every other
    trigger swaps the orientation to test AB/BA position consistency.
    """
    from consistency_ranker.counterfactual_benchmark.request_plan import (
        compute_request_hash,
    )

    if decision.trigger == "structured_output_retry":
        swapped_order = original_pair.initial_presentation_order
    else:
        swapped_order = _swapped(original_pair.initial_presentation_order)
    request_hash = compute_request_hash(
        benchmark_version=str(config["benchmark_version"]),
        dataset=decision.dataset,
        query_id=decision.query_id,
        pool_hash=pool_hash,
        doc_a_id=original_pair.doc_a_id,
        doc_b_id=original_pair.doc_b_id,
        text_hash_a=text_hash_a,
        text_hash_b=text_hash_b,
        presentation_order=swapped_order,
        provider=decision.provider,
        model_id=model_id,
        prompt_sha256=str(config["prompt_sha256"]),
        schema_sha256=str(config["judgment_schema_sha256"]),
        temperature=float(config["generation_defaults"]["temperature"]),
        seed=int(config["generation_defaults"]["seed"]),
        attempt_type="reserve",
    )
    return request_hash, swapped_order
