"""Smoke tests for scripts/run_metric_aware_first_experiment.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_SCRIPT = _REPO / "scripts" / "run_metric_aware_first_experiment.py"


def test_discover_inputs_raises_without_default_paths(monkeypatch, tmp_path: Path):
    import scripts.run_metric_aware_first_experiment as m

    monkeypatch.setattr(m, "INPUT_CANDIDATES", [tmp_path / "missing"])
    with pytest.raises(FileNotFoundError, match="Could not find SciDocs ms1"):
        m._discover_inputs(None)


def test_discover_inputs_accepts_explicit_root(tmp_path: Path):
    import scripts.run_metric_aware_first_experiment as m

    root = tmp_path / "scidocs"
    root.mkdir()
    for name in (
        "query_ids.txt",
        "votes_ms1.jsonl",
        "scores_bm25.jsonl",
        "scores_tfidf.jsonl",
        "scores_minilm.jsonl",
    ):
        (root / name).write_text("x\n" if name.endswith(".txt") else '{"x":1}\n', encoding="utf-8")

    found = m._discover_inputs(root)
    assert found.resolve() == root.resolve()


def test_discover_accepts_bm25_tfidf_without_minilm(tmp_path: Path):
    import scripts.run_metric_aware_first_experiment as m

    root = tmp_path / "scidocs"
    root.mkdir()
    for name in (
        "query_ids.txt",
        "votes_ms1.jsonl",
        "scores_bm25.jsonl",
        "scores_tfidf.jsonl",
    ):
        (root / name).write_text("q\n" if name.endswith(".txt") else '{"q":1}\n', encoding="utf-8")

    found = m._discover_inputs(root)
    assert found == root.resolve()
    paths = m._score_prior_paths(found)
    assert len(paths) == 2
    assert paths[0].name == "scores_bm25.jsonl"


def test_discover_prefers_tree_with_all_three_score_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    partial = tmp_path / "pub_vote_cmp_all4" / "scidocs"
    full = tmp_path / "pub_vote_cmp_v2" / "scidocs"
    for root in (partial, full):
        root.mkdir(parents=True)
        names = (
            "query_ids.txt",
            "votes_ms1.jsonl",
            "scores_bm25.jsonl",
            "scores_tfidf.jsonl",
        )
        for name in names:
            body = "q\n" if name.endswith(".txt") else '{"q":1}\n'
            (root / name).write_text(body, encoding="utf-8")
        if root is full:
            (root / "scores_minilm.jsonl").write_text('{"q":1}\n', encoding="utf-8")

    import scripts.run_metric_aware_first_experiment as m

    monkeypatch.setattr(m, "INPUT_CANDIDATES", [partial, full])
    found = m._discover_inputs(None)
    assert found.resolve() == full.resolve()


def test_dry_run_exits_zero(tmp_path: Path):
    root = tmp_path / "scidocs"
    root.mkdir()
    for name in (
        "query_ids.txt",
        "votes_ms1.jsonl",
        "scores_bm25.jsonl",
        "scores_tfidf.jsonl",
        "scores_minilm.jsonl",
    ):
        (root / name).write_text("q1\n" if name.endswith(".txt") else '{"q":1}\n', encoding="utf-8")
    out = tmp_path / "out"
    r = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--dry-run",
            "--max-queries",
            "1",
            "--inputs-root",
            str(root),
            "--output-root",
            str(out),
        ],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
