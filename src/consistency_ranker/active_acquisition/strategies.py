"""The acquisition strategies compared in the pilot (Phase 3).

Seven distinct algorithms are actually simulated; two reference conditions
(exhaustive, initial) are derived rather than simulated (see the module
docstring in ``simulate.py`` for why that is exact, not an approximation).
Several of the required *named* strategies are, by construction, the same
underlying algorithm under a different label — this is documented here
rather than hidden, per the task's instruction to document (not force) any
degenerate comparison:

* ``existing_uht`` (production UHT's ``uncertainty_x_topk_impact`` score
  mode, see ``src/consistency_ranker/policy_selection/policy_runner.py``)
  uses a vote-based uncertainty measure that is 1.0 for every unqueried pair
  and only differs once a *repeated* judgment exists for the same pair. This
  offline oracle records exactly one judgment per pair (no repeats, no
  multi-provider evidence), so ``vote_uncertainty`` is a constant across all
  remaining candidates at every step and the product ``u * impact`` reduces
  to ranking by ``impact`` alone. ``existing_uht`` is therefore algorithmically
  identical to ``ablation_impact_only`` in this regime — not omitted, just
  disclosed.
* ``ablation_uncertainty_only`` is identical to the required baseline
  ``uncertainty_only``.
* ``ablation_full`` is identical to ``proposed``.

Algorithm keys actually simulated: ``random``, ``static_adjacent``,
``cycle_scc``, ``score:uncertainty_only``, ``score:impact_only``,
``score:impact_x_uncertainty``, ``score:proposed``.
"""

from __future__ import annotations

import random
from typing import Callable

from consistency_ranker.active_acquisition.scoring import (
    StepContext,
    ablation_impact_only,
    ablation_impact_x_uncertainty,
    ablation_uncertainty_only,
    ambiguity_score,
    proposed_score,
    uncertainty_score,
)

ScorerFn = Callable[[StepContext, str, str], float]

SCORERS: dict[str, ScorerFn] = {
    "score:uncertainty_only": ablation_uncertainty_only,
    "score:impact_only": ablation_impact_only,
    "score:impact_x_uncertainty": ablation_impact_x_uncertainty,
    "score:proposed": proposed_score,
}

# distinct algorithms that are actually simulated
ALGORITHMS: tuple[str, ...] = (
    "random",
    "static_adjacent",
    "cycle_scc",
    "score:uncertainty_only",
    "score:impact_only",
    "score:impact_x_uncertainty",
    "score:proposed",
)

# user-facing strategy label -> algorithm key it is computed from
STRATEGY_TO_ALGORITHM: dict[str, str] = {
    "random_unobserved": "random",
    "static_adjacent": "static_adjacent",
    "uncertainty_only": "score:uncertainty_only",
    "cycle_scc": "cycle_scc",
    "existing_uht": "score:impact_only",  # documented collapse, see docstring
    "proposed": "score:proposed",
    "ablation_impact_only": "score:impact_only",
    "ablation_uncertainty_only": "score:uncertainty_only",
    "ablation_impact_x_uncertainty": "score:impact_x_uncertainty",
    "ablation_full": "score:proposed",
}

REQUIRED_PHASE3_STRATEGIES: tuple[str, ...] = (
    "random_unobserved",
    "static_adjacent",
    "uncertainty_only",
    "cycle_scc",
    "existing_uht",
    "proposed",
    # "exhaustive" and "initial" are reference rows, derived not simulated
)

PHASE7_ABLATIONS: tuple[str, ...] = (
    "ablation_impact_only",
    "ablation_uncertainty_only",
    "ablation_impact_x_uncertainty",
    "ablation_full",
)


def pick_next_pair(
    algorithm: str,
    ctx: StepContext,
    remaining: list[frozenset],
    static_order: list[frozenset] | None,
    rng: random.Random,
) -> frozenset:
    """Return the next pair (as a frozenset of two doc ids) to reveal.

    ``remaining`` and ``static_order`` are lists of frozensets over the fixed
    candidate pool; only currently-unrevealed pairs are ever passed in.
    """
    if algorithm == "random":
        return remaining[rng.randrange(len(remaining))]
    if algorithm == "static_adjacent":
        assert static_order is not None
        remaining_set = set(remaining)
        for pair in static_order:
            if pair in remaining_set:
                return pair
        raise RuntimeError("static_adjacent: no remaining pair found in precomputed order")
    if algorithm == "cycle_scc":
        best_pair: frozenset | None = None
        best_tuple: tuple[str, str] = ("", "")
        best_key: tuple[float, float] | None = None
        for pair in remaining:
            i, j = sorted(pair)
            key = (ambiguity_score(ctx, i, j), uncertainty_score(ctx, i, j))
            tup = (i, j)
            if best_key is None or key > best_key or (key == best_key and tup < best_tuple):
                best_key, best_tuple, best_pair = key, tup, pair
        assert best_pair is not None
        return best_pair
    scorer = SCORERS.get(algorithm)
    if scorer is None:
        raise ValueError(f"Unknown algorithm {algorithm!r}")
    best_pair2: frozenset | None = None
    best_tuple2: tuple[str, str] = ("", "")
    best_score: float | None = None
    for pair in remaining:
        i, j = sorted(pair)
        score = scorer(ctx, i, j)
        tup = (i, j)
        if best_score is None or score > best_score or (score == best_score and tup < best_tuple2):
            best_score, best_tuple2, best_pair2 = score, tup, pair
    assert best_pair2 is not None
    return best_pair2


__all__ = [
    "SCORERS",
    "ALGORITHMS",
    "STRATEGY_TO_ALGORITHM",
    "REQUIRED_PHASE3_STRATEGIES",
    "PHASE7_ABLATIONS",
    "pick_next_pair",
]
