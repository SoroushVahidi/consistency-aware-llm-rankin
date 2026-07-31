"""Offline pilot: consistency-aware active preference acquisition for
budgeted reranking.

Uses already-collected, exhaustive real pairwise LLM judgments as an offline
oracle to ask: can an adaptive acquisition strategy recover most of
exhaustive-comparison retrieval quality while acquiring substantially fewer
judgments? See ``scripts/run_offline_active_acquisition_pilot.py`` for the
CLI driver and ``reports/offline_active_acquisition_pilot_*`` for results.

This module is deliberately small and does not reuse the heavier
``adaptive_acquisition`` package: that package models a repeated,
multi-provider, multi-action evidence world (vote/entropy/orientation/
cross-model uncertainty, provider escalation, synthetic judges) that does not
match this pilot's single-shot, exhaustive, already-cached oracle. Generic,
dataset-agnostic primitives are reused directly instead: graph construction
(``graph_construction.py``), ranking/consistency metrics (``evaluation.py``),
and paired statistical inference (``statistical_inference.py``).
"""

from consistency_ranker.active_acquisition.oracle import (
    QueryOracle,
    load_scidocs_pairwise_oracle,
)
from consistency_ranker.active_acquisition.simulate import (
    Checkpoint,
    reference_rankings,
    simulate_trajectory,
)
from consistency_ranker.active_acquisition.strategies import (
    ALGORITHMS,
    PHASE7_ABLATIONS,
    REQUIRED_PHASE3_STRATEGIES,
    STRATEGY_TO_ALGORITHM,
)

__all__ = [
    "QueryOracle",
    "load_scidocs_pairwise_oracle",
    "Checkpoint",
    "reference_rankings",
    "simulate_trajectory",
    "ALGORITHMS",
    "STRATEGY_TO_ALGORITHM",
    "REQUIRED_PHASE3_STRATEGIES",
    "PHASE7_ABLATIONS",
]
