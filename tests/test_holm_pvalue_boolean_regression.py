"""Regression tests for the `holm_active_ms1_family == True` pandas trap.

Caught while building reports/ir_evidence_audit_20260729T182949Z/: a column
named `holm_active_ms1_family` in `pool_cutoff_statistics.csv` is a
Holm-adjusted p-value (float, NaN outside the active family), not a
boolean, despite its boolean-sounding name. `series == True` on a float
column silently matches rows where the p-value happens to equal exactly
1.0 (pandas casts `True` -> `1.0`) -- the OPPOSITE of "significant" --
which produced a spurious "24/216 Holm-significant" result before it was
caught (see reports/repo_cleanup_stage1_20260730T004010Z/).

These tests demonstrate the buggy behavior directly (so the trap stays
documented and detectable), then verify the corrected/centralized helper
(`is_significant_pvalue` in `statistical_inference.py`) behaves correctly
across the dtypes and edge cases the bug brief calls out: Python bool,
NumPy boolean values, nullable pandas BooleanDtype, missing values,
string-like values that must not silently become true, and the exact
filtering behavior used by `scripts/run_ir_evidence_audit.py`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from consistency_ranker.statistical_inference import is_significant_pvalue


def test_naive_equals_true_is_the_bug_not_the_fix() -> None:
    """Document the trap: a float p-value of exactly 1.0 matches `== True`.

    This is not testing something we want -- it is pinning down the buggy
    behavior itself, so that if anyone "simplifies" the audit script back
    to `series == True` in the future, this test still shows why that is
    wrong (a p-value of 1.0 is about as non-significant as it gets).
    """
    p_values = pd.Series([1.0, 0.5, 0.01, np.nan])
    naive_mask = p_values == True  # noqa: E712 -- intentionally demonstrating the bug
    assert naive_mask.tolist() == [True, False, False, False]
    # The row the naive mask flags "significant" (p == 1.0) is in fact the
    # least significant row in the series.
    assert p_values[naive_mask].iloc[0] == 1.0


def test_is_significant_pvalue_matches_manuscript_ground_truth() -> None:
    """Mirrors pool_cutoff_statistics.csv's active-ms1-family shape.

    0/110 rows should be significant at alpha=0.05, matching the
    manuscript's documented figure exactly (see
    reports/ir_evidence_audit_20260729T182949Z/FINAL_IR_EVIDENCE_AUDIT.md).
    """
    # 108 non-significant p-values (including several exact 1.0s -- the
    # values that triggered the original bug), 2 NaN (outside the active
    # family), 0 truly significant.
    values = [1.0] * 40 + [0.9] * 68 + [np.nan] * 2
    series = pd.Series(values, name="holm_active_ms1_family")
    mask = is_significant_pvalue(series, alpha=0.05)
    assert int(mask.sum()) == 0
    assert len(mask) == len(series)

    # Now inject two genuinely significant p-values and confirm they -- and
    # only they -- are flagged.
    values[5] = 0.001
    values[70] = 0.049
    series2 = pd.Series(values, name="holm_active_ms1_family")
    mask2 = is_significant_pvalue(series2, alpha=0.05)
    assert int(mask2.sum()) == 2
    assert mask2.iloc[5] and mask2.iloc[70]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0, True),
        (0.049, True),
        (0.05, False),  # boundary: not strictly less than alpha
        (0.05000001, False),
        (0.5, False),
        (1.0, False),  # the exact value that triggered the original bug
    ],
)
def test_is_significant_pvalue_boundary_values(value: float, expected: bool) -> None:
    mask = is_significant_pvalue(pd.Series([value]), alpha=0.05)
    assert bool(mask.iloc[0]) is expected


def test_missing_values_are_not_significant() -> None:
    """NaN, None, and pd.NA must all resolve to 'not significant', not error."""
    series = pd.Series([np.nan, None, pd.NA, 0.5], dtype=object)
    mask = is_significant_pvalue(series, alpha=0.05)
    assert mask.tolist() == [False, False, False, False]


def test_python_bool_column_is_rejected() -> None:
    """A plain Python-bool-dtype series must never be fed to this helper."""
    series = pd.Series([True, False, True])
    assert series.dtype == bool
    with pytest.raises(TypeError, match="boolean dtype"):
        is_significant_pvalue(series)


def test_numpy_bool_column_is_rejected() -> None:
    series = pd.Series(np.array([True, False], dtype=np.bool_))
    with pytest.raises(TypeError, match="boolean dtype"):
        is_significant_pvalue(series)


def test_nullable_pandas_boolean_dtype_is_rejected() -> None:
    """pandas' nullable BooleanDtype (pd.array([...], dtype='boolean'))."""
    series = pd.Series(pd.array([True, False, None], dtype="boolean"))
    assert isinstance(series.dtype, pd.BooleanDtype)
    with pytest.raises(TypeError, match="boolean dtype"):
        is_significant_pvalue(series)


def test_string_like_true_false_values_are_rejected_not_coerced() -> None:
    """Strings such as "True"/"False"/"significant" must not silently pass.

    `float("True")` raises `ValueError`; `pandas.to_numeric(errors="raise")`
    surfaces the same failure -- this helper must not swallow it or, worse,
    coerce "True" into a numeric 1.0 the way `bool("True")` (truthy for any
    non-empty string) or `pandas`'s `True` casting quietly would.
    """
    series = pd.Series(["True", "False", "0.01"])
    with pytest.raises((ValueError, TypeError)):
        is_significant_pvalue(series)


def test_valid_numeric_strings_are_accepted() -> None:
    """A column of numeric-string p-values (e.g. read from a raw CSV) should
    still work -- only boolean-looking tokens are rejected, not numbers
    that happen to be strings."""
    series = pd.Series(["0.001", "0.9", "1.0", None])
    mask = is_significant_pvalue(series, alpha=0.05)
    assert mask.tolist() == [True, False, False, False]


def test_genuinely_boolean_significance_column_is_used_directly_not_via_helper() -> None:
    """Sanity check on the OTHER column shape in this codebase.

    `holm_significant_at_0.05` in `exact_larger_pool_family_statistics.csv`
    and `baseline_targeted_tests_primary_canonical.csv` is genuinely
    `dtype == bool` (verified against the tracked tables in
    reports/final_revision_task4_exact_baseline_fairness_20260715/tables/).
    For that column, `== True` (or just using the column directly) is
    correct -- this helper is intentionally NOT used there, and this test
    documents why the two cases must never be conflated.
    """
    genuinely_boolean = pd.Series([False, False, False], name="holm_significant_at_0.05")
    assert genuinely_boolean.dtype == bool
    n_sig = int((genuinely_boolean == True).sum())  # noqa: E712 -- correct here, unlike the float case
    assert n_sig == 0
    # And calling the new helper on it should raise, by design.
    with pytest.raises(TypeError, match="boolean dtype"):
        is_significant_pvalue(genuinely_boolean)
