"""
Rank Centrality–style Markov ranking on a weighted preference graph.

An edge ``u → v`` with weight ``w`` means *u is preferred over v* with strength
``w``.  Following Negahban, Oh, and Shah (Operations Research, 2016), define a
Markov chain on nodes with transition matrix ``P``::

    P_ij = A_ji / d   for j ≠ i
    P_ii = 1 − Σ_{j≠i} P_ij

where ``A_ji`` is the weight of edge ``j → v`` with ``v`` omitted — here
``A_ji`` is the weight of ``j → i`` (how strongly *j* is preferred over *i*),
and *d* is a scaling factor satisfying ``d ≥ max_i Σ_{j≠i} A_ji`` so that
``P_ii ≥ 0``.  We set::

    d = max(1.0, max_i Σ_{j≠i} A_ji)

so rows are stochastic.  Intuitively, from item *i* the chain moves toward items
that beat *i* in the data; high–stationary–mass items are strong overall.

**Teleportation / damping:** On disconnected or weakly-connected graphs the
chain can have non-unique stationary distributions.  We use a PageRank-style
uniform restart (same *α* interpretation as common PageRank)::

    π ← (1 − α) π P + α (1/n) 1ᵀ

with default ``α = 0.15``.  This yields a **unique** limit and **deterministic**
power iteration from the uniform start.

This is distinct from :func:`baseline_ranking.pagerank_ranking`, which runs
NetworkX PageRank on the **reversed** graph (authority on the transpose).  It
does not use ``--score-prior-files``.

Tie-break (final sort): higher stationary mass, then **lower** weighted in-degree
(fewer / weaker incoming “losses”), then ``doc_id`` ascending.
"""

from __future__ import annotations

import networkx as nx
import numpy as np

DEFAULT_MARKOV_DAMPING = 0.15
DEFAULT_MARKOV_MAX_ITER = 10_000
DEFAULT_MARKOV_TOL = 1e-10


def _edge_weight(graph: nx.DiGraph, u: str, v: str) -> float:
    data = graph.get_edge_data(u, v)
    if data is None:
        return 0.0
    return float(data.get("weight", 1.0))


def _weighted_in_degree(graph: nx.DiGraph, node: str) -> float:
    return sum(_edge_weight(graph, pred, node) for pred in graph.predecessors(node))


def markov_graph_scores(
    graph: nx.DiGraph,
    *,
    damping: float = DEFAULT_MARKOV_DAMPING,
    max_iter: int = DEFAULT_MARKOV_MAX_ITER,
    tol: float = DEFAULT_MARKOV_TOL,
) -> dict[str, float]:
    """Stationary distribution (approximate) per node; keys match ``graph.nodes()``."""
    ranking = markov_graph_ranking(
        graph, damping=damping, max_iter=max_iter, tol=tol, return_scores=True
    )
    assert isinstance(ranking, dict)
    return ranking


def markov_graph_ranking(
    graph: nx.DiGraph,
    *,
    damping: float = DEFAULT_MARKOV_DAMPING,
    max_iter: int = DEFAULT_MARKOV_MAX_ITER,
    tol: float = DEFAULT_MARKOV_TOL,
    return_scores: bool = False,
) -> list[str] | dict[str, float]:
    """Rank nodes by Rank Centrality–style stationary mass (best first).

    Parameters
    ----------
    graph:
        Weighted directed preference graph.
    damping:
        Uniform restart mass ``α`` in ``(0, 1]``.  ``0`` is treated as ``1e-12``
        for numerical stability (almost no teleportation).
    max_iter, tol:
        Power-iteration limits.

    Returns
    -------
    list[str]
        Nodes sorted by descending score (unless ``return_scores=True``).
    """
    if damping < 0 or damping > 1:
        raise ValueError(f"damping (teleport mass α) must be in [0, 1], got {damping}")
    alpha = max(float(damping), 1e-12)
    if alpha > 1.0:
        alpha = 1.0

    nodes = sorted(graph.nodes())
    n = len(nodes)
    if n == 0:
        return {} if return_scores else []
    if n == 1:
        only = nodes[0]
        return {only: 1.0} if return_scores else [only]

    loss_in = np.zeros(n, dtype=np.float64)
    for i, v in enumerate(nodes):
        s = 0.0
        for u in graph.nodes():
            if u == v:
                continue
            s += _edge_weight(graph, u, v)
        loss_in[i] = s

    d_scale = max(1.0, float(np.max(loss_in)))
    P = np.zeros((n, n), dtype=np.float64)
    for i, vi in enumerate(nodes):
        row_off = 0.0
        for j, vj in enumerate(nodes):
            if i == j:
                continue
            pij = _edge_weight(graph, vj, vi) / d_scale
            P[i, j] = pij
            row_off += pij
        P[i, i] = 1.0 - row_off
        if P[i, i] < -1e-8:
            raise RuntimeError("invalid Rank Centrality row (negative diagonal)")
        P[i, i] = max(P[i, i], 0.0)
        rs = P[i].sum()
        if abs(rs - 1.0) > 1e-6:
            P[i] /= rs

    pi = np.full(n, 1.0 / n, dtype=np.float64)
    teleport = alpha / n
    mix = 1.0 - alpha

    for _ in range(max_iter):
        pi_new = mix * (pi @ P) + teleport
        if float(np.sum(np.abs(pi_new - pi))) < tol:
            pi = pi_new
            break
        pi = pi_new

    scores = {nodes[i]: float(pi[i]) for i in range(n)}
    if return_scores:
        return scores

    win = {v: _weighted_in_degree(graph, v) for v in nodes}
    return sorted(nodes, key=lambda v: (-scores[v], win[v], v))
