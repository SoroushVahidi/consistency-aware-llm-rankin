"""Map named acquisition policies to prior_robust / adaptive engines.

``run_named_policy`` executes one explicitly named policy. ``run_gated_acquisition``
is the **experimental** research harness: it may route to challenger/hybrid,
escalate policies from safeguard requests, and simulate switching, so it
requires ``ExecutionMode.EXPERIMENTAL_GATE``. The production operating point
lives in ``production_runner.run_production_uht``.
"""

from __future__ import annotations

import copy
import time
from typing import Any

from consistency_ranker.adaptive_acquisition import synthetic_roster
from consistency_ranker.policy_selection.diagnostic_probes import (
    ProbeConfig,
    run_diagnostic_probes,
)
from consistency_ranker.policy_selection.execution_mode import (
    ExecutionMode,
    resolve_execution_mode,
)
from consistency_ranker.policy_selection.gate_features import extract_features
from consistency_ranker.policy_selection.policy_gate import (
    PolicyName,
    PolicySelector,
    select_policy,
)
from consistency_ranker.policy_selection.policy_switching import (
    SwitchConfig,
    SwitchState,
    evaluate_switch,
)
from consistency_ranker.policy_selection.policy_utility import PolicyOutcome, compute_utility
from consistency_ranker.policy_selection.safe_fallback import (
    FallbackConfig,
    FallbackState,
    evaluate_safeguards,
    record_uht_step,
)
from consistency_ranker.prior_robust import (
    RobustEngineConfig,
    make_initial_robust_state,
    run_robust_acquisition,
)
from consistency_ranker.prior_robust.exploration_guards import ExplorationConfig
from consistency_ranker.prior_robust.prior_quality import estimate_prior_quality


def policy_to_engine_kwargs(policy: PolicyName) -> dict[str, Any]:
    """Translate a high-level policy name into RobustEngineConfig kwargs + name."""
    if policy == "UHT":
        return {
            "policy_name": "plain_uht",
            "cfg": {"plain_baseline": True, "score_mode": "uncertainty_x_topk_impact"},
        }
    if policy == "UHT_EXPLORE":
        return {
            "policy_name": "uht_epsilon",
            "cfg": {
                "score_mode": "uncertainty_x_topk_impact_epsilon",
                "exploration": ExplorationConfig(
                    epsilon=0.12,
                    enable_epsilon=True,
                    enable_scheduled=False,
                    enable_coverage=False,
                    enable_challenger=False,
                    enable_sentinel=False,
                ),
            },
        }
    if policy == "CHALLENGER":
        return {
            "policy_name": "challenger_focused",
            "cfg": {
                "score_mode": "challenger_resolution",
                "exploration": ExplorationConfig(
                    epsilon=0.1,
                    enable_challenger=True,
                    enable_coverage=True,
                    enable_scheduled=True,
                    scheduled_probe_every=3,
                    min_challenger_per_insider=1,
                ),
            },
        }
    if policy == "ROBUST_COMBINED":
        return {
            "policy_name": "robust_combined",
            "cfg": {"score_mode": "robust_combined"},
        }
    if policy == "BROAD_STATIC":
        return {
            "policy_name": "uht_scheduled_probes",
            "cfg": {
                "score_mode": "uncertainty_x_topk_impact",
                "exploration": ExplorationConfig(
                    epsilon=0.2,
                    enable_epsilon=True,
                    enable_scheduled=True,
                    scheduled_probe_every=3,
                    enable_coverage=True,
                    enable_challenger=True,
                    enable_sentinel=True,
                    n_sentinel_probes=2,
                ),
            },
        }
    if policy == "NO_PRIOR":
        return {
            "policy_name": "no_prior",
            "cfg": {"score_mode": "no_prior", "prior_mode": "none"},
        }
    if policy == "HYBRID":
        return {
            "policy_name": "uht_guarded",
            "cfg": {
                "score_mode": "robust_combined",
                "prior_mode": "adaptive",
                "exploration": ExplorationConfig(
                    epsilon=0.1,
                    enable_epsilon=True,
                    enable_challenger=True,
                    enable_coverage=True,
                    enable_scheduled=True,
                    scheduled_probe_every=4,
                    n_sentinel_probes=1,
                ),
            },
        }
    # STOP_OR_FALLBACK: short robust run / conservative
    return {
        "policy_name": "quality_gated",
        "cfg": {"score_mode": "uncertainty_x_topk_impact"},
    }


