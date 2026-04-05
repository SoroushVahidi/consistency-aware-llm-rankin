"""Tests for scripts/build_paper_evidence_package.py (dataset list wiring)."""

from __future__ import annotations

from pathlib import Path


def test_default_datasets_unchanged():
    import scripts.build_paper_evidence_package as bp

    assert bp.DEFAULT_DATASETS == ("scidocs", "fiqa", "hotpotqa", "bright")
    assert bp.DATASETS == bp.DEFAULT_DATASETS


def test_aggregate_graph_and_ndcg_empty_root():
    import scripts.build_paper_evidence_package as bp

    assert bp.aggregate_graph_and_ndcg(Path("/nonexistent/root/xyz")) == []


def test_load_bootstrap_table_empty_root():
    import scripts.build_paper_evidence_package as bp

    assert bp.load_bootstrap_table(Path("/nonexistent/root/xyz")) == []


def test_aggregate_respects_dataset_filter(tmp_path: Path):
    """Only requested dataset names are scanned (no crash when sibling dirs missing)."""
    import scripts.build_paper_evidence_package as bp

    root = tmp_path
    assert bp.aggregate_graph_and_ndcg(root, datasets=("missing_ds",)) == []
