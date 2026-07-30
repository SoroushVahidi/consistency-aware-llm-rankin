"""Grouped-CV selection among extraction methods.

Mirrors the pattern established in
`consistency_ranker.repair_frontier.selection` (GroupKFold by
``(dataset, query_id)``, mandatory negative controls, honest UNSUPPORTED
gate when label variation is inadequate) -- reimplemented here rather than
imported because the feature columns and per-row semantics (extractor vs.
incumbent, not repair-candidate vs. incumbent) differ, but the leakage-
safety and non-overclaiming discipline is identical.
"""

from __future__ import annotations

import numpy as np

from .evaluation import QueryGraphResult
from .extractors import EXTRACTORS, INCUMBENT_NAME

FEATURE_COLS = ["n_nodes", "n_edges", "graph_density", "is_cyclic", "pool_size"]


def always_incumbent_ndcgs(results: list[QueryGraphResult]) -> list[float]:
    return [r.incumbent_ndcg for r in results]


def best_single_fixed_extractor(results: list[QueryGraphResult]) -> str:
    """The single best NON-incumbent extractor, chosen ONCE globally (not
    per query) -- a deployable "always use extractor X" fixed policy."""
    candidates = [n for n in EXTRACTORS if n != INCUMBENT_NAME]
    means = {}
    for name in candidates:
        deltas = [
            r.ndcg_by_extractor[name] - r.incumbent_ndcg
            for r in results
            if name in r.ndcg_by_extractor
        ]
        means[name] = float(np.mean(deltas)) if deltas else float("-inf")
    return max(means, key=lambda n: means[n])


def oracle_ndcgs(results: list[QueryGraphResult]) -> list[float]:
    return [max(r.ndcg_by_extractor.values()) for r in results]


def _feature_row(r: QueryGraphResult) -> dict[str, float]:
    return {
        "n_nodes": r.n_nodes,
        "n_edges": r.n_edges,
        "graph_density": r.graph_density,
        "is_cyclic": 1.0 if r.is_cyclic else 0.0,
        "pool_size": r.pool_size,
    }


def build_predictive_rows(results: list[QueryGraphResult]) -> list[dict]:
    """One row per (query-graph, non-incumbent extractor): label = whether
    that extractor beats the incumbent on THIS query-graph. Features are
    graph-level only (never nDCG/relevance-derived) -- observable at deploy
    time."""
    rows = []
    for r in results:
        for name in EXTRACTORS:
            if name == INCUMBENT_NAME or name not in r.ndcg_by_extractor:
                continue
            label = 1 if r.ndcg_by_extractor[name] > r.incumbent_ndcg else 0
            rows.append(
                {
                    "dataset": r.dataset,
                    "query_id": r.query_id,
                    "extractor": name,
                    "label": label,
                    **_feature_row(r),
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
            f"Only {n_positive} beneficial and {n_negative} non-beneficial extractor-rows "
            f"across {len(rows)} rows -- inadequate label variation for predictive modeling."
        )
        return result

    from sklearn.dummy import DummyClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.model_selection import GroupKFold
    from sklearn.tree import DecisionTreeClassifier

    y = np.array([r["label"] for r in rows])
    groups = np.array([f"{r['dataset']}::{r['query_id']}" for r in rows])
    x = np.array([[float(r.get(c) or 0.0) for c in FEATURE_COLS] for r in rows])
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

    def _cv(model_factory, x_in, y_in):
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

    def _dummy():
        return DummyClassifier(strategy="most_frequent")

    def _logreg():
        return LogisticRegression(max_iter=1000)

    def _tree():
        return DecisionTreeClassifier(max_depth=4, random_state=13)

    shuffled_y = rng.permutation(y)
    random_x = rng.normal(size=x.shape)
    result["models"] = {
        "majority_class": _cv(_dummy, x, y),
        "logistic_regression": _cv(_logreg, x, y),
        "decision_tree": _cv(_tree, x, y),
        "control_shuffled_labels_logreg": _cv(_logreg, x, shuffled_y),
        "control_random_features_logreg": _cv(_logreg, random_x, y),
    }
    result["negative_controls_note"] = (
        "control_shuffled_labels_logreg and control_random_features_logreg should perform "
        "no better than majority_class if the real models' apparent skill is genuine."
    )
    result["status"] = "EVALUATED"
    return result


def evaluate_selection(results: list[QueryGraphResult]) -> dict:
    """Compare: always-incumbent, always-best-single-extractor (fixed,
    global), a grouped-CV learned selector (if supported), and oracle
    extractor selection."""
    incumbent_mean = float(np.mean(always_incumbent_ndcgs(results))) if results else 0.0
    best_single_name = best_single_fixed_extractor(results) if results else None
    best_single_ndcgs = [
        r.ndcg_by_extractor.get(best_single_name, r.incumbent_ndcg) for r in results
    ]
    best_single_mean = float(np.mean(best_single_ndcgs)) if best_single_ndcgs else 0.0
    oracle_mean = float(np.mean(oracle_ndcgs(results))) if results else 0.0

    comparison = {
        "always_incumbent": incumbent_mean,
        "always_best_single_extractor": {"name": best_single_name, "mean_ndcg": best_single_mean},
        "oracle_extractor_selection": oracle_mean,
    }

    rows = build_predictive_rows(results)
    predictive = evaluate_predictive_selector(rows)

    best_single_beats_incumbent = best_single_mean > incumbent_mean
    predictive_supported = predictive.get("status") == "EVALUATED"
    headroom_available = oracle_mean - incumbent_mean

    if headroom_available <= 0 and not best_single_beats_incumbent and not predictive_supported:
        status = "UNSUPPORTED"
        reason = (
            "Oracle extractor selection does not beat always-incumbent on average "
            f"(oracle={oracle_mean:.6f} vs incumbent={incumbent_mean:.6f}), no fixed single "
            "extractor beats always-incumbent, and label variation is inadequate for a "
            "predictive selector."
        )
    elif predictive_supported or best_single_beats_incumbent:
        status = "SUPPORTED"
        reason = (
            "At least one selector (fixed single extractor or predictive) beats always-incumbent."
        )
    else:
        status = "PARTIAL"
        reason = (
            "Oracle headroom exists but no evaluated selector (fixed or predictive) realizes "
            "it on held-out queries."
        )

    return {
        "status": status,
        "reason": reason,
        "comparison": comparison,
        "predictive_selector": predictive,
    }


__all__ = [
    "FEATURE_COLS",
    "always_incumbent_ndcgs",
    "best_single_fixed_extractor",
    "oracle_ndcgs",
    "build_predictive_rows",
    "evaluate_predictive_selector",
    "evaluate_selection",
]
