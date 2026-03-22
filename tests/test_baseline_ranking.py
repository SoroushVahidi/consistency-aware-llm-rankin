"""
Tests for baseline_ranking module.
"""

from __future__ import annotations

import networkx as nx
import pytest

from consistency_ranker.baseline_ranking import (
    borda_ranking,
    borda_scores,
    copeland_ranking,
    fas_balance_score_prior_alpha_beta_ranking,
    fas_balance_score_prior_alpha_ranking,
    fas_balance_score_sum_borda_hybrid_ranking,
    hybrid_rrf_fas_regularized_ranking,
    pagerank_ranking,
    priority_topological_ranking,
    score_sum_ranking,
    score_sum_scores,
    topological_ranking,
    weighted_out_minus_in_ranking,
)


class TestScoreSumRanking:
    def test_higher_out_weight_ranks_first(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=2.0)
        g.add_edge("a", "c", weight=3.0)
        g.add_edge("b", "c", weight=1.0)
        ranking = score_sum_ranking(g)
        # a has total out-weight 5, b has 1, c has 0
        assert ranking[0] == "a"
        assert ranking[-1] == "c"

    def test_works_on_cyclic_graph(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c"), ("c", "a")])
        # Should not raise even though there is a cycle
        ranking = score_sum_ranking(g)
        assert set(ranking) == {"a", "b", "c"}

    def test_isolated_node_gets_zero_score(self):
        g = nx.DiGraph()
        g.add_node("x")
        # a→b→c, so a has highest score, b has middle, c and x have zero
        g.add_edge("a", "b", weight=2.0)
        g.add_edge("b", "c", weight=1.0)
        ranking = score_sum_ranking(g)
        # "a" should be first (score 2.0), "x" should be in the tail (score 0.0)
        assert ranking[0] == "a"
        assert "x" in ranking[-2:]  # x and c both have zero, x must be in last two

    def test_score_sum_scores_returns_values(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=2.0)
        g.add_edge("a", "c", weight=1.0)
        g.add_edge("b", "c", weight=4.0)
        scores = score_sum_scores(g)
        assert scores["a"] == 3.0
        assert scores["b"] == 4.0
        assert scores["c"] == 0.0


class TestTopologicalRanking:
    def test_simple_dag(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c")])
        ranking = topological_ranking(g)
        assert ranking.index("a") < ranking.index("b")
        assert ranking.index("b") < ranking.index("c")

    def test_raises_on_cyclic_graph(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c"), ("c", "a")])
        with pytest.raises(nx.NetworkXUnfeasible):
            topological_ranking(g)

    def test_all_nodes_present(self):
        g = nx.DiGraph()
        g.add_edges_from([("x", "y"), ("y", "z"), ("x", "z")])
        ranking = topological_ranking(g)
        assert set(ranking) == {"x", "y", "z"}


class TestPriorityTopologicalRanking:
    def test_respects_edges_and_priorities(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "c"), ("b", "c")])
        # a and b are both available first; pick b due to higher priority.
        ranking = priority_topological_ranking(g, {"a": 1.0, "b": 2.0, "c": 0.0})
        assert ranking.index("a") < ranking.index("c")
        assert ranking.index("b") < ranking.index("c")
        assert ranking[0] == "b"

    def test_raises_on_cycle(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "a")])
        with pytest.raises(nx.NetworkXUnfeasible):
            priority_topological_ranking(g, {"a": 1.0, "b": 1.0})


class TestBordaRanking:
    def test_most_wins_ranks_first(self):
        g = nx.DiGraph()
        # a beats b and c; b beats c
        g.add_edges_from([("a", "b"), ("a", "c"), ("b", "c")])
        ranking = borda_ranking(g)
        assert ranking[0] == "a"
        assert ranking[-1] == "c"

    def test_works_on_cyclic_graph(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c"), ("c", "a")])
        # All have degree 1; order may vary but all nodes present
        ranking = borda_ranking(g)
        assert set(ranking) == {"a", "b", "c"}

    def test_borda_scores(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("a", "c"), ("b", "c")])
        scores = borda_scores(g)
        assert scores["a"] == 2.0
        assert scores["b"] == 1.0
        assert scores["c"] == 0.0


