"""
Tests for alternative preference-source modes in run_real_experiment.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_real_experiment import (
    _hybrid_rrf_component_ranking,
    _hybrid_rrf_priority_topological_ranking,
    _build_hybrid_specs,
    _build_query_preferences,
    _average_precision_at_k,
    _copeland_ranking,
    _hybrid_rrf_fas_regularized_ranking,
    _ndcg_at_k,
    _parse_alpha_values,
    _pairwise_accuracy_from_relevance,
    _prior_only_ranking,
    _priority_topological_ranking,
    _precision_recall_at_k,
    _reference_ranking_for_candidates,
    _rrf_prior_scores_for_query,
    _weighted_out_minus_in_ranking,
    _flip_preference_directions,
    _filter_methods,
    _has_usable_eval_labels,
    _load_pairwise_preference_file,
    _resolve_output_dir,
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


def test_copeland_and_priority_topological_rankings():
    graph = build_graph(
        [
            Preference("a", "b", 1.0),
            Preference("a", "c", 1.0),
            Preference("c", "b", 1.0),
        ]
    )
    copeland = _copeland_ranking(graph)
    assert copeland[0] == "a"

    pri = {"a": 0.2, "b": 0.1, "c": 0.9}
    topo = _priority_topological_ranking(graph, pri)
    assert topo[0] == "a"
    assert topo.index("c") < topo.index("b")


def test_rrf_prior_and_hybrid_ranking():
    prior_sets = [
        {"q1": [("a", 3.0), ("b", 2.0), ("c", 1.0)]},
        {"q1": [("c", 3.0), ("a", 2.0), ("b", 1.0)]},
    ]
    pri = _rrf_prior_scores_for_query("q1", {"a", "b", "c"}, prior_sets)
    assert set(pri) == {"a", "b", "c"}
    graph = build_graph([Preference("a", "b", 1.0), Preference("c", "b", 1.0)])
    ranking = _hybrid_rrf_fas_regularized_ranking(graph, pri, fas_regularization=0.2)
    assert ranking[0] in {"a", "c"}


def test_hybrid_component_variants():
    graph = build_graph(
        [
            Preference("a", "b", 2.0),
            Preference("c", "b", 1.0),
        ]
    )
    pri = {"a": 0.7, "b": 0.1, "c": 0.4}
    r_balance = _hybrid_rrf_component_ranking(
        graph, pri, component="balance", alpha=0.5
    )
    r_copeland = _hybrid_rrf_component_ranking(
        graph, pri, component="copeland", alpha=0.3
    )
    r_prio = _hybrid_rrf_priority_topological_ranking(
        graph, pri, component="balance", alpha=0.3
    )
    assert r_balance[0] in {"a", "c"}
    assert r_copeland[0] in {"a", "c"}
    assert r_prio.index("b") == len(r_prio) - 1


def test_hybrid_spec_builder_ablation_and_sweep():
    specs = _build_hybrid_specs(
        include_ablation=True,
        alpha_sweep_components=["balance"],
        alpha_values=[0.0, 0.3],
    )
    names = {s.name for s in specs}
    assert "hybrid_rrf_prior_only" in names
    assert "hybrid_rrf_unrepaired_balance_a03" in names
    assert "hybrid_rrf_repaired_balance_a0p0" in names
    assert "hybrid_rrf_repaired_balance_a0p3" in names


def test_parse_alpha_values_and_prior_only():
    assert _parse_alpha_values("0.0, 0.3,1.0") == [0.0, 0.3, 1.0]
    with pytest.raises(ValueError):
        _parse_alpha_values("")
    ranking = _prior_only_ranking(["b", "a", "c"], {"a": 0.2, "b": 0.9, "c": 0.9})
    assert ranking == ["b", "c", "a"]


def test_filter_methods_keeps_requested_shortlist():
    methods = [
        "score_sum",
        "borda",
        "greedy_fas_weighted_balance",
        "hybrid_rrf_fas_regularized",
    ]
    filtered_methods, filtered_specs = _filter_methods(
        methods,
        {
            "hybrid_rrf_fas_regularized": _build_hybrid_specs(
                include_ablation=False,
                alpha_sweep_components=None,
                alpha_values=[0.2],
            )[0]
        },
        selected_methods=["score_sum", "hybrid_rrf_fas_regularized"],
    )
    assert filtered_methods == ["score_sum", "hybrid_rrf_fas_regularized"]
    assert list(filtered_specs) == ["hybrid_rrf_fas_regularized"]


def test_resolve_output_dir_nests_dataset_and_source():
    root = Path("outputs/real_small_validation")
    assert _resolve_output_dir(root, "scidocs", "qrels") == root / "scidocs" / "qrels"
    assert _resolve_output_dir(root / "scidocs", "scidocs", "qrels_flip") == (
        root / "scidocs" / "qrels_flip"
    )
    assert _resolve_output_dir(root / "scidocs" / "qrels", "scidocs", "qrels") == (
        root / "scidocs" / "qrels"
    )
