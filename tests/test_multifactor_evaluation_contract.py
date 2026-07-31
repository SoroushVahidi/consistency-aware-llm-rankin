"""Regression tests for multifactor evaluation contract and production UHT metrics."""

from __future__ import annotations

from consistency_ranker.adaptive_acquisition import synthetic_roster
from consistency_ranker.multifactor_acquisition.analyze import (
    build_policy_comparison_table,
    eval_ranking,
    render_verdict,
)
from consistency_ranker.multifactor_acquisition.cache_only_judge import CacheOnlyJudge
from consistency_ranker.multifactor_acquisition.evaluation_contract import (
    evaluate_ranking,
    ranking_from_prior,
)
from consistency_ranker.policy_selection.production_runner import (
    ProductionSafeguards,
    run_production_uht,
)
from consistency_ranker.prior_robust import make_initial_robust_state
from consistency_ranker.reliability_repair.pair_evidence import (
    NormalizedEvidence,
    canonical_pair_id,
)


def _ev(qid: str, a: str, b: str, z: int = 1) -> NormalizedEvidence:
    return NormalizedEvidence(
        query_id=qid,
        canonical_pair_id=canonical_pair_id(qid, a, b),
        doc_i=a,
        doc_j=b,
        displayed_orientation="ab",
        z=z,  # type: ignore[arg-type]
        abstention_subtype=None,  # type: ignore[arg-type]
        provider="azure",
        model="m",
        prompt_version="legacy_v1",
        valid=True,
    )


def test_shared_qrels_and_cutoff_across_policies():
    pool = ["a", "b", "c", "d"]
    qrels = {"a": 1, "c": 1}
    prior = ranking_from_prior({"a": 0.1, "b": 0.9, "c": 0.2, "d": 0.0})
    rankings = {
        "UHT": ["b", "a", "c", "d"],
        "HYBRID": ["a", "c", "b", "d"],
        "production_uht": ["b", "d", "a", "c"],
    }
    k = 2
    results = {
        name: evaluate_ranking(
            ranking,
            qrels,
            k=k,
            n_calls=3,
            prior_ranking=prior,
            candidate_pool=pool,
        )
        for name, ranking in rankings.items()
    }
    assert all(r.has_qrels for r in results.values())
    assert all(r.k == k for r in results.values())
    assert all(r.ndcg_at_k is not None for r in results.values())
    # Same pool / cutoff ⇒ comparable denominators.
    assert {r.n_relevant_in_pool for r in results.values()} == {2}


def test_production_uht_nonempty_ndcg_when_qrels_exist():
    ranking = ["a", "b", "c"]
    qrels = {"a": 1, "c": 1}
    oc, u = eval_ranking(
        ranking,
        qrels,
        k=2,
        n_calls=4,
        policy="production_uht",
        prior_ranking=["b", "a", "c"],
        candidate_pool=["a", "b", "c"],
    )
    assert oc.extra["ndcg_at_k"] is not None
    assert oc.extra["ndcg_at_k"] > 0
    assert u is not None


def test_prior_agreement_not_relevance_truth_counterexample():
    """Prior agreement can be 1.0 while nDCG is strictly below 1.0."""
    pool = ["good", "bad", "meh"]
    # Prior ranks bad first; qrels prefer good.
    prior = {"bad": 1.0, "meh": 0.5, "good": 0.1}
    prior_ranking = ranking_from_prior(prior)
    # Production returns the prior order.
    produced = list(prior_ranking)
    qrels = {"good": 2, "meh": 1, "bad": 0}
    result = evaluate_ranking(
        produced,
        qrels,
        k=2,
        n_calls=0,
        prior_ranking=prior_ranking,
        candidate_pool=pool,
    )
    assert result.prior_topk_jaccard == 1.0
    assert result.ndcg_at_k is not None
    assert result.ndcg_at_k < 1.0
    # Therefore prior agreement cannot substitute for relevance evaluation.


def test_missing_qrels_remain_missing_not_zero_or_prior():
    prior_ranking = ["a", "b", "c"]
    result = evaluate_ranking(
        ["a", "b", "c"],
        {},
        k=2,
        n_calls=3,
        prior_ranking=prior_ranking,
        candidate_pool=["a", "b", "c"],
    )
    assert result.has_qrels is False
    assert result.ndcg_at_k is None
    assert result.utility is None
    assert result.missing_qrels_reason == "qrels_unavailable"
    # Prior diagnostic may still be present.
    assert result.prior_topk_jaccard == 1.0


