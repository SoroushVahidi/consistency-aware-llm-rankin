"""Selective graph construction with abstention policies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import networkx as nx

from consistency_ranker.reliability_repair.evidence_aggregation import PairAggregate

AbstentionPolicy = Literal[
    "none",
    "reliability_threshold",
    "margin_threshold",
    "min_support",
    "orientation_required",
    "multi_source_agreement",
    "confidence_interval",
    "validation_threshold",
]


@dataclass
class EdgeDecision:
    pair_id: str
    doc_i: str
    doc_j: str
    keep: bool
    direction: int  # +1: i→j (i preferred), -1: j→i
    reliability: float
    importance: float
    removal_cost: float
    weight: float
    reason: str
    query_id: str


def decide_edge(
    agg: PairAggregate,
    *,
    reliability: float,
    importance: float = 1.0,
    policy: AbstentionPolicy = "reliability_threshold",
    tau: float = 0.25,
    margin_tau: float = 0.2,
    min_support: int = 1,
    weight_mode: Literal["count", "margin", "reliability"] = "reliability",
) -> EdgeDecision:
    """Decide whether to add a directed edge for this unordered pair."""
    d = int(agg.d)
    if d == 0 and policy != "none":
        return EdgeDecision(
            pair_id=agg.canonical_pair_id,
            doc_i=agg.doc_i,
            doc_j=agg.doc_j,
            keep=False,
            direction=0,
            reliability=reliability,
            importance=importance,
            removal_cost=0.0,
            weight=0.0,
            reason="no_direction",
            query_id=agg.query_id,
        )

    keep = True
    reason = "accepted"
    feats = agg.features

    if policy == "none":
        keep = d != 0
        reason = "no_abstention" if keep else "no_direction"
    elif policy == "reliability_threshold":
        keep = d != 0 and reliability >= tau
        reason = "reliability_ok" if keep else "reliability_below_tau"
    elif policy == "margin_threshold":
        keep = d != 0 and abs(agg.m) >= margin_tau
        reason = "margin_ok" if keep else "margin_below_tau"
    elif policy == "min_support":
        keep = d != 0 and agg.n_valid_directional >= min_support
        reason = "support_ok" if keep else "insufficient_support"
    elif policy == "orientation_required":
        keep = d != 0 and float(feats.get("orientation_agreement", 0.0)) >= 0.999
        reason = "orientation_ok" if keep else "orientation_inconsistent"
    elif policy == "multi_source_agreement":
        keep = (
            d != 0
            and float(feats.get("model_diversity", 0.0)) >= 2.0
            and float(feats.get("model_agreement", 0.0)) >= 0.999
        )
        reason = "multi_source_ok" if keep else "need_multi_source_agreement"
    elif policy == "confidence_interval":
        # Wilson-ish: require margin and support
        keep = d != 0 and abs(agg.m) >= margin_tau and agg.n_valid_directional >= min_support
        reason = "ci_ok" if keep else "ci_reject"
    elif policy == "validation_threshold":
        keep = d != 0 and reliability >= tau
        reason = "validation_tau" if keep else "below_validation_tau"
    else:
        raise ValueError(f"Unknown abstention policy {policy!r}")

    if weight_mode == "count":
        w = float(max(agg.n_plus, agg.n_minus))
    elif weight_mode == "margin":
        w = float(abs(agg.m))
    else:
        w = float(reliability)

    cost = float(reliability * importance * max(w, 1e-12))
    return EdgeDecision(
        pair_id=agg.canonical_pair_id,
        doc_i=agg.doc_i,
        doc_j=agg.doc_j,
        keep=keep,
        direction=d if keep else 0,
        reliability=float(reliability),
        importance=float(importance),
        removal_cost=cost if keep else 0.0,
        weight=w if keep else 0.0,
        reason=reason,
        query_id=agg.query_id,
    )


def build_selective_graph(
    decisions: list[EdgeDecision],
    *,
    cost_attr: str = "removal_cost",
) -> tuple[nx.DiGraph, dict[str, Any]]:
    """Build a DiGraph with at most one directed edge per unordered pair.

    Edge attributes: weight, reliability, importance, removal_cost.
    High ``removal_cost`` means **expensive to remove** (preserve if possible).
    """
    g = nx.DiGraph()
    omitted = []
    kept = []
    for dec in decisions:
        g.add_node(dec.doc_i)
        g.add_node(dec.doc_j)
        if not dec.keep or dec.direction == 0:
            omitted.append(dec)
            continue
        if dec.direction == 1:
            u, v = dec.doc_i, dec.doc_j
        else:
            u, v = dec.doc_j, dec.doc_i
        g.add_edge(
            u,
            v,
            weight=dec.weight,
            reliability=dec.reliability,
            importance=dec.importance,
            removal_cost=dec.removal_cost,
            pair_id=dec.pair_id,
        )
        kept.append(dec)
    # Enforce one directed edge per unordered pair (no two-cycles from construction)
    two_cycles = 0
    for u, v in list(g.edges()):
        if g.has_edge(v, u):
            two_cycles += 1
    meta = {
        "n_kept": len(kept),
        "n_omitted": len(omitted),
        "n_edges": g.number_of_edges(),
        "n_nodes": g.number_of_nodes(),
        "construction_two_cycles": two_cycles,
        "omitted_reasons": _count_reasons(omitted),
        "cost_attr": cost_attr,
    }
    return g, meta


def _count_reasons(decs: list[EdgeDecision]) -> dict[str, int]:
    out: dict[str, int] = {}
    for d in decs:
        out[d.reason] = out.get(d.reason, 0) + 1
    return out
