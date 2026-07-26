"""Prior-regularized linear ordering (exact on tiny graphs)."""

from __future__ import annotations

import itertools
import math
from typing import Literal

import networkx as nx

DistanceKind = Literal[
    "kendall",
    "weighted_kendall",
    "displacement",
    "topk_displacement",
]


def prior_distance(
    ranking: list[str],
    prior_ranking: list[str],
    *,
    kind: DistanceKind = "kendall",
    k: int = 10,
) -> float:
    nodes = set(ranking)
    prior = [x for x in prior_ranking if x in nodes]
    for n in ranking:
        if n not in prior:
            prior.append(n)
    pos = {n: i for i, n in enumerate(ranking)}
    ppos = {n: i for i, n in enumerate(prior)}
    if kind == "kendall":
        inv = 0
        for i, a in enumerate(prior):
            for b in prior[i + 1 :]:
                if pos[a] > pos[b]:
                    inv += 1
        return float(inv)
    if kind == "displacement":
        return float(sum(abs(pos[n] - ppos[n]) for n in ranking))
    if kind == "weighted_kendall":
        # Position-weighted: discordant pairs involving top prior ranks cost more.
        inv = 0.0
        for i, a in enumerate(prior):
            wa = 1.0 / math.log2(2 + i)
            for j, b in enumerate(prior):
                if j <= i:
                    continue
                wb = 1.0 / math.log2(2 + j)
                if pos[a] > pos[b]:
                    inv += 0.5 * (wa + wb)
        return float(inv)
    if kind == "topk_displacement":
        top = set(prior[:k])
        return float(sum(abs(pos[n] - ppos[n]) for n in ranking if n in top))
    raise ValueError(kind)


def exact_prior_regularized_ordering(
    graph: nx.DiGraph,
    prior_ranking: list[str],
    *,
    lam: float = 0.0,
    cost_attr: str = "removal_cost",
    distance: DistanceKind = "kendall",
    max_n: int = 8,
    k: int = 10,
) -> tuple[list[str], dict[str, float]]:
    """Minimize sum C_ij 1[π(j)<π(i)] + λ D(π, π0) by enumeration."""
    nodes = list(graph.nodes())
    n = len(nodes)
    if n > max_n:
        raise ValueError(f"exact_prior_regularized_ordering n<={max_n}; got {n}")
    if n == 0:
        return [], {"objective": 0.0, "fas_cost": 0.0, "prior_term": 0.0}
    edges = [
        (u, v, float(graph[u][v].get(cost_attr, graph[u][v].get("weight", 1.0))))
        for u, v in graph.edges()
    ]
    best = None
    best_obj = float("inf")
    best_parts = (0.0, 0.0)
    for perm in itertools.permutations(nodes):
        ranking = list(perm)
        pos = {node: i for i, node in enumerate(ranking)}
        fas = sum(c for u, v, c in edges if pos[v] < pos[u])
        dist = prior_distance(ranking, prior_ranking, kind=distance, k=k)
        obj = fas + float(lam) * dist
        if obj < best_obj:
            best_obj = obj
            best = ranking
            best_parts = (fas, dist)
    assert best is not None
    return best, {
        "objective": float(best_obj),
        "fas_cost": float(best_parts[0]),
        "prior_term": float(best_parts[1]),
        "lambda": float(lam),
        "distance": distance,
    }


def heuristic_prior_regularized_ordering(
    graph: nx.DiGraph,
    prior_ranking: list[str],
    *,
    lam: float = 0.0,
    cost_attr: str = "removal_cost",
) -> tuple[list[str], dict[str, float]]:
    """Heuristic: FAS with costs, then prior-priority topo on residual DAG.

    For λ→∞ effectively prefers prior among available sources after repair.
    For λ=0 ignores prior during repair (prior used only in extraction).
    """
    from consistency_ranker.baseline_ranking import priority_topological_ranking
    from consistency_ranker.reliability_repair.reliability_weighted_repair import (
        greedy_fas_with_costs,
    )

    dag, removed, meta = greedy_fas_with_costs(graph, cost_attr=cost_attr)
    # Blend prior scores with optional λ-scaled boost
    n = len(prior_ranking)
    prior_scores = {d: float(n - i) for i, d in enumerate(prior_ranking)}
    if lam > 0:
        # Inflate prior influence for extraction only (documented heuristic).
        scale = 1.0 + float(lam)
        prior_scores = {d: s * scale for d, s in prior_scores.items()}
    ranking = priority_topological_ranking(dag, prior_scores)
    return ranking, {
        "method": "heuristic_prior_regularized",
        "lambda": float(lam),
        "n_removed": meta["n_removed"],
        "removed_cost": meta["removed_cost"],
        "fas_cost": meta["removed_cost"],
        "prior_term": prior_distance(ranking, prior_ranking, kind="kendall"),
    }
