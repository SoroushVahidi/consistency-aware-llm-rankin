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
    load_pairwise_preferences,
    preferences_from_qrels,
    save_pairwise_preferences,
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
