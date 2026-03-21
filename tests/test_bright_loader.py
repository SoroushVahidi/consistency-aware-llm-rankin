"""
Tests for BRIGHT dataset loading and normalization.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

from consistency_ranker.data.bright_loader import (
    BrightSchemaError,
    _parse_example_row,
    download_bright,
    load_raw_bright_splits,
    normalize_document_record,
    normalize_qrel_record,
    normalize_query_record,
)
from consistency_ranker.data.unified_loader import preferences_from_qrels


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


class TestBrightRecordNormalization:
    def test_normalize_query_record_accepts_alias_keys(self):
        q = normalize_query_record({"id": "q1", "query": "What is BRIGHT?"})
        assert q.query_id == "q1"
        assert q.text == "What is BRIGHT?"

    def test_normalize_document_record_accepts_alias_keys(self):
        doc = normalize_document_record(
            {"id": "d1", "contents": "Document body.", "doc_title": "Doc"}
        )
        assert doc.doc_id == "d1"
        assert doc.text == "Document body."
        assert doc.title == "Doc"

    def test_normalize_qrel_record_accepts_alias_keys(self):
        qrel = normalize_qrel_record({"query-id": "q1", "corpus-id": "d1", "score": "1"})
        assert qrel.query_id == "q1"
        assert qrel.doc_id == "d1"
        assert qrel.relevance == 1

    def test_normalize_query_record_missing_text_raises(self):
        with pytest.raises(BrightSchemaError, match="missing text"):
            normalize_query_record({"id": "q1"})


class TestBrightRawSplits:
    def test_load_raw_bright_splits_normalizes_aliases(self, tmp_path: Path):
        raw = tmp_path / "raw" / "bright"
        _write_jsonl(raw / "queries.jsonl", [{"id": "q1", "query": "Question?"}])
        _write_jsonl(
            raw / "documents.jsonl",
            [{"id": "d1", "text": "Doc one", "title": "T1"}],
        )
        _write_jsonl(
            raw / "qrels.jsonl",
            [{"query-id": "q1", "corpus-id": "d1", "score": 1}],
        )

        queries, docs, qrels = load_raw_bright_splits(raw)
        assert len(queries) == 1
        assert len(docs) == 1
        assert len(qrels) == 1
        assert queries[0].query_id == "q1"
        assert docs[0].doc_id == "d1"
        assert qrels[0].relevance == 1

    def test_load_raw_bright_splits_invalid_query_raises(self, tmp_path: Path):
        raw = tmp_path / "raw" / "bright"
        _write_jsonl(raw / "queries.jsonl", [{"id": "q1"}])  # missing text/query/question
        _write_jsonl(raw / "documents.jsonl", [{"id": "d1", "text": "Doc one"}])
        _write_jsonl(raw / "qrels.jsonl", [{"query_id": "q1", "doc_id": "d1", "relevance": 1}])

        with pytest.raises(BrightSchemaError, match="queries.jsonl"):
            load_raw_bright_splits(raw)


class TestBrightExampleParsing:
    def test_parse_example_row_mapping_docs(self):
        row = {
            "id": "q1",
            "query": "Question?",
            "positive_docs": {"d1": "positive text"},
            "negative_docs": {"d2": {"text": "negative text", "title": "N2"}},
        }
        query, docs, qrels = _parse_example_row(row, row_idx=0)
        assert query.query_id == "q1"
        assert {d.doc_id for d in docs} == {"d1", "d2"}
        rel_map = {q.doc_id: q.relevance for q in qrels}
        assert rel_map["d1"] == 1
        assert rel_map["d2"] == 0

    def test_parse_example_row_missing_docs_raises(self):
        row = {"id": "q1", "query": "Question?"}
        with pytest.raises(BrightSchemaError, match="produced no documents"):
            _parse_example_row(row, row_idx=0)

    def test_parse_example_row_gold_ids_schema(self):
        row = {
            "id": "7",
            "query": "Question?",
            "gold_ids": ["d1", "d2"],
            "excluded_ids": ["d3", "N/A"],
        }
        query, docs, qrels = _parse_example_row(row, row_idx=0, split_name="biology")
        assert query.query_id == "biology:7"
        assert {d.doc_id for d in docs} == {"d1", "d2", "d3"}
        rel_map = {q.doc_id: q.relevance for q in qrels}
        assert rel_map["d1"] == 1
        assert rel_map["d2"] == 1
        assert rel_map["d3"] == 0


class TestBrightDownloadAndCompatibility:
    def test_download_bright_without_network_via_mock(self, tmp_path: Path, monkeypatch):
        fake_datasets = types.ModuleType("datasets")

        def fake_load_dataset(_name, _task, cache_dir=None):
            assert cache_dir is not None
            return {
                "examples": [
                    {
                        "id": "q1",
                        "query": "Question?",
                        "positive_docs": {"d1": "positive text"},
                        "negative_docs": {"d2": {"text": "negative text"}},
                    }
                ]
            }

        fake_datasets.load_dataset = fake_load_dataset
        monkeypatch.setitem(sys.modules, "datasets", fake_datasets)

        queries, docs, qrels = download_bright(
            raw_path=tmp_path / "raw" / "bright",
            task="examples",
            max_examples=None,
        )

        assert len(queries) == 1
        assert len(docs) == 2
        assert len(qrels) == 2

        prefs = preferences_from_qrels(qrels, top_k=10, max_queries=1, seed=7)
        assert len(prefs) == 1
        assert prefs[0].winner_doc_id == "d1"
        assert prefs[0].loser_doc_id == "d2"
