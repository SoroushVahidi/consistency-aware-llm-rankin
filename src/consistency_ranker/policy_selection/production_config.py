"""The single authoritative production operating point (post Outcome F).

Outcome F concluded that synthetic calibration is not sufficient to freeze a
learned production policy gate: on held-out burial-heavy regimes no learned,
hard, calibrated, selective, soft or staged gate beat always-UHT, while an
oracle query-specific selector did. The interim production decision is
therefore *always UHT plus a lightweight, non-routing safety floor*.

Every production default lives here so that no module, CLI flag, or serialized
config can quietly disagree with another. Nothing in this module can select a
policy other than UHT.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "PRODUCTION_PRIMARY_POLICY",
    "PRODUCTION_SAFETY_FLOOR",
    "PRODUCTION_PROBE_DESIGN",
    "PRODUCTION_PROBE_BUDGET",
    "ProductionPolicyConfig",
    "PRODUCTION_OPERATING_POINT",
]

#: The only policy production may execute.
PRODUCTION_PRIMARY_POLICY = "UHT"

#: Fraction of the acquisition budget reserved for safety actions inside the
#: UHT path (mandatory outsider probe, blocked-stop evidence, final challenger).
#: This is a *budget* floor, not a routing weight.
PRODUCTION_SAFETY_FLOOR = 0.15

#: Fixed diagnostic probe. Observational in production; never routes.
PRODUCTION_PROBE_DESIGN = "mixed_diagnostic"
PRODUCTION_PROBE_BUDGET = 3


@dataclass(frozen=True)
class ProductionPolicyConfig:
    """Frozen interim production operating point.

    The dataclass is frozen so a caller cannot mutate the shared constant.
    ``ExecutionMode.PRODUCTION_UHT`` runs exactly this configuration.
    """

    primary_policy: str = PRODUCTION_PRIMARY_POLICY
    safety_floor: float = PRODUCTION_SAFETY_FLOOR
    probe_design: str = PRODUCTION_PROBE_DESIGN
    probe_budget: int = PRODUCTION_PROBE_BUDGET
    #: Mandatory top-k-insider vs outsider probe before the main UHT run.
    require_outsider_probe: bool = True
    #: Stopping on thin evidence is prohibited while budget remains.
    prohibit_weak_evidence_stop: bool = True
    #: Minimum evidence fraction required before a stop is allowed.
    min_evidence_fraction_to_stop: float = 0.2
    #: A final adversarial challenger comparison is evaluated before returning.
    require_final_challenger: bool = True
    #: Diagnostic probe + feature recording. Never affects the executed policy.
    record_diagnostics: bool = False

    def __post_init__(self) -> None:
        if self.primary_policy != PRODUCTION_PRIMARY_POLICY:
            raise ValueError(
                "ProductionPolicyConfig.primary_policy is locked to "
                f"{PRODUCTION_PRIMARY_POLICY!r}; got {self.primary_policy!r}. "
                "Use ExecutionMode.EXPERIMENTAL_GATE for other policies."
            )
        if not 0.0 <= self.safety_floor <= 1.0:
            raise ValueError(f"safety_floor must be in [0, 1]; got {self.safety_floor!r}")
        if self.probe_budget < 0:
            raise ValueError(f"probe_budget must be >= 0; got {self.probe_budget!r}")

    def reserved_safety_calls(self, budget: int) -> int:
        """Budget reserved for in-UHT safety actions.

        The safety floor is a *budget reservation*: it guarantees that a fixed
        share of the budget remains available for the outsider probe, extra
        evidence when a weak-evidence stop is blocked, and the final challenger
        check. It never mixes or replaces the executed policy.
        """
        if budget <= 0:
            return 0
        needed = int(self.require_outsider_probe) + int(self.require_final_challenger)
        if needed == 0 and self.safety_floor <= 0.0:
            return 0
        floor_calls = int(round(self.safety_floor * budget + 0.5 - 1e-9))
        return max(needed, min(budget, max(floor_calls, needed)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_policy": self.primary_policy,
            "safety_floor": self.safety_floor,
            "probe_design": self.probe_design,
            "probe_budget": self.probe_budget,
            "require_outsider_probe": self.require_outsider_probe,
            "prohibit_weak_evidence_stop": self.prohibit_weak_evidence_stop,
            "min_evidence_fraction_to_stop": self.min_evidence_fraction_to_stop,
            "require_final_challenger": self.require_final_challenger,
            "record_diagnostics": self.record_diagnostics,
        }


#: Shared immutable instance. Import this rather than re-declaring defaults.
PRODUCTION_OPERATING_POINT = ProductionPolicyConfig()
