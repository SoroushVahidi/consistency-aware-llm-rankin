"""
llm_api_status.py
=================
Lightweight capability checks for LLM providers (OpenAI, Gemini).

This module deliberately avoids printing or returning secret values.  It only
reports whether required environment variables are present, whether the client
library can be imported, and whether an optional probe call succeeded.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class ProviderProbeResult:
    """Capability probe result for one provider."""

    provider: str
    env_present: bool
    import_ok: bool
    probe_ok: bool
    message: str
    details: dict[str, Any] | None = None


def _bool_env(*names: str) -> bool:
    return any(bool(os.environ.get(n)) for n in names)


def check_openai(probe: bool = False) -> ProviderProbeResult:
    """Check OpenAI availability without leaking secrets."""
    env_present = _bool_env("OPENAI_API_KEY", "AZURE_OPENAI_API_KEY")
    import_ok = False
    probe_ok = False
    details: dict[str, Any] = {}
    message = "OPENAI_API_KEY/AZURE_OPENAI_API_KEY missing"

    try:
        import openai  # type: ignore

        import_ok = True
        if env_present:
            client = openai.OpenAI()  # type: ignore[attr-defined]
            if probe:
                try:
                    resp = client.models.list(timeout=5)
                    sample = [m.id for m in getattr(resp, "data", [])][:3]
                    details["models_sample"] = sample
                    probe_ok = True
                    message = "probe succeeded"
                except Exception as exc:  # pragma: no cover - network/cred dependent
                    message = f"probe failed: {exc}"
            else:
                message = "env present, import ok (probe skipped)"
    except Exception as exc:
        message = f"import failed: {exc}"

    return ProviderProbeResult(
        provider="openai",
        env_present=env_present,
        import_ok=import_ok,
        probe_ok=probe_ok,
        message=message,
        details=details if details else None,
    )


def check_gemini(probe: bool = False) -> ProviderProbeResult:
    """Check Google Gemini availability without leaking secrets.

    Recognizes two independent auth modes: a direct Gemini API key
    (GEMINI_API_KEY/GOOGLE_API_KEY), or Vertex AI via Application Default
    Credentials (GOOGLE_GENAI_USE_VERTEXAI + a resolvable project). See
    ``failure_mining.llm_runner._gemini_vertex_config`` for the canonical
    Vertex-detection logic this mirrors.
    """
    env_present = _bool_env("GEMINI_API_KEY", "GOOGLE_API_KEY")
    vertex_cfg: dict[str, str] | None = None
    if not env_present:
        try:
            from consistency_ranker.failure_mining.llm_runner import _gemini_vertex_config

            vertex_cfg = _gemini_vertex_config()
        except Exception:
            vertex_cfg = None
    mode = "api_key" if env_present else ("vertex" if vertex_cfg else None)
    import_ok = False
    probe_ok = False
    details: dict[str, Any] = {}
    if mode:
        message = f"credentials present ({mode})"
    else:
        message = "GEMINI_API_KEY/GOOGLE_API_KEY missing and no usable Vertex AI config"

    try:
        from google import genai  # type: ignore

        import_ok = True
        if probe and mode == "api_key":
            try:
                api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
                client = genai.Client(api_key=api_key)
                resp = client.models.list()  # type: ignore[attr-defined]
                sample = [getattr(m, "name", "") for m in getattr(resp, "models", [])][:3]
                details["models_sample"] = sample
                probe_ok = True
                message = "probe succeeded (api_key)"
            except Exception as exc:  # pragma: no cover - network/cred dependent
                message = f"probe failed: {exc}"
        elif probe and mode == "vertex" and vertex_cfg:
            try:
                from google.genai import types  # type: ignore

                client = genai.Client(vertexai=True, project=vertex_cfg["project"], location=vertex_cfg["location"])
                resp = client.models.generate_content(
                    model=os.environ.get("GEMINI_VERTEX_MODEL", "gemini-2.5-flash"),
                    contents="Return exactly the word OK.",
                    config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=8),
                )
                details["vertex_project"] = vertex_cfg["project"]
                details["vertex_location"] = vertex_cfg["location"]
                details["response_text"] = getattr(resp, "text", None)
                probe_ok = True
                message = "probe succeeded (vertex)"
            except Exception as exc:  # pragma: no cover - network/cred dependent
                message = f"probe failed: {exc}"
        elif mode:
            message = f"env present, import ok (probe skipped) [{mode}]"
    except Exception as exc:
        message = f"import failed: {exc}"

    return ProviderProbeResult(
        provider="gemini",
        env_present=env_present or bool(vertex_cfg),
        import_ok=import_ok,
        probe_ok=probe_ok,
        message=message,
        details=details if details else None,
    )


def detect_providers(probe: bool = False) -> dict[str, ProviderProbeResult]:
    """Return capability results for known providers."""
    results = {
        "openai": check_openai(probe=probe),
        "gemini": check_gemini(probe=probe),
    }
    return results
