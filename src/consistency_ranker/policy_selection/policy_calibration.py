"""Interpretable calibration models for prior-quality and policy optimality.

Primary models: logistic regression, isotonic / beta calibration wrappers,
shallow decision tree, multinomial logistic. Fitted only on training regimes;
never on test labels at inference.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from consistency_ranker.policy_selection.gate_features import FEATURE_SCHEMA_VERSION

ModelKind = Literal[
    "logistic",
    "multinomial_logistic",
    "isotonic",
    "beta",
    "shallow_tree",
    "heuristic",
]


def _sigmoid(x: float) -> float:
    if x >= 30:
        return 1.0
    if x <= -30:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


@dataclass
class CalibratedModel:
    kind: ModelKind
    feature_names: list[str]
    schema_version: str = FEATURE_SCHEMA_VERSION
    # Logistic / multinomial
    weights: list[float] = field(default_factory=list)
    bias: float = 0.0
    class_weights: dict[str, list[float]] = field(default_factory=dict)
    class_biases: dict[str, float] = field(default_factory=dict)
    classes: list[str] = field(default_factory=list)
    # Isotonic: piecewise constant on sorted scores
    iso_x: list[float] = field(default_factory=list)
    iso_y: list[float] = field(default_factory=list)
    # Beta calibration: a, b, c on logit
    beta_a: float = 1.0
    beta_b: float = 0.0
    beta_c: float = 0.0
    # Shallow tree: list of (feat_idx, threshold, left_leaf, right_leaf) depth-1
    tree_feat: int = 0
    tree_threshold: float = 0.5
    tree_left: float = 0.3
    tree_right: float = 0.7
    # Training metadata
    training_regimes: list[str] = field(default_factory=list)
    target_name: str = "uht_optimal"
    n_train: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "feature_names": list(self.feature_names),
            "schema_version": self.schema_version,
            "weights": list(self.weights),
            "bias": self.bias,
            "class_weights": {k: list(v) for k, v in self.class_weights.items()},
            "class_biases": dict(self.class_biases),
            "classes": list(self.classes),
            "iso_x": list(self.iso_x),
            "iso_y": list(self.iso_y),
            "beta_a": self.beta_a,
            "beta_b": self.beta_b,
            "beta_c": self.beta_c,
            "tree_feat": self.tree_feat,
            "tree_threshold": self.tree_threshold,
            "tree_left": self.tree_left,
            "tree_right": self.tree_right,
            "training_regimes": list(self.training_regimes),
            "target_name": self.target_name,
            "n_train": self.n_train,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CalibratedModel":
        if d.get("schema_version") != FEATURE_SCHEMA_VERSION:
            raise ValueError(
                f"Incompatible feature schema {d.get('schema_version')!r}; "
                f"expected {FEATURE_SCHEMA_VERSION!r}"
            )
        return cls(
            kind=d["kind"],
            feature_names=list(d["feature_names"]),
            schema_version=d["schema_version"],
            weights=list(d.get("weights") or []),
            bias=float(d.get("bias") or 0.0),
            class_weights={k: list(v) for k, v in (d.get("class_weights") or {}).items()},
            class_biases=dict(d.get("class_biases") or {}),
            classes=list(d.get("classes") or []),
            iso_x=list(d.get("iso_x") or []),
            iso_y=list(d.get("iso_y") or []),
            beta_a=float(d.get("beta_a", 1.0)),
            beta_b=float(d.get("beta_b", 0.0)),
            beta_c=float(d.get("beta_c", 0.0)),
            tree_feat=int(d.get("tree_feat", 0)),
            tree_threshold=float(d.get("tree_threshold", 0.5)),
            tree_left=float(d.get("tree_left", 0.3)),
            tree_right=float(d.get("tree_right", 0.7)),
            training_regimes=list(d.get("training_regimes") or []),
            target_name=str(d.get("target_name", "uht_optimal")),
            n_train=int(d.get("n_train") or 0),
            metadata=dict(d.get("metadata") or {}),
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "CalibratedModel":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass
class CalibrationReport:
    brier: float
    log_loss: float
    ece: float
    accuracy: float
    n: int
    reliability_bins: list[dict[str, float]] = field(default_factory=list)
    decision_utility: float | None = None
    subgroup: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "brier": self.brier,
            "log_loss": self.log_loss,
            "ece": self.ece,
            "accuracy": self.accuracy,
            "n": self.n,
            "reliability_bins": list(self.reliability_bins),
            "decision_utility": self.decision_utility,
            "subgroup": dict(self.subgroup),
        }


def _raw_logistic_score(model: CalibratedModel, x: list[float]) -> float:
    if model.kind == "shallow_tree":
        idx = min(model.tree_feat, len(x) - 1) if x else 0
        val = x[idx] if x else 0.0
        return model.tree_right if val >= model.tree_threshold else model.tree_left
    if model.kind == "heuristic":
        # Simple hand weights matching prior_quality heuristic orientation.
        # Expects agreement-like features near the end of probe vector.
        if len(x) >= 12:
            agree = x[10] if len(x) > 10 else 0.5  # weighted_agreement approx
            contra = x[11] if len(x) > 11 else 0.0
            sep = x[1] if len(x) > 1 else 0.5
            return 0.55 * agree + 0.15 * (1 - contra) + 0.15 * sep + 0.15
        return 0.5
    if not model.weights:
        return model.bias
    return _dot(model.weights, x[: len(model.weights)]) + model.bias


def _apply_isotonic(model: CalibratedModel, s: float) -> float:
    if not model.iso_x:
        return s
    # Piecewise constant on midpoints of sorted x.
    xs, ys = model.iso_x, model.iso_y
    if s <= xs[0]:
        return ys[0]
    if s >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= s <= xs[i + 1]:
            # linear interp
            t = (s - xs[i]) / (xs[i + 1] - xs[i] + 1e-12)
            return ys[i] * (1 - t) + ys[i + 1] * t
    return ys[-1]


def _apply_beta(model: CalibratedModel, p: float) -> float:
    p = min(1 - 1e-6, max(1e-6, p))
    logit = math.log(p / (1 - p))
    return _sigmoid(model.beta_a * logit + model.beta_b * math.log(p) + model.beta_c)


def predict_proba(model: CalibratedModel, x: list[float]) -> float:
    """P(positive) for binary models."""
    if model.schema_version != FEATURE_SCHEMA_VERSION:
        raise ValueError("Incompatible feature schema version")
    if model.kind == "multinomial_logistic":
        probs = predict_multinomial(model, x)
        # positive = first class if binary-like
        if model.classes:
            return float(probs.get(model.classes[0], 0.0))
        return 0.5
    s = _raw_logistic_score(model, x)
    if model.kind in ("logistic", "heuristic", "shallow_tree"):
        p = s if model.kind in ("shallow_tree", "heuristic") and 0 <= s <= 1 else _sigmoid(s)
    else:
        p = _sigmoid(s)
    if model.kind == "isotonic" or model.iso_x:
        p = _apply_isotonic(model, p if model.kind != "isotonic" else s)
    if model.kind == "beta" or (model.beta_a != 1.0 or model.beta_b != 0.0 or model.beta_c != 0.0):
        if model.kind == "beta":
            p = _apply_beta(model, p)
    return float(max(0.0, min(1.0, p)))


def predict_multinomial(model: CalibratedModel, x: list[float]) -> dict[str, float]:
    if not model.classes:
        return {}
    logits = {}
    for c in model.classes:
        w = model.class_weights.get(c, [0.0] * len(x))
        b = model.class_biases.get(c, 0.0)
        logits[c] = _dot(w, x[: len(w)]) + b
    m = max(logits.values())
    exps = {c: math.exp(v - m) for c, v in logits.items()}
    z = sum(exps.values()) or 1.0
    return {c: float(exps[c] / z) for c in model.classes}


def _fit_logistic_gd(
    X: list[list[float]],
    y: list[float],
    *,
    lr: float = 0.2,
    n_iter: int = 400,
    l2: float = 0.01,
) -> tuple[list[float], float]:
    d = len(X[0]) if X else 0
    w = [0.0] * d
    b = 0.0
    n = max(len(X), 1)
    for _ in range(n_iter):
        gw = [0.0] * d
        gb = 0.0
        for xi, yi in zip(X, y):
            p = _sigmoid(_dot(w, xi) + b)
            err = p - yi
            for j in range(d):
                gw[j] += err * xi[j]
            gb += err
        for j in range(d):
            w[j] -= lr * (gw[j] / n + l2 * w[j])
        b -= lr * (gb / n)
    return w, b


def _fit_isotonic(scores: list[float], y: list[float]) -> tuple[list[float], list[float]]:
    """PAV isotonic regression (non-decreasing)."""
    if not scores:
        return [], []
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    xs = [scores[i] for i in order]
    ys = [y[i] for i in order]
    # Pool adjacent violators
    blocks: list[list[float]] = [[ys[0]]]
    block_x: list[list[float]] = [[xs[0]]]
    for i in range(1, len(ys)):
        blocks.append([ys[i]])
        block_x.append([xs[i]])
        while len(blocks) >= 2:
            m1 = sum(blocks[-2]) / len(blocks[-2])
            m2 = sum(blocks[-1]) / len(blocks[-1])
            if m1 <= m2:
                break
            blocks[-2].extend(blocks[-1])
            block_x[-2].extend(block_x[-1])
            blocks.pop()
            block_x.pop()
    out_x, out_y = [], []
    for bx, by in zip(block_x, blocks):
        out_x.append(sum(bx) / len(bx))
        out_y.append(sum(by) / len(by))
    return out_x, out_y


def _fit_shallow_tree(X: list[list[float]], y: list[float]) -> tuple[int, float, float, float]:
    """Depth-1 stump maximizing Gini / MSE reduction on binary y."""
    if not X:
        return 0, 0.5, 0.5, 0.5
    d = len(X[0])
    best = (0, 0.5, sum(y) / len(y), sum(y) / len(y))
    best_imp = float("inf")
    for j in range(d):
        vals = sorted(set(xi[j] for xi in X))
        for t in vals:
            left = [yi for xi, yi in zip(X, y) if xi[j] < t]
            right = [yi for xi, yi in zip(X, y) if xi[j] >= t]
            if not left or not right:
                continue
            ml = sum(left) / len(left)
            mr = sum(right) / len(right)
            imp = (
                sum((yi - ml) ** 2 for yi in left)
                + sum((yi - mr) ** 2 for yi in right)
            ) / len(y)
            if imp < best_imp:
                best_imp = imp
                best = (j, t, ml, mr)
    return best


def fit_calibrated_gate(
    X: list[list[float]],
    y: list[float],
    *,
    feature_names: list[str],
    kind: ModelKind = "logistic",
    training_regimes: list[str] | None = None,
    target_name: str = "uht_optimal",
    classes: list[str] | None = None,
    y_multi: list[str] | None = None,
) -> CalibratedModel:
    """Fit an interpretable calibrated model on training features only."""
    model = CalibratedModel(
        kind=kind,
        feature_names=list(feature_names),
        training_regimes=list(training_regimes or []),
        target_name=target_name,
        n_train=len(y),
    )
    if kind == "multinomial_logistic" and y_multi and classes:
        model.classes = list(classes)
        # One-vs-rest logistic
        for c in classes:
            yy = [1.0 if yi == c else 0.0 for yi in y_multi]
            w, b = _fit_logistic_gd(X, yy)
            model.class_weights[c] = w
            model.class_biases[c] = b
        return model

    if kind == "shallow_tree":
        j, t, left, right = _fit_shallow_tree(X, y)
        model.tree_feat = j
        model.tree_threshold = t
        model.tree_left = left
        model.tree_right = right
        return model

    if kind == "heuristic":
        return model

    w, b = _fit_logistic_gd(X, y)
    model.weights = w
    model.bias = b
    raw = [predict_proba(model, xi) for xi in X]

    if kind == "isotonic":
        model.iso_x, model.iso_y = _fit_isotonic(raw, y)
        model.kind = "isotonic"
    elif kind == "beta":
        # Fit a,b,c by simple GD on log-loss of beta-calibrated probs.
        beta_a, beta_b, beta_c = 1.0, 0.0, 0.0
        for _ in range(200):
            ga = gb = gc = 0.0
            for p, yi in zip(raw, y):
                p = min(1 - 1e-6, max(1e-6, p))
                logit = math.log(p / (1 - p))
                logp = math.log(p)
                z = beta_a * logit + beta_b * logp + beta_c
                ph = _sigmoid(z)
                err = ph - yi
                ga += err * logit
                gb += err * logp
                gc += err
            n = max(len(raw), 1)
            beta_a -= 0.05 * ga / n
            beta_b -= 0.05 * gb / n
            beta_c -= 0.05 * gc / n
        model.beta_a, model.beta_b, model.beta_c = beta_a, beta_b, beta_c
        model.kind = "beta"
    else:
        model.kind = "logistic"
    return model


def evaluation_metrics(
    y_true: list[float],
    y_prob: list[float],
    *,
    n_bins: int = 8,
) -> CalibrationReport:
    n = len(y_true)
    if n == 0:
        return CalibrationReport(brier=0.0, log_loss=0.0, ece=0.0, accuracy=0.0, n=0)
    brier = sum((p - t) ** 2 for p, t in zip(y_prob, y_true)) / n
    ll = 0.0
    for p, t in zip(y_prob, y_true):
        p = min(1 - 1e-9, max(1e-9, p))
        ll += -(t * math.log(p) + (1 - t) * math.log(1 - p))
    ll /= n
    preds = [1.0 if p >= 0.5 else 0.0 for p in y_prob]
    acc = sum(1 for a, b in zip(preds, y_true) if a == b) / n
    # ECE
    bins: list[dict[str, float]] = []
    ece = 0.0
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        idx = [i for i, p in enumerate(y_prob) if (lo <= p < hi) or (b == n_bins - 1 and p == 1.0)]
        if not idx:
            bins.append({"lo": lo, "hi": hi, "conf": 0.0, "acc": 0.0, "n": 0.0})
            continue
        conf = sum(y_prob[i] for i in idx) / len(idx)
        a = sum(y_true[i] for i in idx) / len(idx)
        ece += (len(idx) / n) * abs(conf - a)
        bins.append({"lo": lo, "hi": hi, "conf": conf, "acc": a, "n": float(len(idx))})
    return CalibrationReport(
        brier=float(brier),
        log_loss=float(ll),
        ece=float(ece),
        accuracy=float(acc),
        n=n,
        reliability_bins=bins,
    )


__all__ = [
    "ModelKind",
    "CalibratedModel",
    "CalibrationReport",
    "fit_calibrated_gate",
    "predict_proba",
    "predict_multinomial",
    "evaluation_metrics",
]
