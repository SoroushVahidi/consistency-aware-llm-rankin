"""
pairwise_prefs.py
=================
Generate (potentially noisy) pairwise preference observations from a set of
items with known quality scores.

For each ordered pair (i, j) with quality[i] > quality[j] the *true* preference
is i > j.  A noise model then flips this decision with probability *noise*,
producing realistic inconsistencies that can form cycles in the preference graph.

Each returned preference is a triple ``(winner_id, loser_id, weight)`` where
*weight* encodes the confidence or margin of the comparison.
"""

from __future__ import annotations

import random
from itertools import combinations
from typing import NamedTuple

# Minimum edge weight used when two items have exactly equal quality scores.
# Prevents zero-weight edges (which can cause division-by-zero in some
# downstream solvers) while staying small enough not to bias results.
_MIN_EDGE_WEIGHT = 1e-6


class Preference(NamedTuple):
    """A single pairwise preference observation."""

    winner: str
    """Id of the preferred item."""
    loser: str
    """Id of the less-preferred item."""
    weight: float
    """Confidence / strength of the preference (> 0)."""


def generate_preferences(
    quality_map: dict[str, float],
    noise: float = 0.1,
    weight_scheme: str = "margin",
    seed: int | None = None,
) -> list[Preference]:
    """Generate noisy pairwise preferences for all pairs of items.

    Parameters
    ----------
    quality_map:
        Mapping from item id to latent quality score.
    noise:
        Probability of flipping the true preference direction.  Must be in
        ``[0, 1)``.  Higher values introduce more cycles.
    weight_scheme:
        How to assign edge weights:

        - ``"uniform"``: all weights set to 1.0.
        - ``"margin"``: weight = |quality[i] - quality[j]|, the absolute
          quality difference.  Larger margin → stronger preference.

    seed:
        Optional random seed.

    Returns
    -------
    list[Preference]
        One :class:`Preference` per unordered pair.

    Raises
    ------
    ValueError
        If *noise* is not in [0, 1) or *weight_scheme* is unknown.
    """
    if not (0.0 <= noise < 1.0):
        raise ValueError(f"noise must be in [0, 1), got {noise}")
    if weight_scheme not in {"uniform", "margin"}:
        raise ValueError(f"Unknown weight_scheme: {weight_scheme!r}. Choose 'uniform' or 'margin'.")

    rng = random.Random(seed)
    item_ids = list(quality_map.keys())
    preferences: list[Preference] = []

    for id_a, id_b in combinations(item_ids, 2):
        q_a = quality_map[id_a]
        q_b = quality_map[id_b]

        # Determine true winner using strict comparison.
        # Ties (q_a == q_b) are broken by iteration order, which is consistent
        # for a fixed set of item ids but essentially arbitrary.
        true_winner, true_loser = (id_a, id_b) if q_a > q_b else (id_b, id_a)

        # Compute weight before possible flip
        if weight_scheme == "uniform":
            w = 1.0
        else:  # margin
            w = abs(q_a - q_b)
            if w == 0.0:
                w = _MIN_EDGE_WEIGHT

        # Possibly flip
        if rng.random() < noise:
            winner, loser = true_loser, true_winner
        else:
            winner, loser = true_winner, true_loser

        preferences.append(Preference(winner=winner, loser=loser, weight=w))

    return preferences


def preferences_to_dict(
    preferences: list[Preference],
) -> dict[tuple[str, str], float]:
    """Convert a list of :class:`Preference` objects to an edge-weight dict.

    Parameters
    ----------
    preferences:
        Output of :func:`generate_preferences`.

    Returns
    -------
    dict[(winner, loser), weight]
    """
    return {(p.winner, p.loser): p.weight for p in preferences}
