"""Bounded diagnostic study: are the rare benefits of consistency repair
predictable from observable (pre-repair) graph properties, or are they
isolated and non-deployable?

**Related "repair" packages** (repo hygiene Stage 5, 2026-07-30): this
package asks whether repair's benefit is *predictable* from pre-repair
features. ``repair_frontier`` discovers a richer set of repair
*candidates* per query (this package imports its ``edge_confidence``, the
only cross-dependency among these four packages). ``repair_selector_mining``
mines which (preserve, repair) action pairs are worth training a selector
on. ``reliability_repair`` repairs a graph given per-edge reliability
estimates. See each package's own module docstring for its specific
research question.
"""

from .association import (
    ALL_FEATURE_NAMES,
    FeatureAssociation,
    compute_feature_associations,
    feature_stability_by_subgroup,
    full_stability_report,
    outcome_group_stats,
    outlier_sensitivity,
    overall_delta_ci,
)
from .decision import MEANINGFUL_THRESHOLD, Decision, DecisionResult, best_real_model, decide
from .features import (
    POST_REPAIR_FEATURE_NAMES,
    PRE_REPAIR_FEATURE_NAMES,
    PostRepairFeatures,
    PreRepairFeatures,
    compute_post_repair_features,
    compute_pre_repair_features,
)
from .outcomes import Outcome, QueryGraphDiagnostic, evaluate_repair_outcome
from .prediction import (
    baseline_policies,
    build_records,
    compute_headroom_gate,
    evaluate_predictors,
    subgroup_stability,
)

__all__ = [
    "ALL_FEATURE_NAMES",
    "FeatureAssociation",
    "compute_feature_associations",
    "feature_stability_by_subgroup",
    "full_stability_report",
    "outcome_group_stats",
    "outlier_sensitivity",
    "overall_delta_ci",
    "Decision",
    "DecisionResult",
    "MEANINGFUL_THRESHOLD",
    "best_real_model",
    "decide",
    "POST_REPAIR_FEATURE_NAMES",
    "PRE_REPAIR_FEATURE_NAMES",
    "PostRepairFeatures",
    "PreRepairFeatures",
    "compute_post_repair_features",
    "compute_pre_repair_features",
    "Outcome",
    "QueryGraphDiagnostic",
    "evaluate_repair_outcome",
    "baseline_policies",
    "build_records",
    "compute_headroom_gate",
    "evaluate_predictors",
    "subgroup_stability",
]
