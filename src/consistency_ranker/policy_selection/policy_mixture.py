"""Soft policy mixtures: score mix, budget split, staged, safety floor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MixtureConfig:
    mode: str = "score_mixture"  # score_mixture | budget_split | staged | safety_floor
    g_q: float = 0.5  # prior credibility in [0,1]
    safety_floor: float = 0.15  # minimum robust exploration share
    uht_policy: str = "UHT"
    robust_policy: str = "CHALLENGER"


def clipped_credibility(g_q: float, safety_floor: float = 0.15) -> float:
    """Map credibility to mixture weight with a mandatory exploration floor."""
    g = float(max(0.0, min(1.0, g_q)))
    floor = float(max(0.0, min(0.5, safety_floor)))
    # Effective UHT weight cannot exceed 1 - floor.
    return float(min(g, 1.0 - floor))


def hybrid_score(
    score_uht: float,
    score_challenger: float,
    g_q: float,
    *,
    safety_floor: float = 0.15,
) -> float:
    """A_hybrid = g * A_UHT + (1-g) * A_challenger with safety floor on (1-g)."""
    g = clipped_credibility(g_q, safety_floor)
    return float(g * score_uht + (1.0 - g) * score_challenger)


def split_budget(
    total_budget: int,
    g_q: float,
    *,
    safety_floor: float = 0.15,
) -> dict[str, float]:
    """Allocate B_UHT = g*B and B_robust = (1-g)*B with integer rounding.

    ``UHT`` and ``robust`` are whole calls; ``g_eff`` is the floored credibility
    that produced the split, so the mapping is widened to float.
    """
    g = clipped_credibility(g_q, safety_floor)
    b = max(0, int(total_budget))
    b_uht = int(round(g * b))
    b_robust = b - b_uht
    # Enforce at least one robust call when floor > 0 and budget >= 2.
    if safety_floor > 0 and b >= 2 and b_robust == 0:
        b_robust = 1
        b_uht = b - 1
    return {"UHT": b_uht, "robust": b_robust, "g_eff": g}


def staged_plan(
    g_q: float,
    *,
    contradiction_rate: float = 0.0,
    buried_signal: float = 0.0,
    safety_floor: float = 0.15,
) -> dict[str, Any]:
    """Return a staged policy plan given current credibility and signals."""
    g = clipped_credibility(g_q, safety_floor)
    if buried_signal >= 0.5 or contradiction_rate >= 0.35:
        return {
            "phase": "challenger",
            "primary": "CHALLENGER",
            "g_eff": g,
            "reason": "strong_contradiction_or_burial",
        }
    if g >= 0.65:
        return {
            "phase": "uht_local",
            "primary": "UHT",
            "g_eff": g,
            "reason": "high_credibility",
        }
    if g <= 0.35:
        return {
            "phase": "robust",
            "primary": "ROBUST_COMBINED",
            "g_eff": g,
            "reason": "low_credibility",
        }
    return {
        "phase": "hybrid",
        "primary": "HYBRID",
        "g_eff": g,
        "reason": "mid_credibility",
    }


__all__ = [
    "MixtureConfig",
    "clipped_credibility",
    "hybrid_score",
    "split_budget",
    "staged_plan",
]
