"""Provider / model escalation policy and model-action reliability.

Uses only judge identifiers supplied by the caller (see :class:`JudgeProfile`);
it never invents provider names or prices. The default cheap→expensive cascade
follows the task's policy:

1. one low-cost judgment;
2. accept if high-confidence and low-impact;
3. reverse orientation if orientation risk is high;
4. cross-prompt / cross-model if repeated uncertainty remains;
5. escalate to a strong model if the pair affects top-k;
6. otherwise abstain.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from consistency_ranker.adaptive_acquisition.acquisition_actions import (
    Action,
    JudgeProfile,
    generate_eligible_actions,
)
from consistency_ranker.adaptive_acquisition.pair_uncertainty import (
    orientation_uncertainty,
    reliability_uncertainty,
    uncertainty,
)

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState
    from consistency_ranker.adaptive_acquisition.ranking_impact import ImpactContext

ReliabilityModel = Literal["fixed", "empirical", "smoothed", "logistic"]


def synthetic_roster(
    *,
    n_models: int = 3,
    n_prompts: int = 2,
    weak_cost: float = 1.0,
    strong_cost: float = 5.0,
) -> list[JudgeProfile]:
    """Judge roster matching the synthetic judgment generator's naming.

    Providers ``prov_0..`` / models ``model_0..`` / prompts ``prompt_0..`` mirror
    :mod:`reliability_repair.synthetic_judgment_models`. A stronger, costlier
    escalation judge (``model_strong``) is added.
    """
    profiles: list[JudgeProfile] = []
    for m in range(n_models):
        for p in range(n_prompts):
            profiles.append(
                JudgeProfile(
                    name=f"prov_{m}/model_{m}/prompt_{p}",
                    provider=f"prov_{m}",
                    model=f"model_{m}",
                    prompt_version=f"prompt_{p}",
                    cost=weak_cost * (1.0 + 0.25 * m),
                    reliability=max(0.55, 0.85 - 0.05 * m),
                    strong=False,
                )
            )
    profiles.append(
        JudgeProfile(
            name="strong/model_strong/prompt_0",
            provider="strong",
            model="model_strong",
            prompt_version="prompt_0",
            cost=strong_cost,
            reliability=0.95,
            strong=True,
        )
    )
    return profiles


def roster_from_provider_specs(
    specs: list[dict],
) -> list[JudgeProfile]:
    """Build judge profiles from explicit provider specs (real deployments).

    Each spec dict must supply ``provider``, ``model`` and ``prompt_version``;
    optional ``cost``, ``reliability``, ``strong``, ``temperature``,
    ``max_tokens``. No defaults for model names are invented.
    """
    out = []
    for s in specs:
        out.append(
            JudgeProfile(
                name=s.get("name", f"{s['provider']}/{s['model']}/{s['prompt_version']}"),
                provider=str(s["provider"]),
                model=str(s["model"]),
                prompt_version=str(s["prompt_version"]),
                temperature=float(s.get("temperature", 0.0)),
                top_p=s.get("top_p"),
                max_tokens=int(s.get("max_tokens", 32)),
                cost=float(s.get("cost", 1.0)),
                reliability=float(s.get("reliability", 0.7)),
                strong=bool(s.get("strong", False)),
            )
        )
    return out


# ---- model-action reliability ---------------------------------------


@dataclass
class ActionReliabilityModel:
    """Expected reliability of a judge for a pair, with shrinkage on thin data."""

    method: ReliabilityModel = "smoothed"
    prior_strength: float = 4.0
    validation_reliability: dict[tuple[str, str, str], float] | None = None

    def expected(
        self,
        state: "AcquisitionState",
        action: Action,
        *,
        ctx: "ImpactContext | None" = None,
    ) -> float:
        if action.action_type == "NO_ACTION":
            return 0.0
        prior = float(action.expected_reliability)
        if self.method == "fixed":
            return prior

        key = (str(action.provider), str(action.model), str(action.prompt_version))
        if self.method == "empirical" and self.validation_reliability:
            emp = self.validation_reliability.get(key)
            if emp is not None:
                return float(max(0.0, min(1.0, emp)))
            return prior

        if self.method == "smoothed":
            # Observed self-consistency of this judge across all pairs so far,
            # shrunk toward the profile prior.
            obs, n = self._observed_consistency(state, action)
            if n <= 0:
                return prior
            w = n / (n + self.prior_strength)
            return float(max(0.0, min(1.0, w * obs + (1 - w) * prior)))

        if self.method == "logistic":
            return self._logistic(state, action, ctx)
        return prior

    def _observed_consistency(self, state: "AcquisitionState", action: Action) -> tuple[float, int]:
        """Fraction of this provider/model's directional calls that match the
        per-pair aggregate direction (a judgment-free self-consistency proxy)."""
        aggs = state.aggregates
        match = 0
        n = 0
        for e in state.evidence:
            if e.provider != action.provider or e.model != action.model or e.z == 0:
                continue
            agg = aggs.get(e.canonical_pair_id)
            if agg is None or agg.d == 0:
                continue
            n += 1
            if int(e.z) == int(agg.d):
                match += 1
        return (match / n if n else 0.0, n)

    def _logistic(
        self, state: "AcquisitionState", action: Action, ctx: "ImpactContext | None"
    ) -> float:
        obs, n = self._observed_consistency(state, action)
        prior = float(action.expected_reliability)
        s = -0.5 + 2.0 * prior + 1.5 * obs - 1.5 * math.exp(-0.5 * n)
        return float(1.0 / (1.0 + math.exp(-s)))


# ---- cheap→expensive cascade ----------------------------------------


@dataclass
class CascadeConfig:
    confidence_reliability: float = 0.75
    orientation_risk: float = 0.4
    repeat_uncertainty: float = 0.4
    topk_impact_threshold: float = 0.4
    allow_strong: bool = True


def choose_judge_for_pair(
    state: "AcquisitionState",
    pair_id: str,
    ctx: "ImpactContext",
    profiles: list[JudgeProfile],
    *,
    cascade: CascadeConfig | None = None,
    topk_impact: float | None = None,
) -> Action | None:
    """Return the next cascade action for ``pair_id`` (or ``None`` to abstain).

    Implements the cheap-first policy; returns an eligible, non-duplicate action.
    """
    cfg = cascade or CascadeConfig()
    strong = [p for p in profiles if p.strong]
    eligible = generate_eligible_actions(
        state, profiles, strong_profiles=strong, include_no_action=False
    )
    by_pair = [a for a in eligible if a.pair_id == pair_id]
    if not by_pair:
        return None

    agg = state.aggregates.get(pair_id)
    ev = state.evidence_for_pair(pair_id)

    def _first(action_type: str) -> Action | None:
        return next((a for a in by_pair if a.action_type == action_type), None)

    # (1) no evidence yet → one low-cost NEW_PAIR judgment.
    if not ev:
        return _first("NEW_PAIR") or by_pair[0]

    rel_unc = reliability_uncertainty(agg)
    orient_unc = orientation_uncertainty(agg)
    vote_unc = uncertainty(agg, method="vote")
    impact_val = topk_impact if topk_impact is not None else 0.0

    # (2) high-confidence & low-impact → accept (abstain from more calls).
    if rel_unc < (1 - cfg.confidence_reliability) and impact_val < cfg.topk_impact_threshold:
        return None

    # (3) orientation risk high → reverse orientation.
    if orient_unc >= cfg.orientation_risk:
        rev = _first("REVERSE_ORIENTATION")
        if rev is not None:
            return rev

    # (5) affects top-k and disputed → escalate to strong model.
    disputed_topk = impact_val >= cfg.topk_impact_threshold and vote_unc >= cfg.repeat_uncertainty
    if cfg.allow_strong and disputed_topk:
        esc = _first("STRONG_MODEL_ADJUDICATION")
        if esc is not None:
            return esc

    # (4) repeated uncertainty remains → cross-prompt / cross-model.
    if vote_unc >= cfg.repeat_uncertainty:
        for at in ("ALTERNATE_MODEL", "ALTERNATE_PROMPT", "REPEAT_SAME"):
            a = _first(at)
            if a is not None:
                return a

    # (6) otherwise abstain.
    return None


__all__ = [
    "ReliabilityModel",
    "ActionReliabilityModel",
    "CascadeConfig",
    "synthetic_roster",
    "roster_from_provider_specs",
    "choose_judge_for_pair",
]
