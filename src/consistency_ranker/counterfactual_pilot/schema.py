"""Judgment schema validation for counterfactual_pairwise_judgment_v1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

JUDGMENT_SCHEMA_VERSION = "counterfactual_pairwise_judgment_v1"
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
