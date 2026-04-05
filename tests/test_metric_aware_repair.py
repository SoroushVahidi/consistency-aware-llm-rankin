"""Tests for metric-aware FAS edge reweighting (training-free surrogate)."""

from __future__ import annotations

import networkx as nx
import pytest

from consistency_ranker.greedy_fas import greedy_fas
from consistency_ranker.metric_aware_repair import (
    estimate_pair_swap_utility,
    gain_from_relevance_proxy,
    metric_aware_edge_weights,
    reweight_graph_for_metric_aware_fas,
)


def test_utility_larger_for_head_than_tail():
    g1 = gain_from_relevance_proxy(1.0)
    g0 = gain_from_relevance_proxy(0.0)
    u_head = estimate_pair_swap_utility(1, 2, g1, g0, focus_top_k=None)
    u_tail = estimate_pair_swap_utility(20, 21, g1, g0, focus_top_k=None)
    assert u_head > u_tail


def test_utility_near_zero_when_gains_and_positions_match():
    g = gain_from_relevance_proxy(0.5)
    u = estimate_pair_swap_utility(3, 3, g, g, focus_top_k=None)
    assert u == pytest.approx(0.0)


def test_focus_top_k_downweights_tail():
    g1 = gain_from_relevance_proxy(1.0)
    g0 = gain_from_relevance_proxy(0.0)
    u_in = estimate_pair_swap_utility(2, 3, g1, g0, focus_top_k=5, tail_scale=0.05)
    u_out = estimate_pair_swap_utility(8, 9, g1, g0, focus_top_k=5, tail_scale=0.05)
    assert u_in > u_out


def test_reweighting_preserves_edges_and_is_deterministic():
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=2.0)
    g.add_edge("b", "c", weight=1.0)
    prior = {"a": 3.0, "b": 1.0, "c": 0.0}
    r1 = reweight_graph_for_metric_aware_fas(
        g, prior_scores=prior, gain_source="prior_score", beta=1.0
    )
    r2 = reweight_graph_for_metric_aware_fas(
        g, prior_scores=prior, gain_source="prior_score", beta=1.0
    )
    assert set(r1.edges()) == set(g.edges())
    for u, v in g.edges():
        assert r1[u][v]["weight"] == pytest.approx(r2[u][v]["weight"])
        assert r1[u][v]["weight"] >= r1[u][v]["weight_plain"]


def test_beta_zero_leaves_weights_equal_to_confidence():
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=2.5)
    w = metric_aware_edge_weights(
        g,
        prior_scores={"a": 1.0, "b": 0.0},
        gain_source="prior_score",
        beta=0.0,
    )
    assert w[("a", "b")] == pytest.approx(2.5)


def test_beta_zero_reweight_same_greedy_fas_removed_edges():
    """β=0 ⇒ w_new = w_conf; greedy FAS should match the plain-weight graph."""
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=10.0)
    g.add_edge("b", "c", weight=10.0)
    g.add_edge("c", "a", weight=1.0)
    prior = {"a": 1.0, "b": 0.5, "c": 0.0}
    gr = reweight_graph_for_metric_aware_fas(
        g,
        prior_scores=prior,
        gain_source="prior_score",
        beta=0.0,
        focus_top_k=20,
    )
    _d1, removed_plain = greedy_fas(g)
    _d2, removed_ma = greedy_fas(gr)
    assert removed_ma == removed_plain


def test_metric_aware_reweight_changes_removed_edge_weight():
    """Same broken edge may be removed but with reweighted cost (objective differs)."""
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=10.0)
    g.add_edge("b", "c", weight=10.0)
    g.add_edge("c", "a", weight=1.0)
    _, removed_plain = greedy_fas(g)
    assert removed_plain[0][:2] == ("c", "a")

    prior = {"a": 100.0, "b": 50.0, "c": 0.0}
    gr = reweight_graph_for_metric_aware_fas(
        g, prior_scores=prior, gain_source="prior_score", beta=5.0, focus_top_k=3
    )
    _, removed_ma = greedy_fas(gr)
    assert removed_ma[0][:2] == ("c", "a")
    assert removed_ma[0][2] > removed_plain[0][2]
