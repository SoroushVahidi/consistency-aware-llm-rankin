"""Counterfactual action evaluation and expected stability gain.

For an uncertain pair we simulate the possible judgment outcomes *before*
spending a call: for each hypothetical outcome we append a synthetic directional
record, recompute the ranking + stability, and measure the change. Outcome
probabilities come from the current pair estimate and the action's expected
reliability — never from qrels or from any unselected real outcome.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from consistency_ranker.adaptive_acquisition.pair_uncertainty import uncertainty
from consistency_ranker.reliability_repair.pair_evidence import NormalizedEvidence

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_actions import Action
    from consistency_ranker.adaptive_acquisition.acquisition_state import (
        AcquisitionState,
        StateView,
    )


def stability_score(view: "StateView", n_docs: int) -> float:
    """Scalar internal stability in ``[0, 1]`` (higher = more stable).

    Blends top-k set stability (Jaccard-min across sampled extensions), inverse
    sampled rank dispersion, and inverse Kendall-tau dispersion.
    """
    jac = view.stability.get("topk_jaccard_min")
    jac = 1.0 if jac is None else float(jac)

    stats = view.doc_stats or {}
    denom = max(n_docs - 1, 1)
    if stats:
        mean_std = sum(float(s.get("rank_std", 0.0)) for s in stats.values()) / len(stats)
        rank_term = max(0.0, 1.0 - mean_std / denom)
    else:
        rank_term = 1.0

    disp = view.stability.get("extension_tau_dispersion") or {}
    d_std = disp.get("std")
    disp_term = 1.0 if d_std is None else max(0.0, 1.0 - float(d_std))

    return float(0.5 * jac + 0.3 * rank_term + 0.2 * disp_term)


@dataclass
class CounterfactualConfig:
    include_tie: bool = False
    n_stability_samples: int = 12
    reliability_floor: float = 0.55


def _synthetic_outcome_record(
    state: "AcquisitionState", action: "Action", z: int
) -> NormalizedEvidence:
    doc_i, doc_j = state.pair_docs(action.pair_id)
    return NormalizedEvidence(
        query_id=state.query_id,
        canonical_pair_id=action.pair_id,
        doc_i=doc_i,
        doc_j=doc_j,
        displayed_orientation=action.orientation,
        z=z,  # type: ignore[arg-type]
        abstention_subtype="none" if z != 0 else "tie",
        provider=action.provider,
        model=action.model,
        prompt_version=action.prompt_version,
        repetition_index=action.repetition_index,
        temperature=action.temperature,
        valid=z != 0,
        prior_score_i=state.prior_scores.get(doc_i),
        prior_score_j=state.prior_scores.get(doc_j),
        raw_choice="A" if z != 0 else "TIE",
        extra={"counterfactual": True},
    )


def _clone_state_with(
    state: "AcquisitionState", extra: NormalizedEvidence, *, n_samples: int
) -> "AcquisitionState":
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState
    from consistency_ranker.reliability_repair.pipeline import ReliabilityRepairConfig

    cfg = ReliabilityRepairConfig(
        **{**state.repair_config.to_dict(), "n_stability_samples": n_samples}
    )
    clone = AcquisitionState(
        query_id=state.query_id,
        candidate_ids=list(state.candidate_ids),
        prior_scores=dict(state.prior_scores),
        evidence=list(state.evidence) + [extra],
        remaining_budget=state.remaining_budget,
        top_k=state.top_k,
        history=[],
        repair_config=cfg,
        seed=state.seed,
    )
    return clone


def outcome_probabilities(
    state: "AcquisitionState", action: "Action", cfg: CounterfactualConfig
) -> dict[int, float]:
    """P(z=+1), P(z=-1) [, P(z=0)] given current estimate and expected reliability."""
    agg = state.aggregates.get(action.pair_id)
    p_i = 0.5 if agg is None else float(agg.p_hat)  # P(doc_i preferred)
    rel = max(cfg.reliability_floor, float(action.expected_reliability))
    # Blend current belief with reliability: a reliable judge sharpens toward the
    # believed direction; an unreliable one stays near 0.5.
    p_i = 0.5 + (p_i - 0.5) * rel
    probs = {1: p_i, -1: 1.0 - p_i}
    if cfg.include_tie:
        tie = 0.1
        probs = {1: p_i * (1 - tie), -1: (1 - p_i) * (1 - tie), 0: tie}
    return probs


def expected_stability_gain(
    state: "AcquisitionState",
    action: "Action",
    *,
    cfg: CounterfactualConfig | None = None,
) -> dict[str, float]:
    r"""``E[dS] = sum_y P(y|a) [S_after(y) - S_before]`` (Monte-Carlo-free, exact
    over the discrete outcome set)."""
    cfg = cfg or CounterfactualConfig()
    n_docs = len(state.candidate_ids)
    s_before = stability_score(state.view(), n_docs)
    probs = outcome_probabilities(state, action, cfg)
    exp_after = 0.0
    per_outcome = {}
    for z, p in probs.items():
        rec = _synthetic_outcome_record(state, action, int(z))
        clone = _clone_state_with(state, rec, n_samples=cfg.n_stability_samples)
        s_after = stability_score(clone.view(), n_docs)
        per_outcome[z] = s_after
        exp_after += p * s_after
    return {
        "expected_delta_stability": float(exp_after - s_before),
        "s_before": float(s_before),
        "expected_s_after": float(exp_after),
        "s_after_plus": float(per_outcome.get(1, s_before)),
        "s_after_minus": float(per_outcome.get(-1, s_before)),
    }


def cheap_stability_proxy(state: "AcquisitionState", action: "Action") -> float:
    """Inexpensive stand-in for expected stability gain (no re-simulation).

    Uses current vote uncertainty as a proxy for expected reduction: resolving a
    pair we are unsure about is expected to reduce dispersion the most.
    """
    agg = state.aggregates.get(action.pair_id)
    return float(uncertainty(agg, method="vote"))


__all__ = [
    "CounterfactualConfig",
    "stability_score",
    "outcome_probabilities",
    "expected_stability_gain",
    "cheap_stability_proxy",
]
