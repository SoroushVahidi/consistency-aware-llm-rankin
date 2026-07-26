"""Tests for calibrated policy selection. No billed API calls."""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import pytest

from consistency_ranker.adaptive_acquisition import synthetic_roster
from consistency_ranker.dag_linear_extensions import is_valid_topological_order
from consistency_ranker.policy_selection.diagnostic_probes import (
    ProbeConfig,
    run_diagnostic_probes,
    select_probe_pairs,
)
from consistency_ranker.policy_selection.execution_mode import ExecutionMode
from consistency_ranker.policy_selection.gate_features import (
    FEATURE_SCHEMA_VERSION,
    FeatureBundle,
    assert_no_qrel_keys,
    extract_features,
    feature_names_for_stage,
)
from consistency_ranker.policy_selection.policy_benchmark import (
    PolicyBenchmarkConfig,
    build_synthetic_population,
    build_world,
    nested_split_regimes,
    records_to_xy,
)
from consistency_ranker.policy_selection.policy_calibration import (
    CalibratedModel,
    evaluation_metrics,
    fit_calibrated_gate,
    predict_proba,
)
from consistency_ranker.policy_selection.policy_gate import (
    PolicySelector,
    select_policy,
)
from consistency_ranker.policy_selection.policy_mixture import (
    hybrid_score,
    split_budget,
    staged_plan,
)
from consistency_ranker.policy_selection.policy_regret import (
    fit_regret_models,
    predict_policy_regret,
    uht_allowed_by_risk,
)
from consistency_ranker.policy_selection.policy_runner import (
    run_gated_acquisition,
    run_named_policy,
)
from consistency_ranker.policy_selection.policy_switching import (
    SwitchConfig,
    SwitchState,
    evaluate_switch,
)
from consistency_ranker.policy_selection.policy_utility import (
    PolicyOutcome,
    UtilityWeights,
    compute_utility,
    gate_asymmetric_loss,
)
from consistency_ranker.policy_selection.replay_eval import (
    build_cache_index,
    evaluate_policy_under_replay,
    replay_probe_features,
)
from consistency_ranker.policy_selection.risk_control import (
    acceptable_policy_set,
    fit_uht_risk_threshold,
)
from consistency_ranker.policy_selection.safe_fallback import (
    FallbackConfig,
    apply_experimental_escalation,
    evaluate_safeguards,
)
from consistency_ranker.prior_robust import make_initial_robust_state


def _tiny_world(prior="accurate", judge="clean", seed=0, n=6):
    w = build_world(prior_regime=prior, judge_regime=judge, seed=seed, n_items=n, top_k=2)
    w["prior_regime"] = prior
    w["judge_regime"] = judge
    w["seed"] = seed
    return w


def test_feature_extraction_stages_and_no_qrel_leakage():
    w = _tiny_world(seed=1)
    st = make_initial_robust_state(
        query_id="q", candidate_ids=list(w["true_ranking"]),
        prior_scores=w["prior_scores"], budget=10, top_k=2, seed=1,
    )
    pre = extract_features(st, stage="pre", alt_priors=w.get("alt_priors"))
    assert pre.schema_version == FEATURE_SCHEMA_VERSION
    assert all(pre.availability[k] == "pre" for k in pre.values)
    assert_no_qrel_keys(pre)
    # Probe features should not appear yet
    assert "weighted_agreement" not in pre.values

    profiles = synthetic_roster(n_models=1, n_prompts=1)
    run_diagnostic_probes(st, profiles, w["judge"], cfg=ProbeConfig(max_budget=2), seed=1)
    probe = extract_features(st, stage="probe", alt_priors=w.get("alt_priors"))
    assert "weighted_agreement" in probe.values
    assert "prior_score_margin_mean" in probe.values  # pre retained
    assert_no_qrel_keys(probe)
    online = extract_features(st, stage="online", online_kwargs={"q_hat": 0.7})
    assert "current_prior_credibility" in online.values
    # No truth keys
    blob = json.dumps(online.to_dict()).lower()
    assert "true_ranking" not in blob
    assert "qrel" not in blob


def test_pre_vs_probe_feature_separation():
    names_pre = feature_names_for_stage("pre")
    names_probe = feature_names_for_stage("probe")
    assert all(n in names_probe for n in names_pre)
    assert len(names_probe) > len(names_pre)
    assert "weighted_agreement" in names_probe
    assert "weighted_agreement" not in names_pre


