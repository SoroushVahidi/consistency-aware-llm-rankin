"""Periodic repair-specific selector training on train/validation only."""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any, Callable

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

log = logging.getLogger(__name__)

THRESHOLDS = (0.0, 0.0025, 0.005, 0.01)


def _safe_score(record: dict, method: str) -> float | None:
    v = record.get("method_outputs", {}).get(method, {}).get("ndcg_at_k")
    return float(v) if v is not None else None


def repair_label_fn(threshold: float, *, repaired: str = "markov_graph_repaired", unrepaired: str = "markov_graph"):
    def fn(rec: dict) -> int:
        r = _safe_score(rec, repaired)
        u = _safe_score(rec, unrepaired)
        if r is None or u is None:
            return 0
        return 1 if (r - u) >= threshold else 0

    return fn


def _extract_X(records: list[dict], feature_names: list[str], extract_features: Callable) -> np.ndarray:
    rows = []
    for rec in records:
        feats = extract_features(rec)
        rows.append([float(feats.get(n, 0.0)) for n in feature_names])
    return np.array(rows, dtype=float)


def _mean_ndcg(records: list[dict], method: str) -> float:
    vals = [_safe_score(rec, method) for rec in records]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else 0.0


def _selector_utility(
    records: list[dict],
    preds: np.ndarray,
    *,
    default_method: str = "markov_graph",
    override_method: str = "markov_graph_repaired",
) -> float:
    total = 0.0
    n = 0
    for rec, pred in zip(records, preds):
        method = override_method if pred else default_method
        s = _safe_score(rec, method)
        if s is not None:
            total += s
            n += 1
    return total / n if n else 0.0


def _bootstrap_ci(
    records: list[dict],
    preds: np.ndarray,
    *,
    default_method: str,
    override_method: str,
    n_boot: int = 500,
    seed: int = 42,
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(records)
    if n < 2:
        return (math.nan, math.nan)
    utilities = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        sample = [records[i] for i in idx]
        sample_preds = preds[idx]
        utilities.append(
            _selector_utility(
                sample, sample_preds, default_method=default_method, override_method=override_method
            )
        )
    lo, hi = np.percentile(utilities, [2.5, 97.5])
    return float(lo), float(hi)


def _build_model(name: str):
    if name == "logreg":
        return Pipeline([("scaler", StandardScaler()), ("clf", LogisticRegression(max_iter=2000, class_weight="balanced"))])
    if name == "shallow_tree":
        return DecisionTreeClassifier(max_depth=2, class_weight="balanced", random_state=42)
    if name == "tree_depth4":
        return DecisionTreeClassifier(max_depth=4, class_weight="balanced", random_state=42)
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42)
    if name == "random_forest_calibrated":
        return CalibratedClassifierCV(
            RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42),
            cv=3,
        )
    if name == "gradient_boosting":
        return GradientBoostingClassifier(random_state=42)
    raise ValueError(name)


def train_repair_selectors(
    train_records: list[dict],
    val_records: list[dict],
    test_records: list[dict],
    *,
    extract_features: Callable,
    feature_names: list[str],
    out_dir: Path,
    final_eval: bool = False,
) -> dict[str, Any]:
    """Train and evaluate repair selectors. Test eval only when final_eval=True."""
    out_dir.mkdir(parents=True, exist_ok=True)
    default_method = "markov_graph"
    override_method = "markov_graph_repaired"
    results: dict[str, Any] = {"thresholds": {}, "final_eval": final_eval}

    for threshold in THRESHOLDS:
        tkey = f"delta_ge_{threshold:.4f}"
        try:
            results["thresholds"][tkey] = _train_one_threshold(
                threshold,
                train_records,
                val_records,
                test_records,
                extract_features=extract_features,
                feature_names=feature_names,
                final_eval=final_eval,
            )
        except Exception as exc:  # never let one threshold's failure kill the run
            results["thresholds"][tkey] = {
                "positive_train": None,
                "positive_val": None,
                "positive_eval": None,
                "models": [],
                "best_model": None,
                "error": f"N/A: threshold training crashed: {exc}",
            }

    try:
        (out_dir / "selector_training_results.json").write_text(
            json.dumps(results, indent=2, default=str), encoding="utf-8"
        )
    except Exception as exc:
        log.warning("Failed to write selector_training_results.json: %s", exc)
    return results


