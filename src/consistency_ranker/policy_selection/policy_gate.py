"""Query-level policy selector: hard, selective, soft, cost-sensitive, contextual.

All learned routing in this module is **experimental**. The default execution
mode is :attr:`ExecutionMode.PRODUCTION_UHT`, under which :func:`select_policy`
always returns UHT regardless of features, models, or gate mode. See
``production_config`` for the frozen operating point and ``execution_mode`` for
the mode semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from consistency_ranker.policy_selection.execution_mode import (
    ExecutionMode,
    resolve_execution_mode,
)
from consistency_ranker.policy_selection.gate_features import (
    FEATURE_SCHEMA_VERSION,
    FeatureBundle,
    feature_names_for_stage,
    features_to_vector,
)
from consistency_ranker.policy_selection.policy_calibration import (
    CalibratedModel,
    predict_multinomial,
    predict_proba,
)
from consistency_ranker.policy_selection.policy_mixture import (
    clipped_credibility,
    staged_plan,
)
from consistency_ranker.policy_selection.policy_regret import (
    predict_policy_regret,
    uht_allowed_by_risk,
)
from consistency_ranker.policy_selection.policy_utility import UtilityWeights
from consistency_ranker.policy_selection.production_config import (
    PRODUCTION_OPERATING_POINT,
    PRODUCTION_PRIMARY_POLICY,
)
from consistency_ranker.policy_selection.risk_control import (
    RiskControlConfig,
    acceptable_policy_set,
)
from consistency_ranker.policy_selection.safe_fallback import (
    FallbackConfig,
    apply_experimental_escalation,
)

PolicyName = Literal[
    "UHT",
    "UHT_EXPLORE",
    "CHALLENGER",
    "ROBUST_COMBINED",
    "BROAD_STATIC",
    "NO_PRIOR",
    "HYBRID",
    "STOP_OR_FALLBACK",
]

GateMode = Literal[
    "always_uht",
    "always_challenger",
    "always_robust",
    "broad_static",
    "hard_qhat",
    "calibrated_hard",
    "selective_three_way",
    "soft_mixture",
    "budget_split",
    "staged",
    "cost_sensitive_regret",
    "contextual",
    "conservative_fallback",
    "random",
    "majority_best",
    "oracle",
]

TrustLabel = Literal["TRUST_PRIOR", "DISTRUST_PRIOR", "UNCERTAIN"]

#: Every gate mode except ``always_uht`` performs learned or heuristic routing
#: and therefore requires ``ExecutionMode.EXPERIMENTAL_GATE`` (or diagnostic
#: mode, where its output is recorded but not executed).
GATE_MODE_CHOICES: tuple[str, ...] = (
    "always_uht",
    "always_challenger",
    "always_robust",
    "broad_static",
    "hard_qhat",
    "calibrated_hard",
    "selective_three_way",
    "soft_mixture",
    "budget_split",
    "staged",
    "cost_sensitive_regret",
    "contextual",
    "conservative_fallback",
    "random",
    "majority_best",
    "oracle",
)
PRODUCTION_GATE_MODE: GateMode = "always_uht"


def resolve_gate_mode(value: str | None) -> GateMode:
    """Validate a gate-mode string, failing closed to the production mode.

    ``None`` resolves to ``always_uht``. Unknown values raise ``ValueError``
    and are never mapped onto a learned mode.
    """
    if value is None:
        return PRODUCTION_GATE_MODE
    if not isinstance(value, str):
        raise TypeError(f"Gate mode must be a string or None; got {type(value).__name__}.")
    key = value.strip().lower()
    if key not in GATE_MODE_CHOICES:
        raise ValueError(
            f"Unknown gate mode {value!r}. Valid modes: {', '.join(GATE_MODE_CHOICES)}."
        )
    return key  # type: ignore[return-value]

ALL_POLICIES: tuple[PolicyName, ...] = (
    "UHT",
    "UHT_EXPLORE",
    "CHALLENGER",
    "ROBUST_COMBINED",
    "BROAD_STATIC",
    "NO_PRIOR",
    "HYBRID",
    "STOP_OR_FALLBACK",
)


@dataclass
class GateDecision:
    """Outcome of policy selection.

    ``policy`` / ``executed_policy`` is what actually runs. ``diagnostic_recommendation``
    is what a learned gate *would* have chosen and is observational only.
    ``experimental_policy`` is populated only when experimental routing is
    authorised, in which case it equals ``executed_policy``.
    """

    mode: GateMode
    policy: PolicyName
    trust_label: TrustLabel
    g_q: float
    policy_probs: dict[str, float]
    abstained: bool
    reason: str
    mixture: dict[str, Any] = field(default_factory=dict)
    regret: dict[str, Any] = field(default_factory=dict)
    risk_control: dict[str, Any] = field(default_factory=dict)
    feature_schema: str = FEATURE_SCHEMA_VERSION
    execution_mode: ExecutionMode = ExecutionMode.PRODUCTION_UHT
    diagnostic_recommendation: PolicyName | None = None
    experimental_policy: PolicyName | None = None

    @property
    def executed_policy(self) -> PolicyName:
        """The policy that will actually be executed."""
        return self.policy

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "policy": self.policy,
            "executed_policy": self.policy,
            "execution_mode": self.execution_mode.value,
            "diagnostic_recommendation": self.diagnostic_recommendation,
            "experimental_policy": self.experimental_policy,
            "trust_label": self.trust_label,
            "g_q": self.g_q,
            "policy_probs": dict(self.policy_probs),
            "abstained": self.abstained,
            "reason": self.reason,
            "mixture": dict(self.mixture),
            "regret": dict(self.regret),
            "risk_control": dict(self.risk_control),
            "feature_schema": self.feature_schema,
        }


@dataclass
class PolicySelector:
    """Policy-selection configuration.

    Defaults are the production operating point: ``execution_mode`` is
    ``PRODUCTION_UHT`` and ``mode`` is ``always_uht``. A learned gate mode or an
    attached calibration model is rejected in production mode, so no omitted
    argument, missing artifact, or malformed config can enable learned routing.
    """

    mode: GateMode = PRODUCTION_GATE_MODE
    binary_model: CalibratedModel | None = None
    multinomial_model: CalibratedModel | None = None
    regret_models: dict[str, CalibratedModel] = field(default_factory=dict)
    weights: UtilityWeights = field(default_factory=UtilityWeights)
    tau_policy: float = 0.55  # selective commit threshold
    qhat_threshold: float = 0.55
    risk_delta: float = 0.12
    safety_floor: float = PRODUCTION_OPERATING_POINT.safety_floor
    majority_best_policy: PolicyName = "UHT"
    fallback_cfg: FallbackConfig = field(default_factory=FallbackConfig)
    risk_cfg: RiskControlConfig = field(default_factory=RiskControlConfig)
    uht_risk_threshold: float = 0.55
    ood_score: float | None = None  # if set and high → conservative
    execution_mode: ExecutionMode = ExecutionMode.PRODUCTION_UHT

    def __post_init__(self) -> None:
        # Reject unknown modes rather than treating them as experimental.
        self.execution_mode = resolve_execution_mode(self.execution_mode)
        self.mode = resolve_gate_mode(self.mode)
        if self.execution_mode is ExecutionMode.PRODUCTION_UHT:
            if self.mode != PRODUCTION_GATE_MODE:
                raise ValueError(
                    f"Gate mode {self.mode!r} performs learned/heuristic routing and is not "
                    f"allowed in {ExecutionMode.PRODUCTION_UHT.value!r}. Pass "
                    "execution_mode=ExecutionMode.EXPERIMENTAL_GATE to opt in explicitly, "
                    "or ExecutionMode.DIAGNOSTIC to record it without routing."
                )
            if (
                self.binary_model is not None
                or self.multinomial_model is not None
                or self.regret_models
            ):
                raise ValueError(
                    "Calibration models cannot be attached in "
                    f"{ExecutionMode.PRODUCTION_UHT.value!r}: production never consults a "
                    "learned gate. Use ExecutionMode.DIAGNOSTIC to record their predictions."
                )

    @property
    def allows_learned_routing(self) -> bool:
        return self.execution_mode.allows_learned_routing


def _probs_from_binary(p_uht: float) -> dict[str, float]:
    # Spread remaining mass over robust alternatives.
    rem = 1.0 - p_uht
    return {
        "UHT": p_uht * 0.85,
        "UHT_EXPLORE": p_uht * 0.15,
        "CHALLENGER": rem * 0.45,
        "ROBUST_COMBINED": rem * 0.30,
        "HYBRID": rem * 0.15,
        "BROAD_STATIC": rem * 0.05,
        "NO_PRIOR": rem * 0.03,
        "STOP_OR_FALLBACK": rem * 0.02,
    }


def _normalize(d: dict[str, float]) -> dict[str, float]:
    z = sum(d.values()) or 1.0
    return {k: float(v / z) for k, v in d.items()}


def _production_policy() -> PolicyName:
    """The locked production policy, validated against the frozen config."""
    policy = PRODUCTION_PRIMARY_POLICY
    if policy not in ALL_POLICIES:  # pragma: no cover - defensive
        raise ValueError(f"Production policy {policy!r} is not a known policy name.")
    return "UHT"


def _experimental_recommendation(
    features: FeatureBundle,
    *,
    sel: PolicySelector,
    q_hat_heuristic: float | None = None,
    oracle_best: PolicyName | None = None,
    rng_u: float = 0.0,
) -> GateDecision:
    """Compute the learned/heuristic gate recommendation.

    This is *not* the production route. Callers must decide whether the result
    is executed (experimental mode) or merely recorded (diagnostic mode);
    :func:`select_policy` enforces that distinction.
    """
    # For pre-only, still build vector with zeros for missing probe feats.
    x = features_to_vector(features, stage="probe" if features.stage == "pre" else features.stage)
    # Pad/truncate to expected length
    expect = feature_names_for_stage("probe")
    if len(x) < len(expect):
        x = x + [0.0] * (len(expect) - len(x))
    x = x[: len(expect)]

    # Credibility estimate.
    if sel.binary_model is not None:
        g_q = predict_proba(sel.binary_model, x)
    elif q_hat_heuristic is not None:
        g_q = float(q_hat_heuristic)
    else:
        g_q = float(features.values.get("weighted_agreement", features.values.get("topk_boundary_separation", 0.5)))

    # OOD → degrade confidence toward 0.5 and prefer conservative.
    if sel.ood_score is not None and sel.ood_score > 0.6:
        g_q = 0.5 * g_q + 0.5 * 0.5

    policy_probs: dict[str, float]
    if sel.multinomial_model is not None and sel.multinomial_model.classes:
        policy_probs = predict_multinomial(sel.multinomial_model, x)
    else:
        policy_probs = _normalize(_probs_from_binary(g_q))

    mode = sel.mode
    abstained = False
    trust: TrustLabel = "UNCERTAIN"
    reason: str = str(mode)
    mixture: dict[str, Any] = {}
    regret_info: dict[str, Any] = {}
    risk_info: dict[str, Any] = {}
    policy: PolicyName = "HYBRID"

    if mode == "always_uht":
        policy, trust, reason = "UHT", "TRUST_PRIOR", "always_uht"
    elif mode == "always_challenger":
        policy, trust, reason = "CHALLENGER", "DISTRUST_PRIOR", "always_challenger"
    elif mode == "always_robust":
        policy, trust, reason = "ROBUST_COMBINED", "DISTRUST_PRIOR", "always_robust"
    elif mode == "broad_static":
        policy, trust, reason = "BROAD_STATIC", "DISTRUST_PRIOR", "broad_static"
    elif mode == "random":
        # Deterministic from rng_u
        keys = list(ALL_POLICIES)
        policy = keys[int(rng_u * len(keys)) % len(keys)]
        trust = "UNCERTAIN"
        reason = "random"
    elif mode == "majority_best":
        policy = sel.majority_best_policy
        trust = "TRUST_PRIOR" if policy == "UHT" else "DISTRUST_PRIOR"
        reason = "majority_best_global"
    elif mode == "oracle":
        policy = oracle_best or "UHT"
        trust = "TRUST_PRIOR" if policy == "UHT" else "DISTRUST_PRIOR"
        reason = "oracle"
    elif mode == "hard_qhat":
        if g_q >= sel.qhat_threshold:
            policy, trust, reason = "UHT", "TRUST_PRIOR", "hard_qhat_trust"
        else:
            policy, trust, reason = "CHALLENGER", "DISTRUST_PRIOR", "hard_qhat_distrust"
    elif mode == "calibrated_hard":
        if g_q >= sel.qhat_threshold:
            policy, trust, reason = "UHT", "TRUST_PRIOR", "calibrated_hard_trust"
        else:
            policy, trust, reason = "CHALLENGER", "DISTRUST_PRIOR", "calibrated_hard_distrust"
    elif mode == "selective_three_way":
        max_p = max(policy_probs.values()) if policy_probs else 0.0
        best = max(policy_probs, key=lambda k: policy_probs[k]) if policy_probs else "HYBRID"
        if max_p < sel.tau_policy:
            abstained = True
            trust = "UNCERTAIN"
            # Extra probes / hybrid / conservative
            if features.values.get("n_probe_acquired", 0) < 3 / 16:
                policy, reason = "STOP_OR_FALLBACK", "uncertain_need_more_probes"
            else:
                policy, reason = "HYBRID", "uncertain_hybrid"
        else:
            policy = best if best in ALL_POLICIES else "HYBRID"  # type: ignore[assignment]
            trust = "TRUST_PRIOR" if policy in ("UHT", "UHT_EXPLORE") else "DISTRUST_PRIOR"
            reason = f"selective_commit_{policy}"
    elif mode == "soft_mixture":
        policy, trust, reason = "HYBRID", "UNCERTAIN", "soft_score_mixture"
        mixture = {
            "mode": "score_mixture",
            "g_eff": clipped_credibility(g_q, sel.safety_floor),
            "safety_floor": sel.safety_floor,
        }
    elif mode == "budget_split":
        policy, trust, reason = "HYBRID", "UNCERTAIN", "budget_split"
        from consistency_ranker.policy_selection.policy_mixture import split_budget

        mixture = {
            "mode": "budget_split",
            **split_budget(20, g_q, safety_floor=sel.safety_floor),
        }
    elif mode == "staged":
        plan = staged_plan(
            g_q,
            contradiction_rate=float(features.values.get("reliable_contradiction_rate", 0.0)),
            buried_signal=float(features.values.get("n_outsiders_defeating_insiders", 0.0)),
            safety_floor=sel.safety_floor,
        )
        policy = plan["primary"]  # type: ignore[assignment]
        trust = "TRUST_PRIOR" if policy == "UHT" else (
            "DISTRUST_PRIOR" if policy in ("CHALLENGER", "ROBUST_COMBINED") else "UNCERTAIN"
        )
        reason = f"staged_{plan['reason']}"
        mixture = plan
    elif mode == "cost_sensitive_regret":
        if sel.regret_models:
            pred = predict_policy_regret(
                sel.regret_models, x, pair="UHT_vs_CHALLENGER", risk_delta=sel.risk_delta
            )
            regret_info = pred.to_dict()
            if uht_allowed_by_risk(pred, delta_tol=sel.risk_delta):
                policy, trust, reason = "UHT", "TRUST_PRIOR", "regret_uht_safe"
            else:
                policy, trust, reason = "CHALLENGER", "DISTRUST_PRIOR", "regret_uht_risky"
        else:
            # Fall back to asymmetric threshold: require higher g_q to trust.
            thr = sel.qhat_threshold + 0.1 * (sel.weights.false_trust / max(sel.weights.false_distrust, 1e-6) - 1)
            thr = float(max(0.4, min(0.85, thr)))
            if g_q >= thr:
                policy, trust, reason = "UHT", "TRUST_PRIOR", "cost_sensitive_trust"
            else:
                policy, trust, reason = "CHALLENGER", "DISTRUST_PRIOR", "cost_sensitive_distrust"
    elif mode == "contextual":
        # Contextual: argmax expected utility under multinomial probs.
        # Proxy utilities from credibility.
        util = {
            "UHT": g_q - sel.weights.lambda_c * 18,
            "UHT_EXPLORE": 0.9 * g_q - sel.weights.lambda_c * 20,
            "CHALLENGER": (1 - g_q) * 0.9 - sel.weights.lambda_c * 22,
            "ROBUST_COMBINED": (1 - g_q) * 0.85 - sel.weights.lambda_c * 22,
            "HYBRID": 0.5 - sel.weights.lambda_c * 21,
            "BROAD_STATIC": 0.35 - sel.weights.lambda_c * 24,
            "NO_PRIOR": 0.3 - sel.weights.lambda_c * 24,
            "STOP_OR_FALLBACK": 0.2,
        }
        # Softmax blend with policy_probs
        scored = {p: 0.6 * util.get(p, 0.0) + 0.4 * policy_probs.get(p, 0.0) for p in ALL_POLICIES}
        policy = max(scored, key=lambda k: scored[k])
        trust = "TRUST_PRIOR" if policy in ("UHT", "UHT_EXPLORE") else "DISTRUST_PRIOR"
        reason = "contextual_argmax"
        mixture = {"util": util, "scored": scored}
    else:  # conservative_fallback
        # Prefer CHALLENGER / HYBRID with safety floor unless very confident.
        if g_q >= 0.75:
            policy, trust, reason = "UHT_EXPLORE", "TRUST_PRIOR", "conservative_high_q"
        else:
            policy, trust, reason = "HYBRID", "UNCERTAIN", "conservative_default"
        mixture = {"safety_floor": sel.safety_floor, "g_eff": clipped_credibility(g_q, sel.safety_floor)}

    # Risk-control set (empirical).
    pol_scores: dict[str, float] = {p: policy_probs.get(p, 0.0) for p in ALL_POLICIES}
    pol_regrets = {
        "UHT": max(0.0, 0.55 - g_q),
        "CHALLENGER": max(0.0, g_q - 0.45) * 0.3,
        "HYBRID": 0.05,
        "ROBUST_COMBINED": max(0.0, g_q - 0.5) * 0.25,
    }
    rc = acceptable_policy_set(
        policy_scores=pol_scores,
        policy_regrets=pol_regrets,
        cfg=sel.risk_cfg,
        uht_threshold=sel.uht_risk_threshold,
    )
    risk_info = rc.to_dict()
    if mode not in ("oracle", "always_uht", "random", "majority_best") and policy == "UHT" and not rc.uht_allowed:
        policy = rc.allowed_policies[0] if rc.allowed_policies else "CHALLENGER"  # type: ignore[assignment]
        reason = reason + "|risk_control_override"
        trust = "DISTRUST_PRIOR"

    # Experimental escalation: may rewrite the policy name (routing, not safety).
    active = []
    if mode == "conservative_fallback" or (
        float(features.values.get("n_outsiders_defeating_insiders", 0)) > 0.5
    ):
        active = ["mandatory_outsider_probe"]
    policy = apply_experimental_escalation(policy, active, q_hat=g_q)  # type: ignore[assignment]

    return GateDecision(
        mode=mode,
        policy=policy,
        trust_label=trust,
        g_q=float(g_q),
        policy_probs=_normalize(policy_probs),
        abstained=abstained,
        reason=reason,
        mixture=mixture,
        regret=regret_info,
        risk_control=risk_info,
        execution_mode=sel.execution_mode,
    )


def select_policy(
    features: FeatureBundle,
    *,
    selector: PolicySelector | None = None,
    q_hat_heuristic: float | None = None,
    oracle_best: PolicyName | None = None,
    rng_u: float = 0.0,
) -> GateDecision:
    """Select the acquisition policy to execute, from observable features only.

    * ``PRODUCTION_UHT`` (default): returns UHT unconditionally. No model is
      consulted and no safeguard can rewrite the route.
    * ``DIAGNOSTIC``: returns UHT, but records what the configured gate would
      have chosen in ``diagnostic_recommendation``.
    * ``EXPERIMENTAL_GATE``: executes the gate recommendation.
    """
    sel = selector if selector is not None else PolicySelector()
    mode = sel.execution_mode

    if mode is ExecutionMode.EXPERIMENTAL_GATE:
        decision = _experimental_recommendation(
            features,
            sel=sel,
            q_hat_heuristic=q_hat_heuristic,
            oracle_best=oracle_best,
            rng_u=rng_u,
        )
        decision.experimental_policy = decision.policy
        decision.diagnostic_recommendation = decision.policy
        return decision

    recommendation: GateDecision | None = None
    mixture: dict[str, Any] = {}
    if mode is ExecutionMode.DIAGNOSTIC:
        # Observational only: recorded, never executed. A failure to compute a
        # recommendation must not affect the production route.
        try:
            recommendation = _experimental_recommendation(
                features,
                sel=sel,
                q_hat_heuristic=q_hat_heuristic,
                oracle_best=oracle_best,
                rng_u=rng_u,
            )
        except Exception as exc:
            mixture["diagnostic_error"] = f"{type(exc).__name__}: {exc}"

    if recommendation is not None:
        g_q = recommendation.g_q
        probs = dict(recommendation.policy_probs)
    else:
        g_q = float(
            features.values.get(
                "weighted_agreement", features.values.get("topk_boundary_separation", 0.5)
            )
        )
        probs = {"UHT": 1.0}
    reason = f"{mode.value}:always_uht"
    if "diagnostic_error" in mixture:
        reason += "|diagnostic_error"

    return GateDecision(
        mode=sel.mode,
        policy=_production_policy(),
        trust_label="TRUST_PRIOR",
        g_q=float(g_q),
        policy_probs=probs,
        abstained=False,
        reason=reason,
        mixture=mixture,
        regret=dict(recommendation.regret) if recommendation is not None else {},
        risk_control=dict(recommendation.risk_control) if recommendation is not None else {},
        execution_mode=mode,
        diagnostic_recommendation=recommendation.policy if recommendation is not None else None,
        experimental_policy=None,
    )


# Re-export UtilityWeights for callers that import from policy_gate
__all__ = [
    "PolicyName",
    "GateMode",
    "GATE_MODE_CHOICES",
    "PRODUCTION_GATE_MODE",
    "resolve_gate_mode",
    "TrustLabel",
    "ALL_POLICIES",
    "ExecutionMode",
    "GateDecision",
    "PolicySelector",
    "UtilityWeights",
    "select_policy",
]
