"""Grouped-CV prediction of repair outcome using PRE-REPAIR features only,
plus deployable policy-nDCG comparison against never-repair, always-repair,
random selection, and oracle selection.

Reuses ``consistency_ranker.repair_selector_mining.oracle_headroom``'s
``PreserveRepairRecord``/``compute_oracle_headroom``/``evaluate_go_no_go``
for the oracle-headroom gate -- this IS the well-fitting use case that
machinery was designed for (two genuinely independent fixed actions:
preserve vs. this repository's canonical greedy whole-graph repair), unlike
a "best-of-many-candidates" framing where one action trivially dominates.

Only ``simple, interpretable predictors`` are fit (single-feature
threshold, shallow decision tree, regularized logistic regression) --
deliberately no ensembles or deep trees, since the number of independent
query groups here is small (at most 6).
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from consistency_ranker.repair_selector_mining.oracle_headroom import (
    GoNoGoResult,
    OracleHeadroomResult,
    PreserveRepairRecord,
    compute_oracle_headroom,
    evaluate_go_no_go,
)

from .features import PRE_REPAIR_FEATURE_NAMES
from .outcomes import QueryGraphDiagnostic


def build_records(results: list[QueryGraphDiagnostic]) -> list[PreserveRepairRecord]:
    return [
        PreserveRepairRecord(
            dataset=d.dataset,
            query_id=d.query_id,
            preserve_metric=d.ndcg_preserve,
            repair_metric=d.ndcg_repair,
        )
        for d in results
    ]


def compute_headroom_gate(
    results: list[QueryGraphDiagnostic],
    *,
    headroom_threshold: float = 0.01,
    min_heterogeneity_fraction: float = 0.05,
) -> tuple[OracleHeadroomResult, GoNoGoResult]:
    records = build_records(results)
    headroom = compute_oracle_headroom(records)
    gate = evaluate_go_no_go(
        headroom,
        headroom_threshold=headroom_threshold,
        min_heterogeneity_fraction=min_heterogeneity_fraction,
    )
    return headroom, gate


def baseline_policies(results: list[QueryGraphDiagnostic]) -> dict:
    """Requirement 7: never-repair, always-repair, random selection (analytic
    expectation of a 50/50 coin-flip policy), and oracle selection."""
    preserve = [d.ndcg_preserve for d in results]
    repair = [d.ndcg_repair for d in results]
    oracle = [max(d.ndcg_preserve, d.ndcg_repair) for d in results]
    mean_preserve = float(np.mean(preserve)) if preserve else 0.0
    mean_repair = float(np.mean(repair)) if repair else 0.0
    return {
        "never_repair": mean_preserve,
        "always_repair": mean_repair,
        "random_selection": 0.5 * mean_preserve + 0.5 * mean_repair,
        "oracle_selection": float(np.mean(oracle)) if oracle else 0.0,
    }


def _feature_matrix(
    results: list[QueryGraphDiagnostic],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rows = [d.pre_repair.as_numeric_row() for d in results]
    x = np.array([[row[name] for name in PRE_REPAIR_FEATURE_NAMES] for row in rows])
    y = np.array([1 if d.outcome == "improves" else 0 for d in results])
    groups = np.array([f"{d.dataset}::{d.query_id}" for d in results])
    return x, y, groups


def _decision_stump_predictor(x_train: np.ndarray, y_train: np.ndarray):
    """Best single pre-repair feature + threshold + direction maximizing
    TRAIN balanced accuracy -- fit ONLY on the training fold, so the
    grouped-CV score is a genuine held-out estimate, not an in-sample one."""
    from sklearn.metrics import balanced_accuracy_score

    best = None
    for j in range(x_train.shape[1]):
        col = x_train[:, j]
        candidates = np.unique(col)
        if candidates.size < 2:
            continue
        thresholds = (candidates[:-1] + candidates[1:]) / 2.0
        for thr in thresholds:
            for direction in (1, -1):
                pred = (col >= thr).astype(int) if direction == 1 else (col < thr).astype(int)
                acc = balanced_accuracy_score(y_train, pred)
                if best is None or acc > best[0]:
                    best = (acc, j, thr, direction)
    if best is None:
        majority = int(round(np.mean(y_train))) if y_train.size else 0
        return lambda x: np.full(x.shape[0], majority)
    _, j, thr, direction = best
    if direction == 1:
        return lambda x: (x[:, j] >= thr).astype(int)
    return lambda x: (x[:, j] < thr).astype(int)


def evaluate_predictors(results: list[QueryGraphDiagnostic], *, n_splits_max: int = 4) -> dict:
    """Requirement 5/6/8: simple interpretable predictors, grouped CV by
    ``(dataset, query_id)``, both classification performance and out-of-fold
    policy nDCG (never fit and predicted on the same rows)."""
    x, y, groups = _feature_matrix(results)
    n_groups = len(set(groups))
    n_positive = int(y.sum())
    n_negative = int(len(y) - y.sum())
    out: dict = {
        "n_rows": len(results),
        "n_groups": n_groups,
        "class_balance": {"positive": n_positive, "negative": n_negative},
    }
    if n_groups < 3 or len(set(y)) < 2:
        out["status"] = "UNSUPPORTED"
        out["reason"] = (
            f"n_unique_query_groups={n_groups}, n_classes={len(set(y))} -- too few for "
            "grouped cross-validation."
        )
        return out
    if n_positive < 4 or n_negative < 4:
        out["status"] = "UNSUPPORTED"
        out["reason"] = (
            f"Only {n_positive} 'improves' and {n_negative} non-improving rows -- inadequate "
            "class balance for grouped-CV classification (folds without any positive example "
            "would trivially inflate balanced accuracy for every model, including negative "
            "controls). Reporting UNSUPPORTED rather than a misleading metric."
        )
        return out

    from sklearn.dummy import DummyClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.model_selection import GroupKFold
    from sklearn.tree import DecisionTreeClassifier

    n_splits = min(n_splits_max, n_groups)
    gkf = GroupKFold(n_splits=n_splits)
    rng = np.random.RandomState(23)

    def _run(model_kind: str, x_in: np.ndarray, y_in: np.ndarray) -> dict:
        accs = []
        policy_ndcgs = []
        oof_rows = []  # per-row out-of-fold predictions, for subgroup-stability checks
        for train_idx, test_idx in gkf.split(x_in, y_in, groups):
            if len(set(y_in[train_idx])) < 2:
                continue
            if model_kind == "stump":
                predict_fn = _decision_stump_predictor(x_in[train_idx], y_in[train_idx])
                pred = predict_fn(x_in[test_idx])
            elif model_kind == "tree":
                model = DecisionTreeClassifier(max_depth=2, random_state=23)
                model.fit(x_in[train_idx], y_in[train_idx])
                pred = model.predict(x_in[test_idx])
            elif model_kind == "logreg":
                model = LogisticRegression(C=0.1, max_iter=1000)  # L2 penalty is sklearn's default
                model.fit(x_in[train_idx], y_in[train_idx])
                pred = model.predict(x_in[test_idx])
            elif model_kind == "majority":
                model = DummyClassifier(strategy="most_frequent")
                model.fit(x_in[train_idx], y_in[train_idx])
                pred = model.predict(x_in[test_idx])
            else:
                raise ValueError(model_kind)
            accs.append(balanced_accuracy_score(y_in[test_idx], pred))
            for i, idx in enumerate(test_idx):
                d = results[idx]
                policy_ndcg = d.ndcg_repair if pred[i] == 1 else d.ndcg_preserve
                policy_ndcgs.append(policy_ndcg)
                oof_rows.append(
                    {
                        "dataset": d.dataset,
                        "provider": d.provider,
                        "pool_size": d.pool_size,
                        "pred": int(pred[i]),
                        "policy_ndcg": policy_ndcg,
                        "ndcg_preserve": d.ndcg_preserve,
                    }
                )
        return {
            "mean_balanced_accuracy": float(np.mean(accs)) if accs else float("nan"),
            "n_folds_used": len(accs),
            "policy_mean_ndcg": float(np.mean(policy_ndcgs)) if policy_ndcgs else float("nan"),
            "n_policy_rows": len(policy_ndcgs),
            "oof_rows": oof_rows,
        }

    shuffled_y = rng.permutation(y)
    random_x = rng.normal(size=x.shape)

    out["models"] = {
        "majority_class": _run("majority", x, y),
        "single_feature_threshold": _run("stump", x, y),
        "shallow_decision_tree": _run("tree", x, y),
        "regularized_logistic_regression": _run("logreg", x, y),
        "control_shuffled_labels_logreg": _run("logreg", x, shuffled_y),
        "control_random_features_logreg": _run("logreg", random_x, y),
    }
    out["negative_controls_note"] = (
        "control_shuffled_labels_logreg and control_random_features_logreg should perform "
        "no better than majority_class if the real models' apparent skill is genuine."
    )
    out["status"] = "EVALUATED"
    return out


def subgroup_stability(model_result: dict, *, key_name: str) -> dict:
    """Requirement 10.4: fraction of major subgroups (grouped by
    ``key_name`` in {"dataset","provider","pool_size"}) where this model's
    out-of-fold policy nDCG beats never-repair WITHIN that subgroup."""
    oof_rows = model_result.get("oof_rows", [])
    by_group_policy: dict = defaultdict(list)
    by_group_preserve: dict = defaultdict(list)
    for row in oof_rows:
        key = row[key_name]
        by_group_policy[key].append(row["policy_ndcg"])
        by_group_preserve[key].append(row["ndcg_preserve"])
    n_pass = 0
    n_total = 0
    detail = {}
    for key, policy_vals in by_group_policy.items():
        policy_mean = float(np.mean(policy_vals))
        preserve_mean = float(np.mean(by_group_preserve[key]))
        passed = policy_mean > preserve_mean
        detail[str(key)] = {
            "n": len(policy_vals),
            "policy_mean_ndcg": policy_mean,
            "never_repair_mean_ndcg": preserve_mean,
            "passes": passed,
        }
        n_total += 1
        n_pass += int(passed)
    return {"fraction_passing": (n_pass / n_total) if n_total else 0.0, "detail": detail}


__all__ = [
    "build_records",
    "compute_headroom_gate",
    "baseline_policies",
    "evaluate_predictors",
    "subgroup_stability",
]
