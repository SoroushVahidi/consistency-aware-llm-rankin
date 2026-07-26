"""Empirical robustness reports (not formal mathematical certificates)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

RobustnessCategory = Literal[
    "ROBUST",
    "PRIOR_DEPENDENT",
    "UNDEREXPLORED",
    "JUDGE_DISAGREEMENT",
    "BIAS_SUSPECTED",
    "AMBIGUOUS",
    "BUDGET_EXHAUSTED",
]


@dataclass
class RobustnessReport:
    query_id: str
    category: RobustnessCategory
    topk: list[str]
    topk_membership: dict[str, float]
    evidence_only_stability: float
    prior_dependence_gap: float
    prior_credibility: float
    lambda_q: float
    n_exploration_probes: int
    challenger_coverage_ok: bool
    provider_diversity: int
    prompt_diversity: int
    orientation_consistency: float
    max_scc_size: int
    ambiguity_bucket: str | None
    perturbation_topk_jaccard: float | None
    unresolved_consequential: int
    stopping_reason: str
    checks: dict[str, bool] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "category": self.category,
            "topk": list(self.topk),
            "topk_membership": dict(self.topk_membership),
            "evidence_only_stability": self.evidence_only_stability,
            "prior_dependence_gap": self.prior_dependence_gap,
            "prior_credibility": self.prior_credibility,
            "lambda_q": self.lambda_q,
            "n_exploration_probes": self.n_exploration_probes,
            "challenger_coverage_ok": self.challenger_coverage_ok,
            "provider_diversity": self.provider_diversity,
            "prompt_diversity": self.prompt_diversity,
            "orientation_consistency": self.orientation_consistency,
            "max_scc_size": self.max_scc_size,
            "ambiguity_bucket": self.ambiguity_bucket,
            "perturbation_topk_jaccard": self.perturbation_topk_jaccard,
            "unresolved_consequential": self.unresolved_consequential,
            "stopping_reason": self.stopping_reason,
            "checks": dict(self.checks),
            "notes": list(self.notes),
            "kind": "empirical_robustness_report",
        }


def categorize(
    *,
    stopping_reason: str,
    g_prior: float,
    s_evidence: float,
    exploration_ok: bool,
    bias_suspected: list[str],
    ambiguity_bucket: str | None,
    judge_disagreement: float,
    max_g_prior: float = 0.25,
) -> RobustnessCategory:
    if stopping_reason.startswith("budget") or "budget" in stopping_reason:
        if g_prior > max_g_prior or not exploration_ok:
            # Budget ran out while still fragile.
            return "BUDGET_EXHAUSTED"
    if bias_suspected:
        return "BIAS_SUSPECTED"
    if judge_disagreement >= 0.4:
        return "JUDGE_DISAGREEMENT"
    if not exploration_ok:
        return "UNDEREXPLORED"
    if g_prior > max_g_prior:
        return "PRIOR_DEPENDENT"
    if ambiguity_bucket == "highly_ambiguous" and s_evidence < 0.8:
        return "AMBIGUOUS"
    if stopping_reason == "robust_stop_all_checks_passed" and g_prior <= max_g_prior:
        return "ROBUST"
    if g_prior > max_g_prior:
        return "PRIOR_DEPENDENT"
    return "AMBIGUOUS"


__all__ = ["RobustnessCategory", "RobustnessReport", "categorize"]
