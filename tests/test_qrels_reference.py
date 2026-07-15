from __future__ import annotations

import networkx as nx

from consistency_ranker.data.schema import QrelEntry
from consistency_ranker.qrels_reference import (
    build_candidate_qrels_reference,
    judged_pair_order_changed,
    judged_pair_preference,
    pairwise_accuracy_for_judged_pairs,
    qrels_backward_edge_weight,
    qrels_pairwise_inconsistency,
)


def _qrels(*rows) -> list[QrelEntry]:
    return [QrelEntry(query_id=str(q), doc_id=str(d), relevance=int(r)) for q, d, r in rows]


def test_reference_separates_eval_map_from_judged_map():
    reference = build_candidate_qrels_reference(
        _qrels(("q1", "d1", 2), ("q1", "d2", 0)),
        ["d1", "d2", "dX"],
    )
    assert reference.candidate_ranking == ["d1", "d2", "dX"]
    assert reference.eval_rel_map == {"d1": 2, "d2": 0, "dX": 0}
    assert reference.judged_rel_map == {"d1": 2, "d2": 0}


def test_equal_grade_pairs_are_incomparable():
    judged_rel_map = build_candidate_qrels_reference(
        _qrels(("q1", "d1", 2), ("q1", "d2", 2), ("q1", "d3", 1)),
        ["d1", "d2", "d3"],
    ).judged_rel_map
    assert judged_pair_preference("d1", "d2", judged_rel_map) is None
    assert judged_pair_preference("d1", "d3", judged_rel_map) == 1


def test_judged_and_unjudged_pairs_are_incomparable():
    judged_rel_map = build_candidate_qrels_reference(
        _qrels(("q1", "d1", 1), ("q1", "d2", 0)),
        ["d1", "d2", "dX"],
    ).judged_rel_map
    assert judged_pair_preference("d1", "dX", judged_rel_map) is None
    assert judged_pair_preference("dX", "d2", judged_rel_map) is None


def test_zero_relevance_judged_docs_remain_comparable_to_positive_docs():
    judged_rel_map = build_candidate_qrels_reference(
        _qrels(("q1", "d1", 2), ("q1", "d0", 0)),
        ["d1", "d0", "dX"],
    ).judged_rel_map
    assert judged_pair_preference("d1", "d0", judged_rel_map) == 1
    assert judged_pair_preference("d0", "dX", judged_rel_map) is None


def test_pairwise_accuracy_uses_only_explicit_different_grade_pairs():
    judged_rel_map = build_candidate_qrels_reference(
        _qrels(("q1", "d1", 2), ("q1", "d2", 2), ("q1", "d3", 0)),
        ["d1", "d2", "d3", "dX"],
    ).judged_rel_map
    ranking = ["d2", "dX", "d1", "d3"]
    assert pairwise_accuracy_for_judged_pairs(ranking, judged_rel_map) == 1.0


def test_judged_pair_order_changed_ignores_unjudged_and_equal_grade_pairs():
    judged_rel_map = build_candidate_qrels_reference(
        _qrels(("q1", "d1", 2), ("q1", "d2", 2), ("q1", "d3", 0)),
        ["d1", "d2", "d3", "dX"],
    ).judged_rel_map
    assert (
        judged_pair_order_changed(
            ["d1", "d2", "dX", "d3"],
            ["d2", "d1", "d3", "dX"],
            judged_rel_map,
            docs=["d1", "d2", "d3", "dX"],
        )
        is False
    )
    assert (
        judged_pair_order_changed(
            ["d1", "d3", "d2"],
            ["d3", "d1", "d2"],
            judged_rel_map,
            docs=["d1", "d2", "d3"],
        )
        is True
    )


def test_qrels_graph_metrics_ignore_unjudged_pairs_and_tied_grades():
    judged_rel_map = build_candidate_qrels_reference(
        _qrels(("q1", "d1", 2), ("q1", "d2", 0), ("q1", "d3", 0)),
        ["d1", "d2", "d3", "dX"],
    ).judged_rel_map
    graph = nx.DiGraph()
    graph.add_edge("d2", "d1", weight=3.0)
    graph.add_edge("d1", "d3", weight=2.0)
    graph.add_edge("dX", "d1", weight=7.0)
    graph.add_edge("d3", "d2", weight=5.0)
    assert qrels_pairwise_inconsistency(graph, judged_rel_map) == 1
    assert qrels_backward_edge_weight(graph, judged_rel_map) == 3.0
