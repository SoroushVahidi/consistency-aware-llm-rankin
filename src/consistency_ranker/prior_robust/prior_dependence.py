"""Separate prior, acquired, and inferred evidence.

Prior-only relations must never be counted as independently confirmed
judgment evidence. Every relation / ranking decision can report how much
support comes from each category.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

import networkx as nx

from consistency_ranker.reliability_repair.edge_reliability import estimate_reliability

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState

EvidenceCategory = Literal["prior", "acquired", "inferred"]


@dataclass
class RelationSupport:
    """How a pairwise relation is supported."""

    pair_id: str
    doc_i: str
    doc_j: str
    direction: int  # +1: i preferred, -1: j preferred, 0: unknown
    prior_agree: bool | None
    acquired: bool
    inferred: bool
    reliability: float
    n_judgments: int
    path_reliability: float
    categories: list[EvidenceCategory] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair_id": self.pair_id,
            "doc_i": self.doc_i,
            "doc_j": self.doc_j,
            "direction": self.direction,
            "prior_agree": self.prior_agree,
            "acquired": self.acquired,
            "inferred": self.inferred,
            "reliability": self.reliability,
            "n_judgments": self.n_judgments,
            "path_reliability": self.path_reliability,
            "categories": list(self.categories),
        }


def prior_preferred(state: "AcquisitionState", doc_a: str, doc_b: str) -> str | None:
    """Return the prior-preferred doc id, or None if scores equal."""
    sa = float(state.prior_scores.get(doc_a, 0.0))
    sb = float(state.prior_scores.get(doc_b, 0.0))
    if sa == sb:
        return None
    return doc_a if sa > sb else doc_b


def relation_support(
    state: "AcquisitionState",
    pair_id: str,
    *,
    min_path_reliability: float = 0.4,
) -> RelationSupport:
    """Classify support for one unordered pair."""
    doc_i, doc_j = state.pair_docs(pair_id)
    agg = state.aggregates.get(pair_id)
    acquired = agg is not None and agg.n_valid_directional > 0
    direction = int(agg.d) if agg is not None else 0
    reliability = float(estimate_reliability(agg)) if agg is not None else 0.0
    n_judgments = int(agg.n_valid_directional) if agg is not None else 0

    prior_pref = prior_preferred(state, doc_i, doc_j)
    prior_agree: bool | None = None
    if prior_pref is not None and direction != 0:
        pred = doc_i if direction == 1 else doc_j
        prior_agree = pred == prior_pref

    # Inferred via DAG reachability (not counted as acquired).
    view = state.view()
    dag = view.dag
    path_rel = 0.0
    inferred = False
    if doc_i in dag and doc_j in dag and nx.is_directed_acyclic_graph(dag):
        if nx.has_path(dag, doc_i, doc_j) or nx.has_path(dag, doc_j, doc_i):
            # Use min edge reliability on shortest path as path strength.
            src, dst = (doc_i, doc_j) if nx.has_path(dag, doc_i, doc_j) else (doc_j, doc_i)
            try:
                path = nx.shortest_path(dag, src, dst)
                if len(path) >= 2:
                    r = 1.0
                    for u, v in zip(path[:-1], path[1:]):
                        r *= float(dag[u][v].get("reliability", dag[u][v].get("weight", 1.0)))
                    path_rel = r
                    inferred = path_rel >= min_path_reliability and not acquired
                    if direction == 0 and path_rel >= min_path_reliability:
                        direction = 1 if src == doc_i else -1
            except nx.NetworkXNoPath:
                pass

    cats: list[EvidenceCategory] = []
    if acquired:
        cats.append("acquired")
    if inferred:
        cats.append("inferred")
    if prior_agree is True and not acquired:
        cats.append("prior")

    return RelationSupport(
        pair_id=pair_id,
        doc_i=doc_i,
        doc_j=doc_j,
        direction=direction,
        prior_agree=prior_agree,
        acquired=acquired,
        inferred=inferred,
        reliability=reliability,
        n_judgments=n_judgments,
        path_reliability=path_rel,
        categories=cats,
    )


def topk_evidence_coverage(
    state: "AcquisitionState",
    *,
    min_reliability: float = 0.25,
) -> dict[str, Any]:
    """Fraction of top-k-relevant pairs with acquired (not prior-only) support."""
    ranking = state.ranking
    k = state.top_k
    topk = ranking[:k]
    outsiders = ranking[k:]
    relevant_pairs: list[str] = []
    acquired_ok = 0
    # Internal top-k pairs + straddling pairs.
    for i, a in enumerate(topk):
        for b in topk[i + 1 :]:
            relevant_pairs.append(state.canonical_pair(a, b))
        for b in outsiders[: max(k, 3)]:
            relevant_pairs.append(state.canonical_pair(a, b))
    relevant_pairs = list(dict.fromkeys(relevant_pairs))
    for pid in relevant_pairs:
        supp = relation_support(state, pid)
        if supp.acquired and supp.reliability >= min_reliability:
            acquired_ok += 1
    n = max(len(relevant_pairs), 1)
    return {
        "n_relevant_pairs": len(relevant_pairs),
        "n_acquired_supported": acquired_ok,
        "fraction_acquired": acquired_ok / n,
        "topk": list(topk),
    }


def evidence_fraction_summary(state: "AcquisitionState") -> dict[str, Any]:
    """Query-level counts of prior / acquired / inferred relations."""
    n_prior_only = n_acquired = n_inferred = n_agree = n_contra = 0
    for pid in state.all_pair_ids():
        s = relation_support(state, pid)
        if s.acquired:
            n_acquired += 1
            if s.prior_agree is True:
                n_agree += 1
            elif s.prior_agree is False:
                n_contra += 1
        elif s.inferred:
            n_inferred += 1
        elif "prior" in s.categories:
            n_prior_only += 1
    return {
        "n_acquired": n_acquired,
        "n_inferred": n_inferred,
        "n_prior_only": n_prior_only,
        "n_prior_agree_among_acquired": n_agree,
        "n_prior_contradict_among_acquired": n_contra,
        "prior_agreement_rate": (
            n_agree / (n_agree + n_contra) if (n_agree + n_contra) else None
        ),
    }


__all__ = [
    "EvidenceCategory",
    "RelationSupport",
    "prior_preferred",
    "relation_support",
    "topk_evidence_coverage",
    "evidence_fraction_summary",
]
