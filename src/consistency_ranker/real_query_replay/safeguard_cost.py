"""Reconstruct production-safeguard vs plain-UHT cost on synthetic worlds only."""

from __future__ import annotations

from typing import Any

from consistency_ranker.policy_selection.policy_runner import run_named_policy
from consistency_ranker.policy_selection.production_config import PRODUCTION_OPERATING_POINT
from consistency_ranker.policy_selection.production_runner import run_production_uht
from consistency_ranker.prior_robust.adversarial_judges import (
    AdversarialScenario,
    make_adversarial_world,
)


def reconstruct_safeguard_cost_grid(
    *,
    n_items_list: tuple[int, ...] = (8, 16, 20),
    budgets: tuple[int, ...] = (8, 16, 24),
    seeds: tuple[int, ...] = (0, 1, 2, 3),
    top_k: int = 3,
    prior_regime: str = "outsider_buried",
    judge_regime: str = "clean",
) -> list[dict[str, Any]]:
    """Paired plain-UHT vs production-UHT cells (synthetic interactive judges)."""
    rows: list[dict[str, Any]] = []
    for n_items in n_items_list:
        for budget in budgets:
            for seed in seeds:
                scenario = AdversarialScenario(
                    name=f"n{n_items}_b{budget}_s{seed}",
                    prior_regime=prior_regime,  # type: ignore[arg-type]
                    judge_regime=judge_regime,  # type: ignore[arg-type]
                    n_items=n_items,
                    top_k=top_k,
                    seed=seed,
                )
                world = make_adversarial_world(scenario)
                _res, plain_out = run_named_policy(
                    policy="UHT",
                    world=world,
                    budget=budget,
                    top_k=top_k,
                    seed=seed,
                )
                prod = run_production_uht(
                    world=world,
                    budget=budget,
                    top_k=top_k,
                    seed=seed,
                )
                reserved = PRODUCTION_OPERATING_POINT.reserved_safety_calls(budget)
                plain_j = float(plain_out.topk_jaccard or 0.0)
                prod_j = float(prod.outcome.topk_jaccard or 0.0)
                sg = prod.safeguards
                rows.append(
                    {
                        "n_items": n_items,
                        "budget": budget,
                        "seed": seed,
                        "top_k": top_k,
                        "prior_regime": prior_regime,
                        "judge_regime": judge_regime,
                        "reserved_safety_calls": reserved,
                        "plain_uht_calls": int(plain_out.n_calls),
                        "production_uht_calls": int(prod.n_calls),
                        "call_delta": int(prod.n_calls) - int(plain_out.n_calls),
                        "plain_uht_topk_jaccard": plain_j,
                        "production_uht_topk_jaccard": prod_j,
                        "jaccard_delta": prod_j - plain_j,
                        "executed_policy": prod.executed_policy,
                        "outsider_probe_executed": bool(
                            getattr(sg, "outsider_probe_executed", False)
                        ),
                        "final_challenger_executed": bool(
                            getattr(sg, "final_challenger_executed", False)
                        ),
                        "cell_id": f"n{n_items}_b{budget}_s{seed}",
                    }
                )
    return rows
