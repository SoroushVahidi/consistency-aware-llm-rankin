"""Smoke tests for the repository-scale headroom meta-analysis script's
core computation functions. Uses small synthetic DataFrames -- does not
touch real repository data (that would make the test depend on report
directories changing over time) and does not exercise the file-discovery/
loader functions, which are thin, one-shot glue code exercised by the
real run already committed under
reports/repository_scale_headroom_analysis/.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MODULE_PATH = _REPO_ROOT / "scripts" / "run_repository_scale_headroom_analysis.py"

_spec = importlib.util.spec_from_file_location(
    "run_repository_scale_headroom_analysis", _MODULE_PATH
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)


def _df(rows):
    cols = ["dataset", "query_id", "preserve_metric", "repair_metric", "delta"]
    return pd.DataFrame(rows, columns=cols)


def test_headroom_for_group_zero_when_one_action_dominates():
    rows = [{"dataset": "d", "query_id": f"q{i}", "preserve_metric": 0.5,
              "repair_metric": 0.6, "delta": 0.1} for i in range(10)]
    result = _mod._headroom_for_group(_df(rows))
    assert result["headroom"] == pytest.approx(0.0, abs=1e-9)
    assert result["frac_benefit"] == pytest.approx(1.0)
    assert result["frac_harm"] == pytest.approx(0.0)


def test_headroom_for_group_positive_with_heterogeneity():
    rows = [{"dataset": "d", "query_id": f"a{i}", "preserve_metric": 0.2,
              "repair_metric": 0.9, "delta": 0.7} for i in range(5)]
    rows += [{"dataset": "d", "query_id": f"b{i}", "preserve_metric": 0.9,
               "repair_metric": 0.2, "delta": -0.7} for i in range(5)]
    result = _mod._headroom_for_group(_df(rows))
    assert result["headroom"] == pytest.approx(0.35)
    assert result["frac_benefit"] == pytest.approx(0.5)
    assert result["frac_harm"] == pytest.approx(0.5)


def test_query_level_headroom_collapses_repeated_regimes():
    # Same query appears under 3 "regimes" with different but averaging
    # outcomes -- query-level aggregation must collapse these to one row
    # before computing headroom, not treat them as 3 independent queries.
    rows = []
    for regime_delta in (0.1, 0.1, 0.1):
        rows.append(
            {"dataset": "d", "query_id": "q1", "preserve_metric": 0.5,
             "repair_metric": 0.5 + regime_delta, "delta": regime_delta}
        )
    for regime_delta in (-0.1, -0.1):
        rows.append(
            {"dataset": "d", "query_id": "q2", "preserve_metric": 0.5,
             "repair_metric": 0.5 + regime_delta, "delta": regime_delta}
        )
    df = _df(rows)
    result, agg = _mod.query_level_headroom(df)
    assert result["n_distinct_queries"] == 2
    assert set(agg["query_id"]) == {"q1", "q2"}
    q1_row = agg[agg["query_id"] == "q1"].iloc[0]
    assert q1_row["delta"] == pytest.approx(0.1)
    assert q1_row["n_regimes"] == 3


def test_query_level_headroom_matches_row_level_when_no_repetition():
    rows = [{"dataset": "d", "query_id": f"q{i}", "preserve_metric": 0.3,
              "repair_metric": 0.3 + 0.01 * i, "delta": 0.01 * i} for i in range(20)]
    df = _df(rows)
    row_level = _mod._headroom_for_group(df)
    query_level, _ = _mod.query_level_headroom(df)
    assert query_level["headroom"] == pytest.approx(row_level["headroom"], abs=1e-9)
    assert query_level["n_distinct_queries"] == 20


def test_run_headroom_by_skips_small_groups():
    rows = [{"dataset": "big", "query_id": f"q{i}", "preserve_metric": 0.5,
              "repair_metric": 0.5, "delta": 0.0} for i in range(10)]
    rows += [{"dataset": "tiny", "query_id": "q0", "preserve_metric": 0.5,
               "repair_metric": 0.6, "delta": 0.1}]
    df = _df(rows)
    out = _mod.run_headroom_by(df, ["dataset"])
    assert set(out["dataset"]) == {"big"}  # "tiny" (n=1) dropped, min group size is 5


def test_clean_float_handles_missing_and_nonnumeric():
    assert _mod._clean_float("0.5") == pytest.approx(0.5)
    assert _mod._clean_float(None) is None
    assert _mod._clean_float("") is None
    assert _mod._clean_float("not_a_number") is None
    assert _mod._clean_float(float("nan")) is None
