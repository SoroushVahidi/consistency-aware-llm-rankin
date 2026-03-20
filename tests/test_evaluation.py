"""
Tests for evaluation metrics.
"""

from __future__ import annotations

import networkx as nx
import pytest

from consistency_ranker.evaluation import (
    kendall_tau,
    n_violations,
    pairwise_inconsistency_count,
    ranking_agreement,
)


class TestKendallTau:
    def test_perfect_agreement(self):
        ranking = ["a", "b", "c", "d"]
        assert kendall_tau(ranking, ranking) == pytest.approx(1.0)

    def test_perfect_disagreement(self):
        ranking = ["a", "b", "c", "d"]
        reverse = list(reversed(ranking))
        tau = kendall_tau(reverse, ranking)
        assert tau == pytest.approx(-1.0)

    def test_partial_agreement(self):
        # reference: a b c d  → pairs: (a,b),(a,c),(a,d),(b,c),(b,d),(c,d) all concordant=6
        # predicted: a c b d  → (a,c) concordant, (a,b) concordant, (c,b) discordant
        reference = ["a", "b", "c", "d"]
        predicted = ["a", "c", "b", "d"]
        tau = kendall_tau(predicted, reference)
        # 5 concordant, 1 discordant → (5-1)/6 = 4/6 ≈ 0.667
        assert tau == pytest.approx(4 / 6, abs=1e-6)

    def test_single_item_returns_zero(self):
        assert kendall_tau(["a"], ["a"]) == 0.0

    def test_raises_on_different_items(self):
        with pytest.raises(ValueError):
            kendall_tau(["a", "b"], ["a", "c"])


class TestRankingAgreement:
    def test_perfect_agreement_gives_one(self):
        ranking = ["a", "b", "c"]
        assert ranking_agreement(ranking, ranking) == pytest.approx(1.0)

    def test_perfect_disagreement_gives_zero(self):
        ranking = ["a", "b", "c"]
        reverse = list(reversed(ranking))
        assert ranking_agreement(reverse, ranking) == pytest.approx(0.0)


class TestNViolations:
    def test_no_violations(self):
        ranking = ["a", "b", "c"]
        assert n_violations(ranking, ranking) == 0

    def test_all_violations(self):
        ranking = ["a", "b", "c"]
        reverse = list(reversed(ranking))
        # 3 pairs, all discordant
        assert n_violations(reverse, ranking) == 3

    def test_one_violation(self):
        reference = ["a", "b", "c"]
        predicted = ["a", "c", "b"]  # only (b,c) is flipped
        assert n_violations(predicted, reference) == 1


class TestPairwiseInconsistencyCount:
    def test_consistent_graph(self):
        # reference: a > b > c
        ref = ["a", "b", "c"]
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c"), ("a", "c")])
        assert pairwise_inconsistency_count(g, ref) == 0

    def test_all_inconsistent(self):
        # reference: a > b > c  but graph has all reversed edges
        ref = ["a", "b", "c"]
        g = nx.DiGraph()
        g.add_edges_from([("b", "a"), ("c", "b"), ("c", "a")])
        assert pairwise_inconsistency_count(g, ref) == 3

    def test_partial_inconsistency(self):
        ref = ["a", "b", "c"]
        g = nx.DiGraph()
        # a→b is consistent; c→a is inconsistent
        g.add_edges_from([("a", "b"), ("c", "a")])
        assert pairwise_inconsistency_count(g, ref) == 1
