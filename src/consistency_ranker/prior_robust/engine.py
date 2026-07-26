"""Prior-robust adaptive acquisition engine.

Wraps the base acquisition loop with:
* prior-quality estimation and adaptive λ_q;
* evidence-supported stability;
* forced exploration + challenger pool;
* bias diagnostics / counter-bias actions;
* robust stopping and empirical robustness reports.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from consistency_ranker.adaptive_acquisition.acquisition_actions import (
    JudgeProfile,
    generate_eligible_actions,
)
from consistency_ranker.adaptive_acquisition.acquisition_policies import make_policy
from consistency_ranker.adaptive_acquisition.acquisition_state import (
    AcquisitionState,
    initial_state,
)
from consistency_ranker.adaptive_acquisition.anytime_metrics import AnytimeTrace
from consistency_ranker.adaptive_acquisition.engine import EngineConfig
from consistency_ranker.adaptive_acquisition.ranking_impact import ImpactContext
from consistency_ranker.prior_robust.adaptive_prior import (
    AdaptivePriorState,
    PriorMode,
    update_lambda,
)
from consistency_ranker.prior_robust.bias_diagnostics import (
    diagnose_bias,
    suggest_counter_bias_actions,
)
from consistency_ranker.prior_robust.challenger_pool import (
    ChallengerPool,
    challenger_pairs,
    expand_window,
    init_challenger_pool,
    promote_strong_outsiders,
)
from consistency_ranker.prior_robust.evidence_stability import compute_evidence_stability
from consistency_ranker.prior_robust.exploration_guards import (
    ExplorationConfig,
    ExplorationState,
    select_exploration_action,
)
from consistency_ranker.prior_robust.prior_perturbation import prior_perturbation_sensitivity
from consistency_ranker.prior_robust.prior_quality import estimate_prior_quality
from consistency_ranker.prior_robust.robust_acquisition import (
    RobustScoreConfig,
    RobustScoreMode,
    score_action,
)
from consistency_ranker.prior_robust.robust_extraction import extract_ranking
from consistency_ranker.prior_robust.robust_stopping import (
    RobustStopConfig,
    evaluate_robust_stop,
)
from consistency_ranker.prior_robust.robustness_report import (
    RobustnessReport,
    categorize,
)
from consistency_ranker.prior_robust.shared_bias import effective_judge_count


@dataclass
class RobustEngineConfig:
    budget: int = 28
    top_k: int = 3
    seed: int = 0
    n_impact_samples: int = 12
    n_stability_samples: int = 16
    score_mode: RobustScoreMode = "uncertainty_x_topk_impact"
    prior_mode: PriorMode = "adaptive"
    extraction_method: str = "adaptive"
    use_robust_stopping: bool = True
    exploration: ExplorationConfig = field(
        default_factory=lambda: ExplorationConfig(
            epsilon=0.1,
            scheduled_probe_every=5,
            n_sentinel_probes=1,
            min_challenger_per_insider=1,
            enable_epsilon=True,
            enable_scheduled=True,
            enable_coverage=True,
            enable_challenger=True,
            enable_sentinel=True,
        )
    )
    stop_cfg: RobustStopConfig = field(
        default_factory=lambda: RobustStopConfig(
            min_evidence_fraction=0.25,
            max_g_prior=0.35,
            require_exploration=True,
            require_challenger_coverage=False,  # soft: logged but not hard-gated by default
            min_effective_sources=1.0,
        )
    )
    initial_window: int | None = None
    plain_baseline: bool = False


@dataclass
class RobustAcquisitionResult:
    state: AcquisitionState
    trace: AnytimeTrace
    stopping_reason: str
    n_calls: int
    n_strong_calls: int
    total_cost: float
    action_counts: dict[str, int]
    lambda_state: AdaptivePriorState
    explor: ExplorationState
    pool: ChallengerPool
    report: RobustnessReport
    failure_trace: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        return {
            "query_id": self.state.query_id,
            "policy": self.trace.policy,
            "stopping_reason": self.stopping_reason,
            "n_calls": self.n_calls,
            "n_strong_calls": self.n_strong_calls,
            "total_cost": self.total_cost,
            "action_counts": dict(self.action_counts),
            "lambda_q": self.lambda_state.lambda_q,
            "q_hat": self.lambda_state.q_hat,
            "category": self.report.category,
            "g_prior": self.report.prior_dependence_gap,
            "s_evidence": self.report.evidence_only_stability,
            "final_ranking": self.state.ranking,
            **{k: v for k, v in self.trace.final().items() if k not in ("query_id", "policy")},
        }


def run_robust_acquisition(
    state: AcquisitionState,
    profiles: list[JudgeProfile],
    judge,
    *,
    cfg: RobustEngineConfig | None = None,
    alt_priors: list[dict[str, float]] | None = None,
    true_ranking: list[str] | None = None,
    true_prior_quality: float | None = None,
    policy_name: str = "robust_combined",
) -> RobustAcquisitionResult:
    cfg = cfg or RobustEngineConfig()
    rng = random.Random(cfg.seed)
    score_cfg = RobustScoreConfig(mode=cfg.score_mode)

    # Quality-gated meta-policy (Outcome D): probe → trust UHT or distrust robust.
    if policy_name == "quality_gated":
        # Warm-start with a few forced distant probes, estimate Q, then branch.
        q_probe = estimate_prior_quality(state, alt_priors=alt_priors)
        if q_probe.n_acquired < 3 and state.remaining_budget > 0:
            profiles_sorted = list(profiles)
            eligible = generate_eligible_actions(state, profiles_sorted, include_no_action=False)
            prior_rank = {d: i for i, d in enumerate(state.prior_ranking())}
            ranking = state.prior_ranking()
            k = state.top_k
            new_pairs = [a for a in eligible if a.action_type == "NEW_PAIR"]
            # Mix: one top-k adjacent, one insider-outsider challenger, one distant.
            preferred = []
            if len(ranking) > k:
                preferred.append(state.canonical_pair(ranking[k - 1], ranking[k]))
            if len(ranking) > k + 1:
                preferred.append(state.canonical_pair(ranking[0], ranking[-1]))
            if len(ranking) > 1:
                preferred.append(state.canonical_pair(ranking[0], ranking[1]))
            chosen_actions = []
            for pid in preferred:
                for a in new_pairs:
                    if a.pair_id == pid and a not in chosen_actions:
                        chosen_actions.append(a)
                        break
            # Fill with mid-distance pairs if needed.
            mid = sorted(
                new_pairs,
                key=lambda a: abs(
                    abs(prior_rank.get(a.doc_i, 0) - prior_rank.get(a.doc_j, 0)) - max(2, k)
                ),
            )
            for a in mid:
                if a not in chosen_actions:
                    chosen_actions.append(a)
                if len(chosen_actions) >= 3:
                    break
            for a in chosen_actions[: min(3, state.remaining_budget)]:
                rec = judge.judge(a)
                if rec is None:
                    continue
                state.add_evidence([rec])
                state.remaining_budget -= 1
                state.record_action({**a.to_dict(), "exploration_reason": "quality_gate_probe"})
            q_probe = estimate_prior_quality(state, alt_priors=alt_priors)

        # Trust if probes agree with prior / few high-conf contradictions.
        agr = q_probe.agreement_rate
        hc = q_probe.high_conf_contradiction_rate
        trust = False
        if agr is not None and agr >= 0.65 and (hc is None or hc <= 0.25):
            trust = True
        elif hc is not None and hc >= 0.35:
            trust = False
        elif q_probe.q_hat >= 0.55 and (hc is None or hc < 0.3):
            trust = True
        # Default: if very little signal, lightly trust (preserve UHT efficiency).
        if agr is None and hc is None:
            trust = q_probe.q_hat >= 0.45

        if trust:
            # Trust prior → plain UHT on remaining budget.
            from consistency_ranker.adaptive_acquisition.adaptive_stopping import StoppingPolicy
            from consistency_ranker.adaptive_acquisition.engine import run_acquisition
            pol = make_policy("uncertainty_x_topk_impact")
            res = run_acquisition(
                state, pol, profiles, judge,
                engine_cfg=EngineConfig(n_impact_samples=cfg.n_impact_samples, seed=cfg.seed),
                stopping=StoppingPolicy(criteria=("budget",)),
                true_ranking=true_ranking,
            )
            stab = compute_evidence_stability(
                res.state, n_samples=cfg.n_stability_samples, seed=cfg.seed
            )
            q = estimate_prior_quality(res.state, alt_priors=alt_priors)
            lam = AdaptivePriorState(lambda_q=1.0, mode="fixed", q_hat=q.q_hat)
            explor = ExplorationState()
            pool = init_challenger_pool(res.state, initial_window=cfg.initial_window)
            report = _build_report(
                res.state, stab, q, lam, explor, pool,
                stopping_reason=res.stopping_reason + "|quality_gated_trust_prior",
                bias_suspected=[],
            )
            return RobustAcquisitionResult(
                state=res.state, trace=res.trace, stopping_reason=report.stopping_reason,
                n_calls=res.n_calls, n_strong_calls=res.n_strong_calls,
                total_cost=res.total_cost, action_counts=res.action_counts,
                lambda_state=lam, explor=explor, pool=pool, report=report,
                failure_trace={"branch": "trust_prior", "q_hat": q.q_hat},
            )
        # Distrust prior → robust combined path.
        cfg = RobustEngineConfig(
            budget=state.remaining_budget,
            top_k=cfg.top_k,
            seed=cfg.seed,
            n_impact_samples=cfg.n_impact_samples,
            n_stability_samples=cfg.n_stability_samples,
            score_mode="robust_combined",
            prior_mode="decrease_on_contradiction",
            extraction_method="adaptive",
            use_robust_stopping=True,
            exploration=ExplorationConfig(
                epsilon=0.2, scheduled_probe_every=3, n_sentinel_probes=2,
                enable_challenger=True, enable_coverage=True, enable_scheduled=True,
            ),
            initial_window=max(cfg.initial_window or (cfg.top_k * 2), cfg.top_k + 3),
        )
        policy_name = "quality_gated_distrust"
        # fall through into main loop

    # Plain baseline path: reuse existing adaptive engine.
    if cfg.plain_baseline or (
        cfg.score_mode == "uncertainty_x_topk_impact" and policy_name == "plain_uht"
    ):
        from consistency_ranker.adaptive_acquisition.adaptive_stopping import StoppingPolicy
        from consistency_ranker.adaptive_acquisition.engine import run_acquisition

        pol = make_policy("uncertainty_x_topk_impact")
        res = run_acquisition(
            state, pol, profiles, judge,
            engine_cfg=EngineConfig(n_impact_samples=cfg.n_impact_samples, seed=cfg.seed),
            stopping=StoppingPolicy(criteria=("budget",)),
            true_ranking=true_ranking,
        )
        # Build a minimal robustness report post-hoc.
        stab = compute_evidence_stability(
            res.state, n_samples=cfg.n_stability_samples, seed=cfg.seed
        )
        q = estimate_prior_quality(res.state, alt_priors=alt_priors)
        lam = AdaptivePriorState(lambda_q=1.0, mode="fixed", q_hat=q.q_hat)
        explor = ExplorationState()
        pool = init_challenger_pool(res.state, initial_window=cfg.initial_window)
        report = _build_report(
            res.state, stab, q, lam, explor, pool,
            stopping_reason=res.stopping_reason, bias_suspected=[],
        )
        return RobustAcquisitionResult(
            state=res.state, trace=res.trace, stopping_reason=res.stopping_reason,
            n_calls=res.n_calls, n_strong_calls=res.n_strong_calls,
            total_cost=res.total_cost, action_counts=res.action_counts,
            lambda_state=lam, explor=explor, pool=pool, report=report,
        )

    lam = AdaptivePriorState(mode=cfg.prior_mode, lambda_q=0.5)
    explor = ExplorationState()
    pool = init_challenger_pool(state, initial_window=cfg.initial_window)
    trace = AnytimeTrace(query_id=state.query_id, policy=policy_name)
    trace.record(
        state, step=0, n_calls=0, cost=0.0, strong_calls=0,
        last_action_type=None, true_ranking=true_ranking,
    )

    n_calls = n_strong = 0
    total_cost = 0.0
    action_counts: dict[str, int] = {}
    stopping_reason = "continue"
    last_stab = compute_evidence_stability(
        state, n_samples=cfg.n_stability_samples, seed=cfg.seed
    )
    last_bias = diagnose_bias(state)

    step = 0
    while step < cfg.budget * 2 and state.remaining_budget > 0:
        q_est = estimate_prior_quality(state, alt_priors=alt_priors)
        if true_prior_quality is not None and cfg.score_mode == "oracle_prior_quality":
            q_est.q_hat = float(true_prior_quality)
        lam = update_lambda(lam, q_est, step=step)

        last_stab = compute_evidence_stability(
            state, n_samples=cfg.n_stability_samples, seed=cfg.seed + step
        )
        last_bias = diagnose_bias(state)
        eff = effective_judge_count(state.evidence)

        pool = expand_window(pool, state, q_est, step=step)
        pool = promote_strong_outsiders(pool, state, step=step)
        chal_pids = challenger_pairs(state, pool)
        chal_cov_ok = all(
            explor.challenger_done.get(d, 0) >= cfg.exploration.min_challenger_per_insider
            for d in state.ranking[: state.top_k]
        ) if state.evidence else False

        if cfg.use_robust_stopping:
            stop = evaluate_robust_stop(
                state,
                stability=last_stab,
                explor_cfg=cfg.exploration,
                explor=explor,
                cfg=cfg.stop_cfg,
                challenger_coverage_ok=chal_cov_ok,
                n_effective_judges=float(eff["n_effective"]),
                hc_contradiction=q_est.high_conf_contradiction_rate,
            )
            if stop.stop:
                stopping_reason = stop.reason
                break
        elif state.remaining_budget <= 0:
            stopping_reason = "budget_exhausted"
            break

        eligible = generate_eligible_actions(state, profiles, include_no_action=True)
        # Restrict NEW_PAIR actions to active window when prior is trusted;
        # when prior is bad, allow challenger pairs (already in eligible).
        ctx = ImpactContext.build(
            state, n_samples=cfg.n_impact_samples, seed=cfg.seed + step
        )

        # Forced exploration / counter-bias first.
        # Scale exploration with prior quality: more when Q is low.
        explor_cfg = cfg.exploration
        if lam.q_hat >= 0.65:
            # Good prior: light exploration only (scheduled/sentinel off after first).
            explor_cfg = ExplorationConfig(
                epsilon=min(0.05, explor_cfg.epsilon),
                scheduled_probe_every=max(8, explor_cfg.scheduled_probe_every),
                min_topk_coverage=explor_cfg.min_topk_coverage,
                min_challenger_per_insider=0 if explor.probes_done >= 1 else 1,
                n_sentinel_probes=min(1, explor_cfg.n_sentinel_probes),
                enable_epsilon=explor_cfg.enable_epsilon,
                enable_scheduled=explor_cfg.enable_scheduled,
                enable_coverage=explor_cfg.enable_coverage,
                enable_challenger=lam.q_hat < 0.55,
                enable_sentinel=explor_cfg.enable_sentinel and explor.sentinel_done < 1,
            )
        elif lam.q_hat < 0.4:
            explor_cfg = ExplorationConfig(
                epsilon=max(0.2, explor_cfg.epsilon),
                scheduled_probe_every=max(2, explor_cfg.scheduled_probe_every // 2 or 2),
                min_topk_coverage=explor_cfg.min_topk_coverage,
                min_challenger_per_insider=max(1, explor_cfg.min_challenger_per_insider),
                n_sentinel_probes=explor_cfg.n_sentinel_probes,
                enable_epsilon=True,
                enable_scheduled=True,
                enable_coverage=True,
                enable_challenger=True,
                enable_sentinel=True,
            )

        explor_action, explor_reason = select_exploration_action(
            state, eligible, step=step, cfg=explor_cfg, explor=explor,
            rng=rng, challenger_pairs=chal_pids,
        )
        # Counter-bias only after enough evidence and when Q is not high.
        bias_suggestions = []
        if len(state.evidence) >= 6 and lam.q_hat < 0.6 and last_bias.suspected:
            bias_suggestions = suggest_counter_bias_actions(
                state, last_bias, eligible, profiles
            )

        chosen = None
        chosen_reason = None
        if explor_action is not None and (
            explor_reason != "epsilon"
            or cfg.score_mode.endswith("epsilon")
            or cfg.exploration.enable_epsilon
        ):
            # Prefer mandatory probes; epsilon only if mode wants it or default on.
            if explor_reason != "epsilon" or cfg.score_mode in (
                "uncertainty_x_topk_impact_epsilon",
                "robust_combined",
            ):
                chosen = explor_action
                chosen_reason = explor_reason

        if chosen is None and bias_suggestions:
            chosen, chosen_reason = bias_suggestions[0]

        if chosen is None:
            # Score all actionable.
            actionable = [a for a in eligible if a.action_type != "NO_ACTION"]
            chal_set = set(chal_pids)
            scored = []
            for a in actionable:
                # When prior is good and window is active, prefer pairs inside window.
                if (
                    lam.lambda_q >= 0.55
                    and a.action_type == "NEW_PAIR"
                    and a.doc_i not in pool.active
                    and a.doc_j not in pool.active
                ):
                    continue
                val, bd = score_action(
                    state, a, ctx, stability=last_stab, cfg=score_cfg,
                    is_challenger=a.pair_id in chal_set,
                    bias_value=1.0 if last_bias.suspected else 0.0,
                    prior_quality=lam.q_hat,
                )
                a.score = val
                a.score_breakdown = bd
                if chosen_reason:
                    a.reason = (a.reason + f"|{chosen_reason}").strip("|")
                scored.append(a)
            if not scored:
                scored = [a for a in actionable]
                for a in scored:
                    a.score = 0.0
            scored.sort(key=lambda a: (-a.score, a.pair_id, a.action_type))
            if not scored:
                stopping_reason = "no_eligible_actions"
                break
            chosen = scored[0]
            chosen_reason = chosen_reason or "scored"

        # Execute.
        rec = judge.judge(chosen)
        if rec is None:
            # Skip unavailable.
            step += 1
            continue
        state.add_evidence([rec])
        state.remaining_budget -= 1
        n_calls += 1
        total_cost += float(chosen.est_cost)
        action_counts[chosen.action_type] = action_counts.get(chosen.action_type, 0) + 1
        if chosen.action_type == "STRONG_MODEL_ADJUDICATION" or (
            chosen.provider or ""
        ) == "strong":
            n_strong += 1
        state.record_action(
            {
                "step": step,
                **chosen.to_dict(),
                "exploration_reason": chosen_reason,
                "lambda_q": lam.lambda_q,
                "q_hat": lam.q_hat,
                "outcome_z": rec.z,
            }
        )

        # Re-extract with adaptive prior and publish as the active ranking.
        # High λ → prior_priority (efficient when prior is good);
        # low λ → mixed / evidence_only.
        try:
            if cfg.extraction_method == "adaptive":
                if lam.lambda_q >= 0.6:
                    method = "prior_priority"
                elif lam.lambda_q <= 0.3:
                    method = "evidence_only"
                else:
                    method = "mixed_priority"
            else:
                method = cfg.extraction_method
            new_ranking = extract_ranking(
                state,
                method=method,  # type: ignore[arg-type]
                lambda_q=lam.lambda_q,
                alt_priors=alt_priors,
                seed=cfg.seed + step,
            )
            state.set_ranking_override(new_ranking)
            state.history[-1]["extracted_ranking"] = new_ranking
            state.history[-1]["extraction_method"] = method
        except Exception:
            pass

        step += 1
        trace.record(
            state, step=step, n_calls=n_calls, cost=total_cost, strong_calls=n_strong,
            last_action_type=chosen.action_type, true_ranking=true_ranking,
        )

    if stopping_reason == "continue":
        stopping_reason = "budget_exhausted" if state.remaining_budget <= 0 else "max_steps"

    q_final = estimate_prior_quality(state, alt_priors=alt_priors)
    stab_final = compute_evidence_stability(
        state, n_samples=cfg.n_stability_samples, seed=cfg.seed
    )
    report = _build_report(
        state, stab_final, q_final, lam, explor, pool,
        stopping_reason=stopping_reason, bias_suspected=last_bias.suspected,
    )

    failure_trace = {
        "initial_prior_ranking": sorted(
            state.prior_scores, key=lambda d: (-state.prior_scores[d], d)
        ),
        "true_ranking": true_ranking,
        "final_ranking": state.ranking,
        "lambda_trajectory": list(lam.history),
        "exploration_log": list(explor.log),
        "promotions": list(pool.promotions),
        "stopping_reason": stopping_reason,
        "category": report.category,
        "g_prior": stab_final.g_prior,
        "s_evidence": stab_final.s_evidence,
        "s_total": stab_final.s_total,
    }

    return RobustAcquisitionResult(
        state=state,
        trace=trace,
        stopping_reason=stopping_reason,
        n_calls=n_calls,
        n_strong_calls=n_strong,
        total_cost=total_cost,
        action_counts=action_counts,
        lambda_state=lam,
        explor=explor,
        pool=pool,
        report=report,
        failure_trace=failure_trace,
    )


def _build_report(
    state, stab, q_est, lam, explor, pool, *, stopping_reason, bias_suspected
) -> RobustnessReport:
    providers = {e.provider for e in state.evidence if e.provider}
    prompts = {e.prompt_version for e in state.evidence if e.prompt_version}
    orient_agree = []
    for agg in state.aggregates.values():
        orient_agree.append(float(agg.features.get("orientation_agreement", 1.0)))
    view = state.view()
    pert = prior_perturbation_sensitivity(state, n=6, seed=state.seed)
    chal_ok = all(
        explor.challenger_done.get(d, 0) >= 1 for d in state.ranking[: state.top_k]
    ) if explor.challenger_done else False
    from consistency_ranker.prior_robust.exploration_guards import (
        ExplorationConfig,
        exploration_complete,
    )

    explor_ok = exploration_complete(state, ExplorationConfig(), explor)
    cat = categorize(
        stopping_reason=stopping_reason,
        g_prior=stab.g_prior,
        s_evidence=stab.s_evidence,
        exploration_ok=explor_ok,
        bias_suspected=bias_suspected,
        ambiguity_bucket=(view.ambiguity or {}).get("ambiguity_bucket"),
        judge_disagreement=1.0 - (sum(orient_agree) / len(orient_agree) if orient_agree else 1.0),
    )
    return RobustnessReport(
        query_id=state.query_id,
        category=cat,
        topk=list(state.ranking[: state.top_k]),
        topk_membership=dict(stab.topk_membership_evidence),
        evidence_only_stability=stab.s_evidence,
        prior_dependence_gap=stab.g_prior,
        prior_credibility=q_est.q_hat,
        lambda_q=lam.lambda_q,
        n_exploration_probes=len(explor.log),
        challenger_coverage_ok=chal_ok,
        provider_diversity=len(providers),
        prompt_diversity=len(prompts),
        orientation_consistency=(
            sum(orient_agree) / len(orient_agree) if orient_agree else 1.0
        ),
        max_scc_size=view.max_scc_size,
        ambiguity_bucket=(view.ambiguity or {}).get("ambiguity_bucket"),
        perturbation_topk_jaccard=pert.get("mean_topk_jaccard"),
        unresolved_consequential=len(view.unresolved_pairs),
        stopping_reason=stopping_reason,
        notes=[f"window={pool.window}", f"promotions={len(pool.promotions)}"],
    )


def make_initial_robust_state(
    *,
    query_id: str,
    candidate_ids: list[str],
    prior_scores: dict[str, float],
    budget: int,
    top_k: int = 3,
    seed: int = 0,
) -> AcquisitionState:
    return initial_state(
        query_id=query_id,
        candidate_ids=candidate_ids,
        prior_scores=prior_scores,
        budget=budget,
        top_k=top_k,
        seed=seed,
    )


__all__ = [
    "RobustEngineConfig",
    "RobustAcquisitionResult",
    "run_robust_acquisition",
    "make_initial_robust_state",
]
