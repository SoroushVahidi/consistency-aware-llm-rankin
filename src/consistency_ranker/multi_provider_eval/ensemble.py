"""Leakage-free ensemble rules over multi-provider judgments."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable, Sequence


def _pair_key(rec: dict[str, Any]) -> str:
    return str(rec["canonical_pair_id"])


def majority_across_models(
    records: Iterable[dict[str, Any]],
    *,
    require_valid: bool = True,
) -> dict[str, dict[str, Any]]:
    """Per canonical pair, majority vote over model/provider winners.

    Uses normalized_winner_id.  Does not consult qrels.
    """
    by_pair: dict[str, list[str]] = defaultdict(list)
    meta: dict[str, dict[str, Any]] = {}
    for r in records:
        if require_valid and not r.get("valid"):
            continue
        w = r.get("normalized_winner_id")
        if w is None:
            continue
        pid = _pair_key(r)
        by_pair[pid].append(str(w))
        meta[pid] = {
            "query_id": r["query_id"],
            "doc_a_id": r["doc_a_id"],
            "doc_b_id": r["doc_b_id"],
        }
    out: dict[str, dict[str, Any]] = {}
    for pid, winners in by_pair.items():
        ctr = Counter(winners)
        top, n = ctr.most_common(1)[0]
        total = sum(ctr.values())
        out[pid] = {
            **meta[pid],
            "canonical_pair_id": pid,
            "winner": top,
            "n_votes": total,
            "margin": n / total,
            "counts": dict(ctr),
            "rule": "majority_across_models",
        }
    return out


def agreement_only_edges(
    records: Iterable[dict[str, Any]],
    *,
    min_models: int = 2,
) -> dict[str, dict[str, Any]]:
    """Retain an edge only when >= min_models distinct models agree on winner."""
    by_pair_model: dict[str, dict[str, str]] = defaultdict(dict)
    meta: dict[str, dict[str, Any]] = {}
    for r in records:
        if not r.get("valid") or r.get("normalized_winner_id") is None:
            continue
        pid = _pair_key(r)
        model_key = f"{r['provider']}::{r['model']}"
        by_pair_model[pid][model_key] = str(r["normalized_winner_id"])
        meta[pid] = {
            "query_id": r["query_id"],
            "doc_a_id": r["doc_a_id"],
            "doc_b_id": r["doc_b_id"],
        }
    out: dict[str, dict[str, Any]] = {}
    for pid, model_winners in by_pair_model.items():
        if len(model_winners) < min_models:
            continue
        ctr = Counter(model_winners.values())
        if len(ctr) != 1:
            continue  # dispute → abstain
        winner = next(iter(ctr))
        out[pid] = {
            **meta[pid],
            "canonical_pair_id": pid,
            "winner": winner,
            "n_models_agreeing": len(model_winners),
            "rule": "agreement_only",
        }
    return out


def confidence_weighted_vote(
    records: Iterable[dict[str, Any]],
    *,
    confidence_weights: dict[str, float] | None = None,
) -> dict[str, dict[str, Any]]:
    """Weight votes by categorical confidence (validation-free defaults)."""
    weights = confidence_weights or {"HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.3}
    by_pair: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    meta: dict[str, dict[str, Any]] = {}
    for r in records:
        if not r.get("valid") or r.get("normalized_winner_id") is None:
            continue
        pid = _pair_key(r)
        w = str(r["normalized_winner_id"])
        conf = (r.get("confidence_category") or "MEDIUM").upper()
        by_pair[pid][w] += float(weights.get(conf, 0.5))
        meta[pid] = {
            "query_id": r["query_id"],
            "doc_a_id": r["doc_a_id"],
            "doc_b_id": r["doc_b_id"],
        }
    out: dict[str, dict[str, Any]] = {}
    for pid, scores in by_pair.items():
        winner = max(scores, key=scores.get)
        total = sum(scores.values())
        out[pid] = {
            **meta[pid],
            "canonical_pair_id": pid,
            "winner": winner,
            "score": scores[winner],
            "margin": scores[winner] / total if total else 0.0,
            "rule": "confidence_weighted",
        }
    return out


def edges_to_preferences(
    edges: Sequence[dict[str, Any]],
) -> list[tuple[str, str, float]]:
    """Convert ensemble edges to (winner, loser, weight) triples per query group.

    Caller should filter by query_id when building per-query graphs.
    """
    prefs: list[tuple[str, str, float]] = []
    for e in edges:
        winner = e["winner"]
        a, b = e["doc_a_id"], e["doc_b_id"]
        loser = b if winner == a else a
        weight = float(e.get("margin") or e.get("n_votes") or 1.0)
        prefs.append((winner, loser, weight))
    return prefs