def test_production_uht_jaccard_not_automatically_one_vs_qrels():
    # Relevance top-k Jaccard vs qrels should not collapse to 1 when prior agrees.
    prior_ranking = ["x", "y", "z"]
    produced = ["x", "y", "z"]  # prior agreement 1.0
    qrels = {"z": 1, "y": 0, "x": 0}
    result = evaluate_ranking(
        produced,
        qrels,
        k=2,
        n_calls=1,
        prior_ranking=prior_ranking,
        candidate_pool=["x", "y", "z"],
    )
    assert result.prior_topk_jaccard == 1.0
    assert result.relevance_topk_jaccard is not None
    assert result.relevance_topk_jaccard < 1.0


def test_aggregate_denominators_exclude_missing_qrels():
    rows = [
        {
            "policy": "HYBRID",
            "budget": 8,
            "query_id": "q1",
            "provider": "azure",
            "prompt_version": "legacy_v1",
            "orientation": "ab",
            "ndcg_at_k": 0.9,
            "utility": 0.8,
            "n_calls": 4,
            "prior_topk_jaccard": 0.5,
        },
        {
            "policy": "HYBRID",
            "budget": 8,
            "query_id": "q2",
            "provider": "azure",
            "prompt_version": "legacy_v1",
            "orientation": "ab",
            "ndcg_at_k": None,
            "utility": None,
            "n_calls": 4,
            "prior_topk_jaccard": 1.0,
        },
        {
            "policy": "production_uht",
            "budget": 8,
            "query_id": "q1",
            "provider": "azure",
            "prompt_version": "legacy_v1",
            "orientation": "ab",
            "ndcg_at_k": 0.85,
            "utility": 0.7,
            "n_calls": 6,
            "prior_topk_jaccard": 0.5,
        },
        {
            "policy": "production_uht",
            "budget": 8,
            "query_id": "q2",
            "provider": "azure",
            "prompt_version": "legacy_v1",
            "orientation": "ab",
            "ndcg_at_k": None,
            "utility": None,
            "n_calls": 6,
            "prior_topk_jaccard": 1.0,
        },
    ]
    table = build_policy_comparison_table(
        rows,
        baseline_policy="production_uht",
        policies=("HYBRID", "production_uht"),
        budgets=(8,),
    )
    hybrid = next(r for r in table if r["policy"] == "HYBRID")
    assert hybrid["n_rows"] == 2
    assert hybrid["n_qrels_valid"] == 1
    assert hybrid["n_qrels_missing"] == 1


def test_verdict_not_challenger_only_and_not_cost_only():
    # HYBRID has better utility via fewer calls but worse/equal nDCG → not a quality win.
    rows = []
    for qid in ("q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8", "q9", "q10", "q11"):
        rows.append(
            {
                "policy": "production_uht",
                "budget": 8,
                "query_id": qid,
                "provider": "azure",
                "prompt_version": "v",
                "orientation": "ab",
                "ndcg_at_k": 0.9,
                "utility": 0.80,
                "n_calls": 8,
                "prior_topk_jaccard": 0.4,
            }
        )
        rows.append(
            {
                "policy": "HYBRID",
                "budget": 8,
                "query_id": qid,
                "provider": "azure",
                "prompt_version": "v",
                "orientation": "ab",
                "ndcg_at_k": 0.88,
                "utility": 0.86,  # higher utility from fewer calls
                "n_calls": 2,
                "prior_topk_jaccard": 0.4,
            }
        )
        rows.append(
            {
                "policy": "CHALLENGER",
                "budget": 8,
                "query_id": qid,
                "provider": "azure",
                "prompt_version": "v",
                "orientation": "ab",
                "ndcg_at_k": 0.87,
                "utility": 0.85,
                "n_calls": 2,
                "prior_topk_jaccard": 0.4,
            }
        )
        rows.append(
            {
                "policy": "ROBUST_COMBINED",
                "budget": 8,
                "query_id": qid,
                "provider": "azure",
                "prompt_version": "v",
                "orientation": "ab",
                "ndcg_at_k": 0.89,
                "utility": 0.84,
                "n_calls": 3,
                "prior_topk_jaccard": 0.4,
            }
        )
    table = build_policy_comparison_table(
        rows,
        baseline_policy="production_uht",
        policies=("production_uht", "CHALLENGER", "HYBRID", "ROBUST_COMBINED"),
        budgets=(8,),
    )
    verdict = render_verdict(table, min_query_units=10)
    allowed = ("PRESPECIFIED", "COST", "NO MATCHED", "INCONCLUSIVE", "QUALITY")
    assert any(tok in verdict["verdict"] for tok in allowed)
    # Must not declare success from call savings alone.
    assert "ACTIONABLE CRITERION FOUND" not in verdict["verdict"]
    assert any(d["policy"] == "HYBRID" for d in verdict["details"])
    assert any(d["policy"] == "ROBUST_COMBINED" for d in verdict["details"])


