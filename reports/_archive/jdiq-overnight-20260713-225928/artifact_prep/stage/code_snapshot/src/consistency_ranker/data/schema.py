"""
schema.py
=========
Common internal data schema for the consistency-aware ranking project.

All dataset loaders normalise their data to these dataclasses before
passing them to downstream modules (graph construction, evaluation, etc.).

Serialisation helpers convert to/from plain dicts for JSON-lines storage.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Query:
    """A retrieval or ranking query."""

    query_id: str
    """Unique string identifier."""
    text: str
    """The query text."""
    metadata: dict[str, Any] = field(default_factory=dict)
    """Optional extra fields (dataset-specific)."""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Query":
        return cls(
            query_id=str(d["query_id"]),
            text=str(d["text"]),
            metadata=d.get("metadata", {}),
        )


@dataclass
class Document:
    """A document in the retrieval corpus."""

    doc_id: str
    """Unique string identifier."""
    text: str
    """The document body text."""
    title: str = ""
    """Optional document title."""
    metadata: dict[str, Any] = field(default_factory=dict)
    """Optional extra fields."""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Document":
        return cls(
            doc_id=str(d["doc_id"]),
            text=str(d["text"]),
            title=str(d.get("title", "")),
            metadata=d.get("metadata", {}),
        )


@dataclass
class QrelEntry:
    """A single relevance judgement: query → document relevance."""

    query_id: str
    doc_id: str
    relevance: int
    """Relevance grade. Typically 0 (not relevant) or 1 (relevant).
    Multi-grade datasets may use higher values."""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "QrelEntry":
        return cls(
            query_id=str(d["query_id"]),
            doc_id=str(d["doc_id"]),
            relevance=int(d["relevance"]),
        )


@dataclass
class CandidateRanking:
    """A ranked list of candidate documents for a query."""

    query_id: str
    ranked_doc_ids: list[str]
    """Document ids in descending relevance order (best first)."""
    scores: list[float] | None = None
    """Optional numeric scores aligned with ranked_doc_ids."""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CandidateRanking":
        return cls(
            query_id=str(d["query_id"]),
            ranked_doc_ids=[str(x) for x in d["ranked_doc_ids"]],
            scores=d.get("scores"),
        )


@dataclass
class PairwisePreference:
    """A single pairwise preference derived from relevance labels.

    Represents the judgement that *winner_doc_id* is preferred over
    *loser_doc_id* for the given query.
    """

    query_id: str
    winner_doc_id: str
    loser_doc_id: str
    weight: float = 1.0
    """Confidence / preference strength (> 0). Defaults to 1.0."""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PairwisePreference":
        return cls(
            query_id=str(d["query_id"]),
            winner_doc_id=str(d["winner_doc_id"]),
            loser_doc_id=str(d["loser_doc_id"]),
            weight=float(d.get("weight", 1.0)),
        )
