"""Robust stopping: ordinary stability alone cannot terminate acquisition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from consistency_ranker.adaptive_acquisition.adaptive_stopping import (
    budget_exhausted,
    provider_budget_exhausted,
)
from consistency_ranker.prior_robust.exploration_guards import (
    ExplorationConfig,
    ExplorationState,
    exploration_complete,
)
from consistency_ranker.prior_robust.prior_dependence import topk_evidence_coverage

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState
    from consistency_ranker.prior_robust.evidence_stability import EvidenceStability


@dataclass
class RobustStopConfig:
    min_evidence_fraction: float = 0.35
    max_g_prior: float = 0.25
    require_exploration: bool = True
    require_challenger_coverage: bool = True
    min_effective_sources: float = 1.0
    max_hc_contradiction: float = 0.4
    delta_membership: float = 0.1


@dataclass
class RobustStopResult:
    stop: bool
    reason: str
    checks: dict[str, bool] = field(default_factory=dict)
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stop": self.stop,
            "reason": self.reason,
            "checks": dict(self.checks),
            "detail": dict(self.detail),
        }


def evaluate_robust_stop(
    state: "AcquisitionState",
    *,
    stability: "EvidenceStability",
    explor_cfg: ExplorationConfig,
    explor: ExplorationState,
    cfg: RobustStopConfig | None = None,
    challenger_coverage_ok: bool = False,
    n_effective_judges: float = 1.0,
    hc_contradiction: float | None = None,
    provider_stopped_reason: str | None = None,
) -> RobustStopResult:
    """Stop only when budget OR all robustness checks pass."""
    cfg = cfg or RobustStopConfig()
    checks: dict[str, bool] = {}
    detail: dict[str, Any] = {}

    # Hard stops: budget / provider ceiling.
    b = budget_exhausted(state)
    if b.stop:
        return RobustStopResult(True, b.reason, {"budget": True}, b.detail or {})
    p = provider_budget_exhausted(provider_stopped_reason)
    if p.stop:
        return RobustStopResult(True, p.reason, {"provider_budget": True}, p.detail or {})

    cov = topk_evidence_coverage(state)
    checks["evidence_threshold"] = cov["fraction_acquired"] >= cfg.min_evidence_fraction
    detail["fraction_acquired"] = cov["fraction_acquired"]

    checks["prior_dependence"] = stability.g_prior <= cfg.max_g_prior
    detail["g_prior"] = stability.g_prior
    detail["s_total"] = stability.s_total
    detail["s_evidence"] = stability.s_evidence

    if cfg.require_exploration:
        checks["exploration_complete"] = exploration_complete(state, explor_cfg, explor)
    else:
        checks["exploration_complete"] = True

    if cfg.require_challenger_coverage:
        checks["challenger_coverage"] = bool(challenger_coverage_ok)
    else:
        checks["challenger_coverage"] = True

    checks["cross_source_diversity"] = n_effective_judges >= cfg.min_effective_sources
    detail["n_effective_judges"] = n_effective_judges

    if hc_contradiction is not None:
        checks["contradiction_ceiling"] = hc_contradiction <= cfg.max_hc_contradiction
        detail["hc_contradiction"] = hc_contradiction
    else:
        checks["contradiction_ceiling"] = True

    # Ordinary stability (membership) — necessary but not sufficient.
    ranking = state.ranking
    k = state.top_k
    topk = ranking[:k]
    probs = stability.topk_membership_evidence  # evidence-oriented membership
    if topk and probs:
        min_in = min(probs.get(d, 0.0) for d in topk)
        out = [d for d in state.candidate_ids if d not in set(topk)]
        max_out = max((probs.get(d, 0.0) for d in out), default=0.0)
        checks["evidence_topk_stable"] = (
            min_in >= (1 - cfg.delta_membership) and max_out <= cfg.delta_membership
        )
        detail["min_in_evidence"] = min_in
        detail["max_out_evidence"] = max_out
    else:
        checks["evidence_topk_stable"] = False

    failed = [name for name, ok in checks.items() if not ok]
    if not failed:
        return RobustStopResult(True, "robust_stop_all_checks_passed", checks, detail)
    return RobustStopResult(False, "continue:" + ",".join(failed), checks, detail)


__all__ = [
    "RobustStopConfig",
    "RobustStopResult",
    "evaluate_robust_stop",
]
