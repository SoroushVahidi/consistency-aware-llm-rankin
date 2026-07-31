"""Evaluation metrics for the offline active-acquisition pilot (Phase 5).

Reuses :func:`consistency_ranker.evaluation.ndcg_at_k` and
:func:`consistency_ranker.evaluation.kendall_tau` rather than
reimplementing them. Qrels are used *only* here (post-hoc evaluation),
never inside ``scoring.py`` / ``strategies.py`` acquisition decisions.
"""

from __future__ import annotations

from dataclasses import dataclass

from consistency_ranker.evaluation import kendall_tau, ndcg_at_k


def topk_overlap(ranking: list[str], reference_ranking: list[str], k: int) -> float:
    """Jaccard overlap of the top-k sets of *ranking* and *reference_ranking*."""
    a, b = set(ranking[:k]), set(reference_ranking[:k])
    union = a | b
    return (len(a & b) / len(union)) if union else 1.0


@dataclass(frozen=True)
class BudgetRow:
    budget: int
    budget_frac: float
    ndcg: float
    topk_overlap_vs_exhaustive: float
    kendall_tau_vs_exhaustive: float


def evaluate_ranking(
    ranking: list[str],
    relevance: dict[str, int],
    exhaustive_ranking: list[str],
    *,
    k: int,
) -> tuple[float, float, float]:
    """Return (nDCG@k, top-k overlap vs exhaustive, Kendall tau vs exhaustive)."""
    ndcg = ndcg_at_k(ranking, relevance, k=k)
    overlap = topk_overlap(ranking, exhaustive_ranking, k)
    tau = kendall_tau(ranking, exhaustive_ranking)
    return ndcg, overlap, tau


def auc_over_budget(budget_fracs: list[float], ndcgs: list[float]) -> float:
    """Trapezoidal area under the nDCG-vs-normalized-budget curve, in [0, 1]
    x-range (budget_frac must already be sorted ascending and span [0, 1])."""
    if len(budget_fracs) < 2:
        return float(ndcgs[0]) if ndcgs else 0.0
    area = 0.0
    for a in range(len(budget_fracs) - 1):
        dx = budget_fracs[a + 1] - budget_fracs[a]
        area += dx * (ndcgs[a] + ndcgs[a + 1]) / 2.0
    span = budget_fracs[-1] - budget_fracs[0]
    return float(area / span) if span > 0 else float(ndcgs[0])


def budget_to_fraction_of_improvement(
    budgets: list[int],
    ndcgs: list[float],
    ndcg_initial: float,
    ndcg_exhaustive: float,
    *,
    fraction: float,
) -> int | None:
    """Smallest acquired-judgment budget at which *fraction* of the
    (initial -> exhaustive) nDCG improvement has been recovered.

    Returns ``None`` when the query does not improve from initial to
    exhaustive (``ndcg_exhaustive <= ndcg_initial``) — the ratio is
    undefined/misleading in that case and must not be reported as a number
    (Phase 5 requirement). Also returns ``None`` if the target is never
    reached within the swept budgets.
    """
    total_improvement = ndcg_exhaustive - ndcg_initial
    if total_improvement <= 1e-12:
        return None
    target = ndcg_initial + fraction * total_improvement
    for b, n in zip(budgets, ndcgs):
        if n >= target:
            return b
    return None


def topk_stabilization_budget(
    budgets: list[int],
    rankings: list[list[str]],
    k: int,
) -> int | None:
    """First budget at which the top-k *set* equals the top-k set at every
    later recorded budget in this sweep (i.e. it never changes again within
    what was observed). ``None`` if it keeps changing through the last
    checkpoint."""
    final_topk = set(rankings[-1][:k])
    for idx in range(len(budgets)):
        if all(set(rankings[j][:k]) == final_topk for j in range(idx, len(rankings))):
            return budgets[idx]
    return None


__all__ = [
    "topk_overlap",
    "BudgetRow",
    "evaluate_ranking",
    "auc_over_budget",
    "budget_to_fraction_of_improvement",
    "topk_stabilization_budget",
]
