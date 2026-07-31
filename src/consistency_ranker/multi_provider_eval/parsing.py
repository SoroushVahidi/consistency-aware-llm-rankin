"""Strict parsing of pairwise LLM responses (fail-closed)."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from consistency_ranker.multi_provider_eval.schema import Choice

PARSER_VERSION = "pairwise_parse_v2"

_JSON_OBJ_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)
_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
_VALID_CHOICES = {"A", "B", "TIE", "INSUFFICIENT_INFORMATION"}
_CONFIDENCE = {"HIGH", "MEDIUM", "LOW"}

OutputFormatCategory = Literal[
    "exact_label",
    "strict_json",
    "fenced_json",
    "json_unexpected_field",
    "plain_tie_label",
    "truncated_output",
    "empty_output",
    "refusal",
    "natural_language_no_clear_label",
    "ambiguous_or_malformed",
    "incompatible_shape",
]


def _normalize_choice_token(token: str) -> Choice | None:
    t = token.strip().upper().replace(" ", "_")
    aliases = {
        "A": "A",
        "B": "B",
        "TIE": "TIE",
        "EQUAL": "TIE",
        "SAME": "TIE",
        "INSUFFICIENT_INFORMATION": "INSUFFICIENT_INFORMATION",
        "INSUFFICIENT": "INSUFFICIENT_INFORMATION",
        "UNKNOWN": "INSUFFICIENT_INFORMATION",
        "ABSTAIN": "INSUFFICIENT_INFORMATION",
        "NEITHER": "INSUFFICIENT_INFORMATION",
    }
    return aliases.get(t)  # type: ignore[return-value]


def classify_raw_response(
    raw: str,
    *,
    completion_tokens: int | None = None,
    max_tokens: int | None = None,
) -> OutputFormatCategory:
    """Evidence-backed category for a raw model string (no winner guessing)."""
    text = (raw or "").strip()
    if not text:
        return "empty_output"
    if completion_tokens is not None and max_tokens is not None and max_tokens > 0:
        if completion_tokens >= max_tokens and not _looks_complete_label(text):
            return "truncated_output"
    lower = text.lower()
    if any(
        phrase in lower
        for phrase in (
            "i can't",
            "i cannot",
            "i'm unable",
            "i am unable",
            "as an ai",
            "refuse",
            "not able to comply",
        )
    ) and not _has_exclusive_ab_label(text):
        return "refusal"
    if text.lstrip().startswith("{") or _FENCED_JSON_RE.search(text):
        obj = _extract_json_object(text)
        if obj is None:
            return "incompatible_shape"
        if any(k in obj for k in ("choice", "answer", "winner")):
            return "fenced_json" if _FENCED_JSON_RE.search(text) else "strict_json"
        return "json_unexpected_field"
    upper = text.upper().strip()
    first = re.split(r"[\s,.:;]+", upper, maxsplit=1)[0]
    choice = _normalize_choice_token(first)
    if choice in {"A", "B"} and len(upper) <= 4:
        return "exact_label"
    if choice in {"TIE", "INSUFFICIENT_INFORMATION"} and len(upper.split()) <= 2:
        return "plain_tie_label"
    last = upper.strip().splitlines()[-1].strip()
    last_tok = re.split(r"[\s,.:;]+", last, maxsplit=1)[0]
    if (
        _normalize_choice_token(last_tok) in {"A", "B"}
        and last_tok in {"A", "B"}
        and last in {"A", "B"}
    ):
        return "exact_label"
    return "natural_language_no_clear_label"


def _looks_complete_label(text: str) -> bool:
    upper = text.upper().strip()
    if upper in {"A", "B", "TIE"}:
        return True
    if upper.lstrip().startswith("{") and upper.rstrip().endswith("}"):
        return True
    return False


def _has_exclusive_ab_label(text: str) -> bool:
    upper = text.upper()
    has_a = bool(re.search(r"\bA\b", upper))
    has_b = bool(re.search(r"\bB\b", upper))
    return (has_a and not has_b) or (has_b and not has_a)


def parse_pairwise_response(
    raw: str,
    *,
    allow_tie: bool = False,
    structured_json: bool = False,
    completion_tokens: int | None = None,
    max_tokens: int | None = None,
    parser_version: str = PARSER_VERSION,
) -> tuple[Choice, str | None, str | None]:
    """Parse raw LLM text into (choice, confidence_category, parse_note).

    Never invents a winner from unrelated prose.  Ambiguous/malformed text
    yields ``INVALID``.  Explicit refusals yield ``REFUSAL``.
    """
    choice, conf, note, _cat = parse_pairwise_response_detailed(
        raw,
        allow_tie=allow_tie,
        structured_json=structured_json,
        completion_tokens=completion_tokens,
        max_tokens=max_tokens,
        parser_version=parser_version,
    )
    return choice, conf, note


def parse_pairwise_response_detailed(
    raw: str,
    *,
    allow_tie: bool = False,
    structured_json: bool = False,
    completion_tokens: int | None = None,
    max_tokens: int | None = None,
    parser_version: str = PARSER_VERSION,
) -> tuple[Choice, str | None, str | None, OutputFormatCategory]:
    """Parse with explicit output-format category (fail-closed; no fuzzy prose)."""
    _ = parser_version  # versioned entrypoint; behavior pinned by PARSER_VERSION
    text = (raw or "").strip()
    category = classify_raw_response(
        text, completion_tokens=completion_tokens, max_tokens=max_tokens
    )
    if not text:
        return "INVALID", None, "empty_response", category

    lower = text.lower()
    if category == "refusal":
        return "REFUSAL", None, "refusal_language", category
    if any(
        phrase in lower
        for phrase in (
            "i can't",
            "i cannot",
            "i'm unable",
            "i am unable",
            "as an ai",
            "refuse",
            "not able to comply",
        )
    ) and not any(x in text.upper() for x in ("A", "B", "TIE")):
        return "REFUSAL", None, "refusal_language", "refusal"

    confidence: str | None = None
    if structured_json or text.lstrip().startswith("{") or _FENCED_JSON_RE.search(text):
        obj = _extract_json_object(text)
        if obj is not None:
            choice_raw = obj.get("choice", obj.get("answer", obj.get("winner")))
            conf_raw = obj.get("confidence")
            if conf_raw is not None:
                conf_u = str(conf_raw).strip().upper()
                confidence = conf_u if conf_u in _CONFIDENCE else None
            if choice_raw is None:
                return "INVALID", confidence, "json_missing_choice", "json_unexpected_field"
            choice = _normalize_choice_token(str(choice_raw))
            if choice is None:
                return "INVALID", confidence, "json_unknown_choice", "json_unexpected_field"
            if choice in {"TIE", "INSUFFICIENT_INFORMATION"} and not allow_tie:
                return "INVALID", confidence, "tie_not_allowed_by_prompt", category
            if choice in _VALID_CHOICES:
                note = "fenced_json" if _FENCED_JSON_RE.search(text) else "json_ok"
                cat: OutputFormatCategory = (
                    "fenced_json" if note == "fenced_json" else "strict_json"
                )
                return choice, confidence, note, cat
            return "INVALID", confidence, "json_invalid_choice", category

        if structured_json:
            return "INVALID", None, "expected_json_object", "incompatible_shape"

    # Exact first-token / first-line label.
    upper = text.upper().strip()
    first = re.split(r"[\s,.:;]+", upper, maxsplit=1)[0]
    choice = _normalize_choice_token(first)
    if choice in {"A", "B"}:
        return choice, confidence, "plaintext_token", "exact_label"
    if allow_tie and choice in {"TIE", "INSUFFICIENT_INFORMATION"}:
        return choice, confidence, "plaintext_token", "plain_tie_label"

    # Strict last-line exact label only (no fuzzy prose guessing).
    last_line = text.strip().splitlines()[-1].strip()
    if last_line.upper() in {"A", "B"}:
        return last_line.upper(), confidence, "exact_last_line_label", "exact_label"  # type: ignore[return-value]
    if allow_tie and last_line.upper() in {"TIE", "INSUFFICIENT_INFORMATION", "NEITHER"}:
        norm = _normalize_choice_token(last_line)
        if norm is not None:
            return norm, confidence, "exact_last_line_label", "plain_tie_label"

    # Exclusive whole-word A or B only when the entire response is a short label-like string.
    if len(upper) <= 8:
        has_a = bool(re.search(r"\bA\b", upper))
        has_b = bool(re.search(r"\bB\b", upper))
        if has_a and not has_b:
            return "A", confidence, "plaintext_exclusive_a", "exact_label"
        if has_b and not has_a:
            return "B", confidence, "plaintext_exclusive_b", "exact_label"

    if category == "truncated_output":
        return "INVALID", confidence, "truncated_output", category
    if category == "natural_language_no_clear_label":
        return "INVALID", confidence, "ambiguous_or_malformed", category
    return "INVALID", confidence, "ambiguous_or_malformed", "ambiguous_or_malformed"


def _extract_json_object(text: str) -> dict[str, Any] | None:
    fenced = _FENCED_JSON_RE.search(text)
    if fenced:
        try:
            obj = json.loads(fenced.group(1))
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    match = _JSON_OBJ_RE.search(text)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def normalize_winner(
    choice: Choice,
    *,
    doc_a_id: str,
    doc_b_id: str,
    orientation: str,
) -> tuple[str | None, bool]:
    """Map displayed choice back to canonical winner id.

    ``orientation='ab'`` means doc_a was shown as Document A.
    ``orientation='ba'`` means doc_b was shown as Document A (swapped display).
    """
    if choice in {"TIE", "INSUFFICIENT_INFORMATION", "INVALID", "REFUSAL"}:
        return None, True
    if orientation not in {"ab", "ba"}:
        raise ValueError(f"Unknown orientation {orientation!r}")
    # Display A/B relative to shown order.
    if orientation == "ab":
        shown_a, shown_b = doc_a_id, doc_b_id
    else:
        shown_a, shown_b = doc_b_id, doc_a_id
    if choice == "A":
        return shown_a, False
    if choice == "B":
        return shown_b, False
    return None, True
