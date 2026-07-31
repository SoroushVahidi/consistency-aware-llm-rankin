"""Orientation consistency and repeated-call aggregation helpers."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Sequence


def orientation_consistency(
    ab_winner: str | None,
    ba_winner: str | None,
    *,
    doc_a_id: str,
    doc_b_id: str,
    ab_valid: bool = True,
    ba_valid: bool = True,
) -> dict[str, Any]:
    """Compare two oriented judgments for the same unordered pair.

    Position-consistent means the normalized winners agree (same semantic
    preference after undoing display order).
    """
    if not ab_valid or not ba_valid:
        return {
            "comparable": False,
            "position_consistent": False,
            "contradictory": False,
            "both_abstain": False,
            "first_position_bias_signal": None,
            "reason": "invalid_or_missing",
        }
    if ab_winner is None and ba_winner is None:
        return {
            "comparable": True,
            "position_consistent": True,
            "contradictory": False,
            "both_abstain": True,
            "first_position_bias_signal": None,
            "reason": "both_abstain",
        }
    if ab_winner is None or ba_winner is None:
        return {
            "comparable": True,
            "position_consistent": False,
            "contradictory": True,
            "both_abstain": False,
            "first_position_bias_signal": None,
            "reason": "one_abstain",
        }
    consistent = ab_winner == ba_winner
    # First-position bias: both orientations chose the displayed Document A.
    # ab chose doc_a and ba chose doc_b (shown as A when swapped).
    first_pos_bias = ab_winner == doc_a_id and ba_winner == doc_b_id
    second_pos_bias = ab_winner == doc_b_id and ba_winner == doc_a_id
    return {
        "comparable": True,
        "position_consistent": consistent,
        "contradictory": not consistent,
        "both_abstain": False,
        "first_position_bias_signal": bool(first_pos_bias),
        "second_position_bias_signal": bool(second_pos_bias),
        "reason": "agree" if consistent else "disagree",
        "agreed_winner": ab_winner if consistent else None,
    }


def majority_vote(
    winners: Sequence[str | None],
    *,
    min_votes: int = 1,
) -> dict[str, Any]:
    """Majority among non-null winners; reports margin and entropy proxy."""
    counted = [w for w in winners if w is not None]
    if len(counted) < min_votes:
        return {
            "winner": None,
            "n_votes": len(counted),
            "margin": 0.0,
            "entropy": None,
            "stable": False,
            "counts": {},
        }
    ctr = Counter(counted)
    top, top_n = ctr.most_common(1)[0]
    second_n = ctr.most_common(2)[1][1] if len(ctr) > 1 else 0
    total = sum(ctr.values())
    # Shannon entropy in bits.
    import math

    entropy = 0.0
    for c in ctr.values():
        p = c / total
        entropy -= p * math.log2(p)
    margin = (top_n - second_n) / total
    return {
        "winner": top,
        "n_votes": total,
        "margin": margin,
        "entropy": entropy,
        "stable": margin >= 0.5 or top_n == total,
        "counts": dict(ctr),
    }


def aggregate_orientation_pair(
    records: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Require both ab and ba; return consistency + agreed edge if consistent."""
    by_orient: dict[str, dict[str, Any]] = {}
    for r in records:
        by_orient[r["displayed_orientation"]] = r
    if "ab" not in by_orient or "ba" not in by_orient:
        return {"ok": False, "reason": "missing_orientation"}
    ab, ba = by_orient["ab"], by_orient["ba"]
    cons = orientation_consistency(
        ab.get("normalized_winner_id"),
        ba.get("normalized_winner_id"),
        doc_a_id=ab["doc_a_id"],
        doc_b_id=ab["doc_b_id"],
        ab_valid=bool(ab.get("valid")),
        ba_valid=bool(ba.get("valid")),
    )
    return {"ok": True, "ab": ab, "ba": ba, **cons}
