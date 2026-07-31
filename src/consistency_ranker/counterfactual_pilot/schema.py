"""Judgment schema validation for counterfactual_pairwise_judgment_v1."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

JUDGMENT_SCHEMA_VERSION = "counterfactual_pairwise_judgment_v1"

# Matches a response that is *entirely* one markdown code fence (optionally
# tagged ```json), e.g. "```json\n{...}\n```". Gemini's native google-genai
# SDK path (unlike this collector's other providers, which go through an
# OpenAI-compatible chat-completions endpoint) is not configured with
# response_mime_type/response_schema, and is documented to wrap structured
# output in a fence like this by default. Anchored on both ends against the
# *stripped* full response, so it only ever unwraps a single, complete fence
# around the whole payload -- it never scans for a JSON substring inside
# surrounding prose, and a malformed/partial/multi-block fence simply fails
# to match and falls through to the caller's unchanged strict json.loads.
_FULL_FENCE_RE = re.compile(r"^```(?:json)?\s*(?P<body>.*?)\s*```$", re.DOTALL | re.IGNORECASE)


def extract_json_payload(raw_response: str) -> tuple[str, bool]:
    """Return (text_to_parse, wrapper_extraction_used).

    Only unwraps a full-response markdown code fence; every other input is
    returned unchanged so strict json.loads/validate_judgment still reject
    it exactly as before this function existed.
    """
    stripped = raw_response.strip()
    match = _FULL_FENCE_RE.match(stripped)
    if match:
        return match.group("body"), True
    return raw_response, False
ALLOWED_PREFERENCES = frozenset({"A", "B", "TIE", "ABSTAIN"})
ALLOWED_EVIDENCE = frozenset({"weak", "moderate", "strong"})
ALLOWED_REASON_CODES = frozenset(
    {
        "direct_relevance",
        "partial_answer",
        "unsupported",
        "ambiguous",
        "other",
    }
)

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "schemas"
    / "counterfactual_pairwise_judgment_v1.json"
)


def load_json_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_judgment(obj: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a judgment object.

    Raises ValueError on invalid payloads. Confidence is retained as a
    self-report and is not treated as cross-provider calibrated.
    """
    if not isinstance(obj, dict):
        raise ValueError("judgment must be an object")
    version = obj.get("schema_version", JUDGMENT_SCHEMA_VERSION)
    if version != JUDGMENT_SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version: {version!r}")
    pref = str(obj.get("preference", "")).strip().upper()
    if pref == "INSUFFICIENT_INFORMATION":
        pref = "ABSTAIN"
    if pref not in ALLOWED_PREFERENCES:
        raise ValueError(f"invalid preference: {pref!r}")
    try:
        conf = float(obj["confidence"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("confidence must be a number in [0, 1]") from exc
    if not 0.0 <= conf <= 1.0:
        raise ValueError("confidence must be in [0, 1]")
    strength = str(obj.get("evidence_strength", "")).strip().lower()
    if strength not in ALLOWED_EVIDENCE:
        raise ValueError(f"invalid evidence_strength: {strength!r}")
    reason = str(obj.get("reason_code", "")).strip().lower()
    if reason not in ALLOWED_REASON_CODES:
        raise ValueError(f"invalid reason_code: {reason!r}")
    return {
        "schema_version": JUDGMENT_SCHEMA_VERSION,
        "preference": pref,
        "confidence": conf,
        "evidence_strength": strength,
        "reason_code": reason,
    }
