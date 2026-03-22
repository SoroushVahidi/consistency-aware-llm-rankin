"""
Tests for scripts/generate_q1_tables.py
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_MAIN_TABLE_CSV = """\
dataset,variant,n_queries,pct_cyclic,avg_largest_scc,avg_n_edges,mean_graph_ref_bew_pre,mean_graph_ref_bew_post,mean_delta_bew_qrels_pre_minus_post,mean_graph_ref_pic_pre,mean_graph_ref_pic_post,mean_delta_pic_qrels_pre_minus_post,mean_fas_weight_removed,mean_ndcg_prior,mean_ndcg_uco,mean_ndcg_rco,mean_ndcg_uba,mean_ndcg_rba
testds,ms2,100,2.0,1.05,70.0,150.0,149.9,0.1,30.0,29.9,0.1,0.01,0.50,0.52,0.52,0.51,0.51
testds,ms1,100,90.0,12.0,200.0,300.0,298.0,2.0,90.0,80.0,10.0,2.5,0.50,0.51,0.48,0.50,0.50
"""

SAMPLE_BOOTSTRAP_CSV = """\
dataset,variant,pair,n_queries,mean_delta_ndcg,ci95_low,ci95_high,bootstrap_reps
testds,ms2,copeland,100,0.0,0.0,0.0,2000
testds,ms2,balance,100,0.0,0.0,0.0,2000
testds,ms2,copeland_scc_high,100,0.0,0.0,0.0,2000
testds,ms2,copeland_scc_low,0,,,, 2000
testds,ms1,copeland,100,-0.03,-0.05,-0.01,2000
testds,ms1,balance,100,-0.001,-0.002,0.001,2000
testds,ms1,copeland_scc_high,60,-0.04,-0.07,-0.02,2000
testds,ms1,copeland_scc_low,40,0.001,-0.003,0.005,2000
"""


def _make_pub_root(tmp_path: Path) -> Path:
    """Set up a fake pub_root with paper_package/tables containing sample CSVs."""
    tables_dir = tmp_path / "pub_root" / "paper_package" / "tables"
    tables_dir.mkdir(parents=True)
    (tables_dir / "table_graph_ndcg_and_consistency.csv").write_text(
        SAMPLE_MAIN_TABLE_CSV, encoding="utf-8"
    )
    (tables_dir / "table_bootstrap_delta_ndcg.csv").write_text(
        SAMPLE_BOOTSTRAP_CSV, encoding="utf-8"
    )
    (tables_dir / "table_consistency_qrels_bew.csv").write_text(
        SAMPLE_MAIN_TABLE_CSV, encoding="utf-8"
    )
    return tmp_path / "pub_root"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------------------
# Unit tests for table builder functions
# ---------------------------------------------------------------------------


def test_build_main_performance_table(tmp_path):
    """build_main_performance_table produces correct columns and row count."""
    from scripts.generate_q1_tables import build_main_performance_table

    pub_root = _make_pub_root(tmp_path)
    out_dir = tmp_path / "out"
    rows = build_main_performance_table(pub_root, out_dir)

    assert len(rows) == 2
    assert rows[0]["dataset"] == "testds"
    assert rows[0]["vote_construction"] == "ms2"
    # Delta should be ~0 for ms2 (repaired == unrepaired)
    assert float(rows[0]["delta_ndcg_copeland_R_minus_U"]) == pytest.approx(0.0, abs=1e-6)
    # Delta should be negative for ms1
    assert float(rows[1]["delta_ndcg_copeland_R_minus_U"]) < 0

    # CSV was written
    assert (out_dir / "table_main_performance.csv").exists()


def test_build_structural_consistency_table(tmp_path):
    """build_structural_consistency_table has BEW/PIC columns."""
    from scripts.generate_q1_tables import build_structural_consistency_table

    pub_root = _make_pub_root(tmp_path)
    out_dir = tmp_path / "out"
    rows = build_structural_consistency_table(pub_root, out_dir)

    assert len(rows) == 2
    assert "bew_pre" in rows[0]
    assert "pic_pre" in rows[0]
    # ms1 should have larger BEW delta than ms2
    delta_ms2 = float(rows[0]["delta_bew_pre_minus_post"])
    delta_ms1 = float(rows[1]["delta_bew_pre_minus_post"])
    assert delta_ms1 > delta_ms2


def test_build_significance_table(tmp_path):
    """build_significance_table labels significance correctly."""
    from scripts.generate_q1_tables import build_significance_table

    pub_root = _make_pub_root(tmp_path)
    out_dir = tmp_path / "out"
    rows = build_significance_table(pub_root, out_dir)

    # ms2 copeland should be inactive (Δ=0)
    ms2_cop = next(
        r for r in rows if r["vote_construction"] == "ms2" and r["comparison"] == "copeland"
    )
    assert "inactive" in ms2_cop["significance"].lower()

    # ms1 copeland has CI strictly below zero → sig. negative
    ms1_cop = next(
        r for r in rows if r["vote_construction"] == "ms1" and r["comparison"] == "copeland"
    )
    assert "negative" in ms1_cop["significance"].lower()

    # ms1 balance CI straddles zero → not significant
    ms1_bal = next(
        r for r in rows if r["vote_construction"] == "ms1" and r["comparison"] == "balance"
    )
    assert "not significant" in ms1_bal["significance"].lower()

    # n=0 row → n/a
    ms2_low = next(
        r
        for r in rows
        if r["vote_construction"] == "ms2" and r["comparison"] == "copeland_scc_low"
    )
    assert ms2_low["significance"] == "n/a"


def test_build_per_dataset_summary_table(tmp_path):
    """build_per_dataset_summary_table identifies correct best method."""
    from scripts.generate_q1_tables import (
        build_main_performance_table,
        build_per_dataset_summary_table,
        build_significance_table,
    )

    pub_root = _make_pub_root(tmp_path)
    out_dir = tmp_path / "out"
    main_perf = build_main_performance_table(pub_root, out_dir)
    sig = build_significance_table(pub_root, out_dir)
    per_ds = build_per_dataset_summary_table(main_perf, sig, out_dir)

    assert len(per_ds) == 2
    # ms2 best method should be unrepaired_copeland (0.52 > others)
    row_ms2 = next(r for r in per_ds if r["vote_construction"] == "ms2")
    assert "copeland" in row_ms2["best_method"]


def test_build_regime_analysis_table(tmp_path):
    """build_regime_analysis_table contains high/low SCC rows."""
    from scripts.generate_q1_tables import build_regime_analysis_table

    pub_root = _make_pub_root(tmp_path)
    out_dir = tmp_path / "out"
    rows = build_regime_analysis_table(pub_root, out_dir)

    # Should contain rows for both high and low SCC regimes
    regimes = {r["scc_regime"] for r in rows}
    assert "high_scc" in regimes
    assert "low_scc" in regimes

    # High SCC ms1 should be harmful
    ms1_high = next(
        r for r in rows if r["vote_construction"] == "ms1" and r["scc_regime"] == "high_scc"
    )
    assert "harm" in ms1_high["interpretation"].lower()


def test_build_failure_cases_table(tmp_path):
    """build_failure_cases_table captures cases below threshold."""
    from scripts.generate_q1_tables import build_failure_cases_table

    pub_root = _make_pub_root(tmp_path)
    out_dir = tmp_path / "out"
    rows = build_failure_cases_table(pub_root, out_dir, threshold=-0.005)

    # ms1 copeland has mean Δ = -0.03 which is below -0.005
    assert len(rows) >= 1
    datasets = {r["dataset"] for r in rows}
    assert "testds" in datasets


def test_build_failure_cases_table_no_cases(tmp_path):
    """build_failure_cases_table returns empty when threshold is very low."""
    from scripts.generate_q1_tables import build_failure_cases_table

    pub_root = _make_pub_root(tmp_path)
    out_dir = tmp_path / "out"
    rows = build_failure_cases_table(pub_root, out_dir, threshold=-1.0)
    assert rows == []


def test_build_summary_report(tmp_path):
    """build_summary_report produces a non-empty Markdown file."""
    from scripts.generate_q1_tables import (
        build_failure_cases_table,
        build_main_performance_table,
        build_regime_analysis_table,
        build_significance_table,
        build_structural_consistency_table,
        build_summary_report,
    )

    pub_root = _make_pub_root(tmp_path)
    out_dir = tmp_path / "out"

    main_perf = build_main_performance_table(pub_root, out_dir)
    struct = build_structural_consistency_table(pub_root, out_dir)
    sig = build_significance_table(pub_root, out_dir)
    regime = build_regime_analysis_table(pub_root, out_dir)
    failure = build_failure_cases_table(pub_root, out_dir)

    report_path = build_summary_report(main_perf, struct, sig, regime, failure, out_dir)
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "# Q1 Journal Package" in content
    assert "Significance Table" in content
    assert "Regime Analysis" in content


# ---------------------------------------------------------------------------
# Integration test: main() end-to-end
# ---------------------------------------------------------------------------


def test_main_end_to_end(tmp_path):
    """main() with fake pub_root produces all expected output files."""
    from scripts.generate_q1_tables import main

    pub_root = _make_pub_root(tmp_path)
    out_dir = tmp_path / "q1_out"

    rc = main(
        [
            "--pub-root",
            str(pub_root),
            "--out-dir",
            str(out_dir),
        ]
    )
    assert rc == 0

    expected_files = [
        "table_main_performance.csv",
        "table_structural_consistency.csv",
        "table_significance.csv",
        "table_per_dataset_summary.csv",
        "table_regime_analysis.csv",
        "table_failure_cases.csv",
        "summary_report.md",
    ]
    for fname in expected_files:
        assert (out_dir / fname).exists(), f"Expected output file missing: {fname}"


def test_main_missing_pub_root(tmp_path):
    """main() returns non-zero when pub_root does not exist."""
    from scripts.generate_q1_tables import main

    rc = main(
        [
            "--pub-root",
            str(tmp_path / "nonexistent"),
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )
    assert rc != 0


def test_main_empty_pub_root(tmp_path):
    """main() handles empty paper_package (produces zero-row tables without crashing)."""
    from scripts.generate_q1_tables import main

    # Create pub_root but without paper_package/tables inside
    pub_root = tmp_path / "empty_root"
    pub_root.mkdir()
    out_dir = tmp_path / "out"

    rc = main(
        [
            "--pub-root",
            str(pub_root),
            "--out-dir",
            str(out_dir),
        ]
    )
    # Should complete without error (just produce empty tables)
    assert rc == 0
    assert (out_dir / "summary_report.md").exists()


# ---------------------------------------------------------------------------
# Unit tests for internal helpers
# ---------------------------------------------------------------------------


def test_safe_diff_numeric():
    from scripts.generate_q1_tables import _safe_diff

    assert _safe_diff(0.5, 0.3) == pytest.approx(0.2)
    assert _safe_diff("0.5", "0.3") == pytest.approx(0.2)


def test_safe_diff_non_numeric():
    from scripts.generate_q1_tables import _safe_diff

    assert _safe_diff("nan", 0.1) == ""
    assert _safe_diff(None, 0.1) == ""


def test_f_formats_correctly():
    from scripts.generate_q1_tables import _f

    assert _f(3.14159, 2) == "3.14"
    assert _f("3.14159", 2) == "3.14"
    assert _f(None, 4) == ""
    assert _f(float("nan"), 4) == ""


def test_write_csv_creates_parents(tmp_path):
    from scripts.generate_q1_tables import _write_csv

    nested = tmp_path / "a" / "b" / "c.csv"
    _write_csv(nested, [{"x": "1", "y": "2"}])
    assert nested.exists()
    rows = _read_csv(nested)
    assert rows == [{"x": "1", "y": "2"}]


def test_write_csv_empty_rows(tmp_path):
    from scripts.generate_q1_tables import _write_csv

    path = tmp_path / "empty.csv"
    _write_csv(path, [])
    assert path.exists()
    assert path.read_text(encoding="utf-8") == ""