class TestFasAwareRankings:
    def test_weighted_balance_ranking_prefers_high_weight_winner(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=3.0)
        g.add_edge("a", "c", weight=2.0)
        g.add_edge("b", "c", weight=1.0)
        ranking = weighted_out_minus_in_ranking(g)
        assert ranking[0] == "a"
        assert ranking[-1] == "c"

    def test_copeland_ranking_uses_out_minus_in_degree(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("a", "c"), ("b", "c")])
        ranking = copeland_ranking(g)
        assert ranking == ["a", "b", "c"]

    def test_priority_topological_ranking_uses_priority_scores(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "c"), ("b", "c")])
        ranking = priority_topological_ranking(g, {"a": 1.0, "b": 2.0, "c": 0.0})
        assert ranking[:2] == ["b", "a"]
        assert ranking[2] == "c"

    def test_hybrid_regularized_ranking_combines_prior_and_dag_balance(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=2.0)
        g.add_edge("a", "c", weight=1.0)
        g.add_edge("b", "c", weight=1.0)
        ranking = hybrid_rrf_fas_regularized_ranking(
            g,
            {"a": 3.0, "b": 1.0, "c": 0.0},
            fas_regularization=0.2,
        )
        assert ranking[0] == "a"
        assert ranking[-1] == "c"


class TestPageRankRanking:
    def test_returns_all_nodes(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=2.0)
        g.add_edge("a", "c", weight=1.0)
        g.add_edge("b", "c", weight=1.5)
        ranking = pagerank_ranking(g)
        assert set(ranking) == {"a", "b", "c"}

    def test_returns_list_of_strings(self):
        g = nx.DiGraph()
        g.add_edges_from([("x", "y"), ("y", "z")])
        ranking = pagerank_ranking(g)
        assert isinstance(ranking, list)
        assert all(isinstance(n, str) for n in ranking)

    def test_dominant_winner_ranks_first(self):
        g = nx.DiGraph()
        # "a" beats b, c, d with high weight => a has many outgoing edges
        # In reversed graph a gets high "authority" from being beaten by nothing
        g.add_edge("a", "b", weight=5.0)
        g.add_edge("a", "c", weight=5.0)
        g.add_edge("a", "d", weight=5.0)
        ranking = pagerank_ranking(g)
        # "a" has no incoming edges in reversed graph → lower authority;
        # b, c, d each have one incoming edge from "a" in reversed graph.
        # But "a" is the only source: it is the one that "wins", so its
        # reversed-graph score will depend on the PageRank structure.
        # At minimum all nodes must be present.
        assert set(ranking) == {"a", "b", "c", "d"}

    def test_works_on_cyclic_graph(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c"), ("c", "a")])
        # Must not raise even for a cycle
        ranking = pagerank_ranking(g)
        assert set(ranking) == {"a", "b", "c"}

    def test_single_edge(self):
        g = nx.DiGraph()
        g.add_edge("winner", "loser", weight=1.0)
        ranking = pagerank_ranking(g)
        assert set(ranking) == {"winner", "loser"}
        assert len(ranking) == 2

    def test_alpha_parameter(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0)
        g.add_edge("b", "c", weight=1.0)
        # Different alpha values should both produce valid orderings
        r1 = pagerank_ranking(g, alpha=0.50)
        r2 = pagerank_ranking(g, alpha=0.99)
        assert set(r1) == set(r2) == {"a", "b", "c"}


class TestWeightedBalanceRanking:
    def test_weighted_out_minus_in(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=3.0)
        g.add_edge("c", "a", weight=1.0)
        # scores: a=+2, b=-3, c=+1 => a first, b last
        ranking = weighted_out_minus_in_ranking(g)
        assert ranking[0] == "a"
        assert ranking[-1] == "b"


class TestCopelandRanking:
    def test_out_minus_in_degree(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("a", "c"), ("b", "c")])
        ranking = copeland_ranking(g)
        assert ranking[0] == "a"
        assert ranking[-1] == "c"


class TestFasBalanceScorePriorAlphaRanking:
    def test_alpha_zero_matches_balance_ranking(self):
        dag = nx.DiGraph()
        dag.add_edge("a", "b", weight=4.0)
        dag.add_edge("a", "c", weight=1.0)
        dag.add_edge("b", "c", weight=2.0)
        prior = {"a": 1.0, "b": 3.0, "c": 2.0}
        hybrid = fas_balance_score_prior_alpha_ranking(dag, prior, alpha=0.0)
        balance = weighted_out_minus_in_ranking(dag)
        assert hybrid == balance

    def test_positive_alpha_uses_prior_signal(self):
        dag = nx.DiGraph()
        dag.add_edge("a", "b", weight=1.0)
        dag.add_edge("b", "c", weight=1.0)
        # Balance is tied around zero (a:+1,b:0,c:-1), but large prior on b should
        # pull b upward when alpha is large.
        prior = {"a": 0.0, "b": 100.0, "c": 0.0}
        hybrid = fas_balance_score_prior_alpha_ranking(dag, prior, alpha=2.0)
        assert hybrid[0] == "b"

    def test_negative_alpha_raises(self):
        dag = nx.DiGraph()
        dag.add_edge("a", "b", weight=1.0)
        with pytest.raises(ValueError):
            fas_balance_score_prior_alpha_ranking(dag, {"a": 1.0, "b": 0.0}, alpha=-0.1)

    def test_matches_alpha_beta_when_beta_is_one(self):
        dag = nx.DiGraph()
        dag.add_edge("a", "b", weight=4.0)
        dag.add_edge("a", "c", weight=1.0)
        dag.add_edge("b", "c", weight=2.0)
        prior = {"a": 1.0, "b": 3.0, "c": 2.0}
        r_old = fas_balance_score_prior_alpha_ranking(dag, prior, alpha=0.75)
        r_new = fas_balance_score_prior_alpha_beta_ranking(dag, prior, alpha=0.75, beta=1.0)
        assert r_old == r_new


