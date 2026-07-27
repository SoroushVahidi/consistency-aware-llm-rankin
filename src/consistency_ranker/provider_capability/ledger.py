"""Hard-capped live-call ledger for provider capability audits."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from consistency_ranker.provider_capability.sanitize import redact_text, response_hash


class LiveCallCapExceeded(RuntimeError):
    """Raised when a request would exceed a hard safety cap."""


@dataclass
class LiveCallLedger:
    """Append-only ledger that refuses requests exceeding hard caps."""

    max_total_live_calls: int = 16
    max_live_calls_per_provider: int = 4
    max_estimated_cost_usd: float | None = 2.0
    max_total_input_tokens: int = 100_000
    max_total_output_tokens: int = 12_000
    max_retries_per_request: int = 1
    path: Path | None = None

    total_live_calls: int = 0
    calls_by_provider: dict[str, int] = field(default_factory=dict)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float | None = 0.0
    cost_known: bool = False
    retries: int = 0
    entries: list[dict[str, Any]] = field(default_factory=list)
    completed_request_hashes: set[str] = field(default_factory=set)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def load(self) -> None:
        if self.path is None or not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            self.entries.append(rec)
            if rec.get("phase") == "after" and rec.get("success"):
                rh = rec.get("request_hash")
                if rh:
                    self.completed_request_hashes.add(str(rh))
            if rec.get("phase") == "after":
                self.total_live_calls = max(
                    self.total_live_calls, int(rec.get("cumulative_calls") or 0)
                )
                p = str(rec.get("provider") or "")
                if p:
                    self.calls_by_provider[p] = max(
                        self.calls_by_provider.get(p, 0),
                        int(rec.get("cumulative_provider_calls") or 0),
                    )
                self.prompt_tokens = max(
                    self.prompt_tokens, int(rec.get("cumulative_prompt_tokens") or 0)
                )
                self.completion_tokens = max(
                    self.completion_tokens,
                    int(rec.get("cumulative_completion_tokens") or 0),
                )
                if rec.get("is_retry"):
                    self.retries += 1

    def already_completed(self, request_hash: str) -> bool:
        return request_hash in self.completed_request_hashes

    def _would_exceed(
        self,
        provider: str,
        *,
        estimated_input_tokens: int,
        max_output_tokens: int,
        estimated_usd: float | None,
    ) -> str | None:
        if self.total_live_calls >= self.max_total_live_calls:
            return "max_total_live_calls"
        if self.calls_by_provider.get(provider, 0) >= self.max_live_calls_per_provider:
            return "max_live_calls_per_provider"
        if self.prompt_tokens + max(0, estimated_input_tokens) > self.max_total_input_tokens:
            return "max_total_input_tokens"
        if self.completion_tokens + max(0, max_output_tokens) > self.max_total_output_tokens:
            return "max_total_output_tokens"
        if (
            self.max_estimated_cost_usd is not None
            and self.cost_known
            and estimated_usd is not None
            and (self.estimated_cost_usd or 0.0) + float(estimated_usd)
            > self.max_estimated_cost_usd
        ):
            return "max_estimated_cost_usd"
        return None

    def begin_request(
        self,
        *,
        provider: str,
        purpose: str,
        request_hash: str,
        estimated_input_tokens: int,
        max_output_tokens: int,
        is_retry: bool = False,
        estimated_usd: float | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            if self.already_completed(request_hash) and not is_retry:
                raise LiveCallCapExceeded(
                    f"Request already completed (hash={request_hash[:12]}…); "
                    "refusing duplicate live call."
                )
            reason = self._would_exceed(
                provider,
                estimated_input_tokens=estimated_input_tokens,
                max_output_tokens=max_output_tokens,
                estimated_usd=estimated_usd,
            )
            if reason:
                raise LiveCallCapExceeded(f"Refusing live call: {reason}")
            seq = self.total_live_calls + 1
            entry = {
                "phase": "before",
                "provider": provider,
                "sequential_request_number": seq,
                "purpose": purpose,
                "estimated_input_tokens": int(estimated_input_tokens),
                "max_output_tokens": int(max_output_tokens),
                "is_retry": bool(is_retry),
                "request_hash": request_hash,
                "cumulative_calls": self.total_live_calls,
                "cumulative_provider_calls": self.calls_by_provider.get(provider, 0),
            }
            self._append(entry)
            return entry

    def finish_request(
        self,
        *,
        provider: str,
        purpose: str,
        request_hash: str,
        success: bool,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_seconds: float | None = None,
        parse_status: str | None = None,
        raw_response: str = "",
        estimated_usd: float | None = None,
        is_retry: bool = False,
        error: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            self.total_live_calls += 1
            self.calls_by_provider[provider] = self.calls_by_provider.get(provider, 0) + 1
            self.prompt_tokens += int(prompt_tokens or 0)
            self.completion_tokens += int(completion_tokens or 0)
            if is_retry:
                self.retries += 1
            if estimated_usd is not None:
                self.cost_known = True
                self.estimated_cost_usd = float(self.estimated_cost_usd or 0.0) + float(
                    estimated_usd
                )
            if success:
                self.completed_request_hashes.add(request_hash)
            entry = {
                "phase": "after",
                "provider": provider,
                "purpose": purpose,
                "request_hash": request_hash,
                "success": bool(success),
                "prompt_tokens": int(prompt_tokens or 0),
                "completion_tokens": int(completion_tokens or 0),
                "latency_seconds": latency_seconds,
                "parse_status": parse_status,
                "raw_response_hash": response_hash(raw_response),
                "estimated_cost_usd": estimated_usd,
                "is_retry": bool(is_retry),
                "error": redact_text(error) if error else None,
                "cumulative_calls": self.total_live_calls,
                "cumulative_provider_calls": self.calls_by_provider.get(provider, 0),
                "cumulative_prompt_tokens": self.prompt_tokens,
                "cumulative_completion_tokens": self.completion_tokens,
                "cumulative_estimated_cost_usd": (
                    self.estimated_cost_usd if self.cost_known else None
                ),
            }
            self._append(entry)
            return entry

    def summary(self) -> dict[str, Any]:
        return {
            "total_live_calls": self.total_live_calls,
            "live_calls_by_provider": dict(self.calls_by_provider),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "estimated_cost_usd": self.estimated_cost_usd if self.cost_known else None,
            "cost_known": self.cost_known,
            "retries": self.retries,
            "caps": {
                "max_total_live_calls": self.max_total_live_calls,
                "max_live_calls_per_provider": self.max_live_calls_per_provider,
                "max_estimated_cost_usd": self.max_estimated_cost_usd,
                "max_total_input_tokens": self.max_total_input_tokens,
                "max_total_output_tokens": self.max_total_output_tokens,
                "max_retries_per_request": self.max_retries_per_request,
            },
            "completed_request_hashes": sorted(self.completed_request_hashes),
        }

    def _append(self, entry: dict[str, Any]) -> None:
        self.entries.append(entry)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
