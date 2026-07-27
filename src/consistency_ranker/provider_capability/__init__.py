"""Bounded provider-capability audit utilities.

Live calls are fail-closed and ledger-capped. Credential values are never
persisted. Capabilities that are not tested remain ``null`` / unknown.
"""

from __future__ import annotations

from consistency_ranker.provider_capability.schema import (
    SCHEMA_VERSION,
    empty_capability_record,
)

__all__ = [
    "SCHEMA_VERSION",
    "empty_capability_record",
]
