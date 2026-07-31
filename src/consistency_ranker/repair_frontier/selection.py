"""Deployable, label-free selectors over the repair frontier, plus a
grouped-CV predictive-model gate mirroring
``scripts/run_reviewer_concerns_program.py``'s ``stage5_predict`` (GroupKFold
by ``(dataset, query_id)``, mandatory negative controls, and an honest
UNSUPPORTED path when label variation is inadequate -- never fit a model to
a near-constant target).
"""

from __future__ import annotations

import numpy as np

from consistency_ranker.evaluation import ndcg_at_k

from .discovery import QueryFrontierOutcome
from .types import FrontierCandidate

# Label-free features: graph-level (shared across a query's candidates) plus
# per-candidate solver bookkeeping. Never an nDCG/relevance-derived quantity.
SELECTION_FEATURE_COLS = [
    "n_nodes", "n_edges", "graph_density", "n_sccs", "n_non_trivial_sccs",
    "largest_scc_size", "scc_cycle_burden", "n_mutual_pairs", "total_edge_weight",
    "fas_objective", "n_reversed_or_removed", "weight_reversed_or_removed",
    "protected_edge_violations", "topk_membership_changes",
]


def _feature_row(candidate: FrontierCandidate) -> dict[str, float]:
    gf = candidate.graph_features
    return {
        "n_nodes": gf.get("n_nodes", 0),
        "n_edges": gf.get("n_edges", 0),
        "graph_density": gf.get("graph_density", 0.0),
        "n_sccs": gf.get("n_sccs", 0),
        "n_non_trivial_sccs": gf.get("n_non_trivial_sccs", 0),
        "largest_scc_size": gf.get("largest_scc_size", 0),
        "scc_cycle_burden": gf.get("scc_cycle_burden", 0),
        "n_mutual_pairs": gf.get("n_mutual_pairs", 0),
        "total_edge_weight": gf.get("total_edge_weight", 0.0),
        "fas_objective": candidate.fas_objective,
        "n_reversed_or_removed": candidate.n_reversed_or_removed,
        "weight_reversed_or_removed": candidate.weight_reversed_or_removed,
        "protected_edge_violations": candidate.protected_edge_violations,
        "topk_membership_changes": candidate.topk_membership_changes,
    }


def _deployable_candidates(candidates: list[FrontierCandidate]) -> list[FrontierCandidate]:
    """Excludes ``oracle_analysis_only`` candidates -- those use relevance
    labels and are never deployable."""
    return [c for c in candidates if c.acceptance_mode != "oracle_analysis_only"]


def select_always_preserve(candidates: list[FrontierCandidate]) -> FrontierCandidate:
    return next(c for c in _deployable_candidates(candidates) if c.candidate_id == "incumbent")


def select_min_fas_objective(candidates: list[FrontierCandidate]) -> FrontierCandidate:
    pool = _deployable_candidates(candidates)
    return min(pool, key=lambda c: (c.fas_objective, c.candidate_id != "incumbent"))


def _select_named_method(
    candidates: list[FrontierCandidate], method_prefix: str
) -> FrontierCandidate | None:
    pool = [
        c for c in _deployable_candidates(candidates) if c.candidate_id.startswith(method_prefix)
    ]
    if not pool:
        return None
    return min(pool, key=lambda c: c.fas_objective)


def select_greedy(candidates: list[FrontierCandidate]) -> FrontierCandidate:
    found = _select_named_method(candidates, "whole_graph_greedy")
    return found or select_always_preserve(candidates)


def select_exact(candidates: list[FrontierCandidate]) -> FrontierCandidate:
    found = _select_named_method(candidates, "whole_graph_exact")
    return found or select_always_preserve(candidates)


def select_objective_improvement_threshold(
    candidates: list[FrontierCandidate], *, tau: float = 0.05
) -> FrontierCandidate:
    incumbent = select_always_preserve(candidates)
    pool = [c for c in _deployable_candidates(candidates) if c.candidate_id != "incumbent"]
    if not pool or incumbent.fas_objective <= 0:
        return incumbent
    best = min(pool, key=lambda c: c.fas_objective)
    improvement = (incumbent.fas_objective - best.fas_objective) / incumbent.fas_objective
    return best if improvement > tau else incumbent


