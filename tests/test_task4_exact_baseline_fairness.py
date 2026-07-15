# ruff: noqa: I001 -- import order below is semantically constrained (see comment)
from __future__ import annotations

import itertools
import random
import sys
from pathlib import Path

import networkx as nx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TASK4_SCRIPTS = (
    REPO_ROOT / "reports" / "final_revision_task4_exact_baseline_fairness_20260715" / "scripts"
)
FULL_CAL_SCRIPTS = REPO_ROOT / "reports" / "full_calibrated_core" / "scripts"
for path in (REPO_ROOT, FULL_CAL_SCRIPTS, TASK4_SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# task4_common must import before full_calibration_utils: it puts the
# latter's directory on sys.path (see task4_common's sys.path bootstrap).
# Unused directly here; imported only for that side effect.
import task4_common as _t4_bootstrap  # noqa: F401,E402
import full_calibration_utils as fcu  # noqa: E402
import run_exact_repaired_vs_unrepaired as rev  # noqa: E402
from consistency_ranker.baseline_ranking import (  # noqa: E402
    pagerank_ranking,
    rank_centrality_ranking,
    rank_centrality_scores,
)
from consistency_ranker.mwfas_solver import _solve_scip, is_scip_available, solve  # noqa: E402
from consistency_ranker.rrf_ranking import (  # noqa: E402
    DEFAULT_RRF_K,
    per_query_rrf_ranking_from_score_maps,
    ranked_list_from_score_entries,
    rrf_scores_and_best_ranks,
)
from rerankers.tournament_agg import bradley_terry_ranking  # noqa: E402
from scripts.run_real_experiment import (  # noqa: E402
    _prior_only_ranking,
    _rrf_prior_scores_for_query,
    _score_sum_prior_scores,
)

scip_required = pytest.mark.skipif(not is_scip_available(), reason="PySCIPOpt not installed")


# ---------------------------------------------------------------------------
# Exact-repaired vs unrepaired pipeline / solver optimality checks
# ---------------------------------------------------------------------------


@scip_required
def test_exact_calibration_evaluator_produces_repaired_vs_unrepaired_deltas():
    evaluator = rev.ExactCalibrationEvaluator()
    prefs = [
        fcu.Preference(winner="a", loser="b", weight=1.0),
        fcu.Preference(winner="b", loser="c", weight=1.0),
        fcu.Preference(winner="c", loser="a", weight=1.0),  # 3-cycle
    ]
    graph = fcu.build_graph(prefs)
    graph.add_nodes_from(["a", "b", "c"])
    dag, repair_info = evaluator._apply_repair(graph, {"a": 1.0, "b": 1.0, "c": 1.0}, top_k=3)
    assert nx.is_directed_acyclic_graph(dag)
    assert repair_info["solver_proven_optimal"] is True
    assert repair_info["n_edges_removed"] == 1
    assert evaluator.solver_rows[-1]["proven_optimal"] is True


@scip_required
def test_solve_forces_non_optimal_status_under_tiny_time_limit():
    rng = random.Random(11)
    g = nx.DiGraph()
    nodes = [f"n{i}" for i in range(14)]
    g.add_nodes_from(nodes)
    for u, v in itertools.permutations(nodes, 2):
        if rng.random() < 0.5:
            g.add_edge(u, v, weight=round(rng.uniform(0.1, 5.0), 3))
    dag, removed, status = _solve_scip(g, time_limit_s=0.0001, mip_gap=0.0)
    assert status.proven_optimal is False
    with pytest.raises(RuntimeError, match="did not reach proven optimality"):
        solve(g, method="scip", return_status=True, time_limit_s=0.0001, mip_gap=0.0)


@scip_required
def test_solve_raises_before_returning_a_partial_result():
    rng = random.Random(3)
    g = nx.DiGraph()
    nodes = [f"n{i}" for i in range(14)]
    g.add_nodes_from(nodes)
    for u, v in itertools.permutations(nodes, 2):
        if rng.random() < 0.5:
            g.add_edge(u, v, weight=round(rng.uniform(0.1, 5.0), 3))
    # solve() must never silently hand back a non-optimal exact result.
    with pytest.raises(RuntimeError):
        solve(g, method="scip", time_limit_s=0.0001, mip_gap=0.0)


# ---------------------------------------------------------------------------
# Prior vs RRF: score identity, tie handling, missing-document behavior,
# candidate-restricted vs full-list rank universe
# ---------------------------------------------------------------------------


def test_prior_and_rrf_agree_when_pool_equals_full_stored_list():
    """When every ranker's stored list IS exactly the candidate pool (no
    extra documents outside it), Prior's candidate-restricted rank and RRF's
    full-list rank coincide, so the two methods must produce identical fused
    scores -- isolating the rank-universe difference as the true cause of
    divergence (not some other hidden bug)."""
    pool = ["a", "b", "c"]
    raw_scores = {"bm25": {"a": 3.0, "b": 2.0, "c": 1.0}, "tfidf": {}, "minilm": {}}
    score_prior_sets = [{"q1": list(raw_scores["bm25"].items())}]

    prior_scores = _rrf_prior_scores_for_query(
        query_id="q1",
        candidate_nodes=set(pool),
        score_prior_sets=score_prior_sets,
        fallback_scores=None,
    )
    rrf_scores, _best_rank = rrf_scores_and_best_ranks(
        [ranked_list_from_score_entries(score_prior_sets[0]["q1"])], k=DEFAULT_RRF_K
    )
    for doc in pool:
        assert prior_scores[doc] == pytest.approx(rrf_scores[doc])


def test_prior_and_rrf_diverge_when_candidate_outranked_by_noncandidate():
    """The documented root cause: a ranker's full stored list contains
    documents OUTSIDE the candidate pool ranked above some candidates. Prior
    ranks candidates only among themselves (ignoring the outside documents);
    standalone RRF ranks among the full list first. This changes the
    reciprocal-rank CONTRIBUTION, not just tie-breaking."""
    pool = ["a", "b"]
    # Full stored list: x (non-candidate) outranks both a and b.
    raw_scores = {"bm25": {"x": 10.0, "a": 3.0, "b": 2.0}, "tfidf": {}, "minilm": {}}
    score_prior_sets = [{"q1": list(raw_scores["bm25"].items())}]

    prior_scores = _rrf_prior_scores_for_query(
        query_id="q1",
        candidate_nodes=set(pool),
        score_prior_sets=score_prior_sets,
        fallback_scores=None,
    )
    # Prior: "a" is rank 1 AMONG CANDIDATES -> 1/(60+1); "b" is rank 2 -> 1/(60+2)
    assert prior_scores["a"] == pytest.approx(1.0 / 61.0)
    assert prior_scores["b"] == pytest.approx(1.0 / 62.0)

    rrf_scores, _best_rank = rrf_scores_and_best_ranks(
        [ranked_list_from_score_entries(score_prior_sets[0]["q1"])], k=DEFAULT_RRF_K
    )
    # RRF (full list): "a" is rank 2 (behind x) -> 1/(60+2); "b" is rank 3 -> 1/(60+3)
    assert rrf_scores["a"] == pytest.approx(1.0 / 62.0)
    assert rrf_scores["b"] == pytest.approx(1.0 / 63.0)

    # Confirms the scores genuinely differ -- not a tie-break-only difference.
    assert prior_scores["a"] != pytest.approx(rrf_scores["a"])


def test_prior_tie_break_is_doc_id_only():
    pool = ["b", "a"]  # deliberately unsorted input order
    prior_scores = {"a": 5.0, "b": 5.0}
    ranking = _prior_only_ranking(pool, prior_scores)
    assert ranking == ["a", "b"]  # tied score -> ascending doc_id


def test_standalone_rrf_tie_break_uses_best_rank_then_doc_id():
    # bm25 ranks b first (rank1), a second; tfidf ranks a first, b second.
    # Fused RRF score is identical for a and b (symmetric), so the
    # standalone baseline's tie-break falls through to best observed rank
    # (both achieve best_rank=1 here too), then doc_id.
    lists = [["b", "a"], ["a", "b"]]
    scores, best_rank = rrf_scores_and_best_ranks(lists, k=DEFAULT_RRF_K)
    assert scores["a"] == pytest.approx(scores["b"])
    assert best_rank["a"] == best_rank["b"] == 1
    ranking = per_query_rrf_ranking_from_score_maps(
        "q1", [{"q1": [("b", 2.0), ("a", 1.0)]}, {"q1": [("a", 2.0), ("b", 1.0)]}], ["a", "b"]
    )
    assert ranking == ["a", "b"]  # falls through to doc_id


def test_prior_missing_document_uses_graph_fallback_not_zero():
    pool = ["a", "b"]
    raw_scores = {"bm25": {"a": 1.0}, "tfidf": {}, "minilm": {}}  # "b" unscored by every ranker
    score_prior_sets = [{"q1": list(raw_scores["bm25"].items())}]
    graph = nx.DiGraph()
    graph.add_nodes_from(pool)
    graph.add_edge("b", "a", weight=7.0)  # score-sum prior for "b" = 7.0, for "a" = 0.0
    fallback = _score_sum_prior_scores(graph)
    prior_scores = _rrf_prior_scores_for_query(
        query_id="q1",
        candidate_nodes=set(pool),
        score_prior_sets=score_prior_sets,
        fallback_scores=fallback,
    )
    assert prior_scores["b"] == pytest.approx(7.0)  # NOT 0.0


def test_standalone_rrf_missing_document_gets_zero():
    ranking = per_query_rrf_ranking_from_score_maps("q1", [{"q1": [("a", 1.0)]}], ["a", "b"])
    scores, _ = rrf_scores_and_best_ranks(
        [ranked_list_from_score_entries([("a", 1.0)])], k=DEFAULT_RRF_K
    )
    assert scores.get("b", 0.0) == 0.0
    assert ranking == ["a", "b"]  # "a" scored, "b" falls to the bottom


def test_prior_ranking_is_deterministic_across_repeated_calls():
    pool = ["a", "b", "c", "d"]
    raw_scores = {"bm25": {"a": 1.0, "b": 3.0, "c": 2.0, "d": 3.0}, "tfidf": {}, "minilm": {}}
    score_prior_sets = [{"q1": list(raw_scores["bm25"].items())}]
    results = set()
    for _ in range(5):
        prior_scores = _rrf_prior_scores_for_query(
            query_id="q1",
            candidate_nodes=set(pool),
            score_prior_sets=score_prior_sets,
            fallback_scores=None,
        )
        results.add(tuple(_prior_only_ranking(pool, prior_scores)))
    assert len(results) == 1


# ---------------------------------------------------------------------------
# Baseline pool fairness aggregation
# ---------------------------------------------------------------------------


def test_paired_deltas_only_uses_queries_with_both_methods_present():
    rows = [
        {"query_id": "q1", "method_key": "rrf", "ndcg_at_k": "0.5"},
        {"query_id": "q1", "method_key": "combsum", "ndcg_at_k": "0.7"},
        {"query_id": "q2", "method_key": "rrf", "ndcg_at_k": "0.4"},
        # q2 missing combsum -> excluded
    ]
    import run_baseline_pool_fairness as bpf

    deltas = bpf._paired_deltas(rows, "rrf", "combsum")
    assert deltas == [pytest.approx(0.5 - 0.7)]


# ---------------------------------------------------------------------------
# PageRank configuration
# ---------------------------------------------------------------------------


def test_pagerank_winner_outranks_loser_on_a_single_edge():
    """Empirically, the winner of a single preference edge gets the HIGHER
    pagerank_ranking score. This is worth pinning down explicitly: the
    function's docstring claims the reversal makes "being beaten by a
    strong competitor increase your authority" (i.e. the LOSER should rank
    higher), but `graph.reverse()` turns edge u->v ("u beats v") into v->u,
    which sends PageRank mass from the loser to the winner -- so the
    winner accumulates authority, not the loser. Verified directly against
    nx.pagerank rather than assumed from the docstring (see Task 4's
    graph-dependent-baseline audit, which flags this docstring/behavior
    mismatch as a documentation finding, not a bug to silently fix, since
    changing it would alter every committed PageRank-based result)."""
    g = nx.DiGraph()
    g.add_edge("winner", "loser", weight=1.0)
    ranking = pagerank_ranking(g, alpha=0.85)
    assert ranking[0] == "winner"
    scores = nx.pagerank(g.reverse(copy=True))
    assert scores["winner"] > scores["loser"]


def test_pagerank_alpha_zero_gives_uniform_scores():
    g = nx.DiGraph()
    g.add_weighted_edges_from([("a", "b", 1.0), ("b", "c", 1.0)])
    scores = nx.pagerank(g.reverse(copy=True), alpha=0.0, weight="weight")
    # with alpha=0 every node's score collapses to the uniform teleportation vector
    values = list(scores.values())
    assert max(values) - min(values) < 1e-9


def test_pagerank_has_no_explicit_tie_break_and_relies_on_dict_order():
    """Documents a real reproducibility nuance found during Task 4's audit:
    unlike copeland_ranking/rank_centrality_ranking/markov_graph_ranking,
    pagerank_ranking's final sort has no explicit doc_id tie-break, so tied
    PageRank scores are ordered by nx.pagerank's returned dict order (itself
    deterministic for a fixed graph) rather than by a principled rule."""
    g = nx.DiGraph()
    g.add_nodes_from(["z", "a"])  # two isolated nodes: perfectly tied PageRank score
    ranking = pagerank_ranking(g)
    scores = nx.pagerank(g.reverse(copy=True))
    assert scores["z"] == pytest.approx(scores["a"])
    # Order follows reversed-graph node iteration order, NOT sorted(doc_id):
    assert ranking == list(g.reverse(copy=True).nodes())


# ---------------------------------------------------------------------------
# RankCentrality edge cases
# ---------------------------------------------------------------------------


def test_rank_centrality_disconnected_components_each_stay_internally_ordered():
    g = nx.DiGraph()
    g.add_weighted_edges_from(
        [("a", "b", 1.0), ("c", "d", 1.0)]
    )  # two disjoint comparisons, no cross edges
    scores = rank_centrality_scores(g)
    assert scores["a"] > scores["b"]
    assert scores["c"] > scores["d"]
    assert sum(scores.values()) == pytest.approx(1.0)


def test_rank_centrality_all_zero_weight_graph_returns_uniform():
    g = nx.DiGraph()
    g.add_nodes_from(["a", "b", "c"])
    g.add_edge("a", "b", weight=0.0)
    scores = rank_centrality_scores(g)
    assert scores == {
        "a": pytest.approx(1 / 3),
        "b": pytest.approx(1 / 3),
        "c": pytest.approx(1 / 3),
    }


def test_rank_centrality_empty_and_single_node():
    assert rank_centrality_scores(nx.DiGraph()) == {}
    g = nx.DiGraph()
    g.add_node("solo")
    assert rank_centrality_scores(g) == {"solo": 1.0}
    assert rank_centrality_ranking(g) == ["solo"]


# ---------------------------------------------------------------------------
# Bradley-Terry convergence / disconnected graphs
# ---------------------------------------------------------------------------


def test_bradley_terry_isolated_node_with_no_comparisons_ranks_last():
    preferences = [("a", "b", 1.0)]
    result = bradley_terry_ranking(preferences, all_doc_ids=["a", "b", "isolated"])
    assert result.scores["isolated"] == 0.0
    assert result.ranked_doc_ids[-1] == "isolated"


def test_bradley_terry_disconnected_comparison_components():
    # {a beats b} and {c beats d} are two disconnected comparison groups.
    preferences = [("a", "b", 1.0), ("c", "d", 1.0)]
    result = bradley_terry_ranking(preferences)
    assert result.scores["a"] > result.scores["b"]
    assert result.scores["c"] > result.scores["d"]
    assert sum(result.scores.values()) == pytest.approx(1.0)


def test_bradley_terry_converges_on_transitive_chain():
    preferences = [("a", "b", 3.0), ("b", "c", 3.0), ("a", "c", 3.0)]
    result = bradley_terry_ranking(preferences, max_iter=200, tol=1e-9)
    assert result.ranked_doc_ids == ["a", "b", "c"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
