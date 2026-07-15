from __future__ import annotations

import networkx as nx
import pytest

from consistency_ranker.cycle_detection import has_cycle
from consistency_ranker.exact_fas import exact_fas, exact_fas_objective
from consistency_ranker.graph_construction import build_graph, graph_summary
from consistency_ranker.mwfas_solver import available_methods, solve
from consistency_ranker.pairwise_prefs import Preference


def test_build_graph_supports_builtin_aggregations():
    prefs = [
        Preference("a", "b", 1.0),
        Preference("a", "b", 3.0),
        Preference("b", "c", 2.0),
    ]
    g_sum = build_graph(prefs, aggregation="sum")
    g_mean = build_graph(prefs, aggregation="mean")
    g_max = build_graph(prefs, aggregation="max")

    assert g_sum["a"]["b"]["weight"] == pytest.approx(4.0)
    assert g_mean["a"]["b"]["weight"] == pytest.approx(2.0)
    assert g_max["a"]["b"]["weight"] == pytest.approx(3.0)


def test_build_graph_supports_callable_aggregation():
    prefs = [
        Preference("a", "b", 1.0),
        Preference("a", "b", 3.0),
    ]
    g = build_graph(prefs, aggregation=lambda ws: min(ws))
    assert g["a"]["b"]["weight"] == pytest.approx(1.0)


def test_build_graph_unknown_aggregation_raises():
    with pytest.raises(ValueError):
        build_graph([Preference("a", "b", 1.0)], aggregation="median")


def test_graph_summary_reports_expected_fields():
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=2.0)
    g.add_edge("b", "c", weight=1.0)
    s = graph_summary(g)
    assert s["n_nodes"] == 3
    assert s["n_edges"] == 2
    assert s["is_dag"] is True
    assert s["total_weight"] == pytest.approx(3.0)
    assert s["n_sccs"] == 3


def test_exact_fas_removes_lightest_cycle_edge():
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=5.0)
    g.add_edge("b", "c", weight=5.0)
    g.add_edge("c", "a", weight=0.5)

    dag, removed, obj = exact_fas(g, max_n=5)

    assert not has_cycle(dag)
    assert obj == pytest.approx(0.5)
    assert removed == [("c", "a", 0.5)]
    assert exact_fas_objective(g) == pytest.approx(0.5)


def test_exact_fas_raises_when_graph_too_large():
    g = nx.DiGraph()
    for i in range(5):
        g.add_node(str(i))
    with pytest.raises(ValueError):
        exact_fas(g, max_n=4)


def test_mwfas_solver_dispatch_and_errors():
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=1.0)
    g.add_edge("b", "a", weight=0.5)

    dag, removed = solve(g, method="greedy")
    assert not has_cycle(dag)
    assert removed

    try:
        dag_ilp, removed_ilp = solve(g, method="ilp")
    except ImportError:
        pass  # PySCIPOpt not installed (method="ilp" is an alias for the open-source SCIP backend)
    else:
        assert not has_cycle(dag_ilp)
        assert removed_ilp
    with pytest.raises(ValueError):
        solve(g, method="unknown")


def test_available_methods_includes_greedy():
    methods = available_methods()
    assert "greedy" in methods


def test_metric_aware_reweight_keeps_same_nodes_and_edge_set():
    from consistency_ranker.metric_aware_repair import reweight_graph_for_metric_aware_fas

    g = nx.DiGraph()
    g.add_edge("x", "y", weight=1.0)
    g.add_edge("y", "z", weight=2.0)
    gr = reweight_graph_for_metric_aware_fas(
        g,
        prior_scores={"x": 1.0, "y": 0.5, "z": 0.0},
        gain_source="prior_score",
        beta=0.5,
    )
    assert set(gr.nodes()) == set(g.nodes())
    assert set(gr.edges()) == set(g.edges())

