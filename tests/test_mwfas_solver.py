"""
Tests for the unified MWFAS solver interface.

The exact "ilp"/"exact"/"scip" methods are backed by the free, open-source
PySCIPOpt/SCIP solver by default (see `consistency_ranker.mwfas_solver`);
Gurobi is an explicitly optional legacy backend selected only via
`method="gurobi"` and is not required for any test here.
"""

from __future__ import annotations

import networkx as nx
import pytest

from consistency_ranker.exact_fas import exact_fas
from consistency_ranker.metric_aware_repair import reweight_graph_for_metric_aware_fas
from consistency_ranker.mwfas_solver import (
    available_methods,
    is_gurobi_available,
    is_scip_available,
    solve,
)


@pytest.mark.skipif(not is_scip_available(), reason="PySCIPOpt not installed")
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


@pytest.mark.skipif(
    not is_gurobi_available(), reason="gurobipy not installed (optional legacy backend)"
)
def test_legacy_gurobi_backend_matches_scip_objective():
    """The optional, never-required Gurobi backend must solve the identical
    MIP and therefore reach the same objective as the canonical SCIP backend."""
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=5.0)
    g.add_edge("b", "c", weight=4.0)
    g.add_edge("c", "a", weight=0.25)
    dag, removed = solve(g, method="gurobi")
    assert nx.is_directed_acyclic_graph(dag)
    assert removed == [("c", "a", 0.25)]


def test_available_methods_reports_scip_family_when_pyscipopt_present():
    methods = available_methods()
    assert "greedy" in methods
    if is_scip_available():
        assert "scip" in methods
        assert "exact" in methods
        assert "ilp" in methods
    if is_gurobi_available():
        assert "gurobi" in methods


def test_solve_greedy_on_metric_reweighted_graph():
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=1.0)
    g.add_edge("b", "a", weight=1.0)
    gr = reweight_graph_for_metric_aware_fas(
        g,
        prior_scores={"a": 1.0, "b": 0.0},
        gain_source="prior_score",
        beta=2.0,
    )
    dag, removed = solve(gr, method="greedy")
    assert not nx.is_directed_acyclic_graph(g)
    assert nx.is_directed_acyclic_graph(dag)
    assert removed
