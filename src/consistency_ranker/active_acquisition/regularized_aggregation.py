"""Prior-regularized pairwise rank aggregation (the safe-anytime-reranking pivot).

Phase 1 of the offline active-acquisition pilot (see
``reports/offline_active_acquisition_pilot_20260728T142414Z/REPORT.md``)
found that the existing extraction rule (:func:`scoring.rank_from_copeland`)
gives any nonzero revealed-evidence Copeland tally **strict lexicographic
priority** over the BM25 prior: a single revealed edge can move a document's
Copeland score off zero and instantly outrank every document that still has
zero revealed evidence, regardless of how strong that document's BM25 prior
was. This module implements the narrowly-scoped fix this pilot is allowed to
test: a *regularized* Bradley-Terry aggregator whose trust in revealed
pairwise evidence grows smoothly with observation coverage, instead of
switching on with the very first edge.

Mathematical objective
-----------------------
For a fixed candidate pool and a set of revealed (winner, loser) outcomes::

    L(u) = sum_{(w, l) in revealed} -log(sigmoid(u_w - u_l))
           + lambda(c) * sum_d (u_d - u0_d) ** 2

where ``u0`` is the prior utility vector (normalized BM25 score by default),
``c`` is observation coverage (``len(revealed) / n_total_pairs``), and
``lambda(c)`` is one of the three predeclared, monotone-non-increasing
schedules in :data:`SCHEDULES` (frozen before test-set evaluation -- see
``configs/regularized_aggregation_pilot_v1.json``).

At ``c = 0`` the pairwise term is empty (a sum over zero terms), so the
unique minimizer of ``L`` is exactly ``u = u0`` for *any* lambda(0) > 0 --
this is returned directly (Phase 5 property 1), without invoking the
optimizer, so it is exact rather than "converged close to."

Leakage discipline
-------------------
Every public function here takes only (a) the fixed candidate pool, (b) the
revealed-so-far (winner, loser) list, and (c) the qrels-free BM25-derived
prior. None accepts qrels or an oracle object -- enforced by
``tests/test_regularized_aggregation.py``.
"""

from __future__ import annotations

import math
from typing import Callable

import numpy as np

ScheduleFn = Callable[[float], float]


def _validate_revealed(candidates: tuple[str, ...], revealed: list[tuple[str, str]]) -> None:
    cand_set = set(candidates)
    for w, loser in revealed:
        if w == loser:
            raise ValueError(f"malformed judgment: winner and loser are the same document ({w!r})")
        if w not in cand_set or loser not in cand_set:
            raise ValueError(
                f"malformed judgment: ({w!r}, {loser!r}) references a document outside the "
                f"candidate pool {candidates!r}"
            )


# ---------------------------------------------------------------------------
# Regularization schedules (Phase 2/4) -- frozen, deterministic, coverage-only
# ---------------------------------------------------------------------------


def _linear_decay(c: float, lambda0: float) -> float:
    """lambda(c) = lambda0 * (1 - c) -- reaches exactly 0 at full coverage."""
    return float(lambda0 * max(0.0, 1.0 - c))


def _inverse_coverage(c: float, lambda0: float, eps: float) -> float:
    """lambda(c) = lambda0 / (eps + c) -- never fully releases the prior anchor."""
    return float(lambda0 / (eps + c))


def _pseudo_count_cutoff(c: float, lambda0: float, c_star: float) -> float:
    """lambda(c) = lambda0 * max(0, 1 - c/c_star) -- drops to 0 once coverage
    reaches ``c_star``, faster release than the linear schedule."""
    return float(lambda0 * max(0.0, 1.0 - c / c_star))


# The three predeclared schedules (1 primary + 2 alternates, Phase 4). Values
# were chosen once, before dev-set inspection, from the natural scale of the
# pairwise log-likelihood (each revealed edge contributes O(1) to the NLL, so
# lambda0 on the same order keeps the prior term comparable in magnitude to a
# handful of early observations) -- not by grid search. See
# ``configs/regularized_aggregation_pilot_v1.json`` for the frozen selection
# and REPORT.md Phase 4 for the recorded dev-set comparison of all three.
SCHEDULES: dict[str, ScheduleFn] = {
    "linear_decay": lambda c: _linear_decay(c, lambda0=8.0),
    "inverse_coverage": lambda c: _inverse_coverage(c, lambda0=0.5, eps=0.05),
    "pseudo_count_cutoff": lambda c: _pseudo_count_cutoff(c, lambda0=8.0, c_star=0.4),
}

