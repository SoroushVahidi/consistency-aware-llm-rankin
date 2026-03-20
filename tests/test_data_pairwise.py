"""
Tests for pairwise preference generation from relevance judgements
(unified_loader.preferences_from_qrels).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from consistency_ranker.data.schema import PairwisePreference, QrelEntry
from consistency_ranker.data.unified_loader import (
    load_multi_scorer_rankings,
    load_pairwise_preferences,
    load_score_rankings,
    preferences_from_multiple_score_rankings,
    preferences_from_qrels,
    preferences_from_scores,
    save_pairwise_preferences,
    save_score_rankings,
)


def _qrels(*tuples) -> list[QrelEntry]:
    """Build QrelEntry list from (query_id, doc_id, relevance) tuples."""
    return [QrelEntry(query_id=str(q), doc_id=str(d), relevance=r) for q, d, r in tuples]


class TestPreferencesFromQrels:
    def test_binary_relevance_one_query(self):
        qrels = _qrels(
            ("q1", "d1", 1),
            ("q1", "d2", 0),
            ("q1", "d3", 1),
        )
        prefs = preferences_from_qrels(qrels, top_k=10, seed=0)
        # Only d1>d2 and d3>d2 should appear (rel 1 > rel 0)
        pairs = {(p.winner_doc_id, p.loser_doc_id) for p in prefs}
        assert ("d1", "d2") in pairs or ("d3", "d2") in pairs
        # d1 vs d3 should not appear (equal relevance)
        assert ("d1", "d3") not in pairs
        assert ("d3", "d1") not in pairs

    def test_all_preferences_for_single_query(self):
        qrels = _qrels(
            ("q1", "d1", 2),
            ("q1", "d2", 1),
            ("q1", "d3", 0),
        )
        prefs = preferences_from_qrels(qrels, top_k=10, seed=0)
        assert len(prefs) == 3  # d1>d2, d1>d3, d2>d3

    def test_no_preferences_when_all_equal_relevance(self):
        qrels = _qrels(("q1", "d1", 1), ("q1", "d2", 1), ("q1", "d3", 1))
        prefs = preferences_from_qrels(qrels, top_k=10, seed=0)
        assert prefs == []

    def test_top_k_limits_candidates(self):
        # 5 documents with relevance 4,3,2,1,0
        qrels = _qrels(*[("q1", f"d{i}", 4 - i) for i in range(5)])
        # top_k=2 → only d0,d1; one preference
        prefs = preferences_from_qrels(qrels, top_k=2, seed=0)
        assert len(prefs) == 1
        assert prefs[0].winner_doc_id == "d0"
        assert prefs[0].loser_doc_id == "d1"

    def test_multiple_queries(self):
        qrels = _qrels(
            ("q1", "d1", 1), ("q1", "d2", 0),
            ("q2", "d3", 1), ("q2", "d4", 0),
        )
        prefs = preferences_from_qrels(qrels, top_k=10, seed=0)
        query_ids = {p.query_id for p in prefs}
        assert "q1" in query_ids
        assert "q2" in query_ids

    def test_max_queries_limits_output(self):
        qrels = _qrels(
            ("q1", "d1", 1), ("q1", "d2", 0),
            ("q2", "d3", 1), ("q2", "d4", 0),
            ("q3", "d5", 1), ("q3", "d6", 0),
        )
        prefs = preferences_from_qrels(qrels, top_k=10, max_queries=2, seed=0)
        query_ids = {p.query_id for p in prefs}
        assert len(query_ids) <= 2

    def test_grade_diff_weight_scheme(self):
        qrels = _qrels(("q1", "d1", 3), ("q1", "d2", 1))
        prefs = preferences_from_qrels(qrels, top_k=10, seed=0, weight_scheme="grade_diff")
        assert len(prefs) == 1
        assert prefs[0].weight == pytest.approx(2.0)

    def test_binary_weight_scheme(self):
        qrels = _qrels(("q1", "d1", 3), ("q1", "d2", 1))
        prefs = preferences_from_qrels(qrels, top_k=10, seed=0, weight_scheme="binary")
        assert prefs[0].weight == pytest.approx(1.0)

    def test_invalid_weight_scheme_raises(self):
        with pytest.raises(ValueError, match="Unknown weight_scheme"):
            preferences_from_qrels([], weight_scheme="bad_scheme")

    def test_all_preferences_have_positive_weight(self):
        qrels = _qrels(
            ("q1", "d1", 2), ("q1", "d2", 1), ("q1", "d3", 0),
        )
        prefs = preferences_from_qrels(qrels, top_k=10, seed=0, weight_scheme="grade_diff")
        assert all(p.weight > 0 for p in prefs)

    def test_winner_has_higher_relevance(self):
        """Every returned preference should have winner > loser in qrels."""
        qrels = _qrels(
            ("q1", "d1", 3), ("q1", "d2", 2), ("q1", "d3", 1), ("q1", "d4", 0),
        )
        rel_map = {e.doc_id: e.relevance for e in qrels}
        prefs = preferences_from_qrels(qrels, top_k=10, seed=0)
        for p in prefs:
            assert rel_map[p.winner_doc_id] > rel_map[p.loser_doc_id]


class TestPreferencesFromScores:
    def test_binary_weight_scheme(self):
        candidates = [("d1", 0.9), ("d2", 0.5), ("d3", 0.1)]
        prefs = preferences_from_scores("q1", candidates, weight_scheme="binary")
        assert len(prefs) == 3
        assert all(p.weight == pytest.approx(1.0) for p in prefs)
        assert all(p.query_id == "q1" for p in prefs)

    def test_absolute_margin_weight_scheme(self):
        candidates = [("d1", 0.9), ("d2", 0.5), ("d3", 0.1)]
        prefs = preferences_from_scores("q1", candidates, weight_scheme="absolute_margin")
        pairs_to_weight = {(p.winner_doc_id, p.loser_doc_id): p.weight for p in prefs}
        assert pairs_to_weight[("d1", "d2")] == pytest.approx(0.4)
        assert pairs_to_weight[("d1", "d3")] == pytest.approx(0.8)
        assert pairs_to_weight[("d2", "d3")] == pytest.approx(0.4)

    def test_normalized_margin_weight_scheme(self):
        candidates = [("d1", 0.9), ("d2", 0.5), ("d3", 0.1)]
        prefs = preferences_from_scores("q1", candidates, weight_scheme="normalized_margin")
        pairs_to_weight = {(p.winner_doc_id, p.loser_doc_id): p.weight for p in prefs}
        assert pairs_to_weight[("d1", "d2")] == pytest.approx(0.5)
        assert pairs_to_weight[("d1", "d3")] == pytest.approx(1.0)
        assert pairs_to_weight[("d2", "d3")] == pytest.approx(0.5)

    def test_min_margin_filters_pairs(self):
        candidates = [("d1", 0.9), ("d2", 0.85), ("d3", 0.1)]
        prefs = preferences_from_scores(
            "q1", candidates, weight_scheme="absolute_margin", min_margin=0.2
        )
        assert len(prefs) == 2
        pairs = {(p.winner_doc_id, p.loser_doc_id) for p in prefs}
        assert ("d1", "d2") not in pairs
        assert ("d1", "d3") in pairs
        assert ("d2", "d3") in pairs

    def test_min_margin_none_includes_all(self):
        candidates = [("d1", 0.9), ("d2", 0.89), ("d3", 0.1)]
        prefs = preferences_from_scores("q1", candidates, min_margin=None)
        assert len(prefs) == 3

    def test_ties_skipped(self):
        candidates = [("d1", 0.5), ("d2", 0.5), ("d3", 0.1)]
        prefs = preferences_from_scores("q1", candidates)
        assert len(prefs) == 2
        pairs = {(p.winner_doc_id, p.loser_doc_id) for p in prefs}
        assert ("d1", "d2") not in pairs
        assert ("d2", "d1") not in pairs

    def test_single_candidate_returns_empty(self):
        prefs = preferences_from_scores("q1", [("d1", 0.9)])
        assert prefs == []

    def test_empty_candidates_returns_empty(self):
        prefs = preferences_from_scores("q1", [])
        assert prefs == []

    def test_invalid_weight_scheme_raises(self):
        with pytest.raises(ValueError, match="Unknown weight_scheme"):
            preferences_from_scores("q1", [("d1", 1.0), ("d2", 0.0)], weight_scheme="bad")

    def test_all_scores_equal_returns_empty(self):
        candidates = [("d1", 0.5), ("d2", 0.5), ("d3", 0.5)]
        prefs = preferences_from_scores("q1", candidates)
        assert prefs == []

    def test_output_compatible_with_build_graph(self):
        from consistency_ranker.graph_construction import build_graph
        from consistency_ranker.pairwise_prefs import Preference

        candidates = [("d1", 0.9), ("d2", 0.5), ("d3", 0.1)]
        prefs = preferences_from_scores("q1", candidates, weight_scheme="absolute_margin")
        graph_prefs = [
            Preference(winner=p.winner_doc_id, loser=p.loser_doc_id, weight=p.weight)
            for p in prefs
        ]
        graph = build_graph(graph_prefs)
        assert graph.number_of_nodes() == 3
        assert graph.number_of_edges() == 3
        assert graph.has_edge("d1", "d2")
        assert graph.has_edge("d1", "d3")
        assert graph.has_edge("d2", "d3")


class TestPreferencesFromMultipleScoreRankings:
    def test_scorers_agree_completely(self):
        scorer_rankings = {
            "s1": [("d1", 0.9), ("d2", 0.5), ("d3", 0.1)],
            "s2": [("d1", 0.8), ("d2", 0.6), ("d3", 0.2)],
        }
        prefs = preferences_from_multiple_score_rankings(
            "q1", scorer_rankings, weight_mode="majority_vote"
        )
        pairs = {(p.winner_doc_id, p.loser_doc_id) for p in prefs}
        assert ("d1", "d2") in pairs
        assert ("d1", "d3") in pairs
        assert ("d2", "d3") in pairs
        assert len(prefs) == 3

    def test_scorers_disagree_creates_cycles(self):
        scorer_rankings = {
            "s1": [("A", 0.9), ("B", 0.6), ("C", 0.3)],
            "s2": [("B", 0.9), ("C", 0.6), ("A", 0.3)],
            "s3": [("C", 0.9), ("A", 0.6), ("B", 0.3)],
        }
        prefs = preferences_from_multiple_score_rankings(
            "q1", scorer_rankings, weight_mode="majority_vote"
        )
        from consistency_ranker.cycle_detection import has_cycle
        from consistency_ranker.graph_construction import build_graph
        from consistency_ranker.pairwise_prefs import Preference

        graph_prefs = [Preference(p.winner_doc_id, p.loser_doc_id, p.weight) for p in prefs]
        graph = build_graph(graph_prefs)
        assert has_cycle(graph), "Expected cycle from disagreeing scorers"

    def test_missing_docs_in_one_scorer(self):
        scorer_rankings = {
            "full": [("d1", 0.9), ("d2", 0.5), ("d3", 0.1)],
            "partial": [("d1", 0.8), ("d2", 0.7)],
        }
        prefs = preferences_from_multiple_score_rankings(
            "q1", scorer_rankings, weight_mode="majority_vote"
        )
        pairs = {(p.winner_doc_id, p.loser_doc_id) for p in prefs}
        assert ("d1", "d2") in pairs or ("d2", "d1") in pairs
        assert ("d1", "d3") in pairs
        assert ("d2", "d3") in pairs

    def test_min_margin_filters_tiny_margins(self):
        scorer_rankings = {
            "s1": [("d1", 0.51), ("d2", 0.50), ("d3", 0.1)],
            "s2": [("d1", 0.52), ("d2", 0.50), ("d3", 0.1)],
        }
        prefs_full = preferences_from_multiple_score_rankings(
            "q1", scorer_rankings, weight_mode="summed_margin"
        )
        prefs_filtered = preferences_from_multiple_score_rankings(
            "q1", scorer_rankings, weight_mode="summed_margin", min_margin=0.1
        )
        assert len(prefs_filtered) < len(prefs_full)

    def test_summed_margin_direction_from_sign(self):
        scorer_rankings = {
            "s1": [("d1", 0.9), ("d2", 0.5)],
            "s2": [("d1", 0.4), ("d2", 0.8)],
        }
        prefs = preferences_from_multiple_score_rankings(
            "q1", scorer_rankings, weight_mode="summed_margin"
        )
        assert len(prefs) <= 1

    def test_vote_plus_margin_weight(self):
        scorer_rankings = {
            "s1": [("d1", 0.9), ("d2", 0.5)],
            "s2": [("d1", 0.8), ("d2", 0.4)],
        }
        prefs = preferences_from_multiple_score_rankings(
            "q1", scorer_rankings, weight_mode="vote_plus_margin"
        )
        assert len(prefs) == 1
        assert prefs[0].winner_doc_id == "d1"
        assert prefs[0].loser_doc_id == "d2"
        assert prefs[0].weight >= 2.0

    def test_invalid_weight_mode_raises(self):
        with pytest.raises(ValueError, match="Unknown weight_mode"):
            preferences_from_multiple_score_rankings(
                "q1", {"s1": [("d1", 1.0), ("d2", 0.0)]}, weight_mode="invalid"
            )

    def test_output_compatible_with_build_graph(self):
        from consistency_ranker.graph_construction import build_graph
        from consistency_ranker.pairwise_prefs import Preference

        scorer_rankings = {
            "s1": [("d1", 0.9), ("d2", 0.5), ("d3", 0.1)],
            "s2": [("d1", 0.7), ("d2", 0.6), ("d3", 0.2)],
        }
        prefs = preferences_from_multiple_score_rankings(
            "q1", scorer_rankings, weight_mode="majority_vote"
        )
        graph_prefs = [Preference(p.winner_doc_id, p.loser_doc_id, p.weight) for p in prefs]
        graph = build_graph(graph_prefs)
        assert graph.number_of_nodes() == 3
        assert graph.number_of_edges() >= 1

    def test_load_multi_scorer_rankings(self, tmp_path):
        bm25_path = tmp_path / "bm25.jsonl"
        dense_path = tmp_path / "dense.jsonl"
        bm25_path.write_text(
            '{"query_id": "q1", "ranked_doc_ids": ["d1", "d2"], "scores": [0.9, 0.5]}\n'
        )
        dense_path.write_text(
            '{"query_id": "q1", "ranked_doc_ids": ["d2", "d1"], "scores": [0.8, 0.6]}\n'
        )
        multi = load_multi_scorer_rankings({"bm25": bm25_path, "dense": dense_path})
        assert "bm25" in multi
        assert "dense" in multi
        assert multi["bm25"]["q1"] == [("d1", 0.9), ("d2", 0.5)]
        assert multi["dense"]["q1"] == [("d2", 0.8), ("d1", 0.6)]


class TestLoadScoreRankings:
    def test_load_jsonl(self, tmp_path):
        path = tmp_path / "scores.jsonl"
        path.write_text(
            '{"query_id": "q1", "ranked_doc_ids": ["d1", "d2"], "scores": [0.9, 0.5]}\n'
            '{"query_id": "q2", "ranked_doc_ids": ["d3", "d4", "d5"], '
            '"scores": [0.8, 0.6, 0.4]}\n'
        )
        result = load_score_rankings(path)
        assert result["q1"] == [("d1", 0.9), ("d2", 0.5)]
        assert result["q2"] == [("d3", 0.8), ("d4", 0.6), ("d5", 0.4)]

    def test_missing_scores_uses_uniform(self, tmp_path):
        path = tmp_path / "scores.jsonl"
        path.write_text('{"query_id": "q1", "ranked_doc_ids": ["d1", "d2"]}\n')
        result = load_score_rankings(path)
        assert result["q1"] == [("d1", 1.0), ("d2", 1.0)]

    def test_length_mismatch_raises(self, tmp_path):
        path = tmp_path / "scores.jsonl"
        path.write_text('{"query_id": "q1", "ranked_doc_ids": ["d1", "d2"], "scores": [0.9]}\n')
        with pytest.raises(ValueError, match="len"):
            load_score_rankings(path)

    def test_save_and_load_roundtrip(self, tmp_path):
        rankings = {
            "q1": [("d1", 0.9), ("d2", 0.5)],
            "q2": [("d3", 0.8), ("d4", 0.6)],
        }
        out_path = tmp_path / "scores" / "bm25.jsonl"
        save_score_rankings(rankings, out_path)
        loaded = load_score_rankings(out_path)
        assert loaded == rankings


class TestSaveLoadPairwisePreferences:
    def test_roundtrip_jsonl(self):
        prefs = [
            PairwisePreference("q1", "d1", "d2", 2.0),
            PairwisePreference("q1", "d1", "d3", 1.0),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            path = save_pairwise_preferences(prefs, out_dir)
            loaded = load_pairwise_preferences(path)

        assert len(loaded) == 2
        assert loaded[0].query_id == "q1"
        assert loaded[0].winner_doc_id == "d1"
        assert loaded[0].loser_doc_id == "d2"
        assert loaded[0].weight == pytest.approx(2.0)

    def test_empty_preferences_writes_empty_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            path = save_pairwise_preferences([], out_dir)
            loaded = load_pairwise_preferences(path)
        assert loaded == []
