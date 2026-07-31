"""Azure multifactor request-profile constants (provider-isolated).

Repo hygiene Stage 5 (2026-07-30): these constants used to live in
``consistency_ranker.multifactor_acquisition.azure_request``, but their only
real consumer is this package's own ``providers.py`` (they shape the Azure
"compact A/B" request profile inside ``MultiProviderJudge.compare()``) --
having ``multi_provider_eval`` import them from ``multifactor_acquisition``
created a circular package dependency (``multifactor_acquisition.live_judge``
imports ``multi_provider_eval.providers``/``spending`` at module top level,
while ``multi_provider_eval.providers`` imported this file back from
``multifactor_acquisition``). Moved here, where the actual responsibility
(shaping an Azure provider request) belongs.
``consistency_ranker.multifactor_acquisition.azure_request`` now re-exports
these same names as a compatibility shim for any caller still importing the
old path.
"""

from __future__ import annotations

# Compact A/B shaping for Azure gpt-4.1-mini without changing PromptSpec text.
AZURE_SYSTEM_MESSAGE_V1 = (
    "You are a relevance judge. Reply with exactly one character: A or B. "
    "Do not explain. Do not say neither. Do not use markdown."
)
AZURE_MAX_TOKENS_V1 = 16
AZURE_REQUEST_PROFILE = "azure_compact_ab_v1"