# Tiny numerical-stability anchor for the "pure / unregularized" comparison
# condition (Phase 3, method 3). This is *not* an informative prior -- it
# anchors to the zero vector (not BM25) only to keep the additive-shift
# indeterminacy of unregularized Bradley-Terry from diverging to infinity on
# separable early data. Frozen, disclosed, never tuned per query.
_UNREGULARIZED_STABILIZER_LAMBDA = 1.0e-3

# Floor applied inside fit_bt_utilities to every lambda, including the
# schedule-declared value (which reaches exactly 0 at full coverage under
# linear_decay) -- see fit_bt_utilities for why. Far below any pairwise
# log-likelihood term's natural scale (O(1) per observation).
_MIN_LAMBDA_FOR_NUMERICAL_STABILITY = 1.0e-9

# Fixed optimizer schedule for fit_bt_utilities: a fixed iteration count
# (never an adaptive/data-dependent stopping rule) so the exact sequence of
# floating-point operations executed is identical on every call for the same
# input -- see fit_bt_utilities for why this matters more than raw speed.
_ADAM_ITERATIONS = 3000
_ADAM_LR = 0.05
_ADAM_BETA1 = 0.9
_ADAM_BETA2 = 0.999
_ADAM_EPS = 1.0e-12


def _bt_negative_log_likelihood_and_grad(
    u: np.ndarray,
    doc_index: dict[str, int],
    revealed: list[tuple[str, str]],
    prior: np.ndarray,
    lam: float,
) -> tuple[float, np.ndarray]:
    grad = 2.0 * lam * (u - prior)
    loss = float(lam * np.sum((u - prior) ** 2))
    for w, loser in revealed:
        wi, li = doc_index[w], doc_index[loser]
        x = u[wi] - u[li]
        # numerically stable log(sigmoid(x)) and its gradient
        if x >= 0:
            log_s = -math.log1p(math.exp(-x))
            s = 1.0 / (1.0 + math.exp(-x))
        else:
            log_s = x - math.log1p(math.exp(x))
            s = math.exp(x) / (1.0 + math.exp(x))
        loss += -log_s
        grad[wi] += s - 1.0
        grad[li] += 1.0 - s
    return loss, grad


def fit_bt_utilities(
    candidates: tuple[str, ...],
    revealed: list[tuple[str, str]],
    prior: dict[str, float],
    lam: float,
) -> dict[str, float]:
    """Fit regularized Bradley-Terry utilities for one query.

    ``lam`` is a single already-resolved regularization strength (the caller
    applies the coverage schedule before calling this). Deterministic: given
    the same inputs, always returns the same output.

    Uses a fixed-iteration-count Adam optimizer rather than an
    adaptive-tolerance method (e.g. scipy's L-BFGS-B). At lam == 0 exactly
    (the linear_decay schedule's declared value at full coverage), the
    objective is invariant to a uniform shift of every utility (adding the
    same value to every u_d leaves every u_w - u_l unchanged), so the
    Hessian is singular along that direction; an adaptive-tolerance
    optimizer's *iteration count* along that near-flat direction turned out
    to depend on run-to-run floating-point noise (observed empirically: two
    otherwise-identical process runs landed at measurably different points
    along the flat direction, invisible in nDCG/top-k membership but visible
    in the full-list Kendall tau). A fixed iteration count removes that
    ambiguity: the exact same sequence of arithmetic operations executes
    every time for the same input, so the output is bit-identical. The tiny
    lambda floor below additionally keeps the objective strictly convex.
    """
    _validate_revealed(candidates, revealed)
    if not revealed:
        # Exact minimizer when the pairwise term is empty -- see module
        # docstring. Returned directly rather than via the optimizer so this
        # is bit-exact, not "close to," satisfying the zero-observation
        # BM25-reproduction property.
        return dict(prior)

    lam_stable = max(lam, _MIN_LAMBDA_FOR_NUMERICAL_STABILITY)

    doc_index = {d: idx for idx, d in enumerate(candidates)}
    prior_vec = np.array([prior.get(d, 0.0) for d in candidates], dtype=float)
    u = prior_vec.copy()
    m = np.zeros_like(u)
    v = np.zeros_like(u)
    for t in range(1, _ADAM_ITERATIONS + 1):
        _, grad = _bt_negative_log_likelihood_and_grad(
            u, doc_index, revealed, prior_vec, lam_stable
        )
        m = _ADAM_BETA1 * m + (1.0 - _ADAM_BETA1) * grad
        v = _ADAM_BETA2 * v + (1.0 - _ADAM_BETA2) * (grad * grad)
        m_hat = m / (1.0 - _ADAM_BETA1**t)
        v_hat = v / (1.0 - _ADAM_BETA2**t)
        u = u - _ADAM_LR * m_hat / (np.sqrt(v_hat) + _ADAM_EPS)

    return {d: float(u[idx]) for d, idx in doc_index.items()}


