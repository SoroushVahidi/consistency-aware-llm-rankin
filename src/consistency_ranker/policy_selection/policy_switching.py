"""Online policy switching with hysteresis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SwitchConfig:
    q_high: float = 0.65
    q_low: float = 0.40
    contradiction_high: float = 0.35
    buried_signal_high: float = 0.5
    gain_drop: float = 0.05
    challenger_yield_high: float = 0.4
    min_steps_between_switches: int = 3
    hysteresis: float = 0.08  # extra margin to reverse a switch


@dataclass
class SwitchEvent:
    step: int
    from_policy: str
    to_policy: str
    reason: str
    policy_probs: dict[str, float]
    credibility: float
    cost: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "from_policy": self.from_policy,
            "to_policy": self.to_policy,
            "reason": self.reason,
            "policy_probs": dict(self.policy_probs),
            "credibility": self.credibility,
            "cost": self.cost,
        }


@dataclass
class SwitchState:
    current_policy: str
    initial_policy: str
    last_switch_step: int = -999
    credibility_trajectory: list[float] = field(default_factory=list)
    events: list[SwitchEvent] = field(default_factory=list)
    policy_probs: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_policy": self.current_policy,
            "initial_policy": self.initial_policy,
            "last_switch_step": self.last_switch_step,
            "credibility_trajectory": list(self.credibility_trajectory),
            "events": [e.to_dict() for e in self.events],
            "policy_probs": dict(self.policy_probs),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SwitchState":
        st = cls(
            current_policy=d["current_policy"],
            initial_policy=d["initial_policy"],
            last_switch_step=int(d.get("last_switch_step", -999)),
            credibility_trajectory=list(d.get("credibility_trajectory") or []),
            policy_probs=dict(d.get("policy_probs") or {}),
        )
        for e in d.get("events") or []:
            st.events.append(
                SwitchEvent(
                    step=int(e["step"]),
                    from_policy=e["from_policy"],
                    to_policy=e["to_policy"],
                    reason=e["reason"],
                    policy_probs=dict(e.get("policy_probs") or {}),
                    credibility=float(e.get("credibility") or 0.0),
                    cost=float(e.get("cost") or 0.0),
                )
            )
        return st


def evaluate_switch(
    state: SwitchState,
    *,
    step: int,
    q_hat: float,
    contradiction_rate: float = 0.0,
    buried_signal: float = 0.0,
    acquisition_gain: float = 0.1,
    challenger_yield: float = 0.0,
    shared_bias: float = 0.0,
    policy_probs: dict[str, float] | None = None,
    cfg: SwitchConfig | None = None,
) -> SwitchState:
    """Possibly switch policy; mutates and returns ``state``."""
    cfg = cfg or SwitchConfig()
    state.credibility_trajectory.append(float(q_hat))
    if policy_probs:
        state.policy_probs = dict(policy_probs)

    if step - state.last_switch_step < cfg.min_steps_between_switches:
        return state

    cur = state.current_policy
    target = cur
    reason = ""

    # Triggers.
    if buried_signal >= cfg.buried_signal_high and cur in ("UHT", "UHT_EXPLORE", "HYBRID"):
        target, reason = "CHALLENGER", "buried_outsider_evidence"
    elif contradiction_rate >= cfg.contradiction_high and cur in ("UHT", "UHT_EXPLORE"):
        target, reason = "ROBUST_COMBINED", "reliable_contradiction_rise"
    elif shared_bias >= 0.6 and cur == "UHT":
        target, reason = "BROAD_STATIC", "shared_bias_suspicion"
    elif q_hat <= cfg.q_low - cfg.hysteresis and cur in ("UHT", "UHT_EXPLORE", "HYBRID"):
        target, reason = "CHALLENGER", "posterior_q_below_low"
    elif (
        q_hat >= cfg.q_high + cfg.hysteresis
        and cur in ("CHALLENGER", "ROBUST_COMBINED", "BROAD_STATIC", "NO_PRIOR")
        and contradiction_rate < 0.2
        and buried_signal < 0.3
    ):
        target, reason = "UHT", "posterior_q_above_high"
    elif acquisition_gain < cfg.gain_drop and cur == "UHT" and challenger_yield >= cfg.challenger_yield_high:
        target, reason = "CHALLENGER", "uht_gain_drop_challenger_yield"
    elif (
        cur == "CHALLENGER"
        and buried_signal < 0.2
        and contradiction_rate < 0.2
        and q_hat >= 0.55
    ):
        target, reason = "UHT", "challenger_risk_resolved"

    if target != cur and reason:
        state.events.append(
            SwitchEvent(
                step=step,
                from_policy=cur,
                to_policy=target,
                reason=reason,
                policy_probs=dict(state.policy_probs),
                credibility=float(q_hat),
                cost=0.05,
            )
        )
        state.current_policy = target
        state.last_switch_step = step
    return state


__all__ = [
    "SwitchConfig",
    "SwitchEvent",
    "SwitchState",
    "evaluate_switch",
]
