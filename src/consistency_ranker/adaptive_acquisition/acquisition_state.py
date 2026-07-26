"""Serializable, resumable per-query acquisition state.

The state stores only the *inputs* that were expensive to obtain (the accumulated
provenance-safe evidence, the prior, the action history and remaining budget).
All derived quantities — aggregates, selective graph, repaired DAG, ranking,
cycle/SCC diagnostics, ambiguity, sampled rank distributions and top-k
membership probabilities — are recomputed on demand from that evidence via the
existing reliability-repair pipeline. Restarting therefore never requires
re-issuing any LLM judgment: ``from_dict`` fully reconstructs the derived view.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any, Iterable

import networkx as nx

from consistency_ranker.baseline_ranking import priority_topological_ranking
from consistency_ranker.dag_linear_extensions import count_linear_extensions
from consistency_ranker.reliability_repair.evidence_aggregation import (
    PairAggregate,
    aggregate_all,
)
from consistency_ranker.reliability_repair.pair_evidence import (
    NormalizedEvidence,
    canonical_doc_order,
    canonical_pair_id,
)
from consistency_ranker.reliability_repair.pipeline import (
    ReliabilityRepairConfig,
    run_reliability_pipeline,
)


@dataclass
class StateView:
    """Derived, recomputable snapshot of the current knowledge for a query."""

    aggregates: dict[str, PairAggregate]
    graph: nx.DiGraph
    dag: nx.DiGraph
    ranking: list[str]
    stability: dict[str, Any]
    doc_stats: dict[str, Any]
    topk_membership_prob: dict[str, float]
    sccs: list[list[str]]
    n_nontrivial_sccs: int
    max_scc_size: int
    unresolved_pairs: list[str]
    contradictory_pairs: list[str]
    abstained_pairs: list[str]
    incomparable_pairs: list[tuple[str, str]]
    ambiguity: dict[str, Any]
    n_edges: int
    is_dag: bool

    def summary(self) -> dict[str, Any]:
        return {
            "n_edges": self.n_edges,
            "is_dag": self.is_dag,
            "n_nontrivial_sccs": self.n_nontrivial_sccs,
            "max_scc_size": self.max_scc_size,
            "n_unresolved_pairs": len(self.unresolved_pairs),
            "n_contradictory_pairs": len(self.contradictory_pairs),
            "n_abstained_pairs": len(self.abstained_pairs),
            "n_incomparable_pairs": len(self.incomparable_pairs),
            "ambiguity_bucket": self.ambiguity.get("ambiguity_bucket"),
            "fraction_incomparable_pairs": self.ambiguity.get(
                "fraction_incomparable_pairs"
            ),
            "topk_jaccard_min": self.stability.get("topk_jaccard_min"),
            "topk_set_stable": self.stability.get("topk_set_stable"),
        }


@dataclass
class AcquisitionState:
    query_id: str
    candidate_ids: list[str]
    prior_scores: dict[str, float]
    evidence: list[NormalizedEvidence] = field(default_factory=list)
    remaining_budget: int = 0
    top_k: int = 3
    history: list[dict[str, Any]] = field(default_factory=list)
    repair_config: ReliabilityRepairConfig = field(default_factory=ReliabilityRepairConfig)
    seed: int = 0
    ranking_override: list[str] | None = None
    _view: StateView | None = field(default=None, repr=False, compare=False)

    # ---- pair helpers -------------------------------------------------
    def prior_ranking(self) -> list[str]:
        return sorted(
            self.candidate_ids,
            key=lambda d: (-float(self.prior_scores.get(d, 0.0)), d),
        )

    def all_pair_ids(self) -> list[str]:
        ids = []
        for a, b in itertools.combinations(sorted(self.candidate_ids), 2):
            ids.append(canonical_pair_id(self.query_id, a, b))
        return ids

    def pair_docs(self, pair_id: str) -> tuple[str, str]:
        # canonical_pair_id == "{query}::{i}::{j}"
        parts = pair_id.split("::")
        return parts[-2], parts[-1]

    def canonical_pair(self, doc_x: str, doc_y: str) -> str:
        return canonical_pair_id(self.query_id, doc_x, doc_y)

    def evidence_signatures(self) -> set[tuple[str, str, str, str, str, int]]:
        """Signatures of already-collected judgments, to prevent duplicate billing.

        (pair_id, provider, model, prompt_version, orientation, repetition_index)
        """
        sigs = set()
        for e in self.evidence:
            sigs.add(
                (
                    e.canonical_pair_id,
                    str(e.provider),
                    str(e.model),
                    str(e.prompt_version),
                    str(e.displayed_orientation),
                    int(e.repetition_index),
                )
            )
        return sigs

    def evidence_for_pair(self, pair_id: str) -> list[NormalizedEvidence]:
        return [e for e in self.evidence if e.canonical_pair_id == pair_id]

    # ---- mutation -----------------------------------------------------
    def add_evidence(self, records: Iterable[NormalizedEvidence]) -> int:
        added = 0
        for r in records:
            self.evidence.append(r)
            added += 1
        if added:
            self._view = None  # invalidate derived cache
        return added

    def record_action(self, action_dict: dict[str, Any]) -> None:
        self.history.append(action_dict)

    def invalidate(self) -> None:
        self._view = None

    # ---- derived view -------------------------------------------------
    def view(self, *, recompute: bool = False) -> StateView:
        if self._view is not None and not recompute:
            return self._view
        self._view = self._compute_view()
        return self._view

    @property
    def aggregates(self) -> dict[str, PairAggregate]:
        return self.view().aggregates

    @property
    def ranking(self) -> list[str]:
        if self.ranking_override is not None:
            return list(self.ranking_override)
        return self.view().ranking

    def set_ranking_override(self, ranking: list[str] | None) -> None:
        self.ranking_override = list(ranking) if ranking is not None else None

    def _compute_view(self) -> StateView:
        prior_ranking = self.prior_ranking()
        if not self.evidence:
            g = nx.DiGraph()
            g.add_nodes_from(self.candidate_ids)
            incomparable = [
                (a, b) for a, b in itertools.combinations(sorted(self.candidate_ids), 2)
            ]
            return StateView(
                aggregates={},
                graph=g,
                dag=g.copy(),
                ranking=list(prior_ranking),
                stability={"topk_jaccard_min": 0.0, "topk_set_stable": False},
                doc_stats={},
                topk_membership_prob={},
                sccs=[[n] for n in self.candidate_ids],
                n_nontrivial_sccs=0,
                max_scc_size=1 if self.candidate_ids else 0,
                unresolved_pairs=self.all_pair_ids(),
                contradictory_pairs=[],
                abstained_pairs=[],
                incomparable_pairs=incomparable,
                ambiguity={
                    "ambiguity_bucket": "highly_ambiguous",
                    "fraction_incomparable_pairs": 1.0 if len(self.candidate_ids) > 1 else 0.0,
                },
                n_edges=0,
                is_dag=True,
            )

        cfg = ReliabilityRepairConfig(
            **{**self.repair_config.to_dict(), "top_k": self.top_k, "seed": self.seed}
        )
        out = run_reliability_pipeline(
            self.evidence,
            prior_scores=self.prior_scores,
            prior_ranking=prior_ranking,
            config=cfg,
        )
        graph: nx.DiGraph = out["graph"]
        dag: nx.DiGraph = out["dag"]
        # Ensure all candidates are present as nodes.
        for d in self.candidate_ids:
            if d not in graph:
                graph.add_node(d)
            if d not in dag:
                dag.add_node(d)

        aggregates = aggregate_all(
            self.evidence, estimator=self.repair_config.direction_estimator
        )

        # Recompute the ranking over the *full* candidate set (the pipeline's
        # ranking only covers docs appearing in a judged pair). Unjudged docs
        # become sources ordered by prior.
        if nx.is_directed_acyclic_graph(dag) and dag.number_of_nodes():
            ranking = priority_topological_ranking(dag, self.prior_scores)
        else:
            ranking = list(out.get("ranking") or prior_ranking)
        # Append any stragglers deterministically by prior.
        missing = [d for d in prior_ranking if d not in ranking]
        ranking = ranking + missing

        # Categorize pairs.
        unresolved, contradictory, abstained = [], [], []
        for pid in self.all_pair_ids():
            agg = aggregates.get(pid)
            if agg is None:
                unresolved.append(pid)
                continue
            if agg.n_plus > 0 and agg.n_minus > 0:
                contradictory.append(pid)
            if agg.d == 0:
                abstained.append(pid)
                if pid not in unresolved:
                    unresolved.append(pid)

        # Incomparable pairs in the repaired DAG (no directed path either way).
        incomparable = self._incomparable_pairs(dag)

        # SCCs on the pre-repair graph (cycle diagnostics).
        sccs = [list(c) for c in nx.strongly_connected_components(graph)]
        nontrivial = [c for c in sccs if len(c) > 1]
        max_scc = max((len(c) for c in sccs), default=0)

        stability = out.get("stability", {}) or {}
        doc_stats = stability.get("doc_stats", {}) or {}
        topk_prob = {
            d: float(s.get("topk_membership_prob", 0.0)) for d, s in doc_stats.items()
        }
        ambiguity = stability.get("ambiguity") or {}

        return StateView(
            aggregates=aggregates,
            graph=graph,
            dag=dag,
            stability=stability,
            doc_stats=doc_stats,
            topk_membership_prob=topk_prob,
            sccs=sccs,
            n_nontrivial_sccs=len(nontrivial),
            max_scc_size=int(max_scc),
            unresolved_pairs=unresolved,
            contradictory_pairs=contradictory,
            abstained_pairs=abstained,
            incomparable_pairs=incomparable,
            ambiguity=ambiguity,
            n_edges=graph.number_of_edges(),
            is_dag=bool(out.get("is_dag", True)),
            ranking=ranking,
        )

    def _incomparable_pairs(self, dag: nx.DiGraph) -> list[tuple[str, str]]:
        nodes = sorted(self.candidate_ids)
        if len(nodes) < 2 or not nx.is_directed_acyclic_graph(dag):
            # Fall back: treat all pairs with no edge as incomparable.
            reach = {n: set() for n in nodes}
        else:
            reach = {n: set(nx.descendants(dag, n)) for n in nodes if n in dag}
            for n in nodes:
                reach.setdefault(n, set())
        out = []
        for a, b in itertools.combinations(nodes, 2):
            if b not in reach.get(a, set()) and a not in reach.get(b, set()):
                out.append((a, b))
        return out

    def n_linear_extensions(self, *, max_count: int = 20000) -> int | None:
        dag = self.view().dag
        if not nx.is_directed_acyclic_graph(dag):
            return None
        return count_linear_extensions(dag, max_count=max_count)

    # ---- serialization ------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "candidate_ids": list(self.candidate_ids),
            "prior_scores": dict(self.prior_scores),
            "evidence": [e.to_dict() for e in self.evidence],
            "remaining_budget": self.remaining_budget,
            "top_k": self.top_k,
            "history": list(self.history),
            "repair_config": self.repair_config.to_dict(),
            "seed": self.seed,
            "ranking_override": list(self.ranking_override) if self.ranking_override else None,
            "format_version": "adaptive_acquisition_state_v1",
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AcquisitionState:
        ev = [NormalizedEvidence(**_clean_evidence(d)) for d in data.get("evidence", [])]
        cfg_data = data.get("repair_config") or {}
        cfg = ReliabilityRepairConfig(**{k: v for k, v in cfg_data.items()})
        return cls(
            query_id=str(data["query_id"]),
            candidate_ids=list(data["candidate_ids"]),
            prior_scores={k: float(v) for k, v in dict(data.get("prior_scores", {})).items()},
            evidence=ev,
            remaining_budget=int(data.get("remaining_budget", 0)),
            top_k=int(data.get("top_k", 3)),
            history=list(data.get("history", [])),
            repair_config=cfg,
            seed=int(data.get("seed", 0)),
            ranking_override=(
                list(data["ranking_override"]) if data.get("ranking_override") else None
            ),
        )


def _clean_evidence(d: dict[str, Any]) -> dict[str, Any]:
    """Keep only NormalizedEvidence fields (drops any extra serialized keys)."""
    allowed = set(NormalizedEvidence.__dataclass_fields__.keys())
    return {k: v for k, v in d.items() if k in allowed}


def initial_state(
    *,
    query_id: str,
    candidate_ids: list[str],
    prior_scores: dict[str, float],
    budget: int,
    top_k: int = 3,
    repair_config: ReliabilityRepairConfig | None = None,
    seed: int = 0,
) -> AcquisitionState:
    """Convenience constructor for a fresh (no-evidence) acquisition state."""
    return AcquisitionState(
        query_id=query_id,
        candidate_ids=list(candidate_ids),
        prior_scores=dict(prior_scores),
        evidence=[],
        remaining_budget=int(budget),
        top_k=int(top_k),
        history=[],
        repair_config=repair_config or ReliabilityRepairConfig(),
        seed=seed,
    )


__all__ = [
    "AcquisitionState",
    "StateView",
    "initial_state",
    "canonical_doc_order",
]