def test_production_path_invoked_with_safeguard_metadata_and_no_routing():
    docs = [f"d{i}" for i in range(6)]
    prior = {d: float(6 - i) for i, d in enumerate(docs)}
    qid = "q_test"
    # Populate cache with many pairs so safeguards can execute.
    rows = []
    for i, a in enumerate(docs):
        for b in docs[i + 1 :]:
            rows.append(
                {
                    "query_id": qid,
                    "doc_i": a,
                    "doc_j": b,
                    "z": 1,
                    "valid": True,
                    "provider": "azure",
                    "model": "m",
                    "prompt_version": "legacy_v1",
                    "displayed_orientation": "ab",
                    "identity": (
                        f"{canonical_pair_id(qid, a, b)}|azure|m|legacy_v1|ab"
                    ),
                }
            )
    judge = CacheOnlyJudge.from_parsed_rows(
        rows,
        query_id=qid,
        provider="azure",
        model="m",
        prompt_version="legacy_v1",
        orientation="ab",
    )
    prod = run_production_uht(
        world={"candidate_ids": docs, "prior_scores": prior, "judge": judge},
        budget=12,
        top_k=2,
        seed=0,
        query_id=qid,
    )
    assert prod.executed_policy == "UHT"
    assert prod.execution_mode.value == "production_uht"
    assert prod.experimental_policy is None
    sg = prod.safeguards.to_dict()
    assert "outsider_probe_required" in sg
    assert "outsider_probe_attempted" in sg
    assert "outsider_probe_executed" in sg
    assert "outsider_probe_skip_reason" in sg
    assert "final_challenger_attempted" in sg
    assert "production_safeguards_complete" in sg
    assert sg["outsider_probe_executed"] is True
    assert sg["final_challenger_executed"] is True
    assert judge.paid_api_calls == 0


def test_budget_exhaustion_records_safeguard_skip_reason():
    docs = [f"d{i}" for i in range(5)]
    prior = {d: float(5 - i) for i, d in enumerate(docs)}
    qid = "q_empty"
    judge = CacheOnlyJudge.from_parsed_rows(
        [],
        query_id=qid,
        provider="azure",
        model="m",
        prompt_version="legacy_v1",
        orientation="ab",
    )
    prod = run_production_uht(
        world={"candidate_ids": docs, "prior_scores": prior, "judge": judge},
        budget=3,
        top_k=2,
        seed=0,
        query_id=qid,
    )
    sg = prod.safeguards
    assert sg.outsider_probe_required is True
    assert sg.outsider_probe_eligible is True
    assert sg.outsider_probe_attempted is True
    assert sg.outsider_probe_executed is False
    assert sg.outsider_probe_skip_reason in {
        "judge_unavailable",
        "judgment_returned_none",
        "no_candidate_executed",
        "action_ineligible",
        "budget_exhausted",
    }
    # Documented terminal skip ⇒ complete accounting, not empirical success.
    assert sg.production_safeguards_complete is True
    assert sg.outsider_probe_executed is False


def test_outsider_probe_falls_back_beyond_designed_pair():
    """A single unavailable designed pair must not disable the floor."""
    docs = [f"d{i}" for i in range(6)]
    prior = {d: float(6 - i) for i, d in enumerate(docs)}
    state = make_initial_robust_state(
        query_id="q",
        candidate_ids=docs,
        prior_scores=prior,
        budget=8,
        top_k=2,
        seed=0,
    )
    profiles = synthetic_roster(n_models=2, n_prompts=2)
    # Cache only a deep insider-outsider pair that designed topk_vs_outsider may miss.
    io_pairs = ProductionSafeguards()._insider_outsider_pairs(state)
    assert io_pairs
    target = io_pairs[-1]
    a, b = state.pair_docs(target)
    rows = [
        {
            "query_id": "q",
            "doc_i": a,
            "doc_j": b,
            "z": 1,
            "valid": True,
            "provider": "azure",
            "model": "m",
            "prompt_version": "legacy_v1",
            "displayed_orientation": "ab",
            "identity": f"{target}|azure|m|legacy_v1|ab",
        }
    ]
    judge = CacheOnlyJudge.from_parsed_rows(
        rows,
        query_id="q",
        provider="azure",
        model="m",
        prompt_version="legacy_v1",
        orientation="ab",
    )
    ok, skip = ProductionSafeguards().run_outsider_probe(state, profiles, judge, seed=0)
    assert ok is True
    assert skip is None


