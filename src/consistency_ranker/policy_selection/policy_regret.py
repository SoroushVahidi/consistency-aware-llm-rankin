"""Direct policy-regret prediction with uncertainty intervals."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from consistency_ranker.policy_selection.policy_calibration import (
    CalibratedModel,
    fit_calibrated_gate,
    predict_proba,
)


@dataclass
class RegretPrediction:
    pair: str  # e.g. "UHT_vs_CHALLENGER"
    delta_mean: float  # E[U(p1)-U(p2)]
    delta_std: float
    p_worse_than_fallback: float  # P(U_uht < U_fb - eps)
    interval_low: float
    interval_high: float
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair": self.pair,
            "delta_mean": self.delta_mean,
            "delta_std": self.delta_std,
            "p_worse_than_fallback": self.p_worse_than_fallback,
            "interval_low": self.interval_low,
            "interval_high": self.interval_high,
            "extras": dict(self.extras),
        }


def fit_regret_models(
    X: list[list[float]],
    deltas: dict[str, list[float]],
    *,
    feature_names: list[str],
    training_regimes: list[str] | None = None,
) -> dict[str, CalibratedModel]:
    """Fit one logistic model per pair predicting P(delta > 0).

    Continuous delta is also stored as a linear regressor via the same weights
    by fitting on a soft target sigmoid(delta / scale).
    """
    models: dict[str, CalibratedModel] = {}
    for pair, vals in deltas.items():
        # Soft binary: positive when p1 better than p2.
        y = [1.0 if v > 0 else 0.0 for v in vals]
        m = fit_calibrated_gate(
            X,
            y,
            feature_names=feature_names,
            kind="logistic",
            training_regimes=training_regimes,
            target_name=f"regret_{pair}",
        )
        # Attach empirical residual scale for intervals.
        probs = [predict_proba(m, xi) for xi in X]
        resid = [abs(v - (2 * p - 1)) for v, p in zip(vals, probs)]
        scale = (sum(resid) / len(resid)) if resid else 0.2
        m.metadata["delta_scale"] = float(scale)
        m.metadata["delta_mean_train"] = float(sum(vals) / len(vals)) if vals else 0.0
        models[pair] = m
    return models


def predict_policy_regret(
    models: dict[str, CalibratedModel],
    x: list[float],
    *,
    pair: str = "UHT_vs_CHALLENGER",
    eps: float = 0.02,
    risk_delta: float = 0.1,
) -> RegretPrediction:
    """Predict Δ(p1,p2) and P(UHT worse than fallback by > eps)."""
    m = models.get(pair)
    if m is None:
        return RegretPrediction(
            pair=pair,
            delta_mean=0.0,
            delta_std=0.25,
            p_worse_than_fallback=0.5,
            interval_low=-0.25,
            interval_high=0.25,
        )
    p_pos = predict_proba(m, x)
    scale = float(m.metadata.get("delta_scale", 0.2))
    # Map probability to signed expected delta in roughly [-1,1].
    delta_mean = float(2 * p_pos - 1) * max(scale, 0.05)
    delta_std = max(scale, 0.05)
    # Rough one-sided risk: if mean is low, higher P(worse).
    # Use logistic CDF approximation.
    import math

    z = (delta_mean + eps) / (delta_std + 1e-9)
    # P(delta < -eps) ≈ sigmoid(-z)
    p_worse = 1.0 / (1.0 + math.exp(z))
    return RegretPrediction(
        pair=pair,
        delta_mean=delta_mean,
        delta_std=delta_std,
        p_worse_than_fallback=float(p_worse),
        interval_low=delta_mean - 1.64 * delta_std,
        interval_high=delta_mean + 1.64 * delta_std,
        extras={"p_pos": p_pos, "risk_delta": risk_delta},
    )


def uht_allowed_by_risk(
    pred: RegretPrediction,
    *,
    delta_tol: float = 0.1,
) -> bool:
    """Allow UHT only if P(U_UHT < U_fallback - eps) < delta_tol."""
    return pred.p_worse_than_fallback < delta_tol


__all__ = [
    "RegretPrediction",
    "fit_regret_models",
    "predict_policy_regret",
    "uht_allowed_by_risk",
]
