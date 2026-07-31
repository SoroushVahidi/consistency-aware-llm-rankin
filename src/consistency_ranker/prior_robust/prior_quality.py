"""Query-level prior-quality estimation without qrels.

Estimators use only acquired judgments, prior score geometry, and optional
cross-prior agreement. Never fit on test labels.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from consistency_ranker.prior_robust.prior_dependence import (
    evidence_fraction_summary,
    relation_support,
)
from consistency_ranker.reliability_repair.edge_reliability import estimate_reliability

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState


@dataclass
class PriorQualityEstimate:
    q_hat: float  # in [0, 1]
    agreement_rate: float | None
    contradiction_rate: float | None
    high_conf_contradiction_rate: float | None
    score_entropy: float
    topk_separation: float
    cross_prior_agreement: float | None
    n_acquired: int
    components: dict[str, float] = field(default_factory=dict)
    method: str = "heuristic"

    def to_dict(self) -> dict[str, Any]:
        return {
            "q_hat": self.q_hat,
            "agreement_rate": self.agreement_rate,
            "contradiction_rate": self.contradiction_rate,
            "high_conf_contradiction_rate": self.high_conf_contradiction_rate,
            "score_entropy": self.score_entropy,
            "topk_separation": self.topk_separation,
            "cross_prior_agreement": self.cross_prior_agreement,
            "n_acquired": self.n_acquired,
            "components": dict(self.components),
            "method": self.method,
        }


def _normalized_scores(prior: dict[str, float]) -> dict[str, float]:
    vals = list(prior.values())
    if not vals:
        return {}
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        return {d: 1.0 / len(prior) for d in prior}
    return {d: (float(s) - lo) / (hi - lo) for d, s in prior.items()}


def prior_score_entropy(prior: dict[str, float]) -> float:
    """Entropy of softmax-normalized prior scores, scaled to [0, 1]."""
    if len(prior) < 2:
        return 0.0
    # Softmax on raw scores.
    mx = max(prior.values())
    exps = {d: math.exp(float(s) - mx) for d, s in prior.items()}
    z = sum(exps.values()) or 1.0
    probs = [v / z for v in exps.values()]
    h = -sum(p * math.log(p) for p in probs if p > 0)
    return float(h / math.log(len(prior)))


def topk_score_separation(prior: dict[str, float], k: int) -> float:
    """Normalized margin between k-th and (k+1)-th prior scores (0=no sep, 1=large)."""
    ordered = sorted(prior.items(), key=lambda x: (-float(x[1]), x[0]))
    if len(ordered) <= k:
        return 1.0
    sk = float(ordered[k - 1][1])
    sk1 = float(ordered[k][1])
    spread = float(ordered[0][1]) - float(ordered[-1][1])
    if spread <= 0:
        return 0.0
    return float(max(0.0, min(1.0, (sk - sk1) / spread)))


def judgment_prior_agreement(
    state: "AcquisitionState",
    *,
    min_reliability: float = 0.3,
) -> dict[str, float | None]:
    agree = contra = hc_contra = hc_total = 0
    w_agree = w_total = 0.0
    for pid in state.all_pair_ids():
        s = relation_support(state, pid)
        if not s.acquired or s.direction == 0:
            continue
        agg = state.aggregates[pid]
        rel = float(estimate_reliability(agg))
        if s.prior_agree is True:
            agree += 1
            w_agree += rel
        elif s.prior_agree is False:
            contra += 1
            if rel >= min_reliability:
                hc_contra += 1
        if rel >= min_reliability:
            hc_total += 1
        w_total += rel
    n = agree + contra
    return {
        "agreement_rate": (agree / n) if n else None,
        "contradiction_rate": (contra / n) if n else None,
        "weighted_agreement": (w_agree / w_total) if w_total else None,
        "high_conf_contradiction_rate": (hc_contra / hc_total) if hc_total else None,
        "n_scored": float(n),
    }


def cross_prior_kendall(priors: list[dict[str, float]]) -> float | None:
    """Mean pairwise Kendall agreement across alternative priors."""
    if len(priors) < 2:
        return None
    from consistency_ranker.evaluation import kendall_tau

    ranks = []
    for p in priors:
        ranks.append(sorted(p, key=lambda d: (-float(p[d]), d)))
    taus = []
    for i in range(len(ranks)):
        for j in range(i + 1, len(ranks)):
            if set(ranks[i]) == set(ranks[j]) and ranks[i]:
                taus.append(float(kendall_tau(ranks[i], ranks[j])))
    return sum(taus) / len(taus) if taus else None


def estimate_prior_quality(
    state: "AcquisitionState",
    *,
    alt_priors: list[dict[str, float]] | None = None,
    method: str = "heuristic",
) -> PriorQualityEstimate:
    """Heuristic (default) or logistic-features prior-quality estimate in [0,1]."""
    agr = judgment_prior_agreement(state)
    ent = prior_score_entropy(state.prior_scores)
    sep = topk_score_separation(state.prior_scores, state.top_k)
    cross = cross_prior_kendall(alt_priors) if alt_priors else None
    summary = evidence_fraction_summary(state)

    # Components: high agreement → high Q; high contradiction → low Q;
    # peaked scores (low entropy) + separation → mild boost (geometry only).
    agree = agr["agreement_rate"]
    contra = agr["contradiction_rate"]
    hc = agr["high_conf_contradiction_rate"]

    if agree is None:
        # No acquired judgments yet: rely on geometry + mild prior (0.5).
        q = 0.5 + 0.2 * sep - 0.1 * ent
        components = {"geometry_sep": sep, "geometry_entropy": ent, "base": 0.5}
    else:
        q = (
            0.55 * float(agree)
            + 0.15 * (1.0 - float(hc or 0.0))
            + 0.15 * sep
            + 0.10 * (1.0 - ent)
            + 0.05 * (float(cross) if cross is not None else 0.5)
        )
        components = {
            "agreement": float(agree),
            "inv_hc_contra": 1.0 - float(hc or 0.0),
            "sep": sep,
            "inv_entropy": 1.0 - ent,
            "cross": float(cross) if cross is not None else 0.5,
        }

    if method == "logistic":
        # Interpretable logistic on the same features (fixed coeffs, not qrel-fitted).
        x = (
            1.5 * (agree if agree is not None else 0.5)
            - 2.0 * (hc if hc is not None else 0.0)
            + 0.8 * sep
            - 0.5 * ent
        )
        q = 1.0 / (1.0 + math.exp(-x))
        method_used = "logistic"
    else:
        method_used = "heuristic"

    q = float(max(0.0, min(1.0, q)))
    return PriorQualityEstimate(
        q_hat=q,
        agreement_rate=agree if agree is None else float(agree),
        contradiction_rate=contra if contra is None else float(contra),
        high_conf_contradiction_rate=hc if hc is None else float(hc),
        score_entropy=float(ent),
        topk_separation=float(sep),
        cross_prior_agreement=cross if cross is None else float(cross),
        n_acquired=int(summary["n_acquired"]),
        components=components,
        method=method_used,
    )


__all__ = [
    "PriorQualityEstimate",
    "estimate_prior_quality",
    "prior_score_entropy",
    "topk_score_separation",
    "judgment_prior_agreement",
    "cross_prior_kendall",
]