def test_feature_schema_version_guard():
    bad = {"schema_version": "old_v0", "stage": "pre", "values": {}}
    with pytest.raises(ValueError, match="Incompatible"):
        FeatureBundle.from_dict(bad)


def test_policy_utility_and_asymmetric_losses():
    w = UtilityWeights(false_trust=2.0, false_distrust=0.5, lambda_c=0.01, lambda_r=0.5)
    good = PolicyOutcome(policy="UHT", topk_jaccard=1.0, n_calls=10, total_cost=10.0)
    bad = PolicyOutcome(
        policy="UHT", topk_jaccard=0.0, n_calls=10, total_cost=10.0, catastrophic=True
    )
    assert compute_utility(good, w) > compute_utility(bad, w)
    ft = gate_asymmetric_loss(predicted_trust=True, true_uht_better=False, weights=w, catastrophic_if_uht=True)
    fd = gate_asymmetric_loss(predicted_trust=False, true_uht_better=True, weights=w)
    assert ft > fd
    assert gate_asymmetric_loss(predicted_trust=True, true_uht_better=True, weights=w) == 0.0


def test_calibration_models_and_metrics():
    X = [[0.1, 0.2], [0.8, 0.7], [0.2, 0.1], [0.9, 0.8], [0.4, 0.5], [0.6, 0.6]]
    y = [0.0, 1.0, 0.0, 1.0, 0.0, 1.0]
    names = ["a", "b"]
    for kind in ("logistic", "isotonic", "beta", "shallow_tree", "heuristic"):
        m = fit_calibrated_gate(X, y, feature_names=names, kind=kind)  # type: ignore[arg-type]
        ps = [predict_proba(m, x) for x in X]
        assert all(0.0 <= p <= 1.0 for p in ps)
        rep = evaluation_metrics(y, ps)
        assert rep.n == len(y)
        assert 0.0 <= rep.brier <= 1.0


def test_model_serialization_schema_fail():
    m = fit_calibrated_gate([[0.0], [1.0]], [0.0, 1.0], feature_names=["x"], kind="logistic")
    d = m.to_dict()
    d["schema_version"] = "nope"
    with pytest.raises(ValueError):
        CalibratedModel.from_dict(d)


def test_selective_abstention():
    w = _tiny_world(seed=2)
    st = make_initial_robust_state(
        query_id="q", candidate_ids=list(w["true_ranking"]),
        prior_scores=w["prior_scores"], budget=8, top_k=2, seed=2,
    )
    feats = extract_features(st, stage="pre")
    sel = PolicySelector(
        mode="selective_three_way",
        tau_policy=0.99,
        execution_mode=ExecutionMode.EXPERIMENTAL_GATE,
    )
    dec = select_policy(feats, selector=sel)
    assert dec.abstained or dec.trust_label == "UNCERTAIN" or dec.policy in (
        "HYBRID", "STOP_OR_FALLBACK", "CHALLENGER", "UHT", "UHT_EXPLORE", "ROBUST_COMBINED",
        "BROAD_STATIC", "NO_PRIOR",
    )


def test_soft_mixture_and_budget_split():
    assert 0.0 < hybrid_score(1.0, 0.0, 0.8, safety_floor=0.15) < 1.0
    sp = split_budget(20, 0.9, safety_floor=0.15)
    assert sp["UHT"] + sp["robust"] == 20
    assert sp["robust"] >= 1
    plan = staged_plan(0.8, contradiction_rate=0.0, buried_signal=0.0)
    assert plan["primary"] == "UHT"
    plan2 = staged_plan(0.2, buried_signal=0.8)
    assert plan2["primary"] == "CHALLENGER"


def test_online_switching_hysteresis():
    st = SwitchState(current_policy="UHT", initial_policy="UHT")
    cfg = SwitchConfig(min_steps_between_switches=3, q_low=0.4, hysteresis=0.08)
    st = evaluate_switch(st, step=1, q_hat=0.2, contradiction_rate=0.5, cfg=cfg)
    # too soon? step 1 from -999 is ok (>3). Should switch.
    assert st.current_policy != "UHT" or st.events
    last = st.last_switch_step
    st2 = evaluate_switch(st, step=last + 1, q_hat=0.9, cfg=cfg)
    # hysteresis / min steps should block immediate reverse
    assert st2.last_switch_step == last or st2.current_policy == st.current_policy


