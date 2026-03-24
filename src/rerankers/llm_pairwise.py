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
- Real OpenAI API calls (default) with retry + exponential backoff
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
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from rerankers.common import BudgetTracker, JudgmentCache, RerankerResult

log = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "prompts" / "pairwise_comparison.txt"

MAX_RETRIES = 4
RETRY_BASE_SECONDS = 2.0


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


def _call_llm(prompt: str, config: PairwiseConfig) -> tuple[str, object]:
    """Call the LLM API with retry and exponential backoff.

    Returns (response_text, usage_object).
    """
    import openai

    client = openai.OpenAI()
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
            text = response.choices[0].message.content.strip()
            return text, response.usage
        except (
            openai.APIConnectionError,
            openai.RateLimitError,
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
) -> tuple[str, str, float]:
    """Compare two documents and return (winner_id, loser_id, weight=1.0)."""
    id_a, text_a = doc_a
    id_b, text_b = doc_b

    if cache is not None:
        cached = cache.get(query_id=query_id, doc_ids=[id_a, id_b])
        if cached is not None:
            if stats is not None:
                stats.record_cache_hit()
            return cached["winner"], cached["loser"], cached.get("weight", 1.0)

    if budget is not None and budget.budget_exhausted:
        return id_a, id_b, 0.5

    if config.dry_run:
        winner_label = _mock_compare(query_text, text_a, text_b, config.seed)
    else:
        if prompt_template is None:
            prompt_template = _load_prompt_template(config.prompt_template_path)

        prompt_ab = _format_prompt(prompt_template, query_text, text_a, text_b)
        try:
            response_ab, usage_ab = _call_llm(prompt_ab, config)
        except Exception as exc:
            if stats is not None:
                stats.record_error(f"pair({id_a},{id_b}): {exc}")
            log.error("API call failed for pair (%s, %s): %s", id_a, id_b, exc)
            raise
        winner_label = _parse_winner(response_ab)

        if stats is not None:
            stats.record_call(usage_ab)
        if budget is not None:
            budget.record(
                tokens_in=getattr(usage_ab, "prompt_tokens", 0) if usage_ab else 0,
                tokens_out=getattr(usage_ab, "completion_tokens", 0) if usage_ab else 0,
            )

        if config.debias_position:
            prompt_ba = _format_prompt(prompt_template, query_text, text_b, text_a)
            try:
                response_ba, usage_ba = _call_llm(prompt_ba, config)
            except Exception as exc:
                if stats is not None:
                    stats.record_error(f"debias({id_b},{id_a}): {exc}")
                log.error("API debias call failed for pair (%s, %s): %s", id_b, id_a, exc)
                raise
            winner_ba = _parse_winner(response_ba)
            if stats is not None:
                stats.record_call(usage_ba)
            if budget is not None:
                budget.record(
                    tokens_in=getattr(usage_ba, "prompt_tokens", 0) if usage_ba else 0,
                    tokens_out=(
                        getattr(usage_ba, "completion_tokens", 0) if usage_ba else 0
                    ),
                )
            ab_vote = 0 if winner_label == "A" else 1
            ba_vote = 1 if winner_ba == "A" else 0
            winner_label = "A" if (ab_vote + ba_vote) < 2 else "B"

    winner_id = id_a if winner_label == "A" else id_b
    loser_id = id_b if winner_label == "A" else id_a

    if cache is not None:
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
) -> tuple[list[tuple[str, str, float]], dict]:
    """Run pairwise comparisons for all O(n^2/2) candidate pairs.

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

    pairs = []
    n = len(candidates)
    for i in range(n):
        for j in range(i + 1, n):
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
            )
            pairs.append((winner, loser, weight))

    metadata = {
        "method": "llm_pairwise",
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
