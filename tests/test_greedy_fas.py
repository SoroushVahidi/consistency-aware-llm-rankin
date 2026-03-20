"""
Tests for greedy_fas module.
"""

from __future__ import annotations

import networkx as nx
import pytest

from consistency_ranker.cycle_detection import has_cycle
from consistency_ranker.greedy_fas import greedy_fas, greedy_fas_total_weight


class TestGreedyFas:
    def test_dag_unchanged(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c")])
        dag, removed = greedy_fas(g)
        assert not has_cycle(dag)
        assert removed == []
        assert dag.number_of_edges() == g.number_of_edges()

    def test_triangle_becomes_dag(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0)
        g.add_edge("b", "c", weight=1.0)
        g.add_edge("c", "a", weight=1.0)
        dag, removed = greedy_fas(g)
        assert not has_cycle(dag)
        assert len(removed) == 1

    def test_minimum_weight_edge_removed(self):
        g = nx.DiGraph()
        # Triangle with one weak edge
        g.add_edge("a", "b", weight=10.0)
        g.add_edge("b", "c", weight=10.0)
        g.add_edge("c", "a", weight=0.5)  # weakest edge
        dag, removed = greedy_fas(g)
        assert not has_cycle(dag)
        # The weakest edge should be the one removed
        assert removed[0][0] == "c"
        assert removed[0][1] == "a"

    def test_original_graph_not_modified(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0)
        g.add_edge("b", "a", weight=1.0)
        original_edges = set(g.edges())
        greedy_fas(g)
        assert set(g.edges()) == original_edges


class TestGreedyFasTotalWeight:
    def test_empty_removed(self):
        assert greedy_fas_total_weight([]) == 0.0

    def test_sum_of_weights(self):
        removed = [("a", "b", 1.5), ("c", "d", 2.5)]
        assert greedy_fas_total_weight(removed) == pytest.approx(4.0)
