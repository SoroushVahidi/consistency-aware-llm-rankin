"""
Multi-provider LLM pairwise robustness evaluation.

Separates provenance-rich judgment records from the legacy JudgmentCache,
which omits model/prompt/decoding from its keys.  New experiments must write
under a versioned report namespace and must never overwrite existing caches.
"""

from consistency_ranker.multi_provider_eval.prompts import PROMPT_FAMILY, get_prompt
from consistency_ranker.multi_provider_eval.schema import (
    CHOICE_VALUES,
    JudgmentRecord,
    PromptSpec,
)

__all__ = [
    "CHOICE_VALUES",
    "JudgmentRecord",
    "PromptSpec",
    "PROMPT_FAMILY",
    "get_prompt",
]
