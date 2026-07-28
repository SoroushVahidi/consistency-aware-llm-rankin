from __future__ import annotations

import pytest

from consistency_ranker.statistical_inference import (
    bh_adjust,
    bootstrap_mean_interval,
    by_adjust,
    delta_summary,
    exact_sign_flip_pvalue,
    holm_adjust,
    minimum_detectable_effect_normal,
    monte_carlo_sign_flip_pvalue,
    paired_tost,
    proportion_interval,
    sign_flip_pvalue,
    simulate_mde,
)


def test_delta_summary_all_zero_deltas():
    summary = delta_summary([0.0, 0.0, 0.0])
    assert summary["nonzero_count"] == 0
    assert summary["mean"] == 0.0
    assert summary["observed_standardized_effect"] is None


def test_exact_sign_flip_all_zero_deltas():
    result = exact_sign_flip_pvalue([0.0, 0.0, 0.0])
    assert result.pvalue == 1.0
    assert result.nonzero_count == 0


def test_sign_flip_one_nonzero_delta_uses_exact_enumeration():
    result = sign_flip_pvalue([0.0, 0.0, 0.4], exact_max_nonzero=5)
    assert result.method == "exact_sign_flip"
    assert result.pvalue == pytest.approx(1.0)


def test_exact_sign_flip_symmetric_deltas():
    result = exact_sign_flip_pvalue([0.2, -0.2])
    assert result.pvalue == pytest.approx(1.0)


def test_monte_carlo_sign_flip_is_reproducible():
    left = monte_carlo_sign_flip_pvalue([0.0, 0.0, 0.1, 0.2], reps=1024, seed=19)
    right = monte_carlo_sign_flip_pvalue([0.0, 0.0, 0.1, 0.2], reps=1024, seed=19)
    assert left == right


def test_bootstrap_intervals_cover_multiple_methods():
    values = [0.0, 0.0, 0.1, 0.3, -0.05]
    percentile = bootstrap_mean_interval(values, method="percentile", reps=2000, seed=7)
    basic = bootstrap_mean_interval(values, method="basic", reps=2000, seed=7)
    bca = bootstrap_mean_interval(values, method="bca", reps=2000, seed=7)
    studentized = bootstrap_mean_interval(values, method="studentized", reps=2000, seed=7)
    for result in (percentile, basic, bca, studentized):
        assert result.lower is not None
        assert result.upper is not None
        assert result.lower <= result.upper
        assert 0.0 <= result.frac_gt_zero <= 1.0


def test_bca_edge_case_with_constant_values():
    result = bootstrap_mean_interval([0.0, 0.0, 0.0], method="bca", reps=512, seed=11)
    assert result.lower == pytest.approx(0.0)
    assert result.upper == pytest.approx(0.0)


def test_holm_bh_by_adjustments_are_monotone_and_bounded():
    pvals = [0.01, 0.03, 0.20, None, 0.05]
    holm = holm_adjust(pvals)
    bh = bh_adjust(pvals)
    by = by_adjust(pvals)
    for adjusted in (holm, bh, by):
        numeric = [value for value in adjusted if value is not None]
        assert all(0.0 <= value <= 1.0 for value in numeric)
    assert by[0] >= bh[0]
    assert by[1] >= bh[1]


def test_minimum_detectable_effect_normal_returns_none_for_zero_variance():
    assert minimum_detectable_effect_normal(n=10, sd=0.0, alpha=0.05, power=0.8) is None


def test_simulate_mde_is_reproducible():
    grid = [0.0, 0.01, 0.02]
    first = simulate_mde(
        [0.0, 0.0, 0.02, 0.03, -0.01],
        alpha=0.05,
        power_target=0.8,
        shift_grid=grid,
        simulation_reps=40,
        test_reps=256,
        seed=23,
        exact_max_nonzero=6,
    )
    second = simulate_mde(
        [0.0, 0.0, 0.02, 0.03, -0.01],
        alpha=0.05,
        power_target=0.8,
        shift_grid=grid,
        simulation_reps=40,
        test_reps=256,
        seed=23,
        exact_max_nonzero=6,
    )
    assert first == second


def test_simulate_mde_returns_none_when_all_deltas_zero():
    result = simulate_mde(
        [0.0, 0.0, 0.0],
        alpha=0.05,
        power_target=0.8,
        shift_grid=[0.0, 0.01],
        simulation_reps=20,
        test_reps=64,
        seed=5,
    )
    assert result.detected_shift is None
    assert result.achieved_power is None


def test_paired_tost_detects_equivalence_inside_margin():
    result = paired_tost([0.0, 0.001, -0.001, 0.0], margin=0.01, alpha=0.05)
    assert result.equivalent is True
    assert result.pvalue is not None and result.pvalue <= 0.05


def test_paired_tost_rejects_large_mean_difference():
    result = paired_tost([0.02, 0.02, 0.03, 0.02], margin=0.01, alpha=0.05)
    assert result.equivalent is False


@pytest.mark.parametrize("method", ["wilson", "clopper_pearson"])
def test_proportion_interval_zero_successes_has_nonzero_upper_bound(method):
    # This is the exact defect this function replaces: a nonparametric
    # bootstrap of an all-zero 0/35 sample degenerates to [0.0, 0.0],
    # falsely implying certainty of a zero true rate. A valid binomial
    # proportion interval must not do that.
    result = proportion_interval(0, 35, method=method)
    assert result.proportion == 0.0
    assert result.lower == pytest.approx(0.0, abs=1e-9)
    assert result.upper > 0.0
    assert 0.05 < result.upper < 0.15


@pytest.mark.parametrize("method", ["wilson", "clopper_pearson"])
def test_proportion_interval_all_successes_has_nonone_lower_bound(method):
    result = proportion_interval(35, 35, method=method)
    assert result.proportion == 1.0
    assert result.upper == pytest.approx(1.0, abs=1e-9)
    assert result.lower < 1.0
    assert 0.85 < result.lower < 0.95


@pytest.mark.parametrize("method", ["wilson", "clopper_pearson"])
def test_proportion_interval_single_success(method):
    result = proportion_interval(1, 35, method=method)
    assert result.proportion == pytest.approx(1.0 / 35.0)
    assert 0.0 <= result.lower < result.proportion < result.upper <= 1.0


@pytest.mark.parametrize("method", ["wilson", "clopper_pearson"])
def test_proportion_interval_interior_proportion(method):
    result = proportion_interval(10, 35, method=method)
    assert result.proportion == pytest.approx(10.0 / 35.0)
    assert 0.0 < result.lower < result.proportion < result.upper < 1.0
    assert result.method == method
    assert result.confidence == 0.95


def test_proportion_interval_empty_sample_returns_none_fields():
    result = proportion_interval(0, 0)
    assert result.n == 0
    assert result.proportion is None
    assert result.lower is None
    assert result.upper is None


def test_proportion_interval_rejects_invalid_counts():
    with pytest.raises(ValueError):
        proportion_interval(-1, 10)
    with pytest.raises(ValueError):
        proportion_interval(11, 10)
    with pytest.raises(ValueError):
        proportion_interval(3, -1)


def test_proportion_interval_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        proportion_interval(5, 10, confidence=0.0)
    with pytest.raises(ValueError):
        proportion_interval(5, 10, confidence=1.0)


def test_proportion_interval_rejects_unknown_method():
    with pytest.raises(ValueError):
        proportion_interval(5, 10, method="bootstrap")