def _build_cfg(raw: dict[str, Any], *, budget: int, seed: int, top_k: int) -> RobustEngineConfig:
    kwargs = dict(raw)
    explor = kwargs.pop("exploration", None)
    cfg = RobustEngineConfig(
        budget=budget,
        seed=seed,
        top_k=top_k,
        score_mode=kwargs.get("score_mode", "uncertainty_x_topk_impact"),
        prior_mode=kwargs.get("prior_mode", "adaptive"),
        plain_baseline=bool(kwargs.get("plain_baseline", False)),
        use_robust_stopping=bool(kwargs.get("use_robust_stopping", True)),
        n_impact_samples=int(kwargs.get("n_impact_samples", 8)),
        n_stability_samples=int(kwargs.get("n_stability_samples", 8)),
    )
    if explor is not None:
        cfg.exploration = explor
    return cfg


def run_named_policy(
    *,
    policy: PolicyName,
    world: dict[str, Any],
    budget: int,
    top_k: int,
    seed: int,
    query_id: str = "q0",
) -> tuple[Any, PolicyOutcome]:
    """Run one named policy on a synthetic world; return (result, outcome)."""
    mapping = policy_to_engine_kwargs(policy)
    profiles = synthetic_roster(n_models=2, n_prompts=2)
    st = make_initial_robust_state(
        query_id=query_id,
        candidate_ids=list(world["true_ranking"]),
        prior_scores=world["prior_scores"],
        budget=budget,
        top_k=top_k,
        seed=seed,
    )
    cfg = _build_cfg(mapping["cfg"], budget=budget, seed=seed, top_k=top_k)
    t0 = time.perf_counter()
    res = run_robust_acquisition(
        st,
        profiles,
        world["judge"],
        cfg=cfg,
        alt_priors=world.get("alt_priors") or [],
        true_ranking=world["true_ranking"],
        policy_name=mapping["policy_name"],
    )
    runtime = time.perf_counter() - t0
    final = res.trace.final()
    topk_j = float(final.get("topk_jaccard_truth") or 0.0)
    tau = final.get("kendall_tau_truth")
    buried = world["true_ranking"][0]
    recovered = buried in res.state.ranking[:top_k]
    # Catastrophic: true top-1 not in predicted top-k under burial-like priors,
    # or top-k Jaccard == 0.
    catastrophic = topk_j <= 0.0
    stable = float(final.get("topk_jaccard_min") or 0.0) >= 0.9
    wrong = topk_j < 1.0
    outcome = PolicyOutcome(
        policy=policy,
        kendall_tau=float(tau) if tau is not None else None,
        topk_jaccard=topk_j,
        n_calls=res.n_calls,
        total_cost=res.total_cost,
        runtime_s=runtime,
        catastrophic=catastrophic,
        buried_recovered=recovered,
        stable_but_wrong=bool(stable and wrong),
        confidently_wrong=bool(stable and catastrophic),
        stopping_reason=res.stopping_reason,
        exploration_calls=res.report.n_exploration_probes,
        extra={"q_hat": res.lambda_state.q_hat, "g_prior": res.report.prior_dependence_gap},
    )
    return res, outcome


