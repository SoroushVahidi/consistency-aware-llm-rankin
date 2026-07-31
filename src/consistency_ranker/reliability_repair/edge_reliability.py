"""Reliability estimators separate from preference direction."""

from __future__ import annotations

import math
from typing import Literal, Sequence

from consistency_ranker.reliability_repair.evidence_aggregation import PairAggregate

ReliabilityMethod = Literal[
    "margin",
    "entropy",
    "orientation",
    "agreement_composite_mult",
    "agreement_composite_arith",
    "agreement_composite_geom",
    "logistic_features",
]


def reliability_margin(agg: PairAggregate) -> float:
    return float(abs(agg.m))


def reliability_entropy(agg: PairAggregate) -> float:
    """1 - H(p)/log(2); 1 means certain.

    Uses the raw directional fraction when available (not Laplace-smoothed
    ``p_hat``), so unanimous evidence yields reliability 1.
    """
    denom = agg.n_plus + agg.n_minus
    if denom <= 0:
        return 0.0
    p = agg.n_plus / denom
    if p <= 0.0 or p >= 1.0:
        return 1.0
    h = -p * math.log(p) - (1 - p) * math.log(1 - p)
    return float(1.0 - h / math.log(2))


def reliability_orientation(agg: PairAggregate) -> float:
    return float(agg.features.get("orientation_agreement", 1.0))


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def reliability_agreement_composite(
    agg: PairAggregate,
    *,
    mode: Literal["mult", "arith", "geom"] = "mult",
    floor: float = 1e-3,
) -> float:
    parts = [
        reliability_margin(agg),
        reliability_orientation(agg),
        float(agg.features.get("repeat_agreement", 1.0)),
        float(agg.features.get("prompt_agreement", 1.0)),
        float(agg.features.get("model_agreement", 1.0)),
    ]
    parts = [_clip01(p) for p in parts]
    if mode == "mult":
        r = 1.0
        for p in parts:
            r *= max(p, floor)
        return float(r)
    if mode == "arith":
        return float(sum(parts) / len(parts))
    # geom
    logs = [math.log(max(p, floor)) for p in parts]
    return float(math.exp(sum(logs) / len(logs)))


def reliability_logistic_features(
    agg: PairAggregate,
    *,
    coefficients: dict[str, float] | None = None,
    intercept: float = 0.0,
) -> float:
    """Sigmoid of linear features. Default coefficients are heuristic (not fitted)."""
    coef = coefficients or {
        "abs_margin": 2.0,
        "orientation_agreement": 1.0,
        "valid_fraction": 1.0,
        "model_agreement": 0.5,
        "prompt_agreement": 0.5,
        "outcome_entropy": -1.0,
        "invalid_rate": -1.0,
    }
    s = float(intercept)
    for k, w in coef.items():
        if k == "abs_margin":
            s += w * abs(agg.m)
        else:
            s += w * float(agg.features.get(k, 0.0))
    return float(1.0 / (1.0 + math.exp(-s)))


def estimate_reliability(
    agg: PairAggregate,
    method: ReliabilityMethod = "agreement_composite_arith",
    **kwargs,
) -> float:
    if method == "margin":
        return reliability_margin(agg)
    if method == "entropy":
        return reliability_entropy(agg)
    if method == "orientation":
        return reliability_orientation(agg)
    if method == "agreement_composite_mult":
        return reliability_agreement_composite(agg, mode="mult", **kwargs)
    if method == "agreement_composite_arith":
        return reliability_agreement_composite(agg, mode="arith", **kwargs)
    if method == "agreement_composite_geom":
        return reliability_agreement_composite(agg, mode="geom", **kwargs)
    if method == "logistic_features":
        return reliability_logistic_features(agg, **kwargs)
    raise ValueError(f"Unknown reliability method {method!r}")


def estimate_reliability_batch(
    aggregates: Sequence[PairAggregate],
    method: ReliabilityMethod = "agreement_composite_arith",
    **kwargs,
) -> dict[str, float]:
    return {
        a.canonical_pair_id: estimate_reliability(a, method=method, **kwargs)
        for a in aggregates
    }
