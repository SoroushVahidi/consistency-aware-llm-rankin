"""Query-adaptive prior influence λ_q.

λ_q modulates prior regularization, topological tie-breaking, acquisition
impact, and stopping. Changes are rate-limited to avoid oscillation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from consistency_ranker.prior_robust.prior_quality import PriorQualityEstimate

PriorMode = Literal[
    "fixed",
    "none",
    "global_validation",
    "adaptive",
    "decrease_on_contradiction",
    "increase_on_agreement",
    "capped",
]


@dataclass
class AdaptivePriorState:
    """Serializable adaptive prior weight with history."""

    lambda_q: float = 0.5
    mode: PriorMode = "adaptive"
    q_hat: float = 0.5
    lo: float = 0.0
    hi: float = 1.0
    max_step: float = 0.15  # rate limit per update
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lambda_q": self.lambda_q,
            "mode": self.mode,
            "q_hat": self.q_hat,
            "lo": self.lo,
            "hi": self.hi,
            "max_step": self.max_step,
            "history": list(self.history),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AdaptivePriorState":
        return cls(
            lambda_q=float(data.get("lambda_q", 0.5)),
            mode=data.get("mode", "adaptive"),  # type: ignore[arg-type]
            q_hat=float(data.get("q_hat", 0.5)),
            lo=float(data.get("lo", 0.0)),
            hi=float(data.get("hi", 1.0)),
            max_step=float(data.get("max_step", 0.15)),
            history=list(data.get("history", [])),
        )


def _clip(x: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, x)))


def _rate_limit(old: float, target: float, max_step: float) -> float:
    delta = target - old
    if abs(delta) <= max_step:
        return target
    return old + max_step * (1.0 if delta > 0 else -1.0)


def update_lambda(
    state: AdaptivePriorState,
    quality: PriorQualityEstimate,
    *,
    fixed_value: float = 0.5,
    global_value: float = 0.5,
    step: int = 0,
) -> AdaptivePriorState:
    """Update λ_q from a prior-quality estimate according to ``state.mode``."""
    old = state.lambda_q
    q = quality.q_hat
    reason = state.mode

    if state.mode == "fixed":
        target = fixed_value
        reason = "fixed"
    elif state.mode == "none":
        target = 0.0
        reason = "no_prior"
    elif state.mode == "global_validation":
        target = global_value
        reason = "global_validation"
    elif state.mode == "capped":
        # Map Q → λ but hard-cap at hi (default 0.7).
        target = _clip(q, state.lo, min(state.hi, 0.7))
        reason = "capped_adaptive"
    elif state.mode == "decrease_on_contradiction":
        hc = quality.high_conf_contradiction_rate
        if hc is not None and hc > 0.3:
            target = old * (1.0 - 0.5 * hc)
            reason = "decrease_on_contradiction"
        else:
            target = 0.5 * old + 0.5 * q
            reason = "soft_toward_q"
    elif state.mode == "increase_on_agreement":
        agr = quality.agreement_rate
        if agr is not None and agr > 0.7:
            target = old + 0.2 * (agr - 0.5)
            reason = "increase_on_agreement"
        else:
            target = 0.5 * old + 0.5 * q
            reason = "soft_toward_q"
    else:  # adaptive
        target = q
        reason = "adaptive_q"

    target = _clip(target, state.lo, state.hi)
    new = _rate_limit(old, target, state.max_step)
    new = _clip(new, state.lo, state.hi)
    state.lambda_q = new
    state.q_hat = q
    state.history.append(
        {
            "step": step,
            "lambda_q": new,
            "q_hat": q,
            "target": target,
            "reason": reason,
            "agreement_rate": quality.agreement_rate,
            "hc_contradiction": quality.high_conf_contradiction_rate,
        }
    )
    return state


def blend_priorities(
    prior_scores: dict[str, float],
    evidence_scores: dict[str, float],
    lambda_q: float,
) -> dict[str, float]:
    r"""``P(v) = λ P_prior(v) + (1-λ) P_evidence(v)`` after per-map z-scoring."""

    def _z(m: dict[str, float]) -> dict[str, float]:
        if not m:
            return {}
        vals = list(m.values())
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / max(len(vals), 1)
        sd = var**0.5 or 1.0
        return {k: (float(v) - mean) / sd for k, v in m.items()}

    zp, ze = _z(prior_scores), _z(evidence_scores)
    keys = set(zp) | set(ze)
    return {
        k: float(lambda_q) * zp.get(k, 0.0) + (1.0 - float(lambda_q)) * ze.get(k, 0.0)
        for k in keys
    }


__all__ = [
    "PriorMode",
    "AdaptivePriorState",
    "update_lambda",
    "blend_priorities",
]
