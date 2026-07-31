"""Adversarial prior + shared-bias regimes for synthetic evaluation.

Builds on ``adaptive_acquisition.interactive_judges`` without exposing truth to
the policy. Corruption is applied to the *prior* and/or judge config; the
latent true ranking remains available only to the experiment harness.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Literal

from consistency_ranker.adaptive_acquisition.interactive_judges import (
    InteractiveJudgeConfig,
    make_interactive_judge,
)

PriorRegime = Literal[
    "accurate",
    "noisy",
    "reversed_topk",
    "outsider_buried",
    "block_permute_topk",
    "tail_ok_topk_wrong",
    "overconfident_wrong",
    "shared_failure_priors",
    "diverse_priors",
]

JudgeRegime = Literal[
    "clean",
    "shared_position_bias",
    "shared_length_bias",
    "provider_family_bias",
    "correlated_repeats",
    "stable_wrong_consensus",
    "nontransitive",
]


@dataclass
class AdversarialScenario:
    name: str
    prior_regime: PriorRegime
    judge_regime: JudgeRegime
    n_items: int = 8
    top_k: int = 3
    seed: int = 0


def corrupt_prior(
    true_ranking: list[str],
    *,
    regime: PriorRegime,
    seed: int,
    top_k: int = 3,
) -> dict[str, float]:
    """Build a corrupted prior from the true ranking. Never shown as truth."""
    rng = random.Random(seed)
    n = len(true_ranking)
    base = {d: float(n - i) for i, d in enumerate(true_ranking)}

    if regime == "accurate":
        # Mild noise.
        return {d: s + rng.uniform(-0.1, 0.1) for d, s in base.items()}
    if regime == "noisy":
        return {d: s + rng.gauss(0, 1.5) for d, s in base.items()}
    if regime == "reversed_topk":
        order = list(true_ranking)
        order[:top_k] = list(reversed(order[:top_k]))
        return {d: float(n - i) for i, d in enumerate(order)}
    if regime == "outsider_buried":
        # Move the true #1 to the bottom of the prior.
        order = list(true_ranking)
        top = order.pop(0)
        order.append(top)
        return {d: float(n - i) for i, d in enumerate(order)}
    if regime == "block_permute_topk":
        order = list(true_ranking)
        block = order[:top_k]
        rng.shuffle(block)
        order[:top_k] = block
        return {d: float(n - i) for i, d in enumerate(order)}
    if regime == "tail_ok_topk_wrong":
        order = list(true_ranking)
        if top_k >= 2:
            order[0], order[top_k] = order[top_k], order[0]
        return {d: float(n - i) for i, d in enumerate(order)}
    if regime == "overconfident_wrong":
        # Wrong order near top with exaggerated margins.
        order = list(reversed(true_ranking[:top_k])) + list(true_ranking[top_k:])
        scores = {}
        for i, d in enumerate(order):
            scores[d] = float(100 - 10 * i)  # huge margins
        return scores
    if regime in ("shared_failure_priors", "diverse_priors"):
        # Single prior still returned; multi-prior handled by caller.
        return {d: s + rng.uniform(-0.5, 0.5) for d, s in base.items()}
    raise ValueError(f"Unknown prior regime {regime!r}")


def alt_priors_for_regime(
    true_ranking: list[str],
    *,
    regime: PriorRegime,
    seed: int,
    top_k: int = 3,
) -> list[dict[str, float]]:
    """Optional alternative priors (fusion diversity / shared failure)."""
    rng = random.Random(seed + 99)
    n = len(true_ranking)
    if regime == "shared_failure_priors":
        bad = corrupt_prior(true_ranking, regime="reversed_topk", seed=seed, top_k=top_k)
        return [bad, dict(bad), {d: s + rng.uniform(-0.05, 0.05) for d, s in bad.items()}]
    if regime == "diverse_priors":
        return [
            corrupt_prior(true_ranking, regime="accurate", seed=seed, top_k=top_k),
            corrupt_prior(true_ranking, regime="noisy", seed=seed + 1, top_k=top_k),
            {d: float(n - i) + rng.uniform(-1, 1) for i, d in enumerate(true_ranking)},
        ]
    return []


def judge_config_for_regime(
    regime: JudgeRegime,
    *,
    n_items: int,
    seed: int,
) -> InteractiveJudgeConfig:
    if regime == "clean":
        return InteractiveJudgeConfig(
            n_items=n_items, base_accuracy=0.85, position_bias=0.05, seed=seed
        )
    if regime == "shared_position_bias":
        return InteractiveJudgeConfig(
            n_items=n_items, base_accuracy=0.8, position_bias=0.35,
            prompt_bias={"prompt_0": 0.15, "prompt_1": 0.15}, seed=seed,
        )
    if regime == "shared_length_bias":
        # Prefer higher-index docs via prompt-independent accuracy tilt using
        # systematic_error + position as proxy for length preference.
        return InteractiveJudgeConfig(
            n_items=n_items, base_accuracy=0.8, position_bias=0.05,
            systematic_error_rate=0.2, seed=seed,
        )
    if regime == "provider_family_bias":
        return InteractiveJudgeConfig(
            n_items=n_items, base_accuracy=0.75, position_bias=0.1,
            provider_accuracy={"prov_0": 0.7, "prov_1": 0.7, "prov_2": 1.15},
            seed=seed,
        )
    if regime == "correlated_repeats":
        return InteractiveJudgeConfig(
            n_items=n_items, base_accuracy=0.8, position_bias=0.08,
            systematic_error_rate=0.25, seed=seed,
        )
    if regime == "stable_wrong_consensus":
        # High accuracy on a flipped latent — implemented by high systematic flip.
        return InteractiveJudgeConfig(
            n_items=n_items, base_accuracy=0.9, position_bias=0.0,
            systematic_error_rate=0.45, seed=seed,
        )
    if regime == "nontransitive":
        return InteractiveJudgeConfig(
            n_items=n_items, base_accuracy=0.8, position_bias=0.05,
            non_transitivity=0.25, seed=seed,
        )
    raise ValueError(f"Unknown judge regime {regime!r}")


def make_adversarial_world(
    scenario: AdversarialScenario,
) -> dict[str, Any]:
    """Return truth, corrupted prior, alt priors, and interactive judge."""
    jcfg = judge_config_for_regime(
        scenario.judge_regime, n_items=scenario.n_items, seed=scenario.seed
    )
    judge = make_interactive_judge(
        n_items=scenario.n_items, config=jcfg, seed=scenario.seed
    )
    truth = list(judge.true_ranking)
    prior = corrupt_prior(
        truth, regime=scenario.prior_regime, seed=scenario.seed, top_k=scenario.top_k
    )
    alts = alt_priors_for_regime(
        truth, regime=scenario.prior_regime, seed=scenario.seed, top_k=scenario.top_k
    )
    # True pair winners for diagnostics (harness only).
    from consistency_ranker.reliability_repair.pair_evidence import canonical_pair_id

    true_winners = {}
    for i, a in enumerate(truth):
        for b in truth[i + 1 :]:
            true_winners[canonical_pair_id("q0", a, b)] = a
    return {
        "judge": judge,
        "true_ranking": truth,
        "prior_scores": prior,
        "alt_priors": alts,
        "true_pair_winners": true_winners,
        "scenario": scenario,
    }


__all__ = [
    "PriorRegime",
    "JudgeRegime",
    "AdversarialScenario",
    "corrupt_prior",
    "alt_priors_for_regime",
    "judge_config_for_regime",
    "make_adversarial_world",
]
