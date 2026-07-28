"""Tests for the regularized-aggregation pilot CLI's severe-harm-rate
confidence intervals: each method's raw severe-harm rate now carries a
Wilson binomial-proportion interval (previously reported with no interval
at all), while the paired severe-harm-rate-*reduction* statistic (a
paired difference of two correlated binary indicators, not a single-group
proportion) intentionally remains bootstrap-based and is untouched.

Uses purely synthetic rows -- no real oracle or pilot run is required.
"""

from __future__ import annotations

import pytest

from scripts.run_regularized_aggregation_pilot import (
    STATISTICAL_ANALYSIS_SCHEMA_VERSION,
    _statistical_analysis,
)

N_PAIRS = 100  # b05=5, b10=10, b20=20
TEST_IDS = ["t1", "t2", "t3", "t4", "t5"]
DEV_IDS = ["d1", "d2"]
METHODS = ("sparse_copeland", "regularized_bt", "pure_bt_no_prior", "fixed_blend")


def _rows():
    rows = []
    for budget in (5, 10, 20):
        for method in METHODS:
            for i, qid in enumerate(TEST_IDS):
                # sparse_copeland: 2/5 severe harm. Everyone else: 0/5.
                delta = -0.10 if (method == "sparse_copeland" and i < 2) else 0.05
                rows.append(
                    dict(
                        order="random", method=method, budget=budget, query_id=qid,
                        ndcg=0.8 + delta, delta_vs_bm25=delta,
                    )
                )
        for qid in TEST_IDS:
            rows.append(
                dict(order="random", method="initial_bm25", budget=budget, query_id=qid, ndcg=0.8)
            )
    return rows


def _auc_rows():
    rows = []
    for qid in TEST_IDS + DEV_IDS:
        for method in ("regularized_bt", "sparse_copeland", "pure_bt_no_prior", "fixed_blend"):
            rows.append(dict(order="random", method=method, query_id=qid, auc_ndcg=0.85))
    return rows


def _result():
    return _statistical_analysis(_rows(), _auc_rows(), TEST_IDS, [5, 10, 20], N_PAIRS)


def test_result_is_schema_versioned():
    assert _result()["schema_version"] == STATISTICAL_ANALYSIS_SCHEMA_VERSION


def test_severe_harm_zero_events_has_nondegenerate_ci():
    result = _result()
    harm = result["severe_harm"]["5pct"]["regularized_bt"]
    assert harm["n"] == 5
    assert harm["n_severe_harm"] == 0
    assert harm["frac_severe_harm"] == 0.0
    assert harm["frac_severe_harm_ci_method"] == "wilson"
    assert harm["frac_severe_harm_ci95_lower"] == pytest.approx(0.0, abs=1e-9)
    # Regression guard: a bootstrap of an all-zero sample gives exactly 0.0
    # here, falsely implying certainty of zero true risk.
    assert harm["frac_severe_harm_ci95_upper"] > 0.0


def test_severe_harm_interior_rate_has_ci_bracketing_the_estimate():
    result = _result()
    harm = result["severe_harm"]["5pct"]["sparse_copeland"]
    assert harm["n"] == 5
    assert harm["n_severe_harm"] == 2
    assert harm["frac_severe_harm"] == pytest.approx(0.4)
    assert 0.0 < harm["frac_severe_harm_ci95_lower"] < harm["frac_severe_harm"]
    assert harm["frac_severe_harm"] < harm["frac_severe_harm_ci95_upper"] < 1.0


def test_paired_reduction_statistic_is_unaffected_and_still_bootstrap():
    result = _result()
    reduction = result["severe_harm"]["5pct"]["severe_harm_rate_reduction_vs_sparse_copeland"]
    # Still present, still keyed the same way; not converted to a Wilson CI
    # (this is a paired-difference statistic, not a single-group rate).
    assert reduction["n"] == 5
    assert reduction["mean_reduction"] == pytest.approx(0.4)
    assert "ci95_lower" in reduction and "ci95_upper" in reduction
    assert "ci_method" not in reduction
