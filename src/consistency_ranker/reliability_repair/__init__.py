"""
Reliability-aware pairwise evidence, selective graphs, and cycle repair.

Stages (ablate independently):
1. normalize evidence → z ∈ {-1,0,+1}
2. aggregate per unordered pair
3. estimate direction vs reliability separately
4. abstain on weak evidence
5. assign importance and removal costs
6. resolve local contradictions
7. reliability-aware MWFAS
8. optional prior-regularized ordering
9. prior-priority topological extraction + stability diagnostics

**Related "repair" packages** (repo hygiene Stage 5, 2026-07-30 -- added to
help navigate four distinct packages that all use "repair" in their name):
this package repairs a graph *given* per-edge reliability estimates.
``repair_selector_mining`` mines which (preserve, repair) action pairs are
worth training a selector on. ``repair_frontier`` discovers a richer set of
repair *candidates* per query and asks whether a label-free rule can select
among them. ``repair_diagnostic`` asks whether repair's rare benefits are
*predictable* from pre-repair graph features alone. See each package's own
module docstring for its specific research question.
"""

from consistency_ranker.reliability_repair.pair_evidence import (
    NormalizedEvidence,
    canonical_pair_id,
    normalize_judgment_record,
)
from consistency_ranker.reliability_repair.pipeline import (
    ReliabilityRepairConfig,
    run_reliability_pipeline,
)

__all__ = [
    "NormalizedEvidence",
    "canonical_pair_id",
    "normalize_judgment_record",
    "ReliabilityRepairConfig",
    "run_reliability_pipeline",
]
