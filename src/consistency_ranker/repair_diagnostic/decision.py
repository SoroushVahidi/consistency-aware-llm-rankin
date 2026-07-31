"""Predeclared conclusion for the repair-regime diagnostic study.

Declared BEFORE inspecting results. Per the task's requirement 10, a
"useful regime" (``STABLE_REPAIR_REGIME_FOUND``) is claimed only if ALL of
the following hold:

  1. based on pre-repair features -- architecturally guaranteed:
     ``prediction.py``'s feature matrix is built exclusively from
     ``features.PRE_REPAIR_FEATURE_NAMES``, never from post-repair features;
  2. survives grouped validation -- the best real (non-control) model's
     grouped-CV balanced accuracy clears both the majority-class baseline
     and the negative controls by a non-trivial margin;
  3. improves policy nDCG over never-repairing;
  4. stable across major subgroups -- the predicted policy beats
     never-repair in most (not just the aggregate) dataset/provider/
     pool-size subgroups;
  5. practically meaningful -- the policy-nDCG improvement clears the same
     0.01 threshold used throughout this research thread's other studies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Decision = Literal[
    "STABLE_REPAIR_REGIME_FOUND",
    "WEAK_DESCRIPTIVE_PATTERN_ONLY",
    "ORACLE_ONLY_NOT_PREDICTABLE",
    "NO_IDENTIFIABLE_REPAIR_REGIME",
]

MEANINGFUL_THRESHOLD = 0.01
MIN_ACCURACY_MARGIN = 0.05
MIN_STABILITY_FRACTION = 0.6


@dataclass(frozen=True)
class DecisionResult:
    decision: Decision
    rationale: str
    conditions: dict
    best_model_name: str
    best_model_accuracy: float
    policy_ndcg: float


def best_real_model(models: dict) -> tuple[str, float]:
    real = {
        k: v for k, v in models.items() if not k.startswith("control_") and k != "majority_class"
    }
    if not real:
        return "", float("nan")
    name = max(real, key=lambda k: real[k]["mean_balanced_accuracy"])
    return name, real[name]["mean_balanced_accuracy"]


def decide(
    *,
    headroom_gate_decision: str,
    oracle_headroom_mean: float,
    predictor_status: str,
    models: dict,
    never_repair_ndcg: float,
    stability_pass_fraction: float,
    meaningful_threshold: float = MEANINGFUL_THRESHOLD,
    min_accuracy_margin: float = MIN_ACCURACY_MARGIN,
    min_stability_fraction: float = MIN_STABILITY_FRACTION,
) -> DecisionResult:
    oracle_meaningful = oracle_headroom_mean >= meaningful_threshold
    conditions = {"pre_repair_features_only": True}

    if predictor_status != "EVALUATED":
        conditions.update(
            {
                "survives_grouped_validation": False,
                "policy_beats_never_repair": False,
                "stable_across_subgroups": False,
                "practically_meaningful": False,
            }
        )
        best_name, best_acc, policy_ndcg = "", float("nan"), float("nan")
    else:
        best_name, best_acc = best_real_model(models)
        majority_acc = models["majority_class"]["mean_balanced_accuracy"]
        control_accs = [
            models[k]["mean_balanced_accuracy"] for k in models if k.startswith("control_")
        ]
        best_control = max(control_accs) if control_accs else 0.5
        survives_validation = (
            best_acc - majority_acc >= min_accuracy_margin
            and best_acc - best_control >= min_accuracy_margin
        )
        policy_ndcg = models[best_name]["policy_mean_ndcg"] if best_name else float("nan")
        practically_meaningful = (policy_ndcg - never_repair_ndcg) >= meaningful_threshold
        conditions.update(
            {
                "survives_grouped_validation": bool(survives_validation),
                "policy_beats_never_repair": bool(policy_ndcg > never_repair_ndcg),
                "stable_across_subgroups": bool(stability_pass_fraction >= min_stability_fraction),
                "practically_meaningful": bool(practically_meaningful),
            }
        )

    if all(conditions.values()):
        return DecisionResult(
            "STABLE_REPAIR_REGIME_FOUND",
            f"Predictor '{best_name}' (grouped-CV balanced accuracy {best_acc:.3f}), built from "
            f"pre-repair features alone, survives grouped validation; its induced policy nDCG "
            f"({policy_ndcg:.5f}) beats never-repair ({never_repair_ndcg:.5f}) by a practically "
            f"meaningful margin, holding across {stability_pass_fraction:.0%} of major subgroups.",
            conditions,
            best_name,
            best_acc,
            policy_ndcg,
        )

    weak_signal = predictor_status == "EVALUATED" and (
        best_acc > models["majority_class"]["mean_balanced_accuracy"]
    )
    if oracle_meaningful and weak_signal:
        return DecisionResult(
            "WEAK_DESCRIPTIVE_PATTERN_ONLY",
            f"Oracle headroom is meaningful ({oracle_headroom_mean:.5f}) and the best predictor "
            f"shows some above-majority skill ({best_acc:.3f} vs "
            f"{models['majority_class']['mean_balanced_accuracy']:.3f}), but it does not clear "
            "the full deployability bar (validation margin, policy improvement, subgroup "
            "stability, and/or practical significance) -- a descriptive pattern exists but is "
            "not yet a deployable regime.",
            conditions,
            best_name,
            best_acc,
            policy_ndcg,
        )

    if oracle_meaningful:
        return DecisionResult(
            "ORACLE_ONLY_NOT_PREDICTABLE",
            f"Oracle headroom is meaningful ({oracle_headroom_mean:.5f}, gate decision "
            f"'{headroom_gate_decision}') -- repair genuinely helps on some queries -- but no "
            "evaluated predictor (single-feature threshold, shallow tree, or regularized "
            "logistic regression) shows above-chance skill from pre-repair features alone: the "
            "benefit exists but is not identifiable in advance.",
            conditions,
            best_name,
            best_acc,
            policy_ndcg,
        )

    return DecisionResult(
        "NO_IDENTIFIABLE_REPAIR_REGIME",
        f"Oracle headroom ({oracle_headroom_mean:.5f}, gate decision '{headroom_gate_decision}') "
        f"does not clear the {meaningful_threshold} threshold at all -- there is no repair "
        "benefit to identify a regime for, predictable or not.",
        conditions,
        best_name,
        best_acc,
        policy_ndcg,
    )


__all__ = ["Decision", "DecisionResult", "MEANINGFUL_THRESHOLD", "best_real_model", "decide"]
