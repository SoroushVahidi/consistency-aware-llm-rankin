"""
metric_aware_repair.py
======================
Training-free **metric-aware** edge weights for minimum feedback-arc repair.

Greedy FAS removes *low-weight* cycle edges.  Re-weighting edges by a
LambdaRank-style surrogate makes “important” disagreements (near the top of a
prior ranking, with large pseudo-gain spread) **harder to delete**, steering
repair toward edges that matter less for a DCG-shaped objective.

Default combination (configurable via :func:`metric_aware_edge_weights`)::

    w_new = w_conf * (1 + beta * u)

where ``u`` is a non-negative pairwise utility and ``w_conf`` is the original
graph edge weight (vote mass / confidence).

References (context, not dependencies): LambdaRank (:math:`\\lambda`-gradients
for nDCG), pairwise reranking graphs (e.g. PRP-Graph, BlitzRank).
"""

from __future__ import annotations

import math
from typing import Literal

import networkx as nx

GainSource = Literal["prior_score", "rank", "qrels_oracle"]


def dcg_discount(pos: int) -> float:
    """DCG position discount for 1-based rank *pos* (first position = 1)."""
    if pos < 1:
        pos = 1
    return 1.0 / math.log2(float(pos) + 1.0)


def gain_from_relevance_proxy(rel: float) -> float:
    """Standard DCG gain :math:`2^{\\mathrm{rel}} - 1` with mild clamping."""
    rel = max(0.0, float(rel))
    if rel > 30.0:
        rel = 30.0
    return (2.0**rel) - 1.0


def estimate_pair_swap_utility(
    pos_i: int,
    pos_j: int,
    gain_i: float,
    gain_j: float,
    *,
    tail_scale: float = 0.05,
    focus_top_k: int | None = None,
) -> float:
    """Surrogate utility for caring about edge *i* → *j* (prefer *i* over *j*).

    Uses a LambdaRank-style magnitude::

        u ≈ |gain_i - gain_j| * |discount(pos_i) - discount(pos_j)|

    When *focus_top_k* is set, edges whose **worse** endpoint rank exceeds *k*
    are down-weighted by *tail_scale* so head-of-list disagreements dominate.
    """
    di = dcg_discount(pos_i)
    dj = dcg_discount(pos_j)
    u = abs(gain_i - gain_j) * abs(di - dj)
    if focus_top_k is not None and focus_top_k > 0:
        worse = max(pos_i, pos_j)
        if worse > focus_top_k:
            u *= tail_scale
    return float(u)


def _positions_from_prior(
    prior_scores: dict[str, float],
    nodes: set[str],
) -> dict[str, int]:
    """1-based ranks: best prior = 1."""
    scored = [(n, float(prior_scores.get(n, 0.0))) for n in nodes]
    scored.sort(key=lambda x: (-x[1], x[0]))
    return {n: r for r, (n, _) in enumerate(scored, start=1)}


def _gains_prior_score(
    prior_scores: dict[str, float],
    nodes: set[str],
) -> dict[str, float]:
    """Min-max normalize prior scores per query to [0, 1], then use as *rel* proxy."""
    if not nodes:
        return {}
    vals = [float(prior_scores.get(n, 0.0)) for n in nodes]
    lo, hi = min(vals), max(vals)
    if hi - lo <= 1e-12:
        return {n: 0.0 for n in nodes}
    return {n: (float(prior_scores.get(n, 0.0)) - lo) / (hi - lo) for n in nodes}


def _gains_rank_proxy(nodes: set[str], positions: dict[str, int]) -> dict[str, float]:
    """Rel proxy = (n - pos + 1) / n so higher = better rank."""
    n = max(len(nodes), 1)
    return {doc: float(n - positions.get(doc, n) + 1) / float(n) for doc in nodes}


def _rel_and_positions_for_edges(
    graph: nx.DiGraph,
    *,
    prior_scores: dict[str, float],
    gain_source: str,
    qrels_gain_map: dict[str, float] | None,
) -> tuple[dict[str, float], dict[str, int]]:
    nodes = set(graph.nodes())
    positions = _positions_from_prior(prior_scores, nodes)
    if gain_source == "prior_score":
        rel_proxy = _gains_prior_score(prior_scores, nodes)
    elif gain_source == "rank":
        rel_proxy = _gains_rank_proxy(nodes, positions)
    elif gain_source == "qrels_oracle":
        if qrels_gain_map is None:
            raise ValueError("qrels_oracle gain_source requires qrels_gain_map")
        rel_proxy = {n: float(qrels_gain_map.get(n, 0.0)) for n in nodes}
    else:
        raise ValueError(f"Unknown gain_source: {gain_source!r}")
    return rel_proxy, positions


