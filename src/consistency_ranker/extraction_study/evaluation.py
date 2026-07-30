"""Per-query-graph extraction evaluation: nDCG per extractor, delta vs
incumbent, bootstrap CI, win/tie/loss counts, downside risk, and breakdowns
by dataset/provider/pool_size/cyclicity.

Reuses :func:`consistency_ranker.evaluation.ndcg_at_k`,
:func:`consistency_ranker.statistical_inference.bootstrap_mean_interval`/
`delta_summary`, and :func:`consistency_ranker.graph_construction.graph_summary`
rather than reimplementing any of them.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import networkx as nx
import numpy as np

from consistency_ranker.evaluation import ndcg_at_k
from consistency_ranker.graph_construction import graph_summary
from consistency_ranker.statistical_inference import (
    BootstrapIntervalResult,
    bootstrap_mean_interval,
    delta_summary,
)

from .extractors import INCUMBENT_NAME, extract_all


@dataclass(frozen=True)
class QueryGraphResult:
    """One (dataset, query_id, source, variant, graph_id) unit's outcome."""

    key: tuple
    dataset: str
    query_id: str
    provider: str
    pool_size: int
    is_cyclic: bool
    n_nodes: int
    n_edges: int
    graph_density: float
    ndcg_by_extractor: dict[str, float]
    incumbent_ndcg: float


def evaluate_unit_graph(
    graph: nx.DiGraph,
    relevance_map: dict[str, int],
    *,
    key: tuple,
    dataset: str,
    query_id: str,
    provider: str,
    pool_size: int,
    ndcg_k: int = 10,
) -> QueryGraphResult | None:
    """Returns None if the incumbent extractor itself fails (should not
    happen for a well-formed graph) -- callers should not silently drop
    this, see orchestration script's failures.jsonl."""
    rankings = extract_all(graph)
    if INCUMBENT_NAME not in rankings:
        return None
    ndcg_by_extractor = {
        name: ndcg_at_k(ranking, relevance_map, k=ndcg_k) for name, ranking in rankings.items()
    }
    summ = graph_summary(graph)
    return QueryGraphResult(
        key=key,
        dataset=dataset,
        query_id=query_id,
        provider=provider,
        pool_size=pool_size,
        is_cyclic=(not summ["is_dag"]),
        n_nodes=summ["n_nodes"],
        n_edges=summ["n_edges"],
        graph_density=(nx.density(graph) if graph.number_of_nodes() > 1 else 0.0),
        ndcg_by_extractor=ndcg_by_extractor,
        incumbent_ndcg=ndcg_by_extractor[INCUMBENT_NAME],
    )


def deltas_for(results: list[QueryGraphResult], extractor_name: str) -> list[float]:
    return [
        r.ndcg_by_extractor[extractor_name] - r.incumbent_ndcg
        for r in results
        if extractor_name in r.ndcg_by_extractor
    ]


@dataclass(frozen=True)
class ExtractorStats:
    name: str
    n: int
    mean_delta: float
    headroom_ci: BootstrapIntervalResult
    n_win: int
    n_tie: int
    n_loss: int
    downside_q05: float
    delta_summary: dict

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "n": self.n,
            "mean_delta": self.mean_delta,
            "headroom_ci": {
                "method": self.headroom_ci.method,
                "lower": self.headroom_ci.lower,
                "upper": self.headroom_ci.upper,
                "reps": self.headroom_ci.reps,
                "seed": self.headroom_ci.seed,
            },
            "n_win": self.n_win,
            "n_tie": self.n_tie,
            "n_loss": self.n_loss,
            "downside_q05": self.downside_q05,
            "delta_summary": self.delta_summary,
        }


_TIE_TOL = 1e-12


def compute_extractor_stats(results: list[QueryGraphResult], extractor_name: str) -> ExtractorStats:
    deltas = deltas_for(results, extractor_name)
    n_win = sum(1 for d in deltas if d > _TIE_TOL)
    n_loss = sum(1 for d in deltas if d < -_TIE_TOL)
    n_tie = len(deltas) - n_win - n_loss
    ci = bootstrap_mean_interval(deltas) if deltas else bootstrap_mean_interval([])
    ds = delta_summary(deltas)
    return ExtractorStats(
        name=extractor_name,
        n=len(deltas),
        mean_delta=float(np.mean(deltas)) if deltas else 0.0,
        headroom_ci=ci,
        n_win=n_win,
        n_tie=n_tie,
        n_loss=n_loss,
        downside_q05=float(ds.get("q05") or 0.0),
        delta_summary=ds,
    )


def breakdown_by(results: list[QueryGraphResult], extractor_name: str, key_fn) -> dict:
    groups: dict = defaultdict(list)
    for r in results:
        groups[key_fn(r)].append(r)
    return {str(k): compute_extractor_stats(v, extractor_name).to_dict() for k, v in groups.items()}


def full_breakdowns(results: list[QueryGraphResult], extractor_name: str) -> dict:
    """Requirement 3: results by dataset, provider, pool size, and cyclicity."""
    return {
        "by_dataset": breakdown_by(results, extractor_name, lambda r: r.dataset),
        "by_provider": breakdown_by(results, extractor_name, lambda r: r.provider),
        "by_pool_size": breakdown_by(results, extractor_name, lambda r: r.pool_size),
        "by_cyclicity": breakdown_by(
            results, extractor_name, lambda r: "cyclic" if r.is_cyclic else "acyclic"
        ),
    }


def outlier_sensitivity(
    results: list[QueryGraphResult], extractor_name: str, *, drop_top_n: int = 1
) -> dict:
    """Requirement 4: whether gains are driven by isolated outlier queries --
    recompute the mean delta after dropping the `drop_top_n` largest positive
    deltas and compare."""
    deltas = sorted(deltas_for(results, extractor_name), reverse=True)
    if not deltas:
        return {
            "mean_delta_full": 0.0,
            "mean_delta_excluding_top_n": None,
            "drop_top_n": drop_top_n,
        }
    full_mean = float(np.mean(deltas))
    if len(deltas) <= drop_top_n:
        return {
            "mean_delta_full": full_mean,
            "mean_delta_excluding_top_n": None,
            "drop_top_n": drop_top_n,
        }
    excl_mean = float(np.mean(deltas[drop_top_n:]))
    frac_from_top = ((full_mean - excl_mean) / full_mean) if abs(full_mean) > _TIE_TOL else None
    return {
        "mean_delta_full": full_mean,
        "mean_delta_excluding_top_n": excl_mean,
        "drop_top_n": drop_top_n,
        "fraction_of_mean_from_top_n": frac_from_top,
    }


__all__ = [
    "QueryGraphResult",
    "evaluate_unit_graph",
    "deltas_for",
    "ExtractorStats",
    "compute_extractor_stats",
    "breakdown_by",
    "full_breakdowns",
    "outlier_sensitivity",
]
