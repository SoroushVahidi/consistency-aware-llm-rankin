"""Provider capability record schema (provider_capability_v1)."""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "provider_capability_v1"

AUDIT_PROVIDERS = ("azure", "cohere", "fireworks", "gemini")


def empty_capability_record(provider: str) -> dict[str, Any]:
    """Return a capability record with unknown/null fields unset."""
    return {
        "schema_version": SCHEMA_VERSION,
        "provider": provider,
        "model_or_deployment": None,
        "underlying_model_family": None,
        "configured": False,
        "authentication_verified": False,
        "model_identity_verified": False,
        "structured_output": {"supported": None, "verified": False},
        "seed": {"accepted": None, "determinism_verified": False},
        "token_usage_reported": None,
        "latency_measured": None,
        "logprobs": {"supported": None, "verified": False},
        "rerank_endpoint": {"available": None, "verified": False},
        "cache_only_supported": True,
        "dry_run_supported": True,
        "position_swap": {
            "tested": False,
            "document_identity_consistent": None,
            "position_sensitive": None,
        },
        "repeatability": {
            "tested": False,
            "same_preference": None,
            "note": "One repeat is insufficient to claim determinism.",
        },
        "smoke_preference_ab": None,
        "smoke_preference_ba_mapped": None,
        "smoke_preference_ab_repeat": None,
        "live_requests_used": 0,
        "estimated_cost_usd": None,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "errors": [],
        "limitations": [],
    }
