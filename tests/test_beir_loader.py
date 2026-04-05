"""
Tests for BEIR dataset loader, including the BeirNotAvailableError
network-error handling added in the dataset-access-diagnosis pass.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from consistency_ranker.data.beir_loader import (
    BeirNotAvailableError,
    download_beir_dataset,
    load_documents_from_jsonl,
    load_queries_from_jsonl,
    load_qrels_from_jsonl,
    write_jsonl,
)
from consistency_ranker.data.schema import Document, QrelEntry, Query


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_jsonl(path: Path, rows: list[dict]) -> None:
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


# ---------------------------------------------------------------------------
# Local JSONL I/O
# ---------------------------------------------------------------------------

class TestBeirLocalJsonl:
    def test_load_queries(self, tmp_path):
        path = tmp_path / "queries.jsonl"
        _write_jsonl(path, [
            {"query_id": "q1", "text": "what is beir?"},
            {"query_id": "q2", "text": "another query"},
        ])
        queries = load_queries_from_jsonl(path)
        assert len(queries) == 2
        assert queries[0].query_id == "q1"
        assert queries[1].text == "another query"

    def test_load_documents(self, tmp_path):
        path = tmp_path / "documents.jsonl"
        _write_jsonl(path, [
            {"doc_id": "d1", "text": "document text", "title": "Doc 1"},
        ])
        docs = load_documents_from_jsonl(path)
        assert len(docs) == 1
        assert docs[0].doc_id == "d1"
        assert docs[0].title == "Doc 1"

    def test_load_qrels(self, tmp_path):
        path = tmp_path / "qrels.jsonl"
        _write_jsonl(path, [
            {"query_id": "q1", "doc_id": "d1", "relevance": 2},
        ])
        qrels = load_qrels_from_jsonl(path)
        assert len(qrels) == 1
        assert qrels[0].relevance == 2

    def test_write_jsonl_round_trip(self, tmp_path):
        path = tmp_path / "out.jsonl"
        queries = [Query(query_id="q1", text="hello"), Query(query_id="q2", text="world")]
        write_jsonl(queries, path)
        loaded = load_queries_from_jsonl(path)
        assert [q.query_id for q in loaded] == ["q1", "q2"]


# ---------------------------------------------------------------------------
# BeirNotAvailableError — missing datasets library
# ---------------------------------------------------------------------------

class TestBeirNotAvailableErrorMissingPackage:
    def test_raises_when_datasets_not_installed(self, tmp_path, monkeypatch):
        """download_beir_dataset raises BeirNotAvailableError when 'datasets' is absent."""
        monkeypatch.setitem(sys.modules, "datasets", None)

        with pytest.raises(BeirNotAvailableError, match="'datasets' library"):
            download_beir_dataset(
                corpus_name="BeIR/fiqa",
                qrels_name="BeIR/fiqa-qrels",
                raw_path=tmp_path,
            )


# ---------------------------------------------------------------------------
# BeirNotAvailableError — network failure
# ---------------------------------------------------------------------------

class TestBeirNotAvailableErrorNetworkFailure:
    """download_beir_dataset must raise BeirNotAvailableError on network failure."""

    def test_os_error_becomes_beir_not_available(self, tmp_path, monkeypatch):
        fake = types.ModuleType("datasets")
        fake.load_dataset = lambda *a, **kw: (_ for _ in ()).throw(
            OSError("[Errno -5] No address associated with hostname")
        )
        monkeypatch.setitem(sys.modules, "datasets", fake)

        with pytest.raises(BeirNotAvailableError, match="Could not download"):
            download_beir_dataset("BeIR/fiqa", "BeIR/fiqa-qrels", tmp_path)

    def test_runtime_error_becomes_beir_not_available(self, tmp_path, monkeypatch):
        fake = types.ModuleType("datasets")
        fake.load_dataset = lambda *a, **kw: (_ for _ in ()).throw(
            RuntimeError("Cannot send a request, as the client has been closed.")
        )
        monkeypatch.setitem(sys.modules, "datasets", fake)

        with pytest.raises(BeirNotAvailableError, match="Unexpected error"):
            download_beir_dataset("BeIR/fiqa", "BeIR/fiqa-qrels", tmp_path)

    def test_connection_error_becomes_beir_not_available(self, tmp_path, monkeypatch):
        fake = types.ModuleType("datasets")
        fake.load_dataset = lambda *a, **kw: (_ for _ in ()).throw(
            ConnectionError("Connection refused")
        )
        monkeypatch.setitem(sys.modules, "datasets", fake)

        with pytest.raises(BeirNotAvailableError, match="Could not download"):
            download_beir_dataset("BeIR/fiqa", "BeIR/fiqa-qrels", tmp_path)

    def test_error_message_contains_corpus_name(self, tmp_path, monkeypatch):
        fake = types.ModuleType("datasets")
        fake.load_dataset = lambda *a, **kw: (_ for _ in ()).throw(OSError("DNS failure"))
        monkeypatch.setitem(sys.modules, "datasets", fake)

        with pytest.raises(BeirNotAvailableError, match="BeIR/fiqa"):
            download_beir_dataset("BeIR/fiqa", "BeIR/fiqa-qrels", tmp_path)


# ---------------------------------------------------------------------------
# Happy path with mock datasets library
# ---------------------------------------------------------------------------

class TestBeirDownloadWithMock:
    """Verify download_beir_dataset correctly converts HuggingFace rows."""

    def _make_fake_datasets(self):
        fake = types.ModuleType("datasets")

        corpus_rows = [
            {"_id": "d1", "text": "doc one text", "title": "Doc One"},
            {"_id": "d2", "text": "doc two text", "title": ""},
        ]
        query_rows = [{"_id": "q1", "text": "what is retrieval?"}]
        qrel_rows = [
            {"query-id": "q1", "corpus-id": "d1", "score": 2},
            {"query-id": "q1", "corpus-id": "d2", "score": 0},
        ]

        def fake_load_dataset(name, config=None, cache_dir=None):
            if config == "corpus":
                return {"corpus": corpus_rows}
            if config == "queries":
                return {"queries": query_rows}
            return {"test": qrel_rows}

        fake.load_dataset = fake_load_dataset
        return fake

    def test_returns_correct_queries(self, tmp_path, monkeypatch):
        monkeypatch.setitem(sys.modules, "datasets", self._make_fake_datasets())
        queries, docs, qrels = download_beir_dataset("BeIR/fiqa", "BeIR/fiqa-qrels", tmp_path)
        assert len(queries) == 1
        assert queries[0].query_id == "q1"

    def test_returns_correct_documents(self, tmp_path, monkeypatch):
        monkeypatch.setitem(sys.modules, "datasets", self._make_fake_datasets())
        queries, docs, qrels = download_beir_dataset("BeIR/fiqa", "BeIR/fiqa-qrels", tmp_path)
        assert len(docs) == 2
        assert {d.doc_id for d in docs} == {"d1", "d2"}

    def test_returns_correct_qrels(self, tmp_path, monkeypatch):
        monkeypatch.setitem(sys.modules, "datasets", self._make_fake_datasets())
        queries, docs, qrels = download_beir_dataset("BeIR/fiqa", "BeIR/fiqa-qrels", tmp_path)
        assert len(qrels) == 2
        rel_map = {q.doc_id: q.relevance for q in qrels}
        assert rel_map["d1"] == 2
        assert rel_map["d2"] == 0

    def test_max_docs_limits_corpus(self, tmp_path, monkeypatch):
        monkeypatch.setitem(sys.modules, "datasets", self._make_fake_datasets())
        queries, docs, qrels = download_beir_dataset(
            "BeIR/fiqa", "BeIR/fiqa-qrels", tmp_path, max_docs=1
        )
        assert len(docs) == 1

    def test_max_queries_and_qrels_filtered(self, tmp_path, monkeypatch):
        fake = types.ModuleType("datasets")
        corpus_rows = [
            {"_id": "d1", "text": "a", "title": ""},
            {"_id": "d2", "text": "b", "title": ""},
        ]
        query_rows = [
            {"_id": "q1", "text": "one"},
            {"_id": "q2", "text": "two"},
        ]
        qrel_rows = [
            {"query-id": "q1", "corpus-id": "d1", "score": 1},
            {"query-id": "q2", "corpus-id": "d2", "score": 1},
        ]

        def fake_load_dataset(name, config=None, cache_dir=None):
            if config == "corpus":
                return {"corpus": corpus_rows}
            if config == "queries":
                return {"queries": query_rows}
            return {"test": qrel_rows}

        fake.load_dataset = fake_load_dataset
        monkeypatch.setitem(sys.modules, "datasets", fake)
        queries, docs, qrels = download_beir_dataset(
            "BeIR/fiqa", "BeIR/fiqa-qrels", tmp_path, max_queries=1, max_docs=None
        )
        assert len(queries) == 1
        assert queries[0].query_id == "q1"
        assert all(qr.query_id == "q1" for qr in qrels)
