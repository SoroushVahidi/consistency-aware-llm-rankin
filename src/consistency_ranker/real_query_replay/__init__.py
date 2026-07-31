"""Offline real-query repair / policy-utility replay (no network calls)."""

from consistency_ranker.real_query_replay.evidence_index import (
    build_canonical_evidence_index,
)
from consistency_ranker.real_query_replay.network_guard import assert_no_network

__all__ = [
    "assert_no_network",
    "build_canonical_evidence_index",
]
