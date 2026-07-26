"""Azure multifactor request-profile constants (provider-isolated)."""

from __future__ import annotations

# Compact A/B shaping for Azure gpt-4.1-mini without changing PromptSpec text.
AZURE_SYSTEM_MESSAGE_V1 = (
    "You are a relevance judge. Reply with exactly one character: A or B. "
    "Do not explain. Do not say neither. Do not use markdown."
)
AZURE_MAX_TOKENS_V1 = 16
AZURE_REQUEST_PROFILE = "azure_compact_ab_v1"
