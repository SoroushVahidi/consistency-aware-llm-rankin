"""Shared dataclasses for the repair-frontier package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import networkx as nx

Disposition = Literal["preserved", "removed", "reversed", "unresolved"]
AcceptanceMode = Literal["objective_only", "conservative", "oracle_analysis_only"]


@dataclass(frozen=True)
class EdgeConfidence:
    """Multi-provider evidence for one directed edge (winner, loser)."""

    winner: str
    loser: str
    n_providers_total: int
    n_providers_agree: int
    unanimous: bool
    margin: float
    aggregate_weight: float

    @property
    def reliability(self) -> float:
        if self.n_providers_total <= 0:
            return 1.0
        return self.n_providers_agree / self.n_providers_total


@dataclass
class LocalCandidate:
    """One candidate local ordering for a single nontrivial SCC."""

    scc_key: frozenset[str]
    method: str
    local_order: list[str]
    local_dag: nx.DiGraph
    objective: float
    removed_edges: list[tuple[str, str, float]]
    solver_status: dict | None = None
    feasible: bool = True
    protected_edge_violations: int = 0


@dataclass
class FrontierCandidate:
    """One candidate global ranking in the repair frontier for one query."""

    candidate_id: str
    dataset: str
    query_id: str
    global_ranking: list[str]
    modified_sccs: list[frozenset[str]]
    fas_objective: float
    n_reversed_or_removed: int
    weight_reversed_or_removed: float
    protected_edge_violations: int
    topk_membership_changes: int
    graph_features: dict
    runtime_s: float
    identical_to_incumbent: bool
    acceptance_mode: str
    accepted: bool
    edge_dispositions: dict[tuple[str, str], str] = field(default_factory=dict)
    acceptance_by_mode: dict[str, bool] = field(default_factory=dict)
    """For protected SCC-local candidates only (empty for everything else):
    whether THIS candidate's ranking would be deployed (vs. abstaining to
    the incumbent) under each of the three Part-1 acceptance modes. Kept as
    a property of the one raw candidate rather than exploded into separate
    per-mode frontier rows, since a mode's deployed ranking is always
    either this candidate's own ranking or the incumbent's -- both already
    present in the frontier, so per-mode rows would always be dropped by
    ranking-based deduplication."""

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "dataset": self.dataset,
            "query_id": self.query_id,
            "global_ranking": self.global_ranking,
            "modified_sccs": [sorted(s) for s in self.modified_sccs],
            "fas_objective": self.fas_objective,
            "n_reversed_or_removed": self.n_reversed_or_removed,
            "weight_reversed_or_removed": self.weight_reversed_or_removed,
            "protected_edge_violations": self.protected_edge_violations,
            "topk_membership_changes": self.topk_membership_changes,
            "graph_features": self.graph_features,
            "runtime_s": self.runtime_s,
            "identical_to_incumbent": self.identical_to_incumbent,
            "acceptance_mode": self.acceptance_mode,
            "accepted": self.accepted,
            "edge_dispositions": {f"{u}->{v}": d for (u, v), d in self.edge_dispositions.items()},
            "acceptance_by_mode": dict(self.acceptance_by_mode),
        }


__all__ = ["Disposition", "AcceptanceMode", "EdgeConfidence", "LocalCandidate", "FrontierCandidate"]
