"""Policy utility, asymmetric gate losses, and outcome summaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class UtilityWeights:
    """Configurable weights for expected utility.

    U = Q_rank - lambda_c * C - lambda_r * R_catastrophic
    """

    lambda_c: float = 0.01
    lambda_r: float = 0.5
    # Asymmetric gate-error costs (relative).
    false_trust: float = 2.0
    false_distrust: float = 0.5
    # Quality metric preference when aggregating.
    quality_metric: str = "topk_jaccard"  # or kendall_tau


@dataclass
class PolicyOutcome:
    policy: str
    kendall_tau: float | None = None
    topk_jaccard: float | None = None
    pairwise_accuracy: float | None = None
    n_calls: int = 0
    probe_calls: int = 0
    exploration_calls: int = 0
    total_cost: float = 0.0
    runtime_s: float = 0.0
    catastrophic: bool = False  # e.g. buried outsider missed / top-k empty of truth
    buried_recovered: bool | None = None
    stable_but_wrong: bool = False
    confidently_wrong: bool = False
    stopping_reason: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def quality(self, metric: str = "topk_jaccard") -> float:
        if metric == "kendall_tau":
            return float(self.kendall_tau if self.kendall_tau is not None else 0.0)
        return float(self.topk_jaccard if self.topk_jaccard is not None else 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy": self.policy,
            "kendall_tau": self.kendall_tau,
            "topk_jaccard": self.topk_jaccard,
            "pairwise_accuracy": self.pairwise_accuracy,
            "n_calls": self.n_calls,
            "probe_calls": self.probe_calls,
            "exploration_calls": self.exploration_calls,
            "total_cost": self.total_cost,
            "runtime_s": self.runtime_s,
            "catastrophic": self.catastrophic,
            "buried_recovered": self.buried_recovered,
            "stable_but_wrong": self.stable_but_wrong,
            "confidently_wrong": self.confidently_wrong,
            "stopping_reason": self.stopping_reason,
            "extra": dict(self.extra),
        }


def compute_utility(
    outcome: PolicyOutcome,
    weights: UtilityWeights | None = None,
) -> float:
    w = weights or UtilityWeights()
    q = outcome.quality(w.quality_metric)
    c = float(outcome.total_cost if outcome.total_cost else outcome.n_calls)
    r = 1.0 if outcome.catastrophic else 0.0
    if outcome.stable_but_wrong:
        r = max(r, 0.5)
    return float(q - w.lambda_c * c - w.lambda_r * r)


def gate_asymmetric_loss(
    *,
    predicted_trust: bool,
    true_uht_better: bool,
    weights: UtilityWeights | None = None,
    catastrophic_if_uht: bool = False,
) -> float:
    """Cost of a binary trust/distrust decision.

    False trust (trust prior / UHT when UHT is worse) is penalized more heavily,
    especially when UHT would be catastrophic.
    """
    w = weights or UtilityWeights()
    if predicted_trust and not true_uht_better:
        base = w.false_trust
        if catastrophic_if_uht:
            base *= 2.0
        return float(base)
    if (not predicted_trust) and true_uht_better:
        return float(w.false_distrust)
    return 0.0


def expected_utility_from_probs(
    policy_utils: dict[str, float],
    policy_probs: dict[str, float],
) -> float:
    return float(sum(policy_probs.get(p, 0.0) * u for p, u in policy_utils.items()))


def regret_vs_oracle(
    chosen_utility: float,
    oracle_utility: float,
) -> float:
    return float(max(0.0, oracle_utility - chosen_utility))


__all__ = [
    "UtilityWeights",
    "PolicyOutcome",
    "compute_utility",
    "gate_asymmetric_loss",
    "expected_utility_from_probs",
    "regret_vs_oracle",
]
