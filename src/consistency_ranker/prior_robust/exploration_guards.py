"""Forced exploration safeguards for adaptive acquisition."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_actions import Action
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState

ExplorationKind = Literal[
    "epsilon",
    "scheduled_probe",
    "coverage",
    "boundary_challenger",
    "prior_disagreement",
    "sentinel",
]


@dataclass
class ExplorationConfig:
    epsilon: float = 0.15
    scheduled_probe_every: int = 4  # every N steps reserve a probe
    min_topk_coverage: int = 1  # min acquired judgments per top-k doc
    min_challenger_per_insider: int = 1
    n_sentinel_probes: int = 2
    enable_epsilon: bool = True
    enable_scheduled: bool = True
    enable_coverage: bool = True
    enable_challenger: bool = True
    enable_sentinel: bool = True


@dataclass
class ExplorationState:
    probes_done: int = 0
    sentinel_done: int = 0
    coverage_done: dict[str, int] = field(default_factory=dict)
    challenger_done: dict[str, int] = field(default_factory=dict)
    log: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "probes_done": self.probes_done,
            "sentinel_done": self.sentinel_done,
            "coverage_done": dict(self.coverage_done),
            "challenger_done": dict(self.challenger_done),
            "log": list(self.log),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExplorationState":
        return cls(
            probes_done=int(data.get("probes_done", 0)),
            sentinel_done=int(data.get("sentinel_done", 0)),
            coverage_done=dict(data.get("coverage_done", {})),
            challenger_done=dict(data.get("challenger_done", {})),
            log=list(data.get("log", [])),
        )


def _new_pair_actions(eligible: list["Action"]) -> list["Action"]:
    return [a for a in eligible if a.action_type == "NEW_PAIR"]


def coverage_gaps(
    state: "AcquisitionState", cfg: ExplorationConfig
) -> list[str]:
    """Docs in current top-k with fewer than min acquired judgments."""
    ranking = state.ranking
    topk = ranking[: state.top_k]
    gaps = []
    for d in topk:
        n = sum(
            1
            for e in state.evidence
            if e.z != 0 and (e.doc_i == d or e.doc_j == d)
        )
        if n < cfg.min_topk_coverage:
            gaps.append(d)
    return gaps


def select_exploration_action(
    state: "AcquisitionState",
    eligible: list["Action"],
    *,
    step: int,
    cfg: ExplorationConfig,
    explor: ExplorationState,
    rng: random.Random,
    challenger_pairs: list[str] | None = None,
    disagreement_pairs: list[str] | None = None,
) -> tuple["Action | None", str | None]:
    """Return a forced-exploration action and reason, or (None, None)."""
    actionable = [a for a in eligible if a.action_type != "NO_ACTION"]
    if not actionable:
        return None, None
    new_pairs = _new_pair_actions(actionable) or actionable

    # 1) Scheduled prior-testing probe.
    if (
        cfg.enable_scheduled
        and cfg.scheduled_probe_every > 0
        and step > 0
        and step % cfg.scheduled_probe_every == 0
    ):
        # Prefer distant prior pairs (larger rank distance).
        prior_rank = {d: i for i, d in enumerate(state.prior_ranking())}

        def dist(a):
            return abs(prior_rank.get(a.doc_i, 0) - prior_rank.get(a.doc_j, 0))

        a = max(new_pairs, key=dist)
        explor.probes_done += 1
        explor.log.append({"step": step, "kind": "scheduled_probe", "pair": a.pair_id})
        return a, "scheduled_probe"

    # 2) Coverage constraints.
    if cfg.enable_coverage:
        gaps = coverage_gaps(state, cfg)
        for d in gaps:
            cands = [a for a in new_pairs if a.doc_i == d or a.doc_j == d]
            if cands:
                a = rng.choice(cands)
                explor.coverage_done[d] = explor.coverage_done.get(d, 0) + 1
                explor.log.append({"step": step, "kind": "coverage", "doc": d, "pair": a.pair_id})
                return a, "coverage"

    # 3) Boundary challenger pairs.
    if cfg.enable_challenger and challenger_pairs:
        for pid in challenger_pairs:
            insider = None
            ranking = state.ranking
            topk = set(ranking[: state.top_k])
            di, dj = state.pair_docs(pid)
            if di in topk:
                insider = di
            elif dj in topk:
                insider = dj
            if insider is None:
                continue
            if explor.challenger_done.get(insider, 0) >= cfg.min_challenger_per_insider:
                continue
            cands = [a for a in new_pairs if a.pair_id == pid]
            if cands:
                a = cands[0]
                explor.challenger_done[insider] = explor.challenger_done.get(insider, 0) + 1
                explor.log.append(
                    {"step": step, "kind": "boundary_challenger", "pair": pid, "insider": insider}
                )
                return a, "boundary_challenger"

    # 4) Prior-disagreement pairs.
    if disagreement_pairs:
        for pid in disagreement_pairs:
            cands = [a for a in new_pairs if a.pair_id == pid]
            if cands:
                a = cands[0]
                explor.log.append({"step": step, "kind": "prior_disagreement", "pair": pid})
                return a, "prior_disagreement"

    # 5) Sentinel random probes (small budget).
    if cfg.enable_sentinel and explor.sentinel_done < cfg.n_sentinel_probes:
        a = rng.choice(new_pairs)
        explor.sentinel_done += 1
        explor.log.append({"step": step, "kind": "sentinel", "pair": a.pair_id})
        return a, "sentinel"

    # 6) Epsilon-greedy.
    if cfg.enable_epsilon and rng.random() < cfg.epsilon:
        a = rng.choice(actionable)
        explor.log.append({"step": step, "kind": "epsilon", "pair": a.pair_id})
        return a, "epsilon"

    return None, None


def exploration_complete(
    state: "AcquisitionState",
    cfg: ExplorationConfig,
    explor: ExplorationState,
) -> bool:
    """True when mandatory exploration probes are done."""
    if cfg.enable_coverage and coverage_gaps(state, cfg):
        return False
    if cfg.enable_challenger:
        ranking = state.ranking
        for d in ranking[: state.top_k]:
            if explor.challenger_done.get(d, 0) < cfg.min_challenger_per_insider:
                # Only require if there exists a challenger opportunity later;
                # treat incomplete as not done.
                return False
    if cfg.enable_sentinel and explor.sentinel_done < cfg.n_sentinel_probes:
        return False
    return True


__all__ = [
    "ExplorationConfig",
    "ExplorationState",
    "ExplorationKind",
    "select_exploration_action",
    "exploration_complete",
    "coverage_gaps",
]
