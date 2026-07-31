"""Render the frozen pairwise prompt with truncated candidate text."""

from __future__ import annotations

from pathlib import Path

from consistency_ranker.counterfactual_benchmark.pool_builder import truncate_text
from consistency_ranker.counterfactual_pilot.prompt import load_prompt, render_prompt


def render_request_prompt(
    *,
    repo_root: Path,
    query_text: str,
    candidate_a_text: str,
    candidate_b_text: str,
    max_candidate_chars: int,
) -> str:
    template = load_prompt(repo_root)
    return render_prompt(
        template,
        query=query_text,
        candidate_a=truncate_text(candidate_a_text, max_candidate_chars),
        candidate_b=truncate_text(candidate_b_text, max_candidate_chars),
    )


def estimate_tokens_conservative(text: str, *, chars_per_token: float = 3.0) -> int:
    """Conservative (over-, not under-, estimating) token count from text length."""
    return int(len(text) / chars_per_token) + 1
