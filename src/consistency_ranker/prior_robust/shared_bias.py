"""Shared-bias simulation helpers and effective judge diversity.

Agreement across judges is insufficient when they share systematic bias.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from consistency_ranker.reliability_repair.pair_evidence import NormalizedEvidence


@dataclass
class BiasConfig:
    """Latent shared biases injected into the interactive judge."""

    position_bias: float = 0.0
    length_bias: float = 0.0  # prefer longer doc_id as proxy when enabled
    provider_family_bias: dict[str, float] = None  # type: ignore[assignment]
    prompt_family_bias: dict[str, float] = None  # type: ignore[assignment]
    correlated_repeat: float = 0.0
    shared_latent_flip_rate: float = 0.0  # all judges flip the same pairs

    def __post_init__(self) -> None:
        if self.provider_family_bias is None:
            self.provider_family_bias = {}
        if self.prompt_family_bias is None:
            self.prompt_family_bias = {}


def judge_key(e: NormalizedEvidence) -> tuple[str, str, str]:
    return (str(e.provider), str(e.model), str(e.prompt_version))


def pairwise_error_correlation(
    evidence: list[NormalizedEvidence],
    true_winners: dict[str, str],
) -> dict[tuple[str, str], float]:
    """Pearson-like agreement of error indicators across judge pairs.

    For each judge and each pair with a true winner, error=1 if the judge's
    directional outcome disagrees with truth.
    """
    by_judge: dict[tuple, dict[str, int]] = defaultdict(dict)
    for e in evidence:
        if e.z == 0 or e.canonical_pair_id not in true_winners:
            continue
        true = true_winners[e.canonical_pair_id]
        pred = e.doc_i if e.z == 1 else e.doc_j
        by_judge[judge_key(e)][e.canonical_pair_id] = 0 if pred == true else 1

    judges = sorted(by_judge)
    corr: dict[tuple[str, str], float] = {}
    for i, a in enumerate(judges):
        for b in judges[i + 1 :]:
            common = set(by_judge[a]) & set(by_judge[b])
            if len(common) < 3:
                continue
            xa = [by_judge[a][p] for p in common]
            xb = [by_judge[b][p] for p in common]
            ma, mb = sum(xa) / len(xa), sum(xb) / len(xb)
            num = sum((x - ma) * (y - mb) for x, y in zip(xa, xb))
            da = sum((x - ma) ** 2 for x in xa) ** 0.5
            db = sum((y - mb) ** 2 for y in xb) ** 0.5
            if da > 0 and db > 0:
                corr[(f"{a}", f"{b}")] = float(num / (da * db))
    return corr


def effective_judge_count(
    evidence: list[NormalizedEvidence],
    true_winners: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Estimate N_eff from mean pairwise error correlation (or outcome correlation).

    Without truth, use disagreement with the aggregate direction as a proxy error.
    """
    judges = {(e.provider, e.model) for e in evidence if e.provider}
    n = len(judges)
    if n <= 1:
        return {"n_judges": n, "n_effective": float(n), "mean_corr": 0.0}

    # Build per-judge signed outcomes per pair.
    by_j: dict[tuple, dict[str, float]] = defaultdict(dict)
    for e in evidence:
        if e.z == 0:
            continue
        by_j[(e.provider, e.model)][e.canonical_pair_id] = float(e.z)

    keys = sorted(by_j)
    corrs = []
    for i, a in enumerate(keys):
        for b in keys[i + 1 :]:
            common = set(by_j[a]) & set(by_j[b])
            if len(common) < 3:
                continue
            xa = [by_j[a][p] for p in common]
            xb = [by_j[b][p] for p in common]
            ma, mb = sum(xa) / len(xa), sum(xb) / len(xb)
            num = sum((x - ma) * (y - mb) for x, y in zip(xa, xb))
            da = math.sqrt(sum((x - ma) ** 2 for x in xa))
            db = math.sqrt(sum((y - mb) ** 2 for y in xb))
            if da > 0 and db > 0:
                corrs.append(num / (da * db))
    mean_corr = sum(corrs) / len(corrs) if corrs else 0.0
    mean_corr = max(0.0, min(1.0, mean_corr))
    # Classic Kish-style: N_eff = N / (1 + (N-1) ρ)
    n_eff = n / (1.0 + (n - 1) * mean_corr) if n > 0 else 0.0
    return {
        "n_judges": n,
        "n_effective": float(n_eff),
        "mean_corr": float(mean_corr),
        "n_corr_pairs": len(corrs),
    }


def ensemble_shrinkage_weights(
    evidence: list[NormalizedEvidence],
    *,
    floor: float = 0.1,
) -> dict[tuple[str, str], float]:
    """Down-weight judges that are highly correlated with others (heuristic)."""
    stats = effective_judge_count(evidence)
    n = max(int(stats["n_judges"]), 1)
    n_eff = float(stats["n_effective"])
    # Uniform if uncorrelated; otherwise shrink toward equal share of N_eff.
    judges = sorted({(e.provider, e.model) for e in evidence if e.provider})
    if not judges:
        return {}
    base = n_eff / n
    return {j: float(max(floor, base)) for j in judges}


__all__ = [
    "BiasConfig",
    "pairwise_error_correlation",
    "effective_judge_count",
    "ensemble_shrinkage_weights",
]
