"""
Strong test suite for the canonical open-source (SCIP/PySCIPOpt) exact MWFAS
backend in :mod:`consistency_ranker.mwfas_solver`.

Run just this file (skips cleanly if PySCIPOpt is not installed):

    pytest tests/test_exact_mwfas_scip.py -v

Run the full exact-solver suite with the optional dependency installed:

    pip install "consistency-ranker[exact]"
    pytest tests/test_exact_mwfas_scip.py -v -m ""   # (no special marker needed;
                                                       #  tests skip automatically
                                                       #  without PySCIPOpt)
"""

from __future__ import annotations

import itertools
import random

import networkx as nx
import pytest

from consistency_ranker.exact_fas import exact_fas
from consistency_ranker.greedy_fas import greedy_fas
from consistency_ranker.mwfas_solver import SolveStatus, is_scip_available, solve

pytestmark = pytest.mark.skipif(
    not is_scip_available(),
    reason="PySCIPOpt not installed; install with pip install 'consistency-ranker[exact]'",
)


def _weight_of(removed: list[tuple[str, str, float]]) -> float:
    return sum(w for _u, _v, w in removed)


def _random_weighted_digraph(
    rng: random.Random, n: int, p_edge: float, w_lo: float = 0.1, w_hi: float = 5.0
) -> nx.DiGraph:
    g = nx.DiGraph()
    nodes = [f"n{i}" for i in range(n)]
    g.add_nodes_from(nodes)
    for u, v in itertools.permutations(nodes, 2):
        if rng.random() < p_edge:
            g.add_edge(u, v, weight=round(rng.uniform(w_lo, w_hi), 3))
    return g


# ---------------------------------------------------------------------------
# Trivial graphs: solver must not be invoked, but the interface must still work.
# ---------------------------------------------------------------------------


def test_empty_graph():
    g = nx.DiGraph()
    dag, removed, status = solve(g, method="scip", return_status=True)
    assert removed == []
    assert nx.is_directed_acyclic_graph(dag)
    assert status.proven_optimal
    assert status.trivial
    assert status.objective == 0.0


def test_one_node_graph():
    g = nx.DiGraph()
    g.add_node("solo")
    dag, removed, status = solve(g, method="scip", return_status=True)
    assert removed == []
    assert list(dag.nodes()) == ["solo"]
    assert status.trivial


def test_dag_is_returned_unchanged():
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=2.0)
    g.add_edge("b", "c", weight=3.0)
    dag, removed, status = solve(g, method="scip", return_status=True)
    assert removed == []
    assert set(dag.edges()) == set(g.edges())
    assert status.trivial
    assert status.proven_optimal


# ---------------------------------------------------------------------------
# Small hand-constructed cases with known optimal answers.
# ---------------------------------------------------------------------------


def test_two_node_mutual_contradiction():
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=3.0)
    g.add_edge("b", "a", weight=1.0)
    dag, removed, status = solve(g, method="scip", return_status=True)
    assert nx.is_directed_acyclic_graph(dag)
    assert removed == [("b", "a", 1.0)]
    assert status.objective == pytest.approx(1.0)
    assert not status.trivial


def test_directed_triangle_removes_weakest_edge():
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=5.0)
    g.add_edge("b", "c", weight=4.0)
    g.add_edge("c", "a", weight=0.25)
    dag, removed = solve(g, method="scip")
    assert nx.is_directed_acyclic_graph(dag)
    assert removed == [("c", "a", 0.25)]


def test_exact_beats_greedy_when_locally_cheapest_edge_is_not_globally_optimal():
    """Two triangles sharing edge b->c: greedy processes one cycle at a time
    and removes a locally-cheap edge (d->b, weight 0.9) that only breaks one
    cycle, then must remove a second edge for the other cycle (total 1.9+).
    The exact solver recognizes that removing the single shared edge b->c
    (weight 1.0) breaks both cycles at once, which is the true optimum."""
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=1.0)
    g.add_edge("b", "c", weight=1.0)
    g.add_edge("c", "a", weight=1.0)
    g.add_edge("c", "d", weight=1.0)
    g.add_edge("d", "b", weight=0.9)

    _, greedy_removed = greedy_fas(g)
    dag, exact_removed, status = solve(g, method="scip", return_status=True)

    assert nx.is_directed_acyclic_graph(dag)
    assert exact_removed == [("b", "c", 1.0)]
    assert status.objective == pytest.approx(1.0)
    assert _weight_of(exact_removed) < _weight_of(greedy_removed)
    assert _weight_of(greedy_removed) == pytest.approx(1.9)


def test_disconnected_cyclic_components_solved_independently():
    g = nx.DiGraph()
    # Component 1: triangle, optimal removal = 0.5
    g.add_edge("a", "b", weight=5.0)
    g.add_edge("b", "c", weight=5.0)
    g.add_edge("c", "a", weight=0.5)
    # Component 2: disjoint triangle, optimal removal = 0.3
    g.add_edge("x", "y", weight=2.0)
    g.add_edge("y", "z", weight=2.0)
    g.add_edge("z", "x", weight=0.3)

    dag, removed, status = solve(g, method="scip", return_status=True)
    assert nx.is_directed_acyclic_graph(dag)
    assert status.objective == pytest.approx(0.8)
    removed_set = {(u, v) for u, v, _w in removed}
    assert removed_set == {("c", "a"), ("z", "x")}


