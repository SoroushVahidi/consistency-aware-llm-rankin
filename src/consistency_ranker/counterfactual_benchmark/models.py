"""Plain dataclasses for the collector's plan/judgment/outcome records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RenderedDocumentRecord:
    """Rendering/truncation provenance for one candidate document.

    ``full_document_sha256`` hashes the complete composed document (title +
    text, before truncation) so a truncated excerpt can always be traced back
    to -- without ever storing -- the full original content.
    """

    document_id: str
    full_document_sha256: str
    rendered_excerpt_sha256: str
    original_character_count: int
    rendered_character_count: int
    truncated: bool
    truncation_policy: str
    title_included: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CandidatePoolRecord:
    dataset: str
    query_id: str
    candidate_ids: tuple[str, ...]
    pool_hash: str
    text_hashes: dict[str, str]
    construction_method: str
    pool_protocol_version: str
    rendering_policy_version: str
    prior_scores_primary: dict[str, float]
    prior_scores_secondary: dict[str, float]
    truncated_texts: dict[str, str]
    rendering_metadata: dict[str, RenderedDocumentRecord]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["candidate_ids"] = list(self.candidate_ids)
        return d


@dataclass(frozen=True)
class PairRecord:
    dataset: str
    query_id: str
    doc_a_id: str
    doc_b_id: str
    pair_id: str
    reason: str
    initial_presentation_order: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlannedRequest:
    request_hash: str
    benchmark_version: str
    dataset: str
    query_id: str
    pool_hash: str
    provider: str
    model_id: str
    doc_a_id: str
    doc_b_id: str
    presentation_order: str
    pair_id: str
    pair_reason: str
    temperature: float
    seed: int
    attempt_type: str  # "initial" | "reserve"
    reserve_trigger: str | None = None
    reserve_priority: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizedJudgment:
    request_hash: str
    dataset: str
    query_id: str
    provider: str
    model_id: str
    doc_a_id: str
    doc_b_id: str
    pair_id: str
    presentation_order: str
    attempt_type: str
    success: bool
    preference: str | None = None
    normalized_document_preference: str | None = None
    confidence: float | None = None
    evidence_strength: str | None = None
    reason_code: str | None = None
    raw_response_hash: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_seconds: float | None = None
    from_cache: bool = False
    parse_failed: bool = False
    inference_attempted: bool = True
    error_category: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReserveDecision:
    request_hash: str
    dataset: str
    query_id: str
    provider: str
    pair_id: str
    trigger: str
    priority: int
    scheduled: bool
    skip_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TerminalOutcome:
    dataset: str
    query_id: str
    provider: str
    ranking: list[str]
    ndcg_at_5: float | None
    mrr: float | None
    recall_at_5: float | None
    has_qrels: bool
    missing_qrels_reason: str | None
    prior_agreement_diagnostic: dict[str, Any]
    n_judgments_used: int
    policy_replay_ready: bool = False
    executed_policies: list[str] = field(default_factory=list)
    judgment_collection_note: str = (
        "Ranking derived from the collected shared pairwise judgments via a "
        "win-graph feedback-arc-set ranking; this is a judgment-collection "
        "diagnostic, not the output of an executed acquisition policy."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
