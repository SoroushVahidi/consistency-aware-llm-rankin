"""
DAG ambiguity features for linear-extension sensitivity analysis.

Features characterize when a repaired (or originally acyclic) preference DAG
admits many valid total rankings.  They are judgment-free: no qrels are used.
"""

from __future__ import annotations

import math
from typing import Any

import networkx as nx

from consistency_ranker.dag_linear_extensions import (
    all_pairs_reachable_incomparable_fraction,
    count_linear_extensions,
    require_dag,
)


def _frontier_stats(dag: nx.DiGraph) -> dict[str, float | int]:
    """Simulate lexicographic Kahn and record zero-indegree frontier sizes."""
    require_dag(dag, "_frontier_stats")
    in_deg = {n: dag.in_degree(n) for n in dag.nodes()}
    available = sorted(n for n, d in in_deg.items() if d == 0)
    frontier_sizes: list[int] = []
    steps_gt1 = 0
    while available:
        frontier_sizes.append(len(available))
        if len(available) > 1:
            steps_gt1 += 1
        best = available.pop(0)
        for child in dag.successors(best):
            in_deg[child] -= 1
            if in_deg[child] == 0:
                inserted = False
                for i, node in enumerate(available):
                    if child < node:
                        available.insert(i, child)
                        inserted = True
                        break
                if not inserted:
                    available.append(child)
    if not frontier_sizes:
        return {
            "mean_frontier_size": 0.0,
            "max_frontier_size": 0,
            "n_steps_frontier_gt1": 0,
            "fraction_steps_frontier_gt1": 0.0,
        }
    mean_f = sum(frontier_sizes) / len(frontier_sizes)
    return {
        "mean_frontier_size": float(mean_f),
        "max_frontier_size": int(max(frontier_sizes)),
        "n_steps_frontier_gt1": int(steps_gt1),
        "fraction_steps_frontier_gt1": float(steps_gt1 / len(frontier_sizes)),
    }


def _width_proxy(dag: nx.DiGraph) -> int:
    """Efficient width proxy: size of the maximum antichain lower-bounded by
    the maximum number of mutual incomparables via Dilworth is expensive;
    we use max frontier size under Kahn as a cheap proxy, and also the size of
    the largest set of nodes with equal topological level.
    """
    levels: dict[str, int] = {}
    for node in nx.topological_sort(dag):
        preds = list(dag.predecessors(node))
        levels[node] = 0 if not preds else 1 + max(levels[p] for p in preds)
    if not levels:
        return 0
    by_level: dict[int, int] = {}
    for lvl in levels.values():
        by_level[lvl] = by_level.get(lvl, 0) + 1
    return int(max(by_level.values()))


def estimate_log_linear_extensions_mcmc(
    dag: nx.DiGraph,
    *,
    n_samples: int = 200,
    seed: int = 0,
) -> float | None:
    """Cheap proxy: mean log of frontier sizes along random topo walks.

    This is **not** an unbiased estimator of log(#extensions); it is a
    monotonic-ish ambiguity signal used when exact counting is intractable.
    """
    require_dag(dag, "estimate_log_linear_extensions_mcmc")
    n = dag.number_of_nodes()
    if n == 0:
        return 0.0
    import random

    rng = random.Random(seed)
    logs: list[float] = []
    for _ in range(n_samples):
        in_deg = {v: dag.in_degree(v) for v in dag.nodes()}
        available = [v for v, d in in_deg.items() if d == 0]
        log_count = 0.0
        placed = 0
        while available:
            log_count += math.log(len(available))
            choice = rng.choice(sorted(available))
            available = [x for x in available if x != choice]
            placed += 1
            for child in dag.successors(choice):
                in_deg[child] -= 1
                if in_deg[child] == 0:
                    available.append(child)
        if placed == n:
            logs.append(log_count)
    if not logs:
        return None
    return float(sum(logs) / len(logs))


def dag_ambiguity_features(
    dag: nx.DiGraph,
    *,
    exact_extension_limit: int = 50_000,
    exact_count_max_nodes: int = 12,
) -> dict[str, Any]:
    """Compute ambiguity features for a DAG.

    Returns a dict including:
    * ``n_nodes``, ``n_edges``
    * ``n_linear_extensions`` (exact or None if truncated/too large)
    * ``log_linear_extensions_proxy``
    * ``fraction_incomparable_pairs``
    * frontier statistics
    * ``width_proxy``
    * discrete buckets: ``unique`` / ``multiple`` / ``highly_ambiguous``
    """
    require_dag(dag, "dag_ambiguity_features")
    n = dag.number_of_nodes()
    m = dag.number_of_edges()
    frontier = _frontier_stats(dag)
    frac_inc = all_pairs_reachable_incomparable_fraction(dag)
    width = _width_proxy(dag)

    n_ext: int | None
    if n <= exact_count_max_nodes:
        n_ext = count_linear_extensions(dag, max_count=exact_extension_limit)
    else:
        n_ext = None

    log_proxy = estimate_log_linear_extensions_mcmc(dag, n_samples=min(100, max(10, 5 * n)))

    # Bucket assignment.
    if n_ext == 1 or (n_ext is None and frontier["max_frontier_size"] <= 1):
        bucket = "unique_topological_order"
    elif (
        (n_ext is not None and n_ext >= 100)
        or frac_inc >= 0.35
        or int(frontier["max_frontier_size"]) >= max(4, n // 3)
    ):
        bucket = "highly_ambiguous"
    else:
        bucket = "multiple_valid_orders"

    return {
        "n_nodes": n,
        "n_edges": m,
        "n_linear_extensions": n_ext,
        "linear_extensions_truncated": n_ext is None and n <= exact_count_max_nodes,
        "log_linear_extensions_proxy": log_proxy,
        "fraction_incomparable_pairs": float(frac_inc),
        "width_proxy": width,
        "ambiguity_bucket": bucket,
        **frontier,
    }
