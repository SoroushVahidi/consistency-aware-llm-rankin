"""Ranking stability diagnostics via linear-extension sampling."""

from __future__ import annotations

from typing import Any

import networkx as nx

from consistency_ranker.baseline_ranking import priority_topological_ranking
from consistency_ranker.dag_ambiguity import dag_ambiguity_features
from consistency_ranker.dag_linear_extensions import (
    linear_extension_metric_dispersion,
    sample_linear_extensions,
)


def ranking_stability(
    dag: nx.DiGraph,
    *,
    prior_scores: dict[str, float],
    k: int = 10,
    n_samples: int = 32,
    seed: int = 0,
) -> dict[str, Any]:
    """Stability metadata for a repaired DAG under prior-priority extraction."""
    if dag.number_of_nodes() == 0:
        return {"ranking": [], "ambiguity": None, "doc_stats": {}, "topk_stable": True}
    ranking = priority_topological_ranking(dag, prior_scores)
    amb = dag_ambiguity_features(dag)
    samples = sample_linear_extensions(dag, n_samples=n_samples, seed=seed)
    disp = linear_extension_metric_dispersion(samples, ranking, metric="kendall_tau")

    # Per-doc sampled ranks
    doc_stats: dict[str, Any] = {}
    for doc in dag.nodes():
        ranks = []
        topk_hits = 0
        for s in samples:
            r = s.index(doc) + 1
            ranks.append(r)
            if r <= k:
                topk_hits += 1
        mean_r = sum(ranks) / len(ranks)
        var = sum((x - mean_r) ** 2 for x in ranks) / len(ranks)
        final_r = ranking.index(doc) + 1 if doc in ranking else None
        doc_stats[doc] = {
            "final_rank": final_r,
            "expected_sampled_rank": mean_r,
            "rank_std": var**0.5,
            "min_sampled_rank": min(ranks),
            "max_sampled_rank": max(ranks),
            "topk_membership_prob": topk_hits / len(ranks),
            "determined_by_edges_or_prior": (
                "edges" if amb.get("max_frontier_size", 1) <= 1 else "mixed_or_prior"
            ),
        }

    topk = set(ranking[:k])
    jaccards = []
    for s in samples:
        other = set(s[:k])
        inter = len(topk & other)
        union = len(topk | other) or 1
        jaccards.append(inter / union)
    return {
        "ranking": ranking,
        "ambiguity": amb,
        "extension_tau_dispersion": disp,
        "doc_stats": doc_stats,
        "topk_jaccard_mean": sum(jaccards) / len(jaccards) if jaccards else 1.0,
        "topk_jaccard_min": min(jaccards) if jaccards else 1.0,
        "topk_set_stable": (min(jaccards) if jaccards else 1.0) >= 0.999,
    }
