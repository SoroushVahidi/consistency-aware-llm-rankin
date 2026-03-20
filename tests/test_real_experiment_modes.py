"""
Tests for alternative preference-source modes in run_real_experiment.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_real_experiment import (
    _build_query_preferences,
    _average_precision_at_k,
    _ndcg_at_k,
    _pairwise_accuracy_from_relevance,
    _precision_recall_at_k,
    _reference_ranking_for_candidates,
    _weighted_out_minus_in_ranking,
    _flip_preference_directions,
    _has_usable_eval_labels,
    _load_pairwise_preference_file,
    _load_score_file,
    _score_entries_to_preferences,
)
from consistency_ranker.data.schema import QrelEntry
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.pairwise_prefs import Preference


def _qrels(*rows) -> list[QrelEntry]:
    return [QrelEntry(query_id=str(q), doc_id=str(d), relevance=int(r)) for q, d, r in rows]


def test_has_usable_eval_labels_true():
    assert _has_usable_eval_labels(_qrels(("q1", "d1", 1), ("q1", "d2", 0)))


def test_has_usable_eval_labels_false_single_grade():
    assert not _has_usable_eval_labels(_qrels(("q1", "d1", 1), ("q1", "d2", 1)))


def test_score_entries_to_preferences_builds_pairs():
    prefs = _score_entries_to_preferences(
        [("d1", 0.9), ("d2", 0.7), ("d3", 0.3)],
        top_k=3,
        seed=42,
    )
    assert len(prefs) == 3
    pairs = {(p.winner, p.loser) for p in prefs}
    assert ("d1", "d2") in pairs
    assert ("d1", "d3") in pairs
    assert ("d2", "d3") in pairs


def test_flip_preference_directions_deterministic():
    from consistency_ranker.pairwise_prefs import Preference

    base = [
        Preference("a", "b", 1.0),
        Preference("a", "c", 1.0),
        Preference("b", "c", 1.0),
    ]
    flipped_1 = _flip_preference_directions(base, flip_prob=1.0, seed=7, query_id="q1")
    flipped_2 = _flip_preference_directions(base, flip_prob=1.0, seed=7, query_id="q1")
    assert flipped_1 == flipped_2
    assert {(p.winner, p.loser) for p in flipped_1} == {("b", "a"), ("c", "a"), ("c", "b")}


def test_load_pairwise_preference_file(tmp_path: Path):
    f = tmp_path / "pairs.jsonl"
    f.write_text(
        "\n".join(
            [
                json.dumps({"query_id": "q1", "winner_doc_id": "d1", "loser_doc_id": "d2", "weight": 2}),
                json.dumps({"query_id": "q1", "winner": "d2", "loser": "d3"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    idx = _load_pairwise_preference_file(f)
    assert "q1" in idx
    assert len(idx["q1"]) == 2
    assert idx["q1"][0].weight == pytest.approx(2.0)


def test_load_score_file(tmp_path: Path):
    f = tmp_path / "scores.jsonl"
    f.write_text(
        "\n".join(
            [
                json.dumps({"query_id": "q1", "doc_id": "d1", "score": 1.2}),
                json.dumps({"query_id": "q1", "doc_id": "d2", "score": 0.8}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    idx = _load_score_file(f)
    assert idx["q1"] == [("d1", 1.2), ("d2", 0.8)]


def test_build_query_preferences_qrels_flip():
    prefs, note = _build_query_preferences(
        query_id="q1",
        qrels_for_query=_qrels(("q1", "d1", 2), ("q1", "d2", 1), ("q1", "d3", 0)),
        top_k=3,
        weight_scheme="grade_diff",
        seed=1,
        preference_source="qrels_flip",
        flip_prob=0.5,
        pairwise_index=None,
        score_index=None,
    )
    assert prefs
    assert "synthetic corruption" in note


def test_build_query_preferences_score_file():
    prefs, note = _build_query_preferences(
        query_id="q1",
        qrels_for_query=_qrels(("q1", "d1", 2), ("q1", "d2", 1)),
        top_k=2,
        weight_scheme="grade_diff",
        seed=1,
        preference_source="score_file",
        flip_prob=0.0,
        pairwise_index=None,
        score_index={"q1": [("d1", 0.9), ("d2", 0.2)]},
    )
    assert len(prefs) == 1
    assert prefs[0].winner == "d1"
    assert "score file" in note


def test_candidate_aligned_reference_and_quality_metrics():
    qrels = _qrels(("q1", "d1", 2), ("q1", "d2", 1), ("q1", "d3", 0))
    ref, rel_map = _reference_ranking_for_candidates(qrels, {"d1", "d2", "dX"})
    assert ref == ["d1", "d2", "dX"]
    assert rel_map["d1"] == 2
    assert rel_map["dX"] == 0

    ranking = ["d2", "dX", "d1"]
    ndcg = _ndcg_at_k(ranking, rel_map, k=2)
    ap = _average_precision_at_k(ranking, rel_map, k=2)
    p_at_k, r_at_k = _precision_recall_at_k(ranking, rel_map, k=2)
    pair_acc = _pairwise_accuracy_from_relevance(ranking, rel_map)
    assert ndcg is not None and 0.0 <= ndcg <= 1.0
    assert ap is not None and 0.0 <= ap <= 1.0
    assert p_at_k is not None and 0.0 <= p_at_k <= 1.0
    assert r_at_k is not None and 0.0 <= r_at_k <= 1.0
    assert pair_acc is not None and 0.0 <= pair_acc <= 1.0


def test_weighted_out_minus_in_ranking_runs():
    graph = build_graph(
        [
            Preference("a", "b", 2.0),
            Preference("a", "c", 1.0),
            Preference("c", "b", 1.0),
        ]
    )
    ranking = _weighted_out_minus_in_ranking(graph)
    assert ranking[0] == "a"
