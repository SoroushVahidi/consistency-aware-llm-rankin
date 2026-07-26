"""Robust acquisition scoring objectives beyond ordinary stability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from consistency_ranker.adaptive_acquisition.pair_uncertainty import uncertainty
from consistency_ranker.adaptive_acquisition.ranking_impact import (
    ImpactContext,
    impact,
    topk_boundary_proximity,
)
from consistency_ranker.prior_robust.evidence_stability import EvidenceStability

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_actions import Action
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState

RobustScoreMode = Literal[
    "uncertainty_x_topk_impact",
    "uncertainty_x_topk_impact_epsilon",
    "evidence_stability_gain",
    "prior_dependence_reduction",
    "challenger_resolution",
    "bias_diagnostic",
    "robust_combined",
    "no_prior",
    "oracle_prior_quality",
]


@dataclass
class RobustScoreConfig:
    mode: RobustScoreMode = "robust_combined"
    alpha: float = 1.0  # evidence-stability
    beta: float = 1.0  # topk impact
    gamma: float = 1.0  # prior-dependence reduction proxy
    delta: float = 0.5  # bias diagnostic
    eps: float = 1e-9


def score_action(
    state: "AcquisitionState",
    action: "Action",
    ctx: ImpactContext,
    *,
    stability: EvidenceStability | None = None,
    cfg: RobustScoreConfig | None = None,
    is_challenger: bool = False,
    bias_value: float = 0.0,
    prior_quality: float = 0.5,
) -> tuple[float, dict[str, float]]:
    """Score one action under a robust objective."""
    cfg = cfg or RobustScoreConfig()
    if action.action_type == "NO_ACTION":
        return (float("-inf"), {})

    agg = state.aggregates.get(action.pair_id)
    u = uncertainty(agg, method="vote")
    h = impact(state, action.pair_id, ctx, method="topk_membership_sensitivity")
    hb = topk_boundary_proximity(state, action.pair_id, ctx)
    c = max(float(action.est_cost), cfg.eps)
    g = float(stability.g_prior) if stability is not None else 0.5
    s_ev = float(stability.s_evidence) if stability is not None else 0.0

    # Proxies (cheap; no full counterfactual re-simulation by default).
    # Evidence-stability gain ≈ uncertainty × (1 - evidence stability) × impact.
    d_sev = u * (1.0 - s_ev) * max(h, hb)
    # Prior-dependence reduction ≈ uncertainty × g_prior × impact
    # (resolving uncertain consequential pairs should shrink the gap).
    d_g = u * g * max(h, hb)
    d_chal = (1.0 if is_challenger else 0.0) * max(u, 0.5) * max(hb, 0.5)
    d_bias = bias_value * u

    mode = cfg.mode
    breakdown = {"U": u, "H": h, "Hb": hb, "G": g, "dSev": d_sev, "dG": d_g}

    if mode == "uncertainty_x_topk_impact":
        val = u * h
        # Prefer acquiring new pairs over re-querying the same relation unless
        # the pair is still highly uncertain after evidence.
        if action.action_type == "NEW_PAIR":
            val += 0.15
        elif action.action_type in (
            "REPEAT_SAME",
            "REVERSE_ORIENTATION",
            "ALTERNATE_PROMPT",
            "ALTERNATE_MODEL",
        ):
            if u < 0.55:
                val *= 0.25  # already fairly settled — deprioritize
    elif mode == "uncertainty_x_topk_impact_epsilon":
        val = u * h
        if action.action_type == "NEW_PAIR":
            val += 0.15
    elif mode == "evidence_stability_gain":
        val = d_sev
        if action.action_type == "NEW_PAIR":
            val += 0.1
    elif mode == "prior_dependence_reduction":
        val = d_g
        if action.action_type == "NEW_PAIR":
            val += 0.1
    elif mode == "challenger_resolution":
        val = d_chal if is_challenger else u * hb * 0.1
        if action.action_type == "NEW_PAIR":
            val += 0.05
    elif mode == "bias_diagnostic":
        val = d_bias if d_bias > 0 else u * 0.05
    elif mode == "no_prior":
        # Ignore prior-shaped impact; use extension sensitivity only.
        h2 = impact(state, action.pair_id, ctx, method="linear_extension_sensitivity")
        val = u * h2
        if action.action_type == "NEW_PAIR":
            val += 0.1
        breakdown["H_ext"] = h2
    elif mode == "oracle_prior_quality":
        # Diagnostic upper bound: if prior is good, behave like u×h; else challenger.
        if prior_quality >= 0.6:
            val = u * h
            if action.action_type == "NEW_PAIR":
                val += 0.15
        else:
            val = d_chal if is_challenger else d_g
            if action.action_type == "NEW_PAIR":
                val += 0.1
        breakdown["oracle_q"] = prior_quality
    else:  # robust_combined
        novelty = 0.15 if action.action_type == "NEW_PAIR" else 0.0
        re_pen = 0.0
        if action.action_type != "NEW_PAIR" and u < 0.55 and not is_challenger:
            re_pen = 0.7
        val = (
            (1.0 - re_pen)
            * (
                cfg.alpha * d_sev
                + cfg.beta * u * h
                + cfg.gamma * d_g
                + cfg.delta * d_bias
                + (0.75 * d_chal if is_challenger else 0.0)
                + novelty
            )
            / (c + cfg.eps)
        )
        breakdown.update({"C": c, "combined": val, "novelty": novelty})
        return float(val), breakdown

    return float(val), breakdown


__all__ = ["RobustScoreMode", "RobustScoreConfig", "score_action"]
