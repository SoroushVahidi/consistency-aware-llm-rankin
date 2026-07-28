"""Qrel-free stopping rules for the regularized partial-information rank
aggregator (`regularized_aggregation.py`).

The prior regularized-aggregation pilot established that a coverage-adaptive
prior-regularized Bradley-Terry aggregator can safely combine a BM25 prior
with sparse pairwise judgments, but always acquired a *fixed* budget. This
module adds one interpretable, qrel-free stopping rule that decides, after
each newly revealed pairwise judgment, whether the current top-k ranking is
stable enough that no further judgment is likely to matter.

Primary rule: counterfactual worst-case top-k stability. At each step,
consider a deterministic subset of still-unrevealed pairs (those touching a
window of documents near the current rank-k cutoff -- pairs far from the
cutoff essentially never flip top-k membership, so evaluating them exactly
would spend most of the budget on pairs that cannot matter). For each such
pair, simulate both possible outcomes, refit the regularized aggregator
under each, and measure how far the counterfactual top-k drifts from the
*current* top-k. Stop once the worst case over all considered pairs and
outcomes has been below a frozen threshold ``tau`` for ``m`` consecutive
steps (patience, to avoid stopping on a transient lull).

Leakage discipline: every function here takes only (a) the fixed candidate
pool, (b) the revealed-so-far outcomes, (c) the qrels-free BM25 prior, (d)
the frozen regularization schedule, and (e) the *hypothetical* outcomes of
still-*unrevealed* pairs it is itself simulating (never the oracle's cached
actual answer for them, and never qrels). See
``tests/test_stopping.py`` for the enforced leakage tests.

Computational note: the counterfactual refits used *only* to make the
stopping decision are warm-started from the current (already-converged)
utilities with a much smaller fixed iteration count than the frozen
aggregator's own 3000-iteration fit (see ``_WARM_START_ITERATIONS`` below).
This is a disclosed approximation for computational tractability -- it never
changes what ranking or nDCG is *reported* at the moment the rule decides to
stop, which always uses the exact, unmodified, already-frozen
``regularized_bt_ranking`` / ``fit_bt_utilities`` from
``regularized_aggregation.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from consistency_ranker.active_acquisition.regularized_aggregation import (
    _ADAM_BETA1,
    _ADAM_BETA2,
    _ADAM_EPS,
    _MIN_LAMBDA_FOR_NUMERICAL_STABILITY,
    _bt_negative_log_likelihood_and_grad,
    _validate_revealed,
    rank_from_utilities,
)
from consistency_ranker.evaluation import kendall_tau

ScheduleFn = Callable[[float], float]

# Fixed, deterministic (no adaptive stopping) warm-start refit used only for
# the stopping rule's internal what-if simulations -- much cheaper than the
# frozen aggregator's 3000-iteration cold-start fit because it starts from
# the already-converged current utilities and only needs to absorb one new
# observation. Never used for anything that is reported as a ranking/nDCG
# result; see module docstring.
_WARM_START_ITERATIONS = 150
_WARM_START_LR = 0.05

# Deterministic candidate-pair subset (Phase 2, step 2): only unrevealed
# pairs with at least one endpoint within this many ranks of the current
# cutoff k are considered. Frozen, disclosed, not tuned per query.
_BOUNDARY_WINDOW = 3


def _warm_fit_bt_utilities(
    candidates: tuple[str, ...],
    revealed: list[tuple[str, str]],
    prior: dict[str, float],
    lam: float,
    warm_start: dict[str, float],
) -> dict[str, float]:
    """Like ``regularized_aggregation.fit_bt_utilities``, but starts Adam
    from ``warm_start`` (the current utilities) instead of the prior, and
    runs a much smaller fixed iteration count -- see module docstring."""
    _validate_revealed(candidates, revealed)
    if not revealed:
        return dict(prior)

    lam_stable = max(lam, _MIN_LAMBDA_FOR_NUMERICAL_STABILITY)
    doc_index = {d: idx for idx, d in enumerate(candidates)}
    prior_vec = np.array([prior.get(d, 0.0) for d in candidates], dtype=float)
    u = np.array([warm_start.get(d, 0.0) for d in candidates], dtype=float)
    m = np.zeros_like(u)
    v = np.zeros_like(u)
    for t in range(1, _WARM_START_ITERATIONS + 1):
        _, grad = _bt_negative_log_likelihood_and_grad(
            u, doc_index, revealed, prior_vec, lam_stable
        )
        m = _ADAM_BETA1 * m + (1.0 - _ADAM_BETA1) * grad
        v = _ADAM_BETA2 * v + (1.0 - _ADAM_BETA2) * (grad * grad)
        m_hat = m / (1.0 - _ADAM_BETA1**t)
        v_hat = v / (1.0 - _ADAM_BETA2**t)
        u = u - _WARM_START_LR * m_hat / (np.sqrt(v_hat) + _ADAM_EPS)
    return {d: float(u[idx]) for d, idx in doc_index.items()}


def _restrict_preserving_order(ranking: list[str], keep: set[str]) -> list[str]:
    return [d for d in ranking if d in keep]


def topk_distance(
    current_ranking: list[str], counterfactual_ranking: list[str], k: int
) -> tuple[float, dict[str, float]]:
    """Distance between a current ranking and a counterfactual one, combining
    three interpretable components (Phase 2, step 5):

    - ``membership``: Jaccard distance between the two top-k sets.
    - ``ordering``: (1 - Kendall tau) / 2, restricted to the union of the two
      top-k sets (i.e. specifically top-k re-ordering, not whole-list order).
    - ``displacement``: max normalized rank displacement among documents
      currently within ``_BOUNDARY_WINDOW`` ranks of the cutoff.

    The scalar distance returned is the max of the three components -- a
    conservative, interpretable "worst of the three lenses" choice, matching
    this rule's overall worst-case framing.
    """
    n = len(current_ranking)
    cur_topk = set(current_ranking[:k])
    cf_topk = set(counterfactual_ranking[:k])
    union = cur_topk | cf_topk
    membership = 1.0 - (len(cur_topk & cf_topk) / len(union)) if union else 0.0

    cur_restricted = _restrict_preserving_order(current_ranking, union)
    cf_restricted = _restrict_preserving_order(counterfactual_ranking, union)
    tau = kendall_tau(cur_restricted, cf_restricted) if len(union) >= 2 else 1.0
    ordering = (1.0 - tau) / 2.0

    cur_pos = {d: i for i, d in enumerate(current_ranking)}
    cf_pos = {d: i for i, d in enumerate(counterfactual_ranking)}
    window_docs = current_ranking[max(0, k - _BOUNDARY_WINDOW) : min(n, k + _BOUNDARY_WINDOW)]
    denom = max(n - 1, 1)
    displacement = (
        max(abs(cur_pos[d] - cf_pos[d]) for d in window_docs) / denom if window_docs else 0.0
    )

    scalar = max(membership, ordering, displacement)
    return scalar, {"membership": membership, "ordering": ordering, "displacement": displacement}


def counterfactual_candidate_pairs(
    candidates: tuple[str, ...],
    remaining_pairs: list[frozenset],
    current_ranking: list[str],
    k: int,
    window: int = _BOUNDARY_WINDOW,
) -> list[tuple[str, str]]:
    """Deterministic subset (Phase 2, step 2): unrevealed pairs with at least
    one endpoint within ``window`` ranks of the current cutoff k. Sorted for
    a fully deterministic evaluation order (tie-breaking, reproducibility)."""
    n = len(candidates)
    window_docs = set(current_ranking[max(0, k - window) : min(n, k + window)])
    kept = [tuple(sorted(p)) for p in remaining_pairs if any(d in window_docs for d in p)]
    return sorted(kept)


@dataclass(frozen=True)
class WorstCaseResult:
    scalar: float
    membership: float
    ordering: float
    displacement: float
    triggering_pair: tuple[str, str] | None
    triggering_outcome: str | None
    n_pairs_considered: int


def _worst_case_over_pairs(
    candidates: tuple[str, ...],
    revealed: list[tuple[str, str]],
    bm25_norm: dict[str, float],
    lam_after: float,
    current_utilities: dict[str, float],
    current_ranking: list[str],
    k: int,
    pair_list: list[tuple[str, str]],
) -> WorstCaseResult:
    """Max, over the *given* ``pair_list`` and both hypothetical outcomes of
    each pair, of :func:`topk_distance` between ``current_ranking`` and the
    counterfactual ranking. Does no windowing/filtering itself -- callers
    decide which pairs to pass in. Iterates in the exact order of
    ``pair_list`` with a fixed tie-break (first-seen wins ties), so the
    result is deterministic given a deterministic ``pair_list``.
    """
    best = WorstCaseResult(0.0, 0.0, 0.0, 0.0, None, None, len(pair_list))
    for i, j in pair_list:
        for winner, loser in ((i, j), (j, i)):
            hypothetical = revealed + [(winner, loser)]
            cf_utilities = _warm_fit_bt_utilities(
                candidates, hypothetical, bm25_norm, lam_after, current_utilities
            )
            cf_ranking = rank_from_utilities(candidates, cf_utilities, bm25_norm)
            scalar, components = topk_distance(current_ranking, cf_ranking, k)
            if scalar > best.scalar:
                best = WorstCaseResult(
                    scalar,
                    components["membership"],
                    components["ordering"],
                    components["displacement"],
                    (i, j),
                    winner,
                    len(pair_list),
                )
    return best


def worst_case_topk_change(
    candidates: tuple[str, ...],
    revealed: list[tuple[str, str]],
    bm25_norm: dict[str, float],
    n_total_pairs: int,
    schedule: ScheduleFn,
    remaining_pairs: list[frozenset],
    k: int,
    current_utilities: dict[str, float],
) -> WorstCaseResult:
    """The primary stopping statistic (Phase 2): worst-case top-k distance
    over a deterministic subset of still-unrevealed pairs and both
    hypothetical outcomes of each. Uses only the fixed candidate pool, the
    revealed-so-far outcomes, the qrels-free BM25 prior, the frozen
    schedule, and the current (already-fitted, qrels-free) utilities --
    never qrels, never the oracle's actual cached answer for an unrevealed
    pair, never the exhaustive ranking.
    """
    current_ranking = rank_from_utilities(candidates, current_utilities, bm25_norm)
    if not remaining_pairs:
        return WorstCaseResult(0.0, 0.0, 0.0, 0.0, None, None, 0)
    candidate_pairs = counterfactual_candidate_pairs(
        candidates, remaining_pairs, current_ranking, k
    )
    coverage_after = (len(revealed) + 1) / n_total_pairs if n_total_pairs > 0 else 0.0
    lam_after = schedule(coverage_after)
    return _worst_case_over_pairs(
        candidates, revealed, bm25_norm, lam_after, current_utilities, current_ranking, k,
        candidate_pairs,
    )


def counterfactual_rule_is_stable(worst_case_scalar: float, tau: float) -> bool:
    return worst_case_scalar <= tau


def simple_rule_is_stable(ranking_history: list[list[str]], k: int) -> bool:
    """True iff the top-k set at the current step equals the top-k set at
    the immediately preceding step (i.e. no membership change this step)."""
    if len(ranking_history) < 2:
        return False
    return set(ranking_history[-1][:k]) == set(ranking_history[-2][:k])


def apply_patience(prev_consecutive_stable: int, stable_now: bool) -> int:
    return prev_consecutive_stable + 1 if stable_now else 0


def has_stopped(consecutive_stable: int, patience_m: int) -> bool:
    return consecutive_stable >= patience_m


def apply_counterfactual_rule(history: list[dict], tau: float, patience_m: int) -> dict:
    """Scan a precomputed per-step history (as produced by
    ``scripts/run_stopping_rule_pilot.py``'s simulate stage) and return the
    first step at which the counterfactual worst-case rule would have
    stopped, or the last available step if it never does within the
    simulated horizon (``stopped=False``, i.e. "capped")."""
    consecutive = 0
    for row in history:
        stable = counterfactual_rule_is_stable(row["worst_case_scalar"], tau)
        consecutive = apply_patience(consecutive, stable)
        if has_stopped(consecutive, patience_m):
            return dict(stopped=True, stop_step=row["step"], row=row)
    last = history[-1]
    return dict(stopped=False, stop_step=last["step"], row=last)


def apply_simple_rule(history: list[dict], patience_m: int, k: int) -> dict:
    """Same as :func:`apply_counterfactual_rule`, but for the simple
    recent-stability baseline: stable iff the top-k set is unchanged from
    the immediately preceding step."""
    consecutive = 0
    prev_topk: set[str] | None = None
    for row in history:
        cur_topk = set(row["topk"][:k])
        stable = prev_topk is not None and cur_topk == prev_topk
        consecutive = apply_patience(consecutive, stable)
        prev_topk = cur_topk
        if has_stopped(consecutive, patience_m):
            return dict(stopped=True, stop_step=row["step"], row=row)
    last = history[-1]
    return dict(stopped=False, stop_step=last["step"], row=last)


__all__ = [
    "topk_distance",
    "counterfactual_candidate_pairs",
    "WorstCaseResult",
    "worst_case_topk_change",
    "counterfactual_rule_is_stable",
    "simple_rule_is_stable",
    "apply_patience",
    "has_stopped",
    "apply_counterfactual_rule",
    "apply_simple_rule",
]
