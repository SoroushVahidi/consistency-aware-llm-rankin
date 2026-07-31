"""Local contradiction resolution before global cycle repair."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from consistency_ranker.reliability_repair.evidence_aggregation import PairAggregate

LocalPolicy = Literal[
    "majority",
    "signed_margin",
    "abstain_small_margin",
    "diagnostic_both",
    "prior_assisted",
]


@dataclass
class LocalResolution:
    pair_id: str
    policy: str
    had_both_directions: bool
    resolution: Literal["one_edge", "incomparable", "diagnostic_two_cycle"]
    direction: int
    detail: str


def resolve_local_contradiction(
    agg: PairAggregate,
    *,
    policy: LocalPolicy = "signed_margin",
    small_margin: float = 0.1,
    prior_scores: dict[str, float] | None = None,
) -> LocalResolution:
    """Resolve unordered-pair conflicts into at most one production direction.

    ``had_both_directions`` is True when both z=+1 and z=-1 appear in evidence.
    """
    both = agg.n_plus > 0 and agg.n_minus > 0
    if not both:
        return LocalResolution(
            pair_id=agg.canonical_pair_id,
            policy=policy,
            had_both_directions=False,
            resolution="one_edge" if agg.d != 0 else "incomparable",
            direction=int(agg.d),
            detail="no_local_conflict",
        )

    if policy == "diagnostic_both":
        return LocalResolution(
            pair_id=agg.canonical_pair_id,
            policy=policy,
            had_both_directions=True,
            resolution="diagnostic_two_cycle",
            direction=int(agg.d),
            detail="retain_both_diagnostic",
        )

    if policy == "majority":
        if agg.n_plus == agg.n_minus:
            return LocalResolution(
                agg.canonical_pair_id, policy, True, "incomparable", 0, "majority_tie"
            )
        d = 1 if agg.n_plus > agg.n_minus else -1
        return LocalResolution(
            agg.canonical_pair_id, policy, True, "one_edge", d, "majority"
        )

    if policy == "signed_margin":
        if abs(agg.m) < 1e-15:
            return LocalResolution(
                agg.canonical_pair_id, policy, True, "incomparable", 0, "zero_margin"
            )
        return LocalResolution(
            agg.canonical_pair_id,
            policy,
            True,
            "one_edge",
            1 if agg.m > 0 else -1,
            "signed_margin",
        )

    if policy == "abstain_small_margin":
        if abs(agg.m) < small_margin:
            return LocalResolution(
                agg.canonical_pair_id,
                policy,
                True,
                "incomparable",
                0,
                "small_margin_abstain",
            )
        return LocalResolution(
            agg.canonical_pair_id,
            policy,
            True,
            "one_edge",
            1 if agg.m > 0 else -1,
            "margin_ok",
        )

    if policy == "prior_assisted":
        if abs(agg.m) >= small_margin:
            return LocalResolution(
                agg.canonical_pair_id,
                policy,
                True,
                "one_edge",
                1 if agg.m > 0 else -1,
                "margin_decides",
            )
        prior_scores = prior_scores or {}
        si = float(prior_scores.get(agg.doc_i, 0.0))
        sj = float(prior_scores.get(agg.doc_j, 0.0))
        if abs(si - sj) < 1e-15:
            return LocalResolution(
                agg.canonical_pair_id, policy, True, "incomparable", 0, "prior_tie"
            )
        d = 1 if si > sj else -1
        return LocalResolution(
            agg.canonical_pair_id, policy, True, "one_edge", d, "prior_tiebreak"
        )

    raise ValueError(f"Unknown local policy {policy!r}")
