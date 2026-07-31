"""Pre-repair vs. post-repair feature extraction for the repair-regime
diagnostic study.

Pre-repair features are observable BEFORE any repair is applied and are
the ONLY features allowed to feed the deployable predictor (see
`prediction.py`). Post-repair features (repair objective, reversed-edge
count/weight) require having already run repair and are kept in a
SEPARATE dataclass, for descriptive/association analysis only -- never
passed to the classifier.

``dataset``/``provider`` are tracked at the diagnostic-record level (see
`outcomes.py`), not inside :class:`PreRepairFeatures` itself: with only 6
underlying queries, one-hot encoding them as classifier inputs would let a
shallow model memorize per-dataset/provider intercepts rather than learn a
genuine graph-structural regime, so they are used for subgroup
stability/breakdown checks only.

Reuses :func:`consistency_ranker.baseline_ranking.copeland_ranking` and
:func:`consistency_ranker.repair_frontier.edge_confidence.compute_edge_confidence`
rather than reimplementing either.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np

from consistency_ranker.baseline_ranking import copeland_ranking
from consistency_ranker.pairwise_prefs import Preference
from consistency_ranker.repair_frontier.edge_confidence import compute_edge_confidence

PRE_REPAIR_FEATURE_NAMES = [
    "n_nodes",
    "n_edges",
    "graph_density",
    "pool_size",
    "n_sccs",
    "n_nontrivial_sccs",
    "largest_scc_size",
    "largest_scc_frac",
    "is_cyclic",
    "scc_cycle_weight",
    "scc_cycle_weight_frac",
    "edge_weight_mean",
    "edge_weight_std",
    "edge_weight_max",
    "mean_edge_reliability",
    "frac_edges_unanimous",
    "provider_disagreement",
    "topk_involvement",
    "incumbent_topk_margin",
]

POST_REPAIR_FEATURE_NAMES = [
    "repair_objective",
    "n_reversed_edges",
    "weight_reversed_edges",
    "repair_objective_frac",
]


@dataclass(frozen=True)
class PreRepairFeatures:
    n_nodes: int
    n_edges: int
    graph_density: float
    pool_size: int
    n_sccs: int
    n_nontrivial_sccs: int
    largest_scc_size: int
    largest_scc_frac: float
    is_cyclic: bool
    scc_cycle_weight: float
    scc_cycle_weight_frac: float
    edge_weight_mean: float
    edge_weight_std: float
    edge_weight_max: float
    mean_edge_reliability: float
    frac_edges_unanimous: float
    provider_disagreement: float
    topk_involvement: bool
    incumbent_topk_margin: float

    def to_dict(self) -> dict:
        return {name: getattr(self, name) for name in PRE_REPAIR_FEATURE_NAMES}

    def as_numeric_row(self) -> dict[str, float]:
        """Numeric-only encoding (booleans -> 0.0/1.0) for the classifier."""
        row = {}
        for k, v in self.to_dict().items():
            row[k] = (1.0 if v else 0.0) if isinstance(v, bool) else float(v)
        return row


@dataclass(frozen=True)
class PostRepairFeatures:
    repair_objective: float
    n_reversed_edges: int
    weight_reversed_edges: float
    repair_objective_frac: float

    def to_dict(self) -> dict:
        return {name: getattr(self, name) for name in POST_REPAIR_FEATURE_NAMES}


def _scc_cycle_weight(graph: nx.DiGraph, nontrivial_sccs: list[frozenset]) -> float:
    weight = 0.0
    for u, v, data in graph.edges(data=True):
        for scc in nontrivial_sccs:
            if u in scc and v in scc:
                weight += float(data.get("weight", 1.0))
                break
    return weight


def compute_pre_repair_features(
    graph: nx.DiGraph,
    *,
    pool_size: int,
    provider_prefs: dict[str, list[Preference]] | None = None,
    topk: int = 10,
) -> PreRepairFeatures:
    n_nodes = graph.number_of_nodes()
    n_edges = graph.number_of_edges()
    density = nx.density(graph) if n_nodes > 1 else 0.0

    sccs_all = list(nx.strongly_connected_components(graph))
    n_sccs = len(sccs_all)
    nontrivial = [frozenset(s) for s in sccs_all if len(s) > 1]
    n_nontrivial = len(nontrivial)
    largest_scc = max((len(s) for s in sccs_all), default=0)
    largest_scc_frac = (largest_scc / n_nodes) if n_nodes else 0.0
    is_cyclic = n_nontrivial > 0

    weights = [float(d.get("weight", 1.0)) for _, _, d in graph.edges(data=True)]
    total_weight = sum(weights)
    scc_weight = _scc_cycle_weight(graph, nontrivial)
    scc_weight_frac = (scc_weight / total_weight) if total_weight > 0 else 0.0
    weight_mean = float(np.mean(weights)) if weights else 0.0
    weight_std = float(np.std(weights)) if weights else 0.0
    weight_max = float(max(weights)) if weights else 0.0

    mean_reliability = 1.0
    frac_unanimous = 1.0
    provider_disagreement = 0.0
    if provider_prefs:
        confidences = compute_edge_confidence(provider_prefs)
        relevant = [confidences[(u, v)] for u, v in graph.edges() if (u, v) in confidences]
        if relevant:
            mean_reliability = float(np.mean([c.reliability for c in relevant]))
            frac_unanimous = float(np.mean([1.0 if c.unanimous else 0.0 for c in relevant]))
            multi_provider = [c for c in relevant if c.n_providers_total > 1]
            if multi_provider:
                disagreements = [1.0 - c.reliability for c in multi_provider]
                provider_disagreement = float(np.mean(disagreements))

    incumbent_ranking = copeland_ranking(graph)
    topk_nodes = set(incumbent_ranking[:topk])
    topk_involvement = any(any(n in topk_nodes for n in scc) for scc in nontrivial)

    scores = {n: graph.out_degree(n) - graph.in_degree(n) for n in graph.nodes()}
    if len(incumbent_ranking) > topk:
        boundary_margin = float(
            scores[incumbent_ranking[topk - 1]] - scores[incumbent_ranking[topk]]
        )
    else:
        boundary_margin = 0.0

    return PreRepairFeatures(
        n_nodes=n_nodes,
        n_edges=n_edges,
        graph_density=density,
        pool_size=pool_size,
        n_sccs=n_sccs,
        n_nontrivial_sccs=n_nontrivial,
        largest_scc_size=largest_scc,
        largest_scc_frac=largest_scc_frac,
        is_cyclic=is_cyclic,
        scc_cycle_weight=scc_weight,
        scc_cycle_weight_frac=scc_weight_frac,
        edge_weight_mean=weight_mean,
        edge_weight_std=weight_std,
        edge_weight_max=weight_max,
        mean_edge_reliability=mean_reliability,
        frac_edges_unanimous=frac_unanimous,
        provider_disagreement=provider_disagreement,
        topk_involvement=topk_involvement,
        incumbent_topk_margin=boundary_margin,
    )


def compute_post_repair_features(
    total_graph_weight: float, removed_edges: list[tuple[str, str, float]]
) -> PostRepairFeatures:
    objective = sum(w for _, _, w in removed_edges)
    return PostRepairFeatures(
        repair_objective=objective,
        n_reversed_edges=len(removed_edges),
        weight_reversed_edges=objective,
        repair_objective_frac=(objective / total_graph_weight) if total_graph_weight > 0 else 0.0,
    )


__all__ = [
    "PRE_REPAIR_FEATURE_NAMES",
    "POST_REPAIR_FEATURE_NAMES",
    "PreRepairFeatures",
    "PostRepairFeatures",
    "compute_pre_repair_features",
    "compute_post_repair_features",
]
