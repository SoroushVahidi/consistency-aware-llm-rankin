"""Tiny public synthetic fixture for provider smoke tests.

Expected preference A is a diagnostic label only — not provider ground truth.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

FIXTURE_ID = "earth_seasons_v1"

QUERY = "Why does Earth have seasons?"

CANDIDATE_A = (
    "Earth has seasons mainly because its rotational axis is tilted "
    "relative to its orbit around the Sun."
)

CANDIDATE_B = (
    "Earth has seasons mainly because its distance from the Sun changes "
    "substantially during the year."
)

# Diagnostic only; never treat as ranking gold for scientific claims.
DIAGNOSTIC_EXPECTED_PREFERENCE = "A"

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

SMOKE_PROMPT_TEMPLATE = """You are a search relevance judge.
Choose which document is more relevant to the query.

Query: {query}
Document A: {document_a}
Document B: {document_b}

Respond with ONLY a single JSON object and no other text:
{{"preference":"A","confidence":0.0,"evidence_strength":"strong","reason_code":"direct_relevance"}}

Rules:
- preference must be exactly one of: A, B, TIE, ABSTAIN
- confidence must be a number in [0, 1]
- evidence_strength must be one of: weak, moderate, strong
- reason_code must be one of: direct_relevance, partial_answer, unsupported, ambiguous, other
- Do not explain. Do not include chain-of-thought.
"""

PROMPT_VERSION = "provider_capability_smoke_v1"


def fixture_payload() -> dict[str, Any]:
    return {
        "fixture_id": FIXTURE_ID,
        "query": QUERY,
        "candidate_a": {"doc_id": "doc_a", "text": CANDIDATE_A},
        "candidate_b": {"doc_id": "doc_b", "text": CANDIDATE_B},
        "diagnostic_expected_preference": DIAGNOSTIC_EXPECTED_PREFERENCE,
        "prompt_version": PROMPT_VERSION,
        "note": (
            "Diagnostic expected preference is for smoke connectivity only; "
            "it is not provider ranking ground truth."
        ),
    }


def fixture_hash() -> str:
    blob = json.dumps(fixture_payload(), sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def prompt_hash() -> str:
    return hashlib.sha256(SMOKE_PROMPT_TEMPLATE.encode("utf-8")).hexdigest()


def format_smoke_prompt(*, document_a: str, document_b: str) -> str:
    return SMOKE_PROMPT_TEMPLATE.format(
        query=QUERY,
        document_a=document_a,
        document_b=document_b,
    )
