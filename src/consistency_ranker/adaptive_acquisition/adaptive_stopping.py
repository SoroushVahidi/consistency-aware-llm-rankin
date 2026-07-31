"""Top-k-aware stopping criteria (beyond budget exhaustion).

Every criterion returns a :class:`StopDecision` carrying whether to stop and a
machine-readable reason, so the engine can always report *why* it stopped.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState

StopCriterion = Literal[
    "budget",
    "stable_topk_membership",
    "stable_topk_order",
    "low_expected_value",
    "no_actionable_uncertainty",
    "provider_budget",
]


@dataclass
class StopDecision:
    stop: bool
    reason: str
    detail: dict | None = None


def budget_exhausted(state: "AcquisitionState") -> StopDecision:
    if state.remaining_budget <= 0:
        return StopDecision(True, "budget_exhausted", {"remaining_budget": state.remaining_budget})
    return StopDecision(False, "budget_remaining")


def stable_topk_membership(state: "AcquisitionState", *, delta: float = 0.1) -> StopDecision:
    r"""Stop when ``min_{i in Tk} P(i in Tk) >= 1-delta`` and
    ``max_{j not in Tk} P(j in Tk) <= delta``."""
    view = state.view()
    probs = view.topk_membership_prob
    if not probs:
        return StopDecision(False, "no_membership_estimates")
    ranking = view.ranking
    k = state.top_k
    topk = set(ranking[:k])
    if not topk:
        return StopDecision(False, "empty_topk")
    min_in = min((probs.get(d, 0.0) for d in topk), default=0.0)
    out = [d for d in state.candidate_ids if d not in topk]
    max_out = max((probs.get(d, 0.0) for d in out), default=0.0)
    ok = min_in >= (1 - delta) and max_out <= delta
    return StopDecision(
        ok,
        "stable_topk_membership" if ok else "topk_membership_unstable",
        {"min_in": min_in, "max_out": max_out, "delta": delta},
    )


def stable_topk_order(state: "AcquisitionState", *, threshold: float = 0.9) -> StopDecision:
    """Stop when the internal top-k ordering is stable across sampled extensions."""
    view = state.view()
    jac = view.stability.get("topk_jaccard_min")
    if jac is None:
        return StopDecision(False, "no_stability_estimate")
    ok = float(jac) >= threshold
    return StopDecision(
        ok,
        "stable_topk_order" if ok else "topk_order_unstable",
        {"topk_jaccard_min": jac, "threshold": threshold},
    )


def low_expected_value(best_value: float, *, eta: float) -> StopDecision:
    r"""Stop when ``max_a E[dS|a]/(C_a+eps) < eta``."""
    ok = best_value < eta
    return StopDecision(
        ok,
        "low_expected_value" if ok else "value_above_eta",
        {"best_value": best_value, "eta": eta},
    )


def no_actionable_uncertainty(
    state: "AcquisitionState",
    *,
    min_topk_impact: float = 0.05,
    topk_impacts: dict[str, float] | None = None,
) -> StopDecision:
    """Stop when all remaining uncertain pairs have negligible top-k impact."""
    if not topk_impacts:
        return StopDecision(False, "no_impact_estimates")
    max_impact = max(topk_impacts.values(), default=0.0)
    ok = max_impact < min_topk_impact
    return StopDecision(
        ok,
        "no_actionable_uncertainty" if ok else "actionable_uncertainty_remains",
        {"max_topk_impact": max_impact, "min_topk_impact": min_topk_impact},
    )


def provider_budget_exhausted(stopped_reason: str | None) -> StopDecision:
    if stopped_reason:
        return StopDecision(True, f"provider_{stopped_reason}", {"ceiling": stopped_reason})
    return StopDecision(False, "provider_budget_ok")


@dataclass
class StoppingPolicy:
    """Compose several stopping criteria; stop when the first fires."""

    criteria: tuple[StopCriterion, ...] = ("budget", "provider_budget")
    delta: float = 0.1
    order_threshold: float = 0.9
    eta: float = 0.01
    min_topk_impact: float = 0.05

    def decide(
        self,
        state: "AcquisitionState",
        *,
        best_value: float | None = None,
        topk_impacts: dict[str, float] | None = None,
        provider_stopped_reason: str | None = None,
    ) -> StopDecision:
        for c in self.criteria:
            if c == "budget":
                d = budget_exhausted(state)
            elif c == "provider_budget":
                d = provider_budget_exhausted(provider_stopped_reason)
            elif c == "stable_topk_membership":
                d = stable_topk_membership(state, delta=self.delta)
            elif c == "stable_topk_order":
                d = stable_topk_order(state, threshold=self.order_threshold)
            elif c == "low_expected_value":
                d = low_expected_value(best_value or 0.0, eta=self.eta)
            elif c == "no_actionable_uncertainty":
                d = no_actionable_uncertainty(
                    state, min_topk_impact=self.min_topk_impact, topk_impacts=topk_impacts
                )
            else:
                raise ValueError(f"Unknown stop criterion {c!r}")
            if d.stop:
                return d
        return StopDecision(False, "continue")


__all__ = [
    "StopCriterion",
    "StopDecision",
    "StoppingPolicy",
    "budget_exhausted",
    "stable_topk_membership",
    "stable_topk_order",
    "low_expected_value",
    "no_actionable_uncertainty",
    "provider_budget_exhausted",
]
