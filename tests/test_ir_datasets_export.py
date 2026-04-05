"""Unit tests for optional ir-datasets export helpers (mocked, no network)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import importlib.util

from consistency_ranker.data.ir_datasets_export import (
    export_robust04_to_raw,
    export_trec_dl_passage_to_raw,
    ir_datasets_available,
)


def test_ir_datasets_available_matches_environment():
    assert ir_datasets_available() == (importlib.util.find_spec("ir_datasets") is not None)


def test_export_trec_dl_mocked(tmp_path: Path):
    q1 = SimpleNamespace(query_id="q1", text="query one")
    qr1 = SimpleNamespace(query_id="q1", doc_id="d1", relevance=1)
    doc1 = SimpleNamespace(text="passage text", title="")

    mock_ds = MagicMock()
    mock_ds.queries_iter.return_value = [q1]
    mock_ds.qrels_iter.return_value = [qr1]

    mock_store = MagicMock()
    mock_store.get.return_value = doc1

    mock_mcp = MagicMock()
    mock_mcp.docs_store.return_value = mock_store

    def fake_load(name: str):
        if "trec-dl" in name:
            return mock_ds
        if name == "msmarco-passage":
            return mock_mcp
        raise AssertionError(name)

    with patch(
        "consistency_ranker.data.ir_datasets_export._require_ir_datasets"
    ) as req:
        fake_ir = MagicMock()
        fake_ir.load = fake_load
        req.return_value = fake_ir

        export_trec_dl_passage_to_raw(
            tmp_path,
            ir_subset="msmarco-passage/trec-dl-2019",
            max_queries=None,
            force=True,
        )

    assert (tmp_path / "queries.jsonl").exists()
    assert (tmp_path / "documents.jsonl").exists()
    assert (tmp_path / "qrels.jsonl").exists()


def test_export_robust04_mocked(tmp_path: Path):
    q1 = SimpleNamespace(query_id="301", text="robust query")
    qr1 = SimpleNamespace(query_id="301", doc_id="LA123", relevance=1)
    doc1 = SimpleNamespace(text="news text", title="headline")

    mock_ds = MagicMock()
    mock_ds.queries_iter.return_value = [q1]
    mock_ds.qrels_iter.return_value = [qr1]

    mock_store = MagicMock()
    mock_store.get.return_value = doc1
    mock_ds.docs_store.return_value = mock_store

    with patch(
        "consistency_ranker.data.ir_datasets_export._require_ir_datasets"
    ) as req:
        fake_ir = MagicMock()
        fake_ir.load = lambda name: mock_ds
        req.return_value = fake_ir

        export_robust04_to_raw(
            tmp_path,
            max_queries=None,
            max_docs=None,
            force=True,
        )

    assert (tmp_path / "queries.jsonl").read_text(encoding="utf-8").strip()
    assert "LA123" in (tmp_path / "documents.jsonl").read_text(encoding="utf-8")

