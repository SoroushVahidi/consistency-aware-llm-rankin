"""Tests for scripts/generate_manuscript_tables_and_figures.py and, for the
source-loading invariants specifically, scripts/run_repository_scale_headroom_analysis.py.

One slow integration test re-runs the real 76-file unification against
already-committed repository artifacts to verify the exact counts quoted
in the manuscript planning documents (419 queries, 122,203 rows). The
rest use small synthetic DataFrames for speed and isolation.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_module(name: str, relpath: str):
    path = _REPO_ROOT / relpath
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_headroom_mod = _load_module(
    "run_repository_scale_headroom_analysis", "scripts/run_repository_scale_headroom_analysis.py"
)
_mfg_mod = _load_module(
    "generate_manuscript_tables_and_figures", "scripts/generate_manuscript_tables_and_figures.py"
)


# ---------------------------------------------------------------------------
# Slow integration test: real source-file loading invariants.
# ---------------------------------------------------------------------------


def test_real_unified_table_matches_committed_summary_counts():
    """Re-derives the unified table from the real, already-committed source
    files and checks it against the numbers already committed in
    reports/repository_scale_headroom_analysis/summary.json -- this is the
    actual regression guard against silently losing or duplicating a
    source file.
    """
    summary_path = (
        _REPO_ROOT / "reports/repository_scale_headroom_analysis/summary.json"
    )
    if not summary_path.exists():
        pytest.skip("summary.json not present in this checkout")
    committed = json.loads(summary_path.read_text())

    df, coverage = _headroom_mod.build_unified_table()

    assert len(coverage) == committed["n_source_files"] == 76
    n_distinct = df[["dataset", "query_id"]].drop_duplicates().shape[0]
    assert n_distinct == committed["n_distinct_query_dataset_pairs"] == 419
    assert len(df) == committed["n_total_rows"] == 122203
    assert sorted(df["dataset"].dropna().unique().tolist()) == committed["datasets"]


# ---------------------------------------------------------------------------
# Fast synthetic tests: query-by-regime collapsing (no pseudo-replication).
# ---------------------------------------------------------------------------


def _synthetic_df(rows):
    cols = ["dataset", "query_id", "regime", "preserve_metric", "repair_metric", "delta"]
    return pd.DataFrame(rows, columns=cols)


def test_query_by_regime_table_collapses_pool_pair_variants_only():
    # Same query, same regime, 3 "pool/pair variants" -> must collapse to
    # ONE row per (dataset, query_id, regime), not stay as 3 rows.
    rows = [
        {"dataset": "d", "query_id": "q1", "regime": "ms1",
         "preserve_metric": 0.5, "repair_metric": 0.5 + x, "delta": x}
        for x in (0.1, 0.2, 0.3)
    ]
    # Different regime for the same query -> must remain a SEPARATE row.
    rows.append(
        {"dataset": "d", "query_id": "q1", "regime": "ms2",
         "preserve_metric": 0.5, "repair_metric": 0.5, "delta": 0.0}
    )
    df = _synthetic_df(rows)
    out = _mfg_mod._query_by_regime_table(df)
    assert len(out) == 2
    ms1_row = out[out["regime"] == "ms1"].iloc[0]
    assert ms1_row["n_variants"] == 3
    assert ms1_row["delta"] == pytest.approx((0.1 + 0.2 + 0.3) / 3)
    ms2_row = out[out["regime"] == "ms2"].iloc[0]
    assert ms2_row["delta"] == pytest.approx(0.0)


def test_benefit_harm_neutral_ci_uses_proportion_interval_not_degenerate():
    import numpy as np

    delta = np.array([0.0] * 35)  # all-neutral, analogous to a 0/35 rate elsewhere on this branch
    result = _mfg_mod._benefit_harm_neutral_with_ci(delta)
    assert result["n_benefit"] == 0
    # Regression guard: a degenerate bootstrap CI for 0/35 collapses to
    # [0, 0]; a valid proportion interval (Wilson, via
    # statistical_inference.proportion_interval) must not.
    assert result["frac_benefit_ci_upper"] > 0.0
    assert result["mean_benefit_magnitude"] is None
    assert result["mean_harm_magnitude"] is None


def test_benefit_harm_neutral_magnitudes_not_confused_with_counts():
    import numpy as np

    delta = np.array([0.1, 0.2, -0.05, 0.0, 0.0])
    result = _mfg_mod._benefit_harm_neutral_with_ci(delta)
    assert result["n_benefit"] == 2
    assert result["n_harm"] == 1
    assert result["n_neutral"] == 2
    assert result["mean_benefit_magnitude"] == pytest.approx(0.15)
    assert result["mean_harm_magnitude"] == pytest.approx(-0.05)


# ---------------------------------------------------------------------------
# Table generation: structural correctness on synthetic data.
# ---------------------------------------------------------------------------


def _full_synthetic_df():
    rows = []
    for i in range(30):
        rows.append(
            {
                "dataset": "ds1", "query_id": f"q{i}", "regime": "ms1",
                "preserve_metric": 0.5, "repair_metric": 0.5 + (0.01 if i % 3 == 0 else 0.0),
                "delta": 0.01 if i % 3 == 0 else 0.0,
                "repair_algorithm": "greedy", "source_family": "synthetic",
                "repair_cost": 0.1, "largest_scc_size": 3, "graph_density": 0.4,
                "is_cyclic": True,
            }
        )
    return pd.DataFrame(rows)


def test_table_1_coverage_counts_are_consistent():
    df = _full_synthetic_df()
    out = _mfg_mod.table_1_coverage(df)
    ds1_row = out[out["dataset"] == "ds1"].iloc[0]
    all_row = out[out["dataset"] == "ALL (pooled)"].iloc[0]
    assert ds1_row["n_query_regime_rows"] == 30
    assert ds1_row["n_distinct_queries"] == 30
    assert all_row["n_query_regime_rows"] == len(df)


def test_table_4_benefit_harm_neutral_query_level_matches_manual():
    df = _full_synthetic_df()
    agg = df.rename(columns={})[["dataset", "query_id", "delta"]].copy()
    out = _mfg_mod.table_4_benefit_harm_neutral(df, agg)
    all_row = out[(out["slice"] == "ALL") & (out["unit"] == "query-level")].iloc[0]
    assert all_row["n"] == 30
    assert all_row["n_benefit"] == sum(1 for i in range(30) if i % 3 == 0)


# ---------------------------------------------------------------------------
# Determinism and failure modes.
# ---------------------------------------------------------------------------


def test_figure_generation_is_deterministic(tmp_path, monkeypatch):
    agg = pd.DataFrame(
        {
            "dataset": ["ds1"] * 10,
            "query_id": [f"q{i}" for i in range(10)],
            "delta": [0.01 * i - 0.05 for i in range(10)],
        }
    )
    monkeypatch.setattr(_mfg_mod, "FIGURES_DIR", tmp_path)
    _mfg_mod.figure_2_delta_distribution(agg)
    first = hashlib.sha256((tmp_path / "figure_2_delta_distribution.png").read_bytes()).hexdigest()
    (tmp_path / "figure_2_delta_distribution.png").unlink()
    _mfg_mod.figure_2_delta_distribution(agg)
    second = hashlib.sha256((tmp_path / "figure_2_delta_distribution.png").read_bytes()).hexdigest()
    assert first == second


def test_require_raises_on_missing_artifact(tmp_path):
    with pytest.raises(FileNotFoundError):
        _mfg_mod._require(tmp_path / "does_not_exist.csv")


def test_main_refuses_inconsistent_row_count(tmp_path, monkeypatch):
    # per_query_effects.csv row count deliberately does not match
    # summary.json's n_total_rows -- main() must refuse, not silently
    # generate manuscript artifacts from stale/inconsistent inputs.
    effects = tmp_path / "per_query_effects.csv"
    row = {"dataset": ["d"], "query_id": ["q1"], "delta": [0.0]}
    pd.DataFrame(row).to_csv(effects, index=False)
    agg = tmp_path / "per_query_aggregated_effects.csv"
    pd.DataFrame(row).to_csv(agg, index=False)
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps({"n_total_rows": 999}))
    headroom = tmp_path / "headroom_by_regime.csv"
    pd.DataFrame({"slice_type": [], "dataset": [], "regime": []}).to_csv(headroom, index=False)
    predictability = tmp_path / "predictability_upper_bounds.json"
    predictability.write_text("[]")

    monkeypatch.setattr(_mfg_mod, "PER_QUERY_EFFECTS_CSV", effects)
    monkeypatch.setattr(_mfg_mod, "PER_QUERY_AGG_CSV", agg)
    monkeypatch.setattr(_mfg_mod, "SUMMARY_JSON", summary)
    monkeypatch.setattr(_mfg_mod, "HEADROOM_BY_REGIME_CSV", headroom)
    monkeypatch.setattr(_mfg_mod, "PREDICTABILITY_JSON", predictability)

    with pytest.raises(ValueError, match="does not match"):
        _mfg_mod.main()


def test_main_refuses_duplicate_query_rows_in_aggregated_table(tmp_path, monkeypatch):
    effects = tmp_path / "per_query_effects.csv"
    pd.DataFrame({"dataset": ["d", "d"], "query_id": ["q1", "q1"], "delta": [0.0, 0.0]}).to_csv(
        effects, index=False
    )
    agg = tmp_path / "per_query_aggregated_effects.csv"
    # Duplicate (dataset, query_id) row -- not properly aggregated.
    pd.DataFrame({"dataset": ["d", "d"], "query_id": ["q1", "q1"], "delta": [0.0, 0.0]}).to_csv(
        agg, index=False
    )
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps({"n_total_rows": 2}))
    headroom = tmp_path / "headroom_by_regime.csv"
    pd.DataFrame({"slice_type": [], "dataset": [], "regime": []}).to_csv(headroom, index=False)
    predictability = tmp_path / "predictability_upper_bounds.json"
    predictability.write_text("[]")

    monkeypatch.setattr(_mfg_mod, "PER_QUERY_EFFECTS_CSV", effects)
    monkeypatch.setattr(_mfg_mod, "PER_QUERY_AGG_CSV", agg)
    monkeypatch.setattr(_mfg_mod, "SUMMARY_JSON", summary)
    monkeypatch.setattr(_mfg_mod, "HEADROOM_BY_REGIME_CSV", headroom)
    monkeypatch.setattr(_mfg_mod, "PREDICTABILITY_JSON", predictability)

    with pytest.raises(ValueError, match="duplicate"):
        _mfg_mod.main()


def test_table_7_reads_tracked_evidence_table():
    out = _mfg_mod.table_7_claims_and_evidence()
    assert "claim" in out.columns
    assert len(out) >= 10
