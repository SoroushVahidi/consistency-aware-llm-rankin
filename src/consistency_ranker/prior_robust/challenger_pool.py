"""Challenger pool and candidate-window expansion for bad-prior recovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState
    from consistency_ranker.prior_robust.prior_quality import PriorQualityEstimate


@dataclass
class ChallengerPool:
    """Docs outside the active window that can be promoted into consideration."""

    window: int
    active: list[str]
    outsiders: list[str]
    promotions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "window": self.window,
            "active": list(self.active),
            "outsiders": list(self.outsiders),
            "promotions": list(self.promotions),
        }


def init_challenger_pool(
    state: "AcquisitionState",
    *,
    initial_window: int | None = None,
) -> ChallengerPool:
    """Active window = top-w by prior; outsiders are the rest."""
    ranking = state.prior_ranking()
    w = initial_window or max(state.top_k * 2, state.top_k + 2)
    w = min(w, len(ranking))
    return ChallengerPool(
        window=w,
        active=list(ranking[:w]),
        outsiders=list(ranking[w:]),
    )


def expand_window(
    pool: ChallengerPool,
    state: "AcquisitionState",
    quality: "PriorQualityEstimate",
    *,
    delta: int = 2,
    contradiction_threshold: float = 0.35,
    min_evidence_frac: float = 0.25,
    step: int = 0,
) -> ChallengerPool:
    """Expand active window when prior credibility declines or evidence is thin."""
    from consistency_ranker.prior_robust.prior_dependence import topk_evidence_coverage

    cov = topk_evidence_coverage(state)
    hc = quality.high_conf_contradiction_rate
    should = False
    reason = None
    if hc is not None and hc >= contradiction_threshold:
        should, reason = True, "high_conf_contradiction"
    elif cov["fraction_acquired"] < min_evidence_frac and quality.n_acquired > 0:
        should, reason = True, "low_evidence_support"
    elif quality.q_hat < 0.35:
        should, reason = True, "low_prior_quality"

    if not should or not pool.outsiders:
        return pool

    n = min(delta, len(pool.outsiders))
    promoted = pool.outsiders[:n]
    pool.active.extend(promoted)
    pool.outsiders = pool.outsiders[n:]
    pool.window = len(pool.active)
    pool.promotions.append(
        {"step": step, "promoted": promoted, "reason": reason, "window": pool.window}
    )
    return pool


def challenger_pairs(state: "AcquisitionState", pool: ChallengerPool) -> list[str]:
    """Insider (top-k) vs plausible outsider pairs for acquisition."""
    ranking = state.ranking
    topk = ranking[: state.top_k]
    # Plausible outsiders: next window docs + recently promoted.
    candidates = [d for d in pool.active if d not in topk] + list(pool.outsiders[: state.top_k])
    candidates = list(dict.fromkeys(candidates))
    pairs = []
    for insider in topk:
        for out in candidates[: max(2, state.top_k)]:
            pairs.append(state.canonical_pair(insider, out))
    return pairs


def outsider_wins(
    state: "AcquisitionState", outsider: str, *, against_topk: bool = True
) -> int:
    """Count acquired wins of ``outsider`` against current top-k."""
    topk = set(state.ranking[: state.top_k]) if against_topk else set(state.candidate_ids)
    wins = 0
    for agg in state.aggregates.values():
        if agg.d == 0:
            continue
        if outsider not in (agg.doc_i, agg.doc_j):
            continue
        other = agg.doc_j if agg.doc_i == outsider else agg.doc_i
        if other not in topk:
            continue
        winner = agg.doc_i if agg.d == 1 else agg.doc_j
        if winner == outsider:
            wins += 1
    return wins


def promote_strong_outsiders(
    pool: ChallengerPool,
    state: "AcquisitionState",
    *,
    min_wins: int = 2,
    step: int = 0,
) -> ChallengerPool:
    """Promote outsiders that beat multiple top-k documents."""
    still = []
    for d in pool.outsiders:
        if outsider_wins(state, d) >= min_wins:
            pool.active.append(d)
            pool.promotions.append(
                {
                    "step": step,
                    "promoted": [d],
                    "reason": "outsider_wins",
                    "window": len(pool.active),
                }
            )
        else:
            still.append(d)
    pool.outsiders = still
    pool.window = len(pool.active)
    return pool


__all__ = [
    "ChallengerPool",
    "init_challenger_pool",
    "expand_window",
    "challenger_pairs",
    "outsider_wins",
    "promote_strong_outsiders",
]
