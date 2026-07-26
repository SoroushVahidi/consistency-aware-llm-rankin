"""Prior perturbation and leave-one-source-out robustness tests."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from consistency_ranker.baseline_ranking import priority_topological_ranking
from consistency_ranker.evaluation import kendall_tau

if TYPE_CHECKING:

    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState


def adjacent_swap_prior(prior: dict[str, float], rng: random.Random) -> dict[str, float]:
    order = sorted(prior, key=lambda d: (-float(prior[d]), d))
    if len(order) < 2:
        return dict(prior)
    i = rng.randrange(len(order) - 1)
    a, b = order[i], order[i + 1]
    out = dict(prior)
    out[a], out[b] = out[b], out[a]
    return out


def score_noise_prior(
    prior: dict[str, float], rng: random.Random, *, noise: float = 1.0
) -> dict[str, float]:
    return {d: float(s) + rng.uniform(-noise, noise) for d, s in prior.items()}


def topk_boundary_swap(
    prior: dict[str, float], k: int, rng: random.Random
) -> dict[str, float]:
    order = sorted(prior, key=lambda d: (-float(prior[d]), d))
    if len(order) <= k:
        return dict(prior)
    a, b = order[k - 1], order[k]
    out = dict(prior)
    out[a], out[b] = out[b], out[a]
    return out


def remove_prior_order(prior: dict[str, float]) -> dict[str, float]:
    return {d: 0.0 for d in prior}


def generate_perturbed_priors(
    prior: dict[str, float],
    *,
    k: int = 3,
    n: int = 8,
    seed: int = 0,
) -> list[tuple[str, dict[str, float]]]:
    rng = random.Random(seed)
    out: list[tuple[str, dict[str, float]]] = [
        ("identity", dict(prior)),
        ("remove_order", remove_prior_order(prior)),
        ("topk_boundary_swap", topk_boundary_swap(prior, k, rng)),
    ]
    for i in range(max(0, n - 3)):
        kind = rng.choice(["adjacent_swap", "score_noise"])
        if kind == "adjacent_swap":
            out.append((f"adjacent_swap_{i}", adjacent_swap_prior(prior, rng)))
        else:
            out.append((f"score_noise_{i}", score_noise_prior(prior, rng)))
    return out


def prior_perturbation_sensitivity(
    state: "AcquisitionState",
    *,
    n: int = 8,
    seed: int = 0,
) -> dict[str, Any]:
    """Measure ranking change under perturbed priors (DAG fixed)."""
    dag = state.view().dag
    if dag.number_of_nodes() == 0:
        return {"n": 0, "mean_topk_jaccard": 1.0, "mean_kendall": 1.0}
    base = priority_topological_ranking(dag, state.prior_scores)
    k = state.top_k
    base_top = set(base[:k])
    jacs, taus = [], []
    for kind, pp in generate_perturbed_priors(state.prior_scores, k=k, n=n, seed=seed):
        if kind == "identity":
            continue
        r = priority_topological_ranking(dag, pp)
        top = set(r[:k])
        union = len(base_top | top) or 1
        jacs.append(len(base_top & top) / union)
        # Restrict to shared nodes.
        if set(r) == set(base):
            taus.append(float(kendall_tau(r, base)))
    return {
        "n": len(jacs),
        "mean_topk_jaccard": sum(jacs) / len(jacs) if jacs else 1.0,
        "min_topk_jaccard": min(jacs) if jacs else 1.0,
        "mean_kendall": sum(taus) / len(taus) if taus else 1.0,
    }


def leave_one_source_out(
    state: "AcquisitionState",
) -> list[dict[str, Any]]:
    """Recompute ranking after removing each provider/prompt/orientation group."""
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState
    from consistency_ranker.reliability_repair.pipeline import ReliabilityRepairConfig

    base = list(state.ranking)
    k = state.top_k
    base_top = set(base[:k])
    rows = []

    def _jaccard(other: list[str]) -> float:
        top = set(other[:k])
        union = len(base_top | top) or 1
        return len(base_top & top) / union

    providers = sorted({e.provider for e in state.evidence if e.provider})
    prompts = sorted({e.prompt_version for e in state.evidence if e.prompt_version})
    orients = sorted(
        {e.displayed_orientation for e in state.evidence if e.displayed_orientation}
    )

    # Remove prior: evidence-only extraction on same evidence.
    from consistency_ranker.prior_robust.robust_extraction import extract_ranking

    r_noprior = extract_ranking(state, method="evidence_only")
    rows.append({"removed": "prior", "topk_jaccard": _jaccard(r_noprior)})

    for p in providers:
        ev = [e for e in state.evidence if e.provider != p]
        clone = AcquisitionState(
            query_id=state.query_id,
            candidate_ids=list(state.candidate_ids),
            prior_scores=dict(state.prior_scores),
            evidence=ev,
            remaining_budget=state.remaining_budget,
            top_k=state.top_k,
            repair_config=ReliabilityRepairConfig(**state.repair_config.to_dict()),
            seed=state.seed,
        )
        rows.append({"removed": f"provider:{p}", "topk_jaccard": _jaccard(clone.ranking)})

    for pr in prompts:
        ev = [e for e in state.evidence if e.prompt_version != pr]
        clone = AcquisitionState(
            query_id=state.query_id,
            candidate_ids=list(state.candidate_ids),
            prior_scores=dict(state.prior_scores),
            evidence=ev,
            remaining_budget=state.remaining_budget,
            top_k=state.top_k,
            repair_config=ReliabilityRepairConfig(**state.repair_config.to_dict()),
            seed=state.seed,
        )
        rows.append({"removed": f"prompt:{pr}", "topk_jaccard": _jaccard(clone.ranking)})

    for o in orients:
        ev = [e for e in state.evidence if e.displayed_orientation != o]
        clone = AcquisitionState(
            query_id=state.query_id,
            candidate_ids=list(state.candidate_ids),
            prior_scores=dict(state.prior_scores),
            evidence=ev,
            remaining_budget=state.remaining_budget,
            top_k=state.top_k,
            repair_config=ReliabilityRepairConfig(**state.repair_config.to_dict()),
            seed=state.seed,
        )
        rows.append({"removed": f"orientation:{o}", "topk_jaccard": _jaccard(clone.ranking)})

    return rows


__all__ = [
    "generate_perturbed_priors",
    "prior_perturbation_sensitivity",
    "leave_one_source_out",
    "adjacent_swap_prior",
    "score_noise_prior",
    "topk_boundary_swap",
    "remove_prior_order",
]
