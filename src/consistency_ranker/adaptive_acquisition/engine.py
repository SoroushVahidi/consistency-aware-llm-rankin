"""Acquisition engine: run a policy against a judge under a budget.

Supports sequential and batched acquisition, dry-run planning, exact call
ceilings (global + per provider via :class:`SpendingCeiling`), online state
updates after every judgment, and resumable state. The same code path drives a
simulated :class:`InteractiveJudge`, a provenance-safe :class:`ReplayPool`, and
(interface-compatibly) a billed judge — actions are deduplicated by billing
signature so restarts never re-issue a judgment.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from consistency_ranker.adaptive_acquisition.acquisition_actions import (
    Action,
    JudgeProfile,
    generate_eligible_actions,
)
from consistency_ranker.adaptive_acquisition.acquisition_policies import (
    AcquisitionPolicy,
    select_batch,
)
from consistency_ranker.adaptive_acquisition.adaptive_stopping import StoppingPolicy
from consistency_ranker.adaptive_acquisition.anytime_metrics import AnytimeTrace
from consistency_ranker.adaptive_acquisition.ranking_impact import (
    ImpactContext,
    topk_boundary_proximity,
)

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState
    from consistency_ranker.multi_provider_eval.spending import SpendingCeiling
    from consistency_ranker.reliability_repair.pair_evidence import NormalizedEvidence


class Judge(Protocol):
    def judge(self, action: Action) -> "NormalizedEvidence | None": ...


def _available(judge: Judge, action: Action) -> bool:
    fn = getattr(judge, "available", None)
    if callable(fn):
        return bool(fn(action))
    has = getattr(judge, "has", None)
    if callable(has):
        return bool(has(action))
    return True


@dataclass
class EngineConfig:
    batch_size: int = 1
    n_impact_samples: int = 24
    max_steps: int = 10_000
    seed: int = 0
    dry_run: bool = False
    one_per_doc_batch: bool = True
    record_rejected: bool = True


@dataclass
class AcquisitionResult:
    state: "AcquisitionState"
    trace: AnytimeTrace
    stopping_reason: str
    n_calls: int
    n_strong_calls: int
    total_cost: float
    action_counts: dict[str, int] = field(default_factory=dict)
    rejected_log: list[dict[str, Any]] = field(default_factory=list)
    planned_actions: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {
            "query_id": self.state.query_id,
            "policy": self.trace.policy,
            "stopping_reason": self.stopping_reason,
            "n_calls": self.n_calls,
            "n_strong_calls": self.n_strong_calls,
            "total_cost": self.total_cost,
            "action_counts": dict(self.action_counts),
            "final_ranking": self.state.ranking,
            **self.trace.final(),
        }


def _topk_impacts(state: "AcquisitionState", ctx: ImpactContext) -> dict[str, float]:
    out = {}
    for pid in state.all_pair_ids():
        out[pid] = topk_boundary_proximity(state, pid, ctx)
    return out


def run_acquisition(
    state: "AcquisitionState",
    policy: AcquisitionPolicy,
    profiles: list[JudgeProfile],
    judge: Judge,
    *,
    stopping: StoppingPolicy | None = None,
    engine_cfg: EngineConfig | None = None,
    spending_ceiling: "SpendingCeiling | None" = None,
    strong_profiles: list[JudgeProfile] | None = None,
    true_ranking: list[str] | None = None,
    full_info_ranking: list[str] | None = None,
    replay_pool: Any | None = None,
) -> AcquisitionResult:
    cfg = engine_cfg or EngineConfig()
    stopping = stopping or StoppingPolicy()
    rng = random.Random(cfg.seed)
    trace = AnytimeTrace(query_id=state.query_id, policy=policy.name)
    strong_profiles = strong_profiles or [p for p in profiles if p.strong]

    n_calls = 0
    n_strong = 0
    total_cost = 0.0
    action_counts: dict[str, int] = {}
    rejected_log: list[dict[str, Any]] = []
    planned: list[dict[str, Any]] = []

    # initial snapshot
    trace.record(
        state, step=0, n_calls=0, cost=0.0, strong_calls=0,
        last_action_type=None, true_ranking=true_ranking,
        full_info_ranking=full_info_ranking,
    )

    step = 0
    stopping_reason = "continue"
    while step < cfg.max_steps:
        # stopping check (pre-action)
        ctx = ImpactContext.build(state, n_samples=cfg.n_impact_samples, seed=cfg.seed + step)
        eligible = generate_eligible_actions(
            state, profiles, strong_profiles=strong_profiles, include_no_action=True
        )
        if replay_pool is not None:
            eligible = replay_pool.available_actions(eligible)

        ranked = policy.select(state, ctx, eligible, rng=rng)
        actionable = [a for a in ranked if a.action_type != "NO_ACTION"]
        best_value = actionable[0].score if actionable else 0.0
        decision = stopping.decide(
            state,
            best_value=best_value,
            topk_impacts=_topk_impacts(state, ctx),
            provider_stopped_reason=(
                spending_ceiling.stopped_reason if spending_ceiling else None
            ),
        )
        if decision.stop:
            stopping_reason = decision.reason
            break
        if not actionable:
            stopping_reason = "no_eligible_actions"
            break

        # choose actions for this step (batch or single)
        if cfg.batch_size > 1:
            chosen = select_batch(
                policy, state, ctx, eligible,
                batch_size=cfg.batch_size,
                one_per_doc=cfg.one_per_doc_batch,
                rng=rng,
            )
        else:
            chosen = actionable[:1]

        if cfg.record_rejected:
            for a in actionable[len(chosen): len(chosen) + 5]:
                rejected_log.append({"step": step, **a.to_dict()})

        if cfg.dry_run:
            planned.extend(a.to_dict() for a in chosen)
            stopping_reason = "dry_run_plan"
            break

        executed_any = False
        for action in chosen:
            if state.remaining_budget <= 0:
                stopping_reason = "budget_exhausted"
                break
            if spending_ceiling is not None and not spending_ceiling.allow(str(action.provider)):
                continue  # per-provider cap; try other actions
            if not _available(judge, action):
                rejected_log.append({"step": step, "reason": "unavailable", **action.to_dict()})
                continue
            rec = judge.judge(action)
            if rec is None:
                rejected_log.append({"step": step, "reason": "judge_none", **action.to_dict()})
                continue
            state.add_evidence([rec])
            state.remaining_budget -= 1
            n_calls += 1
            executed_any = True
            action_counts[action.action_type] = action_counts.get(action.action_type, 0) + 1
            is_strong = action.action_type == "STRONG_MODEL_ADJUDICATION"
            if is_strong or (action.provider or "") == "strong":
                n_strong += 1
            total_cost += float(action.est_cost)
            if spending_ceiling is not None:
                spending_ceiling.record(str(action.provider))
            state.record_action({
                "step": step,
                **action.to_dict(),
                "outcome_z": rec.z,
                "outcome_valid": rec.valid,
            })

        step += 1
        trace.record(
            state, step=step, n_calls=n_calls, cost=total_cost, strong_calls=n_strong,
            last_action_type=chosen[0].action_type if chosen else None,
            true_ranking=true_ranking, full_info_ranking=full_info_ranking,
        )
        if not executed_any and not cfg.dry_run:
            stopping_reason = "no_executable_actions"
            break
        if state.remaining_budget <= 0:
            stopping_reason = "budget_exhausted"
            break

    if stopping_reason == "continue":
        stopping_reason = "max_steps"

    return AcquisitionResult(
        state=state,
        trace=trace,
        stopping_reason=stopping_reason,
        n_calls=n_calls,
        n_strong_calls=n_strong,
        total_cost=total_cost,
        action_counts=action_counts,
        rejected_log=rejected_log,
        planned_actions=planned,
    )


__all__ = ["EngineConfig", "AcquisitionResult", "run_acquisition", "Judge"]
