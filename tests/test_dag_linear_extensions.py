"""Unit tests for hard-constraint DAG linear-extension ranking."""

from __future__ import annotations

import networkx as nx
import pytest

from consistency_ranker.baseline_ranking import (
    priority_topological_ranking,
    score_sum_scores,
    weighted_out_minus_in_ranking,
)
from consistency_ranker.dag_linear_extensions import (
    HARD_CONSTRAINT_METHODS,
    assert_valid_topological_order,
    balance_priority_topological_ranking,
    borda_fuse_prior_from_ranked_lists,
    closest_valid_extension_exact,
    closest_valid_extension_greedy,
    closest_valid_extension_ilp,
    count_linear_extensions,
    degree_ratio_priority_topological_ranking,
    enumerate_linear_extensions,
    farthest_valid_extension_exact,
    is_valid_topological_order,
    lexicographic_topological_ranking,
    linear_extension_metric_dispersion,
    normalized_balance_priority_scores,
    prior_priority_topological_ranking,
    random_topological_ranking,
    rrf_prior_from_ranked_lists,
    run_hard_constraint_method,
    sample_linear_extensions,
    source_sink_peeling_ranking,
)
from consistency_ranker.evaluation import n_violations


def _diamond_dag() -> nx.DiGraph:
    """a→b, a→c, b→d, c→d — two valid extensions: a,b,c,d and a,c,b,d."""
    g = nx.DiGraph()
    g.add_edges_from(
        [
            ("a", "b", {"weight": 1.0}),
            ("a", "c", {"weight": 3.0}),
            ("b", "d", {"weight": 1.0}),
            ("c", "d", {"weight": 2.0}),
        ]
    )
    return g


def _ambiguous_dag() -> nx.DiGraph:
    """Three parallel chains into a sink — many linear extensions."""
    g = nx.DiGraph()
    g.add_edges_from(
        [
            ("s1", "t", {"weight": 1.0}),
            ("s2", "t", {"weight": 2.0}),
            ("s3", "t", {"weight": 3.0}),
        ]
    )
    g.add_node("iso")
    return g


def _tiny_chain() -> nx.DiGraph:
    g = nx.DiGraph()
    g.add_edges_from([("a", "b", {"weight": 1.0}), ("b", "c", {"weight": 1.0})])
    return g


class TestValidityInvariants:
    @pytest.mark.parametrize(
        "method",
        [
            "lexicographic_topo",
            "balance_priority_topo_static",
            "balance_priority_topo_dynamic",
            "norm_balance_priority_topo_static",
            "norm_balance_priority_topo_dynamic",
            "degree_ratio_priority_topo_static",
            "degree_ratio_priority_topo_dynamic",
            "log_degree_ratio_priority_topo_static",
            "log_degree_ratio_priority_topo_dynamic",
            "source_sink_peeling",
        ],
    )
    def test_hard_methods_are_valid_permutations(self, method: str):
        dag = _ambiguous_dag()
        ranking = run_hard_constraint_method(method, dag, seed=0)
        assert set(ranking) == set(dag.nodes())
        assert len(ranking) == dag.number_of_nodes()
        assert_valid_topological_order(dag, ranking)

    def test_prior_and_closest_methods_valid(self):
        dag = _diamond_dag()
        prior_scores = {"a": 1.0, "b": 5.0, "c": 4.0, "d": 0.0}
        prior_ranking = ["b", "c", "a", "d"]
        for method, kwargs in [
            ("prior_priority_topo", {"prior_scores": prior_scores}),
            ("closest_valid_extension_greedy", {"prior_ranking": prior_ranking}),
            ("closest_valid_extension_exact", {"prior_ranking": prior_ranking}),
            ("random_topo", {"seed": 7}),
        ]:
            ranking = run_hard_constraint_method(method, dag, **kwargs)
            assert_valid_topological_order(dag, ranking)

    def test_rejects_cyclic_graph(self):
        g = nx.DiGraph([("a", "b"), ("b", "c"), ("c", "a")])
        with pytest.raises(nx.NetworkXUnfeasible):
            lexicographic_topological_ranking(g)


