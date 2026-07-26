"""Lightweight safe fallbacks that limit worst-case loss when the gate is wrong.

Two distinct concepts live in this module and must not be conflated:

**Safety enforcement within UHT** (production). ``evaluate_safeguards`` returns
*action requests* — "probe an outsider", "do not stop yet", "run the final
challenger comparison". Those actions are executed *inside* the UHT acquisition
path by ``production_runner``. They spend budget and add evidence; they never
change which policy is executing. ``NON_ROUTING_ACTIONS`` lists them.

**Experimental policy switching** (research only). ``apply_experimental_escalation``
rewrites a policy name (e.g. UHT → HYBRID/CHALLENGER) in response to the same
action requests. That is a routing decision, it was never validated against
always-UHT on held-out data, and it is reachable only under
``ExecutionMode.EXPERIMENTAL_GATE``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Safeguard = Literal[
    "mandatory_outsider_probes",
    "min_challenger_coverage",
    "max_consecutive_uht",
    "periodic_sentinel",
    "window_expand_on_contradiction",
    "stop_prohibit_weak_evidence",
    "leave_one_prior_out_check",
    "randomized_audit",
    "final_adversarial_challenger",
]


@dataclass
class FallbackConfig:
    enabled: tuple[Safeguard, ...] = (
        "mandatory_outsider_probes",
        "min_challenger_coverage",
        "max_consecutive_uht",
        "periodic_sentinel",
        "window_expand_on_contradiction",
        "stop_prohibit_weak_evidence",
        "final_adversarial_challenger",
    )
    n_mandatory_outsider: int = 1
    min_challenger_per_insider: int = 1
    max_consecutive_uht: int = 6
    sentinel_every: int = 5
    contradiction_expand_threshold: float = 0.3
    min_evidence_fraction_to_stop: float = 0.2
    audit_probability: float = 0.05
    # Under high credibility, keep fallbacks lightweight.
    light_when_q_hat_above: float = 0.7


@dataclass
class FallbackState:
    consecutive_uht: int = 0
    outsider_probes_done: int = 0
    sentinel_done: int = 0
    challenger_done: dict[str, int] = field(default_factory=dict)
    window_expanded: bool = False
    final_challenger_done: bool = False
    audit_done: int = 0
    triggers: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "consecutive_uht": self.consecutive_uht,
            "outsider_probes_done": self.outsider_probes_done,
            "sentinel_done": self.sentinel_done,
            "challenger_done": dict(self.challenger_done),
            "window_expanded": self.window_expanded,
            "final_adversarial_challenger": self.final_challenger_done,
            "audit_done": self.audit_done,
            "triggers": list(self.triggers),
        }


def evaluate_safeguards(
    *,
    step: int,
    q_hat: float,
    contradiction_rate: float,
    evidence_fraction: float,
    remaining_budget: int,
    intending_stop: bool,
    cfg: FallbackConfig | None = None,
    state: FallbackState | None = None,
    rng_draw: float = 0.0,
) -> tuple[FallbackState, list[str]]:
    """Return updated state and list of active safeguard action requests."""
    cfg = cfg or FallbackConfig()
    state = state or FallbackState()
    actions: list[str] = []
    light = q_hat >= cfg.light_when_q_hat_above

    if "mandatory_outsider_probes" in cfg.enabled:
        need = 1 if light else cfg.n_mandatory_outsider
        if state.outsider_probes_done < need:
            actions.append("mandatory_outsider_probe")
            state.triggers.append({"step": step, "action": "mandatory_outsider_probe"})

    if "max_consecutive_uht" in cfg.enabled:
        lim = cfg.max_consecutive_uht + (4 if light else 0)
        if state.consecutive_uht >= lim:
            actions.append("force_non_local")
            state.triggers.append({"step": step, "action": "force_non_local"})

    if "periodic_sentinel" in cfg.enabled and not light:
        if step > 0 and step % cfg.sentinel_every == 0 and state.sentinel_done < 2:
            actions.append("sentinel")
            state.triggers.append({"step": step, "action": "sentinel"})

    if "window_expand_on_contradiction" in cfg.enabled:
        if contradiction_rate >= cfg.contradiction_expand_threshold and not state.window_expanded:
            actions.append("expand_window")
            state.window_expanded = True
            state.triggers.append({"step": step, "action": "expand_window"})

    if "stop_prohibit_weak_evidence" in cfg.enabled and intending_stop:
        if evidence_fraction < cfg.min_evidence_fraction_to_stop:
            actions.append("prohibit_stop")
            state.triggers.append({"step": step, "action": "prohibit_stop"})

    if "randomized_audit" in cfg.enabled and not light:
        if rng_draw < cfg.audit_probability:
            actions.append("audit_action")
            state.audit_done += 1
            state.triggers.append({"step": step, "action": "audit_action"})

    if "final_adversarial_challenger" in cfg.enabled and intending_stop:
        if remaining_budget > 0 and not state.final_challenger_done:
            actions.append("final_challenger")
            state.triggers.append({"step": step, "action": "final_challenger"})

    if "min_challenger_coverage" in cfg.enabled and not light:
        actions.append("ensure_challenger_coverage")

    if "leave_one_prior_out_check" in cfg.enabled and intending_stop and not light:
        actions.append("lopo_stability_check")

    return state, actions


#: Safeguard requests that are executed as actions *inside* the running policy.
#: None of these may change the executed policy name.
NON_ROUTING_ACTIONS: frozenset[str] = frozenset(
    {
        "mandatory_outsider_probe",
        "prohibit_stop",
        "final_challenger",
        "sentinel",
        "expand_window",
        "ensure_challenger_coverage",
        "lopo_stability_check",
        "audit_action",
    }
)


def production_safety_actions(actions: list[str]) -> list[str]:
    """Filter safeguard requests down to the non-routing subset.

    Production executes these actions inside the UHT path. Any request that is
    not in :data:`NON_ROUTING_ACTIONS` (currently only ``force_non_local``,
    which asks for a different action *kind*) is dropped, because acting on it
    would amount to changing the executed policy.
    """
    return [a for a in actions if a in NON_ROUTING_ACTIONS]


def apply_experimental_escalation(
    preferred_policy: str,
    active_actions: list[str],
    *,
    q_hat: float,
) -> str:
    """Rewrite the policy name in response to safeguard requests. EXPERIMENTAL.

    This is *policy routing*, not safety enforcement: it can turn UHT into
    HYBRID or CHALLENGER. Outcome F found no evidence that such escalation
    beats always-UHT, so it is reachable only under
    ``ExecutionMode.EXPERIMENTAL_GATE``. Production must instead execute the
    requested actions inside UHT (see :func:`production_safety_actions` and
    ``production_runner.run_production_uht``).
    """
    if not active_actions:
        return preferred_policy
    if "final_challenger" in active_actions or "mandatory_outsider_probe" in active_actions:
        if preferred_policy in ("UHT", "UHT_EXPLORE"):
            return "HYBRID" if q_hat >= 0.55 else "CHALLENGER"
    if "force_non_local" in active_actions and preferred_policy == "UHT":
        return "UHT_EXPLORE"
    if "prohibit_stop" in active_actions and preferred_policy == "STOP_OR_FALLBACK":
        return "BROAD_STATIC"
    return preferred_policy


def record_uht_step(state: FallbackState, used_uht_local: bool) -> FallbackState:
    if used_uht_local:
        state.consecutive_uht += 1
    else:
        state.consecutive_uht = 0
    return state


__all__ = [
    "Safeguard",
    "FallbackConfig",
    "FallbackState",
    "NON_ROUTING_ACTIONS",
    "evaluate_safeguards",
    "production_safety_actions",
    "apply_experimental_escalation",
    "record_uht_step",
]
