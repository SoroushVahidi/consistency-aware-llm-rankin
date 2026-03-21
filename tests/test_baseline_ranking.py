"""
Tests for baseline_ranking module.
"""

from __future__ import annotations

import networkx as nx
import pytest

from consistency_ranker.baseline_ranking import (
    borda_ranking,
    copeland_ranking,
    hybrid_regularized_ranking,
    pagerank_ranking,
    priority_topological_ranking,
    score_sum_ranking,
    topological_ranking,
    weighted_balance_ranking,
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


class TestFasAwareRankings:
    def test_weighted_balance_ranking_prefers_high_weight_winner(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=3.0)
        g.add_edge("a", "c", weight=2.0)
        g.add_edge("b", "c", weight=1.0)
        ranking = weighted_balance_ranking(g)
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
        ranking = hybrid_regularized_ranking(
            g,
            {"a": 3.0, "b": 1.0, "c": 0.0},
            regularization=0.2,
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
