"""Schemas for multi-provider pairwise judgments."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Choice = Literal["A", "B", "TIE", "INSUFFICIENT_INFORMATION", "INVALID", "REFUSAL"]
CHOICE_VALUES: tuple[str, ...] = (
    "A",
    "B",
    "TIE",
    "INSUFFICIENT_INFORMATION",
    "INVALID",
    "REFUSAL",
)


@dataclass(frozen=True)
class PromptSpec:
    """Predeclared prompt variant (no post-hoc tuning on test labels)."""

    version: str
    template: str
    allows_tie: bool
    structured_json: bool
    notes: str = ""


@dataclass
class JudgmentRecord:
    """Normalized, provenance-rich record for one oriented pairwise call."""

    provider: str
    model: str
    deployment_or_endpoint: str | None
    query_id: str
    doc_a_id: str
    doc_b_id: str
    canonical_pair_id: str
    displayed_orientation: Literal["ab", "ba"]
    prompt_version: str
    raw_response: str
    parsed_choice: Choice
    normalized_winner_id: str | None
    tie_or_abstention: bool
    valid: bool
    confidence_category: str | None = None
    vote_margin: float | None = None
    logprob_margin: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    latency_seconds: float | None = None
    retry_count: int = 0
    seed: int | None = None
    temperature: float = 0.0
    top_p: float | None = None
    max_tokens: int = 32
    timestamp_utc: str = ""
    cache_key: str = ""
    code_version: str = "multi_provider_eval_v1"
    from_cache: bool = False
    error_category: str | None = None
    error_message: str | None = None
    estimated_cost_usd: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