def test_deterministic_offline_replay_for_fixed_cache_and_seed():
    docs = [f"d{i}" for i in range(5)]
    prior = {d: float(5 - i) for i, d in enumerate(docs)}
    qid = "q_det"
    rows = []
    for i, a in enumerate(docs):
        for b in docs[i + 1 :]:
            rows.append(
                {
                    "query_id": qid,
                    "doc_i": a,
                    "doc_j": b,
                    "z": 1 if a < b else -1,
                    "valid": True,
                    "provider": "azure",
                    "model": "m",
                    "prompt_version": "legacy_v1",
                    "displayed_orientation": "ab",
                    "identity": f"{canonical_pair_id(qid, a, b)}|azure|m|legacy_v1|ab",
                }
            )

    def once():
        judge = CacheOnlyJudge.from_parsed_rows(
            rows,
            query_id=qid,
            provider="azure",
            model="m",
            prompt_version="legacy_v1",
            orientation="ab",
        )
        return run_production_uht(
            world={"candidate_ids": docs, "prior_scores": prior, "judge": judge},
            budget=8,
            top_k=2,
            seed=7,
            query_id=qid,
        )

    a, b = once(), once()
    assert a.ranking == b.ranking
    assert a.n_calls == b.n_calls
    assert a.safeguards.to_dict() == b.safeguards.to_dict()


def test_full_pool_top_k_documents_outsider_inapplicable():
    """When top_k == n_candidates there is no outsider; skip is documented."""
    docs = [f"d{i}" for i in range(4)]
    prior = {d: float(4 - i) for i, d in enumerate(docs)}
    qid = "q_full"
    rows = []
    for i, a in enumerate(docs):
        for b in docs[i + 1 :]:
            rows.append(
                {
                    "query_id": qid,
                    "doc_i": a,
                    "doc_j": b,
                    "z": 1,
                    "valid": True,
                    "provider": "azure",
                    "model": "m",
                    "prompt_version": "legacy_v1",
                    "displayed_orientation": "ab",
                    "identity": f"{canonical_pair_id(qid, a, b)}|azure|m|legacy_v1|ab",
                }
            )
    judge = CacheOnlyJudge.from_parsed_rows(
        rows,
        query_id=qid,
        provider="azure",
        model="m",
        prompt_version="legacy_v1",
        orientation="ab",
    )
    prod = run_production_uht(
        world={"candidate_ids": docs, "prior_scores": prior, "judge": judge},
        budget=8,
        top_k=4,
        seed=0,
        query_id=qid,
    )
    sg = prod.safeguards
    assert sg.outsider_probe_required is True
    assert sg.outsider_probe_eligible is False
    assert sg.outsider_probe_attempted is False
    assert sg.outsider_probe_executed is False
    assert sg.outsider_probe_skip_reason == "not_eligible:no_insider_outsider_pairs"
    assert sg.final_challenger_eligible is False
    assert sg.final_challenger_attempted is False
    assert sg.final_challenger_skip_reason == "not_eligible:no_insider_outsider_pairs"
    # Inapplicable ≠ silent failure.
    assert sg.production_safeguards_complete is True


def test_full_pool_topk_jaccard_is_uninformative_membership():
    """k >= pool_size ⇒ Jaccard==1 is membership, not ranking equality."""
    pool = ["a", "b", "c", "d"]
    prior = ["a", "b", "c", "d"]
    # Distinct permutation of the same full pool.
    produced = ["d", "c", "b", "a"]
    result = evaluate_ranking(
        produced,
        {"a": 1, "d": 2},
        k=4,
        n_calls=0,
        prior_ranking=prior,
        candidate_pool=pool,
    )
    assert result.prior_topk_jaccard == 1.0
    assert result.prior_topk_jaccard_informative is False
    assert result.prior_kendall_tau is not None
    assert result.prior_kendall_tau < 1.0
    assert result.agreement_metric_informative is True


