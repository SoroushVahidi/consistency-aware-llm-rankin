"""LLM reranking integration for failure mining with caching and provider detection."""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rerankers.common import BudgetTracker, RerankerResult
from rerankers.llm_pairwise import LLMCallStats, PairwiseConfig, collect_all_pairs


PROMPT_VERSION = "pairwise_comparison_v1"
SUPPORTED_PROVIDERS = ("cohere", "gemini", "cloudrift", "azure", "openai", "fireworks")

# Coarse, stable failure categories. Previously every LLM call failure --
# authentication, a nonexistent model, a genuinely exhausted budget, and (as
# found investigating CloudRift) a provider-side "no active servers for this
# model" 503 -- was collapsed into a single "unavailable_or_budget" string in
# api_failures.csv, making a pure infra-availability issue look identical to
# an account-budget problem. classify_llm_error() distinguishes them so the
# circuit breaker and reports can act on (and report) the real cause.
ERROR_CATEGORIES = (
    "auth_error",
    "permission_error",
    "model_not_found",
    "model_unavailable",
    "rate_limited",
    "budget_exhausted",
    "timeout",
    "connection_error",
    "malformed_request",
    "malformed_response",
    "server_error",
    "unknown_error",
)


def classify_llm_error(exc: BaseException) -> str:
    """Map a raised exception to one of ERROR_CATEGORIES.

    Uses the openai SDK's exception hierarchy where available (this repo's
    "openai"-family providers -- cohere, cloudrift, azure, fireworks, openai
    itself -- all go through openai.OpenAI()), then falls back to message
    substring matching for the gemini SDK and anything else.
    """
    msg = str(exc).lower()

    try:
        import openai

        if isinstance(exc, openai.AuthenticationError):
            return "auth_error"
        if isinstance(exc, openai.PermissionDeniedError):
            return "permission_error"
        if isinstance(exc, openai.NotFoundError):
            return "model_not_found"
        if isinstance(exc, openai.RateLimitError):
            if "insufficient_quota" in msg or "exceeded your current quota" in msg:
                return "budget_exhausted"
            return "rate_limited"
        if isinstance(exc, openai.APITimeoutError):
            return "timeout"
        if isinstance(exc, openai.APIConnectionError):
            return "connection_error"
        if isinstance(exc, openai.BadRequestError):
            return "malformed_request"
        if isinstance(exc, openai.InternalServerError):
            if "no active server" in msg or "no healthy" in msg or "no available" in msg:
                return "model_unavailable"
            return "server_error"
    except ImportError:
        pass

    if "no active server" in msg:
        return "model_unavailable"
    if "insufficient_quota" in msg or "exceeded your current quota" in msg or "insufficient balance" in msg:
        return "budget_exhausted"
    if "response.text is none" in msg or "empty response" in msg or "empty content" in msg:
        return "malformed_response"
    if "timed out" in msg or "timeout" in msg:
        return "timeout"
    if "401" in msg or "unauthorized" in msg or "invalid api key" in msg or "authentication" in msg:
        return "auth_error"
    if "403" in msg or "forbidden" in msg or "permission" in msg:
        return "permission_error"
    if "404" in msg or "not found" in msg:
        return "model_not_found"
    if "429" in msg or "rate limit" in msg:
        return "rate_limited"
    if "502" in msg or "503" in msg or "504" in msg or "500" in msg:
        return "server_error"
    return "unknown_error"


@dataclass
class ProviderStatus:
    provider: str
    available: bool
    reason: str
    # "api_key" or "vertex" for gemini; None for providers with only one mode.
    mode: str | None = None


# Error categories that mean "this provider will keep failing every call for
# the rest of the run" (a dead/unserved model, wrong credentials, wrong model
# name) as opposed to transient conditions (rate limits, timeouts) that are
# worth continuing to retry per-query. Drives both the one-time startup
# health check and the mid-run consecutive-failure circuit breaker below.
PERSISTENT_FAILURE_CATEGORIES = frozenset(
    {"model_unavailable", "model_not_found", "auth_error", "permission_error"}
)


