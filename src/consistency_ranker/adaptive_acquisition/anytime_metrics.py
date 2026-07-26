"""Anytime (budget-indexed) trajectory recording for acquisition runs.

Every acquisition step (or batch) appends a snapshot so we can plot quality,
top-k stability, cycles, ambiguity and regret *as a function of budget*, not only
at the final point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from consistency_ranker.adaptive_acquisition.counterfactual import stability_score
from consistency_ranker.evaluation import kendall_tau

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState


@dataclass
class AnytimeTrace:
    query_id: str
    policy: str
    steps: list[dict[str, Any]] = field(default_factory=list)

    def record(
        self,
        state: "AcquisitionState",
        *,
        step: int,
        n_calls: int,
        cost: float,
        strong_calls: int,
        last_action_type: str | None,
        true_ranking: list[str] | None = None,
        full_info_ranking: list[str] | None = None,
        qrels_metric: float | None = None,
    ) -> None:
        view = state.view()
        n_docs = len(state.candidate_ids)
        ranking = list(state.ranking)
        amb = view.ambiguity or {}
        row: dict[str, Any] = {
            "step": step,
            "n_calls": n_calls,
            "cost": cost,
            "strong_calls": strong_calls,
            "last_action_type": last_action_type,
            "n_edges": view.n_edges,
            "is_dag": view.is_dag,
            "n_nontrivial_sccs": view.n_nontrivial_sccs,
            "max_scc_size": view.max_scc_size,
            "n_incomparable_pairs": len(view.incomparable_pairs),
            "fraction_incomparable_pairs": amb.get("fraction_incomparable_pairs"),
            "ambiguity_bucket": amb.get("ambiguity_bucket"),
            "topk_jaccard_min": view.stability.get("topk_jaccard_min"),
            "topk_set_stable": view.stability.get("topk_set_stable"),
            "stability_score": stability_score(view, n_docs),
        }
        if true_ranking is not None and ranking:
            row["kendall_tau_truth"] = float(kendall_tau(ranking, true_ranking))
            k = state.top_k
            top_pred = set(ranking[:k])
            top_true = set(true_ranking[:k])
            inter = len(top_pred & top_true)
            union = len(top_pred | top_true) or 1
            row["topk_jaccard_truth"] = inter / union
            row["topk_set_accuracy"] = 1.0 if top_pred == top_true else 0.0
        if full_info_ranking is not None and ranking:
            row["kendall_tau_full_info"] = float(kendall_tau(ranking, full_info_ranking))
            if true_ranking is not None:
                full_tau = float(kendall_tau(full_info_ranking, true_ranking))
                row["regret_vs_full_info"] = full_tau - row.get("kendall_tau_truth", full_tau)
        if qrels_metric is not None:
            row["qrels_metric"] = qrels_metric
        self.steps.append(row)

    def rows(self) -> list[dict[str, Any]]:
        return [{"query_id": self.query_id, "policy": self.policy, **s} for s in self.steps]

    def final(self) -> dict[str, Any]:
        return self.rows()[-1] if self.steps else {"query_id": self.query_id, "policy": self.policy}


__all__ = ["AnytimeTrace"]
