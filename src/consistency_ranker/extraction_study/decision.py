"""Predeclared decision rule for the extraction-vs-repair study.

Declared BEFORE inspecting results (per the task's own requirement): a
0.01 nDCG average-gain threshold, with an explicit override when the gain
is small but the lower tail (downside risk) is still consistently
positive -- a small-but-reliable improvement is treated as meaningful even
if it misses the raw mean-threshold cut.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Decision = Literal[
    "EXTRACTION_IMPROVES_RANKING",
    "SELECTIVE_EXTRACTION_ONLY",
    "ORACLE_ONLY_NOT_DEPLOYABLE",
    "NO_MEANINGFUL_EXTRACTION_GAIN",
]

MEANINGFUL_THRESHOLD = 0.01


@dataclass(frozen=True)
class DecisionResult:
    decision: Decision
    rationale: str


def decide(
    *,
    best_fixed_name: str,
    best_fixed_mean_delta: float,
    best_fixed_headroom_ci_lower: float,
    best_fixed_downside_q05: float,
    selection_status: str,
    oracle_mean_delta: float,
    meaningful_threshold: float = MEANINGFUL_THRESHOLD,
) -> DecisionResult:
    """
    Precedence (checked in this fixed order):

    1. ``EXTRACTION_IMPROVES_RANKING`` -- a single fixed extractor's mean
       delta clears the threshold, OR its CI lower bound is positive AND
       its lower-tail (downside_q05) is also positive (strong + consistent
       improvement even though the raw mean is below the threshold).
    2. ``SELECTIVE_EXTRACTION_ONLY`` -- no fixed extractor clears the bar,
       but a deployable per-query selector beats always-incumbent AND
       oracle extractor selection itself has meaningful headroom.
    3. ``ORACLE_ONLY_NOT_DEPLOYABLE`` -- oracle headroom is meaningful but
       no evaluated selector realizes it.
    4. ``NO_MEANINGFUL_EXTRACTION_GAIN`` -- none of the above.
    """
    strong_consistent_lower_tail = best_fixed_headroom_ci_lower > 0 and best_fixed_downside_q05 > 0
    fixed_meaningful = best_fixed_mean_delta >= meaningful_threshold or strong_consistent_lower_tail

    if fixed_meaningful:
        extra = (
            " (mean gain is below the raw threshold, but the CI lower bound and the "
            "worst-case 5% (downside_q05) are both still positive -- a small, consistently "
            "reliable improvement)"
            if best_fixed_mean_delta < meaningful_threshold
            else ""
        )
        return DecisionResult(
            "EXTRACTION_IMPROVES_RANKING",
            f"Extractor '{best_fixed_name}' achieves mean delta {best_fixed_mean_delta:.5f} "
            f"(CI lower bound {best_fixed_headroom_ci_lower:.5f}) over the incumbent{extra} -- "
            "deployable as a fixed replacement, no per-query selection needed.",
        )

    if selection_status == "SUPPORTED" and oracle_mean_delta >= meaningful_threshold:
        return DecisionResult(
            "SELECTIVE_EXTRACTION_ONLY",
            f"No single fixed extractor clears the {meaningful_threshold} threshold "
            f"(best: '{best_fixed_name}' at {best_fixed_mean_delta:.5f}), but a deployable "
            "selector (fixed rule or grouped-CV classifier) beats always-incumbent, and "
            f"oracle extractor selection has meaningful headroom ({oracle_mean_delta:.5f}) -- "
            "benefit is selective (query-dependent), not universal.",
        )

    if oracle_mean_delta >= meaningful_threshold:
        return DecisionResult(
            "ORACLE_ONLY_NOT_DEPLOYABLE",
            f"Oracle extractor selection has meaningful headroom ({oracle_mean_delta:.5f}) "
            "but no evaluated selector (fixed rule or predictive classifier) realizes it on "
            "held-out queries -- the gain exists only under oracle knowledge of the true "
            "labels, not deployably.",
        )

    return DecisionResult(
        "NO_MEANINGFUL_EXTRACTION_GAIN",
        f"Neither a fixed extractor (best: '{best_fixed_name}' at {best_fixed_mean_delta:.5f}), "
        f"a selector, nor the oracle ({oracle_mean_delta:.5f}) clears the "
        f"{meaningful_threshold} threshold -- extraction method choice does not meaningfully "
        "change ranking quality on this data.",
    )


__all__ = ["Decision", "DecisionResult", "MEANINGFUL_THRESHOLD", "decide"]
