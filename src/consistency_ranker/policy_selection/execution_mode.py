"""Explicit execution modes separating production routing from research routing.

Three modes exist and no others:

``production_uht``
    The interim production operating point frozen after Outcome F. The executed
    acquisition policy is always UHT. Approved safeguards run inside the UHT
    path (they may add evidence or block premature stopping) but they can never
    change the executed policy. Learned gates cannot be loaded or activated.

``diagnostic``
    Same executed policy as production (UHT), but the fixed ``mixed_diagnostic``
    probe runs and gate features / calibrated predictions are recorded. The
    recorded recommendation is observational only; it never changes routing.

``experimental_gate``
    Research mode. Hard, calibrated, selective, soft, staged, switching, hybrid
    and challenger routing are permitted. Must always be requested explicitly:
    no default constructor, omitted CLI flag, environment variable, or missing
    configuration value may resolve to this mode.

Resolution fails closed: ``None`` resolves to ``production_uht`` and any
unrecognised value raises ``ValueError`` rather than being mapped to a mode.
"""

from __future__ import annotations

from enum import Enum

__all__ = [
    "ExecutionMode",
    "resolve_execution_mode",
    "EXECUTION_MODE_CHOICES",
]


class ExecutionMode(Enum):
    """Typed execution mode. Never construct from unvalidated strings."""

    PRODUCTION_UHT = "production_uht"
    DIAGNOSTIC = "diagnostic"
    EXPERIMENTAL_GATE = "experimental_gate"

    @property
    def allows_learned_routing(self) -> bool:
        """True only when learned/heuristic gates may choose the executed policy."""
        return self is ExecutionMode.EXPERIMENTAL_GATE

    @property
    def records_diagnostics(self) -> bool:
        """True when gate features / predictions are recorded for analysis."""
        return self in (ExecutionMode.DIAGNOSTIC, ExecutionMode.EXPERIMENTAL_GATE)

    @property
    def is_experimental(self) -> bool:
        return self is ExecutionMode.EXPERIMENTAL_GATE

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


EXECUTION_MODE_CHOICES: tuple[str, ...] = tuple(m.value for m in ExecutionMode)


def resolve_execution_mode(value: "ExecutionMode | str | None") -> ExecutionMode:
    """Resolve an execution mode, failing closed to production.

    ``None`` (missing configuration) resolves to ``PRODUCTION_UHT``. Unknown
    strings raise ``ValueError``; they are never mapped to an experimental mode.
    """
    if isinstance(value, ExecutionMode):
        return value
    if value is None:
        return ExecutionMode.PRODUCTION_UHT
    if isinstance(value, str):
        key = value.strip().lower()
        for mode in ExecutionMode:
            if mode.value == key:
                return mode
        raise ValueError(
            f"Unknown execution mode {value!r}. "
            f"Valid modes: {', '.join(EXECUTION_MODE_CHOICES)}."
        )
    raise TypeError(
        f"Execution mode must be ExecutionMode, str, or None; got {type(value).__name__}."
    )