def _train_one_threshold(
    threshold: float,
    train_records: list[dict],
    val_records: list[dict],
    test_records: list[dict],
    *,
    extract_features: Callable,
    feature_names: list[str],
    final_eval: bool,
) -> dict[str, Any]:
    default_method = "markov_graph"
    override_method = "markov_graph_repaired"
    label_fn = repair_label_fn(threshold)
    y_train = np.array([label_fn(r) for r in train_records], dtype=int)
    y_val = np.array([label_fn(r) for r in val_records], dtype=int)
    eval_records = test_records if final_eval else val_records
    y_eval = np.array([label_fn(r) for r in eval_records], dtype=int)

    X_train = _extract_X(train_records, feature_names, extract_features)
    X_val = _extract_X(val_records, feature_names, extract_features)
    X_eval = _extract_X(eval_records, feature_names, extract_features)

    threshold_results: list[dict] = []

    # Fixed baselines
    never_preds = np.zeros(len(eval_records), dtype=int)
    always_preds = np.ones(len(eval_records), dtype=int)
    for name, preds in [("never_repair", never_preds), ("always_repair", always_preds)]:
        threshold_results.append(
            _summarize_model(
                name, preds, y_eval, eval_records, default_method, override_method, chosen_threshold=None
            )
        )

    # Heuristic: repair if cyclic and large SCC
    heuristic_preds = np.array(
        [
            1
            if rec.get("graph_stats", {}).get("is_cyclic")
            and (rec.get("graph_stats", {}).get("largest_scc_size") or 0) >= 2
            else 0
            for rec in eval_records
        ],
        dtype=int,
    )
    threshold_results.append(
        _summarize_model(
            "heuristic_cyclic_scc",
            heuristic_preds,
            y_eval,
            eval_records,
            default_method,
            override_method,
            chosen_threshold=None,
        )
    )

    if len(np.unique(y_train)) < 2 or len(train_records) < 5:
        return {
            "positive_train": int(y_train.sum()),
            "positive_val": int(y_val.sum()),
            "positive_eval": int(y_eval.sum()),
            "models": threshold_results,
            "best_model": threshold_results[0]["model_name"] if threshold_results else None,
            "skipped_learned": True,
        }

    for model_name in (
        "logreg",
        "shallow_tree",
        "tree_depth4",
        "random_forest",
        "gradient_boosting",
        "random_forest_calibrated",
    ):
        try:
            model = _build_model(model_name)
            model.fit(X_train, y_train)
            if hasattr(model, "predict_proba"):
                val_probs = model.predict_proba(X_val)[:, 1]
            else:
                val_probs = model.predict(X_val).astype(float)
            # Tune threshold on validation only
            best_t, best_util = 0.5, -1.0
            for t in np.linspace(0.05, 0.95, 19):
                val_preds = (val_probs >= t).astype(int)
                util = _selector_utility(
                    val_records, val_preds, default_method=default_method, override_method=override_method
                )
                if util > best_util:
                    best_util = util
                    best_t = float(t)
            if hasattr(model, "predict_proba"):
                eval_probs = model.predict_proba(X_eval)[:, 1]
            else:
                eval_probs = model.predict(X_eval).astype(float)
            eval_preds = (eval_probs >= best_t).astype(int)
            row = _summarize_model(
                model_name,
                eval_preds,
                y_eval,
                eval_records,
                default_method,
                override_method,
                chosen_threshold=best_t,
                probs=eval_probs,
            )
            threshold_results.append(row)
        except Exception as exc:
            threshold_results.append({"model_name": model_name, "error": str(exc)})

    threshold_results.sort(key=lambda r: -(r.get("mean_ndcg_at_10") or -1e9))
    return {
        "positive_train": int(y_train.sum()),
        "positive_val": int(y_val.sum()),
        "positive_eval": int(y_eval.sum()),
        "models": threshold_results,
        "best_model": threshold_results[0]["model_name"] if threshold_results else None,
    }


def _safe_classification_metrics(labels: np.ndarray, preds: np.ndarray) -> dict[str, Any]:
    """Precision/recall/F1/balanced-accuracy that never raise.

    scikit-learn's precision/recall/F1 raise ``ValueError`` on a zero-length
    ``y_true``/``y_pred`` (ran into this in production: a final locked-test
    evaluation with an empty test split crashed the whole run here). Return
    ``None`` with an implicit "not applicable" meaning instead, matching how
    ``balanced_accuracy`` already degrades for single-class labels.
    """
    if labels.size == 0 or preds.size == 0:
        return {"balanced_accuracy": None, "precision": None, "recall": None, "f1": None, "n_eval": 0}
    out: dict[str, Any] = {"n_eval": int(labels.size)}
    out["balanced_accuracy"] = (
        float(balanced_accuracy_score(labels, preds)) if len(np.unique(labels)) > 1 else None
    )
    try:
        out["precision"] = float(precision_score(labels, preds, zero_division=0))
    except Exception:
        out["precision"] = None
    try:
        out["recall"] = float(recall_score(labels, preds, zero_division=0))
    except Exception:
        out["recall"] = None
    try:
        out["f1"] = float(f1_score(labels, preds, zero_division=0))
    except Exception:
        out["f1"] = None
    return out


def _summarize_model(
    name: str,
    preds: np.ndarray,
    labels: np.ndarray,
    records: list[dict],
    default_method: str,
    override_method: str,
    *,
    chosen_threshold: float | None,
    probs: np.ndarray | None = None,
) -> dict[str, Any]:
    mean_ndcg = _selector_utility(records, preds, default_method=default_method, override_method=override_method)
    ci_lo, ci_hi = _bootstrap_ci(records, preds, default_method=default_method, override_method=override_method)
    row: dict[str, Any] = {
        "model_name": name,
        "mean_ndcg_at_10": mean_ndcg,
        "ndcg_ci_95_lo": ci_lo,
        "ndcg_ci_95_hi": ci_hi,
        "override_rate": float(preds.mean()) if len(preds) else 0.0,
        "chosen_probability_threshold": chosen_threshold,
    }
    row.update(_safe_classification_metrics(labels, preds))
    if labels.size == 0:
        row["note"] = "N/A: empty eval split (no examples available for this threshold/split)"
    if probs is not None and labels.size > 0 and len(np.unique(labels)) > 1:
        try:
            row["roc_auc"] = float(roc_auc_score(labels, probs))
            row["pr_auc"] = float(average_precision_score(labels, probs))
            row["brier_score"] = float(brier_score_loss(labels, probs))
        except Exception:
            pass
    # Regret vs oracle repair
    oracle_util = 0.0
    n = 0
    for rec in records:
        d = _safe_score(rec, default_method)
        r = _safe_score(rec, override_method)
        if d is not None and r is not None:
            oracle_util += max(d, r)
            n += 1
    row["regret_vs_repair_oracle"] = (oracle_util / n - mean_ndcg) if n else None
    return row
