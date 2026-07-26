"""Predeclared prompt family for multi-provider pairwise robustness.

Variants are fixed before seeing test relevance outcomes.  Do not add or
retune prompts based on qrels.
"""

from __future__ import annotations

from pathlib import Path

from consistency_ranker.multi_provider_eval.schema import PromptSpec

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LEGACY = (_REPO_ROOT / "prompts" / "pairwise_comparison.txt").read_text(encoding="utf-8")

_CONCISE = """Compare relevance of two passages to the query.\nReply with only A or B.

Query: {query}
A: {document_a}
B: {document_b}
Answer:"""

_JSON = """You are a search relevance judge. Choose which document is more relevant.

Query: {query}
Document A: {document_a}
Document B: {document_b}

Respond with ONLY a single JSON object and no other text:
{{"choice":"A"}}
or
{{"choice":"B"}}
Valid values for choice are exactly: "A" or "B".
"""

_TIE_ALLOWED = """You are a search relevance judge. Given a query and two passages,
decide relevance, or answer TIE / INSUFFICIENT_INFORMATION.

Query: {query}
Document A: {document_a}
Document B: {document_b}

Respond with ONLY a single JSON object:
{{"choice":"A","confidence":"high"}}
choice must be one of: "A", "B", "TIE", "INSUFFICIENT_INFORMATION".
confidence must be one of: "high", "medium", "low".
No other text.
"""

PROMPT_FAMILY: dict[str, PromptSpec] = {
    "legacy_v1": PromptSpec(
        version="legacy_v1",
        template=_LEGACY,
        allows_tie=False,
        structured_json=False,
        notes="Current repository prompts/pairwise_comparison.txt",
    ),
    "concise_v1": PromptSpec(
        version="concise_v1",
        template=_CONCISE,
        allows_tie=False,
        structured_json=False,
        notes="Short relevance comparison; A/B only",
    ),
    "json_ab_v1": PromptSpec(
        version="json_ab_v1",
        template=_JSON,
        allows_tie=False,
        structured_json=True,
        notes="Reasoning-free structured JSON; A/B only",
    ),
    "json_tie_v1": PromptSpec(
        version="json_tie_v1",
        template=_TIE_ALLOWED,
        allows_tie=True,
        structured_json=True,
        notes="Explicitly permits TIE / INSUFFICIENT_INFORMATION",
    ),
}


def get_prompt(version: str) -> PromptSpec:
    if version not in PROMPT_FAMILY:
        raise KeyError(f"Unknown prompt version {version!r}; known={sorted(PROMPT_FAMILY)}")
    return PROMPT_FAMILY[version]


def format_prompt(spec: PromptSpec, *, query: str, document_a: str, document_b: str) -> str:
    return spec.template.format(query=query, document_a=document_a, document_b=document_b)
