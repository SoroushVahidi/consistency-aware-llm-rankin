"""Tests for stability-guided adaptive comparison acquisition.

No test issues any billed API call; all judgments come from the simulated
interactive judge or the provenance-safe replay pool.
"""

from __future__ import annotations

import networkx as nx
import pytest

from consistency_ranker.adaptive_acquisition import (
    AcquisitionState,
    EngineConfig,
    StoppingPolicy,
    generate_eligible_actions,
    initial_state,
    make_interactive_judge,
    make_policy,
    run_acquisition,
    synthetic_roster,
)
from consistency_ranker.adaptive_acquisition.acquisition_actions import Action
from consistency_ranker.adaptive_acquisition.acquisition_policies import select_batch
from consistency_ranker.adaptive_acquisition.counterfactual import (
    expected_stability_gain,
    stability_score,
)
from consistency_ranker.adaptive_acquisition.interactive_judges import InteractiveJudgeConfig
from consistency_ranker.adaptive_acquisition.offline_replay import ReplayPool
from consistency_ranker.adaptive_acquisition.pair_uncertainty import (
    all_uncertainties,
    entropy_uncertainty,
    uncertainty,
    vote_uncertainty,
)
from consistency_ranker.adaptive_acquisition.provider_escalation import (
    ActionReliabilityModel,
    CascadeConfig,
    choose_judge_for_pair,
)
from consistency_ranker.adaptive_acquisition.ranking_impact import (
    ImpactContext,
    all_impacts,
    linear_extension_sensitivity,
)
from consistency_ranker.adaptive_acquisition.transitivity import implied_relation
from consistency_ranker.dag_linear_extensions import is_valid_topological_order
from consistency_ranker.multi_provider_eval.spending import SpendingCeiling
from consistency_ranker.reliability_repair.evidence_aggregation import aggregate_pair
from consistency_ranker.reliability_repair.pair_evidence import (
    NormalizedEvidence,
    canonical_pair_id,
    preference_from_simple,
)

# ---- fixtures --------------------------------------------------------

def _prior(items):
    n = len(items)
    return {d: float(n - i) for i, d in enumerate(items)}


def _state(n=6, budget=30, top_k=3, seed=0):
    items = [f"item_{i:02d}" for i in range(n)]
    return initial_state(
        query_id="q0",
        candidate_ids=items,
        prior_scores=_prior(items),
        budget=budget,
        top_k=top_k,
        seed=seed,
    )


def _judge(n=6, acc=0.8, seed=0, **kw):
    cfg = InteractiveJudgeConfig(n_items=n, base_accuracy=acc, seed=seed, **kw)
    return make_interactive_judge(n_items=n, config=cfg, seed=seed)


def _agg_from(pairs):
    """Build a PairAggregate from a list of (winner, loser)."""
    ev = [preference_from_simple(query_id="q0", winner=w, loser=lo) for w, lo in pairs]
    return aggregate_pair(ev)


# ---- state -----------------------------------------------------------

def test_state_serialization_roundtrip_and_resume():
    st = _state(n=5, budget=10)
    judge = _judge(n=5)
    profiles = synthetic_roster(n_models=2, n_prompts=1)
    res = run_acquisition(
        st, make_policy("uncertainty_only"), profiles, judge,
        engine_cfg=EngineConfig(n_impact_samples=6),
        stopping=StoppingPolicy(criteria=("budget",)),
    )
    d = res.state.to_dict()
    st2 = AcquisitionState.from_dict(d)
    assert len(st2.evidence) == len(res.state.evidence)
    assert st2.ranking == res.state.ranking
    assert st2.remaining_budget == res.state.remaining_budget
    # derived view recomputed without any stored judgments beyond evidence
    assert set(st2.view().aggregates) == set(res.state.view().aggregates)