def test_zero_weight_edges_still_produce_acyclic_graph():
    """With an all-zero objective, the MIP is indifferent among any feasible
    acyclic ordering, so SCIP may remove 1, 2, or all 3 edges — all are
    optimal (objective 0). Only acyclicity and a zero objective are
    guaranteed; the exact removed-edge count is not."""
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=0.0)
    g.add_edge("b", "c", weight=0.0)
    g.add_edge("c", "a", weight=0.0)
    dag, removed, status = solve(g, method="scip", return_status=True)
    assert nx.is_directed_acyclic_graph(dag)
    assert status.objective == pytest.approx(0.0)
    # The original 3-cycle is cyclic, so at least one edge must be removed.
    assert 1 <= len(removed) <= 3
    assert all(w == pytest.approx(0.0) for _u, _v, w in removed)


def test_tied_weight_edges_removes_exactly_one():
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=2.0)
    g.add_edge("b", "c", weight=2.0)
    g.add_edge("c", "a", weight=2.0)
    dag, removed, status = solve(g, method="scip", return_status=True)
    assert nx.is_directed_acyclic_graph(dag)
    assert len(removed) == 1
    assert status.objective == pytest.approx(2.0)


def test_deterministic_objective_across_repeated_runs():
    g = nx.DiGraph()
    rng = random.Random(4242)
    for u, v in itertools.permutations(range(6), 2):
        if rng.random() < 0.35:
            g.add_edge(f"n{u}", f"n{v}", weight=round(rng.uniform(0.1, 5.0), 3))

    objectives = []
    removed_sets = []
    for _ in range(5):
        _, removed, status = solve(g, method="scip", return_status=True)
        objectives.append(status.objective)
        removed_sets.append(frozenset((u, v) for u, v, _w in removed))

    assert len({round(o, 9) for o in objectives}) == 1
    assert len(set(removed_sets)) == 1


# ---------------------------------------------------------------------------
# Brute-force cross-validation on many small random graphs.
# ---------------------------------------------------------------------------


def test_matches_bruteforce_on_many_small_random_graphs():
    rng = random.Random(7)
    n_checked = 0
    for trial in range(40):
        n = rng.choice([3, 4, 5, 6])
        p = rng.choice([0.3, 0.5, 0.7])
        g = _random_weighted_digraph(rng, n, p)
        if g.number_of_edges() == 0 or nx.is_directed_acyclic_graph(g):
            continue
        _, _, brute_obj = exact_fas(g, max_n=8)
        _, scip_removed, status = solve(g, method="scip", return_status=True)
        assert status.proven_optimal
        assert nx.is_directed_acyclic_graph(solve(g, method="scip")[0])
        assert _weight_of(scip_removed) == pytest.approx(brute_obj, abs=1e-6)
        assert status.objective == pytest.approx(brute_obj, abs=1e-6)
        n_checked += 1
    assert n_checked >= 15, f"expected at least 15 cyclic graphs to be checked, got {n_checked}"


def test_scip_removed_weight_never_worse_than_greedy():
    rng = random.Random(99)
    n_checked = 0
    for trial in range(40):
        n = rng.choice([4, 5, 6, 7, 8])
        p = rng.choice([0.2, 0.4, 0.6])
        g = _random_weighted_digraph(rng, n, p)
        if g.number_of_edges() == 0 or nx.is_directed_acyclic_graph(g):
            continue
        _, greedy_removed = greedy_fas(g)
        _, scip_removed = solve(g, method="scip")
        assert _weight_of(scip_removed) <= _weight_of(greedy_removed) + 1e-6
        n_checked += 1
    assert n_checked >= 15, f"expected at least 15 cyclic graphs to be checked, got {n_checked}"


# ---------------------------------------------------------------------------
# Solver-agnostic dispatch and status-object behavior.
# ---------------------------------------------------------------------------


def test_exact_and_ilp_and_scip_aliases_agree():
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=1.0)
    g.add_edge("b", "a", weight=0.4)
    for method in ("scip", "exact", "ilp"):
        dag, removed = solve(g, method=method)
        assert removed == [("b", "a", 0.4)]


def test_return_status_false_by_default():
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=1.0)
    g.add_edge("b", "a", weight=0.4)
    result = solve(g, method="scip")
    assert len(result) == 2


def test_return_status_true_gives_solve_status():
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=1.0)
    g.add_edge("b", "a", weight=0.4)
    result = solve(g, method="scip", return_status=True)
    assert len(result) == 3
    assert isinstance(result[2], SolveStatus)


def test_configurable_time_limit_is_accepted():
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=1.0)
    g.add_edge("b", "a", weight=0.4)
    dag, removed, status = solve(
        g, method="scip", return_status=True, time_limit_s=5.0, mip_gap=0.0
    )
    assert status.proven_optimal
    assert removed == [("b", "a", 0.4)]
