"""Compatibility shim (repo hygiene Stage 5, 2026-07-30).

These constants moved to
:mod:`consistency_ranker.multi_provider_eval.azure_request`, which is now
their canonical home -- ``multi_provider_eval.providers`` is their actual
consumer, and importing them from here into that package was the cause of a
circular package dependency between ``multi_provider_eval`` and
``multifactor_acquisition`` (see the canonical module's docstring for the
full explanation). This module re-exports the same three names unchanged so
that any existing import of
``consistency_ranker.multifactor_acquisition.azure_request`` keeps working
without modification.
"""

from __future__ import annotations

from consistency_ranker.multi_provider_eval.azure_request import (
    AZURE_MAX_TOKENS_V1,
    AZURE_REQUEST_PROFILE,
    AZURE_SYSTEM_MESSAGE_V1,
)

__all__ = [
    "AZURE_MAX_TOKENS_V1",
    "AZURE_REQUEST_PROFILE",
    "AZURE_SYSTEM_MESSAGE_V1",
]