def test_resume_continues_acquisition():
    st = _state(n=6, budget=4)
    judge = _judge(n=6)
    profiles = synthetic_roster(n_models=2, n_prompts=1)
    res = run_acquisition(st, make_policy("uncertainty_only"), profiles, judge,
                          engine_cfg=EngineConfig(n_impact_samples=6),
                          stopping=StoppingPolicy(criteria=("budget",)))
    st2 = AcquisitionState.from_dict(res.state.to_dict())
    n_before = len(st2.evidence)
    st2.remaining_budget = 4
    res2 = run_acquisition(st2, make_policy("uncertainty_only"), profiles, judge,
                           engine_cfg=EngineConfig(n_impact_samples=6),
                           stopping=StoppingPolicy(criteria=("budget",)))
    assert len(res2.state.evidence) > n_before


def test_final_ranking_is_valid_topological_order():
    st = _state(n=7, budget=25)
    judge = _judge(n=7, acc=0.85)
    profiles = synthetic_roster(n_models=3, n_prompts=2)
    res = run_acquisition(st, make_policy("uncertainty_x_topk_impact"), profiles, judge,
                          engine_cfg=EngineConfig(n_impact_samples=8),
                          stopping=StoppingPolicy(criteria=("budget",)))
    dag = res.state.view().dag
    assert nx.is_directed_acyclic_graph(dag)
    assert is_valid_topological_order(dag, [d for d in res.state.ranking if d in dag])


# ---- actions ---------------------------------------------------------

def test_no_duplicate_billed_actions():
    st = _state(n=4, budget=10)
    profiles = synthetic_roster(n_models=2, n_prompts=2)
    # add one judgment then regenerate actions
    e = preference_from_simple(query_id="q0", winner="item_00", loser="item_01",
                               provider="prov_0", model="model_0", prompt_version="prompt_0")
    st.add_evidence([e])
    acts = generate_eligible_actions(st, profiles)
    sigs = [a.billing_signature() for a in acts if a.action_type != "NO_ACTION"]
    assert len(sigs) == len(set(sigs))
    # the already-executed signature is not re-offered
    assert e_signature(e) not in set(sigs)


def e_signature(e: NormalizedEvidence):
    return (e.canonical_pair_id, str(e.provider), str(e.model),
            str(e.prompt_version), str(e.displayed_orientation), int(e.repetition_index))


def test_orientation_and_alternate_actions_generated():
    st = _state(n=3, budget=10)
    profiles = synthetic_roster(n_models=2, n_prompts=2)
    e = preference_from_simple(query_id="q0", winner="item_00", loser="item_01",
                               provider="prov_0", model="model_0", prompt_version="prompt_0")
    st.add_evidence([e])
    acts = generate_eligible_actions(st, profiles)
    types = {a.action_type for a in acts}
    assert "REVERSE_ORIENTATION" in types
    assert "ALTERNATE_PROMPT" in types
    assert "ALTERNATE_MODEL" in types
    assert "NEW_PAIR" in types  # other pairs still unqueried


def test_provider_model_action_normalization():
    st = _state(n=3, budget=10)
    profiles = synthetic_roster(n_models=2, n_prompts=1)
    acts = generate_eligible_actions(st, profiles, include_no_action=False)
    for a in acts:
        assert a.provider is not None and a.model is not None
        assert a.orientation in ("ab", "ba")
        assert a.est_cost > 0


# ---- uncertainty -----------------------------------------------------

def test_vote_and_entropy_extremes():
    unanimous = _agg_from([("item_00", "item_01")] * 4)
    split = _agg_from([("item_00", "item_01"), ("item_01", "item_00")])
    assert vote_uncertainty(unanimous) < 0.5
    assert vote_uncertainty(split) == pytest.approx(1.0, abs=1e-6)
    assert entropy_uncertainty(split) == pytest.approx(1.0, abs=1e-6)
    assert vote_uncertainty(None) == 1.0
    for v in all_uncertainties(split).values():
        assert 0.0 <= v <= 1.0


def test_cross_model_uncertainty_detects_disagreement():
    ev = [
        preference_from_simple(query_id="q0", winner="item_00", loser="item_01",
                               provider="prov_0", model="model_0"),
        preference_from_simple(query_id="q0", winner="item_01", loser="item_00",
                               provider="prov_1", model="model_1"),
    ]
    agg = aggregate_pair(ev)
    assert uncertainty(agg, method="cross_model") == pytest.approx(1.0, abs=1e-6)


