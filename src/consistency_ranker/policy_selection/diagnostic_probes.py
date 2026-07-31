"""Standardized diagnostic probe phase before main policy selection.

Probe designs discriminate trustworthy priors from locally wrong top-k,
buried outsiders, globally noisy priors, shared judge bias, and weak-but-
not-misleading priors — under an explicit maximum budget.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_actions import (
        Action,
        JudgeProfile,
    )
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState

ProbeDesign = Literal[
    "random_pairs",
    "prior_adjacent",
    "boundary_pairs",
    "topk_vs_outsider",
    "cross_prior_disagreement",
    "rank_distance_stratified",
    "mixed_diagnostic",
    "adaptive_diagnostic",
]


@dataclass
class ProbeConfig:
    design: ProbeDesign = "mixed_diagnostic"
    max_budget: int = 3
    profile_index: int = 0  # which roster profile to use for probes


@dataclass
class ProbeResult:
    pairs: list[str]
    n_executed: int
    design: str
    remaining_budget: int
    log: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pairs": list(self.pairs),
            "n_executed": self.n_executed,
            "design": self.design,
            "remaining_budget": self.remaining_budget,
            "log": list(self.log),
        }


def _prior_rank(state: "AcquisitionState") -> dict[str, int]:
    ranking = state.prior_ranking()
    return {d: i for i, d in enumerate(ranking)}


def select_probe_pairs(
    state: "AcquisitionState",
    *,
    design: ProbeDesign = "mixed_diagnostic",
    max_budget: int = 3,
    alt_priors: list[dict[str, float]] | None = None,
    seed: int = 0,
) -> list[str]:
    """Return up to ``max_budget`` pair_ids (no execution)."""
    rng = random.Random(seed)
    ranking = state.prior_ranking()
    k = state.top_k
    n = len(ranking)
    if n < 2 or max_budget <= 0:
        return []
    pr = _prior_rank(state)
    all_pids = list(state.all_pair_ids())
    acquired = {pid for pid, agg in state.aggregates.items() if agg.evidence}

    def unused(pids: list[str]) -> list[str]:
        return [p for p in pids if p not in acquired]

    adjacent = []
    for i in range(n - 1):
        adjacent.append(state.canonical_pair(ranking[i], ranking[i + 1]))

    boundary = []
    if n > k:
        for i in range(max(0, k - 2), k):
            for j in range(k, min(n, k + 3)):
                boundary.append(state.canonical_pair(ranking[i], ranking[j]))

    topk_out = []
    if n > k:
        for i in range(k):
            for j in range(k, min(n, k + 4)):
                topk_out.append(state.canonical_pair(ranking[i], ranking[j]))

    # Cross-prior disagreement: pairs where alt priors disagree on order.
    disagree: list[str] = []
    if alt_priors:
        for pid in all_pids:
            di, dj = state.pair_docs(pid)
            signs = []
            for prior in [state.prior_scores, *alt_priors]:
                if di not in prior or dj not in prior:
                    continue
                signs.append(1 if float(prior[di]) >= float(prior[dj]) else -1)
            if len(set(signs)) > 1:
                disagree.append(pid)

    # Rank-distance stratified: short / mid / long.
    by_dist: dict[str, list[str]] = {"short": [], "mid": [], "long": []}
    for pid in all_pids:
        di, dj = state.pair_docs(pid)
        dist = abs(pr.get(di, 0) - pr.get(dj, 0))
        if dist <= 1:
            by_dist["short"].append(pid)
        elif dist <= max(2, k):
            by_dist["mid"].append(pid)
        else:
            by_dist["long"].append(pid)

    chosen: list[str] = []

    if design == "random_pairs":
        pool = unused(all_pids)
        rng.shuffle(pool)
        chosen = pool[:max_budget]
    elif design == "prior_adjacent":
        chosen = unused(adjacent)[:max_budget]
    elif design == "boundary_pairs":
        chosen = unused(boundary)[:max_budget]
    elif design == "topk_vs_outsider":
        chosen = unused(topk_out)[:max_budget]
    elif design == "cross_prior_disagreement":
        pool = unused(disagree) or unused(boundary) or unused(adjacent)
        chosen = pool[:max_budget]
    elif design == "rank_distance_stratified":
        for bucket in ("short", "mid", "long"):
            pool = unused(by_dist[bucket])
            if pool and len(chosen) < max_budget:
                chosen.append(pool[0])
        # fill
        for bucket in ("mid", "long", "short"):
            for p in unused(by_dist[bucket]):
                if p not in chosen:
                    chosen.append(p)
                if len(chosen) >= max_budget:
                    break
            if len(chosen) >= max_budget:
                break
    elif design == "adaptive_diagnostic":
        # Prefer boundary + buried challenger + one disagreement if any.
        for pool in (boundary, topk_out, disagree, adjacent):
            for p in unused(pool):
                if p not in chosen:
                    chosen.append(p)
                if len(chosen) >= max_budget:
                    break
            if len(chosen) >= max_budget:
                break
    else:  # mixed_diagnostic
        prefs: list[str] = []
        # 1) top-k adjacent boundary
        if n > k:
            prefs.append(state.canonical_pair(ranking[k - 1], ranking[k]))
        # 2) top insider vs far outsider (burial detector)
        if n > k + 1:
            prefs.append(state.canonical_pair(ranking[0], ranking[-1]))
        # 3) adjacent near top
        if n > 1:
            prefs.append(state.canonical_pair(ranking[0], ranking[1]))
        # optional disagreement
        if disagree:
            prefs.append(disagree[0])
        for p in prefs:
            if p not in acquired and p not in chosen:
                chosen.append(p)
            if len(chosen) >= max_budget:
                break
        if len(chosen) < max_budget:
            for p in unused(boundary + adjacent):
                if p not in chosen:
                    chosen.append(p)
                if len(chosen) >= max_budget:
                    break

    return chosen[:max_budget]


def _action_for_pair(
    state: "AcquisitionState",
    pair_id: str,
    profiles: list["JudgeProfile"],
    profile_index: int = 0,
) -> "Action | None":
    from consistency_ranker.adaptive_acquisition.acquisition_actions import (
        generate_eligible_actions,
    )

    eligible = generate_eligible_actions(state, profiles, include_no_action=False)
    new_pairs = [a for a in eligible if a.action_type == "NEW_PAIR" and a.pair_id == pair_id]
    if not new_pairs:
        return None
    # Prefer requested profile if present.
    if 0 <= profile_index < len(profiles):
        pref = profiles[profile_index]
        for a in new_pairs:
            if (
                a.provider == pref.provider
                and a.model == pref.model
                and a.prompt_version == pref.prompt_version
            ):
                return a
    return new_pairs[0]


def run_diagnostic_probes(
    state: "AcquisitionState",
    profiles: list["JudgeProfile"],
    judge,
    *,
    cfg: ProbeConfig | None = None,
    alt_priors: list[dict[str, float]] | None = None,
    seed: int = 0,
) -> ProbeResult:
    """Execute up to ``cfg.max_budget`` diagnostic judgments in-place on ``state``."""
    cfg = cfg or ProbeConfig()
    pairs = select_probe_pairs(
        state,
        design=cfg.design,
        max_budget=cfg.max_budget,
        alt_priors=alt_priors,
        seed=seed,
    )
    log: list[dict[str, Any]] = []
    executed = 0
    for pid in pairs:
        if state.remaining_budget <= 0:
            break
        action = _action_for_pair(state, pid, profiles, cfg.profile_index)
        if action is None:
            continue
        if hasattr(judge, "available") and not judge.available(action):
            log.append({"pair_id": pid, "status": "unavailable"})
            continue
        rec = judge.judge(action)
        if rec is None:
            log.append({"pair_id": pid, "status": "null"})
            continue
        state.add_evidence([rec])
        state.remaining_budget -= 1
        state.record_action(
            {
                **action.to_dict(),
                "exploration_reason": f"diagnostic_probe:{cfg.design}",
                "probe_design": cfg.design,
            }
        )
        executed += 1
        log.append({"pair_id": pid, "status": "ok", "z": rec.z})
    return ProbeResult(
        pairs=pairs,
        n_executed=executed,
        design=cfg.design,
        remaining_budget=state.remaining_budget,
        log=log,
    )


def probe_informativeness_scores() -> dict[str, dict[str, float]]:
    """Qualitative diagnostic value scores used by the experiment report.

    These are design priors (not fitted on qrels) describing which failure
    modes each probe type is intended to detect.
    """
    modes = (
        "trustworthy",
        "local_topk_wrong",
        "buried_outsider",
        "globally_noisy",
        "shared_bias",
        "weak_not_misleading",
    )
    table = {
        "random_pairs": dict(zip(modes, (0.3, 0.3, 0.2, 0.5, 0.2, 0.3))),
        "prior_adjacent": dict(zip(modes, (0.6, 0.7, 0.2, 0.4, 0.3, 0.5))),
        "boundary_pairs": dict(zip(modes, (0.5, 0.8, 0.6, 0.4, 0.3, 0.5))),
        "topk_vs_outsider": dict(zip(modes, (0.4, 0.6, 0.9, 0.4, 0.3, 0.4))),
        "cross_prior_disagreement": dict(zip(modes, (0.5, 0.6, 0.5, 0.5, 0.4, 0.6))),
        "rank_distance_stratified": dict(zip(modes, (0.5, 0.5, 0.7, 0.6, 0.3, 0.5))),
        "mixed_diagnostic": dict(zip(modes, (0.7, 0.8, 0.85, 0.6, 0.4, 0.6))),
        "adaptive_diagnostic": dict(zip(modes, (0.7, 0.8, 0.85, 0.55, 0.45, 0.55))),
    }
    return table


__all__ = [
    "ProbeDesign",
    "ProbeConfig",
    "ProbeResult",
    "select_probe_pairs",
    "run_diagnostic_probes",
    "probe_informativeness_scores",
]
