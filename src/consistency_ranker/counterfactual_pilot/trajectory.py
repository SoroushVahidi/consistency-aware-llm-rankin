"""Trajectory schema and qrels-isolation helpers for the micro-pilot."""

from __future__ import annotations

from typing import Any, Mapping

STEP_REQUIRED_FIELDS = (
    "benchmark_version",
    "dataset",
    "query_id",
    "candidate_pool_id",
    "candidate_ids",
    "policy",
    "budget",
    "provider",
    "model_id",
    "step",
    "available_action_count",
    "selected_pair",
    "presentation_order",
    "request_hash",
    "judgment",
    "normalized_document_preference",
    "confidence",
    "remaining_budget",
    "graph_state_summary",
    "ranking_after_step",
    "stop_reason",
    "calls_used",
    "tokens_used",
    "latency",
)

TERMINAL_REQUIRED_FIELDS = (
    "final_ranking",
    "ndcg_at_5",
    "mrr",
    "recall_at_5",
    "modeled_cost",
    "catastrophic_indicator",
    "prior_agreement_diagnostic",
)

# Runtime policy execution must never receive qrels under these keys.
FORBIDDEN_QRELS_KEYS = frozenset(
    {
        "qrels",
        "relevance_map",
        "relevance_labels",
        "true_relevance",
        "gold_labels",
    }
)


def validate_step_record(record: Mapping[str, Any]) -> None:
    missing = [k for k in STEP_REQUIRED_FIELDS if k not in record]
    if missing:
        raise ValueError(f"trajectory step missing fields: {missing}")
    cands = record["candidate_ids"]
    if not isinstance(cands, list) or len(cands) < 2:
        raise ValueError("candidate_ids must be a list with >= 2 ids")
    if record.get("presentation_order") not in {"ab", "ba"}:
        raise ValueError("presentation_order must be 'ab' or 'ba'")


def validate_terminal_record(record: Mapping[str, Any]) -> None:
    missing = [k for k in TERMINAL_REQUIRED_FIELDS if k not in record]
    if missing:
        raise ValueError(f"terminal record missing fields: {missing}")


def assert_no_qrels_in_policy_inputs(payload: Mapping[str, Any]) -> None:
    """Fail closed if qrels-like keys appear in runtime policy inputs."""
    bad = sorted(k for k in payload if k in FORBIDDEN_QRELS_KEYS)
    if bad:
        raise ValueError(
            f"qrels leakage into policy execution inputs: {bad}. "
            "Qrels may be used only after trajectories finish."
        )


def assert_same_candidate_pool(
    pool_a: list[str],
    pool_b: list[str],
    *,
    context: str = "",
) -> None:
    if list(pool_a) != list(pool_b):
        raise ValueError(
            f"candidate-pool mismatch{(' in ' + context) if context else ''}: "
            f"{pool_a!r} vs {pool_b!r}"
        )