# ---- impact ----------------------------------------------------------

def test_impact_measures_bounded():
    st = _state(n=6, budget=10)
    judge = _judge(n=6)
    profiles = synthetic_roster(n_models=2, n_prompts=1)
    run_acquisition(st, make_policy("uncertainty_only"), profiles, judge,
                    engine_cfg=EngineConfig(n_impact_samples=8),
                    stopping=StoppingPolicy(criteria=("budget",)))
    ctx = ImpactContext.build(st, n_samples=8)
    for pid in st.all_pair_ids():
        for name, v in all_impacts(st, pid, ctx).items():
            assert 0.0 <= v <= 1.0, (name, v)


def test_linear_extension_sensitivity_high_for_incomparable():
    # empty-ish DAG: two isolated nodes are (near-)fully variable in order.
    st = _state(n=2, budget=1)
    ctx = ImpactContext.build(st, n_samples=8)
    pid = st.all_pair_ids()[0]
    assert linear_extension_sensitivity(st, pid, ctx) >= 0.7


def test_linear_extension_sensitivity_low_for_determined():
    st = _state(n=2, budget=1)
    st.add_evidence([preference_from_simple(query_id="q0", winner="item_00", loser="item_01")])
    ctx = ImpactContext.build(st, n_samples=8)
    pid = st.all_pair_ids()[0]
    # edge fixes the order → not variable
    assert linear_extension_sensitivity(st, pid, ctx) == pytest.approx(0.0, abs=1e-6)


# ---- counterfactual & cost ------------------------------------------

def test_expected_stability_gain_shape():
    st = _state(n=5, budget=5)
    judge = _judge(n=5)
    profiles = synthetic_roster(n_models=1, n_prompts=1)
    # seed a couple of judgments so a graph exists
    run_acquisition(st, make_policy("uncertainty_only"), profiles, judge,
                    engine_cfg=EngineConfig(n_impact_samples=6),
                    stopping=StoppingPolicy(criteria=("budget",)))
    acts = generate_eligible_actions(st, profiles, include_no_action=False)
    a = next(x for x in acts if x.action_type in ("REVERSE_ORIENTATION", "REPEAT_SAME", "NEW_PAIR"))
    out = expected_stability_gain(st, a)
    assert set(out) >= {"expected_delta_stability", "s_before", "expected_s_after"}
    assert 0.0 <= out["s_before"] <= 1.0


def test_cost_normalization_penalizes_expensive():
    # Fresh, unresolved state: every pair is uncertain (U=1) and incomparable
    # (S=1) so the numerator U*H*S*R is strictly positive.
    st = _state(n=5, budget=8)
    ctx = ImpactContext.build(st, n_samples=6)
    pol = make_policy("cost_normalized_value")
    pid = st.all_pair_ids()[0]
    di, dj = st.pair_docs(pid)
    cheap = Action(action_type="NEW_PAIR", pair_id=pid,
                   doc_i=di, doc_j=dj, provider="prov_0", model="model_0",
                   prompt_version="prompt_0", est_cost=1.0, expected_reliability=0.8)
    exp = Action(**{**cheap.__dict__, "est_cost": 10.0})
    sc_cheap, bd = pol.base_score(st, ctx, cheap)
    sc_exp, _ = pol.base_score(st, ctx, exp)
    assert sc_cheap > sc_exp > 0.0


# ---- stopping --------------------------------------------------------

def test_budget_stop():
    st = _state(n=5, budget=3)
    judge = _judge(n=5)
    profiles = synthetic_roster(n_models=1, n_prompts=1)
    res = run_acquisition(st, make_policy("uncertainty_only"), profiles, judge,
                          engine_cfg=EngineConfig(n_impact_samples=6),
                          stopping=StoppingPolicy(criteria=("budget",)))
    assert res.n_calls <= 3
    assert res.stopping_reason in ("budget_exhausted", "no_eligible_actions")