def health_check_provider(provider: str) -> dict[str, Any]:
    """Make one trivial live call to check a provider is actually usable.

    Distinct from detect_llm_providers(), which only checks that credentials
    are *present* in the environment -- it says nothing about whether the
    configured model is actually serving. Found in production: CloudRift's
    credentials were present but the configured model returned a 503 "No
    active servers" on every single call (113/114 failures in one overnight
    run), burning the model's full MAX_RETRIES backoff on every query before
    giving up. One cheap health-check call at startup catches this once
    instead of hundreds of times.
    """
    from rerankers.llm_pairwise import PairwiseConfig, _call_llm

    call_cfg = _provider_call_config(provider)
    config_kwargs: dict[str, Any] = dict(
        provider=call_cfg["family"],
        model=call_cfg["model"],
        api_key=call_cfg.get("api_key"),
        base_url=call_cfg.get("base_url"),
        max_tokens=8,
        gemini_use_vertex=bool(call_cfg.get("gemini_use_vertex", False)),
        vertex_project=call_cfg.get("vertex_project"),
        vertex_location=call_cfg.get("vertex_location"),
        extra_body=call_cfg.get("extra_body"),
    )
    if call_cfg.get("max_tokens_override") is not None:
        config_kwargs["max_tokens"] = call_cfg["max_tokens_override"]
    config = PairwiseConfig(**config_kwargs)
    try:
        text, _usage = _call_llm("Reply with exactly the word OK.", config)
        return {"provider": provider, "model": call_cfg["model"], "ok": True, "category": None, "message": text}
    except Exception as exc:
        category = classify_llm_error(exc)
        return {
            "provider": provider,
            "model": call_cfg["model"],
            "ok": False,
            "category": category,
            "message": str(exc)[:500],
        }


def _gemini_vertex_config() -> dict[str, str] | None:
    """Resolve Vertex AI config for Gemini from env + Application Default
    Credentials, without making any network call or exposing secrets.

    Returns a dict with "project" and "location" if Vertex AI mode looks
    usable (``GOOGLE_GENAI_USE_VERTEXAI`` is truthy, a project can be
    resolved, and ADC can be loaded locally), else None.
    """
    if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").strip().lower() not in ("1", "true", "yes"):
        return None
    project = (
        os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCLOUD_PROJECT")
        or os.environ.get("GCP_PROJECT")
        or os.environ.get("VERTEXAI_PROJECT")
    )
    location = os.environ.get("GOOGLE_CLOUD_LOCATION") or os.environ.get("VERTEX_LOCATION")
    try:
        import google.auth

        creds, adc_project = google.auth.default()
        if not project:
            project = adc_project
    except Exception:
        return None
    if not project:
        return None
    return {"project": project, "location": location or "us-central1"}


def detect_llm_providers(requested: list[str]) -> list[ProviderStatus]:
    """Check which LLM providers have credentials without exposing secrets."""
    statuses: list[ProviderStatus] = []
    env_map = {
        "cohere": ["COHERE_API_KEY"],
        "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "cloudrift": ["CLOUDRIFT_API_KEY"],
        "azure": ["AZURE_OPENAI_API_KEY"],
        "openai": ["OPENAI_API_KEY"],
        "fireworks": ["FIREWORKS_API_KEY"],
    }
    for p in requested:
        if p == "none":
            continue
        if p not in env_map:
            statuses.append(ProviderStatus(p, False, "unknown provider"))
            continue
        if p == "gemini":
            has_api_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
            if has_api_key:
                statuses.append(ProviderStatus(p, True, "credentials present (direct API key)", mode="api_key"))
                continue
            vertex_cfg = _gemini_vertex_config()
            if vertex_cfg is not None:
                statuses.append(
                    ProviderStatus(
                        p,
                        True,
                        f"credentials present (Vertex AI, project={vertex_cfg['project']}, "
                        f"location={vertex_cfg['location']})",
                        mode="vertex",
                    )
                )
            else:
                statuses.append(
                    ProviderStatus(
                        p,
                        False,
                        "missing env: GEMINI_API_KEY, GOOGLE_API_KEY "
                        "(and no usable Vertex AI config: GOOGLE_GENAI_USE_VERTEXAI + project + ADC)",
                    )
                )
            continue
        missing = [k for k in env_map[p] if not os.environ.get(k)]
        if p == "azure":
            if not (os.environ.get("AZURE_OPENAI_ENDPOINT") or os.environ.get("AZURE_API_BASE")):
                missing.append("AZURE_OPENAI_ENDPOINT or AZURE_API_BASE")
            if not (os.environ.get("AZURE_OPENAI_DEPLOYMENT") or os.environ.get("AZURE_OPENAI_STRONG_DEPLOYMENT")):
                missing.append("AZURE_OPENAI_DEPLOYMENT")
        if missing:
            statuses.append(ProviderStatus(p, False, f"missing env: {', '.join(missing)}"))
        else:
            statuses.append(ProviderStatus(p, True, "credentials present"))
    return statuses