def metric_aware_edge_weights(
    graph: nx.DiGraph,
    *,
    prior_scores: dict[str, float],
    gain_source: GainSource = "prior_score",
    qrels_gain_map: dict[str, float] | None = None,
    beta: float = 1.0,
    focus_top_k: int | None = None,
    tail_scale: float = 0.05,
) -> dict[tuple[str, str], float]:
    """Return new edge weight for each directed edge (training-free).

    Formula: ``w_new = w_conf * (1 + beta * utility)``.

    Parameters
    ----------
    graph:
        Preference graph (weights = confidence / vote mass).
    prior_scores:
        Per-document score prior (same signal as hybrid RRF extractors).
    gain_source:
        How to set pseudo-relevance: ``prior_score`` (default), ``rank``, or
        ``qrels_oracle`` (diagnostic: uses *qrels_gain_map* as rel).
    qrels_gain_map:
        Doc → non-negative relevance-like value (e.g. graded qrels) when
        *gain_source* is ``qrels_oracle``.
    beta:
        Strength of metric-aware term (0 recovers multiplicative identity on
        the confidence factor only if utility=0; use small beta for gentle effect).
    focus_top_k:
        If set, down-weight utilities for edges whose worse endpoint rank exceeds *k*.
    tail_scale:
        Multiplier applied to tail utilities when *focus_top_k* is used.
    """
    rel_proxy, positions = _rel_and_positions_for_edges(
        graph,
        prior_scores=prior_scores,
        gain_source=gain_source,
        qrels_gain_map=qrels_gain_map,
    )
    nodes = set(graph.nodes())
    out: dict[tuple[str, str], float] = {}
    for u, v, data in graph.edges(data=True):
        conf = float(data.get("weight", 1.0))
        gi = gain_from_relevance_proxy(rel_proxy.get(u, 0.0))
        gj = gain_from_relevance_proxy(rel_proxy.get(v, 0.0))
        pi = positions.get(u, len(nodes) + 1)
        pj = positions.get(v, len(nodes) + 1)
        util = estimate_pair_swap_utility(
            pi,
            pj,
            gi,
            gj,
            tail_scale=tail_scale,
            focus_top_k=focus_top_k,
        )
        out[(u, v)] = conf * (1.0 + beta * util)
    return out


def reweight_graph_for_metric_aware_fas(
    graph: nx.DiGraph,
    *,
    prior_scores: dict[str, float],
    gain_source: GainSource = "prior_score",
    qrels_gain_map: dict[str, float] | None = None,
    beta: float = 1.0,
    focus_top_k: int | None = None,
    tail_scale: float = 0.05,
) -> nx.DiGraph:
    """Copy *graph* with ``weight`` replaced by metric-aware weights.

    Preserves original weight on attribute ``weight_plain`` and stores per-edge
    ``metric_aware_utility`` for diagnostics.
    """
    rel_proxy, positions = _rel_and_positions_for_edges(
        graph,
        prior_scores=prior_scores,
        gain_source=gain_source,
        qrels_gain_map=qrels_gain_map,
    )
    nodes = set(graph.nodes())
    out = nx.DiGraph()
    out.add_nodes_from(graph.nodes())
    for u, v, data in graph.edges(data=True):
        conf = float(data.get("weight", 1.0))
        gi = gain_from_relevance_proxy(rel_proxy.get(u, 0.0))
        gj = gain_from_relevance_proxy(rel_proxy.get(v, 0.0))
        pi = positions.get(u, len(nodes) + 1)
        pj = positions.get(v, len(nodes) + 1)
        util = estimate_pair_swap_utility(
            pi,
            pj,
            gi,
            gj,
            tail_scale=tail_scale,
            focus_top_k=focus_top_k,
        )
        w_new = conf * (1.0 + beta * util)
        out.add_edge(
            u,
            v,
            weight=w_new,
            weight_plain=conf,
            metric_aware_utility=float(util),
        )
    return out


def mean_edge_weight(graph: nx.DiGraph, *, key: str = "weight") -> float:
    """Mean of *key* over edges (0 if no edges)."""
    edges = list(graph.edges(data=True))
    if not edges:
        return 0.0
    return sum(float(d.get(key, 0.0)) for _u, _v, d in edges) / len(edges)


def mean_removed_weight_plain(removed: list[tuple[str, str, float]]) -> float:
    """Average original confidence on removed edges if available on graph; else removed weight."""
    if not removed:
        return 0.0
    return sum(w for _, _, w in removed) / len(removed)