def test_stable_topk_membership_stops_early_with_good_prior():
    st = _state(n=6, budget=50)
    judge = _judge(n=6, acc=0.95)
    profiles = synthetic_roster(n_models=2, n_prompts=1)
    res = run_acquisition(st, make_policy("uncertainty_x_topk_impact"), profiles, judge,
                          engine_cfg=EngineConfig(n_impact_samples=10),
                          stopping=StoppingPolicy(criteria=("budget", "stable_topk_membership"),
                                                  delta=0.1))
    assert res.n_calls < 50  # stopped before exhausting budget


# ---- transitivity ----------------------------------------------------

def test_transitive_inference_on_chain():
    st = _state(n=3, budget=10)
    # a>b and b>c => a>c implied
    ev = [
        preference_from_simple(query_id="q0", winner="item_00", loser="item_01"),
        preference_from_simple(query_id="q0", winner="item_01", loser="item_02"),
    ]
    st.add_evidence(ev)
    ctx = ImpactContext.build(st, n_samples=8)
    pid_ac = canonical_pair_id("q0", "item_00", "item_02")
    rel = implied_relation(st, pid_ac, ctx, min_path_reliability=0.0)
    assert rel.implied
    assert rel.direction == 1  # item_00 -> item_02


# ---- batch -----------------------------------------------------------

def test_batch_one_per_doc():
    st = _state(n=8, budget=20)
    profiles = synthetic_roster(n_models=1, n_prompts=1)
    ctx = ImpactContext.build(st, n_samples=6)
    acts = generate_eligible_actions(st, profiles)
    batch = select_batch(make_policy("uncertainty_only"), st, ctx, acts,
                         batch_size=3, one_per_doc=True)
    docs = []
    for a in batch:
        docs += [a.doc_i, a.doc_j]
    assert len(docs) == len(set(docs))  # no doc reused within the batch


# ---- interactive judge isolation ------------------------------------

def test_judge_only_answers_on_request():
    st = _state(n=5, budget=4)
    judge = _judge(n=5)
    profiles = synthetic_roster(n_models=2, n_prompts=1)
    res = run_acquisition(st, make_policy("uncertainty_only"), profiles, judge,
                          engine_cfg=EngineConfig(n_impact_samples=6),
                          stopping=StoppingPolicy(criteria=("budget",)))
    # judge.calls equals number of successful/attempted judged actions (no leakage)
    assert judge.calls == len(res.state.evidence)


def test_judge_missing_provider_returns_none():
    judge = _judge(n=4, available_providers=("prov_0",))
    a = Action(action_type="ALTERNATE_MODEL", pair_id=canonical_pair_id("q0", "item_00", "item_01"),
               doc_i="item_00", doc_j="item_01", provider="prov_9", model="model_9",
               prompt_version="prompt_0")
    assert judge.available(a) is False
    assert judge.judge(a) is None


def test_judge_deterministic_same_signature():
    judge = _judge(n=4, seed=7)
    a = Action(action_type="NEW_PAIR", pair_id=canonical_pair_id("q0", "item_00", "item_02"),
               doc_i="item_00", doc_j="item_02", provider="prov_0", model="model_0",
               prompt_version="prompt_0", orientation="ab", repetition_index=0)
    r1 = judge.judge(a)
    r2 = judge.judge(a)
    assert r1.z == r2.z


# ---- replay isolation ------------------------------------------------

def _replay_records():
    recs = []
    q = "q0"
    for pid_docs in [("d0", "d1"), ("d1", "d2")]:
        a, b = pid_docs
        recs.append({
            "query_id": q, "provider": "azure", "model": "m", "prompt_version": "p",
            "doc_a_id": a, "doc_b_id": b,
            "canonical_pair_id": canonical_pair_id(q, a, b),
            "displayed_orientation": "ab", "normalized_winner_id": a,
            "parsed_choice": "A", "valid": True, "cache_key": f"k_{a}_{b}",
        })
    return recs


