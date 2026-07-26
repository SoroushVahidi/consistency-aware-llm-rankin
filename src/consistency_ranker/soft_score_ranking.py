"""
Soft score-based graph ranking methods.

These methods treat pairwise relations as **soft evidence**.  Returned rankings
are total orders but are **not** guaranteed to respect every DAG edge.  Keep
them separate from :mod:`consistency_ranker.dag_linear_extensions`.

Includes
--------
* ``normalized_weighted_balance_ranking`` — soft analogue of the older MWFAS
  normalized degree heuristic.
* ``springrank_ranking`` — SpringRank (De Bacco et al.), dense/scipy sparse.
* ``serialrank_ranking`` — SerialRank (Fogel et al.), scipy eigensolve.
"""

from __future__ import annotations

import warnings

import networkx as nx
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from consistency_ranker.dag_linear_extensions import (
    DEFAULT_EPS,
    normalized_balance_priority_scores,
)

SOFT_SCORE_METHODS: tuple[str, ...] = (
    "normalized_weighted_balance",
    "springrank",
    "serialrank",
    "weighted_out_minus_in",  # already in baseline_ranking; catalogued here
    "score_sum",
    "borda",
    "copeland",
    "pagerank",
    "rank_centrality",
    "markov_graph",
)


def normalized_weighted_balance_scores(
    graph: nx.DiGraph,
    *,
    eps: float = DEFAULT_EPS,
) -> dict[str, float]:
    """Soft scores ``(W_out - W_in) / (W_out + W_in + eps)``."""
    return normalized_balance_priority_scores(graph, eps=eps)


def normalized_weighted_balance_ranking(
    graph: nx.DiGraph,
    *,
    eps: float = DEFAULT_EPS,
) -> list[str]:
    """Soft ranking by normalized weighted balance (may violate DAG edges)."""
    scores = normalized_weighted_balance_scores(graph, eps=eps)
    return sorted(scores, key=lambda n: (-scores[n], n))


def _adjacency_matrix(graph: nx.DiGraph) -> tuple[list[str], np.ndarray]:
    nodes = sorted(graph.nodes())
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    A = np.zeros((n, n), dtype=float)
    for u, v, data in graph.edges(data=True):
        A[idx[u], idx[v]] += float(data.get("weight", 1.0))
    return nodes, A


def springrank_scores(
    graph: nx.DiGraph,
    *,
    alpha: float = 0.0,
    l0: float = 1.0,
    l1: float = 1.0,
) -> dict[str, float]:
    """SpringRank scores (higher = better / higher rank).

    Adapted from De Bacco, Larremore & Moore (Science Advances, 2018) /
    cdebacco/SpringRank, using only numpy/scipy (no ``sparse`` package).
    """
    nodes, A = _adjacency_matrix(graph)
    n = len(nodes)
    if n == 0:
        return {}
    if n == 1:
        return {nodes[0]: 0.0}

    k_in = A.sum(axis=0)
    k_out = A.sum(axis=1)
    d1 = k_in + k_out
    d2 = l1 * (k_out - k_in)

    if alpha != 0.0:
        B = np.ones(n) * (alpha * l0) + d2
        M = -(A + A.T)
        np.fill_diagonal(M, alpha + d1 + np.diagonal(M))
    else:
        last = A[n - 1, :] + A[:, n - 1]
        M = A + A.T
        M = M + last.reshape(1, n)
        M = -M
        np.fill_diagonal(M, np.diagonal(M) + d1)
        d3 = np.ones(n) * (l1 * (k_out[n - 1] - k_in[n - 1]))
        B = d2 + d3

    M_sp = sp.csr_matrix(M)
    try:
        sol = spla.spsolve(M_sp, B)
    except Exception:
        sol, info = spla.bicgstab(M_sp, B, atol=1.0e-10)
        if info != 0:
            warnings.warn(
                f"SpringRank bicgstab did not fully converge (info={info}); "
                "using best iterate.",
                RuntimeWarning,
                stacklevel=2,
            )
    sol = np.asarray(sol, dtype=float).reshape(-1)
    return {nodes[i]: float(sol[i]) for i in range(n)}


def springrank_ranking(
    graph: nx.DiGraph,
    *,
    alpha: float = 0.0,
    l0: float = 1.0,
    l1: float = 1.0,
) -> list[str]:
    """Soft SpringRank total order (may violate DAG edges)."""
    scores = springrank_scores(graph, alpha=alpha, l0=l0, l1=l1)
    return sorted(scores, key=lambda n: (-scores[n], n))


def serialrank_scores(graph: nx.DiGraph) -> dict[str, float]:
    """SerialRank scores from the Fiedler vector of the SerialRank Laplacian.

    Adapted from Fogel, Jenatton, Bach & d'Aspremont (ICML 2014) as used in
    GNNRank ``serialRank``.  Higher score = better.
    """
    nodes, A = _adjacency_matrix(graph)
    n = len(nodes)
    if n == 0:
        return {}
    if n == 1:
        return {nodes[0]: 0.0}

    # GNNRank convention: transpose so A[i,j] means j beats i before forming C.
    At = A.T
    C = np.sign(At - At.T)
    S = C @ C.T / 2.0
    S = S + (n / 2.0) * np.eye(n)
    # Zero diagonal of similarity contribution already handled; Laplacian:
    L = np.diag(S.sum(axis=1)) - S
    # Smallest nontrivial eigenvector.
    try:
        # eigh is stable for symmetric L
        vals, vecs = np.linalg.eigh(0.5 * (L + L.T))
        # eigenvector for second-smallest eigenvalue
        order = np.argsort(vals)
        fiedler = np.real(vecs[:, order[1]])
    except Exception:
        L_sp = sp.csr_matrix(0.5 * (L + L.T))
        vals, vecs = spla.eigs(L_sp.asfptype(), k=2, which="SM")
        fiedler = np.real(vecs[:, 1])

    # Orient so that the majority of edges go from higher to lower score
    # consistently with "winner has higher score".
    scores = {nodes[i]: float(fiedler[i]) for i in range(n)}
    # Flip if needed so mean out-neighbor score is lower than mean in-neighbor.
    forward_agree = 0
    for u, v in graph.edges():
        if scores[u] > scores[v]:
            forward_agree += 1
        elif scores[u] < scores[v]:
            forward_agree -= 1
    if forward_agree < 0:
        scores = {n: -s for n, s in scores.items()}
    return scores


def serialrank_ranking(graph: nx.DiGraph) -> list[str]:
    """Soft SerialRank total order (may violate DAG edges)."""
    scores = serialrank_scores(graph)
    return sorted(scores, key=lambda n: (-scores[n], n))


def soft_method_metadata() -> list[dict[str, object]]:
    """Catalog soft methods with explicit no-topo-guarantee flag."""
    return [
        {
            "method": "normalized_weighted_balance",
            "family": "soft_score",
            "guarantees_topo": False,
            "uses_qrels": False,
            "deterministic": True,
            "notes": "Soft ranking by (W_out-W_in)/(W_out+W_in+eps).",
        },
        {
            "method": "springrank",
            "family": "soft_score",
            "guarantees_topo": False,
            "uses_qrels": False,
            "deterministic": True,
            "notes": "SpringRank linear system; may violate repaired edges.",
        },
        {
            "method": "serialrank",
            "family": "soft_score",
            "guarantees_topo": False,
            "uses_qrels": False,
            "deterministic": True,
            "notes": "SerialRank Fiedler ranking; may violate repaired edges.",
        },
    ]
