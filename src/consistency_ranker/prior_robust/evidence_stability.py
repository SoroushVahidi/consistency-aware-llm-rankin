"""Evidence-supported vs prior-driven stability.

Ordinary sampled stability can look high because the headline top-k is resolved
by the prior. This module computes:

* ``S_total`` — stability under normal prior-priority extraction;
* ``S_evidence`` — stability when prior tie-breaking is randomized / removed;
* ``G_prior = S_total - S_evidence`` — prior-dependence gap.

A large gap means apparent certainty is inherited from the prior.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import networkx as nx

from consistency_ranker.baseline_ranking import priority_topological_ranking
from consistency_ranker.dag_linear_extensions import sample_linear_extensions
from consistency_ranker.prior_robust.prior_dependence import topk_evidence_coverage

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState


def _topk_jaccard(ref: list[str], samples: list[list[str]], k: int) -> float:
    if not samples or not ref:
        return 1.0
    top = set(ref[:k])
    jacs = []
    for s in samples:
        other = set(s[:k])
        union = len(top | other) or 1
        jacs.append(len(top & other) / union)
    return float(min(jacs)) if jacs else 1.0


def _membership_probs(samples: list[list[str]], docs: list[str], k: int) -> dict[str, float]:
    if not samples:
        return {d: 0.0 for d in docs}
    out = {}
    n = len(samples)
    for d in docs:
        hits = sum(1 for s in samples if d in s[:k])
        out[d] = hits / n
    return out


@dataclass
class EvidenceStability:
    s_total: float
    s_evidence: float
    s_prior_randomized: float
    g_prior: float
    topk_membership_total: dict[str, float]
    topk_membership_evidence: dict[str, float]
    topk_membership_prior_rand: dict[str, float]
    n_topk_with_direct_support: int
    fraction_acquired_topk: float
    n_samples: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "s_total": self.s_total,
            "s_evidence": self.s_evidence,
            "s_prior_randomized": self.s_prior_randomized,
            "g_prior": self.g_prior,
            "topk_membership_total": dict(self.topk_membership_total),
            "topk_membership_evidence": dict(self.topk_membership_evidence),
            "topk_membership_prior_rand": dict(self.topk_membership_prior_rand),
            "n_topk_with_direct_support": self.n_topk_with_direct_support,
            "fraction_acquired_topk": self.fraction_acquired_topk,
            "n_samples": self.n_samples,
        }


def _evidence_priority(state: "AcquisitionState") -> dict[str, float]:
    """Priority from acquired vote margins only (no prior scores)."""
    scores = {d: 0.0 for d in state.candidate_ids}
    for pid, agg in state.aggregates.items():
        if agg.d == 0:
            continue
        winner = agg.doc_i if agg.d == 1 else agg.doc_j
        loser = agg.doc_j if agg.d == 1 else agg.doc_i
        w = abs(float(agg.m))
        scores[winner] = scores.get(winner, 0.0) + w
        scores[loser] = scores.get(loser, 0.0) - w
    return scores


def _perturbed_prior(
    prior: dict[str, float], rng: random.Random, *, noise: float = 1.0
) -> dict[str, float]:
    return {d: float(s) + rng.uniform(-noise, noise) for d, s in prior.items()}


def compute_evidence_stability(
    state: "AcquisitionState",
    *,
    n_samples: int = 24,
    seed: int = 0,
    prior_noise: float = 2.0,
) -> EvidenceStability:
    """Compute total / evidence-only / prior-randomized stability and G_prior."""
    view = state.view()
    dag = view.dag
    docs = list(state.candidate_ids)
    k = state.top_k
    rng = random.Random(seed)

    if dag.number_of_nodes() == 0 or not nx.is_directed_acyclic_graph(dag):
        # Fall back: empty / cyclic → fully prior-dependent.
        cov = topk_evidence_coverage(state)
        return EvidenceStability(
            s_total=1.0,
            s_evidence=0.0,
            s_prior_randomized=0.0,
            g_prior=1.0,
            topk_membership_total={d: 1.0 if i < k else 0.0 for i, d in enumerate(state.ranking)},
            topk_membership_evidence={d: 0.0 for d in docs},
            topk_membership_prior_rand={d: 0.0 for d in docs},
            n_topk_with_direct_support=0,
            fraction_acquired_topk=float(cov["fraction_acquired"]),
            n_samples=0,
        )

    # No acquired directional evidence ⇒ apparent order is prior-only.
    n_acquired = sum(1 for a in state.aggregates.values() if a.n_valid_directional > 0)
    if n_acquired == 0 or dag.number_of_edges() == 0:
        cov = topk_evidence_coverage(state)
        samples = sample_linear_extensions(dag, n_samples=n_samples, seed=seed)
        ranking_total = priority_topological_ranking(dag, state.prior_scores)
        s_total = _topk_jaccard(ranking_total, samples, k)
        return EvidenceStability(
            s_total=float(s_total),
            s_evidence=0.0,
            s_prior_randomized=0.0,
            g_prior=float(max(s_total, 0.5)),  # at least half — fully prior-dependent
            topk_membership_total=_membership_probs(samples, docs, k),
            topk_membership_evidence={d: 0.0 for d in docs},
            topk_membership_prior_rand={d: 0.0 for d in docs},
            n_topk_with_direct_support=0,
            fraction_acquired_topk=float(cov["fraction_acquired"]),
            n_samples=len(samples),
        )

    samples = sample_linear_extensions(dag, n_samples=n_samples, seed=seed)
    ranking_total = priority_topological_ranking(dag, state.prior_scores)
    # Evidence-only: use acquired margins; ties broken by document id (no prior).
    ev_prio = _evidence_priority(state)
    # Force id-only among equals by adding tiny id hash — priority_topo already
    # falls back to id, so zero priors + evidence scores is enough.
    ranking_ev = priority_topological_ranking(dag, ev_prio)

    # Prior-randomized: average Jaccard across several perturbed priors.
    rand_rankings = []
    for i in range(max(4, n_samples // 4)):
        pp = _perturbed_prior(state.prior_scores, rng, noise=prior_noise)
        rand_rankings.append(priority_topological_ranking(dag, pp))

    s_total = _topk_jaccard(ranking_total, samples, k)
    s_evidence = _topk_jaccard(ranking_ev, samples, k)
    # Prior-randomized stability: agreement of samples with each perturbed ranking,
    # then mean of the *min* jaccards (conservative).
    s_rand_vals = [_topk_jaccard(r, samples, k) for r in rand_rankings]
    s_prior_rand = float(sum(s_rand_vals) / len(s_rand_vals)) if s_rand_vals else 0.0

    # Membership under evidence-only headline vs total.
    mem_total = _membership_probs(samples, docs, k)
    # Evidence membership: fraction of samples whose top-k matches evidence ranking's top-k members
    # More useful: re-score membership using evidence-priority Kahn samples.
    # Approximate: use random samples (already prior-free) vs evidence ranking.
    mem_ev = _membership_probs(samples, docs, k)
    # Prior-randomized membership: average over perturbed rankings' implied membership
    # via samples relative to each ranking — use mean membership across perturbed tops.
    mem_rand = {d: 0.0 for d in docs}
    for r in rand_rankings:
        top = set(r[:k])
        for d in docs:
            mem_rand[d] += 1.0 / len(rand_rankings) if d in top else 0.0

    cov = topk_evidence_coverage(state)
    # Count top-k members that appear in at least one acquired edge.
    topk = ranking_total[:k]
    supported = 0
    for d in topk:
        for e in state.evidence:
            if e.z != 0 and (e.doc_i == d or e.doc_j == d):
                supported += 1
                break

    g = float(s_total - s_evidence)
    return EvidenceStability(
        s_total=float(s_total),
        s_evidence=float(s_evidence),
        s_prior_randomized=float(s_prior_rand),
        g_prior=g,
        topk_membership_total=mem_total,
        topk_membership_evidence=mem_ev,
        topk_membership_prior_rand=mem_rand,
        n_topk_with_direct_support=supported,
        fraction_acquired_topk=float(cov["fraction_acquired"]),
        n_samples=len(samples),
    )


__all__ = ["EvidenceStability", "compute_evidence_stability"]
