"""
Tests for cycle_detection module.
"""

from __future__ import annotations

import networkx as nx
import pytest

from consistency_ranker.cycle_detection import (
    count_cycles,
    cycle_edge_set,
    cycle_summary,
    find_simple_cycles,
    has_cycle,
    nodes_in_cycles,
)


class TestHasCycle:
    def test_acyclic_graph_returns_false(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c"), ("a", "c")])
        assert has_cycle(g) is False

    def test_cyclic_graph_returns_true(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c"), ("c", "a")])
        assert has_cycle(g) is True

    def test_self_loop_returns_true(self):
        g = nx.DiGraph()
        g.add_edge("x", "x")
        assert has_cycle(g) is True

    def test_empty_graph_returns_false(self):
        g = nx.DiGraph()
        assert has_cycle(g) is False


class TestFindSimpleCycles:
    def test_no_cycles(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c")])
        assert find_simple_cycles(g) == []

    def test_single_triangle_cycle(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c"), ("c", "a")])
        cycles = find_simple_cycles(g)
        assert len(cycles) == 1
        assert len(cycles[0]) == 3

    def test_two_independent_cycles(self):
        g = nx.DiGraph()
        # Cycle 1: a→b→a
        g.add_edges_from([("a", "b"), ("b", "a")])
        # Cycle 2: c→d→c
        g.add_edges_from([("c", "d"), ("d", "c")])
        cycles = find_simple_cycles(g)
        assert len(cycles) == 2


class TestCountCycles:
    def test_dag_has_zero_cycles(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c"), ("c", "d")])
        assert count_cycles(g) == 0

    def test_single_cycle(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c"), ("c", "a")])
        assert count_cycles(g) == 1


class TestNodesInCycles:
    def test_all_nodes_in_triangle(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c"), ("c", "a")])
        assert nodes_in_cycles(g) == {"a", "b", "c"}

    def test_some_nodes_not_in_cycles(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c"), ("c", "a"), ("c", "d")])
        # d is not part of the cycle
        in_cycles = nodes_in_cycles(g)
        assert "d" not in in_cycles
        assert {"a", "b", "c"}.issubset(in_cycles)


class TestCycleEdgeSet:
    def test_triangle_edges(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c"), ("c", "a")])
        edges = cycle_edge_set(g)
        assert ("a", "b") in edges
        assert ("b", "c") in edges
        assert ("c", "a") in edges

    def test_dag_has_no_cycle_edges(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c")])
        assert cycle_edge_set(g) == set()


class TestCycleSummary:
    def test_summary_keys(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c"), ("c", "a")])
        s = cycle_summary(g)
        assert "n_cycles" in s
        assert "n_nodes_in_cycles" in s
        assert "n_edges_in_cycles" in s

    def test_summary_values_triangle(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c"), ("c", "a")])
        s = cycle_summary(g)
        assert s["n_cycles"] == 1
        assert s["n_nodes_in_cycles"] == 3
        assert s["n_edges_in_cycles"] == 3