def rank_from_utilities(
    candidates: tuple[str, ...],
    utilities: dict[str, float],
    bm25_norm: dict[str, float],
) -> list[str]:
    """Deterministic extraction: utility descending, BM25 tie-break, doc-id
    tie-break -- same tie-break convention as :func:`scoring.rank_from_copeland`."""
    return sorted(
        candidates,
        key=lambda d: (-utilities.get(d, 0.0), -bm25_norm.get(d, 0.0), d),
    )


def regularized_bt_ranking(
    candidates: tuple[str, ...],
    revealed: list[tuple[str, str]],
    bm25_norm: dict[str, float],
    n_total_pairs: int,
    schedule: ScheduleFn,
) -> list[str]:
    """The proposed method (Phase 2): coverage-adaptive prior-regularized BT.

    Uses only the fixed candidate pool, the revealed-so-far outcomes, the
    qrels-free BM25 prior, and the current coverage fraction -- never qrels,
    never an unrevealed outcome, never the exhaustive ranking.
    """
    coverage = len(revealed) / n_total_pairs if n_total_pairs > 0 else 0.0
    lam = schedule(coverage)
    utilities = fit_bt_utilities(candidates, revealed, bm25_norm, lam)
    return rank_from_utilities(candidates, utilities, bm25_norm)


def pure_bt_ranking(
    candidates: tuple[str, ...],
    revealed: list[tuple[str, str]],
    bm25_norm: dict[str, float],
) -> list[str]:
    """Comparison method 3 (Phase 3): revealed-evidence Bradley-Terry with no
    informative prior -- regularized only toward the zero vector, and only
    with the tiny fixed stabilizer needed to keep unregularized BT from
    diverging on separable early data (see module docstring). BM25 is used
    solely for the deterministic tie-break, never as a utility prior."""
    zero_prior = {d: 0.0 for d in candidates}
    utilities = fit_bt_utilities(candidates, revealed, zero_prior, _UNREGULARIZED_STABILIZER_LAMBDA)
    return rank_from_utilities(candidates, utilities, bm25_norm)


def fixed_blend_ranking(
    candidates: tuple[str, ...],
    revealed: list[tuple[str, str]],
    bm25_norm: dict[str, float],
    weight_bm25: float = 0.5,
) -> list[str]:
    """Comparison method 4 (Phase 3): a fixed-weight (not coverage-adaptive)
    linear blend of the BM25 prior and the current Copeland tally, normalized
    the same way :mod:`scoring`'s ``uncertainty_score`` does
    (``copeland / (n - 1)``). ``weight_bm25`` is frozen at a neutral 0.5
    before evaluation, disclosed as arbitrary rather than tuned."""
    _validate_revealed(candidates, revealed)
    n_max = max(len(candidates) - 1, 1)
    copeland = {d: 0.0 for d in candidates}
    for w, loser in revealed:
        copeland[w] += 1.0
        copeland[loser] -= 1.0
    blended = {
        d: weight_bm25 * bm25_norm.get(d, 0.0) + (1.0 - weight_bm25) * (copeland[d] / n_max)
        for d in candidates
    }
    return sorted(candidates, key=lambda d: (-blended[d], -bm25_norm.get(d, 0.0), d))


__all__ = [
    "SCHEDULES",
    "fit_bt_utilities",
    "rank_from_utilities",
    "regularized_bt_ranking",
    "pure_bt_ranking",
    "fixed_blend_ranking",
]
