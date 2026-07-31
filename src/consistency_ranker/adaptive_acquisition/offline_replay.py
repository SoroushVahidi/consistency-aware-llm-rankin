"""Provenance-safe offline replay of cached judgments.

A policy may only *select* actions that exist in the replay pool; it never sees
the outcome of an unselected action. Each cached record is consumed at most once,
so repeated selections draw down real coverage. Unavailable actions are reported
as ``unavailable`` — explicitly distinct from a model abstention. Missing
outcomes are **never** filled from qrels or any other label source.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from consistency_ranker.reliability_repair.pair_evidence import (
    NormalizedEvidence,
    normalize_judgment_record,
)


def _record_key(rec: dict) -> tuple[str, str, str, str, str]:
    return (
        str(rec.get("canonical_pair_id")),
        str(rec.get("provider")),
        str(rec.get("model")),
        str(rec.get("prompt_version")),
        str(rec.get("displayed_orientation")),
    )


def _action_key(action) -> tuple[str, str, str, str, str]:
    return (
        str(action.pair_id),
        str(action.provider),
        str(action.model),
        str(action.prompt_version),
        str(action.orientation),
    )


@dataclass
class ReplayPool:
    """Deterministic, single-use pool of provenance-safe judgment records."""

    query_id: str
    _queues: dict[tuple, deque] = field(default_factory=lambda: defaultdict(deque))
    n_records: int = 0
    n_consumed: int = 0
    n_requests: int = 0
    n_unavailable: int = 0

    @classmethod
    def from_records(cls, query_id: str, records: list[dict]) -> "ReplayPool":
        pool = cls(query_id=query_id)
        # deterministic ordering by cache_key / timestamp for reproducibility
        ordered = sorted(
            (r for r in records if str(r.get("query_id")) == query_id),
            key=lambda r: (str(r.get("cache_key", "")), str(r.get("timestamp_utc", ""))),
        )
        for r in ordered:
            if not r.get("provider"):
                continue
            pool._queues[_record_key(r)].append(r)
            pool.n_records += 1
        return pool

    def has(self, action) -> bool:
        return bool(self._queues.get(_action_key(action)))

    def available_actions(self, actions: list) -> list:
        """Filter to actions with at least one remaining cached record."""
        avail_counts: dict[tuple, int] = {}
        out = []
        for a in actions:
            if getattr(a, "action_type", None) == "NO_ACTION":
                out.append(a)
                continue
            key = _action_key(a)
            have = len(self._queues.get(key, ())) - avail_counts.get(key, 0)
            if have > 0:
                avail_counts[key] = avail_counts.get(key, 0) + 1
                out.append(a)
        return out

    def judge(self, action) -> NormalizedEvidence | None:
        """Return the next cached judgment for ``action`` or ``None`` if unavailable."""
        self.n_requests += 1
        key = _action_key(action)
        q = self._queues.get(key)
        if not q:
            self.n_unavailable += 1
            return None
        rec = q.popleft()
        self.n_consumed += 1
        ev = normalize_judgment_record(rec)
        # tag repetition index by consumption order to keep signatures unique
        return ev

    def coverage(self, generated_actions: list) -> dict[str, Any]:
        def _is_action(a) -> bool:
            return getattr(a, "action_type", None) != "NO_ACTION"

        total = sum(1 for a in generated_actions if _is_action(a))
        avail = len([a for a in self.available_actions(list(generated_actions)) if _is_action(a)])
        return {
            "n_generated_actions": total,
            "n_available_actions": avail,
            "action_coverage": (avail / total) if total else 0.0,
            "n_records": self.n_records,
            "n_consumed": self.n_consumed,
            "n_unavailable_requests": self.n_unavailable,
        }


def load_replay_pools(records: list[dict]) -> dict[str, ReplayPool]:
    """Group provenance-safe records into one replay pool per query."""
    by_q: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        qid = str(r.get("query_id"))
        if qid and r.get("provider"):
            by_q[qid].append(r)
    return {qid: ReplayPool.from_records(qid, recs) for qid, recs in by_q.items()}


__all__ = ["ReplayPool", "load_replay_pools"]