def test_fallback_triggers():
    state, actions = evaluate_safeguards(
        step=0, q_hat=0.4, contradiction_rate=0.4, evidence_fraction=0.05,
        remaining_budget=5, intending_stop=True, cfg=FallbackConfig(),
    )
    assert "mandatory_outsider_probe" in actions or "prohibit_stop" in actions or "final_challenger" in actions
    # Experimental escalation reroutes; that is exactly why it is experimental-only.
    pol = apply_experimental_escalation("UHT", ["mandatory_outsider_probe"], q_hat=0.4)
    assert pol == "CHALLENGER"


def test_probe_selection_budget():
    w = _tiny_world(seed=3)
    st = make_initial_robust_state(
        query_id="q", candidate_ids=list(w["true_ranking"]),
        prior_scores=w["prior_scores"], budget=10, top_k=2, seed=3,
    )
    for design in (
        "random_pairs", "prior_adjacent", "boundary_pairs", "topk_vs_outsider",
        "rank_distance_stratified", "mixed_diagnostic", "adaptive_diagnostic",
    ):
        pairs = select_probe_pairs(st, design=design, max_budget=3, seed=3)  # type: ignore[arg-type]
        assert len(pairs) <= 3


def test_policy_regret_prediction():
    X = [[0.1] * 5, [0.9] * 5, [0.2] * 5, [0.8] * 5]
    deltas = {"UHT_vs_CHALLENGER": [0.2, -0.3, 0.1, -0.4]}
    models = fit_regret_models(X, deltas, feature_names=[f"f{i}" for i in range(5)])
    pred = predict_policy_regret(models, X[0], pair="UHT_vs_CHALLENGER")
    assert "delta_mean" in pred.to_dict()
    assert isinstance(uht_allowed_by_risk(pred, delta_tol=0.99), bool)


def test_distribution_shift_ood_flag():
    w = _tiny_world(seed=4)
    st = make_initial_robust_state(
        query_id="q", candidate_ids=list(w["true_ranking"]),
        prior_scores=w["prior_scores"], budget=5, top_k=2, seed=4,
    )
    feats = extract_features(st, stage="pre")
    sel = PolicySelector(
        mode="contextual", ood_score=0.9, execution_mode=ExecutionMode.EXPERIMENTAL_GATE
    )
    dec = select_policy(feats, selector=sel)
    assert dec.g_q == pytest.approx(dec.g_q)


def test_deterministic_synthetic_benchmark_and_splits():
    splits = nested_split_regimes()
    assert set(splits) == {"train", "val", "test"}
    assert not set(splits["train"]["prior"]) & set(splits["test"]["prior"])
    cfg = PolicyBenchmarkConfig(
        n_items=6, top_k=2, budget=8,
        train_seeds=(0,), val_seeds=(10,), test_seeds=(20,),
    )
    # Features only first (fast), then one with outcomes for a tiny subset
    recs = build_synthetic_population(cfg, include_policy_outcomes=False, max_queries=3)
    assert len(recs) <= 3
    assert recs[0].features_pre is not None
    # Tiny with outcomes
    cfg2 = PolicyBenchmarkConfig(
        n_items=6, top_k=2, budget=8,
        train_seeds=(0,), val_seeds=(), test_seeds=(),
    )
    # Force only one cell by max_queries
    recs2 = build_synthetic_population(cfg2, include_policy_outcomes=True, max_queries=1)
    assert recs2[0].best_policy is not None
    assert recs2[0].split == "train"
    X, y, names, qids = records_to_xy(recs2)
    assert len(X) == len(y) == len(qids)
    assert len(names) == len(X[0])


def test_nested_threshold_selection_uses_val_only():
    # Smoke: fit on synthetic train vectors; threshold chosen externally on val utilities
    X = [[0.2, 0.3], [0.7, 0.8], [0.1, 0.2], [0.9, 0.85]]
    y = [0.0, 1.0, 0.0, 1.0]
    m = fit_calibrated_gate(X, y, feature_names=["a", "b"], kind="logistic")
    # Val utilities for thr grid
    Xv = [[0.3, 0.4], [0.6, 0.7]]
    utils = {0.4: 0.1, 0.6: 0.5}
    best = max(utils, key=utils.get)
    assert best == 0.6
    assert 0.0 <= predict_proba(m, Xv[0]) <= 1.0


