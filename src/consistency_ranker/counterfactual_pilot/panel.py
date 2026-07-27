"""Frozen four-provider panel for counterfactual micro-pilot v1."""

from __future__ import annotations

from typing import Any

PANEL_VERSION = "counterfactual_provider_panel_v1"

# Exact configured identifiers observed in the capability audit.
# Exact backend revisions may be opaque; do not invent versions.
_PANEL: tuple[dict[str, Any], ...] = (
    {
        "provider": "azure",
        "model_or_deployment": "gpt-4.1-mini",
        "family": "openai_compatible_chat",
        "intended_role": "closed-model production-style judge",
        "scientific_role": (
            "Current production-style reference path; not ground truth."
        ),
        "structured_output_observed": True,
        "token_usage_reported": True,
        "latency_reported": True,
        "temperature": 0.0,
        "seed_behavior": (
            "Client accepts seed where the OpenAI-compatible path supports it; "
            "determinism is not claimed."
        ),
        "max_output_tokens": 128,
        "backend_revision_visible": False,
        "limitations": [
            "Deployment identifier may not expose exact model revision.",
            "No native listwise rerank used as pairwise judge.",
        ],
    },
    {
        "provider": "cohere",
        "model_or_deployment": "command-r-plus-08-2024",
        "family": "command_r",
        "intended_role": "independent Command-family judge",
        "scientific_role": "Independent Command-family pairwise judge.",
        "structured_output_observed": True,
        "token_usage_reported": True,
        "latency_reported": True,
        "temperature": 0.0,
        "seed_behavior": "Seed accepted by client config; determinism not claimed.",
        "max_output_tokens": 128,
        "backend_revision_visible": False,
        "limitations": [
            "Native Cohere Rerank is a separate listwise baseline, not this judge.",
            "Exact hosted revision may be opaque.",
        ],
    },
    {
        "provider": "fireworks",
        "model_or_deployment": "accounts/fireworks/models/gpt-oss-120b",
        "family": "open_weight_hosted_chat",
        "intended_role": "open-weight or hosted low-cost judge",
        "scientific_role": "Economical open/hosted model path.",
        "structured_output_observed": True,
        "token_usage_reported": True,
        "latency_reported": True,
        "temperature": 0.0,
        "seed_behavior": "Seed accepted by client config; determinism not claimed.",
        "max_output_tokens": 128,
        "backend_revision_visible": False,
        "limitations": [
            "Hosted open-weight path; serving stack may differ from local weights.",
        ],
    },
    {
        "provider": "gemini",
        "model_or_deployment": "gemini-2.5-flash",
        "family": "gemini",
        "intended_role": "independent Gemini-family judge",
        "scientific_role": "Independent Gemini-family pairwise judge via Vertex.",
        "structured_output_observed": True,
        "token_usage_reported": True,
        "latency_reported": True,
        "temperature": 0.0,
        "seed_behavior": "Seed accepted by client config; determinism not claimed.",
        "max_output_tokens": 128,
        "backend_revision_visible": False,
        "limitations": [
            "Vertex project/location are redacted in published artifacts.",
            "Exact backend revision may be opaque.",
        ],
    },
)


def frozen_panel() -> list[dict[str, Any]]:
    """Return a deep-ish copy of the frozen panel members."""
    return [dict(x) for x in _PANEL]


def require_panel_version(version: str) -> None:
    """Refuse silent panel edits; bump PANEL_VERSION / freeze doc for replacements."""
    if version != PANEL_VERSION:
        raise ValueError(
            f"Invalid panel version {version!r}; expected {PANEL_VERSION!r}. "
            "Model replacements require counterfactual_provider_panel_v2 (or later) "
            "and a new freeze document."
        )


def panel_model_ids() -> list[str]:
    return [str(m["model_or_deployment"]) for m in _PANEL]


def panel_providers() -> list[str]:
    return [str(m["provider"]) for m in _PANEL]
