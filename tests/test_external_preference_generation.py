"""
Tests for external score/vote generation pipeline scripts.
"""

from __future__ import annotations

import json
from pathlib import Path

from consistency_ranker.data.schema import Document, QrelEntry, Query
from scripts import build_votes_file, generate_score_file


def _mock_dataset():
    queries = [
        Query(query_id="q1", text="alpha beta"),
        Query(query_id="q2", text="gamma"),
        Query(query_id="q3", text="delta"),
    ]
    docs = [
        Document(doc_id="d1", text="alpha one"),
        Document(doc_id="d2", text="beta two"),
        Document(doc_id="d3", text="gamma three"),
    ]
    qrels = [
        QrelEntry(query_id="q1", doc_id="d1", relevance=1),
        QrelEntry(query_id="q1", doc_id="d2", relevance=0),
        QrelEntry(query_id="q2", doc_id="d2", relevance=1),
        QrelEntry(query_id="q2", doc_id="d3", relevance=0),
        QrelEntry(query_id="q3", doc_id="d1", relevance=1),
        QrelEntry(query_id="q3", doc_id="d3", relevance=0),
    ]
    return queries, docs, qrels


class _FakeRanker:
    def top_docs(self, query_text: str, top_n: int):
        rows = {
            "alpha beta": [("d1", 0.9), ("d2", 0.8), ("d3", 0.1)],
            "gamma": [("d3", 0.95), ("d2", 0.2), ("d1", 0.1)],
            "delta": [("d2", 0.7), ("d1", 0.6), ("d3", 0.05)],
        }[query_text]
        return rows[:top_n]


def test_generate_score_file_schema_and_query_id_export(tmp_path: Path, monkeypatch):
    out = tmp_path / "scores.jsonl"
    qfile = tmp_path / "queries.txt"
    monkeypatch.setattr(generate_score_file, "load_dataset_splits", lambda _ds: _mock_dataset())
    monkeypatch.setattr(generate_score_file, "_build_ranker", lambda _name, _docs: _FakeRanker())

    generate_score_file.main(
        [
            "--dataset", "scidocs",
            "--ranker", "bm25",
            "--max-queries", "2",
            "--top-n", "2",
            "--seed", "11",
            "--output", str(out),
            "--query-id-file", str(qfile),
        ]
    )

    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line]
    assert rows
    for row in rows:
        assert set(row.keys()) == {"query_id", "doc_id", "score", "ranker"}
        assert row["ranker"] == "bm25"
        assert isinstance(row["score"], float)

    assert qfile.exists()
    assert qfile.read_text(encoding="utf-8").strip()


def test_deterministic_query_sampling_import_export(tmp_path: Path):
    _q, _d, qrels = _mock_dataset()
    qfile = tmp_path / "query_ids.txt"

    selected_a, _ = generate_score_file._resolve_query_ids(
        qrels=qrels,
        max_queries=2,
        seed=123,
        query_id_file=qfile,
    )
    selected_b, _ = generate_score_file._resolve_query_ids(
        qrels=qrels,
        max_queries=2,
        seed=999,  # different seed should not matter once file exists
        query_id_file=qfile,
    )
    assert selected_a == selected_b


def test_votes_for_query_from_conflicting_rankers():
    rows = build_votes_file._votes_for_query(
        query_id="q1",
        ranker_scores={
            "bm25": {"d1": 0.9, "d2": 0.1},
            "tfidf": {"d2": 0.8, "d1": 0.2},
        },
        top_k=2,
    )
    triples = {(r["voter"], r["winner_doc_id"], r["loser_doc_id"]) for r in rows}
    assert ("bm25", "d1", "d2") in triples
    assert ("tfidf", "d2", "d1") in triples


def test_votes_v2_margin_abstention_and_support_filter():
    rows = build_votes_file._votes_for_query(
        query_id="q1",
        ranker_scores={
            "r1": {"d1": 1.0, "d2": 0.95},   # margin 0.05 (abstain)
            "r2": {"d1": 1.0, "d2": 0.70},   # margin 0.30 vote d1>d2
            "r3": {"d1": 0.60, "d2": 0.90},  # margin 0.30 vote d2>d1
            "r4": {"d1": 1.2},               # missing d2 -> abstain when enabled
        },
        top_k=2,
        vote_weight_scheme="margin",
        min_vote_margin=0.1,
        abstain_missing=True,
        min_support=2,
        min_aggregate_margin=0.4,
    )
    # No edge should pass: each direction has only one supporting voter.
    assert rows == []


def test_build_votes_file_schema(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(build_votes_file, "load_dataset_splits", lambda _ds: _mock_dataset())
    score_a = tmp_path / "a.jsonl"
    score_b = tmp_path / "b.jsonl"
    out = tmp_path / "votes.jsonl"
    qfile = tmp_path / "qids.txt"
    qfile.write_text("q1\nq2\n", encoding="utf-8")

    score_a.write_text(
        "\n".join(
            [
                json.dumps({"query_id": "q1", "doc_id": "d1", "score": 0.9, "ranker": "bm25"}),
                json.dumps({"query_id": "q1", "doc_id": "d2", "score": 0.1, "ranker": "bm25"}),
                json.dumps({"query_id": "q2", "doc_id": "d2", "score": 0.8, "ranker": "bm25"}),
                json.dumps({"query_id": "q2", "doc_id": "d3", "score": 0.2, "ranker": "bm25"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    score_b.write_text(
        "\n".join(
            [
                json.dumps({"query_id": "q1", "doc_id": "d2", "score": 0.95, "ranker": "tfidf"}),
                json.dumps({"query_id": "q1", "doc_id": "d1", "score": 0.2, "ranker": "tfidf"}),
                json.dumps({"query_id": "q2", "doc_id": "d3", "score": 0.7, "ranker": "tfidf"}),
                json.dumps({"query_id": "q2", "doc_id": "d2", "score": 0.4, "ranker": "tfidf"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    build_votes_file.main(
        [
            "--dataset", "scidocs",
            "--score-files", str(score_a), str(score_b),
            "--top-k", "2",
            "--output", str(out),
            "--query-id-file", str(qfile),
        ]
    )

    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line]
    assert rows
    for row in rows:
        assert set(row.keys()) == {
            "query_id",
            "winner_doc_id",
            "loser_doc_id",
            "weight",
            "voter",
        }
        assert row["weight"] == 1.0