def test_replay_pool_isolation_and_single_use():
    recs = _replay_records()
    pool = ReplayPool.from_records("q0", recs)
    a_avail = Action(action_type="NEW_PAIR", pair_id=canonical_pair_id("q0", "d0", "d1"),
                     doc_i="d0", doc_j="d1", provider="azure", model="m",
                     prompt_version="p", orientation="ab")
    a_missing = Action(action_type="NEW_PAIR", pair_id=canonical_pair_id("q0", "d0", "d2"),
                       doc_i="d0", doc_j="d2", provider="azure", model="m",
                       prompt_version="p", orientation="ab")
    assert pool.has(a_avail)
    assert not pool.has(a_missing)
    assert pool.judge(a_avail) is not None
    # consumed once
    assert pool.judge(a_avail) is None
    assert pool.n_unavailable >= 1


# ---- determinism -----------------------------------------------------

def test_deterministic_seed_reproducibility():
    def run():
        st = _state(n=6, budget=12, seed=5)
        judge = _judge(n=6, seed=5)
        profiles = synthetic_roster(n_models=2, n_prompts=1)
        res = run_acquisition(st, make_policy("uncertainty_x_topk_impact"), profiles, judge,
                              engine_cfg=EngineConfig(n_impact_samples=8, seed=5),
                              stopping=StoppingPolicy(criteria=("budget",)))
        return res.state.ranking, res.action_counts
    assert run() == run()


# ---- provider ceilings ----------------------------------------------

def test_spending_ceiling_stops_run():
    st = _state(n=6, budget=100)
    judge = _judge(n=6)
    profiles = synthetic_roster(n_models=3, n_prompts=2)
    ceiling = SpendingCeiling(max_new_calls_global=5,
                              max_new_calls_per_provider={}, max_prompt_tokens_global=None)
    res = run_acquisition(st, make_policy("uncertainty_x_topk_impact"), profiles, judge,
                          engine_cfg=EngineConfig(n_impact_samples=6),
                          stopping=StoppingPolicy(criteria=("budget", "provider_budget")),
                          spending_ceiling=ceiling)
    assert res.n_calls <= 5
    assert ceiling.new_calls_global <= 5


# ---- reliability model ----------------------------------------------

def test_reliability_model_shrinkage():
    st = _state(n=4, budget=4)
    model = ActionReliabilityModel(method="smoothed", prior_strength=4.0)
    a = Action(action_type="NEW_PAIR", pair_id=canonical_pair_id("q0", "item_00", "item_01"),
               doc_i="item_00", doc_j="item_01", provider="prov_0", model="model_0",
               prompt_version="prompt_0", expected_reliability=0.7)
    # no history -> falls back to prior
    assert model.expected(st, a) == pytest.approx(0.7, abs=1e-6)


# ---- cascade ---------------------------------------------------------

def test_cascade_new_pair_when_unqueried():
    st = _state(n=4, budget=10)
    profiles = synthetic_roster(n_models=2, n_prompts=1)
    ctx = ImpactContext.build(st, n_samples=6)
    pid = st.all_pair_ids()[0]
    a = choose_judge_for_pair(st, pid, ctx, profiles, cascade=CascadeConfig())
    assert a is not None and a.action_type == "NEW_PAIR"


def test_stability_score_bounded():
    st = _state(n=5, budget=6)
    judge = _judge(n=5)
    profiles = synthetic_roster(n_models=1, n_prompts=1)
    run_acquisition(st, make_policy("uncertainty_only"), profiles, judge,
                    engine_cfg=EngineConfig(n_impact_samples=6),
                    stopping=StoppingPolicy(criteria=("budget",)))
    s = stability_score(st.view(), len(st.candidate_ids))
    assert 0.0 <= s <= 1.0


def test_no_qrel_dependency_in_run():
    # A full run needs only prior + judge; no labels are passed to selection.
    st = _state(n=5, budget=8)
    judge = _judge(n=5)
    profiles = synthetic_roster(n_models=2, n_prompts=1)
    res = run_acquisition(st, make_policy("cost_normalized_esg"), profiles, judge,
                          engine_cfg=EngineConfig(n_impact_samples=6),
                          stopping=StoppingPolicy(criteria=("budget",)))
    assert res.n_calls > 0
