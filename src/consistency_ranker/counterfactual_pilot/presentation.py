"""Presentation-order handling for pairwise judgments."""

from __future__ import annotations

from typing import Literal

PresentationOrder = Literal["ab", "ba"]


def presentation_orders() -> tuple[PresentationOrder, PresentationOrder]:
    return ("ab", "ba")


def map_displayed_preference_to_document(
    preference: str | None,
    *,
    orientation: PresentationOrder,
    doc_a_id: str,
    doc_b_id: str,
) -> str | None:
    """Map displayed A/B labels back to stable document IDs.

    Never infer document identity from the returned letter alone without
    knowing the presentation order.
    """
    if preference is None:
        return None
    pref = str(preference).strip().upper()
    if pref in {"TIE", "ABSTAIN"}:
        return pref
    if pref not in {"A", "B"}:
        return None
    if orientation == "ab":
        return doc_a_id if pref == "A" else doc_b_id
    if orientation == "ba":
        return doc_b_id if pref == "A" else doc_a_id
    raise ValueError(f"unknown orientation: {orientation!r}")


def position_consistent(
    preference_ab: str | None,
    preference_ba: str | None,
    *,
    doc_a_id: str,
    doc_b_id: str,
) -> bool | None:
    """True when AB and BA agree after document-identity remapping."""
    mapped_ab = map_displayed_preference_to_document(
        preference_ab, orientation="ab", doc_a_id=doc_a_id, doc_b_id=doc_b_id
    )
    mapped_ba = map_displayed_preference_to_document(
        preference_ba, orientation="ba", doc_a_id=doc_a_id, doc_b_id=doc_b_id
    )
    if mapped_ab is None or mapped_ba is None:
        return None
    return mapped_ab == mapped_ba
