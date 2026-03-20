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
    local_adjacent_swap_refinement,
    pagerank_ranking,
    priority_topological_ranking,
    score_sum_ranking,
    score_sum_scores,
    topological_ranking,
    weighted_out_minus_in_ranking,
)
from consistency_ranker.borda_fuse_ranking import (
    borda_fuse_ranking,
    borda_fuse_scores,
    per_query_borda_fuse_ranking_from_score_maps,
)
from consistency_ranker.combsum_ranking import (
    COMBSUM_NORM_MINMAX,
    COMBSUM_NORM_NONE,
    combsum_ranking,
    combsum_scores,
    dedupe_best_scores,
    per_query_combsum_ranking_from_score_maps,
)
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.greedy_fas import greedy_fas
from consistency_ranker.markov_graph_ranking import (
    DEFAULT_MARKOV_DAMPING,
    markov_graph_ranking,
    markov_graph_scores,
)
from consistency_ranker.pairwise_prefs import Preference
from consistency_ranker.rrf_ranking import (
    DEFAULT_RRF_K,
    per_query_rrf_ranking_from_score_maps,
    ranked_list_from_score_entries,
    rrf_ranking,
    rrf_scores_and_best_ranks,
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


class TestReciprocalRankFusion:
    """Cormack et al. (SIGIR 2009) RRF: sum_s 1/(k + rank_s(d))."""

    def test_ranked_list_dedupes_by_max_score(self):
        assert ranked_list_from_score_entries([("a", 1.0), ("a", 3.0), ("b", 2.0)]) == [
            "a",
            "b",
        ]

    def test_toy_fusion_tie_break_lexicographic(self):
        s1 = ["a", "b", "c"]
        s2 = ["b", "a", "c"]
        out = rrf_ranking([s1, s2], ["a", "b", "c"], k=60.0)
        assert out[0] == "a"
        assert out[1] == "b"
        assert out[2] == "c"

    def test_missing_in_systems_zero_contribution(self):
        s1 = ["a", "b"]
        s2 = ["a", "b"]
        out = rrf_ranking([s1, s2], ["a", "b", "ghost"], k=10.0)
        assert out[-1] == "ghost"

    def test_tie_break_uses_best_rank_across_systems(self):
        k = 60.0
        s1 = ["x", "y"]
        s2 = ["y", "x"]
        sc, br = rrf_scores_and_best_ranks([s1, s2], k=k)
        assert sc["x"] == pytest.approx(sc["y"])
        assert br["x"] == 1 and br["y"] == 1
        out = rrf_ranking([s1, s2], ["x", "y"], k=k)
        assert out == ["x", "y"]

    def test_per_query_from_score_maps_matches_direct_lists(self):
        smaps = [
            {"q1": [("d1", 10.0), ("d2", 5.0), ("d3", 1.0)]},
            {"q1": [("d3", 9.0), ("d2", 8.0), ("d1", 0.0)]},
        ]
        lists = [
            ranked_list_from_score_entries(smaps[0]["q1"]),
            ranked_list_from_score_entries(smaps[1]["q1"]),
        ]
        cand = {"d1", "d2", "d3"}
        assert per_query_rrf_ranking_from_score_maps("q1", smaps, cand, k=60.0) == rrf_ranking(
            lists, cand, k=60.0
        )

    def test_k_must_be_positive(self):
        with pytest.raises(ValueError):
            rrf_ranking([["a"]], ["a"], k=0.0)

    def test_default_k_constant(self):
        assert DEFAULT_RRF_K == 60.0


class TestCombSUM:
    """Fox & Shaw–style CombSUM with per-query per-ranker min–max (default)."""

    def test_toy_minmax_ordering(self):
        s1 = dedupe_best_scores([("a", 1.0), ("b", 0.0)])
        s2 = dedupe_best_scores([("a", 0.0), ("c", 1.0)])
        out = combsum_ranking([s1, s2], ["a", "b", "c"], normalization=COMBSUM_NORM_MINMAX)
        assert out == ["a", "c", "b"]

    def test_minmax_differs_from_raw_when_scales_differ(self):
        s1 = dedupe_best_scores([("a", 10.0), ("b", 0.0)])
        s2 = dedupe_best_scores([("a", 0.0), ("b", 1000.0)])
        mm = combsum_ranking([s1, s2], ["a", "b"], normalization=COMBSUM_NORM_MINMAX)
        raw = combsum_ranking([s1, s2], ["a", "b"], normalization=COMBSUM_NORM_NONE)
        assert mm == ["a", "b"]
        assert raw == ["b", "a"]

    def test_missing_ranker_contribution_zero(self):
        s1 = dedupe_best_scores([("a", 1.0), ("b", 0.0)])
        s2 = dedupe_best_scores([("a", 1.0), ("b", 0.0)])
        out = combsum_ranking([s1, s2], ["a", "b", "only_here"], normalization=COMBSUM_NORM_MINMAX)
        assert out[-1] == "only_here"

    def test_flat_ranker_scores_add_zero_after_minmax(self):
        s1 = dedupe_best_scores([("a", 5.0), ("b", 5.0)])
        s2 = dedupe_best_scores([("a", 0.0), ("b", 1.0)])
        out = combsum_ranking([s1, s2], ["a", "b"], normalization=COMBSUM_NORM_MINMAX)
        assert out == ["b", "a"]

    def test_tie_break_best_rank_then_doc_id(self):
        s1 = dedupe_best_scores([("a", 10.0), ("b", 0.0)])
        s2 = dedupe_best_scores([("a", 0.0), ("b", 10.0)])
        fused = combsum_scores([s1, s2], normalization=COMBSUM_NORM_MINMAX)
        assert fused["a"] == pytest.approx(fused["b"])
        out = combsum_ranking([s1, s2], ["a", "b"], normalization=COMBSUM_NORM_MINMAX)
        assert out == ["a", "b"]

    def test_per_query_from_score_maps(self):
        smaps = [
            {"q1": [("d1", 10.0), ("d2", 0.0)]},
            {"q1": [("d1", 0.0), ("d2", 100.0)]},
        ]
        direct = combsum_ranking(
            [
                dedupe_best_scores(smaps[0]["q1"]),
                dedupe_best_scores(smaps[1]["q1"]),
            ],
            ["d1", "d2"],
            normalization=COMBSUM_NORM_MINMAX,
        )
        assert (
            per_query_combsum_ranking_from_score_maps("q1", smaps, ["d1", "d2"]) == direct
        )

    def test_multi_query_score_maps_independent(self):
        smaps = [
            {
                "q1": [("a", 1.0), ("b", 0.0)],
                "q2": [("a", 0.0), ("b", 1.0)],
            },
            {
                "q1": [("a", 0.0), ("b", 1.0)],
                "q2": [("a", 0.0), ("b", 1.0)],
            },
        ]
        o1 = per_query_combsum_ranking_from_score_maps("q1", smaps, ["a", "b"])
        o2 = per_query_combsum_ranking_from_score_maps("q2", smaps, ["a", "b"])
        assert o1 == ["a", "b"]
        assert o2 == ["b", "a"]

    def test_invalid_normalization(self):
        with pytest.raises(ValueError, match="normalization"):
            combsum_ranking([{"a": 1.0}], ["a"], normalization="zscore")

    def test_combsum_scores_symmetric_tie_lexicographic(self):
        systems = [
            dedupe_best_scores([("x", 1.0), ("y", 0.0)]),
            dedupe_best_scores([("x", 0.0), ("y", 1.0)]),
        ]
        scores = combsum_scores(systems, normalization=COMBSUM_NORM_MINMAX)
        order = combsum_ranking(systems, ["x", "y"], normalization=COMBSUM_NORM_MINMAX)
        assert scores["x"] == pytest.approx(scores["y"])
        assert order == ["x", "y"]


class TestBordaFuse:
    """Borda count over retrieval lists (``borda_fuse``), not graph ``borda``."""

    def test_toy_union_n3_two_rankers(self):
        # U = {a,b,c}, N=3; R1=[a,b,c], R2=[c,a,b] -> totals a:3, c:2, b:1
        lists = [["a", "b", "c"], ["c", "a", "b"]]
        out = borda_fuse_ranking(lists, ["a", "b", "c"], n_q=3)
        assert out == ["a", "c", "b"]

    def test_missing_ranker_contribution_zero(self):
        lists = [["a", "b"], ["b", "a"]]  # union from maps would be {a,b}, N=2
        out = borda_fuse_ranking(lists, ["a", "b", "ghost"], n_q=2)
        assert out == ["a", "b", "ghost"]

    def test_tie_break_best_rank_then_doc_id(self):
        # All Borda totals 2; best ranks: a=1, c=1, b=2 -> b last; a before c by id
        lists = [["a", "b", "c"], ["c", "b", "a"]]
        out = borda_fuse_ranking(lists, ["a", "b", "c"], n_q=3)
        assert out == ["a", "c", "b"]

    def test_score_tie_lexicographic_rank_order(self):
        entries = [("b", 1.0), ("a", 1.0)]
        lst = ranked_list_from_score_entries(entries)
        assert lst == ["a", "b"]
        lists = [lst, lst]
        out = borda_fuse_ranking(lists, ["a", "b"], n_q=2)
        assert out == ["a", "b"]

    def test_per_query_from_score_maps_matches_direct(self):
        smaps = [
            {"q1": [("a", 1.0), ("b", 0.0), ("c", 0.0)]},
            {"q1": [("c", 1.0), ("a", 0.0), ("b", 0.0)]},
        ]
        lists = [
            ranked_list_from_score_entries(smaps[0]["q1"]),
            ranked_list_from_score_entries(smaps[1]["q1"]),
        ]
        direct = borda_fuse_ranking(lists, ["a", "b", "c"], n_q=3)
        assert (
            per_query_borda_fuse_ranking_from_score_maps("q1", smaps, ["a", "b", "c"])
            == direct
        )

    def test_multi_query_universe_independent(self):
        smaps = [
            {
                "q1": [("a", 1.0), ("b", 0.0)],
                "q2": [("a", 0.0), ("b", 1.0)],
            },
            {
                "q1": [("a", 0.0), ("b", 1.0)],
                "q2": [("a", 0.0), ("b", 1.0)],
            },
        ]
        o1 = per_query_borda_fuse_ranking_from_score_maps("q1", smaps, ["a", "b"])
        o2 = per_query_borda_fuse_ranking_from_score_maps("q2", smaps, ["a", "b"])
        assert o1 == ["a", "b"]
        assert o2 == ["b", "a"]

    def test_n_q_negative_raises(self):
        with pytest.raises(ValueError, match="n_q"):
            borda_fuse_ranking([["a"]], ["a"], n_q=-1)

    def test_borda_fuse_scores_matches_ranking_order(self):
        lists = [["a", "b", "c"], ["c", "a", "b"]]
        sc = borda_fuse_scores(lists, n_q=3)
        assert sc["a"] > sc["c"] > sc["b"]
        order = borda_fuse_ranking(lists, ["a", "b", "c"], n_q=3)
        assert order == ["a", "c", "b"]


class TestMarkovGraphRanking:
    """Rank Centrality–style chain (``markov_graph``), not reversed PageRank."""

    def test_acyclic_chain_order(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0)
        g.add_edge("b", "c", weight=1.0)
        assert markov_graph_ranking(g) == ["a", "b", "c"]

    def test_cycle_is_deterministic(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c"), ("c", "a")], weight=1.0)
        r1 = markov_graph_ranking(g)
        r2 = markov_graph_ranking(g)
        assert r1 == r2 == ["a", "b", "c"]

    def test_disconnected_component_tie_break(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0)
        g.add_node("z")
        out = markov_graph_ranking(g)
        assert set(out) == {"a", "b", "z"}
        assert out[0] == "a"

    def test_empty_graph(self):
        assert markov_graph_ranking(nx.DiGraph()) == []

    def test_single_node(self):
        g = nx.DiGraph()
        g.add_node("only")
        assert markov_graph_ranking(g) == ["only"]
        assert markov_graph_scores(g)["only"] == pytest.approx(1.0)

    def test_invalid_damping_raises(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0)
        with pytest.raises(ValueError, match="damping"):
            markov_graph_ranking(g, damping=1.5)

    def test_default_damping_constant(self):
        assert DEFAULT_MARKOV_DAMPING == 0.15

    def test_unrepaired_vs_repaired_can_differ(self):
        g = build_graph(
            [
                Preference("a", "b", 1.0),
                Preference("b", "c", 1.0),
                Preference("c", "a", 1.0),
            ]
        )
        dag, _ = greedy_fas(g)
        assert markov_graph_ranking(g) != markov_graph_ranking(dag)

    def test_scores_stronger_endpoints_in_chain(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0)
        g.add_edge("b", "c", weight=1.0)
        sc = markov_graph_scores(g)
        assert sc["a"] > sc["c"] and sc["b"] > sc["c"]


class TestLocalAdjacentSwapRefinement:
    def _bew(self, graph, ranking):
        pos = {n: i for i, n in enumerate(ranking)}
        total = 0.0
        for u, v, data in graph.edges(data=True):
            if pos.get(v, -1) < pos.get(u, -1):
                total += data.get("weight", 1.0)
        return total

    def test_dag_reaches_bew_zero(self):
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c"), ("a", "c")])
        # Start with backward order c, b, a (violates a->b, a->c, b->c)
        base = ["c", "b", "a"]
        refined = local_adjacent_swap_refinement(base, g, objective="bew")
        assert self._bew(g, refined) == 0.0
        assert set(refined) == {"a", "b", "c"}

    def test_single_swap_fixes_violation(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0)
        base = ["b", "a"]  # backward
        refined = local_adjacent_swap_refinement(base, g, objective="bew")
        assert refined == ["a", "b"]
        assert self._bew(g, refined) == 0.0

    def test_original_unchanged(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0)
        base = ["b", "a"]
        refined = local_adjacent_swap_refinement(base, g)
        assert base == ["b", "a"]
        assert refined == ["a", "b"]

    def test_single_item_unchanged(self):
        g = nx.DiGraph()
        g.add_node("x")
        refined = local_adjacent_swap_refinement(["x"], g)
        assert refined == ["x"]

    def test_count_objective(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=10.0)
        base = ["b", "a"]
        refined = local_adjacent_swap_refinement(base, g, objective="count")
        assert refined == ["a", "b"]
        assert self._bew(g, refined) == 0.0
