"""Active mining pipeline for repair-specific selector training data.

**Related "repair" packages** (repo hygiene Stage 5, 2026-07-30): this
package mines which (preserve, repair) action pairs are worth training a
selector on -- the oracle-headroom go/no-go gate here is designed for
exactly two independent fixed actions (preserve vs. canonical greedy
repair). ``reliability_repair`` repairs a graph given per-edge reliability
estimates. ``repair_frontier`` discovers a richer set of repair
*candidates* per query (a "best of many" framing, not two fixed actions).
``repair_diagnostic`` asks whether repair's rare benefits are predictable
from pre-repair graph features alone. See each package's own module
docstring for its specific research question.
"""

from .repair_pairs import REPAIR_PAIRS, RepairPair

__all__ = ["REPAIR_PAIRS", "RepairPair"]
