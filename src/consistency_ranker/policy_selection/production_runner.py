"""Executable production operating point: always UHT plus a non-routing safety floor.

This is the only entry point that implements the interim operating point frozen
after Outcome F. It executes UHT and nothing else. The safety floor is a budget
reservation plus three safeguards that run *inside* the UHT path:

1. a mandatory top-k-insider vs outsider probe before the main run,
2. a prohibition on stopping while the evidence fraction is below threshold,
3. a final adversarial challenger comparison before the ranking is returned.

None of those safeguards can change the executed policy. Anything that would
change the policy lives in ``policy_runner.run_gated_acquisition`` and requires
``ExecutionMode.EXPERIMENTAL_GATE``.

Every safeguard is a method on :class:`ProductionSafeguards` so that tests can
substitute a spy and assert the method was actually called and that its result
changed execution — instantiating the object is not evidence of enforcement.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from consistency_ranker.adaptive_acquisition import synthetic_roster
from consistency_ranker.policy_selection.diagnostic_probes import (
    ProbeConfig,
    _action_for_pair,
    run_diagnostic_probes,
    select_probe_pairs,
)
from consistency_ranker.policy_selection.execution_mode import (
    ExecutionMode,
    resolve_execution_mode,
)
from consistency_ranker.policy_selection.gate_features import extract_features
from consistency_ranker.policy_selection.policy_gate import (
    GateDecision,
    PolicyName,
    PolicySelector,
    select_policy,
)
from consistency_ranker.policy_selection.policy_utility import PolicyOutcome, compute_utility
from consistency_ranker.policy_selection.production_config import (
    PRODUCTION_OPERATING_POINT,
    PRODUCTION_PRIMARY_POLICY,
    ProductionPolicyConfig,
)
from consistency_ranker.policy_selection.safe_fallback import (
    FallbackConfig,
    FallbackState,
    evaluate_safeguards,
    production_safety_actions,
)
from consistency_ranker.prior_robust import (
    make_initial_robust_state,
    run_robust_acquisition,
)
from consistency_ranker.prior_robust.prior_dependence import topk_evidence_coverage
from consistency_ranker.prior_robust.prior_quality import estimate_prior_quality

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_actions import JudgeProfile
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState

__all__ = [
    "SafeguardLog",
    "ProductionSafeguards",
    "ProductionRunResult",
    "run_production_uht",
]


@dataclass
class SafeguardLog:
    """Evidence that each safeguard ran and what it did."""

    reserved_calls: int = 0
    requested_actions: list[str] = field(default_factory=list)
    outsider_probe_required: bool = False
    outsider_probe_executed: bool = False
    outsider_probe_pair: str | None = None
    weak_evidence_stop_checked: bool = False
    weak_evidence_stop_blocked: bool = False
    evidence_fraction_at_stop: float = 0.0
    extra_evidence_calls: int = 0
    final_challenger_required: bool = False
    final_challenger_executed: bool = False
    final_challenger_pair: str | None = None
    safeguard_calls: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reserved_calls": self.reserved_calls,
            "requested_actions": list(self.requested_actions),
            "outsider_probe_required": self.outsider_probe_required,
            "outsider_probe_executed": self.outsider_probe_executed,
            "outsider_probe_pair": self.outsider_probe_pair,
            "weak_evidence_stop_checked": self.weak_evidence_stop_checked,
            "weak_evidence_stop_blocked": self.weak_evidence_stop_blocked,
            "evidence_fraction_at_stop": self.evidence_fraction_at_stop,
            "extra_evidence_calls": self.extra_evidence_calls,
            "final_challenger_required": self.final_challenger_required,
            "final_challenger_executed": self.final_challenger_executed,
            "final_challenger_pair": self.final_challenger_pair,
            "safeguard_calls": self.safeguard_calls,
            "errors": list(self.errors),
        }


class ProductionSafeguards:
    """The approved safety floor, expressed as executable in-UHT actions."""

    def __init__(self, cfg: ProductionPolicyConfig | None = None) -> None:
        self.cfg = cfg or PRODUCTION_OPERATING_POINT

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def _judge_pair(
        state: "AcquisitionState",
        profiles: list["JudgeProfile"],
        judge: Any,
        pair_id: str,
        *,
        reason: str,
    ) -> bool:
        """Execute one judgment on ``pair_id``; return True when it happened."""
        if state.remaining_budget <= 0:
            return False
        action = _action_for_pair(state, pair_id, profiles, 0)
        if action is None:
            return False
        if hasattr(judge, "available") and not judge.available(action):
            return False
        rec = judge.judge(action)
        if rec is None:
            return False
        state.add_evidence([rec])
        state.remaining_budget -= 1
        state.record_action({**action.to_dict(), "exploration_reason": reason})
        return True

    @staticmethod
    def _insider_outsider_pairs(state: "AcquisitionState") -> list[str]:
        """Boundary-crossing pairs using the current (evidence-aware) ranking."""
        ranking = list(state.ranking) or list(state.prior_ranking())
        k = state.top_k
        if len(ranking) <= k:
            return []
        acquired = {pid for pid, agg in state.aggregates.items() if agg.evidence}
        pairs: list[str] = []
        # Weakest insider first: that is the comparison a wrong prior hides behind.
        for i in range(k - 1, -1, -1):
            for j in range(k, len(ranking)):
                pid = state.canonical_pair(ranking[i], ranking[j])
                if pid not in acquired and pid not in pairs:
                    pairs.append(pid)
        return pairs

    # -- safeguards ------------------------------------------------------
    def run_outsider_probe(
        self,
        state: "AcquisitionState",
        profiles: list["JudgeProfile"],
        judge: Any,
        *,
        alt_priors: list[dict[str, float]] | None = None,
        seed: int = 0,
    ) -> bool:
        """Mandatory insider-vs-outsider probe. Returns True if it executed."""
        candidates = select_probe_pairs(
            state,
            design="topk_vs_outsider",
            max_budget=max(1, self.cfg.require_outsider_probe),
            alt_priors=alt_priors,
            seed=seed,
        ) or self._insider_outsider_pairs(state)
        for pid in candidates:
            if self._judge_pair(
                state, profiles, judge, pid, reason="safety_floor:mandatory_outsider_probe"
            ):
                return True
        return False

    def evidence_fraction(self, state: "AcquisitionState") -> float:
        """Fraction of top-k-relevant pairs with reliable *acquired* support.

        Prior-derived and transitively inferred relations deliberately do not
        count: "weak evidence" must mean "few of the comparisons that decide the
        top-k were actually judged", which is the failure mode the stop ban
        exists to prevent.
        """
        cov = topk_evidence_coverage(state)
        return float(cov.get("fraction_acquired") or 0.0)

    def check_weak_evidence_stop(self, state: "AcquisitionState") -> bool:
        """Return True when stopping is prohibited because evidence is too thin."""
        if not self.cfg.prohibit_weak_evidence_stop:
            return False
        frac = self.evidence_fraction(state)
        return frac < self.cfg.min_evidence_fraction_to_stop and state.remaining_budget > 0

    def unsupported_topk_pairs(self, state: "AcquisitionState") -> list[str]:
        """Top-k-relevant pairs that currently have no acquired judgment."""
        ranking = list(state.ranking)
        k = state.top_k
        insiders, outsiders = ranking[:k], ranking[k:]
        pairs: list[str] = []
        for i, a in enumerate(insiders):
            for b in outsiders[: max(k, 3)]:
                pairs.append(state.canonical_pair(a, b))
            for b in insiders[i + 1 :]:
                pairs.append(state.canonical_pair(a, b))
        acquired = {pid for pid, agg in state.aggregates.items() if agg.evidence}
        return [p for p in dict.fromkeys(pairs) if p not in acquired]

    def gather_additional_evidence(
        self,
        state: "AcquisitionState",
        profiles: list["JudgeProfile"],
        judge: Any,
        *,
        max_calls: int,
        seed: int = 0,
        true_ranking: list[str] | None = None,
        alt_priors: list[dict[str, float]] | None = None,
    ) -> int:
        """Acquire the evidence whose absence blocked the stop.

        The stop was blocked because the comparisons that decide the current
        top-k are unjudged, so this judges exactly those pairs. It is an
        evidence action inside UHT: the executed policy does not change and no
        alternative scoring function is used.
        """
        if max_calls <= 0 or state.remaining_budget <= 0:
            return 0
        executed = 0
        for pid in self.unsupported_topk_pairs(state):
            if executed >= max_calls or state.remaining_budget <= 0:
                break
            if self._judge_pair(
                state, profiles, judge, pid, reason="safety_floor:weak_evidence_stop_blocked"
            ):
                executed += 1
        return executed

    def run_final_challenger(
        self,
        state: "AcquisitionState",
        profiles: list["JudgeProfile"],
        judge: Any,
        *,
        seed: int = 0,
    ) -> bool:
        """Final adversarial comparison of the weakest insider vs the best outsider."""
        for pid in self._insider_outsider_pairs(state):
            if self._judge_pair(
                state, profiles, judge, pid, reason="safety_floor:final_challenger"
            ):
                return True
        return False


@dataclass
class ProductionRunResult:
    """Result of a production run. ``executed_policy`` is always ``UHT``."""

    executed_policy: PolicyName
    diagnostic_recommendation: PolicyName | None
    experimental_policy: PolicyName | None
    execution_mode: ExecutionMode
    decision: GateDecision
    outcome: PolicyOutcome
    utility: float
    safeguards: SafeguardLog
    ranking: list[str]
    n_calls: int
    config: ProductionPolicyConfig
    probe: dict[str, Any] | None = None
    result: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "executed_policy": self.executed_policy,
            "diagnostic_recommendation": self.diagnostic_recommendation,
            "experimental_policy": self.experimental_policy,
            "execution_mode": self.execution_mode.value,
            "decision": self.decision.to_dict(),
            "utility": self.utility,
            "safeguards": self.safeguards.to_dict(),
            "ranking": list(self.ranking),
            "n_calls": self.n_calls,
            "config": self.config.to_dict(),
            "probe": dict(self.probe) if self.probe else None,
        }


def _run_uht(
    state: "AcquisitionState",
    profiles: list["JudgeProfile"],
    judge: Any,
    *,
    seed: int,
    true_ranking: list[str] | None,
    alt_priors: list[dict[str, float]] | None,
) -> Any:
    """Run the UHT engine configuration on the state's remaining budget."""
    from consistency_ranker.policy_selection.policy_runner import (
        _build_cfg,
        policy_to_engine_kwargs,
    )

    mapping = policy_to_engine_kwargs(PRODUCTION_PRIMARY_POLICY)  # type: ignore[arg-type]
    cfg = _build_cfg(
        mapping["cfg"], budget=state.remaining_budget, seed=seed, top_k=state.top_k
    )
    return run_robust_acquisition(
        state,
        profiles,
        judge,
        cfg=cfg,
        alt_priors=list(alt_priors or []),
        true_ranking=true_ranking,
        policy_name=mapping["policy_name"],
    )


