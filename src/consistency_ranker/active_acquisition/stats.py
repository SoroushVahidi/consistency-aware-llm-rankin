"""Paired query-level statistical analysis (Phase 6).

Thin wrappers around the repository's existing statistical primitives
(:mod:`consistency_ranker.statistical_inference`) — no new inference
machinery is implemented here.
"""

from __future__ import annotations

from dataclasses import dataclass

from consistency_ranker.statistical_inference import (
    bootstrap_mean_interval,
    delta_summary,
    holm_adjust,
    sign_flip_pvalue,
)

WIN_TOL = 1e-9


@dataclass(frozen=True)
class PairedComparison:
    label: str
    n: int
    mean_delta: float
    cohen_d: float | None
    ci_lower: float | None
    ci_upper: float | None
    pvalue: float | None
    wins: int
    ties: int
    losses: int


def win_tie_loss(deltas: list[float], *, tol: float = WIN_TOL) -> tuple[int, int, int]:
    wins = sum(1 for d in deltas if d > tol)
    losses = sum(1 for d in deltas if d < -tol)
    ties = len(deltas) - wins - losses
    return wins, ties, losses


def paired_comparison(
    label: str,
    deltas: list[float],
    *,
    bootstrap_reps: int = 10_000,
    seed: int = 13,
) -> PairedComparison:
    """One proposed-vs-baseline paired comparison at a fixed budget/AUC.

    ``deltas`` is per-query ``proposed_metric - baseline_metric``.
    """
    summary = delta_summary(deltas)
    ci = bootstrap_mean_interval(deltas, reps=bootstrap_reps, seed=seed)
    sf = sign_flip_pvalue(deltas)
    wins, ties, losses = win_tie_loss(deltas)
    return PairedComparison(
        label=label,
        n=int(summary["n"] or 0),
        mean_delta=float(summary["mean"] or 0.0),
        cohen_d=summary["observed_standardized_effect"],
        ci_lower=ci.lower,
        ci_upper=ci.upper,
        pvalue=sf.pvalue,
        wins=wins,
        ties=ties,
        losses=losses,
    )


def holm_correct(comparisons: list[PairedComparison]) -> list[float | None]:
    """Holm-adjusted p-values across a family of comparisons, in the same order."""
    return holm_adjust([c.pvalue for c in comparisons])


__all__ = ["PairedComparison", "win_tie_loss", "paired_comparison", "holm_correct"]