def run_gated_acquisition(
    *,
    world: dict[str, Any],
    selector: PolicySelector,
    budget: int,
    top_k: int,
    seed: int,
    probe_budget: int = 3,
    probe_design: str = "mixed_diagnostic",
    enable_switching: bool = False,
    enable_fallback: bool = True,
    oracle_best: PolicyName | None = None,
    query_id: str = "q0",
    execution_mode: ExecutionMode | str | None = None,
) -> dict[str, Any]:
    """EXPERIMENTAL: probe → select policy → run (optional switching / escalation).

    Requires ``ExecutionMode.EXPERIMENTAL_GATE`` both here and on ``selector``.
    Learned routing and policy escalation happen in this function, which is why
    it can never be reached from a production default.
    """
    mode = resolve_execution_mode(execution_mode) if execution_mode is not None else (
        selector.execution_mode
    )
    if not mode.allows_learned_routing or not selector.execution_mode.allows_learned_routing:
        raise ValueError(
            "run_gated_acquisition performs experimental policy routing and requires "
            "ExecutionMode.EXPERIMENTAL_GATE on both the call and the selector "
            f"(call={mode.value}, selector={selector.execution_mode.value}). "
            "Use production_runner.run_production_uht for the production operating point."
        )
    profiles = synthetic_roster(n_models=2, n_prompts=2)
    st = make_initial_robust_state(
        query_id=query_id,
        candidate_ids=list(world["true_ranking"]),
        prior_scores=world["prior_scores"],
        budget=budget,
        top_k=top_k,
        seed=seed,
    )
    # Pre features (no judgments).
    pre_feats = extract_features(st, stage="pre", alt_priors=world.get("alt_priors"))

    probe_res = None
    if probe_budget > 0 and selector.mode not in ("always_uht", "oracle", "random", "majority_best"):
        probe_res = run_diagnostic_probes(
            st,
            profiles,
            world["judge"],
            cfg=ProbeConfig(design=probe_design, max_budget=probe_budget),  # type: ignore[arg-type]
            alt_priors=world.get("alt_priors"),
            seed=seed,
        )

    feats = extract_features(
        st,
        stage="probe" if probe_budget > 0 else "pre",
        alt_priors=world.get("alt_priors"),
    )
    q_heur = estimate_prior_quality(st, alt_priors=world.get("alt_priors")).q_hat
    decision = select_policy(
        feats,
        selector=selector,
        q_hat_heuristic=q_heur,
        oracle_best=oracle_best,
        rng_u=(seed % 1000) / 1000.0,
    )

    # If uncertain and STOP_OR_FALLBACK with remaining budget for more probes.
    if decision.policy == "STOP_OR_FALLBACK" and st.remaining_budget > 0 and probe_budget < 5:
        extra = run_diagnostic_probes(
            st,
            profiles,
            world["judge"],
            cfg=ProbeConfig(design="adaptive_diagnostic", max_budget=min(2, st.remaining_budget)),
            alt_priors=world.get("alt_priors"),
            seed=seed + 1,
        )
        feats = extract_features(st, stage="probe", alt_priors=world.get("alt_priors"))
        q_heur = estimate_prior_quality(st, alt_priors=world.get("alt_priors")).q_hat
        # Re-select with soft mixture after extra probes.
        sel2 = copy.copy(selector)
        sel2.mode = "soft_mixture"
        decision = select_policy(feats, selector=sel2, q_hat_heuristic=q_heur, oracle_best=oracle_best)
        decision.reason = "extra_probes_then_" + decision.reason
        if probe_res is not None:
            probe_res.n_executed += extra.n_executed

    switch_state = SwitchState(current_policy=decision.policy, initial_policy=decision.policy)
    fallback_state = FallbackState()

    # One-shot: run selected policy on remaining budget.
    # For switching mode we still run the initial policy to completion in this
    # lightweight experiment harness, but we simulate switch decisions on a
    # credibility trajectory derived from post-hoc q_hat updates every few steps
    # by running HYBRID which already adapts internally, and logging switches.
    run_policy = decision.policy
    if enable_fallback:
        fb_state, actions = evaluate_safeguards(
            step=0,
            q_hat=decision.g_q,
            contradiction_rate=float(feats.values.get("reliable_contradiction_rate", 0.0)),
            evidence_fraction=float(feats.values.get("evidence_only_stability_proxy", 0.0)),
            remaining_budget=st.remaining_budget,
            intending_stop=False,
            cfg=FallbackConfig(),
            state=fallback_state,
        )
        fallback_state = fb_state
        from consistency_ranker.policy_selection.safe_fallback import (
            apply_experimental_escalation,
        )

        # Experimental routing: may rewrite UHT → HYBRID/CHALLENGER. Unreachable
        # from production, which executes the same requests inside UHT instead.
        run_policy = apply_experimental_escalation(  # type: ignore[assignment]
            run_policy, actions, q_hat=decision.g_q
        )

    if enable_switching:
        # Prefer staged/hybrid engine that can adapt; log prospective switches.
        run_policy = "HYBRID" if decision.policy in ("UHT", "CHALLENGER", "HYBRID") else run_policy
        switch_state = evaluate_switch(
            switch_state,
            step=1,
            q_hat=decision.g_q,
            contradiction_rate=float(feats.values.get("reliable_contradiction_rate", 0.0)),
            buried_signal=float(feats.values.get("n_outsiders_defeating_insiders", 0.0)),
            policy_probs=decision.policy_probs,
            cfg=SwitchConfig(),
        )

    mapping = policy_to_engine_kwargs(run_policy)  # type: ignore[arg-type]
    cfg = _build_cfg(mapping["cfg"], budget=st.remaining_budget, seed=seed, top_k=top_k)
    # Preserve already-acquired probe evidence by continuing on same state.
    t0 = time.perf_counter()
    res = run_robust_acquisition(
        st,
        profiles,
        world["judge"],
        cfg=cfg,
        alt_priors=world.get("alt_priors") or [],
        true_ranking=world["true_ranking"],
        policy_name=mapping["policy_name"],
    )
    runtime = time.perf_counter() - t0

    if enable_switching:
        # Post-hoc switch evaluation using final q_hat vs initial.
        q_final = res.lambda_state.q_hat
        switch_state = evaluate_switch(
            switch_state,
            step=max(3, res.n_calls // 2),
            q_hat=q_final,
            contradiction_rate=float(
                estimate_prior_quality(res.state).high_conf_contradiction_rate or 0.0
            ),
            buried_signal=float(feats.values.get("n_outsiders_defeating_insiders", 0.0)),
            acquisition_gain=0.02,
            challenger_yield=0.5 if q_final < decision.g_q else 0.1,
            policy_probs=decision.policy_probs,
        )
        record_uht_step(fallback_state, run_policy in ("UHT", "UHT_EXPLORE"))

    final = res.trace.final()
    topk_j = float(final.get("topk_jaccard_truth") or 0.0)
    tau = final.get("kendall_tau_truth")
    buried = world["true_ranking"][0]
    recovered = buried in res.state.ranking[:top_k]
    stable = float(final.get("topk_jaccard_min") or 0.0) >= 0.9
    outcome = PolicyOutcome(
        policy=f"gated:{selector.mode}:{decision.policy}",
        kendall_tau=float(tau) if tau is not None else None,
        topk_jaccard=topk_j,
        n_calls=res.n_calls + (probe_res.n_executed if probe_res else 0),
        probe_calls=probe_res.n_executed if probe_res else 0,
        total_cost=res.total_cost,
        runtime_s=runtime,
        catastrophic=topk_j <= 0.0,
        buried_recovered=recovered,
        stable_but_wrong=bool(stable and topk_j < 1.0),
        stopping_reason=res.stopping_reason,
        exploration_calls=res.report.n_exploration_probes,
        extra={
            "decision": decision.to_dict(),
            "pre_features": pre_feats.to_dict(),
            "probe_features": feats.to_dict(),
            "switch": switch_state.to_dict(),
            "fallback": fallback_state.to_dict(),
            "run_policy": run_policy,
        },
    )
    return {
        "outcome": outcome,
        "decision": decision,
        "result": res,
        "utility": compute_utility(outcome, selector.weights),
        "probe": probe_res.to_dict() if probe_res else None,
        "executed_policy": run_policy,
        "experimental_policy": run_policy,
        "diagnostic_recommendation": decision.diagnostic_recommendation,
        "execution_mode": mode.value,
    }


__all__ = [
    "policy_to_engine_kwargs",
    "run_named_policy",
    "run_gated_acquisition",
]
