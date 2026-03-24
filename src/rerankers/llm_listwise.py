"""
llm_listwise.py
===============
LLM listwise (RankGPT-style) reranking baseline.

Uses a sliding-window approach: present the LLM with a window of documents
and ask it to rank them. Slide the window to progressively promote the best
documents to the top of the list.

Provenance
----------
- Approach: Sliding-window listwise prompting
- Reference: Sun et al. (2023), "Is ChatGPT Good at Search? Investigating Large
  Language Models as Re-Ranking Agent" (EMNLP 2023 Outstanding Paper)
- Prompt template: prompts/listwise_ranking.txt
- Label: "practical proxy baseline — LLM listwise reranking (RankGPT-style)"

Supports:
- Configurable window size and step size
- Multiple passes for refinement
- Judgment caching
- Budget controls
- Dry-run / mock mode
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from rerankers.common import BudgetTracker, JudgmentCache, RerankerResult

log = logging.getLogger(__name__)

_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent.parent / "prompts" / "listwise_ranking.txt"
)


@dataclass
class ListwiseConfig:
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int = 512
    window_size: int = 10
    step_size: int = 5
    num_passes: int = 1
    prompt_template_path: Path = _PROMPT_PATH
    cache_dir: Path | None = None
    max_calls: int | None = None
    dry_run: bool = False
    seed: int = 42
    strict_parsing: bool = False


@dataclass
class ListwiseCallStats:
    """Accumulated API/cache statistics for listwise runs."""

    api_calls: int = 0
    cache_hits: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    parse_failures: int = 0
    parse_error_details: list[str] = field(default_factory=list)

    def record_call(self, usage) -> None:
        self.api_calls += 1
        if usage is not None:
            self.prompt_tokens += getattr(usage, "prompt_tokens", 0)
            self.completion_tokens += getattr(usage, "completion_tokens", 0)
            self.total_tokens += getattr(usage, "total_tokens", 0)

    def record_cache_hit(self) -> None:
        self.cache_hits += 1

    def record_parse_failure(self, response_text: str) -> None:
        self.parse_failures += 1
        self.parse_error_details.append(response_text)

    def summary(self) -> dict:
        return {
            "api_calls": self.api_calls,
            "cache_hits": self.cache_hits,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "parse_failures": self.parse_failures,
        }


def _load_prompt_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _format_documents(candidates: list[tuple[str, str]], indices: list[int]) -> str:
    """Format a subset of candidates for the prompt."""
    lines = []
    for idx in indices:
        doc_id, doc_text = candidates[idx]
        display_text = doc_text[:500] if len(doc_text) > 500 else doc_text
        lines.append(f"[{idx + 1}] {display_text}")
    return "\n\n".join(lines)


def _parse_ranking(
    response_text: str,
    valid_indices: list[int],
    *,
    strict: bool = False,
) -> list[int]:
    """Parse a ranking from LLM response.

    Looks for patterns like "[3] > [1] > [5]" or "3, 1, 5" or "3 > 1 > 5".
    Returns 0-indexed positions.
    """
    numbers = [int(x) for x in re.findall(r"\d+", response_text)]
    if strict and not numbers:
        raise ValueError(f"Could not parse listwise ranking from response: {response_text!r}")

    valid_set = set(valid_indices)
    parsed = []
    seen = set()
    for n in numbers:
        idx = n - 1
        if idx in valid_set and idx not in seen:
            parsed.append(idx)
            seen.add(idx)

    for idx in valid_indices:
        if idx not in seen:
            parsed.append(idx)
            seen.add(idx)

    return parsed


def _mock_ranking(
    query: str, candidates: list[tuple[str, str]], indices: list[int], seed: int
) -> list[int]:
    """Deterministic mock ranking based on hashing."""
    scored = []
    for idx in indices:
        doc_id, doc_text = candidates[idx]
        h = hashlib.md5(f"{query}:{doc_id}:{seed}".encode()).hexdigest()
        scored.append((idx, int(h[:8], 16)))
    scored.sort(key=lambda x: -x[1])
    return [idx for idx, _ in scored]


def _call_llm(prompt: str, config: ListwiseConfig) -> tuple[str, object]:
    """Call the LLM API."""
    import openai

    client = openai.OpenAI()
    response = client.chat.completions.create(
        model=config.model,
        messages=[{"role": "user", "content": prompt}],
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    return response.choices[0].message.content.strip(), response.usage


def _sliding_window_pass(
    query_text: str,
    query_id: str,
    candidates: list[tuple[str, str]],
    current_order: list[int],
    config: ListwiseConfig,
    prompt_template: str,
    cache: JudgmentCache | None,
    budget: BudgetTracker | None,
    stats: ListwiseCallStats | None,
) -> list[int]:
    """One pass of the sliding window through the candidate list."""
    n = len(current_order)
    if n <= config.window_size:
        window_indices = list(current_order)
        if config.dry_run:
            ranked = _mock_ranking(query_text, candidates, window_indices, config.seed)
        else:
            if budget is not None and budget.budget_exhausted:
                return current_order

            cache_doc_ids = [candidates[idx][0] for idx in window_indices]
            if cache is not None:
                cached = cache.get(query_id=query_id, doc_ids=cache_doc_ids)
                if cached is not None:
                    if stats is not None:
                        stats.record_cache_hit()
                    return list(cached.get("ranked_indices", window_indices))
            docs_str = _format_documents(candidates, window_indices)
            prompt = prompt_template.format(query=query_text, documents=docs_str)
            response, usage = _call_llm(prompt, config)
            try:
                ranked = _parse_ranking(response, window_indices, strict=config.strict_parsing)
            except ValueError:
                if stats is not None:
                    stats.record_parse_failure(response)
                raise
            if cache is not None:
                cache.put(
                    query_id=query_id,
                    doc_ids=cache_doc_ids,
                    result={"ranked_indices": ranked, "response_text": response},
                )
            if stats is not None:
                stats.record_call(usage)
            if budget is not None:
                budget.record(
                    tokens_in=getattr(usage, "prompt_tokens", 0) if usage else 0,
                    tokens_out=getattr(usage, "completion_tokens", 0) if usage else 0,
                )
        return ranked

    result = list(current_order)

    end = n
    while end > 0:
        start = max(0, end - config.window_size)
        window_indices = result[start:end]

        if len(window_indices) < 2:
            break

        if config.dry_run:
            ranked_window = _mock_ranking(
                query_text, candidates, window_indices, config.seed
            )
        else:
            if budget is not None and budget.budget_exhausted:
                break
            cache_doc_ids = [candidates[idx][0] for idx in window_indices]
            if cache is not None:
                cached = cache.get(query_id=query_id, doc_ids=cache_doc_ids)
                if cached is not None:
                    if stats is not None:
                        stats.record_cache_hit()
                    result[start:end] = list(cached.get("ranked_indices", window_indices))
                    end -= config.step_size
                    continue
            docs_str = _format_documents(candidates, window_indices)
            prompt = prompt_template.format(query=query_text, documents=docs_str)
            response, usage = _call_llm(prompt, config)
            try:
                ranked_window = _parse_ranking(
                    response,
                    window_indices,
                    strict=config.strict_parsing,
                )
            except ValueError:
                if stats is not None:
                    stats.record_parse_failure(response)
                raise
            if cache is not None:
                cache.put(
                    query_id=query_id,
                    doc_ids=cache_doc_ids,
                    result={"ranked_indices": ranked_window, "response_text": response},
                )
            if stats is not None:
                stats.record_call(usage)
            if budget is not None:
                budget.record(
                    tokens_in=getattr(usage, "prompt_tokens", 0) if usage else 0,
                    tokens_out=getattr(usage, "completion_tokens", 0) if usage else 0,
                )

        result[start:end] = ranked_window
        end -= config.step_size

    return result


def rerank_query(
    query_id: str,
    query_text: str,
    candidates: list[tuple[str, str]],
    config: ListwiseConfig | None = None,
) -> RerankerResult:
    """Rerank candidates using sliding-window listwise LLM prompting."""
    if config is None:
        config = ListwiseConfig(dry_run=True)

    stats = ListwiseCallStats()
    cache = None
    if config.cache_dir is not None:
        cache = JudgmentCache(config.cache_dir, "llm_listwise", preserve_doc_order=True)

    budget = BudgetTracker(max_calls=config.max_calls)
    prompt_template = _load_prompt_template(config.prompt_template_path)

    current_order = list(range(len(candidates)))

    for pass_num in range(config.num_passes):
        current_order = _sliding_window_pass(
            query_text,
            query_id,
            candidates,
            current_order,
            config,
            prompt_template,
            cache,
            budget,
            stats,
        )

    ranked_ids = [candidates[idx][0] for idx in current_order]
    n = len(ranked_ids)
    scores = {doc_id: float(n - rank) for rank, doc_id in enumerate(ranked_ids)}

    return RerankerResult(
        query_id=query_id,
        ranked_doc_ids=ranked_ids,
        scores=scores,
        metadata={
            "method": "llm_listwise",
            "model": config.model,
            "dry_run": config.dry_run,
            "window_size": config.window_size,
            "step_size": config.step_size,
            "num_passes": config.num_passes,
            "budget": budget.summary(),
            "api_stats": stats.summary(),
        },
    )
