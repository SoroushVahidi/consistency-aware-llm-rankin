"""
synthetic_data.py
=================
Generate synthetic ranked item sets for controlled experiments.

Each item has a numeric *quality score* drawn from a uniform distribution.
The ground-truth ranking is the descending order of quality scores.  Callers
can then feed the items into :mod:`pairwise_prefs` to get noisy pairwise
comparisons.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SyntheticItem:
    """A single synthetic item with an identifier and a latent quality score."""

    item_id: str
    quality: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:  # pragma: no cover
        return f"SyntheticItem(id={self.item_id!r}, quality={self.quality:.4f})"


def generate_items(
    n: int,
    seed: int | None = None,
    id_prefix: str = "item",
) -> list[SyntheticItem]:
    """Generate *n* synthetic items with uniform random quality scores.

    Parameters
    ----------
    n:
        Number of items to generate.  Must be ≥ 2.
    seed:
        Optional random seed for reproducibility.
    id_prefix:
        String prefix used to construct item ids (e.g. ``"item"`` → ``"item_00"``)

    Returns
    -------
    list[SyntheticItem]
        Items in **random** order (not sorted by quality).

    Raises
    ------
    ValueError
        If *n* < 2.
    """
    if n < 2:
        raise ValueError(f"n must be at least 2, got {n}")
    rng = random.Random(seed)
    items = [
        SyntheticItem(
            item_id=f"{id_prefix}_{i:02d}",
            quality=rng.random(),
        )
        for i in range(n)
    ]
    return items


def ground_truth_ranking(items: list[SyntheticItem]) -> list[str]:
    """Return item ids sorted from best (highest quality) to worst.

    Parameters
    ----------
    items:
        List of :class:`SyntheticItem` objects.

    Returns
    -------
    list[str]
        Item ids in descending quality order.
    """
    return [item.item_id for item in sorted(items, key=lambda x: x.quality, reverse=True)]


def quality_map(items: list[SyntheticItem]) -> dict[str, float]:
    """Return a mapping from item id to quality score.

    Parameters
    ----------
    items:
        List of :class:`SyntheticItem` objects.

    Returns
    -------
    dict[str, float]
    """
    return {item.item_id: item.quality for item in items}