class TestLexicographic:
    def test_min_id_among_sources(self):
        dag = _ambiguous_dag()
        ranking = lexicographic_topological_ranking(dag)
        # Sources initially: iso, s1, s2, s3 — lexicographically iso first.
        assert ranking[0] == "iso"
        assert ranking[-1] == "t"
        assert_valid_topological_order(dag, ranking)

    def test_deterministic(self):
        dag = _diamond_dag()
        assert lexicographic_topological_ranking(dag) == lexicographic_topological_ranking(dag)


class TestPriorPriority:
    def test_prefers_higher_prior_among_sources(self):
        dag = _diamond_dag()
        # After placing a, sources are b and c; higher prior should win.
        ranking = prior_priority_topological_ranking(
            dag, {"a": 0.0, "b": 1.0, "c": 10.0, "d": 0.0}
        )
        assert ranking == ["a", "c", "b", "d"]

    def test_matches_legacy_priority_topological(self):
        dag = _diamond_dag()
        pri = score_sum_scores(dag)
        assert prior_priority_topological_ranking(dag, pri) == priority_topological_ranking(
            dag, pri
        )


class TestStaticVsDynamic:
    def test_static_and_dynamic_differ_on_residual_inweight(self):
        """Static keeps original W_in; dynamic zeros it for new sources.

        Constructed so that after removing ``a``:
        * static prefers ``b`` (balance 20 > residual-static of ``v`` = 10);
        * dynamic prefers ``v`` (balance 50 > 20).
        """
        g = nx.DiGraph()
        g.add_edges_from(
            [
                ("a", "v", {"weight": 40.0}),
                ("b", "w", {"weight": 20.0}),
                ("v", "w", {"weight": 50.0}),
            ]
        )
        static = balance_priority_topological_ranking(g, mode="static")
        dynamic = balance_priority_topological_ranking(g, mode="dynamic")
        assert_valid_topological_order(g, static)
        assert_valid_topological_order(g, dynamic)
        assert static == ["a", "b", "v", "w"]
        assert dynamic == ["a", "v", "b", "w"]
        assert static != dynamic

    def test_normalized_balance_scores_bounded(self):
        dag = _diamond_dag()
        scores = normalized_balance_priority_scores(dag, eps=1e-12)
        for v in scores.values():
            assert -1.0 - 1e-9 <= v <= 1.0 + 1e-9

    def test_ratio_only_chooses_among_sources(self):
        dag = _diamond_dag()
        ranking = degree_ratio_priority_topological_ranking(dag, mode="dynamic")
        assert_valid_topological_order(dag, ranking)


class TestSourceSinkPeeling:
    def test_valid_and_deterministic(self):
        dag = _ambiguous_dag()
        r1 = source_sink_peeling_ranking(dag)
        r2 = source_sink_peeling_ranking(dag)
        assert r1 == r2
        assert_valid_topological_order(dag, r1)
        assert r1[-1] == "t"  # unique sink should be last or near last

    def test_isolated_and_zero_weight_safe(self):
        g = nx.DiGraph()
        g.add_node("alone")
        g.add_edge("a", "b", weight=0.0)
        g.add_edge("b", "c", weight=1.0)
        ranking = source_sink_peeling_ranking(g)
        assert_valid_topological_order(g, ranking)
        assert set(ranking) == {"alone", "a", "b", "c"}