def select_low_confidence_changed_edges_only(
    candidates: list[FrontierCandidate], *, max_protected_violations: int = 0
) -> FrontierCandidate:
    """Pick the best-objective SCC-local candidate whose changes triggered
    no protected-edge violations (i.e. only low-confidence/disputed edges
    were touched); falls back to always-preserve."""
    incumbent = select_always_preserve(candidates)
    pool = [
        c
        for c in _deployable_candidates(candidates)
        if c.candidate_id.startswith("scc_local_")
        and c.candidate_id != "incumbent"
        and c.protected_edge_violations <= max_protected_violations
    ]
    if not pool:
        return incumbent
    return min(pool, key=lambda c: c.fas_objective)


DEPLOYABLE_SELECTORS = {
    "always_preserve": select_always_preserve,
    "min_fas_objective": select_min_fas_objective,
    "greedy": select_greedy,
    "exact": select_exact,
    "objective_improvement_threshold": select_objective_improvement_threshold,
    "low_confidence_changed_edges_only": select_low_confidence_changed_edges_only,
}


def _build_feature_matrix(
    candidates_by_query: dict[tuple[str, str], list[FrontierCandidate]],
    relevance_maps: dict[tuple[str, str], dict[str, int]],
    outcomes_by_query: dict[tuple[str, str], QueryFrontierOutcome],
    *,
    ndcg_k: int = 10,
) -> list[dict]:
    """One row per (query, non-incumbent candidate): label = whether that
    candidate beats the incumbent's nDCG. Multiple rows share a query, so
    grouping by ``(dataset, query_id)`` is mandatory downstream."""
    rows = []
    for key, cands in candidates_by_query.items():
        rel = relevance_maps[key]
        incumbent_ndcg = outcomes_by_query[key].incumbent_ndcg
        for c in _deployable_candidates(cands):
            if c.candidate_id == "incumbent":
                continue
            cand_ndcg = ndcg_at_k(c.global_ranking, rel, k=ndcg_k)
            rows.append(
                {
                    "dataset": key[0],
                    "query_id": key[1],
                    "candidate_id": c.candidate_id,
                    "label": 1 if cand_ndcg > incumbent_ndcg else 0,
                    **_feature_row(c),
                }
            )
    return rows


def evaluate_predictive_selector(rows: list[dict]) -> dict:
    n_positive = sum(1 for r in rows if r["label"] == 1)
    n_negative = len(rows) - n_positive
    result: dict = {
        "n_rows": len(rows),
        "n_positive_rows": n_positive,
        "n_negative_rows": n_negative,
    }

    if n_positive < 4 or n_negative < 4:
        result["status"] = "UNSUPPORTED"
        result["reason"] = (
            f"Only {n_positive} beneficial and {n_negative} non-beneficial candidate-rows "
            f"across {len(rows)} rows -- inadequate label variation for predictive modeling. "
            "Reporting UNSUPPORTED rather than fitting a model to a near-constant target."
        )
        return result

    from sklearn.dummy import DummyClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.model_selection import GroupKFold
    from sklearn.tree import DecisionTreeClassifier

    y = np.array([r["label"] for r in rows])
    groups = np.array([f"{r['dataset']}::{r['query_id']}" for r in rows])
    x = np.array([[float(r.get(c) or 0.0) for c in SELECTION_FEATURE_COLS] for r in rows])
    n_groups = len(set(groups))
    result["n_groups"] = n_groups
    if n_groups < 3 or len(set(y)) < 2:
        result["status"] = "UNSUPPORTED"
        result["reason"] = (
            f"n_unique_query_groups={n_groups}, n_classes={len(set(y))} -- too few for "
            "grouped cross-validation."
        )
        return result

    n_splits = min(4, n_groups)
    gkf = GroupKFold(n_splits=n_splits)
    rng = np.random.RandomState(13)

    def _cv_balanced_accuracy(model_factory, x_in, y_in):
        scores = []
        for train_idx, test_idx in gkf.split(x_in, y_in, groups):
            if len(set(y_in[train_idx])) < 2:
                continue
            model = model_factory()
            model.fit(x_in[train_idx], y_in[train_idx])
            pred = model.predict(x_in[test_idx])
            scores.append(balanced_accuracy_score(y_in[test_idx], pred))
        return {
            "mean_balanced_accuracy": float(np.mean(scores)) if scores else float("nan"),
            "n_folds_used": len(scores),
        }

    def _logreg():
        return LogisticRegression(max_iter=1000)

    def _dummy():
        return DummyClassifier(strategy="most_frequent")

    def _tree():
        return DecisionTreeClassifier(max_depth=4, random_state=13)

    shuffled_y = rng.permutation(y)
    random_x = rng.normal(size=x.shape)
    result["models"] = {
        "majority_class": _cv_balanced_accuracy(_dummy, x, y),
        "logistic_regression": _cv_balanced_accuracy(_logreg, x, y),
        "decision_tree": _cv_balanced_accuracy(_tree, x, y),
        "control_shuffled_labels_logreg": _cv_balanced_accuracy(_logreg, x, shuffled_y),
        "control_random_features_logreg": _cv_balanced_accuracy(_logreg, random_x, y),
    }
    result["negative_controls_note"] = (
        "control_shuffled_labels_logreg and control_random_features_logreg should perform "
        "no better than majority_class if the real models' apparent skill is genuine."
    )
    result["status"] = "EVALUATED"
    return result