def test_policy_definitions_distinguish_uht_variants():
    from consistency_ranker.multifactor_acquisition.evaluation_contract import (
        POLICY_DEFINITIONS,
    )

    assert set(POLICY_DEFINITIONS) >= {"production_uht", "plain_uht", "UHT"}
    assert POLICY_DEFINITIONS["production_uht"]["runner"] == "run_production_uht"
    assert POLICY_DEFINITIONS["plain_uht"]["safeguards"] == "no"
    assert POLICY_DEFINITIONS["UHT"]["safeguards"] == "no"
    assert (
        POLICY_DEFINITIONS["production_uht"]["display_name"]
        != POLICY_DEFINITIONS["UHT"]["display_name"]
    )
    assert (
        POLICY_DEFINITIONS["production_uht"]["display_name"]
        != POLICY_DEFINITIONS["plain_uht"]["display_name"]
    )


def test_safeguard_invariants_executed_implies_attempted_implies_eligible():
    docs = [f"d{i}" for i in range(6)]
    prior = {d: float(6 - i) for i, d in enumerate(docs)}
    qid = "q_inv"
    rows = []
    for i, a in enumerate(docs):
        for b in docs[i + 1 :]:
            rows.append(
                {
                    "query_id": qid,
                    "doc_i": a,
                    "doc_j": b,
                    "z": 1,
                    "valid": True,
                    "provider": "azure",
                    "model": "m",
                    "prompt_version": "legacy_v1",
                    "displayed_orientation": "ab",
                    "identity": f"{canonical_pair_id(qid, a, b)}|azure|m|legacy_v1|ab",
                }
            )
    judge = CacheOnlyJudge.from_parsed_rows(
        rows,
        query_id=qid,
        provider="azure",
        model="m",
        prompt_version="legacy_v1",
        orientation="ab",
    )
    prod = run_production_uht(
        world={"candidate_ids": docs, "prior_scores": prior, "judge": judge},
        budget=12,
        top_k=2,
        seed=0,
        query_id=qid,
    )
    sg = prod.safeguards
    if sg.outsider_probe_executed:
        assert sg.outsider_probe_attempted
        assert sg.outsider_probe_eligible
        assert sg.outsider_probe_skip_reason is None
    if sg.outsider_probe_attempted:
        assert sg.outsider_probe_eligible
    if sg.final_challenger_executed:
        assert sg.final_challenger_attempted
        assert sg.final_challenger_eligible
    if (not sg.outsider_probe_executed) and sg.outsider_probe_required:
        assert sg.outsider_probe_skip_reason
    # Safeguard calls counted once in n_calls.
    assert prod.n_calls >= sg.safeguard_calls


def test_verdict_quality_win_non_challenger():
    rows = []
    for qid in [f"q{i}" for i in range(12)]:
        rows.append(
            {
                "policy": "production_uht",
                "budget": 8,
                "query_id": qid,
                "provider": "azure",
                "prompt_version": "v",
                "orientation": "ab",
                "ndcg_at_k": 0.5,
                "utility": 0.4,
                "n_calls": 8,
                "prior_kendall_tau": 0.5,
                "prior_topk_jaccard": 1.0,
                "prior_topk_jaccard_informative": False,
            }
        )
        rows.append(
            {
                "policy": "HYBRID",
                "budget": 8,
                "query_id": qid,
                "provider": "azure",
                "prompt_version": "v",
                "orientation": "ab",
                "ndcg_at_k": 0.9,
                "utility": 0.85,
                "n_calls": 4,
                "prior_kendall_tau": 0.4,
                "prior_topk_jaccard": 1.0,
                "prior_topk_jaccard_informative": False,
            }
        )
        rows.append(
            {
                "policy": "CHALLENGER",
                "budget": 8,
                "query_id": qid,
                "provider": "azure",
                "prompt_version": "v",
                "orientation": "ab",
                "ndcg_at_k": 0.45,
                "utility": 0.4,
                "n_calls": 4,
                "prior_kendall_tau": 0.4,
                "prior_topk_jaccard": 1.0,
                "prior_topk_jaccard_informative": False,
            }
        )
        rows.append(
            {
                "policy": "ROBUST_COMBINED",
                "budget": 8,
                "query_id": qid,
                "provider": "azure",
                "prompt_version": "v",
                "orientation": "ab",
                "ndcg_at_k": 0.48,
                "utility": 0.42,
                "n_calls": 4,
                "prior_kendall_tau": 0.4,
                "prior_topk_jaccard": 1.0,
                "prior_topk_jaccard_informative": False,
            }
        )
    table = build_policy_comparison_table(
        rows,
        baseline_policy="production_uht",
        policies=("production_uht", "CHALLENGER", "HYBRID", "ROBUST_COMBINED"),
        budgets=(8,),
    )
    verdict = render_verdict(table, min_query_units=10)
    assert "QUALITY ADVANTAGE" in verdict["verdict"]
    assert any(w["policy"] == "HYBRID" for w in verdict["quality_wins"])


