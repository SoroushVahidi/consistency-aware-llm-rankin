"""Offline arithmetic for real counterfactual benchmark call counts.

No provider requests. Prices are optional and never invented.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def unordered_pairs(pool_size: int) -> int:
    if pool_size < 2:
        return 0
    return pool_size * (pool_size - 1) // 2


def estimate_complete_matrix_requests(
    *,
    n_queries: int,
    pool_size: int,
    n_providers: int,
    presentation_orders: int = 2,
    repeats: int = 1,
) -> dict[str, Any]:
    pairs = unordered_pairs(pool_size)
    requests = (
        pairs * presentation_orders * repeats * n_providers * n_queries
    )
    return {
        "n_queries": n_queries,
        "pool_size": pool_size,
        "unordered_pairs_per_query": pairs,
        "n_providers": n_providers,
        "presentation_orders": presentation_orders,
        "repeats": repeats,
        "total_requests": requests,
        "formula": (
            "unordered_pairs = P*(P-1)/2; "
            "requests = unordered_pairs * presentation_orders * repeats "
            "* providers * queries"
        ),
    }


def estimate_logged_policy_requests(
    *,
    n_queries: int,
    n_providers: int,
    budgets: list[int],
    presentation_orders: int = 2,
    instability_repeat_fraction: float = 0.0,
    instability_repeats: int = 2,
) -> dict[str, Any]:
    """Sparse logged shell: one selected pair per budget step (not full matrix)."""
    # Pilot design: each query evaluated at each budget as a separate cell,
    # selecting `budget` pairs (with optional dual orientation).
    per_query = 0
    detail = []
    for b in budgets:
        base = b * presentation_orders
        # Small instability subset may add extra repeats on a fraction of steps.
        extra = int(round(b * instability_repeat_fraction)) * max(0, instability_repeats - 1)
        cell = base + extra
        detail.append({"budget": b, "requests_per_query_per_provider": cell})
        per_query += cell
    total = per_query * n_providers * n_queries
    return {
        "n_queries": n_queries,
        "n_providers": n_providers,
        "budgets": list(budgets),
        "presentation_orders": presentation_orders,
        "requests_per_query_all_budgets_per_provider": per_query,
        "budget_detail": detail,
        "total_requests": total,
        "note": (
            "Counts acquisition judgments only. Graph repair / ranking extraction "
            "are local compute. Provider-native rerank is separate and optional."
        ),
    }


def apply_optional_prices(
    total_requests: int,
    prices: dict[str, float] | None,
) -> dict[str, Any]:
    """prices maps provider -> USD per request (or leave empty)."""
    if not prices:
        return {
            "estimated_cost_usd": None,
            "price_status": "missing_prices",
            "note": "Do not invent provider prices; supply a price config to estimate USD.",
        }
    # If a single blended price is provided as {"blended": x}
    if "blended" in prices and len(prices) == 1:
        return {
            "estimated_cost_usd": float(prices["blended"]) * total_requests,
            "price_status": "blended_price_applied",
            "note": "Blended per-request price; not token-accurate.",
        }
    return {
        "estimated_cost_usd": None,
        "price_status": "provider_prices_present_but_allocation_unspecified",
        "prices_provided_for": sorted(prices),
        "note": "Provide blended or an allocation rule; refusing to invent totals.",
    }


def default_plans() -> dict[str, Any]:
    """Three economical plans matching the benchmark specification."""
    providers = 4
    presentation_orders = 2

    minimal: dict[str, Any] = {
        "name": "minimal_pilot",
        "goal": "Verify real oracle heterogeneity cheaply",
        "datasets": ["scidocs", "fiqa", "hotpotqa", "bright"],
        "queries_per_dataset": 8,
        "pool_size": 10,
        "eval_k": 5,
        "budgets": [2, 4, 6, 8],
        "providers": providers,
        "presentation_orders": presentation_orders,
        "instability_repeat_fraction": 0.1,
        "instability_repeats": 2,
        "policies": 6,
    }
    medium: dict[str, Any] = {
        "name": "medium_pilot",
        "goal": "Workshop / benchmark preprint scale",
        "datasets": ["scidocs", "fiqa", "hotpotqa", "bright"],
        "queries_per_dataset": 25,
        "pool_size": 10,
        "eval_k": 5,
        "budgets": [2, 4, 6, 8, 12],
        "providers": providers,
        "presentation_orders": presentation_orders,
        "instability_repeat_fraction": 0.2,
        "instability_repeats": 2,
        "policies": 6,
    }
    full: dict[str, Any] = {
        "name": "full_benchmark",
        "goal": "Only after pilot shows oracle opportunity",
        "datasets": ["scidocs", "fiqa", "hotpotqa", "bright"],
        "queries_per_dataset": 50,
        "pool_size": 15,
        "eval_k": 10,
        "budgets": [2, 4, 6, 8, 12, 16],
        "providers": providers,
        "presentation_orders": presentation_orders,
        "instability_repeat_fraction": 0.25,
        "instability_repeats": 3,
        "policies": 8,
    }

    out: dict[str, Any] = {"plans": {}, "complete_matrix_warnings": {}}
    for plan in (minimal, medium, full):
        datasets = list(plan["datasets"])
        n_queries = int(plan["queries_per_dataset"]) * len(datasets)
        logged = estimate_logged_policy_requests(
            n_queries=n_queries,
            n_providers=int(plan["providers"]),
            budgets=[int(b) for b in plan["budgets"]],
            presentation_orders=int(plan["presentation_orders"]),
            instability_repeat_fraction=float(plan["instability_repeat_fraction"]),
            instability_repeats=int(plan["instability_repeats"]),
        )
        # Policy factor: each policy cell needs its own trajectory under the
        # same judgment cache when replaying; live collection can share a
        # logged shell. Report both interpretations.
        live_logged_shell = int(logged["total_requests"])
        replay_policy_multiplier = int(plan["policies"])
        matrix = estimate_complete_matrix_requests(
            n_queries=n_queries,
            pool_size=int(plan["pool_size"]),
            n_providers=int(plan["providers"]),
            presentation_orders=int(plan["presentation_orders"]),
            repeats=1,
        )
        out["plans"][str(plan["name"])] = {
            **plan,
            "n_queries_total": n_queries,
            "live_logged_shell_requests": live_logged_shell,
            "if_naively_repeated_per_policy_live": live_logged_shell
            * replay_policy_multiplier,
            "complete_matrix_requests": int(matrix["total_requests"]),
            "cost": apply_optional_prices(live_logged_shell, None),
            "logged_detail": logged,
            "matrix_detail": matrix,
        }
        out["complete_matrix_warnings"][str(plan["name"])] = {
            "message": (
                "A complete pair×provider×orientation matrix grows as P(P-1)/2 "
                "and is usually wasteful relative to a logged acquisition shell."
            ),
            "matrix_requests": int(matrix["total_requests"]),
            "logged_shell_requests": live_logged_shell,
            "matrix_over_logged_ratio": (
                int(matrix["total_requests"]) / live_logged_shell
                if live_logged_shell
                else None
            ),
        }
    return out


def write_plans(path: Path, *, prices: dict[str, float] | None = None) -> dict[str, Any]:
    plans = default_plans()
    if prices:
        for name, plan in plans["plans"].items():
            plan["cost"] = apply_optional_prices(plan["live_logged_shell_requests"], prices)
    path.write_text(json.dumps(plans, indent=2) + "\n", encoding="utf-8")
    return plans
