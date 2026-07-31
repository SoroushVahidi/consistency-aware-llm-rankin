"""
Prior-robust, bias-aware adaptive ranking.

Safeguards against confident anchoring to a bad prior and stable-but-wrong
early stopping. Builds on adaptive_acquisition + reliability_repair.
"""

from consistency_ranker.prior_robust.adaptive_prior import (
    AdaptivePriorState,
    update_lambda,
)
from consistency_ranker.prior_robust.adversarial_judges import (
    AdversarialScenario,
    make_adversarial_world,
)
from consistency_ranker.prior_robust.engine import (
    RobustAcquisitionResult,
    RobustEngineConfig,
    make_initial_robust_state,
    run_robust_acquisition,
)
from consistency_ranker.prior_robust.evidence_stability import (
    EvidenceStability,
    compute_evidence_stability,
)
from consistency_ranker.prior_robust.prior_quality import (
    PriorQualityEstimate,
    estimate_prior_quality,
)
from consistency_ranker.prior_robust.robustness_report import RobustnessReport

__all__ = [
    "AdaptivePriorState",
    "update_lambda",
    "AdversarialScenario",
    "make_adversarial_world",
    "RobustAcquisitionResult",
    "RobustEngineConfig",
    "make_initial_robust_state",
    "run_robust_acquisition",
    "EvidenceStability",
    "compute_evidence_stability",
    "PriorQualityEstimate",
    "estimate_prior_quality",
    "RobustnessReport",
]