def _topk_jaccard(ranking: list[str], true_ranking: list[str], k: int) -> float:
    pred, true = set(ranking[:k]), set(true_ranking[:k])
    union = len(pred | true) or 1
    return len(pred & true) / union


def run_production_uht(
    *,
    world: dict[str, Any],
    budget: int,
    top_k: int,
    seed: int,
    config: ProductionPolicyConfig | None = None,
    execution_mode: ExecutionMode | str | None = None,
    selector: PolicySelector | None = None,
    safeguards: ProductionSafeguards | None = None,
    query_id: str = "q0",
) -> ProductionRunResult:
    """Run the interim production operating point end to end.

    The executed policy is UHT in every code path. ``execution_mode`` may be
    ``production_uht`` or ``diagnostic``; ``experimental_gate`` is rejected here
    because experimental routing belongs to ``run_gated_acquisition``.
    """
    mode = resolve_execution_mode(execution_mode)
    if mode is ExecutionMode.EXPERIMENTAL_GATE:
        raise ValueError(
            "run_production_uht never performs experimental routing. Use "
            "policy_runner.run_gated_acquisition for experimental_gate mode."
        )
    cfg = config or PRODUCTION_OPERATING_POINT
    guards = safeguards or ProductionSafeguards(cfg)
    log = SafeguardLog()

    profiles = synthetic_roster(n_models=2, n_prompts=2)
    state = make_initial_robust_state(
        query_id=query_id,
        candidate_ids=list(world["true_ranking"]),
        prior_scores=world["prior_scores"],
        budget=budget,
        top_k=top_k,
        seed=seed,
    )
    alt_priors = world.get("alt_priors") or []
    true_ranking = list(world["true_ranking"])

    # 1. Optional diagnostic probe. Observational: it feeds features only.
    probe_res = None
    if cfg.record_diagnostics or mode is ExecutionMode.DIAGNOSTIC:
        probe_res = run_diagnostic_probes(
            state,
            profiles,
            world["judge"],
            cfg=ProbeConfig(design=cfg.probe_design, max_budget=cfg.probe_budget),  # type: ignore[arg-type]
            alt_priors=alt_priors,
            seed=seed,
        )

    # 2. Reserve budget for the safety floor before any main acquisition.
    reserve = cfg.reserved_safety_calls(state.remaining_budget)
    log.reserved_calls = reserve

    # 3. Mandatory outsider probe (spends part of the reserve).
    fb_state, requested = evaluate_safeguards(
        step=0,
        q_hat=estimate_prior_quality(state, alt_priors=alt_priors).q_hat,
        contradiction_rate=0.0,
        evidence_fraction=guards.evidence_fraction(state),
        remaining_budget=state.remaining_budget,
        intending_stop=False,
        cfg=FallbackConfig(),
        state=FallbackState(),
    )
    log.requested_actions = production_safety_actions(requested)
    log.outsider_probe_required = cfg.require_outsider_probe and (
        "mandatory_outsider_probe" in log.requested_actions
    )
    if log.outsider_probe_required:
        before = state.remaining_budget
        try:
            log.outsider_probe_executed = guards.run_outsider_probe(
                state, profiles, world["judge"], alt_priors=alt_priors, seed=seed
            )
            log.safeguard_calls += before - state.remaining_budget
        except Exception as exc:
            # Fail closed: log and continue on the plain UHT path.
            log.errors.append(f"outsider_probe: {type(exc).__name__}: {exc}")
        if log.outsider_probe_executed:
            log.outsider_probe_pair = _last_action_pair(state)
            reserve = max(0, reserve - 1)

    # 4. Policy selection. Structurally UHT; recorded for auditability.
    feats = extract_features(
        state,
        stage="probe" if (probe_res or log.outsider_probe_executed) else "pre",
        alt_priors=alt_priors,
    )
    sel = selector if selector is not None else PolicySelector(execution_mode=mode)
    if sel.execution_mode.allows_learned_routing:
        raise ValueError(
            "A selector authorised for experimental routing cannot be used in production."
        )
    decision = select_policy(
        feats,
        selector=sel,
        q_hat_heuristic=estimate_prior_quality(state, alt_priors=alt_priors).q_hat,
    )
    if decision.policy != PRODUCTION_PRIMARY_POLICY:  # pragma: no cover - defensive
        log.errors.append(f"selector returned {decision.policy!r}; forcing UHT")
        decision.policy = PRODUCTION_PRIMARY_POLICY  # type: ignore[assignment]

    # 5. Main UHT run on budget minus the remaining safety reserve.
    held_back = min(reserve, state.remaining_budget)
    state.remaining_budget -= held_back
    t0 = time.perf_counter()
    res = _run_uht(
        state,
        profiles,
        world["judge"],
        seed=seed,
        true_ranking=true_ranking,
        alt_priors=alt_priors,
    )
    runtime = time.perf_counter() - t0
    state = res.state
    state.remaining_budget += held_back
    main_calls = res.n_calls

    # 6. Weak-evidence stop prohibition: the run above stopped; if evidence is
    #    thin and budget remains, continue the same UHT policy instead.
    log.weak_evidence_stop_checked = True
    try:
        blocked = guards.check_weak_evidence_stop(state)
    except Exception as exc:
        blocked = False
        log.errors.append(f"weak_evidence_stop: {type(exc).__name__}: {exc}")
    log.weak_evidence_stop_blocked = bool(blocked)
    if blocked:
        allow_extra = max(0, state.remaining_budget - int(cfg.require_final_challenger))
        try:
            extra = guards.gather_additional_evidence(
                state,
                profiles,
                world["judge"],
                max_calls=allow_extra,
                seed=seed + 1,
                true_ranking=true_ranking,
                alt_priors=alt_priors,
            )
        except Exception as exc:
            extra = 0
            log.errors.append(f"gather_additional_evidence: {type(exc).__name__}: {exc}")
        log.extra_evidence_calls = extra
        log.safeguard_calls += extra
    log.evidence_fraction_at_stop = guards.evidence_fraction(state)

    # 7. Final adversarial challenger check before the ranking is returned.
    log.final_challenger_required = bool(cfg.require_final_challenger)
    if log.final_challenger_required:
        before = state.remaining_budget
        try:
            log.final_challenger_executed = guards.run_final_challenger(
                state, profiles, world["judge"], seed=seed + 2
            )
            log.safeguard_calls += before - state.remaining_budget
        except Exception as exc:
            log.errors.append(f"final_challenger: {type(exc).__name__}: {exc}")
        if log.final_challenger_executed:
            log.final_challenger_pair = _last_action_pair(state)

    ranking = list(state.ranking)
    topk_j = _topk_jaccard(ranking, true_ranking, top_k)
    n_calls = (
        main_calls
        + (probe_res.n_executed if probe_res else 0)
        + log.safeguard_calls
    )
    outcome = PolicyOutcome(
        policy=f"production:{PRODUCTION_PRIMARY_POLICY}",
        kendall_tau=None,
        topk_jaccard=topk_j,
        n_calls=n_calls,
        probe_calls=probe_res.n_executed if probe_res else 0,
        total_cost=res.total_cost,
        runtime_s=runtime,
        catastrophic=topk_j <= 0.0,
        buried_recovered=true_ranking[0] in ranking[:top_k],
        stopping_reason=res.stopping_reason,
        exploration_calls=res.report.n_exploration_probes + log.safeguard_calls,
        extra={
            "decision": decision.to_dict(),
            "safeguards": log.to_dict(),
            "executed_policy": PRODUCTION_PRIMARY_POLICY,
        },
    )
    return ProductionRunResult(
        executed_policy="UHT",
        diagnostic_recommendation=decision.diagnostic_recommendation,
        experimental_policy=None,
        execution_mode=mode,
        decision=decision,
        outcome=outcome,
        utility=compute_utility(outcome, sel.weights),
        safeguards=log,
        ranking=ranking,
        n_calls=n_calls,
        config=cfg,
        probe=probe_res.to_dict() if probe_res else None,
        result=res,
    )


def _last_action_pair(state: "AcquisitionState") -> str | None:
    for entry in reversed(state.history):
        if isinstance(entry, dict) and entry.get("pair_id"):
            return str(entry["pair_id"])
    return None
