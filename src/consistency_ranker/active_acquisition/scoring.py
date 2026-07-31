"""Ranking extraction and acquisition-scoring signals for the pilot.

Everything here reuses the repository's existing primitives instead of
duplicating them:

* graph construction — :func:`consistency_ranker.graph_construction.build_graph`
* Kendall tau — :func:`consistency_ranker.evaluation.kendall_tau`
* SCC / cycle detection — :mod:`networkx` (as ``cycle_detection.py`` itself does)

The single extraction rule (:func:`rank_from_copeland`) is Copeland
aggregation (wins minus losses over *revealed* edges only) with a BM25
tie-break, deliberately **not** graph repair — this pilot studies the
acquisition policy, not the repairer, and Copeland is well-defined on a
partial, possibly-cyclic graph at every acquisition step.

Leakage discipline: every function in this module takes only (a) the fixed
candidate pool, (b) the *revealed-so-far* Copeland tally, and (c) the
qrels-free BM25 prior. None accepts qrels or the oracle's cached answer for
an unrevealed pair — see ``tests/test_offline_active_acquisition.py`` for the
enforced leakage tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx

from consistency_ranker.evaluation import kendall_tau
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.pairwise_prefs import Preference


def normalize_bm25(candidates: tuple[str, ...], bm25: dict[str, float]) -> dict[str, float]:
    vals = [bm25.get(d, 0.0) for d in candidates]
    lo, hi = (min(vals), max(vals)) if vals else (0.0, 0.0)
    span = (hi - lo) or 1.0
    return {d: (bm25.get(d, 0.0) - lo) / span for d in candidates}


def rank_from_copeland(
    candidates: tuple[str, ...],
    copeland: dict[str, float],
    bm25_norm: dict[str, float],
) -> list[str]:
    """The single extraction rule used everywhere: Copeland, BM25 tie-break, id tie-break."""
    return sorted(candidates, key=lambda d: (-copeland[d], -bm25_norm.get(d, 0.0), d))


@dataclass
class StepContext:
    """Per-acquisition-step cached quantities, built once and reused across
    every candidate pair scored at that step (not rebuilt per pair)."""

    candidates: tuple[str, ...]
    copeland: dict[str, float]
    bm25_norm: dict[str, float]
    k: int
    graph: "nx.DiGraph" = field(repr=False)
    scc_of: dict[str, int] = field(default_factory=dict)
    ranking: list[str] = field(default_factory=list)
    n_max: int = 1

    @classmethod
    def build(
        cls,
        candidates: tuple[str, ...],
        revealed: list[tuple[str, str]],
        copeland: dict[str, float],
        bm25_norm: dict[str, float],
        k: int,
    ) -> "StepContext":
        prefs = [Preference(w, loser, 1.0) for w, loser in revealed]
        graph = build_graph(prefs) if prefs else nx.DiGraph()
        graph.add_nodes_from(candidates)
        scc_of: dict[str, int] = {}
        for idx, comp in enumerate(nx.strongly_connected_components(graph)):
            if len(comp) > 1:
                for n in comp:
                    scc_of[n] = idx
        ranking = rank_from_copeland(candidates, copeland, bm25_norm)
        return cls(
            candidates=candidates,
            copeland=copeland,
            bm25_norm=bm25_norm,
            k=k,
            graph=graph,
            scc_of=scc_of,
            ranking=ranking,
            n_max=max(len(candidates) - 1, 1),
        )


def uncertainty_score(ctx: StepContext, i: str, j: str) -> float:
    """Score-margin uncertainty: how close the current (revealed-evidence +
    BM25) combined score of *i* and *j* is. 1.0 = maximally uncertain
    ordering; 0.0 = one strongly dominates the other under current evidence.
    Uses only the current, revealed-so-far state — never the unrevealed
    oracle answer for (i, j).
    """
    ci = ctx.copeland[i] / ctx.n_max + ctx.bm25_norm.get(i, 0.0)
    cj = ctx.copeland[j] / ctx.n_max + ctx.bm25_norm.get(j, 0.0)
    margin = abs(ci - cj)
    return float(1.0 / (1.0 + margin))


def ambiguity_score(ctx: StepContext, i: str, j: str) -> float:
    """Current graph ambiguity: 1.0 if i, j already sit in the same
    strongly-connected component (an unresolved cycle already implicates
    both); 0.5 if either sits in some (other) cycle; else 0.0."""
    si, sj = ctx.scc_of.get(i), ctx.scc_of.get(j)
    if si is not None and si == sj:
        return 1.0
    if si is not None or sj is not None:
        return 0.5
    return 0.0


def _topk_jaccard(a: list[str], b: list[str], k: int) -> float:
    ta, tb = set(a[:k]), set(b[:k])
    union = ta | tb
    return (len(ta & tb) / len(union)) if union else 1.0


def topk_impact_score(ctx: StepContext, i: str, j: str) -> float:
    """Exact counterfactual top-k impact (Phase 4).

    Temporarily adds each hypothetical outcome (i beats j; j beats i),
    recomputes the extraction ranking under the *same* rule used everywhere
    else, and measures (a) top-k membership disagreement between the two
    hypothetical rankings and (b) overall rank-order disagreement (Kendall
    tau, reused from ``evaluation.py``) between them. Higher = the unknown
    outcome of this pair could matter more to the final top-k ranking.
    """
    cop_a = dict(ctx.copeland)
    cop_a[i] += 1.0
    cop_a[j] -= 1.0
    cop_b = dict(ctx.copeland)
    cop_b[j] += 1.0
    cop_b[i] -= 1.0
    ranking_a = rank_from_copeland(ctx.candidates, cop_a, ctx.bm25_norm)
    ranking_b = rank_from_copeland(ctx.candidates, cop_b, ctx.bm25_norm)
    jacc = _topk_jaccard(ranking_a, ranking_b, ctx.k)
    tau = kendall_tau(ranking_a, ranking_b)
    disagreement_topk = 1.0 - jacc
    disagreement_order = (1.0 - tau) / 2.0
    return float(0.5 * disagreement_topk + 0.5 * disagreement_order)


def proposed_score(ctx: StepContext, i: str, j: str) -> float:
    """The pilot's single proposed, non-learned formula (Phase 2/7 ablation 4):

    ``score(i, j) = uncertainty(i, j) * impact(i, j) * (1 + ambiguity(i, j))``

    Acquisition cost is uniform in this dataset (every judgment costs one
    unit), so no explicit cost term is included; this is stated, not hidden.
    """
    u = uncertainty_score(ctx, i, j)
    h = topk_impact_score(ctx, i, j)
    s = ambiguity_score(ctx, i, j)
    return float(u * h * (1.0 + s))


def ablation_impact_only(ctx: StepContext, i: str, j: str) -> float:
    return topk_impact_score(ctx, i, j)


def ablation_uncertainty_only(ctx: StepContext, i: str, j: str) -> float:
    return uncertainty_score(ctx, i, j)


def ablation_impact_x_uncertainty(ctx: StepContext, i: str, j: str) -> float:
    return float(topk_impact_score(ctx, i, j) * uncertainty_score(ctx, i, j))


__all__ = [
    "normalize_bm25",
    "rank_from_copeland",
    "StepContext",
    "uncertainty_score",
    "ambiguity_score",
    "topk_impact_score",
    "proposed_score",
    "ablation_impact_only",
    "ablation_uncertainty_only",
    "ablation_impact_x_uncertainty",
]
