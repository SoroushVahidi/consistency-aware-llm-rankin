"""
Calibrated query-level policy selection with safe fallback.

Chooses among acquisition policies using observable features, diagnostic
probes, calibrated prior-quality / regret models, selective abstention,
soft mixtures, online switching, and lightweight catastrophic safeguards.
Builds on prior_robust + adaptive_acquisition; never uses qrels online.

**Production vs research.** After Outcome F the production operating point is
always-UHT plus a non-routing safety floor: see
:func:`production_runner.run_production_uht` and
:data:`production_config.PRODUCTION_OPERATING_POINT`. Every other gate in this
package (hard, calibrated, selective, soft, staged, switching, hybrid,
challenger) is experimental and requires
:attr:`execution_mode.ExecutionMode.EXPERIMENTAL_GATE` to be requested
explicitly. Defaults resolve to production.
"""

from consistency_ranker.policy_selection.diagnostic_probes import (
    ProbeConfig,
    ProbeDesign,
    run_diagnostic_probes,
    select_probe_pairs,
)
from consistency_ranker.policy_selection.execution_mode import (
    EXECUTION_MODE_CHOICES,
    ExecutionMode,
    resolve_execution_mode,
)
from consistency_ranker.policy_selection.gate_features import (
    FEATURE_SCHEMA_VERSION,
    FeatureBundle,
    extract_features,
    features_to_vector,
)
from consistency_ranker.policy_selection.policy_benchmark import (
    PolicyBenchmarkConfig,
    build_synthetic_population,
    evaluate_policies_on_query,
    nested_split_regimes,
)
from consistency_ranker.policy_selection.policy_calibration import (
    CalibratedModel,
    CalibrationReport,
    fit_calibrated_gate,
    predict_proba,
)
from consistency_ranker.policy_selection.policy_gate import (
    GATE_MODE_CHOICES,
    PRODUCTION_GATE_MODE,
    GateDecision,
    GateMode,
    PolicyName,
    PolicySelector,
    UtilityWeights,
    resolve_gate_mode,
    select_policy,
)
from consistency_ranker.policy_selection.policy_mixture import (
    MixtureConfig,
    hybrid_score,
    split_budget,
)
from consistency_ranker.policy_selection.policy_regret import (
    RegretPrediction,
    predict_policy_regret,
)
from consistency_ranker.policy_selection.policy_switching import (
    SwitchConfig,
    SwitchEvent,
    SwitchState,
    evaluate_switch,
)
from consistency_ranker.policy_selection.policy_utility import (
    PolicyOutcome,
    compute_utility,
    gate_asymmetric_loss,
)
from consistency_ranker.policy_selection.production_config import (
    PRODUCTION_OPERATING_POINT,
    PRODUCTION_PRIMARY_POLICY,
    PRODUCTION_SAFETY_FLOOR,
    ProductionPolicyConfig,
)
from consistency_ranker.policy_selection.production_runner import (
    ProductionRunResult,
    ProductionSafeguards,
    SafeguardLog,
    run_production_uht,
)
from consistency_ranker.policy_selection.risk_control import (
    RiskControlConfig,
    RiskControlResult,
    acceptable_policy_set,
)
from consistency_ranker.policy_selection.safe_fallback import (
    NON_ROUTING_ACTIONS,
    FallbackConfig,
    FallbackState,
    apply_experimental_escalation,
    evaluate_safeguards,
    production_safety_actions,
)

__all__ = [
    "FEATURE_SCHEMA_VERSION",
    "FeatureBundle",
    "extract_features",
    "features_to_vector",
    "ProbeConfig",
    "ProbeDesign",
    "run_diagnostic_probes",
    "select_probe_pairs",
    "PolicyBenchmarkConfig",
    "build_synthetic_population",
    "evaluate_policies_on_query",
    "nested_split_regimes",
    "CalibratedModel",
    "CalibrationReport",
    "fit_calibrated_gate",
    "predict_proba",
    "GateDecision",
    "GateMode",
    "GATE_MODE_CHOICES",
    "PRODUCTION_GATE_MODE",
    "resolve_gate_mode",
    "PolicyName",
    "PolicySelector",
    "UtilityWeights",
    "select_policy",
    "ExecutionMode",
    "EXECUTION_MODE_CHOICES",
    "resolve_execution_mode",
    "ProductionPolicyConfig",
    "PRODUCTION_OPERATING_POINT",
    "PRODUCTION_PRIMARY_POLICY",
    "PRODUCTION_SAFETY_FLOOR",
    "ProductionRunResult",
    "ProductionSafeguards",
    "SafeguardLog",
    "run_production_uht",
    "MixtureConfig",
    "hybrid_score",
    "split_budget",
    "RegretPrediction",
    "predict_policy_regret",
    "SwitchConfig",
    "SwitchEvent",
    "SwitchState",
    "evaluate_switch",
    "PolicyOutcome",
    "compute_utility",
    "gate_asymmetric_loss",
    "RiskControlConfig",
    "RiskControlResult",
    "acceptable_policy_set",
    "FallbackConfig",
    "FallbackState",
    "NON_ROUTING_ACTIONS",
    "apply_experimental_escalation",
    "production_safety_actions",
    "evaluate_safeguards",
]
