"""Configurable label generation for the preserve-vs-repair prediction task.

Two label families over the same per-query records
(``oracle_headroom.PreserveRepairRecord``):

- regression: ``y_q = delta_q`` (the raw repair effect);
- three-way classification: ``beneficial`` / ``neutral`` / ``harmful``,
  parameterized by a predeclared, sensitivity-tested threshold ``epsilon``
  -- never hard-coded to one value, per the roadmap doc's requirement.

This module produces LABELS only. It must never be imported by feature-
extraction code -- ``assert_no_outcome_leakage`` exists precisely to catch
that mistake in tests, mirroring
``policy_selection.gate_features.assert_no_qrel_keys``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from consistency_ranker.repair_selector_mining.oracle_headroom import PreserveRepairRecord

ThreeWayLabel = Literal["beneficial", "neutral", "harmful"]

# Substrings that must never appear in a feature name -- they name the
# outcome, not something observable before choosing an action. Mirrors
# policy_selection.gate_features.assert_no_qrel_keys's leakage-guard idea,
# generalized to this action space's own outcome vocabulary.
_FORBIDDEN_FEATURE_SUBSTRINGS = (
    "ndcg",
    "delta",
    "oracle",
    "repair_gain",
    "gold",
    "post_repair",
    "label",
    "target",
)


def regression_labels(records: list[PreserveRepairRecord]) -> dict[tuple[str, str], float]:
    """y_q = delta_q, keyed by (dataset, query_id)."""
    return {r.key(): r.delta for r in records}


def three_way_label(delta: float, *, epsilon: float) -> ThreeWayLabel:
    if epsilon < 0:
        raise ValueError(f"epsilon must be >= 0, got {epsilon}")
    if delta > epsilon:
        return "beneficial"
    if delta < -epsilon:
        return "harmful"
    return "neutral"


def three_way_labels(
    records: list[PreserveRepairRecord], *, epsilon: float
) -> dict[tuple[str, str], ThreeWayLabel]:
    """Three-way beneficial/neutral/harmful labels at one fixed epsilon."""
    return {r.key(): three_way_label(r.delta, epsilon=epsilon) for r in records}


@dataclass(frozen=True)
class EpsilonSensitivityRow:
    epsilon: float
    n_beneficial: int
    n_neutral: int
    n_harmful: int
    frac_beneficial: float
    frac_neutral: float
    frac_harmful: float


def label_sensitivity_table(
    records: list[PreserveRepairRecord], epsilons: list[float]
) -> list[EpsilonSensitivityRow]:
    """Class balance at each candidate epsilon -- required before picking one.

    A threshold chosen without looking at this table (or chosen and then
    silently never revisited) is exactly the "arbitrary hard-coded
    threshold" the roadmap doc prohibits. This function does not pick a
    threshold; it only reports the consequences of each candidate so a
    human (or a predeclared rule, e.g. "smallest epsilon giving >=10% in
    each non-neutral class") can choose one and record the choice in the
    decision log.
    """
    if not records:
        raise ValueError("label_sensitivity_table requires at least one record")
    n = len(records)
    rows = []
    for eps in epsilons:
        labels = [three_way_label(r.delta, epsilon=eps) for r in records]
        n_b = sum(1 for label in labels if label == "beneficial")
        n_h = sum(1 for label in labels if label == "harmful")
        n_neu = n - n_b - n_h
        rows.append(
            EpsilonSensitivityRow(
                epsilon=eps,
                n_beneficial=n_b,
                n_neutral=n_neu,
                n_harmful=n_h,
                frac_beneficial=n_b / n,
                frac_neutral=n_neu / n,
                frac_harmful=n_h / n,
            )
        )
    return rows


def assert_no_outcome_leakage(feature_names: list[str]) -> None:
    """Raise if any candidate feature name references the repair outcome.

    Pre-repair features must be computable before the repair-vs-preserve
    decision is made; this is a fast, cheap guard against a name-level
    mistake (e.g. accidentally including ``"delta_ndcg"`` as a "feature"),
    not a substitute for the tests in ``tests/test_oracle_headroom.py``
    that check actual leakage-free construction.
    """
    lowered = [name.lower() for name in feature_names]
    for name in lowered:
        for forbidden in _FORBIDDEN_FEATURE_SUBSTRINGS:
            if forbidden in name:
                raise AssertionError(
                    f"Feature name {name!r} contains forbidden substring "
                    f"{forbidden!r} -- this looks like an outcome/label, not "
                    "a pre-repair feature. Rename or remove it."
                )


__all__ = [
    "ThreeWayLabel",
    "regression_labels",
    "three_way_label",
    "three_way_labels",
    "EpsilonSensitivityRow",
    "label_sensitivity_table",
    "assert_no_outcome_leakage",
]
