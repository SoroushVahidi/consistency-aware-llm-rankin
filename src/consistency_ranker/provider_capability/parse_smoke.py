"""Parse and normalize provider-capability smoke responses."""

from __future__ import annotations

import json
import re
from typing import Any

from consistency_ranker.provider_capability.fixture import (
    ALLOWED_EVIDENCE,
    ALLOWED_PREFERENCES,
    ALLOWED_REASON_CODES,
)

_JSON_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)
_FENCED = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def _extract_obj(raw: str) -> dict[str, Any] | None:
    text = (raw or "").strip()
    if not text:
        return None
    m = _FENCED.search(text)
    if m:
        text = m.group(1)
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    m2 = _JSON_RE.search(raw or "")
    if not m2:
        return None
    try:
        obj = json.loads(m2.group(0))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def parse_smoke_response(raw: str) -> dict[str, Any]:
    """Return normalized smoke judgment fields + parse_status."""
    obj = _extract_obj(raw)
    if obj is None:
        # Fallback: exclusive A/B first token.
        token = re.split(r"[\s,.:;]+", (raw or "").strip().upper(), maxsplit=1)[0]
        if token in {"A", "B"}:
            return {
                "parse_status": "fallback_label",
                "preference": token,
                "confidence": None,
                "evidence_strength": None,
                "reason_code": None,
                "structured_ok": False,
            }
        return {
            "parse_status": "parse_failure",
            "preference": None,
            "confidence": None,
            "evidence_strength": None,
            "reason_code": None,
            "structured_ok": False,
        }

    pref = str(obj.get("preference", obj.get("choice", ""))).strip().upper()
    if pref == "INSUFFICIENT_INFORMATION":
        pref = "ABSTAIN"
    conf_raw = obj.get("confidence")
    try:
        conf = float(conf_raw) if conf_raw is not None else None
    except (TypeError, ValueError):
        conf = None
    if conf is not None:
        conf = max(0.0, min(1.0, conf))
    strength = str(obj.get("evidence_strength") or "").strip().lower() or None
    reason = str(obj.get("reason_code") or "").strip().lower() or None

    ok = (
        pref in ALLOWED_PREFERENCES
        and (strength is None or strength in ALLOWED_EVIDENCE)
        and (reason is None or reason in ALLOWED_REASON_CODES)
    )
    if pref not in ALLOWED_PREFERENCES:
        return {
            "parse_status": "invalid_preference",
            "preference": None,
            "confidence": conf,
            "evidence_strength": strength,
            "reason_code": reason,
            "structured_ok": False,
        }
    has_pref_key = "preference" in obj or "choice" in obj
    structured_ok = bool(ok and has_pref_key)
    return {
        "parse_status": "ok" if structured_ok else "partial_schema",
        "preference": pref,
        "confidence": conf,
        "evidence_strength": strength if strength in ALLOWED_EVIDENCE else None,
        "reason_code": reason if reason in ALLOWED_REASON_CODES else None,
        "structured_ok": structured_ok,
    }


def map_preference_to_document(
    preference: str | None,
    *,
    orientation: str,
) -> str | None:
    """Map displayed A/B preference back to stable document ids.

    orientation ``ab`` means displayed A=doc_a, B=doc_b.
    orientation ``ba`` means displayed A=doc_b, B=doc_a.
    """
    if preference is None:
        return None
    if preference in {"TIE", "ABSTAIN"}:
        return preference
    if preference not in {"A", "B"}:
        return None
    if orientation == "ab":
        return "doc_a" if preference == "A" else "doc_b"
    if orientation == "ba":
        return "doc_b" if preference == "A" else "doc_a"
    raise ValueError(f"Unknown orientation: {orientation}")
