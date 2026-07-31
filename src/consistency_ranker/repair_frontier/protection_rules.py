"""Configurable, HARD edge-protection rules for SCC-local repair.

Protection is HARD, not a soft preference: a protected edge is excluded
from the removable-edge set passed to the solver (via a shadow graph whose
`weight` is overwritten to a large removal cost -- see
:func:`annotate_removal_costs`), so the solver only ever removes a
protected edge when every non-protected cut is exhausted. This makes
"protected edges cannot be reversed" a hard guarantee for every *accepted*
candidate: if a cycle cannot be broken without a protected edge, that
candidate is infeasible for the SCC (the caller abstains, keeping the
incumbent local order) rather than silently violating protection.

``protected_edge_violations`` on a :class:`~.types.FrontierCandidate` counts
how many protected edges were implicated in such a residual/unresolved
cycle -- i.e. it flags *abstention caused by over-aggressive protection*,
not a broken promise.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Literal

import networkx as nx

from .types import EdgeConfidence

ProtectionKind = Literal[
    "none",
    "unanimous_multi_provider",
    "confidence_threshold",
    "margin_threshold",
    "topk_boundary_crossing",
    "low_confidence_first",
]

# Cost multiplier applied to a protected edge's removal cost. Large enough
# that the solver only ever picks a protected edge when every non-protected
# cut is exhausted (i.e. the SCC cannot be made acyclic without it).
PROTECTED_COST_MULTIPLIER = 1.0e6


@dataclass(frozen=True)
class EdgeProtectionRule:
    kind: ProtectionKind = "none"
    reliability_tau: float = 0.25
    """Confidence-threshold rules: minimum agreement fraction to protect.
    ``low_confidence_first``: fraction of a SCC's edges (the least-confident
    ones) left OPEN for repair; the rest are protected -- a relative,
    SCC-scoped notion of "primarily disputed edges", distinct from the
    absolute global threshold used by ``confidence_threshold``."""
    margin_tau: float = 0.2
    min_providers_for_unanimity: int = 2
    topk: int | None = None
    topk_window: int = 2

    @property
    def rule_id(self) -> str:
        if self.kind == "none":
            return "none"
        if self.kind == "topk_boundary_crossing":
            return f"{self.kind}:topk={self.topk}:window={self.topk_window}"
        if self.kind in ("confidence_threshold", "low_confidence_first"):
            return f"{self.kind}:tau={self.reliability_tau}"
        if self.kind == "margin_threshold":
            return f"{self.kind}:tau={self.margin_tau}"
        if self.kind == "unanimous_multi_provider":
            return f"{self.kind}:min_providers={self.min_providers_for_unanimity}"
        return self.kind


def _reliability(conf: EdgeConfidence | None) -> float:
    """Default to 1.0 (treat as high-confidence/protectable) when no
    provider evidence is available -- without evidence we should not
    consider an edge "disputed" and therefore repairable."""
    return conf.reliability if conf is not None else 1.0


def _is_protected_pointwise(
    u: str,
    v: str,
    conf: EdgeConfidence | None,
    rule: EdgeProtectionRule,
    *,
    incumbent_rank: dict[str, int] | None,
) -> bool:
    if rule.kind == "unanimous_multi_provider":
        return bool(
            conf is not None
            and conf.unanimous
            and conf.n_providers_total >= rule.min_providers_for_unanimity
        )
    if rule.kind == "confidence_threshold":
        return _reliability(conf) >= rule.reliability_tau
    if rule.kind == "margin_threshold":
        return conf is not None and abs(conf.margin) >= rule.margin_tau
    if rule.kind == "topk_boundary_crossing":
        if incumbent_rank is None or rule.topk is None:
            return False
        ru, rv = incumbent_rank.get(u), incumbent_rank.get(v)
        if ru is None or rv is None:
            return False
        lo, hi = rule.topk, rule.topk + rule.topk_window
        u_in_core, v_in_core = ru < rule.topk, rv < rule.topk
        u_in_band, v_in_band = lo <= ru < hi, lo <= rv < hi
        return (u_in_core and v_in_band) or (v_in_core and u_in_band)
    return False


def protected_edges(
    sub: nx.DiGraph,
    confidences: dict[tuple[str, str], EdgeConfidence],
    rule: EdgeProtectionRule,
    *,
    incumbent_rank: dict[str, int] | None = None,
) -> set[tuple[str, str]]:
    """Return the set of (u, v) edges of *sub* protected under *rule*."""
    if rule.kind == "none":
        return set()
    edges = list(sub.edges())
    if not edges:
        return set()
    if rule.kind == "low_confidence_first":
        # Sort least-confident first; the bottom `reliability_tau` fraction
        # stays open for repair, everything else is protected.
        scored = sorted(edges, key=lambda e: _reliability(confidences.get(e)))
        n_open = max(1, round(len(edges) * rule.reliability_tau))
        open_for_repair = set(scored[:n_open])
        return set(edges) - open_for_repair
    return {
        (u, v)
        for u, v in edges
        if _is_protected_pointwise(
            u, v, confidences.get((u, v)), rule, incumbent_rank=incumbent_rank
        )
    }


def annotate_removal_costs(
    sub: nx.DiGraph,
    confidences: dict[tuple[str, str], EdgeConfidence],
    rule: EdgeProtectionRule,
    *,
    incumbent_rank: dict[str, int] | None = None,
    weight_attr: str = "weight",
) -> tuple[nx.DiGraph, set[tuple[str, str]]]:
    """Return (shadow_graph, protected_set).

    ``shadow_graph`` is a copy of *sub* with ``weight_attr`` overwritten to
    a removal cost: protected edges get a cost inflated by
    :data:`PROTECTED_COST_MULTIPLIER`; unprotected edges keep their
    original weight. The original weight is preserved under
    ``orig_weight`` so callers can remap removed-edge weights back for
    objective/reporting purposes.
    """
    protected = protected_edges(sub, confidences, rule, incumbent_rank=incumbent_rank)
    shadow = copy.deepcopy(sub)
    for u, v, data in shadow.edges(data=True):
        orig_w = float(data.get(weight_attr, 1.0))
        data["orig_weight"] = orig_w
        if (u, v) in protected:
            data[weight_attr] = orig_w * PROTECTED_COST_MULTIPLIER + PROTECTED_COST_MULTIPLIER
    return shadow, protected


__all__ = [
    "ProtectionKind",
    "PROTECTED_COST_MULTIPLIER",
    "EdgeProtectionRule",
    "protected_edges",
    "annotate_removal_costs",
]
