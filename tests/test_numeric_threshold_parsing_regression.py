"""Regression tests for the `.holm_significant_at_0.05` attribute-parsing trap.

Caught while building reports/ir_evidence_audit_20260729T182949Z/: pandas
attribute access `df.holm_significant_at_0.05` does not parse as "the
column named `holm_significant_at_0.05`" -- Python tokenizes the trailing
`.05` as a float literal, and `df.holm_significant_at_0` followed
immediately by `.05` with no operator between them is a `SyntaxError` at
parse time (verified directly below), not a silent runtime bug. The fix
is to always use bracket indexing, `df["holm_significant_at_0.05"]`, for
any column name containing a literal `.`.

These tests cover: `.05`; `0.05`; `5e-2`; negative decimals; malformed
expressions; the forbidden attribute-access form itself; and the valid
numeric threshold expressions already used elsewhere in this repository
(`MEANINGFUL_THRESHOLD = 0.01` in `scripts/run_ir_evidence_audit.py`,
`alpha=0.05` throughout `statistical_inference.py`).
"""

from __future__ import annotations

import ast

import pandas as pd
import pytest

from consistency_ranker.statistical_inference import parse_numeric_threshold

# ---------------------------------------------------------------------------
# Bug B, part 1: the attribute-access form itself is forbidden (SyntaxError)
# ---------------------------------------------------------------------------


def test_dotted_column_name_via_attribute_access_is_a_syntax_error() -> None:
    """`df.holm_significant_at_0.05` must never parse as column access.

    Demonstrated with `ast.parse` (a pure syntax check, no execution)
    rather than `exec`/`eval`, so this test itself stays safe and fast.
    """
    source = "df.holm_significant_at_0.05"
    with pytest.raises(SyntaxError):
        ast.parse(source)


def test_bracket_indexing_is_the_correct_and_only_safe_form() -> None:
    """The fix: always use bracket indexing for dotted column names."""
    df = pd.DataFrame({"holm_significant_at_0.05": [False, False, True]})
    # ast.parse must succeed for the correct form (sanity check that our
    # SyntaxError test above is specific to the attribute-access form, not
    # to the presence of a dot anywhere in the statement).
    ast.parse('df["holm_significant_at_0.05"]')
    assert df["holm_significant_at_0.05"].tolist() == [False, False, True]


# ---------------------------------------------------------------------------
# Bug B, part 2: numeric threshold parsing (the broader class of mistake --
# treating a threshold expression as something other than a plain float)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("literal", "expected"),
    [
        (".05", 0.05),
        ("0.05", 0.05),
        ("5e-2", 0.05),
        ("5E-2", 0.05),
        ("-0.01", -0.01),
        ("-.01", -0.01),
        ("0.01", 0.01),
        (0.01, 0.01),
        (1, 1.0),
    ],
)
def test_parse_numeric_threshold_accepts_valid_forms(literal: object, expected: float) -> None:
    assert parse_numeric_threshold(literal) == pytest.approx(expected)


@pytest.mark.parametrize(
    "malformed",
    [
        "0.05.05",  # exactly the shape of the original attribute-access typo, as a string
        "abc",
        "",
        "0.05e",
        "--0.05",
        None,
    ],
)
def test_parse_numeric_threshold_rejects_malformed_expressions(malformed: object) -> None:
    with pytest.raises((ValueError, TypeError)):
        parse_numeric_threshold(malformed)


def test_parse_numeric_threshold_rejects_bool_even_though_float_bool_succeeds() -> None:
    """`float(True) == 1.0` "succeeds" in plain Python but is not a valid
    threshold -- guard against a bool sneaking in as if it were numeric,
    the same family of type-confusion as the `holm_active_ms1_family`
    boolean-vs-float mixup this stage's other regression test covers."""
    with pytest.raises(TypeError):
        parse_numeric_threshold(True)
    with pytest.raises(TypeError):
        parse_numeric_threshold(False)


def test_valid_thresholds_already_used_in_this_repository() -> None:
    """Pin down the exact constants this research thread relies on, so a
    future edit that accidentally turns one into a string/bool/malformed
    expression fails a test immediately instead of silently changing every
    downstream practical-significance decision."""
    meaningful_threshold = 0.01  # scripts/run_ir_evidence_audit.py: MEANINGFUL_THRESHOLD
    holm_alpha = 0.05  # statistical_inference.py / scripts/run_ir_evidence_audit.py: alpha
    assert parse_numeric_threshold(meaningful_threshold) == pytest.approx(0.01)
    assert parse_numeric_threshold(holm_alpha) == pytest.approx(0.05)
    assert isinstance(parse_numeric_threshold(meaningful_threshold), float)
    assert isinstance(parse_numeric_threshold(holm_alpha), float)


def test_run_ir_evidence_audit_meaningful_threshold_constant_is_numeric() -> None:
    """Import the actual audit script and check its threshold constant
    directly, rather than only a hand-copied literal above."""
    import importlib.util
    import pathlib

    script_path = (
        pathlib.Path(__file__).resolve().parent.parent / "scripts" / "run_ir_evidence_audit.py"
    )
    spec = importlib.util.spec_from_file_location("run_ir_evidence_audit", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert parse_numeric_threshold(module.MEANINGFUL_THRESHOLD) == pytest.approx(0.01)
