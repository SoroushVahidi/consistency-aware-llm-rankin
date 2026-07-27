"""Load the frozen micro-pilot config and verify it against live frozen artifacts.

Verification here answers "has anything the freeze depends on drifted since
it was committed?" -- it is intentionally strict and offers no override flag.
A genuinely changed experiment must get a new versioned config, not a bypass.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from consistency_ranker.counterfactual_benchmark import pool_builder
from consistency_ranker.counterfactual_pilot.panel import (
    PANEL_VERSION,
    panel_model_ids,
    panel_providers,
    require_panel_version,
)
from consistency_ranker.counterfactual_pilot.prompt import prompt_sha256
from consistency_ranker.counterfactual_pilot.query_selection import (
    select_lexicographic_queries,
)


class FreezeMismatchError(RuntimeError):
    """Raised when the on-disk config disagrees with the frozen contracts."""


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _schema_sha256(repo_root: Path, schema_path: str) -> str:
    return hashlib.sha256((repo_root / schema_path).read_bytes()).hexdigest()


def verify_frozen_contract(config: dict[str, Any], *, repo_root: Path) -> None:
    """Refuse to proceed when any frozen artifact differs from the config.

    Checks: prompt hash, schema hash, panel version, exact model ids,
    temperature, per-request output-token cap, and (when a live dataset is
    declared) that recomputing query selection from the same qrels/queries
    files reproduces the frozen query id list exactly.
    """
    problems: list[str] = []

    expected_prompt_hash = str(config["prompt_sha256"])
    actual_prompt_hash = prompt_sha256(repo_root)
    if actual_prompt_hash != expected_prompt_hash:
        problems.append(
            f"prompt_sha256 mismatch: config={expected_prompt_hash!r} "
            f"actual={actual_prompt_hash!r}"
        )

    expected_schema_hash = str(config["judgment_schema_sha256"])
    actual_schema_hash = _schema_sha256(repo_root, config["judgment_schema_path"])
    if actual_schema_hash != expected_schema_hash:
        problems.append(
            f"judgment_schema_sha256 mismatch: config={expected_schema_hash!r} "
            f"actual={actual_schema_hash!r}"
        )

    panel_version = str(config["panel_version"])
    try:
        require_panel_version(panel_version)
    except ValueError as exc:
        problems.append(str(exc))

    if panel_version == PANEL_VERSION:
        expected_providers = sorted(panel_providers())
        expected_models = sorted(panel_model_ids())
        config_providers = sorted(str(m["provider"]) for m in config["provider_panel"])
        config_models = sorted(str(m["model_or_deployment"]) for m in config["provider_panel"])
        if config_providers != expected_providers:
            problems.append(
                f"provider list mismatch: config={config_providers} "
                f"frozen={expected_providers}"
            )
        if config_models != expected_models:
            problems.append(
                f"model id mismatch: config={config_models} frozen={expected_models}"
            )

    gen = config["generation_defaults"]
    if float(gen["temperature"]) != 0.0:
        problems.append(f"temperature mismatch: config={gen['temperature']!r} frozen=0.0")
    cb = config["call_budget"]
    per_req_out = cb.get("max_output_tokens_per_request")
    if per_req_out is not None and int(per_req_out) != int(gen["max_output_tokens"]):
        problems.append(
            "max_output_tokens_per_request disagrees with generation_defaults."
            f"max_output_tokens: {per_req_out!r} vs {gen['max_output_tokens']!r}"
        )

    pool_cfg = config["candidate_pool"]
    if int(pool_cfg["pool_size"]) <= int(pool_cfg["eval_k"]):
        problems.append(
            f"candidate_pool.pool_size ({pool_cfg['pool_size']}) must exceed "
            f"eval_k ({pool_cfg['eval_k']})"
        )
    if pool_cfg.get("pool_protocol_version") != pool_builder.POOL_PROTOCOL_VERSION:
        problems.append(
            "candidate_pool.pool_protocol_version mismatch: "
            f"config={pool_cfg.get('pool_protocol_version')!r} "
            f"implemented={pool_builder.POOL_PROTOCOL_VERSION!r}"
        )
    if pool_cfg.get("rendering_policy_version") != pool_builder.RENDERING_POLICY_VERSION:
        problems.append(
            "candidate_pool.rendering_policy_version mismatch: "
            f"config={pool_cfg.get('rendering_policy_version')!r} "
            f"implemented={pool_builder.RENDERING_POLICY_VERSION!r}"
        )

    for dataset, meta in (config.get("datasets") or {}).items():
        qrels_path = repo_root / meta["qrels_path"]
        queries_path = repo_root / meta["queries_path"]
        if not qrels_path.exists() or not queries_path.exists():
            problems.append(f"{dataset}: qrels_path or queries_path missing on disk")
            continue
        recomputed = select_lexicographic_queries(
            qrels_path=qrels_path, queries_path=queries_path, n=len(meta["query_ids"])
        )
        if recomputed != list(meta["query_ids"]):
            problems.append(
                f"{dataset}: query selection drift: config={meta['query_ids']} "
                f"recomputed={recomputed}"
            )

    if problems:
        raise FreezeMismatchError(
            "Refusing to run: frozen artifact(s) differ from configs/"
            + config.get("benchmark_version", "<unknown>")
            + ".json:\n  - "
            + "\n  - ".join(problems)
        )


def validate_against_previous_plan(
    new_plan_summary: dict[str, Any], previous_plan_summary: dict[str, Any]
) -> None:
    """Refuse to resume into an output directory whose frozen plan changed."""
    frozen_keys = (
        "prompt_sha256",
        "judgment_schema_sha256",
        "panel_version",
        "model_ids",
        "temperature",
        "max_output_tokens",
        "pool_hashes",
        "query_ids",
        "policies",
        "eval_k",
        "hard_max_live_calls",
    )
    problems = []
    for key in frozen_keys:
        old = previous_plan_summary.get(key)
        new = new_plan_summary.get(key)
        if old != new:
            problems.append(f"{key}: previous={old!r} new={new!r}")
    if problems:
        raise FreezeMismatchError(
            "Refusing to resume: this output directory's recorded plan differs "
            "from the freshly computed plan:\n  - " + "\n  - ".join(problems)
        )
