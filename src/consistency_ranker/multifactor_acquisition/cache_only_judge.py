"""Cache-only judge for offline multifactor replay (never contacts providers)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from consistency_ranker.reliability_repair.pair_evidence import (
    NormalizedEvidence,
    canonical_pair_id,
    normalize_judgment_record,
)


@dataclass
class CacheOnlyJudge:
    """Serve judgments exclusively from a preloaded identity → evidence map.

    Unavailable pairs return ``None`` with an accounting increment. No network
    calls are possible from this object.
    """

    query_id: str
    provider: str
    model: str
    prompt_version: str
    orientation: str
    cache: dict[str, NormalizedEvidence] = field(default_factory=dict)
    n_requests: int = 0
    n_hits: int = 0
    n_misses: int = 0
    n_unique_served: int = 0
    _served: set[str] = field(default_factory=set)
    paid_api_calls: int = 0  # always 0

    @classmethod
    def from_parsed_rows(
        cls,
        rows: list[dict[str, Any]],
        *,
        query_id: str,
        provider: str,
        model: str,
        prompt_version: str,
        orientation: str,
    ) -> "CacheOnlyJudge":
        cache: dict[str, NormalizedEvidence] = {}
        suffix = f"|{provider}|{model}|{prompt_version}|{orientation}"
        for row in rows:
            identity = str(row.get("identity") or "")
            if query_id not in identity:
                continue
            if not identity.endswith(suffix):
                # Also accept rows keyed only by metadata fields.
                if not (
                    str(row.get("provider")) == provider
                    and str(row.get("model")) == model
                    and str(row.get("prompt_version")) == prompt_version
                    and str(row.get("displayed_orientation") or row.get("orientation"))
                    == orientation
                    and str(row.get("query_id") or query_id) == query_id
                ):
                    continue
            if row.get("valid") is False:
                continue
            if int(row.get("z") or 0) == 0 and not row.get("valid", False):
                continue
            ev = normalize_judgment_record(row)
            ev.displayed_orientation = orientation  # type: ignore[assignment]
            ev.provider = provider
            ev.model = model
            ev.prompt_version = prompt_version
            di, dj = str(ev.doc_i), str(ev.doc_j)
            key = (
                f"{canonical_pair_id(query_id, di, dj)}"
                f"|{provider}|{model}|{prompt_version}|{orientation}"
            )
            cache[key] = ev
            if identity:
                cache[identity] = ev
        return cls(
            query_id=query_id,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            orientation=orientation,
            cache=cache,
        )

    def _identity(self, action: Any) -> str:
        return (
            f"{canonical_pair_id(self.query_id, str(action.doc_i), str(action.doc_j))}"
            f"|{self.provider}|{self.model}|{self.prompt_version}|{self.orientation}"
        )

    def available(self, action: Any) -> bool:
        if getattr(action, "action_type", None) == "NO_ACTION":
            return True
        return self._identity(action) in self.cache

    def judge(self, action: Any, *, consumer: str = "offline") -> NormalizedEvidence | None:
        if getattr(action, "action_type", None) == "NO_ACTION":
            return None
        self.n_requests += 1
        key = self._identity(action)
        ev = self.cache.get(key)
        if ev is None:
            self.n_misses += 1
            return None
        self.n_hits += 1
        if key not in self._served:
            self._served.add(key)
            self.n_unique_served += 1
        return ev
