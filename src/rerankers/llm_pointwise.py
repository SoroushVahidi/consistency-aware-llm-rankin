"""
llm_pointwise.py
================
LLM pointwise relevance scoring baseline.

Each document is independently scored for relevance to the query using a single
LLM call. Documents are then ranked by descending score.

Provenance
----------
- Approach: Standard pointwise LLM relevance assessment
- References: Liang et al. (2022); Sun et al. (2023) — pointwise prompting variant
- Prompt template: prompts/pointwise_relevance.txt
- Label: "practical proxy baseline — LLM pointwise relevance scoring"

Supports:
- Deterministic decoding (temperature=0)
- Judgment caching to disk
- Budget controls (max calls)
- Dry-run / mock mode when no API key is available
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from rerankers.common import BudgetTracker, JudgmentCache, RerankerResult

log = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "prompts" / "pointwise_relevance.txt"


@dataclass
class PointwiseConfig:
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int = 8
    prompt_template_path: Path = _PROMPT_PATH
    cache_dir: Path | None = None
    max_calls: int | None = None
    dry_run: bool = False
    seed: int = 42


def _load_prompt_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _format_prompt(template: str, query: str, document: str) -> str:
    return template.format(query=query, document=document)


def _parse_score(response_text: str) -> float:
    """Extract integer score from LLM response."""
    match = re.search(r"\b(\d{1,2})\b", response_text.strip())
    if match:
        score = int(match.group(1))
        return float(min(score, 10))
    return 5.0


def _mock_score(query: str, document: str, seed: int) -> float:
    """Deterministic mock score based on text hashing (for dry-run mode)."""
    h = hashlib.md5(f"{query}:{document}:{seed}".encode()).hexdigest()
    return (int(h[:8], 16) % 110) / 10.0


def _call_llm(prompt: str, config: PointwiseConfig) -> str:
    """Call the LLM API. Requires openai package and API key."""
    import openai

    client = openai.OpenAI()
    response = client.chat.completions.create(
        model=config.model,
        messages=[{"role": "user", "content": prompt}],
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    return response.choices[0].message.content.strip()


def score_document(
    query_text: str,
    doc_id: str,
    doc_text: str,
    *,
    config: PointwiseConfig,
    cache: JudgmentCache | None = None,
    budget: BudgetTracker | None = None,
    prompt_template: str | None = None,
) -> float:
    """Score a single document for relevance to the query.

    Returns a float score in [0, 10].
    """
    if cache is not None:
        cached = cache.get(query_id="", doc_ids=[doc_id])
        if cached is not None:
            return cached.get("score", 5.0)

    if budget is not None and budget.budget_exhausted:
        return 5.0

    if config.dry_run:
        score = _mock_score(query_text, doc_text, config.seed)
    else:
        if prompt_template is None:
            prompt_template = _load_prompt_template(config.prompt_template_path)
        prompt = _format_prompt(prompt_template, query_text, doc_text)
        response = _call_llm(prompt, config)
        score = _parse_score(response)
        if budget is not None:
            budget.record(tokens_in=len(prompt.split()), tokens_out=len(response.split()))

    if cache is not None:
        cache.put(query_id="", doc_ids=[doc_id], result={"score": score})

    return score


def rerank_query(
    query_id: str,
    query_text: str,
    candidates: list[tuple[str, str]],
    config: PointwiseConfig | None = None,
) -> RerankerResult:
    """Rerank candidates using pointwise LLM scoring."""
    if config is None:
        config = PointwiseConfig(dry_run=True)

    cache = None
    if config.cache_dir is not None:
        cache = JudgmentCache(config.cache_dir, "llm_pointwise")

    budget = BudgetTracker(max_calls=config.max_calls)
    prompt_template = _load_prompt_template(config.prompt_template_path)

    scores: dict[str, float] = {}
    for doc_id, doc_text in candidates:
        scores[doc_id] = score_document(
            query_text,
            doc_id,
            doc_text,
            config=config,
            cache=cache,
            budget=budget,
            prompt_template=prompt_template,
        )

    ranked = sorted(scores, key=lambda d: (-scores[d], d))

    return RerankerResult(
        query_id=query_id,
        ranked_doc_ids=ranked,
        scores=scores,
        metadata={
            "method": "llm_pointwise",
            "model": config.model,
            "dry_run": config.dry_run,
            "budget": budget.summary(),
        },
    )