class TestClosestExtension:
    def test_greedy_moves_toward_prior(self):
        dag = _diamond_dag()
        prior = ["a", "c", "b", "d"]
        ranking = closest_valid_extension_greedy(dag, prior)
        assert ranking == ["a", "c", "b", "d"]

    def test_exact_agrees_with_brute_force(self):
        dag = _diamond_dag()
        prior = ["d", "c", "b", "a"]  # reverse-ish; constrained by DAG
        exact = closest_valid_extension_exact(dag, prior, objective="kendall")
        extensions = enumerate_linear_extensions(dag)
        prior_r = [x for x in prior if x in dag]
        best = min(extensions, key=lambda e: n_violations(e, prior_r))
        assert exact == best
        assert is_valid_topological_order(dag, exact)

    def test_ilp_agrees_with_enumeration(self):
        dag = _diamond_dag()
        prior = ["d", "c", "b", "a"]
        exact = closest_valid_extension_exact(dag, prior, objective="kendall")
        ilp = closest_valid_extension_ilp(dag, prior, objective="kendall")
        assert is_valid_topological_order(dag, ilp)
        # Same Kendall cost (order may differ among optima).
        prior_r = [x for x in prior if x in dag]
        assert n_violations(ilp, prior_r) == n_violations(exact, prior_r)

    def test_ilp_displacement_valid(self):
        dag = _diamond_dag()
        prior = ["a", "b", "c", "d"]
        ranking = closest_valid_extension_ilp(dag, prior, objective="displacement")
        assert_valid_topological_order(dag, ranking)

    def test_farthest_is_maximally_discordant(self):
        dag = _diamond_dag()
        prior = ["a", "b", "c", "d"]
        far = farthest_valid_extension_exact(dag, prior)
        extensions = enumerate_linear_extensions(dag)
        worst = max(extensions, key=lambda e: n_violations(e, prior))
        assert far == worst


class TestJudgmentFreePriors:
    def test_rrf_and_borda_fuse_priors(self):
        lists = [["a", "b", "c"], ["b", "a", "c"]]
        rrf = rrf_prior_from_ranked_lists(lists, ["a", "b", "c"], k=60.0)
        assert rrf["a"] > 0 and rrf["b"] > 0
        borda = borda_fuse_prior_from_ranked_lists(lists, ["a", "b", "c"])
        assert borda["a"] > 0 and set(borda) == {"a", "b", "c"}
        # Prior-priority topo with RRF prior remains a valid extension.
        dag = _diamond_dag()
        ranking = prior_priority_topological_ranking(
            dag, {**rrf, "d": 0.0}
        )
        assert_valid_topological_order(dag, ranking)


class TestRandomSampling:
    def test_seed_reproducible(self):
        dag = _ambiguous_dag()
        a = random_topological_ranking(dag, seed=123)
        b = random_topological_ranking(dag, seed=123)
        c = random_topological_ranking(dag, seed=124)
        assert a == b
        assert_valid_topological_order(dag, a)
        assert_valid_topological_order(dag, c)

    def test_dispersion_stats(self):
        dag = _ambiguous_dag()
        samples = sample_linear_extensions(dag, n_samples=20, seed=0)
        ref = lexicographic_topological_ranking(dag)
        stats = linear_extension_metric_dispersion(samples, ref)
        assert stats["n_samples"] == 20
        assert stats["min"] <= stats["mean"] <= stats["max"]


class TestEnumeration:
    def test_diamond_has_two_extensions(self):
        dag = _diamond_dag()
        assert count_linear_extensions(dag) == 2
        exts = {tuple(e) for e in enumerate_linear_extensions(dag)}
        assert exts == {("a", "b", "c", "d"), ("a", "c", "b", "d")}

    def test_chain_unique(self):
        assert count_linear_extensions(_tiny_chain()) == 1


class TestSoftMayViolate:
    def test_soft_balance_can_differ_from_topo(self):
        """Document that soft ranking is a different family (may violate)."""
        dag = _diamond_dag()
        soft = weighted_out_minus_in_ranking(dag)
        # Soft ranking on a DAG often still happens to be valid, but the API
        # contract does not guarantee it — construct a case with an extra
        # comparable soft method on a cyclic graph instead.
        cyclic = nx.DiGraph()
        cyclic.add_edges_from(
            [
                ("a", "b", {"weight": 1.0}),
                ("b", "c", {"weight": 1.0}),
                ("c", "a", {"weight": 10.0}),
            ]
        )
        soft_cyc = weighted_out_minus_in_ranking(cyclic)
        assert set(soft_cyc) == {"a", "b", "c"}
        # Hard methods must reject cycles.
        with pytest.raises(nx.NetworkXUnfeasible):
            lexicographic_topological_ranking(cyclic)
        assert soft  # silence unused if diamond soft is valid


class TestCatalog:
    def test_hard_methods_tuple_nonempty(self):
        assert "lexicographic_topo" in HARD_CONSTRAINT_METHODS
        assert "norm_balance_priority_topo_dynamic" in HARD_CONSTRAINT_METHODS
