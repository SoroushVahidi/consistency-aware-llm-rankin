"""Frontier discovery: does ANY candidate in the frontier beat the incumbent?

**Important correctness note**: the "best candidate" for a query is, by
construction, always at least as good as the incumbent (the incumbent is
itself always one of the candidates -- see `build_repair_frontier`). This
means the classic 2-fixed-action oracle-headroom machinery
(`repair_selector_mining.oracle_headroom.compute_oracle_headroom`), which
assumes `oracle_metric = max(preserve_metric, repair_metric)` for two
INDEPENDENT fixed policies, is degenerate here: `repair_metric` (best
candidate's nDCG) trivially dominates `preserve_metric` (incumbent's nDCG)
for every single query, so `oracle_metric == repair_metric` always, making
`headroom_vs_best_baseline` and its CI collapse to exactly 0 regardless of
the underlying data. That machinery is kept below ONLY as an audit/
cross-reference artifact (`two_action_oracle_headroom_audit_only`, clearly
labeled degenerate) -- the actual "does the frontier ever help" question is
answered by a proper ONE-SIDED bootstrap CI over the per-query deltas
(`best_ndcg - incumbent_ndcg`, which is >= 0 by construction, so no
heterogeneity requirement applies the way it does for a genuinely
two-sided fixed policy).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

import numpy as np

from consistency_ranker.evaluation import ndcg_at_k
from consistency_ranker.repair_selector_mining.oracle_headroom import (
    OracleHeadroomResult,
    PreserveRepairRecord,
    compute_oracle_headroom,
)
from consistency_ranker.statistical_inference import (
    BootstrapIntervalResult,
    bootstrap_mean_interval,
)

from .types import FrontierCandidate


@dataclass(frozen=True)
class QueryFrontierOutcome:
    key: tuple
    dataset: str
    query_id: str
    incumbent_ndcg: float
    best_ndcg: float
    best_candidate_id: str
    worst_ndcg: float
    worst_candidate_id: str
    per_candidate_ndcg: dict[str, float]


def evaluate_query_frontier(
    candidates: list[FrontierCandidate],
    relevance_map: dict[str, int],
    *,
    key: tuple | None = None,
    ndcg_k: int = 10,
) -> QueryFrontierOutcome:
    """*key* identifies this query's frontier for downstream lookups (e.g.
    `localization_summary`). Defaults to `(dataset, query_id)`, but callers
    with multiple frontiers sharing that pair (e.g. one per provider graph
    or construction variant) MUST pass an explicit, unique key so lookups
    resolve to the right candidate list."""
    if not candidates:
        raise ValueError("evaluate_query_frontier requires at least one candidate")
    dataset, query_id = candidates[0].dataset, candidates[0].query_id
    per_candidate = {
        c.candidate_id: ndcg_at_k(c.global_ranking, relevance_map, k=ndcg_k) for c in candidates
    }
    incumbent = next((c for c in candidates if c.candidate_id == "incumbent"), None)
    if incumbent is None:
        raise ValueError(
            "frontier is missing the 'incumbent' candidate -- "
            "build_repair_frontier invariant violated"
        )
    incumbent_ndcg = per_candidate["incumbent"]
    best_id = max(per_candidate, key=lambda cid: per_candidate[cid])
    worst_id = min(per_candidate, key=lambda cid: per_candidate[cid])
    return QueryFrontierOutcome(
        key=key if key is not None else (dataset, query_id),
        dataset=dataset,
        query_id=query_id,
        incumbent_ndcg=incumbent_ndcg,
        best_ndcg=per_candidate[best_id],
        best_candidate_id=best_id,
        worst_ndcg=per_candidate[worst_id],
        worst_candidate_id=worst_id,
        per_candidate_ndcg=per_candidate,
    )


def frontier_records(outcomes: list[QueryFrontierOutcome]) -> list[PreserveRepairRecord]:
    """AUDIT-ONLY: see module docstring -- this feeds the repo's existing
    2-action oracle-headroom machinery, which is degenerate for this
    application (best >= incumbent always). Kept for cross-reference, not
    used for the discovery decision."""
    return [
        PreserveRepairRecord(
            dataset=o.dataset,
            query_id=o.query_id,
            preserve_metric=o.incumbent_ndcg,
            repair_metric=o.best_ndcg,
        )
        for o in outcomes
    ]


def _frontier_decision(
    headroom_ci: BootstrapIntervalResult, headroom_threshold: float
) -> tuple[str, str]:
    lo, hi = headroom_ci.lower, headroom_ci.upper
    if hi is not None and hi <= headroom_threshold:
        return (
            "NO_MEANINGFUL_HEADROOM",
            f"Headroom 95% CI upper bound ({hi:.5f}) does not exceed the threshold "
            f"({headroom_threshold:.5f}); the frontier cannot plausibly beat "
            "always-preserve by more than noise on this slice.",
        )
    if lo is not None and lo > headroom_threshold:
        return (
            "MEANINGFUL_HEADROOM",
            f"Headroom 95% CI lower bound ({lo:.5f}) exceeds the threshold "
            f"({headroom_threshold:.5f}) -- the frontier plausibly beats always-preserve "
            "by a non-noise margin on this slice.",
        )
    return (
        "AMBIGUOUS_NEED_MORE_DATA",
        f"Headroom CI [{lo}, {hi}] straddles the threshold ({headroom_threshold:.5f}); "
        "expand the query sample before deciding.",
    )


@dataclass(frozen=True)
class DiscoveryResult:
    n_queries: int
    mean_incumbent_ndcg: float
    mean_best_ndcg: float
    mean_headroom: float
    headroom_ci: BootstrapIntervalResult
    n_beneficial: int
    n_neutral: int
    n_harmful: int
    frac_queries_with_beneficial_candidate: float
    best_delta: float
    median_delta: float
    worst_delta: float
    oracle_best_method_per_query: dict[tuple, str]
    decision: str
    decision_rationale: str
    two_action_oracle_headroom_audit_only: OracleHeadroomResult | None

    def to_dict(self) -> dict:
        return {
            "n_queries": self.n_queries,
            "mean_incumbent_ndcg": self.mean_incumbent_ndcg,
            "mean_best_ndcg": self.mean_best_ndcg,
            "mean_headroom": self.mean_headroom,
            "headroom_ci": {
                "method": self.headroom_ci.method,
                "lower": self.headroom_ci.lower,
                "upper": self.headroom_ci.upper,
                "frac_gt_zero": self.headroom_ci.frac_gt_zero,
                "reps": self.headroom_ci.reps,
                "seed": self.headroom_ci.seed,
            },
            "n_beneficial": self.n_beneficial,
            "n_neutral": self.n_neutral,
            "n_harmful": self.n_harmful,
            "frac_queries_with_beneficial_candidate": self.frac_queries_with_beneficial_candidate,
            "best_delta": self.best_delta,
            "median_delta": self.median_delta,
            "worst_delta": self.worst_delta,
            "oracle_best_method_per_query": {
                "::".join(str(x) for x in key): m
                for key, m in self.oracle_best_method_per_query.items()
            },
            "decision": self.decision,
            "decision_rationale": self.decision_rationale,
            "two_action_oracle_headroom_audit_only_DEGENERATE_SEE_DOCSTRING": (
                self.two_action_oracle_headroom_audit_only.to_dict()
                if self.two_action_oracle_headroom_audit_only is not None
                else None
            ),
        }


def compute_discovery_result(
    outcomes: list[QueryFrontierOutcome],
    *,
    headroom_threshold: float = 0.01,
) -> DiscoveryResult:
    deltas = [o.best_ndcg - o.incumbent_ndcg for o in outcomes]
    n_beneficial = sum(1 for d in deltas if d > 0)
    n_harmful = sum(1 for d in deltas if d < 0)  # structurally always 0; kept as a sanity check
    n_neutral = len(deltas) - n_beneficial - n_harmful
    headroom_ci = bootstrap_mean_interval(deltas) if deltas else bootstrap_mean_interval([])
    decision, rationale = _frontier_decision(headroom_ci, headroom_threshold)

    records = frontier_records(outcomes)
    two_action = compute_oracle_headroom(records) if records else None

    mean_incumbent = float(np.mean([o.incumbent_ndcg for o in outcomes])) if outcomes else 0.0
    mean_best = float(np.mean([o.best_ndcg for o in outcomes])) if outcomes else 0.0
    return DiscoveryResult(
        n_queries=len(outcomes),
        mean_incumbent_ndcg=mean_incumbent,
        mean_best_ndcg=mean_best,
        mean_headroom=float(np.mean(deltas)) if deltas else 0.0,
        headroom_ci=headroom_ci,
        n_beneficial=n_beneficial,
        n_neutral=n_neutral,
        n_harmful=n_harmful,
        frac_queries_with_beneficial_candidate=(n_beneficial / len(deltas)) if deltas else 0.0,
        best_delta=max(deltas) if deltas else 0.0,
        median_delta=statistics.median(deltas) if deltas else 0.0,
        worst_delta=min(deltas) if deltas else 0.0,
        oracle_best_method_per_query={o.key: o.best_candidate_id for o in outcomes},
        decision=decision,
        decision_rationale=rationale,
        two_action_oracle_headroom_audit_only=two_action,
    )


def localization_summary(
    outcomes: list[QueryFrontierOutcome],
    candidates_by_query: dict[tuple, list[FrontierCandidate]],
) -> dict:
    """Whether benefit localizes to particular SCCs or top-k changes: for
    each query where the oracle-best candidate beats the incumbent, join
    against that candidate's ``modified_sccs``/``topk_membership_changes``.
    Looks candidates up by ``o.key`` (NOT ``(dataset, query_id)``, which may
    not uniquely identify a frontier when callers key by a richer tuple)."""
    n_beneficial = 0
    beneficial_with_scc_change = 0
    beneficial_with_topk_change = 0
    for o in outcomes:
        if o.best_ndcg <= o.incumbent_ndcg:
            continue
        n_beneficial += 1
        cands = candidates_by_query.get(o.key, [])
        best = next((c for c in cands if c.candidate_id == o.best_candidate_id), None)
        if best is None:
            continue
        if best.modified_sccs:
            beneficial_with_scc_change += 1
        if best.topk_membership_changes > 0:
            beneficial_with_topk_change += 1
    return {
        "n_beneficial_queries": n_beneficial,
        "n_beneficial_with_scc_modification": beneficial_with_scc_change,
        "n_beneficial_with_topk_membership_change": beneficial_with_topk_change,
    }


__all__ = [
    "QueryFrontierOutcome",
    "evaluate_query_frontier",
    "frontier_records",
    "DiscoveryResult",
    "compute_discovery_result",
    "localization_summary",
]