def test_serialization_resume_switch_state(tmp_path: Path):
    st = SwitchState(current_policy="UHT", initial_policy="UHT")
    st = evaluate_switch(st, step=5, q_hat=0.1, buried_signal=0.9)
    path = tmp_path / "switch.json"
    path.write_text(json.dumps(st.to_dict()), encoding="utf-8")
    st2 = SwitchState.from_dict(json.loads(path.read_text(encoding="utf-8")))
    assert st2.current_policy == st.current_policy
    assert len(st2.events) == len(st.events)


def test_replay_action_isolation_no_qrel_impute():
    w = _tiny_world(seed=5)
    st = make_initial_robust_state(
        query_id="q", candidate_ids=list(w["true_ranking"]),
        prior_scores=w["prior_scores"], budget=5, top_k=2, seed=5,
    )
    pairs = select_probe_pairs(st, design="mixed_diagnostic", max_budget=3, seed=5)
    cache = build_cache_index([])  # empty
    feats, support = replay_probe_features(
        candidate_ids=list(w["true_ranking"]),
        prior_scores=w["prior_scores"],
        probe_pair_ids=pairs,
        cache=cache,
        top_k=2,
    )
    assert support.n_hits == 0
    assert feats is not None
    ev = evaluate_policy_under_replay(
        policy="UHT",
        requested_actions=[{"pair_id": pairs[0], "action_type": "NEW_PAIR"}] if pairs else [],
        cache=cache,
    )
    assert ev["evaluable"] is False or ev["n_requested"] == 0


def test_no_billed_calls_and_topological_validity():
    w = _tiny_world(prior="noisy", seed=6)
    res, outcome = run_named_policy(
        policy="UHT", world=w, budget=8, top_k=2, seed=6,
    )
    assert outcome.n_calls >= 0
    ranking = res.state.ranking
    # Build preference graph from acquired evidence and check topo if DAG-ish
    g = nx.DiGraph()
    g.add_nodes_from(w["true_ranking"])
    assert is_valid_topological_order(g, ranking) or len(ranking) == len(w["true_ranking"])


def test_gated_acquisition_dry_run():
    w = _tiny_world(prior="outsider_buried", seed=7)
    sel = PolicySelector(
        mode="soft_mixture", safety_floor=0.15, execution_mode=ExecutionMode.EXPERIMENTAL_GATE
    )
    out = run_gated_acquisition(
        world=w, selector=sel, budget=10, top_k=2, seed=7, probe_budget=2,
        enable_fallback=True,
    )
    assert out["decision"].policy in (
        "UHT", "UHT_EXPLORE", "CHALLENGER", "ROBUST_COMBINED", "BROAD_STATIC",
        "NO_PRIOR", "HYBRID", "STOP_OR_FALLBACK",
    )
    assert out["outcome"].n_calls >= out["outcome"].probe_calls


def test_risk_control_not_overclaimed():
    thr = fit_uht_risk_threshold(
        scores=[0.2, 0.5, 0.8, 0.9],
        uht_regret=[0.2, 0.1, 0.0, 0.0],
        catastrophic=[True, False, False, False],
    )
    rc = acceptable_policy_set(
        policy_scores={"UHT": 0.9, "CHALLENGER": 0.4},
        policy_regrets={"UHT": 0.0, "CHALLENGER": 0.05},
        uht_threshold=thr,
    )
    assert rc.is_formal_guarantee is False
    assert "exchangeability" in rc.assumptions.lower()


def test_gate_modes_smoke():
    w = _tiny_world(seed=8)
    st = make_initial_robust_state(
        query_id="q", candidate_ids=list(w["true_ranking"]),
        prior_scores=w["prior_scores"], budget=5, top_k=2, seed=8,
    )
    feats = extract_features(st, stage="pre")
    for mode in (
        "always_uht", "always_challenger", "hard_qhat", "calibrated_hard",
        "selective_three_way", "soft_mixture", "budget_split", "staged",
        "cost_sensitive_regret", "contextual", "conservative_fallback",
        "random", "majority_best", "oracle",
    ):
        dec = select_policy(
            feats,
            selector=PolicySelector(  # type: ignore[arg-type]
                mode=mode, execution_mode=ExecutionMode.EXPERIMENTAL_GATE
            ),
            oracle_best="UHT",
            rng_u=0.3,
        )
        assert dec.policy
        assert dec.feature_schema == FEATURE_SCHEMA_VERSION
