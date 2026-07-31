"""Incumbent-protected SCC-local repair and the repair-frontier evaluation.

See ``docs/`` (or the module docstrings in this package) for the
discovery-vs-selection framing: does a richer candidate set contain
beneficial rankings the original single-method repair missed (discovery),
and can a label-free rule pick them out on held-out queries (selection)?

**Related "repair" packages** (repo hygiene Stage 5, 2026-07-30): this
package discovers a *richer set of repair candidates* per query (a "best
of many" framing). ``repair_diagnostic`` asks whether repair's rare
benefits are predictable from pre-repair graph features alone (and imports
this package's ``edge_confidence`` -- the only cross-dependency among these
four packages). ``repair_selector_mining`` mines which (preserve, repair)
action pairs are worth training a selector on -- two fixed actions, not a
candidate set. ``reliability_repair`` repairs a graph given per-edge
reliability estimates. See each package's own module docstring for its
specific research question.
"""

from .acceptance import accept_candidate, candidate_objective
from .discovery import (
    DiscoveryResult,
    QueryFrontierOutcome,
    compute_discovery_result,
    evaluate_query_frontier,
    frontier_records,
    localization_summary,
)
from .disposition import classify_edge_dispositions
from .edge_confidence import compute_edge_confidence
from .frontier import build_repair_frontier
from .protection_rules import EdgeProtectionRule, annotate_removal_costs, protected_edges
from .reinsertion import reinsert_scc_orderings
from .selection import DEPLOYABLE_SELECTORS, evaluate_selection
from .types import EdgeConfidence, FrontierCandidate, LocalCandidate

__all__ = [
    "accept_candidate",
    "candidate_objective",
    "classify_edge_dispositions",
    "DiscoveryResult",
    "QueryFrontierOutcome",
    "compute_discovery_result",
    "evaluate_query_frontier",
    "frontier_records",
    "localization_summary",
    "compute_edge_confidence",
    "build_repair_frontier",
    "EdgeProtectionRule",
    "annotate_removal_costs",
    "protected_edges",
    "reinsert_scc_orderings",
    "DEPLOYABLE_SELECTORS",
    "evaluate_selection",
    "EdgeConfidence",
    "FrontierCandidate",
    "LocalCandidate",
]
