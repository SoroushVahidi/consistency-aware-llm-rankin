"""Unit tests for reliability-aware graph construction and repair."""

from __future__ import annotations

import networkx as nx
import pytest

from consistency_ranker.reliability_repair.edge_reliability import (
    estimate_reliability,
    reliability_entropy,
)
from consistency_ranker.reliability_repair.evidence_aggregation import aggregate_pair
from consistency_ranker.reliability_repair.local_contradiction import (
    resolve_local_contradiction,
)
from consistency_ranker.reliability_repair.pair_evidence import (
    canonical_pair_id,
    normalize_judgment_record,
    preference_from_simple,
)
from consistency_ranker.reliability_repair.pipeline import (
    ReliabilityRepairConfig,
    run_reliability_pipeline,
)
from consistency_ranker.reliability_repair.reliability_weighted_repair import (
    apply_cost_scheme,
    exact_fas_with_costs,
    greedy_fas_with_costs,
)
from consistency_ranker.reliability_repair.selective_graph import (
    decide_edge,
)
from consistency_ranker.reliability_repair.synthetic_judgment_models import (
    SyntheticConfig,
    generate_synthetic_judgments,
)


class TestNormalization:
    def test_canonical_order(self):
        assert canonical_pair_id("q", "b", "a") == "q::a::b"

    def test_invalid_not_forced_to_winner(self):
        e = normalize_judgment_record(
            {
                "query_id": "q",
                "doc_a_id": "a",
                "doc_b_id": "b",
                "parsed_choice": "INVALID",
                "normalized_winner_id": None,
                "valid": False,
            }
        )
        assert e.z == 0
        assert e.abstention_subtype == "invalid"

    def test_orientation_maps_winner(self):
        e = normalize_judgment_record(
            {
                "query_id": "q",
                "doc_a_id": "b",
                "doc_b_id": "a",
                "normalized_winner_id": "b",
                "parsed_choice": "A",
                "valid": True,
                "displayed_orientation": "ab",
            }
        )
        # canonical i=a,j=b; winner b → z=-1
        assert e.doc_i == "a" and e.doc_j == "b"
        assert e.z == -1


class TestAggregationReliability:
    def test_smoothed_margin(self):
        ev = [
            preference_from_simple(query_id="q", winner="a", loser="b"),
            preference_from_simple(query_id="q", winner="a", loser="b"),
            preference_from_simple(query_id="q", winner="b", loser="a"),
        ]
        # Fix docs to same pair with orientations
        for e in ev:
            e.doc_i, e.doc_j = "a", "b"
            e.canonical_pair_id = "q::a::b"
        agg = aggregate_pair(ev, estimator="smoothed", alpha=1.0)
        assert agg.n_plus == 2 and agg.n_minus == 1
        assert agg.d == 1
        assert 0 < agg.p_hat < 1
        r = estimate_reliability(agg, method="margin")
        assert r == abs(agg.m)

    def test_entropy_extremes(self):
        ev = [preference_from_simple(query_id="q", winner="a", loser="b") for _ in range(5)]
        for e in ev:
            e.doc_i, e.doc_j = "a", "b"
            e.canonical_pair_id = "q::a::b"
        agg = aggregate_pair(ev, estimator="unweighted_majority")
        assert reliability_entropy(agg) == pytest.approx(1.0)


class TestSelectiveAndRepair:
    def test_one_edge_per_pair(self):
        ev = [
            preference_from_simple(query_id="q", winner="a", loser="b"),
            preference_from_simple(query_id="q", winner="b", loser="c"),
            preference_from_simple(query_id="q", winner="a", loser="c"),
        ]
        out = run_reliability_pipeline(
            ev,
            prior_scores={"a": 3, "b": 2, "c": 1},
            config=ReliabilityRepairConfig(abstention_policy="none", tau=0.0),
        )
        g = out["graph"]
        for u, v in g.edges():
            assert not g.has_edge(v, u)

    def test_threshold_abstains(self):
        e = preference_from_simple(query_id="q", winner="a", loser="b")
        e.doc_i, e.doc_j = "a", "b"
        e.canonical_pair_id = "q::a::b"
        # Single judgment with opposing → weak after another?
        e2 = preference_from_simple(query_id="q", winner="b", loser="a")
        e2.doc_i, e2.doc_j = "a", "b"
        e2.canonical_pair_id = "q::a::b"
        agg = aggregate_pair([e, e2], estimator="smoothed")
        dec = decide_edge(agg, reliability=0.05, policy="reliability_threshold", tau=0.2)
        assert not dec.keep

    def test_greedy_vs_exact_tiny(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0, removal_cost=1.0)
        g.add_edge("b", "c", weight=1.0, removal_cost=1.0)
        g.add_edge("c", "a", weight=5.0, removal_cost=5.0)  # expensive
        dg, rem_g, _ = greedy_fas_with_costs(g)
        de, rem_e, meta = exact_fas_with_costs(g)
        assert nx.is_directed_acyclic_graph(dg)
        assert nx.is_directed_acyclic_graph(de)
        assert meta["optimal"]
        # Optimal removes a cheap edge, not the cost-5 edge preferably
        assert meta["objective"] <= 1.0 + 1e-9

    def test_cost_schemes(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=2.0, reliability=0.5, importance=2.0)
        g2 = apply_cost_scheme(g, scheme="weight_x_reliability_x_importance")
        assert g2["a"]["b"]["removal_cost"] == pytest.approx(2.0)


class TestLocalContradiction:
    def test_majority_resolves(self):
        ev = [
            preference_from_simple(query_id="q", winner="a", loser="b"),
            preference_from_simple(query_id="q", winner="a", loser="b"),
            preference_from_simple(query_id="q", winner="b", loser="a"),
        ]
        for e in ev:
            e.doc_i, e.doc_j = "a", "b"
            e.canonical_pair_id = "q::a::b"
        agg = aggregate_pair(ev)
        res = resolve_local_contradiction(agg, policy="majority")
        assert res.resolution == "one_edge" and res.direction == 1


class TestSyntheticPipeline:
    def test_synthetic_runs(self):
        ev, meta = generate_synthetic_judgments(
            SyntheticConfig(n_items=5, n_models=2, n_prompts=1, repeats=1, seed=1)
        )
        assert len(ev) > 0
        true = meta["true_ranking"]
        prior = {d: float(len(true) - i) for i, d in enumerate(true)}
        out = run_reliability_pipeline(
            ev,
            prior_scores=prior,
            prior_ranking=meta["true_ranking"],
            config=ReliabilityRepairConfig(
                abstention_policy="reliability_threshold",
                tau=0.15,
                repair="greedy",
                n_stability_samples=8,
            ),
        )
        assert out["is_dag"]
        assert set(out["ranking"]) == set(meta["true_ranking"])
