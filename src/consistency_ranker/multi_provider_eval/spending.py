"""Per-provider and global spending / call ceilings."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SpendingCeiling:
    """Stop safely when ceilings are reached (never invent unlimited spend)."""

    max_new_calls_global: int | None = 200
    max_new_calls_per_provider: dict[str, int] = field(
        default_factory=lambda: {
            "azure": 80,
            "cohere": 60,
            "fireworks": 40,
            "gemini": 60,
            "openai": 40,
        }
    )
    max_prompt_tokens_global: int | None = 500_000
    max_estimated_usd_global: float | None = None  # optional; None = tokens-only

    new_calls_global: int = 0
    new_calls_by_provider: dict[str, int] = field(default_factory=dict)
    prompt_tokens_global: int = 0
    completion_tokens_global: int = 0
    estimated_usd_global: float = 0.0
    stopped_reason: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def allow(self, provider: str) -> bool:
        with self._lock:
            if self.stopped_reason:
                return False
            if (
                self.max_new_calls_global is not None
                and self.new_calls_global >= self.max_new_calls_global
            ):
                self.stopped_reason = "global_call_ceiling"
                return False
            cap = self.max_new_calls_per_provider.get(provider)
            if cap is not None and self.new_calls_by_provider.get(provider, 0) >= cap:
                return False
            if (
                self.max_prompt_tokens_global is not None
                and self.prompt_tokens_global >= self.max_prompt_tokens_global
            ):
                self.stopped_reason = "global_token_ceiling"
                return False
            if (
                self.max_estimated_usd_global is not None
                and self.estimated_usd_global >= self.max_estimated_usd_global
            ):
                self.stopped_reason = "global_usd_ceiling"
                return False
            return True

    def record(
        self,
        provider: str,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        estimated_usd: float | None = None,
    ) -> None:
        with self._lock:
            self.new_calls_global += 1
            self.new_calls_by_provider[provider] = (
                self.new_calls_by_provider.get(provider, 0) + 1
            )
            self.prompt_tokens_global += int(prompt_tokens or 0)
            self.completion_tokens_global += int(completion_tokens or 0)
            if estimated_usd is not None:
                self.estimated_usd_global += float(estimated_usd)

    def summary(self) -> dict[str, Any]:
        return {
            "new_calls_global": self.new_calls_global,
            "new_calls_by_provider": dict(self.new_calls_by_provider),
            "prompt_tokens_global": self.prompt_tokens_global,
            "completion_tokens_global": self.completion_tokens_global,
            "estimated_usd_global": self.estimated_usd_global,
            "stopped_reason": self.stopped_reason,
            "ceilings": {
                "max_new_calls_global": self.max_new_calls_global,
                "max_new_calls_per_provider": dict(self.max_new_calls_per_provider),
                "max_prompt_tokens_global": self.max_prompt_tokens_global,
                "max_estimated_usd_global": self.max_estimated_usd_global,
            },
        }
