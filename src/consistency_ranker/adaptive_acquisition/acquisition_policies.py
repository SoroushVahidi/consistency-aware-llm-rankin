"""Acquisition policies: scoring, baselines, exploration and batch selection.

A policy scores eligible actions and returns them ranked best-first. The engine
consumes the ranked list (top-1 for sequential, a diverse prefix for batch).
Scores compose the independent signals from ``pair_uncertainty``,
``ranking_impact`` and ``structural_signals``; several score modes and every
required baseline are provided by :func:`make_policy`.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from consistency_ranker.adaptive_acquisition.counterfactual import (
    CounterfactualConfig,
    expected_stability_gain,
)
from consistency_ranker.adaptive_acquisition.pair_uncertainty import uncertainty
from consistency_ranker.adaptive_acquisition.provider_escalation import ActionReliabilityModel
from consistency_ranker.adaptive_acquisition.ranking_impact import (
    ImpactContext,
    impact,
    topk_boundary_proximity,
)
from consistency_ranker.adaptive_acquisition.structural_signals import structural_relevance
from consistency_ranker.adaptive_acquisition.transitivity import is_skippable

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_actions import Action
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState

EPS = 1e-9

ScoreMode = str

SCORE_MODES: tuple[str, ...] = (
    "uncertainty",
    "impact",
    "u_times_h",
    "u_h_s",
    "cost_normalized",
    "expected_stability_gain",
    "cost_normalized_esg",
    "random",
    "prior_margin",
    "prior_adjacent",
    "cycle_only",
    "ambiguity_only",
    "topk_boundary_only",
    "repo_fixed",
    "uniform",
)

Exploration = str


@dataclass
class ScoreConfig:
    score_mode: ScoreMode = "u_h_s"
    uncertainty_method: str = "vote"
    impact_method: str = "topk_membership_sensitivity"
    structural_mode: str = "blend"
    reliability_model: str = "smoothed"
    exploration: Exploration = "none"
    epsilon: float = 0.1
    ucb_c: float = 0.5
    use_transitivity: bool = False
    trans_min_path_reliability: float = 0.4
    esg_samples: int = 10
    esg_prefilter_top: int = 12  # only re-simulate the most promising candidates
    restrict_new_pair: bool = False  # baselines that only query new pairs


@dataclass
class AcquisitionPolicy:
    name: str
    config: ScoreConfig = field(default_factory=ScoreConfig)

    def __post_init__(self) -> None:
        self._rel = ActionReliabilityModel(method=self.config.reliability_model)  # type: ignore[arg-type]

    # ---- scoring ------------------------------------------------------
    def base_score(
        self, state: "AcquisitionState", ctx: ImpactContext, action: "Action"
    ) -> tuple[float, dict[str, float]]:
        if action.action_type == "NO_ACTION":
            return (-math.inf, {})
        pair = action.pair_id
        agg = state.aggregates.get(pair)
        mode = self.config.score_mode

        if mode == "random":
            return (0.0, {})
        if mode == "repo_fixed" or mode == "uniform":
            # deterministic fixed order over pairs (collect_all_pairs order)
            order = {pid: i for i, pid in enumerate(state.all_pair_ids())}
            return (-float(order.get(pair, 1e9)), {})
        if mode == "prior_margin":
            doc_i, doc_j = state.pair_docs(pair)
            margin = abs(
                state.prior_scores.get(doc_i, 0.0) - state.prior_scores.get(doc_j, 0.0)
            )
            return (-margin, {"prior_margin": margin})
        if mode == "prior_adjacent":
            di, dj = state.pair_docs(pair)
            d = abs(ctx.prior_rank.get(di, 999) - ctx.prior_rank.get(dj, 999))
            return (1.0 / (1.0 + d), {"prior_rank_dist": d})

        u = uncertainty(agg, method=self.config.uncertainty_method)
        if mode == "uncertainty":
            return (u, {"U": u})
        h = impact(state, pair, ctx, method=self.config.impact_method)
        if mode == "impact":
            return (h, {"H": h})
        if mode == "topk_boundary_only":
            hb = topk_boundary_proximity(state, pair, ctx)
            return (hb, {"H_topk": hb})
        s = structural_relevance(state, pair, ctx, mode=self.config.structural_mode)
        if mode == "cycle_only":
            sc = structural_relevance(state, pair, ctx, mode="inconsistency")
            return (sc, {"S_cycle": sc})
        if mode == "ambiguity_only":
            sa = structural_relevance(state, pair, ctx, mode="ambiguity")
            return (sa, {"S_amb": sa})
        if mode == "u_times_h":
            return (u * h, {"U": u, "H": h})
        if mode == "u_h_s":
            return (u * h * s, {"U": u, "H": h, "S": s})

        r = self._rel.expected(state, action, ctx=ctx)
        c = max(action.est_cost, EPS)
        if mode == "cost_normalized":
            val = u * h * s * r / (c + EPS)
            return (val, {"U": u, "H": h, "S": s, "R": r, "C": c})
        if mode in ("expected_stability_gain", "cost_normalized_esg"):
            cf = CounterfactualConfig(n_stability_samples=self.config.esg_samples)
            esg = expected_stability_gain(state, action, cfg=cf)["expected_delta_stability"]
            if mode == "expected_stability_gain":
                return (esg, {"ESG": esg, "R": r})
            return (esg * r / (c + EPS), {"ESG": esg, "R": r, "C": c})
        raise ValueError(f"Unknown score mode {mode!r}")

    def _exploration_adjust(
        self,
        score: float,
        state: "AcquisitionState",
        action: "Action",
        rng: random.Random,
    ) -> float:
        exp = self.config.exploration
        if exp == "none":
            return score
        if exp == "ucb":
            n_pair = len(state.evidence_for_pair(action.pair_id))
            t = max(len(state.evidence), 1)
            bonus = self.config.ucb_c * math.sqrt(math.log(t + 1) / (n_pair + 1))
            return score + bonus
        if exp == "thompson":
            # sample reliability noise as posterior draw
            return score * (0.5 + rng.random())
        return score

    # ---- selection ----------------------------------------------------
    def _filter_eligible(
        self, state: "AcquisitionState", ctx: ImpactContext, eligible: list["Action"]
    ) -> list["Action"]:
        out = eligible
        if self.config.restrict_new_pair:
            new = [a for a in out if a.action_type == "NEW_PAIR"]
            out = new or [a for a in out if a.action_type != "NO_ACTION"]
        if self.config.use_transitivity:
            kept = []
            for a in out:
                if a.action_type == "NO_ACTION":
                    kept.append(a)
                    continue
                if is_skippable(
                    state,
                    a.pair_id,
                    ctx,
                    min_path_reliability=self.config.trans_min_path_reliability,
                ):
                    continue
                kept.append(a)
            out = kept or out
        return out

    def select(
        self,
        state: "AcquisitionState",
        ctx: ImpactContext,
        eligible: list["Action"],
        *,
        rng: random.Random | None = None,
    ) -> list["Action"]:
        rng = rng or random.Random(state.seed)
        pool = self._filter_eligible(state, ctx, eligible)
        actionable = [a for a in pool if a.action_type != "NO_ACTION"]
        if not actionable:
            return [a for a in pool if a.action_type == "NO_ACTION"]

        # Epsilon-greedy exploration: with prob epsilon return a random ordering.
        if self.config.exploration == "epsilon" and rng.random() < self.config.epsilon:
            rng.shuffle(actionable)
            for a in actionable:
                a.score = 0.0
                a.reason = (a.reason + "|explore").strip("|")
            return actionable

        # For expensive ESG modes, prefilter to the most promising candidates by
        # a cheap uncertainty*impact proxy so we only re-simulate a handful.
        esg_modes = {"expected_stability_gain", "cost_normalized_esg"}
        prefilter: set[int] | None = None
        if self.config.score_mode in esg_modes and len(actionable) > self.config.esg_prefilter_top:
            proxy = []
            for a in actionable:
                agg = state.aggregates.get(a.pair_id)
                u = uncertainty(agg, method=self.config.uncertainty_method)
                h = impact(state, a.pair_id, ctx, method=self.config.impact_method)
                proxy.append((u * h, id(a)))
            proxy.sort(key=lambda t: -t[0])
            prefilter = {i for _, i in proxy[: self.config.esg_prefilter_top]}

        scored = []
        for a in actionable:
            if prefilter is not None and id(a) not in prefilter:
                a.score = -math.inf
                a.score_breakdown = {"prefiltered": 1.0}
                scored.append(a)
                continue
            base, breakdown = self.base_score(state, ctx, a)
            base = self._exploration_adjust(base, state, a, rng)
            a.score = float(base)
            a.score_breakdown = breakdown
            scored.append(a)
        # Random policy: shuffle deterministically.
        if self.config.score_mode == "random":
            rng.shuffle(scored)
            return scored
        scored.sort(key=lambda a: (-a.score, a.pair_id, a.action_type))
        return scored


def select_batch(
    policy: AcquisitionPolicy,
    state: "AcquisitionState",
    ctx: ImpactContext,
    eligible: list["Action"],
    *,
    batch_size: int,
    one_per_doc: bool = True,
    diversity_penalty: float = 0.5,
    rng: random.Random | None = None,
) -> list["Action"]:
    """Greedy diverse batch: avoid multiple actions on the same doc / pair.

    Applies a submodular-style penalty: once a document (or pair) is chosen this
    batch, remaining actions touching it are down-weighted.
    """
    ranked = policy.select(state, ctx, eligible, rng=rng)
    ranked = [a for a in ranked if a.action_type != "NO_ACTION"]
    chosen: list["Action"] = []
    used_docs: set[str] = set()
    used_pairs: set[str] = set()
    # Work on a mutable score copy.
    remaining = list(ranked)
    while remaining and len(chosen) < batch_size:
        best = None
        best_val = -math.inf
        for a in remaining:
            penalty = 0.0
            if a.pair_id in used_pairs:
                penalty += diversity_penalty
            if one_per_doc and (a.doc_i in used_docs or a.doc_j in used_docs):
                penalty += diversity_penalty
            val = a.score - penalty
            if val > best_val:
                best_val, best = val, a
        if best is None:
            break
        if one_per_doc and (best.doc_i in used_docs or best.doc_j in used_docs) and len(chosen) > 0:
            # skip conflicting doc for strict one-per-doc batches
            remaining.remove(best)
            continue
        chosen.append(best)
        used_pairs.add(best.pair_id)
        used_docs.add(best.doc_i)
        used_docs.add(best.doc_j)
        remaining.remove(best)
    return chosen


# ---- factory ---------------------------------------------------------

def make_policy(name: str) -> AcquisitionPolicy:
    """Construct one of the required baselines / variants by name."""
    presets: dict[str, ScoreConfig] = {
        # baselines
        "random_unqueried": ScoreConfig(score_mode="random", restrict_new_pair=True),
        "random_adjacent_prior": ScoreConfig(
            score_mode="prior_adjacent", restrict_new_pair=True, exploration="epsilon", epsilon=0.5
        ),
        "static_prior_adjacent": ScoreConfig(score_mode="prior_adjacent", restrict_new_pair=True),
        "smallest_prior_margin": ScoreConfig(score_mode="prior_margin", restrict_new_pair=True),
        "uncertainty_only": ScoreConfig(score_mode="uncertainty"),
        "cycle_participation_only": ScoreConfig(score_mode="cycle_only"),
        "ambiguity_only": ScoreConfig(score_mode="ambiguity_only"),
        "topk_boundary_only": ScoreConfig(score_mode="topk_boundary_only"),
        "uncertainty_x_topk_impact": ScoreConfig(
            score_mode="u_times_h", impact_method="topk_membership_sensitivity"
        ),
        "uncertainty_x_structural": ScoreConfig(
            score_mode="u_h_s", impact_method="reachability_impact"
        ),
        "expected_stability_gain": ScoreConfig(
            score_mode="expected_stability_gain", esg_samples=6, esg_prefilter_top=8
        ),
        "cost_normalized_esg": ScoreConfig(
            score_mode="cost_normalized_esg", esg_samples=6, esg_prefilter_top=8
        ),
        "cheap_first_escalation": ScoreConfig(
            score_mode="cost_normalized", impact_method="topk_membership_sensitivity"
        ),
        "strongest_model_only": ScoreConfig(
            score_mode="u_times_h", reliability_model="fixed"
        ),
        "uniform_all_pairs": ScoreConfig(score_mode="uniform", restrict_new_pair=True),
        "current_repo_fixed": ScoreConfig(score_mode="repo_fixed", restrict_new_pair=True),
        # variants
        "adaptive_uhs_transitive": ScoreConfig(score_mode="u_h_s", use_transitivity=True),
        "adaptive_uhs_epsilon": ScoreConfig(
            score_mode="u_h_s", exploration="epsilon", epsilon=0.15
        ),
        "adaptive_uhs_ucb": ScoreConfig(score_mode="u_h_s", exploration="ucb"),
        "cost_normalized_value": ScoreConfig(score_mode="cost_normalized"),
    }
    if name not in presets:
        raise ValueError(f"Unknown policy {name!r}. Known: {sorted(presets)}")
    return AcquisitionPolicy(name=name, config=presets[name])


REQUIRED_BASELINES: tuple[str, ...] = (
    "random_unqueried",
    "random_adjacent_prior",
    "static_prior_adjacent",
    "smallest_prior_margin",
    "uncertainty_only",
    "cycle_participation_only",
    "ambiguity_only",
    "topk_boundary_only",
    "uncertainty_x_topk_impact",
    "uncertainty_x_structural",
    "expected_stability_gain",
    "cost_normalized_esg",
    "cheap_first_escalation",
    "strongest_model_only",
    "uniform_all_pairs",
    "current_repo_fixed",
)


__all__ = [
    "ScoreConfig",
    "AcquisitionPolicy",
    "select_batch",
    "make_policy",
    "REQUIRED_BASELINES",
    "SCORE_MODES",
]