def _provider_call_config(provider: str) -> dict[str, Any]:
    """Map failure-mining provider name to llm_pairwise call parameters.

    Cohere, CloudRift, and Azure are all reached through OpenAI-compatible
    chat-completions endpoints (Cohere's "compatibility" API, CloudRift's
    OpenAI-compatible inference API, Azure OpenAI's v1 API), so they share
    the "openai" provider family in llm_pairwise but override api_key/base_url
    per provider. Gemini uses its native SDK path.
    """
    if provider == "gemini":
        has_api_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
        if has_api_key:
            return {
                "family": "gemini",
                "model": os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
                "mode": "api_key",
            }
        vertex_cfg = _gemini_vertex_config()
        if vertex_cfg is not None:
            return {
                "family": "gemini",
                # gemini-2.0-flash is not published on Vertex AI for every
                # project/region; gemini-2.5-flash is confirmed available.
                # Override via GEMINI_VERTEX_MODEL if a project needs a
                # different one.
                "model": os.environ.get("GEMINI_VERTEX_MODEL", "gemini-2.5-flash"),
                "mode": "vertex",
                "gemini_use_vertex": True,
                "vertex_project": vertex_cfg["project"],
                "vertex_location": vertex_cfg["location"],
            }
        # No usable credentials in either mode; fall through with the
        # api-key default so the resulting failure message is unambiguous.
        return {
            "family": "gemini",
            "model": os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
            "mode": "api_key",
        }
    if provider == "azure":
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT") or os.environ.get("AZURE_API_BASE")
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT") or os.environ.get(
            "AZURE_OPENAI_STRONG_DEPLOYMENT", "gpt-4o-mini"
        )
        return {
            "family": "openai",
            "model": deployment,
            "api_key": os.environ.get("AZURE_OPENAI_API_KEY") or os.environ.get("AZURE_API_KEY"),
            "base_url": endpoint,
            # The Azure latency diagnostic found the ~151s/query median was
            # pure serial-execution arithmetic (210 sequential HTTP round
            # trips at ~700ms each; Azure's own usage.latency_checkpoint
            # showed only ~150-230ms of actual server-side inference per
            # call), not a slow model or throttling -- the deployment's
            # 250-requests/60s rate limit has ample headroom. A live,
            # full-scale 210-call burst at concurrency=8 completed in 22.4s
            # with 0 errors. Set AZURE_OPENAI_CONCURRENCY=1 to reproduce the
            # original fully-serial behavior.
            "concurrency": int(os.environ.get("AZURE_OPENAI_CONCURRENCY", "8")),
        }
    if provider == "fireworks":
        # The previous default, "accounts/fireworks/models/llama-v3p1-8b-instruct",
        # has been removed from Fireworks' serverless catalog -- every call
        # against it returns 404 "Model not found, inaccessible, and/or not
        # deployed" (confirmed via a live GET /v1/models call against this
        # account, which lists gpt-oss-120b, glm-5p1/5p2, deepseek-v4-pro,
        # kimi-k2p5/k2p6 but no llama variant at all). gpt-oss-120b is
        # confirmed live and chat-capable for this account.
        fw_model = os.environ.get("FIREWORKS_MODEL", "accounts/fireworks/models/gpt-oss-120b")
        cfg: dict[str, Any] = {
            "family": "openai",
            "model": fw_model,
            "api_key": os.environ.get("FIREWORKS_API_KEY"),
            "base_url": os.environ.get(
                "FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1"
            ),
        }
        if "gpt-oss" in fw_model.lower():
            # gpt-oss is a reasoning model: it spends max_tokens on hidden
            # reasoning_content before emitting visible content, so the
            # pipeline's normal max_tokens=4 (sized for a single A/B letter
            # on non-reasoning models) silently returns content=None. Bound
            # reasoning effort and give enough budget for reasoning + the
            # answer to both fit. 128 (empirically ~19-48 completion tokens
            # for a *trivial* health-check prompt at reasoning_effort=low)
            # was not enough headroom: a real pairwise-comparison prompt (with
            # full query + two candidate document snippets) hit
            # finish_reason="length" with empty content in a live smoke test.
            # 512 leaves comfortable margin for real-prompt reasoning depth
            # while reasoning_effort=low keeps it from ballooning further.
            cfg["extra_body"] = {"reasoning_effort": "low"}
            cfg["max_tokens_override"] = int(os.environ.get("FIREWORKS_MAX_TOKENS", "512"))
        return cfg
    if provider == "cohere":
        return {
            "family": "openai",
            "model": os.environ.get("COHERE_MODEL", "command-r-plus-08-2024"),
            "api_key": os.environ.get("COHERE_API_KEY"),
            "base_url": os.environ.get(
                "COHERE_BASE_URL", "https://api.cohere.ai/compatibility/v1"
            ),
            # The Cohere latency diagnostic found the same ~60s/query serial-
            # execution pattern as Azure (210 sequential calls/query), but a
            # *tighter* real per-minute rate limit than Azure's. An isolated
            # single 210-call burst at concurrency=8 looked clean (0 errors,
            # 7.3s) only because it ran right after a quota-reset window --
            # two consecutive back-to-back 210-call bursts (the realistic
            # shape of a sustained mining run) at concurrency=8 hit 130/210
            # then 210/210 real 429s ("past the per minute request limit").
            # Concurrency=4 was validated safe across two consecutive
            # back-to-back full-scale bursts (0 errors both times, ~14s
            # each, vs. ~60s serial). Set COHERE_CONCURRENCY=1 to reproduce
            # the original serial behavior.
            "concurrency": int(os.environ.get("COHERE_CONCURRENCY", "4")),
        }
    if provider == "cloudrift":
        return {
            "family": "openai",
            "model": os.environ.get("CLOUDRIFT_MODEL", "gpt-4o-mini"),
            "api_key": os.environ.get("CLOUDRIFT_API_KEY"),
            "base_url": os.environ.get("CLOUDRIFT_BASE_URL"),
        }
    return {
        "family": "openai",
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "api_key": os.environ.get("OPENAI_API_KEY"),
    }


