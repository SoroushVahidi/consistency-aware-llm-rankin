"""
llm_pairwise.py
===============
LLM pairwise document comparison baseline.

For each pair of candidate documents, the LLM decides which is more relevant.
Pairwise outcomes are collected and can be fed into aggregation methods
(Copeland, Bradley-Terry, or the existing pipeline's graph-repair approach).

Provenance
----------
- Approach: Pairwise Ranking Prompting (PRP)
- Reference: Qin et al. (2023), "Large Language Models are Effective Text Rankers
  with Pairwise Ranking Prompting"
- Prompt template: prompts/pairwise_comparison.txt
- Label: "practical proxy baseline — LLM pairwise comparison reranking"

Supports:
- Real OpenAI API calls (provider="openai") with retry + exponential backoff
- Real Google Gemini API calls (provider="gemini") with retry + exponential backoff
- Deterministic decoding (temperature=0)
- Disk-backed judgment caching (query-aware keys)
- Budget controls (max API calls)
- Position de-biasing (compare A-B and B-A, majority wins)
- Resumable runs via cache
- Dry-run / mock mode (only when explicitly requested)
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from rerankers.common import BudgetTracker, JudgmentCache, RerankerResult

log = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "prompts" / "pairwise_comparison.txt"

MAX_RETRIES = 4
RETRY_BASE_SECONDS = 2.0


SUPPORTED_PROVIDERS = ("openai", "gemini")

# Process-wide OpenAI-compatible client cache, keyed by (api_key, base_url).
# The Azure OpenAI latency diagnostic found _call_openai() was constructing a
# brand-new openai.OpenAI() client (and therefore a fresh TCP+TLS connection,
# no keep-alive reuse) on *every single pairwise comparison call* -- up to 210
# times per query. Reusing one client per (api_key, base_url) measured ~30%
# lower per-call latency in that diagnostic and is safe: openai.OpenAI()
# instances are stateless besides their HTTP connection pool.
_openai_client_cache: dict[tuple[str | None, str | None], object] = {}
_openai_client_cache_lock = threading.Lock()

# Guards mutations shared across concurrent compare_pair() calls (stats,
# budget, judgment cache, prompt detail sink) when PairwiseConfig.concurrency
# > 1. Cheap/uncontended when concurrency == 1 (the default, unchanged
# behavior for every provider that doesn't opt in).
_mutation_lock = threading.Lock()


def _get_openai_client(config: "PairwiseConfig"):
    import openai

    key = (config.api_key, config.base_url)
    with _openai_client_cache_lock:
        client = _openai_client_cache.get(key)
        if client is None:
            client_kwargs: dict = {}
            if config.api_key:
                client_kwargs["api_key"] = config.api_key
            if config.base_url:
                client_kwargs["base_url"] = config.base_url
            client = openai.OpenAI(**client_kwargs)
            _openai_client_cache[key] = client
        return client


@dataclass
class PairwiseConfig:
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int = 4
    prompt_template_path: Path = _PROMPT_PATH
    cache_dir: Path | None = None
    max_calls: int | None = None
    dry_run: bool = False
    debias_position: bool = False
    seed: int = 42
    provider: str = "openai"
    call_delay: float = 0.0
    api_key: str | None = None
    base_url: str | None = None
    # Gemini-only: when set, use Vertex AI (ADC-based) instead of a direct
    # Gemini API key. See detect_llm_providers()/_provider_call_config() in
    # failure_mining/llm_runner.py for how this is resolved from env vars.
    gemini_use_vertex: bool = False
    vertex_project: str | None = None
    vertex_location: str | None = None
    # Extra provider-specific chat-completions kwargs passed through as-is
    # (openai SDK's extra_body). Used for e.g. Fireworks reasoning models
    # (gpt-oss-*) that need {"reasoning_effort": "low"} to keep hidden
    # chain-of-thought tokens bounded -- see _provider_call_config("fireworks")
    # in failure_mining/llm_runner.py.
    extra_body: dict | None = None
    # Number of pairwise comparisons to run concurrently in collect_all_pairs().
    # Default 1 preserves the original fully-serial behavior for every
    # provider that doesn't opt in. The Azure OpenAI latency diagnostic found
    # collect_all_pairs() runs up to 210 sequential HTTP round trips per
    # query (15 candidates -> C(15,2) pairs x 2 debias directions), which is
    # the actual cause of Azure's ~151s median per-query wall time -- not a
    # slow model (Azure's own usage.latency_checkpoint showed ~150-230ms
    # server-side inference). A live, full-scale (210-call) concurrency=8
    # test against the real endpoint completed in 22.4s with 0 errors, safely
    # under the account's 250-requests-per-60s rate limit for a single
    # query's burst. See failure_mining/llm_runner.py's
    # _provider_call_config("azure") for where this is set.
    concurrency: int = 1

    def __post_init__(self) -> None:
        if self.provider not in SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unknown provider {self.provider!r}. "
                f"Supported: {SUPPORTED_PROVIDERS}"
            )


@dataclass
class LLMCallStats:
    """Accumulated real token / call statistics from API responses."""

    api_calls: int = 0
    cache_hits: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    errors: int = 0
    error_details: list = field(default_factory=list)

    def record_call(self, usage) -> None:
        self.api_calls += 1
        if usage is not None:
            self.prompt_tokens += getattr(usage, "prompt_tokens", 0)
            self.completion_tokens += getattr(usage, "completion_tokens", 0)
            self.total_tokens += getattr(usage, "total_tokens", 0)

    def record_cache_hit(self) -> None:
        self.cache_hits += 1

    def record_error(self, err_msg: str) -> None:
        self.errors += 1
        self.error_details.append(err_msg)

    def summary(self) -> dict:
        return {
            "api_calls": self.api_calls,
            "cache_hits": self.cache_hits,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "errors": self.errors,
        }


def _load_prompt_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _format_prompt(template: str, query: str, doc_a: str, doc_b: str) -> str:
    return template.format(query=query, document_a=doc_a, document_b=doc_b)


def _parse_winner(response_text: str) -> str:
    """Parse 'A' or 'B' from LLM response."""
    text = response_text.strip().upper()
    if text.startswith("A"):
        return "A"
    if text.startswith("B"):
        return "B"
    if "A" in text and "B" not in text:
        return "A"
    if "B" in text and "A" not in text:
        return "B"
    return "A"


def _mock_compare(query: str, doc_a: str, doc_b: str, seed: int) -> str:
    """Deterministic mock comparison based on text hashing."""
    h = hashlib.md5(f"{query}:{doc_a}:{doc_b}:{seed}".encode()).hexdigest()
    return "A" if int(h[:4], 16) % 2 == 0 else "B"


def _is_quota_exhausted(exc) -> bool:
    """Return True if the error is a hard quota exhaustion (not a transient rate limit)."""
    msg = str(exc).lower()
    return "insufficient_quota" in msg or "exceeded your current quota" in msg


def _needs_responses_api_fallback(exc) -> bool:
    """Return True when the endpoint rejects chat-completions ``messages``."""
    msg = str(exc).lower()
    return (
        "unsupported parameter: 'messages'" in msg
        or "parameter has moved to 'input'" in msg
        or "responses api" in msg
    )


class _OpenAIResponsesUsage:
    """Normalize OpenAI Responses usage to the chat-completions token shape."""

    def __init__(self, usage) -> None:
        self.prompt_tokens = getattr(usage, "input_tokens", 0) if usage else 0
        self.completion_tokens = getattr(usage, "output_tokens", 0) if usage else 0
        self.total_tokens = getattr(usage, "total_tokens", 0) if usage else 0


def _extract_openai_responses_text(response) -> str:
    """Extract text robustly from a Responses API object."""
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)

    for item in getattr(response, "output", []) or []:
        for block in getattr(item, "content", []) or []:
            if getattr(block, "type", "") in {"output_text", "text"}:
                text = getattr(block, "text", "")
                if text:
                    return str(text)
    return ""


def _call_openai(prompt: str, config: PairwiseConfig) -> tuple[str, object]:
    """Call the OpenAI API with retry and exponential backoff.

    Returns (response_text, usage_object).
    Retries on transient errors but fails immediately on quota exhaustion.
    """
    import openai

    client = _get_openai_client(config)
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                extra_body=config.extra_body,
            )
            raw_text = response.choices[0].message.content
            if raw_text is None:
                # Reasoning models (e.g. Fireworks' gpt-oss-*) can return
                # content=None with finish_reason="length" when the whole
                # max_tokens budget was consumed by hidden reasoning_content
                # before any visible answer was emitted. Surface this as a
                # clear, classifiable error rather than crashing on
                # .strip() -- see classify_llm_error()'s "malformed_response".
                finish_reason = getattr(response.choices[0], "finish_reason", None)
                raise ValueError(
                    f"OpenAI-compatible response has empty content "
                    f"(finish_reason={finish_reason!r}, model={config.model!r}); "
                    "the model may need a larger max_tokens or reasoning_effort override"
                )
            text = raw_text.strip()
            return text, response.usage
        except openai.BadRequestError as exc:
            if not _needs_responses_api_fallback(exc):
                raise
            max_output_tokens = max(16, int(config.max_tokens))
            response = client.responses.create(
                model=config.model,
                input=prompt,
                temperature=config.temperature,
                max_output_tokens=max_output_tokens,
            )
            text = _extract_openai_responses_text(response).strip()
            return text, _OpenAIResponsesUsage(getattr(response, "usage", None))
        except openai.RateLimitError as exc:
            if _is_quota_exhausted(exc):
                raise
            last_error = exc
            if attempt < MAX_RETRIES:
                wait = RETRY_BASE_SECONDS * (2 ** attempt)
                log.warning(
                    "Rate limit (attempt %d/%d): %s — retrying in %.1fs",
                    attempt + 1, MAX_RETRIES + 1, exc, wait,
                )
                time.sleep(wait)
            else:
                raise
        except (
            openai.APIConnectionError,
            openai.APITimeoutError,
            openai.InternalServerError,
        ) as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                wait = RETRY_BASE_SECONDS * (2 ** attempt)
                log.warning(
                    "LLM API error (attempt %d/%d): %s — retrying in %.1fs",
                    attempt + 1, MAX_RETRIES + 1, exc, wait,
                )
                time.sleep(wait)
            else:
                raise
    raise last_error  # unreachable but satisfies type checker


class _GeminiUsage:
    """Lightweight usage object that mirrors the OpenAI usage interface."""

    def __init__(self, prompt_tokens: int = 0, completion_tokens: int = 0):
        self.prompt_tokens = prompt_tokens or 0
        self.completion_tokens = completion_tokens or 0
        self.total_tokens = self.prompt_tokens + self.completion_tokens


def _call_gemini(prompt: str, config: PairwiseConfig) -> tuple[str, object]:
    """Call the Google Gemini API with retry and exponential backoff.

    Uses the ``google-genai`` SDK (``google.genai``), in either of two modes:

    - Direct Gemini API key mode (``config.gemini_use_vertex=False``): reads
      ``GEMINI_API_KEY``/``GOOGLE_API_KEY`` directly, same as before.
    - Vertex AI mode (``config.gemini_use_vertex=True``): authenticates via
      Application Default Credentials (no API key), using
      ``config.vertex_project``/``config.vertex_location``. Selected when the
      environment is configured for Vertex (see
      ``failure_mining/llm_runner.py::_gemini_vertex_config``) and no direct
      API key is present.

    Returns (response_text, usage_object).
    """
    import os

    from google import genai
    from google.genai import types

    if config.gemini_use_vertex:
        if not config.vertex_project:
            raise RuntimeError("Vertex AI mode requires a resolvable GCP project")
        client = genai.Client(
            vertexai=True,
            project=config.vertex_project,
            location=config.vertex_location or "us-central1",
        )
    else:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set")
        client = genai.Client(api_key=api_key)

    gen_config_kwargs: dict = {
        "temperature": config.temperature,
        "max_output_tokens": config.max_tokens,
    }
    if config.gemini_use_vertex:
        # Vertex AI's 2.5-series models think by default and spend the
        # max_output_tokens budget on hidden reasoning tokens before ever
        # emitting visible text -- with the small max_tokens used for a
        # single-letter A/B judgment this silently returns an empty
        # response (finish_reason=MAX_TOKENS, .text=None) instead of an
        # error. Disabling thinking keeps behavior aligned with direct
        # API-key mode's non-thinking default models. Only applied in
        # Vertex mode: unverified whether direct API-key mode needs it too.
        gen_config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    gen_config = types.GenerateContentConfig(**gen_config_kwargs)

    gemini_max_retries = MAX_RETRIES + 4  # extra retries for transient rate limits
    last_error = None
    for attempt in range(gemini_max_retries + 1):
        try:
            response = client.models.generate_content(
                model=config.model,
                contents=prompt,
                config=gen_config,
            )
            raw_text = response.text
            if raw_text is None:
                raise ValueError("Gemini returned empty response (response.text is None)")
            text = raw_text.strip()
            um = response.usage_metadata
            usage = _GeminiUsage(
                prompt_tokens=getattr(um, "prompt_token_count", 0) if um else 0,
                completion_tokens=getattr(um, "candidates_token_count", 0) if um else 0,
            )
            return text, usage
        except Exception as exc:
            err_msg = str(exc).lower()
            is_rate_limit = "resource_exhausted" in err_msg or "429" in err_msg
            is_hard_quota = is_rate_limit and "per_day" in err_msg.replace(" ", "_").lower()
            if is_hard_quota:
                raise
            if is_rate_limit and attempt < gemini_max_retries:
                wait = min(RETRY_BASE_SECONDS * (2 ** attempt), 60.0)
                log.warning(
                    "Gemini rate limit (attempt %d/%d): retrying in %.1fs",
                    attempt + 1, gemini_max_retries + 1, wait,
                )
                time.sleep(wait)
                continue
            if not is_rate_limit and ("quota" in err_msg):
                raise
            last_error = exc
            if attempt < gemini_max_retries:
                wait = RETRY_BASE_SECONDS * (2 ** min(attempt, 4))
                log.warning(
                    "Gemini API error (attempt %d/%d): %s — retrying in %.1fs",
                    attempt + 1, gemini_max_retries + 1, exc, wait,
                )
                time.sleep(wait)
            else:
                raise
    raise last_error  # unreachable but satisfies type checker


def _call_llm(prompt: str, config: PairwiseConfig) -> tuple[str, object]:
    """Dispatch to the appropriate provider backend."""
    if config.call_delay > 0:
        time.sleep(config.call_delay)
    if config.provider == "gemini":
        return _call_gemini(prompt, config)
    return _call_openai(prompt, config)


def compare_pair(
    query_text: str,
    doc_a: tuple[str, str],
    doc_b: tuple[str, str],
    *,
    query_id: str = "",
    config: PairwiseConfig,
    cache: JudgmentCache | None = None,
    budget: BudgetTracker | None = None,
    prompt_template: str | None = None,
    stats: LLMCallStats | None = None,
    detail_sink: list[dict] | None = None,
) -> tuple[str, str, float]:
    """Compare two documents and return (winner_id, loser_id, weight=1.0).

    If ``detail_sink`` is given, one dict is appended per underlying LLM call
    (or one lightweight cache-hit record) with the exact prompt text, raw
    response text, and parsed winner — the full API record needed for
    reproducibility. Left ``None`` by default so existing callers that don't
    need this (and don't want the extra memory/IO) are unaffected.
    """
    id_a, text_a = doc_a
    id_b, text_b = doc_b

    if cache is not None:
        cached = cache.get(query_id=query_id, doc_ids=[id_a, id_b])
        if cached is not None:
            with _mutation_lock:
                if stats is not None:
                    stats.record_cache_hit()
                if detail_sink is not None:
                    detail_sink.append(
                        {
                            "query_id": query_id,
                            "doc_a_id": id_a,
                            "doc_b_id": id_b,
                            "direction": "cached",
                            "from_cache": True,
                            "winner_id": cached["winner"],
                            "loser_id": cached["loser"],
                        }
                    )
            return cached["winner"], cached["loser"], cached.get("weight", 1.0)

    if budget is not None and budget.budget_exhausted:
        return id_a, id_b, 0.5

    if config.dry_run:
        winner_label = _mock_compare(query_text, text_a, text_b, config.seed)
    else:
        if prompt_template is None:
            prompt_template = _load_prompt_template(config.prompt_template_path)

        prompt_ab = _format_prompt(prompt_template, query_text, text_a, text_b)
        parse_error_ab = None
        try:
            response_ab, usage_ab = _call_llm(prompt_ab, config)
        except Exception as exc:
            if stats is not None:
                stats.record_error(f"pair({id_a},{id_b}): {exc}")
            log.error("API call failed for pair (%s, %s): %s", id_a, id_b, exc)
            raise
        winner_label = _parse_winner(response_ab)
        if winner_label not in ("A", "B"):
            parse_error_ab = f"unparseable response: {response_ab!r}"

        with _mutation_lock:
            if stats is not None:
                stats.record_call(usage_ab)
            if budget is not None:
                budget.record(
                    tokens_in=getattr(usage_ab, "prompt_tokens", 0) if usage_ab else 0,
                    tokens_out=getattr(usage_ab, "completion_tokens", 0) if usage_ab else 0,
                )
            if detail_sink is not None:
                detail_sink.append(
                    {
                        "query_id": query_id,
                        "doc_a_id": id_a,
                        "doc_b_id": id_b,
                        "direction": "ab",
                        "from_cache": False,
                        "prompt": prompt_ab,
                        "raw_response": response_ab,
                        "parsed_winner_label": winner_label,
                        "parse_error": parse_error_ab,
                        "prompt_tokens": getattr(usage_ab, "prompt_tokens", None) if usage_ab else None,
                        "completion_tokens": (
                            getattr(usage_ab, "completion_tokens", None) if usage_ab else None
                        ),
                    }
                )

        if config.debias_position:
            prompt_ba = _format_prompt(prompt_template, query_text, text_b, text_a)
            parse_error_ba = None
            try:
                response_ba, usage_ba = _call_llm(prompt_ba, config)
            except Exception as exc:
                if stats is not None:
                    stats.record_error(f"debias({id_b},{id_a}): {exc}")
                log.error("API debias call failed for pair (%s, %s): %s", id_b, id_a, exc)
                raise
            winner_ba = _parse_winner(response_ba)
            if winner_ba not in ("A", "B"):
                parse_error_ba = f"unparseable response: {response_ba!r}"
            with _mutation_lock:
                if stats is not None:
                    stats.record_call(usage_ba)
                if budget is not None:
                    budget.record(
                        tokens_in=getattr(usage_ba, "prompt_tokens", 0) if usage_ba else 0,
                        tokens_out=(
                            getattr(usage_ba, "completion_tokens", 0) if usage_ba else 0
                        ),
                    )
                if detail_sink is not None:
                    detail_sink.append(
                        {
                            "query_id": query_id,
                            "doc_a_id": id_a,
                            "doc_b_id": id_b,
                            "direction": "ba",
                            "from_cache": False,
                            "prompt": prompt_ba,
                            "raw_response": response_ba,
                            "parsed_winner_label": winner_ba,
                            "parse_error": parse_error_ba,
                            "prompt_tokens": (
                                getattr(usage_ba, "prompt_tokens", None) if usage_ba else None
                            ),
                            "completion_tokens": (
                                getattr(usage_ba, "completion_tokens", None) if usage_ba else None
                            ),
                        }
                    )
            ab_vote = 0 if winner_label == "A" else 1
            ba_vote = 1 if winner_ba == "A" else 0
            winner_label = "A" if (ab_vote + ba_vote) < 2 else "B"

    winner_id = id_a if winner_label == "A" else id_b
    loser_id = id_b if winner_label == "A" else id_a

    if cache is not None:
        with _mutation_lock:
            cache.put(
                query_id=query_id,
                doc_ids=[id_a, id_b],
                result={"winner": winner_id, "loser": loser_id, "weight": 1.0},
            )

    return winner_id, loser_id, 1.0


def collect_all_pairs(
    query_id: str,
    query_text: str,
    candidates: list[tuple[str, str]],
    config: PairwiseConfig | None = None,
    stats: LLMCallStats | None = None,
    detail_sink: list[dict] | None = None,
) -> tuple[list[tuple[str, str, float]], dict]:
    """Run pairwise comparisons for all O(n^2/2) candidate pairs.

    Parameters
    ----------
    detail_sink:
        If given, every underlying LLM call (exact prompt, raw response,
        parsed winner, parse error if any, token counts) and every cache hit
        is appended to this list — the full API record needed for
        reproducibility. ``None`` by default (no behavior change for
        existing callers).

    Returns
    -------
    pairs : list of (winner_id, loser_id, weight) tuples
    metadata : dict with comparison statistics
    """
    if config is None:
        config = PairwiseConfig(dry_run=True)

    cache = None
    if config.cache_dir is not None:
        cache = JudgmentCache(config.cache_dir, "llm_pairwise")

    budget = BudgetTracker(max_calls=config.max_calls)
    prompt_template = _load_prompt_template(config.prompt_template_path)

    n = len(candidates)
    pair_indices = [(i, j) for i in range(n) for j in range(i + 1, n)]

    if config.concurrency > 1 and len(pair_indices) > 1:
        # Bounded concurrency: see PairwiseConfig.concurrency docstring.
        # compare_pair()'s shared-state mutations (stats/budget/cache/
        # detail_sink) are guarded by _mutation_lock so this is safe.
        import concurrent.futures

        results: list[tuple[str, str, float] | None] = [None] * len(pair_indices)
        with concurrent.futures.ThreadPoolExecutor(max_workers=config.concurrency) as executor:
            future_to_idx = {
                executor.submit(
                    compare_pair,
                    query_text,
                    candidates[i],
                    candidates[j],
                    query_id=query_id,
                    config=config,
                    cache=cache,
                    budget=budget,
                    prompt_template=prompt_template,
                    stats=stats,
                    detail_sink=detail_sink,
                ): idx
                for idx, (i, j) in enumerate(pair_indices)
            }
            for future in concurrent.futures.as_completed(future_to_idx):
                results[future_to_idx[future]] = future.result()
        pairs = list(results)
    else:
        pairs = []
        for i, j in pair_indices:
            winner, loser, weight = compare_pair(
                query_text,
                candidates[i],
                candidates[j],
                query_id=query_id,
                config=config,
                cache=cache,
                budget=budget,
                prompt_template=prompt_template,
                stats=stats,
                detail_sink=detail_sink,
            )
            pairs.append((winner, loser, weight))

    metadata = {
        "method": "llm_pairwise",
        "provider": config.provider,
        "model": config.model,
        "dry_run": config.dry_run,
        "debias_position": config.debias_position,
        "n_pairs": len(pairs),
        "n_candidates": n,
        "budget": budget.summary(),
    }
    if stats is not None:
        metadata["llm_stats"] = stats.summary()
    return pairs, metadata


def rerank_query(
    query_id: str,
    query_text: str,
    candidates: list[tuple[str, str]],
    config: PairwiseConfig | None = None,
) -> RerankerResult:
    """Rerank candidates using pairwise comparisons with Copeland aggregation."""
    pairs, metadata = collect_all_pairs(query_id, query_text, candidates, config)

    wins: dict[str, int] = defaultdict(int)
    losses: dict[str, int] = defaultdict(int)
    for winner, loser, _ in pairs:
        wins[winner] += 1
        losses[loser] += 1

    all_ids = [doc_id for doc_id, _ in candidates]
    copeland_scores = {d: wins.get(d, 0) - losses.get(d, 0) for d in all_ids}
    ranked = sorted(copeland_scores, key=lambda d: (-copeland_scores[d], d))

    return RerankerResult(
        query_id=query_id,
        ranked_doc_ids=ranked,
        scores={d: float(copeland_scores[d]) for d in all_ids},
        metadata=metadata,
    )
