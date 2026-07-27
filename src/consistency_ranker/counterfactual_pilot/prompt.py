"""Prompt hashing and loading for the frozen pairwise judge prompt."""

from __future__ import annotations

import hashlib
from pathlib import Path

PROMPT_VERSION = "counterfactual_pairwise_judge_v1"
PROMPT_REL_PATH = Path("prompts") / f"{PROMPT_VERSION}.txt"


def prompt_path(repo_root: Path) -> Path:
    return repo_root / PROMPT_REL_PATH


def load_prompt(repo_root: Path) -> str:
    return prompt_path(repo_root).read_text(encoding="utf-8")


def prompt_sha256(repo_root: Path) -> str:
    return hashlib.sha256(prompt_path(repo_root).read_bytes()).hexdigest()


def render_prompt(template: str, *, query: str, candidate_a: str, candidate_b: str) -> str:
    return template.format(
        query=query,
        candidate_a=candidate_a,
        candidate_b=candidate_b,
    )
