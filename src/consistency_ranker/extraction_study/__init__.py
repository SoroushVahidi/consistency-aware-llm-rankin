"""Bounded study: does preference-graph EXTRACTION method choice (not
repair) explain the ranking gains observed in the repair-frontier program?
Same graphs, same relevance labels, only the extraction step varies.
"""

from .decision import MEANINGFUL_THRESHOLD, Decision, DecisionResult, decide
from .evaluation import (
    ExtractorStats,
    QueryGraphResult,
    breakdown_by,
    compute_extractor_stats,
    deltas_for,
    evaluate_unit_graph,
    full_breakdowns,
    outlier_sensitivity,
)
from .extractors import EXTRACTORS, INCUMBENT_NAME, Extractor, extract_all
from .selection import (
    best_single_fixed_extractor,
    build_predictive_rows,
    evaluate_predictive_selector,
    evaluate_selection,
    oracle_ndcgs,
)

__all__ = [
    "Decision",
    "DecisionResult",
    "MEANINGFUL_THRESHOLD",
    "decide",
    "ExtractorStats",
    "QueryGraphResult",
    "breakdown_by",
    "compute_extractor_stats",
    "deltas_for",
    "evaluate_unit_graph",
    "full_breakdowns",
    "outlier_sensitivity",
    "EXTRACTORS",
    "INCUMBENT_NAME",
    "Extractor",
    "extract_all",
    "best_single_fixed_extractor",
    "build_predictive_rows",
    "evaluate_predictive_selector",
    "evaluate_selection",
    "oracle_ndcgs",
]
