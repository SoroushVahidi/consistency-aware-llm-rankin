"""Empirical risk-control / conformal-style gating helpers.

Assumptions and limitations are stated explicitly: under exchangeability of
calibration queries with deployment queries, split-conformal thresholds
provide finite-sample marginal coverage. Synthetic regime shifts violate
exchangeability; then these are diagnostics, not guarantees.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RiskControlConfig:
    # Bound P(select UHT when regret_UHT > eps) ≤ alpha  (empirical, exchangeable)
    eps_regret: float = 0.05
    alpha: float = 0.1
    # Bound catastrophic-failure rate when selecting UHT
    alpha_catastrophic: float = 0.05
    # Produce a set of acceptable policies rather than one
    set_valued: bool = True


@dataclass
class RiskControlResult:
    allowed_policies: list[str]
    uht_allowed: bool
    threshold_score: float
    empirical_risk: float
    assumptions: str
    is_formal_guarantee: bool
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed_policies": list(self.allowed_policies),
            "uht_allowed": self.uht_allowed,
            "threshold_score": self.threshold_score,
            "empirical_risk": self.empirical_risk,
            "assumptions": self.assumptions,
            "is_formal_guarantee": self.is_formal_guarantee,
            "notes": list(self.notes),
        }


ASSUMPTIONS = (
    "Split-conformal / risk-control thresholds assume exchangeability between "
    "calibration and deployment queries. Nested synthetic regime shifts and "
    "real distribution shift violate this; treat results as empirical bounds "
    "on the calibration distribution only, not as deployment guarantees."
)


def _quantile(xs: list[float], q: float) -> float:
    if not xs:
        return 0.0
    ys = sorted(xs)
    idx = min(len(ys) - 1, max(0, int(q * len(ys))))
    return float(ys[idx])


def fit_uht_risk_threshold(
    *,
    scores: list[float],
    uht_regret: list[float],
    catastrophic: list[bool],
    cfg: RiskControlConfig | None = None,
) -> float:
    """Return minimum score required to allow UHT under empirical risk control.

    Higher score = more confidence that UHT is safe. We find the lowest
    threshold t such that among calibration points with score >= t, the
    fraction with regret > eps (or catastrophic) is ≤ alpha.
    """
    cfg = cfg or RiskControlConfig()
    if not scores:
        return 1.0
    candidates = sorted(set(scores))
    best = 1.0
    for t in candidates:
        idx = [i for i, s in enumerate(scores) if s >= t]
        if len(idx) < 3:
            continue
        risk = sum(1 for i in idx if uht_regret[i] > cfg.eps_regret) / len(idx)
        cat = sum(1 for i in idx if catastrophic[i]) / len(idx)
        if risk <= cfg.alpha and cat <= cfg.alpha_catastrophic:
            best = t
            break
    return float(best)


def acceptable_policy_set(
    *,
    policy_scores: dict[str, float],
    policy_regrets: dict[str, float],
    cfg: RiskControlConfig | None = None,
    uht_threshold: float = 0.5,
) -> RiskControlResult:
    cfg = cfg or RiskControlConfig()
    allowed = []
    notes = []
    for p, s in policy_scores.items():
        r = policy_regrets.get(p, 0.0)
        if p == "UHT":
            if s >= uht_threshold and r <= cfg.eps_regret:
                allowed.append(p)
            else:
                notes.append(f"UHT excluded: score={s:.3f} thr={uht_threshold:.3f} regret={r:.3f}")
        else:
            if r <= cfg.eps_regret + 0.05:
                allowed.append(p)
    if not allowed:
        allowed = ["CHALLENGER", "STOP_OR_FALLBACK"]
        notes.append("empty set → conservative fallback")
    # Prefer highest score among allowed
    allowed.sort(key=lambda p: -policy_scores.get(p, 0.0))
    return RiskControlResult(
        allowed_policies=allowed,
        uht_allowed="UHT" in allowed,
        threshold_score=uht_threshold,
        empirical_risk=float(policy_regrets.get("UHT", 0.0)),
        assumptions=ASSUMPTIONS,
        is_formal_guarantee=False,
        notes=notes,
    )


def conformal_prediction_set(
    calib_scores: list[tuple[str, float, str]],
    *,
    alpha: float = 0.1,
) -> dict[str, float]:
    """Return per-policy nonconformity quantile thresholds.

    ``calib_scores`` entries are (predicted_policy, score, true_best_policy).
    Nonconformity = 1 - score if predicted == true else 1.0 (simplified).
    """
    by_pol: dict[str, list[float]] = {}
    for pred, score, truth in calib_scores:
        nc = (1.0 - score) if pred == truth else 1.0
        by_pol.setdefault(pred, []).append(nc)
    return {p: _quantile(vs, 1.0 - alpha) for p, vs in by_pol.items()}


__all__ = [
    "RiskControlConfig",
    "RiskControlResult",
    "ASSUMPTIONS",
    "fit_uht_risk_threshold",
    "acceptable_policy_set",
    "conformal_prediction_set",
]
