"""Canonical pairwise evidence representation (fail-closed)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

OutcomeZ = Literal[-1, 0, 1]
AbstentionSubtype = Literal[
    "none",
    "tie",
    "insufficient_information",
    "refusal",
    "invalid",
    "missing",
]


def canonical_doc_order(doc_x: str, doc_y: str) -> tuple[str, str]:
    """Return (doc_i, doc_j) with doc_i < doc_j lexicographically."""
    a, b = str(doc_x), str(doc_y)
    return (a, b) if a < b else (b, a)


def canonical_pair_id(query_id: str, doc_x: str, doc_y: str) -> str:
    i, j = canonical_doc_order(doc_x, doc_y)
    return f"{query_id}::{i}::{j}"


@dataclass
class NormalizedEvidence:
    """One provenance-rich judgment normalized to canonical pair orientation.

    ``z``:
      * +1 — canonical first doc (``doc_i``) preferred over ``doc_j``
      * -1 — ``doc_j`` preferred over ``doc_i``
      *  0 — tie / abstain / refuse / invalid (see ``abstention_subtype``)
    """

    query_id: str
    canonical_pair_id: str
    doc_i: str
    doc_j: str
    displayed_orientation: str | None
    z: OutcomeZ
    abstention_subtype: AbstentionSubtype
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    repetition_index: int = 0
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    valid: bool = False
    confidence_category: str | None = None
    logprob_margin: float | None = None
    prior_score_i: float | None = None
    prior_score_j: float | None = None
    prior_rank_i: int | None = None
    prior_rank_j: int | None = None
    timestamp_utc: str | None = None
    cache_key: str | None = None
    raw_choice: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _z_from_winner(
    winner_id: str | None,
    *,
    doc_i: str,
    doc_j: str,
    choice: str | None,
) -> tuple[OutcomeZ, AbstentionSubtype]:
    if winner_id == doc_i:
        return 1, "none"
    if winner_id == doc_j:
        return -1, "none"
    ch = (choice or "").upper()
    if ch == "TIE":
        return 0, "tie"
    if ch in {"INSUFFICIENT_INFORMATION", "INSUFFICIENT"}:
        return 0, "insufficient_information"
    if ch == "REFUSAL":
        return 0, "refusal"
    if ch == "INVALID" or not winner_id:
        return 0, "invalid"
    return 0, "missing"


def normalize_judgment_record(
    record: dict[str, Any],
    *,
    prior_scores: dict[str, float] | None = None,
) -> NormalizedEvidence:
    """Normalize a multi_provider_eval (or compatible) judgment dict.

    Fail-closed: invalid/tie/refusal → z=0. Never invents a winner.
    """
    query_id = str(record["query_id"])
    a = str(record.get("doc_a_id") or record.get("doc_i"))
    b = str(record.get("doc_b_id") or record.get("doc_j"))
    doc_i, doc_j = canonical_doc_order(a, b)
    pair_id = record.get("canonical_pair_id") or canonical_pair_id(query_id, a, b)

    winner = record.get("normalized_winner_id")
    choice = record.get("parsed_choice") or record.get("raw_choice")
    valid = bool(record.get("valid", False))
    if not valid and winner is not None:
        # Do not trust winners from invalid rows.
        winner = None
    z, subtype = _z_from_winner(
        str(winner) if winner is not None else None,
        doc_i=doc_i,
        doc_j=doc_j,
        choice=str(choice) if choice is not None else None,
    )

    prior_scores = prior_scores or {}
    ranks: dict[str, int] = {}
    if prior_scores:
        ordered = sorted(prior_scores, key=lambda d: (-float(prior_scores[d]), d))
        ranks = {d: i + 1 for i, d in enumerate(ordered)}

    extra = dict(record.get("extra") or {})
    rep = int(extra.get("repeat_index", record.get("repetition_index", 0)) or 0)

    return NormalizedEvidence(
        query_id=query_id,
        canonical_pair_id=str(pair_id),
        doc_i=doc_i,
        doc_j=doc_j,
        displayed_orientation=record.get("displayed_orientation"),
        z=z,  # type: ignore[arg-type]
        abstention_subtype=subtype,
        provider=record.get("provider"),
        model=record.get("model"),
        prompt_version=record.get("prompt_version"),
        repetition_index=rep,
        temperature=record.get("temperature"),
        top_p=record.get("top_p"),
        max_tokens=record.get("max_tokens"),
        valid=bool(record.get("valid", False)),
        confidence_category=record.get("confidence_category"),
        logprob_margin=record.get("logprob_margin"),
        prior_score_i=float(prior_scores[doc_i]) if doc_i in prior_scores else None,
        prior_score_j=float(prior_scores[doc_j]) if doc_j in prior_scores else None,
        prior_rank_i=ranks.get(doc_i),
        prior_rank_j=ranks.get(doc_j),
        timestamp_utc=record.get("timestamp_utc"),
        cache_key=record.get("cache_key"),
        raw_choice=str(choice) if choice is not None else None,
        extra=extra,
    )


def preference_from_simple(
    *,
    query_id: str,
    winner: str,
    loser: str,
    provider: str = "synthetic",
    model: str = "synth",
    prompt_version: str = "synthetic_v1",
    valid: bool = True,
) -> NormalizedEvidence:
    """Helper for synthetic / unit tests."""
    return normalize_judgment_record(
        {
            "query_id": query_id,
            "doc_a_id": winner,
            "doc_b_id": loser,
            "normalized_winner_id": winner,
            "parsed_choice": "A",
            "valid": valid,
            "provider": provider,
            "model": model,
            "prompt_version": prompt_version,
            "displayed_orientation": "ab",
        }
    )