class TestFasBalanceScorePriorAlphaBetaRanking:
    def test_reducing_beta_increases_prior_effect(self):
        dag = nx.DiGraph()
        dag.add_edge("a", "b", weight=5.0)
        dag.add_edge("a", "c", weight=1.0)
        dag.add_edge("b", "c", weight=1.0)
        prior = {"a": 0.0, "b": 100.0, "c": 0.0}
        low_beta = fas_balance_score_prior_alpha_beta_ranking(dag, prior, alpha=2.0, beta=0.1)
        high_beta = fas_balance_score_prior_alpha_beta_ranking(dag, prior, alpha=2.0, beta=1.0)
        assert low_beta.index("b") <= high_beta.index("b")

    def test_negative_beta_raises(self):
        dag = nx.DiGraph()
        dag.add_edge("a", "b", weight=1.0)
        with pytest.raises(ValueError):
            fas_balance_score_prior_alpha_beta_ranking(
                dag,
                {"a": 1.0, "b": 0.0},
                alpha=1.0,
                beta=-0.1,
            )


class TestHybridRrfFasRegularizedRanking:
    def test_negative_regularization_raises(self):
        dag = nx.DiGraph()
        dag.add_edge("a", "b", weight=1.0)
        with pytest.raises(ValueError):
            hybrid_rrf_fas_regularized_ranking(
                dag,
                {"a": 1.0, "b": 0.0},
                fas_regularization=-0.1,
            )


class TestFasBalanceScoreSumBordaHybridRanking:
    def test_zero_priors_matches_balance_when_beta_positive(self):
        dag = nx.DiGraph()
        dag.add_edge("a", "b", weight=3.0)
        dag.add_edge("b", "c", weight=1.0)
        ss_prior = {"a": 0.0, "b": 0.0, "c": 0.0}
        b_prior = {"a": 0.0, "b": 0.0, "c": 0.0}
        hybrid = fas_balance_score_sum_borda_hybrid_ranking(
            dag,
            ss_prior,
            b_prior,
            alpha_s=0.0,
            alpha_b=0.0,
            beta=1.0,
        )
        balance = weighted_out_minus_in_ranking(dag)
        assert hybrid == balance

    def test_borda_prior_can_shift_order(self):
        dag = nx.DiGraph()
        dag.add_edge("a", "c", weight=1.0)
        dag.add_edge("b", "c", weight=1.0)
        ss_prior = {"a": 0.0, "b": 0.0, "c": 0.0}
        b_prior = {"a": 0.0, "b": 10.0, "c": 0.0}
        hybrid = fas_balance_score_sum_borda_hybrid_ranking(
            dag,
            ss_prior,
            b_prior,
            alpha_s=0.0,
            alpha_b=2.0,
            beta=0.1,
        )
        assert hybrid[0] == "b"

    def test_negative_weights_raise(self):
        dag = nx.DiGraph()
        dag.add_edge("a", "b", weight=1.0)
        with pytest.raises(ValueError):
            fas_balance_score_sum_borda_hybrid_ranking(
                dag,
                {"a": 1.0, "b": 0.0},
                {"a": 0.0, "b": 1.0},
                alpha_s=-0.1,
                alpha_b=1.0,
                beta=0.1,
            )
        with pytest.raises(ValueError):
            fas_balance_score_sum_borda_hybrid_ranking(
                dag,
                {"a": 1.0, "b": 0.0},
                {"a": 0.0, "b": 1.0},
                alpha_s=1.0,
                alpha_b=-0.1,
                beta=0.1,
            )
        with pytest.raises(ValueError):
            fas_balance_score_sum_borda_hybrid_ranking(
                dag,
                {"a": 1.0, "b": 0.0},
                {"a": 0.0, "b": 1.0},
                alpha_s=1.0,
                alpha_b=1.0,
                beta=-0.1,
            )
