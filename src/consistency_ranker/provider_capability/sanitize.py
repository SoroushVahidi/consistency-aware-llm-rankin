"""Redaction helpers — never persist secret values."""

from __future__ import annotations

import hashlib
import re
from typing import Any

_SECRET_KEY_RE = re.compile(
    r"(^|_)(api[_-]?key|authorization|auth_header|bearer|access_token|refresh_token|"
    r"password|secret|credential|private_key)(_|$)",
    re.IGNORECASE,
)
_PROJECT_RE = re.compile(
    r"(project[=:\s]+)([a-z0-9\-]+)",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_HOME_RE = re.compile(r"(/home/[^/\s]+|/Users/[^/\s]+|/workspace)")


def redact_text(text: str | None) -> str:
    if not text:
        return ""
    out = str(text)
    out = _EMAIL_RE.sub("[REDACTED_EMAIL]", out)
    out = _HOME_RE.sub("[REDACTED_PATH]", out)
    out = _PROJECT_RE.sub(r"\1[REDACTED_PROJECT]", out)
    # Long opaque tokens (heuristics; never echo secrets).
    out = re.sub(r"\bsk-[A-Za-z0-9]{8,}\b", "[REDACTED_TOKEN]", out)
    out = re.sub(r"\bAIza[A-Za-z0-9_\-]{10,}\b", "[REDACTED_TOKEN]", out)
    return out


def sanitize_mapping(obj: Any) -> Any:
    """Recursively drop/redact secret-looking fields."""
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if _SECRET_KEY_RE.search(str(k)):
                out[str(k)] = "[REDACTED]"
            else:
                out[str(k)] = sanitize_mapping(v)
        return out
    if isinstance(obj, list):
        return [sanitize_mapping(x) for x in obj]
    if isinstance(obj, str):
        return redact_text(obj)
    return obj


def response_hash(raw: str) -> str:
    return hashlib.sha256((raw or "").encode("utf-8")).hexdigest()


def sanitize_model_identity(provider: str, model: str | None) -> str | None:
    """Keep model/deployment labels; never include endpoints or keys."""
    if model is None:
        return None
    text = str(model).strip()
    if not text:
        return None
    # Strip anything that looks like a URL.
    if "://" in text or "openai.azure.com" in text.lower():
        return f"sanitized:{hashlib.sha256(text.encode()).hexdigest()[:12]}"
    return text


def env_names_for_provider(provider: str) -> list[str]:
    """Return environment-variable NAMES only (never values)."""
    mapping = {
        "azure": [
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_API_BASE",
            "AZURE_OPENAI_DEPLOYMENT",
            "AZURE_OPENAI_STRONG_DEPLOYMENT",
        ],
        "cohere": ["COHERE_API_KEY", "COHERE_MODEL", "COHERE_BASE_URL"],
        "fireworks": ["FIREWORKS_API_KEY", "FIREWORKS_MODEL", "FIREWORKS_BASE_URL"],
        "gemini": [
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "GOOGLE_GENAI_USE_VERTEXAI",
            "GOOGLE_CLOUD_PROJECT",
            "GOOGLE_CLOUD_LOCATION",
            "GEMINI_MODEL",
            "GEMINI_VERTEX_MODEL",
        ],
    }
    return list(mapping.get(provider, []))
