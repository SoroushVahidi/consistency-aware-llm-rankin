"""
Tests for the unified data schema (Query, Document, QrelEntry,
CandidateRanking, PairwisePreference).
"""

from __future__ import annotations

import json

import pytest

from consistency_ranker.data.schema import (
    CandidateRanking,
    Document,
    PairwisePreference,
    QrelEntry,
    Query,
)


class TestQuery:
    def test_roundtrip(self):
        q = Query(query_id="q1", text="What is MWFAS?", metadata={"source": "test"})
        d = q.to_dict()
        q2 = Query.from_dict(d)
        assert q2.query_id == "q1"
        assert q2.text == "What is MWFAS?"
        assert q2.metadata == {"source": "test"}

    def test_id_coerced_to_str(self):
        q = Query.from_dict({"query_id": 42, "text": "hello"})
        assert isinstance(q.query_id, str)
        assert q.query_id == "42"

    def test_missing_metadata_defaults_to_empty_dict(self):
        q = Query.from_dict({"query_id": "q1", "text": "x"})
        assert q.metadata == {}

    def test_json_serialisable(self):
        q = Query(query_id="q1", text="test")
        json.dumps(q.to_dict())  # should not raise


class TestDocument:
    def test_roundtrip(self):
        doc = Document(doc_id="d1", text="A document.", title="Title", metadata={"k": "v"})
        d = doc.to_dict()
        doc2 = Document.from_dict(d)
        assert doc2.doc_id == "d1"
        assert doc2.title == "Title"
        assert doc2.metadata == {"k": "v"}

    def test_id_coerced_to_str(self):
        doc = Document.from_dict({"doc_id": 99, "text": "x"})
        assert isinstance(doc.doc_id, str)

    def test_defaults(self):
        doc = Document.from_dict({"doc_id": "d1", "text": "x"})
        assert doc.title == ""
        assert doc.metadata == {}


class TestQrelEntry:
    def test_roundtrip(self):
        q = QrelEntry(query_id="q1", doc_id="d1", relevance=2)
        q2 = QrelEntry.from_dict(q.to_dict())
        assert q2.query_id == "q1"
        assert q2.doc_id == "d1"
        assert q2.relevance == 2

    def test_relevance_coerced_to_int(self):
        q = QrelEntry.from_dict({"query_id": "q1", "doc_id": "d1", "relevance": "3"})
        assert isinstance(q.relevance, int)
        assert q.relevance == 3


class TestCandidateRanking:
    def test_roundtrip_without_scores(self):
        cr = CandidateRanking(query_id="q1", ranked_doc_ids=["d1", "d2", "d3"])
        cr2 = CandidateRanking.from_dict(cr.to_dict())
        assert cr2.query_id == "q1"
        assert cr2.ranked_doc_ids == ["d1", "d2", "d3"]
        assert cr2.scores is None

    def test_roundtrip_with_scores(self):
        cr = CandidateRanking(query_id="q1", ranked_doc_ids=["d1", "d2"], scores=[0.9, 0.7])
        cr2 = CandidateRanking.from_dict(cr.to_dict())
        assert cr2.scores == [0.9, 0.7]

    def test_doc_ids_coerced_to_str(self):
        cr = CandidateRanking.from_dict({"query_id": "q1", "ranked_doc_ids": [1, 2, 3]})
        assert all(isinstance(x, str) for x in cr.ranked_doc_ids)


class TestPairwisePreference:
    def test_roundtrip(self):
        pref = PairwisePreference(
            query_id="q1",
            winner_doc_id="d1",
            loser_doc_id="d2",
            weight=2.5,
        )
        pref2 = PairwisePreference.from_dict(pref.to_dict())
        assert pref2.query_id == "q1"
        assert pref2.winner_doc_id == "d1"
        assert pref2.loser_doc_id == "d2"
        assert pref2.weight == pytest.approx(2.5)

    def test_default_weight(self):
        pref = PairwisePreference.from_dict(
            {"query_id": "q1", "winner_doc_id": "d1", "loser_doc_id": "d2"}
        )
        assert pref.weight == pytest.approx(1.0)

    def test_json_serialisable(self):
        pref = PairwisePreference(query_id="q1", winner_doc_id="d1", loser_doc_id="d2")
        json.dumps(pref.to_dict())
