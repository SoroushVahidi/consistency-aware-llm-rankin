"""Interpretable predictors for repair gain / UHT optimality on real queries."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class CriterionResult:
    name: str
    n_queries: int
    mean_utility_delta: float
    n_escalated: int
    escalation_rate: float
    catastrophic_false_trust_rate: float
    notes: str = ""


def _sign_flip_ci(
    deltas: list[float],
    *,
    n_perm: int = 2000,
    seed: int = 0,
) -> tuple[float, float, float]:
    """Return (mean, lo, hi) for a two-sided 95% sign-flip interval on the mean."""
    if not deltas:
        return 0.0, 0.0, 0.0
    mean = sum(deltas) / len(deltas)
    rng = random.Random(seed)
    abs_vals = [abs(d) for d in deltas]
    samples = []
    for _ in range(n_perm):
        s = sum(a if rng.random() < 0.5 else -a for a in abs_vals) / len(abs_vals)
        samples.append(s)
    samples.sort()
    lo = samples[int(0.025 * (n_perm - 1))]
    hi = samples[int(0.975 * (n_perm - 1))]
    return mean, lo, hi


def evaluate_threshold_criterion(
    rows: list[dict[str, Any]],
    *,
    name: str,
    feature_key: str,
    threshold: float,
    direction: str,
    gain_key: str = "repair_gain",
    catastrophic_if_negative: bool = True,
) -> CriterionResult:
    """Escalate to repaired policy when feature crosses threshold; else keep unrepaired (=0 gain).

    Utility delta vs always-unrepaired (which has gain 0 by definition) equals
    repair_gain on escalated queries and 0 otherwise. Vs always-repair, the
    complementary quantity is reported in notes.
    """
    if not rows:
        return CriterionResult(name, 0, 0.0, 0, 0.0, 0.0, "empty")

    deltas: list[float] = []
    n_esc = 0
    n_cat = 0
    for r in rows:
        feat = float(r.get(feature_key) or 0.0)
        gain = float(r.get(gain_key) or 0.0)
        escalate = feat >= threshold if direction == "ge" else feat > threshold
        if direction == "le":
            escalate = feat <= threshold
        if escalate:
            n_esc += 1
            deltas.append(gain)
            if catastrophic_if_negative and gain < -1e-9:
                n_cat += 1
        else:
            deltas.append(0.0)

    mean, lo, hi = _sign_flip_ci(deltas)
    return CriterionResult(
        name=name,
        n_queries=len(rows),
        mean_utility_delta=mean,
        n_escalated=n_esc,
        escalation_rate=n_esc / len(rows),
        catastrophic_false_trust_rate=(n_cat / n_esc) if n_esc else 0.0,
        notes=f"sign_flip_mean_ci95=[{lo:.6f},{hi:.6f}]; feature={feature_key} {direction} {threshold}",
    )


def evaluate_always_repair(rows: list[dict[str, Any]], *, gain_key: str = "repair_gain") -> CriterionResult:
    deltas = [float(r.get(gain_key) or 0.0) for r in rows]
    mean, lo, hi = _sign_flip_ci(deltas)
    n_cat = sum(1 for d in deltas if d < -1e-9)
    return CriterionResult(
        name="always_repair",
        n_queries=len(rows),
        mean_utility_delta=mean,
        n_escalated=len(rows),
        escalation_rate=1.0,
        catastrophic_false_trust_rate=n_cat / len(rows) if rows else 0.0,
        notes=f"sign_flip_mean_ci95=[{lo:.6f},{hi:.6f}]",
    )


def evaluate_always_unrepaired(rows: list[dict[str, Any]]) -> CriterionResult:
    return CriterionResult(
        name="always_unrepaired",
        n_queries=len(rows),
        mean_utility_delta=0.0,
        n_escalated=0,
        escalation_rate=0.0,
        catastrophic_false_trust_rate=0.0,
        notes="baseline; gain defined as repaired - unrepaired",
    )


def evaluate_oracle(rows: list[dict[str, Any]], *, gain_key: str = "repair_gain") -> CriterionResult:
    deltas = [max(0.0, float(r.get(gain_key) or 0.0)) for r in rows]
    mean, lo, hi = _sign_flip_ci(deltas)
    n_esc = sum(1 for r in rows if float(r.get(gain_key) or 0.0) > 0)
    return CriterionResult(
        name="oracle_repair_if_positive",
        n_queries=len(rows),
        mean_utility_delta=mean,
        n_escalated=n_esc,
        escalation_rate=n_esc / len(rows) if rows else 0.0,
        catastrophic_false_trust_rate=0.0,
        notes=f"sign_flip_mean_ci95=[{lo:.6f},{hi:.6f}]; uses outcome labels (not deployable)",
    )


def evaluate_matched_random(
    rows: list[dict[str, Any]],
    *,
    escalation_rate: float,
    gain_key: str = "repair_gain",
    seed: int = 0,
) -> CriterionResult:
    """Random routing at a matched escalation rate (query-level, not judgment-level)."""
    if not rows:
        return CriterionResult("random_matched", 0, 0.0, 0, 0.0, 0.0, "empty")
    rng = random.Random(seed)
    n = len(rows)
    k = int(round(escalation_rate * n))
    idx = list(range(n))
    rng.shuffle(idx)
    chosen = set(idx[:k])
    deltas = []
    n_cat = 0
    for i, r in enumerate(rows):
        gain = float(r.get(gain_key) or 0.0)
        if i in chosen:
            deltas.append(gain)
            if gain < -1e-9:
                n_cat += 1
        else:
            deltas.append(0.0)
    mean, lo, hi = _sign_flip_ci(deltas, seed=seed + 1)
    return CriterionResult(
        name=f"random_matched_rate_{escalation_rate:.2f}",
        n_queries=n,
        mean_utility_delta=mean,
        n_escalated=k,
        escalation_rate=k / n,
        catastrophic_false_trust_rate=(n_cat / k) if k else 0.0,
        notes=f"sign_flip_mean_ci95=[{lo:.6f},{hi:.6f}]",
    )


def fit_logistic_1d(
    rows: list[dict[str, Any]],
    *,
    feature_key: str,
    label_fn: Callable[[dict[str, Any]], float],
    n_steps: int = 200,
    lr: float = 0.5,
) -> tuple[float, float]:
    """Return (weight, bias) for P(label=1 | feature) via hand GD logistic."""
    xs = [float(r.get(feature_key) or 0.0) for r in rows]
    ys = [float(label_fn(r)) for r in rows]
    w, b = 0.0, 0.0
    n = max(len(xs), 1)
    for _ in range(n_steps):
        gw = gb = 0.0
        for x, y in zip(xs, ys):
            z = w * x + b
            p = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))
            gw += (p - y) * x
            gb += p - y
        w -= lr * gw / n
        b -= lr * gb / n
    return w, b


def evaluate_logistic_1d(
    train: list[dict[str, Any]],
    test: list[dict[str, Any]],
    *,
    feature_key: str,
    gain_key: str = "repair_gain",
    decision_threshold: float = 0.5,
) -> CriterionResult:
    """Train on train folds to predict repair_gain>0; apply on test."""

    def label(r: dict[str, Any]) -> float:
        return 1.0 if float(r.get(gain_key) or 0.0) > 0 else 0.0

    w, b = fit_logistic_1d(train, feature_key=feature_key, label_fn=label)
    deltas = []
    n_esc = 0
    n_cat = 0
    for r in test:
        x = float(r.get(feature_key) or 0.0)
        z = w * x + b
        p = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))
        gain = float(r.get(gain_key) or 0.0)
        if p >= decision_threshold:
            n_esc += 1
            deltas.append(gain)
            if gain < -1e-9:
                n_cat += 1
        else:
            deltas.append(0.0)
    mean, lo, hi = _sign_flip_ci(deltas)
    return CriterionResult(
        name=f"logistic1d_{feature_key}",
        n_queries=len(test),
        mean_utility_delta=mean,
        n_escalated=n_esc,
        escalation_rate=n_esc / len(test) if test else 0.0,
        catastrophic_false_trust_rate=(n_cat / n_esc) if n_esc else 0.0,
        notes=f"w={w:.4f},b={b:.4f}; sign_flip_mean_ci95=[{lo:.6f},{hi:.6f}]",
    )


def leave_one_dataset_out(
    rows: list[dict[str, Any]],
    *,
    feature_key: str,
    gain_key: str = "repair_gain",
) -> list[CriterionResult]:
    datasets = sorted({str(r["dataset"]) for r in rows})
    results = []
    for held in datasets:
        train = [r for r in rows if str(r["dataset"]) != held]
        test = [r for r in rows if str(r["dataset"]) == held]
        if len(train) < 5 or len(test) < 3:
            results.append(
                CriterionResult(
                    name=f"lodo_{held}_{feature_key}",
                    n_queries=len(test),
                    mean_utility_delta=float("nan"),
                    n_escalated=0,
                    escalation_rate=0.0,
                    catastrophic_false_trust_rate=0.0,
                    notes="insufficient folds",
                )
            )
            continue
        res = evaluate_logistic_1d(train, test, feature_key=feature_key, gain_key=gain_key)
        res.name = f"lodo_{held}_{feature_key}"
        results.append(res)
    return results