def evaluate_selection(
    candidates_by_query: dict[tuple[str, str], list[FrontierCandidate]],
    relevance_maps: dict[tuple[str, str], dict[str, int]],
    outcomes_by_query: dict[tuple[str, str], QueryFrontierOutcome],
    *,
    ndcg_k: int = 10,
) -> dict:
    """Compare deployable selectors against never-repair, always-repair,
    min-objective-candidate, and the frontier oracle. Returns
    ``status in {"SUPPORTED", "PARTIAL", "UNSUPPORTED"}`` -- never fits or
    reports a predictive model when label variation/oracle headroom is
    inadequate."""
    keys = sorted(candidates_by_query)
    if not keys:
        return {"status": "UNSUPPORTED", "reason": "no queries provided"}

    def _selector_mean_ndcg(fn) -> float:
        ndcgs = [
            ndcg_at_k(fn(candidates_by_query[k]).global_ranking, relevance_maps[k], k=ndcg_k)
            for k in keys
        ]
        return float(np.mean(ndcgs))

    fixed_mean_ndcg = {name: _selector_mean_ndcg(fn) for name, fn in DEPLOYABLE_SELECTORS.items()}
    oracle_mean_ndcg = float(np.mean([outcomes_by_query[k].best_ndcg for k in keys]))

    comparison = {
        "never_repair": fixed_mean_ndcg["always_preserve"],
        "always_repair": fixed_mean_ndcg["greedy"],
        "min_objective_candidate": fixed_mean_ndcg["min_fas_objective"],
        "frontier_oracle": oracle_mean_ndcg,
        "all_fixed_selectors": fixed_mean_ndcg,
    }

    predictive_rows = _build_feature_matrix(
        candidates_by_query, relevance_maps, outcomes_by_query, ndcg_k=ndcg_k
    )
    predictive = evaluate_predictive_selector(predictive_rows)

    headroom_available = oracle_mean_ndcg - fixed_mean_ndcg["always_preserve"]
    best_fixed_beats_preserve = max(fixed_mean_ndcg.values()) > fixed_mean_ndcg["always_preserve"]
    predictive_supported = predictive.get("status") == "EVALUATED"

    if headroom_available <= 0 and not best_fixed_beats_preserve and not predictive_supported:
        status = "UNSUPPORTED"
        preserve_ndcg = fixed_mean_ndcg["always_preserve"]
        reason = (
            "Frontier oracle does not beat always-preserve on average "
            f"(oracle={oracle_mean_ndcg:.6f} vs preserve={preserve_ndcg:.6f}), "
            "no fixed selector beats always-preserve, and label variation is inadequate for a "
            "predictive selector -- selection is UNSUPPORTED on this data; do not deploy a "
            "learned or fixed repair-preferring policy."
        )
    elif predictive_supported or best_fixed_beats_preserve:
        status = "SUPPORTED"
        reason = "At least one selector (fixed or predictive) beats always-preserve on this data."
    else:
        status = "PARTIAL"
        reason = (
            "Frontier oracle headroom exists but no evaluated selector (fixed or predictive) "
            "realizes it -- generation found benefit, selection did not."
        )

    return {
        "status": status,
        "reason": reason,
        "fixed_selector_comparison": comparison,
        "predictive_selector": predictive,
    }


__all__ = [
    "SELECTION_FEATURE_COLS",
    "DEPLOYABLE_SELECTORS",
    "select_always_preserve",
    "select_min_fas_objective",
    "select_greedy",
    "select_exact",
    "select_objective_improvement_threshold",
    "select_low_confidence_changed_edges_only",
    "evaluate_predictive_selector",
    "evaluate_selection",
]
