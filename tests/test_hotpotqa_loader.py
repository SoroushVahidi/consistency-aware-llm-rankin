from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from consistency_ranker.data.hotpotqa_loader import download_hotpotqa


def test_download_hotpotqa_attaches_query_metadata(monkeypatch, tmp_path: Path):
    fake_dataset = [
        {
            "id": "q1",
            "question": "Who wrote Hamlet?",
            "supporting_facts": {"title": ["Hamlet"]},
            "context": {
                "title": ["Hamlet", "William Shakespeare"],
                "sentences": [["Hamlet is a play."], ["William Shakespeare wrote Hamlet."]],
            },
        },
        {
            "id": "q2",
            "question": "Which work features Hamlet?",
            "supporting_facts": {"title": ["Hamlet"]},
            "context": {
                "title": ["Hamlet"],
                "sentences": [["Hamlet is a tragedy."]],
            },
        },
    ]

    def fake_load_dataset(*args, **kwargs):
        return fake_dataset

    monkeypatch.setitem(
        sys.modules,
        "datasets",
        SimpleNamespace(load_dataset=fake_load_dataset),
    )

    queries, documents, qrels = download_hotpotqa(tmp_path)

    assert [q.query_id for q in queries] == ["q1", "q2"]
    assert [d.doc_id for d in documents] == [
        "q1::hamlet",
        "q1::william_shakespeare",
        "q2::hamlet",
    ]
    assert [d.metadata for d in documents] == [
        {"query_id": "q1"},
        {"query_id": "q1"},
        {"query_id": "q2"},
    ]
    assert [(q.query_id, q.doc_id, q.relevance) for q in qrels] == [
        ("q1", "q1::hamlet", 1),
        ("q1", "q1::william_shakespeare", 0),
        ("q2", "q2::hamlet", 1),
    ]
