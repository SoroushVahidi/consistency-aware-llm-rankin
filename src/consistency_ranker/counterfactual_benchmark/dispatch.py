"""Fail-closed, per-provider call dispatch. No provider fallback, ever.

A failed call to one provider produces a failed cell for that provider; it
never substitutes another provider or model. The real network path
(``rerankers.llm_pairwise._call_llm``) is injected as ``call_fn`` so tests
can supply a deterministic fake without touching the network.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Protocol

from consistency_ranker.counterfactual_benchmark.prompt_renderer import (
    estimate_tokens_conservative,
)
from consistency_ranker.failure_mining.llm_runner import classify_llm_error
from consistency_ranker.multi_provider_eval.providers import _build_pairwise_config
from consistency_ranker.provider_capability.sanitize import env_names_for_provider


class CallFn(Protocol):
    def __call__(self, prompt: str, config: Any) -> tuple[str, object]: ...


@dataclass
class DispatchResult:
    raw_response: str
    prompt_tokens: int
    completion_tokens: int
    latency_seconds: float
    error_category: str | None
    error_message: str | None


def preflight_provider_ready(provider: str) -> tuple[bool, str]:
    """Check environment-variable *presence* only; never read or log values."""
    names = env_names_for_provider(provider)
    if not names:
        return True, "no_known_env_requirement"
    present = [n for n in names if os.environ.get(n)]
    if present:
        return True, f"env_present:{','.join(sorted(present))}"
    return False, f"missing_env:{','.join(names)}"


def _usage_tokens(usage: object | None) -> tuple[int, int]:
    if usage is None:
        return 0, 0
    pt = int(getattr(usage, "prompt_tokens", 0) or 0)
    ct = int(getattr(usage, "completion_tokens", 0) or 0)
    return pt, ct


def call_provider(
    *,
    provider: str,
    model_id: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    call_fn: CallFn | None = None,
) -> DispatchResult:
    """Issue exactly one live call to *provider*. Never falls back to another."""
    if call_fn is None:
        from rerankers.llm_pairwise import _call_llm as _real_call_llm

        call_fn = _real_call_llm

    ready, reason = preflight_provider_ready(provider)
    if not ready:
        return DispatchResult(
            raw_response="",
            prompt_tokens=0,
            completion_tokens=0,
            latency_seconds=0.0,
            error_category="missing_credentials",
            error_message=reason,
        )

    config, _call_cfg = _build_pairwise_config(
        provider,
        model=model_id,
        temperature=temperature,
        max_tokens=max_tokens,
        dry_run=False,
    )
    t0 = time.perf_counter()
    try:
        raw, usage = call_fn(prompt, config)
    except Exception as exc:  # noqa: BLE001 - classified below, never re-raised bare
        latency = time.perf_counter() - t0
        return DispatchResult(
            raw_response="",
            prompt_tokens=0,
            completion_tokens=0,
            latency_seconds=latency,
            error_category=classify_llm_error(exc),
            error_message=str(exc)[:500],
        )
    latency = time.perf_counter() - t0
    pt, ct = _usage_tokens(usage)
    return DispatchResult(
        raw_response=raw,
        prompt_tokens=pt,
        completion_tokens=ct,
        latency_seconds=latency,
        error_category=None,
        error_message=None,
    )


def estimate_request_tokens(prompt: str, *, max_output_tokens: int) -> tuple[int, int]:
    """Conservative (prompt_tokens, max_output_tokens) estimate for cap checks."""
    return estimate_tokens_conservative(prompt), max_output_tokens
