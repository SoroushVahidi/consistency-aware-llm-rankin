"""
Tests for the unified MWFAS solver interface.
"""

from __future__ import annotations

import networkx as nx
import pytest

from consistency_ranker.exact_fas import exact_fas
from consistency_ranker.mwfas_solver import available_methods, solve


def _has_gurobi() -> bool:
    try:
        import gurobipy  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.mark.skipif(not _has_gurobi(), reason="gurobipy not installed")
class TestMwfasIlp:
    def test_triangle_removes_weakest_edge(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=5.0)
        g.add_edge("b", "c", weight=4.0)
        g.add_edge("c", "a", weight=0.25)

        dag, removed = solve(g, method="ilp")

        assert nx.is_directed_acyclic_graph(dag)
        assert removed == [("c", "a", 0.25)]

    def test_matches_bruteforce_exact_objective_on_small_graph(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=4.0)
        g.add_edge("b", "c", weight=3.0)
        g.add_edge("c", "a", weight=1.0)
        g.add_edge("c", "d", weight=2.0)
        g.add_edge("d", "b", weight=0.5)

        ilp_dag, ilp_removed = solve(g, method="ilp")
        brute_dag, brute_removed, brute_obj = exact_fas(g)

        assert nx.is_directed_acyclic_graph(ilp_dag)
        assert nx.is_directed_acyclic_graph(brute_dag)
        assert sum(weight for _, _, weight in ilp_removed) == pytest.approx(brute_obj)
        assert len(ilp_removed) == len(brute_removed)


def test_available_methods_reports_ilp_when_gurobi_present():
    methods = available_methods()
    assert "greedy" in methods
    if _has_gurobi():
        assert "ilp" in methods