def test_verdict_quality_loss_but_higher_utility_is_cost_only():
    rows = []
    for qid in [f"q{i}" for i in range(12)]:
        rows.append(
            {
                "policy": "production_uht",
                "budget": 8,
                "query_id": qid,
                "provider": "azure",
                "prompt_version": "v",
                "orientation": "ab",
                "ndcg_at_k": 0.90,
                "utility": 0.90 - 0.01 * 8,
                "n_calls": 8,
                "prior_kendall_tau": 0.5,
                "prior_topk_jaccard": 1.0,
                "prior_topk_jaccard_informative": False,
            }
        )
        # Slightly worse nDCG, far fewer calls → higher utility, no CI quality win.
        for pol, ndcg, calls in (
            ("HYBRID", 0.85, 1),
            ("CHALLENGER", 0.84, 1),
            ("ROBUST_COMBINED", 0.84, 1),
        ):
            rows.append(
                {
                    "policy": pol,
                    "budget": 8,
                    "query_id": qid,
                    "provider": "azure",
                    "prompt_version": "v",
                    "orientation": "ab",
                    "ndcg_at_k": ndcg,
                    "utility": ndcg - 0.01 * calls,
                    "n_calls": calls,
                    "prior_kendall_tau": 0.4,
                    "prior_topk_jaccard": 1.0,
                    "prior_topk_jaccard_informative": False,
                }
            )
    table = build_policy_comparison_table(
        rows,
        baseline_policy="production_uht",
        policies=("production_uht", "CHALLENGER", "HYBRID", "ROBUST_COMBINED"),
        budgets=(8,),
    )
    verdict = render_verdict(table, min_query_units=10)
    assert "COST-ONLY" in verdict["verdict"] or "ESTABLISHED" in verdict["verdict"]
    assert "ACTIONABLE CRITERION FOUND" not in verdict["verdict"]


def test_verdict_interval_crossing_zero_is_not_equality_claim():
    rows = []
    for i, qid in enumerate([f"q{j}" for j in range(12)]):
        delta = 0.01 if i % 2 == 0 else -0.01
        rows.append(
            {
                "policy": "production_uht",
                "budget": 8,
                "query_id": qid,
                "provider": "azure",
                "prompt_version": "v",
                "orientation": "ab",
                "ndcg_at_k": 0.80,
                "utility": 0.70,
                "n_calls": 8,
                "prior_kendall_tau": 0.5,
                "prior_topk_jaccard": 1.0,
                "prior_topk_jaccard_informative": False,
            }
        )
        for pol in ("CHALLENGER", "HYBRID", "ROBUST_COMBINED"):
            rows.append(
                {
                    "policy": pol,
                    "budget": 8,
                    "query_id": qid,
                    "provider": "azure",
                    "prompt_version": "v",
                    "orientation": "ab",
                    "ndcg_at_k": 0.80 + delta,
                    "utility": 0.70 + delta,
                    "n_calls": 8,
                    "prior_kendall_tau": 0.5,
                    "prior_topk_jaccard": 1.0,
                    "prior_topk_jaccard_informative": False,
                }
            )
    table = build_policy_comparison_table(
        rows,
        baseline_policy="production_uht",
        policies=("production_uht", "CHALLENGER", "HYBRID", "ROBUST_COMBINED"),
        budgets=(8,),
    )
    hybrid = next(r for r in table if r["policy"] == "HYBRID")
    assert hybrid["quality_ci_excludes_zero_positive"] is False
    verdict = render_verdict(table, min_query_units=10)
    reason = verdict["reason"].lower()
    assert "does not assert" in reason or "inconclusive" in reason
    assert "equal quality" not in verdict["verdict"].lower()
