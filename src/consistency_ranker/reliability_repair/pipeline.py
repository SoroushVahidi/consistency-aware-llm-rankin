"""End-to-end reliability-aware repair pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Sequence

import networkx as nx

from consistency_ranker.baseline_ranking import (
    priority_topological_ranking,
)
from consistency_ranker.reliability_repair.edge_importance import (
    ImportanceMethod,
    estimate_importance,
)
from consistency_ranker.reliability_repair.edge_reliability import (
    ReliabilityMethod,
    estimate_reliability,
)
from consistency_ranker.reliability_repair.evidence_aggregation import (
    DirectionEstimator,
    PairAggregate,
    aggregate_all,
)
from consistency_ranker.reliability_repair.local_contradiction import (
    LocalPolicy,
    resolve_local_contradiction,
)
from consistency_ranker.reliability_repair.pair_evidence import NormalizedEvidence
from consistency_ranker.reliability_repair.prior_regularized_repair import (
    exact_prior_regularized_ordering,
    heuristic_prior_regularized_ordering,
)
from consistency_ranker.reliability_repair.reliability_weighted_repair import (
    apply_cost_scheme,
    exact_fas_with_costs,
    greedy_fas_with_costs,
)
from consistency_ranker.reliability_repair.selective_graph import (
    AbstentionPolicy,
    build_selective_graph,
    decide_edge,
)
from consistency_ranker.reliability_repair.stability_diagnostics import ranking_stability

CostScheme = Literal[
    "weight",
    "reliability",
    "reliability_x_importance",
    "weight_x_reliability",
    "weight_x_reliability_x_importance",
]


@dataclass
class ReliabilityRepairConfig:
    direction_estimator: DirectionEstimator = "smoothed"
    alpha: float = 1.0
    reliability_method: ReliabilityMethod = "agreement_composite_arith"
    importance_method: ImportanceMethod = "prior_position"
    abstention_policy: AbstentionPolicy = "reliability_threshold"
    tau: float = 0.25
    margin_tau: float = 0.2
    min_support: int = 1
    local_policy: LocalPolicy = "signed_margin"
    cost_scheme: CostScheme = "reliability_x_importance"
    repair: Literal["greedy", "exact", "none"] = "greedy"
    prior_lambda: float = 0.0
    use_exact_prior_reg: bool = False
    top_k: int = 10
    n_stability_samples: int = 24
    seed: int = 0
    method_version: str = "reliability_repair_v1"
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reliability_pipeline(
    evidence: Sequence[NormalizedEvidence],
    *,
    prior_scores: dict[str, float] | None = None,
    prior_ranking: list[str] | None = None,
    config: ReliabilityRepairConfig | None = None,
) -> dict[str, Any]:
    """Run normalize→aggregate→reliability→abstain→repair→extract→stability."""
    cfg = config or ReliabilityRepairConfig()
    if not evidence:
        return {
            "config": cfg.to_dict(),
            "ranking": [],
            "graph_meta": {},
            "repair_meta": {},
            "stability": {},
            "aggregates": {},
        }

    aggregates = aggregate_all(
        list(evidence), estimator=cfg.direction_estimator, alpha=cfg.alpha
    )

    # Apply local contradiction resolutions (may zero direction)
    local_stats = {"both_directions": 0, "one_edge": 0, "incomparable": 0, "diagnostic": 0}
    for pid, agg in list(aggregates.items()):
        res = resolve_local_contradiction(
            agg, policy=cfg.local_policy, prior_scores=prior_scores
        )
        if res.had_both_directions:
            local_stats["both_directions"] += 1
        if res.resolution == "one_edge":
            local_stats["one_edge"] += 1
            aggregates[pid].d = res.direction
            # Keep m sign consistent when overridden
            if res.direction != 0 and aggregates[pid].m * res.direction < 0:
                aggregates[pid].m = abs(aggregates[pid].m) * res.direction
        elif res.resolution == "incomparable":
            local_stats["incomparable"] += 1
            aggregates[pid].d = 0
        else:
            local_stats["diagnostic"] += 1

    # Priors
    if prior_scores is None:
        # Fallback: from evidence prior fields if present
        prior_scores = {}
        for e in evidence:
            if e.prior_score_i is not None:
                prior_scores[e.doc_i] = float(e.prior_score_i)
            if e.prior_score_j is not None:
                prior_scores[e.doc_j] = float(e.prior_score_j)
    if prior_ranking is None:
        prior_ranking = sorted(
            prior_scores, key=lambda d: (-float(prior_scores.get(d, 0.0)), d)
        )

    prior_ranks = {d: i + 1 for i, d in enumerate(prior_ranking)}

    decisions = []
    for agg in aggregates.values():
        rel = estimate_reliability(agg, method=cfg.reliability_method)
        imp = estimate_importance(
            agg,
            method=cfg.importance_method,
            prior_ranks=prior_ranks,
            k=cfg.top_k,
        )
        decisions.append(
            decide_edge(
                agg,
                reliability=rel,
                importance=imp,
                policy=cfg.abstention_policy,
                tau=cfg.tau,
                margin_tau=cfg.margin_tau,
                min_support=cfg.min_support,
            )
        )

    graph, graph_meta = build_selective_graph(decisions)
    graph = apply_cost_scheme(graph, scheme=cfg.cost_scheme)

    repair_meta: dict[str, Any] = {"method": "none"}
    dag: nx.DiGraph
    if cfg.repair == "none" or nx.is_directed_acyclic_graph(graph):
        dag = graph.copy()
        repair_meta = {
            "method": "none" if cfg.repair == "none" else "already_dag",
            "n_removed": 0,
            "removed_cost": 0.0,
        }
    elif cfg.repair == "exact" and graph.number_of_nodes() <= 9:
        dag, _removed, repair_meta = exact_fas_with_costs(graph)
    else:
        dag, _removed, repair_meta = greedy_fas_with_costs(graph)

    # Optional prior-regularized ordering override
    if cfg.prior_lambda > 0 and dag.number_of_nodes() > 0:
        if cfg.use_exact_prior_reg and dag.number_of_nodes() <= 8:
            ranking, preg = exact_prior_regularized_ordering(
                graph,  # use pre-repair graph costs for objective
                prior_ranking,
                lam=cfg.prior_lambda,
            )
            # Build DAG consistent with ranking
            dag = _dag_from_ranking_constraints(graph, ranking)
            repair_meta["prior_regularized"] = preg
        else:
            ranking, preg = heuristic_prior_regularized_ordering(
                graph, prior_ranking, lam=cfg.prior_lambda
            )
            dag = _dag_from_ranking_constraints(graph, ranking)
            repair_meta["prior_regularized"] = preg
    else:
        ranking = (
            priority_topological_ranking(dag, prior_scores)
            if dag.number_of_nodes()
            else []
        )

    stability = ranking_stability(
        dag,
        prior_scores=prior_scores,
        k=cfg.top_k,
        n_samples=cfg.n_stability_samples,
        seed=cfg.seed,
    )
    # Prefer pipeline ranking if prior-reg produced one; else stability ranking
    if ranking:
        stability = {**stability, "ranking": ranking}

    return {
        "config": cfg.to_dict(),
        "aggregates": {k: v.to_dict() for k, v in aggregates.items()},
        "decisions": [d.__dict__ for d in decisions],
        "local_stats": local_stats,
        "graph_meta": graph_meta,
        "repair_meta": repair_meta,
        "n_edges_before_repair": graph.number_of_edges(),
        "n_edges_after_repair": dag.number_of_edges(),
        "is_dag": nx.is_directed_acyclic_graph(dag),
        "ranking": ranking,
        "stability": stability,
        "graph": graph,
        "dag": dag,
    }


def _dag_from_ranking_constraints(graph: nx.DiGraph, ranking: list[str]) -> nx.DiGraph:
    """Retain only forward edges under *ranking* (hard topo projection)."""
    pos = {n: i for i, n in enumerate(ranking)}
    dag = nx.DiGraph()
    dag.add_nodes_from(graph.nodes())
    for u, v, data in graph.edges(data=True):
        if u in pos and v in pos and pos[u] < pos[v]:
            dag.add_edge(u, v, **data)
    return dag


def raw_weight_baseline_from_aggregates(
    aggregates: dict[str, PairAggregate],
) -> nx.DiGraph:
    """No-abstention graph with weight=|m| (may contain no two-cycles by construction)."""
    decisions = []
    for agg in aggregates.values():
        decisions.append(
            decide_edge(
                agg,
                reliability=abs(agg.m),
                importance=1.0,
                policy="none",
                weight_mode="margin",
            )
        )
    g, _ = build_selective_graph(decisions)
    return apply_cost_scheme(g, scheme="weight")