@dataclass
class LLMRunner:
    output_path: Path
    cache_dir: Path
    max_calls: int | None = None
    use_cache: bool = True
    records: list[dict] = field(default_factory=list)
    prompt_log_path: Path | None = None
    # Set by run_pairwise_rerank() on failure so callers (e.g. the overnight
    # orchestrator's api_failures.csv writer) can report the real cause
    # instead of a generic placeholder. None after a successful call.
    last_error: dict[str, Any] | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._budget = BudgetTracker(max_calls=self.max_calls)
        if self.prompt_log_path is None:
            self.prompt_log_path = self.output_path.parent / "llm_prompt_call_log.jsonl"
        self.prompt_log_path.parent.mkdir(parents=True, exist_ok=True)

    def _append_record(self, record: dict) -> None:
        self.records.append(record)
        with self.output_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    def _append_prompt_details(
        self, *, provider: str, model: str, detail_sink: list[dict]
    ) -> None:
        if not detail_sink:
            return
        timestamp = time.time()
        with self.prompt_log_path.open("a", encoding="utf-8") as fh:
            for detail in detail_sink:
                row = {"provider": provider, "model": model, "timestamp": timestamp, **detail}
                fh.write(json.dumps(row) + "\n")

    def run_pairwise_rerank(
        self,
        *,
        provider: str,
        query_id: str,
        query_text: str,
        doc_texts: dict[str, str],
        candidate_ids: list[str],
    ) -> dict[str, Any] | None:
        """Run LLM pairwise reranking; return ranking + full API record."""
        self.last_error = None
        status = detect_llm_providers([provider])
        if not status or not status[0].available:
            self.last_error = {
                "category": "auth_error",
                "message": status[0].reason if status else "unknown",
                "model": None,
                "http_status": None,
            }
            self._append_record(
                {
                    "provider": provider,
                    "query_id": query_id,
                    "available": False,
                    "reason": status[0].reason if status else "unknown",
                }
            )
            return None

        if self._budget.budget_exhausted:
            self.last_error = {
                "category": "budget_exhausted",
                "message": "local max_calls budget exhausted",
                "model": None,
                "http_status": None,
            }
            return None

        call_cfg = _provider_call_config(provider)
        pw_provider = call_cfg["family"]
        model = call_cfg["model"]
        # Isolate each provider+model's pairwise-judgment cache in its own
        # subdirectory. collect_all_pairs() writes its on-disk cache under a
        # fixed "llm_pairwise" filename per cache_dir, so without this a
        # second provider (e.g. cloudrift) would silently read back
        # judgments cached by a different provider (e.g. cohere) for the
        # same query/candidate pair.
        provider_cache_dir = self.cache_dir / f"{provider}_{model}".replace("/", "_")
        config_kwargs: dict[str, Any] = dict(
            provider=pw_provider,
            model=model,
            api_key=call_cfg.get("api_key"),
            base_url=call_cfg.get("base_url"),
            cache_dir=provider_cache_dir if self.use_cache else None,
            max_calls=self.max_calls,
            dry_run=False,
            debias_position=True,
            gemini_use_vertex=bool(call_cfg.get("gemini_use_vertex", False)),
            vertex_project=call_cfg.get("vertex_project"),
            vertex_location=call_cfg.get("vertex_location"),
            extra_body=call_cfg.get("extra_body"),
            concurrency=int(call_cfg.get("concurrency", 1)),
        )
        if call_cfg.get("max_tokens_override") is not None:
            config_kwargs["max_tokens"] = call_cfg["max_tokens_override"]
        config = PairwiseConfig(**config_kwargs)

        candidates = [(cid, doc_texts.get(cid, "")) for cid in candidate_ids]

        t0 = time.time()
        retry_count = 0
        stats = LLMCallStats()
        detail_sink: list[dict] = []
        try:
            pairs, metadata = collect_all_pairs(
                query_id=query_id,
                query_text=query_text,
                candidates=candidates,
                config=config,
                stats=stats,
                detail_sink=detail_sink,
            )
            latency = time.time() - t0
            self._budget.record()
        except Exception as exc:
            self._append_prompt_details(provider=provider, model=model, detail_sink=detail_sink)
            error_category = classify_llm_error(exc)
            http_status = getattr(exc, "status_code", None)
            self.last_error = {
                "category": error_category,
                "message": str(exc)[:2000],
                "model": model,
                "http_status": http_status,
            }
            record = {
                "provider": provider,
                "provider_mode": call_cfg.get("mode"),
                "model": model,
                "api_provider_family": pw_provider,
                "prompt_template_version": PROMPT_VERSION,
                "query_id": query_id,
                "candidate_ids": candidate_ids,
                "error": str(exc),
                "error_category": error_category,
                "http_status": http_status,
                "retry_count": retry_count,
                "latency_s": time.time() - t0,
                "from_cache": False,
            }
            self._append_record(record)
            return None

        self._append_prompt_details(provider=provider, model=model, detail_sink=detail_sink)

        wins: dict[str, int] = defaultdict(int)
        losses: dict[str, int] = defaultdict(int)
        for winner, loser, _weight in pairs:
            wins[winner] += 1
            losses[loser] += 1
        all_ids = [cid for cid, _ in candidates]
        copeland_scores = {d: wins.get(d, 0) - losses.get(d, 0) for d in all_ids}
        ranked = sorted(copeland_scores, key=lambda d: (-copeland_scores[d], d))
        result = RerankerResult(
            query_id=query_id,
            ranked_doc_ids=ranked,
            scores={d: float(copeland_scores[d]) for d in all_ids},
            metadata=metadata,
        )
        total_pairs = len(pairs)
        cached = total_pairs > 0 and stats.cache_hits == total_pairs

        record = {
            "provider": provider,
            "provider_mode": call_cfg.get("mode"),
            "model": model,
            "api_provider_family": pw_provider,
            "prompt_template_version": PROMPT_VERSION,
            "query_id": query_id,
            "candidate_ids": candidate_ids,
            "raw_response_summary": result.metadata if hasattr(result, "metadata") else {},
            "parsed_ranking": result.ranked_doc_ids,
            "parsed_scores": result.scores,
            "llm_stats": stats.summary(),
            "temperature": config.temperature,
            "latency_s": latency,
            "retry_count": retry_count,
            "from_cache": cached,
            "budget_summary": self._budget.summary(),
        }
        self._append_record(record)
        return {
            "ranking": result.ranked_doc_ids,
            "scores": result.scores,
            "llm_record": record,
        }
