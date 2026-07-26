"""Feature rows for repair-gain prediction (legacy_v1 vs coverage_v2)."""

from __future__ import annotations

from typing import Any


def features_from_repair_row(row: dict[str, Any]) -> dict[str, float]:
    """Pre-decision structural features available from the reconstructed graph.

    These do not use nDCG / qrels. ``is_cyclic`` and SCC size are observable
    from the preference graph before choosing to repair.
    """
    return {
        "is_cyclic": 1.0 if row.get("is_cyclic") else 0.0,
        "largest_scc_frac": float(row.get("largest_scc") or 0) / max(float(row.get("n_candidates") or 1), 1.0),
        "n_scc_norm": float(row.get("n_scc") or 0) / max(float(row.get("n_candidates") or 1), 1.0),
        "n_candidates_norm": float(row.get("n_candidates") or 0) / 32.0,
        "n_judgments_norm": float(row.get("n_judgments") or 0) / 128.0,
        # FAS weight is post-repair; exclude from deployable predictors.
    }


def attach_gains_and_features(
    gains: list[dict[str, Any]],
    policy_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Join gain rows with structural features from unrepaired policy cells."""
    index = {
        (str(r["dataset"]), str(r["query_id"])): r
        for r in policy_rows
        if r.get("policy") == "unrepaired_copeland"
    }
    out = []
    for g in gains:
        key = (str(g["dataset"]), str(g["query_id"]))
        base = index.get(key) or {}
        feats = features_from_repair_row({**base, **g})
        out.append({**g, **feats})
    return out
