"""Controlled synthetic pairwise judgments with known reliability."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from consistency_ranker.reliability_repair.pair_evidence import (
    NormalizedEvidence,
    canonical_pair_id,
)


@dataclass
class SyntheticConfig:
    n_items: int = 8
    n_models: int = 3
    n_prompts: int = 2
    orientations: bool = True
    repeats: int = 2
    base_accuracy: float = 0.8
    position_bias: float = 0.1  # P(prefer displayed A regardless)
    abstention_rate: float = 0.05
    invalid_rate: float = 0.02
    seed: int = 0
    topk_harder: int = 3  # first k ranks are harder (lower accuracy)


def generate_synthetic_judgments(
    cfg: SyntheticConfig,
) -> tuple[list[NormalizedEvidence], dict[str, Any]]:
    """Generate judgments over a ground-truth total order item_00 ≻ item_01 ≻ ..."""
    rng = random.Random(cfg.seed)
    items = [f"item_{i:02d}" for i in range(cfg.n_items)]
    # True rank: lower index = better
    true_rank = {d: i + 1 for i, d in enumerate(items)}
    models = [f"model_{m}" for m in range(cfg.n_models)]
    prompts = [f"prompt_{p}" for p in range(cfg.n_prompts)]
    providers = [f"prov_{m}" for m in range(cfg.n_models)]

    evidence: list[NormalizedEvidence] = []
    truth_pairs = {}
    for i, a in enumerate(items):
        for b in items[i + 1 :]:
            # a better than b
            truth_pairs[canonical_pair_id("q0", a, b)] = a

    for a_idx, a in enumerate(items):
        for b in items[a_idx + 1 :]:
            true_winner = a
            hard = true_rank[a] <= cfg.topk_harder or true_rank[b] <= cfg.topk_harder
            acc = cfg.base_accuracy - (0.15 if hard else 0.0)
            for mi, model in enumerate(models):
                model_acc = acc - 0.05 * mi  # later models slightly worse
                for prompt in prompts:
                    orients = ["ab", "ba"] if cfg.orientations else ["ab"]
                    for orient in orients:
                        for rep in range(cfg.repeats):
                            if rng.random() < cfg.invalid_rate:
                                z_choice = "INVALID"
                                winner = None
                                valid = False
                                subtype_choice = "INVALID"
                            elif rng.random() < cfg.abstention_rate:
                                z_choice = "TIE"
                                winner = None
                                valid = True
                                subtype_choice = "TIE"
                            else:
                                # Position bias: with prob prefer displayed A
                                if rng.random() < cfg.position_bias:
                                    shown_a = a if orient == "ab" else b
                                    winner = shown_a
                                elif rng.random() < model_acc:
                                    winner = true_winner
                                else:
                                    winner = b if true_winner == a else a
                                z_choice = "A"
                                valid = True
                                subtype_choice = "A"
                            evidence.append(
                                NormalizedEvidence(
                                    query_id="q0",
                                    canonical_pair_id=canonical_pair_id("q0", a, b),
                                    doc_i=a if a < b else b,
                                    doc_j=b if a < b else a,
                                    displayed_orientation=orient,
                                    z=(
                                        0
                                        if winner is None
                                        else (
                                            1
                                            if winner == (a if a < b else b)
                                            else -1
                                        )
                                    ),
                                    abstention_subtype=(
                                        "invalid"
                                        if subtype_choice == "INVALID"
                                        else (
                                            "tie"
                                            if subtype_choice == "TIE"
                                            else "none"
                                        )
                                    ),
                                    provider=providers[mi],
                                    model=model,
                                    prompt_version=prompt,
                                    repetition_index=rep,
                                    temperature=0.0,
                                    valid=valid and winner is not None,
                                    prior_score_i=float(cfg.n_items - true_rank[a if a < b else b]),
                                    prior_score_j=float(cfg.n_items - true_rank[b if a < b else a]),
                                    prior_rank_i=true_rank[a if a < b else b],
                                    prior_rank_j=true_rank[b if a < b else a],
                                    raw_choice=z_choice,
                                )
                            )
    meta = {
        "true_ranking": items,
        "true_pair_winners": truth_pairs,
        "config": cfg.__dict__,
    }
    return evidence, meta


def corrupt_aggregates_flip(
    true_ranking: list[str],
    *,
    flip_rate: float,
    seed: int,
) -> list[tuple[str, str, str]]:
    """Return list of (winner, loser, pair_id) with random flips from truth."""
    rng = random.Random(seed)
    prefs = []
    for i, a in enumerate(true_ranking):
        for b in true_ranking[i + 1 :]:
            winner, loser = a, b
            if rng.random() < flip_rate:
                winner, loser = b, a
            prefs.append((winner, loser, canonical_pair_id("q0", a, b)))
    return prefs
