"""Frozen multi-provider counterfactual micro-pilot contracts (v1).

No live provider calls. Collection is a separate, explicitly gated task.
"""

from __future__ import annotations

from consistency_ranker.counterfactual_pilot.panel import (
    PANEL_VERSION,
    frozen_panel,
    require_panel_version,
)
from consistency_ranker.counterfactual_pilot.presentation import (
    map_displayed_preference_to_document,
    presentation_orders,
)
from consistency_ranker.counterfactual_pilot.schema import (
    JUDGMENT_SCHEMA_VERSION,
    validate_judgment,
)

__all__ = [
    "PANEL_VERSION",
    "JUDGMENT_SCHEMA_VERSION",
    "frozen_panel",
    "require_panel_version",
    "validate_judgment",
    "map_displayed_preference_to_document",
    "presentation_orders",
]
