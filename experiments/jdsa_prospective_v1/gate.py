"""Evaluate prespecified instrument criteria, never retrieval utility."""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from .common import GATE_THRESHOLDS, paired_disposition


def gate_report(records, manifest, runtime, charged_s):
    from consistency_ranker.statistical_inference import proportion_interval

    def rate(k, n):
        interval = proportion_interval(k, n)
        return {
            "numerator": k,
            "denominator": n,
            "rate": k / n if n else None,
            "wilson95": [interval.lower, interval.upper],
        }

    checks, variants = {}, {}
    initial = [r for r in records if not r["uid"].startswith("control:") and not r["repeat"]]
    by_variant = {}
    for variant in ("primary", "robustness"):
        rows = [r for r in initial if r["variant"] == variant]
        directional = [r for r in rows if r["status"] == "valid"]
        pairs = defaultdict(list)
        for row in rows:
            pairs[(row["uid"], tuple(row["pair"]))].append(row)
        both_valid = [
            p for p in pairs.values() if len(p) == 2 and all(r["status"] == "valid" for r in p)
        ]
        corroborated = sum(paired_disposition(p)[0] == "corroborated" for p in pairs.values())
        data = {
            "valid": rate(len(directional), 96),
            "abstention": rate(sum(r["status"] == "abstention" for r in rows), 96),
            "displayed_a": rate(sum(r["label"] == "A" for r in directional), len(directional)),
            "reversal_agreement": rate(corroborated, len(both_valid)),
            "usable_pairs": rate(corroborated, 48),
        }
        variants[variant] = data
        by_variant[variant] = {(r["uid"], tuple(r["pair"]), r["orientation"]): r for r in rows}
        t = GATE_THRESHOLDS
        checks[variant + "_complete"] = len(rows) == 96 and len(pairs) == 48
        checks[variant + "_valid"] = data["valid"]["rate"] >= t["valid_fraction_min"]
        checks[variant + "_abstention"] = data["abstention"]["rate"] <= t["abstention_fraction_max"]
        a = data["displayed_a"]["rate"]
        checks[variant + "_position"] = (
            a is not None and t["displayed_a_fraction_min"] <= a <= t["displayed_a_fraction_max"]
        )
        reversal = data["reversal_agreement"]["rate"]
        checks[variant + "_reversal"] = (
            reversal is not None and reversal >= t["reversal_agreement_min"]
        )
        checks[variant + "_usable"] = data["usable_pairs"]["rate"] >= t["usable_pair_fraction_min"]
    repeats = [r for r in records if r["repeat"]]
    repeat_agree = 0
    for r in repeats:
        old = by_variant["primary"].get((r["uid"], tuple(r["pair"]), r["orientation"]))
        repeat_agree += bool(
            old and r["status"] == old["status"] == "valid" and r["raw"] == old["raw"]
        )
    repeat_data = rate(repeat_agree, 24)
    checks["repeat_complete"] = len(repeats) == 24
    checks["repeatability"] = repeat_data["rate"] >= GATE_THRESHOLDS["repeat_agreement_min"]
    agreement = sum(
        key in by_variant["robustness"]
        and row["status"] == "valid"
        and by_variant["robustness"][key]["status"] == "valid"
        and row["winner"] == by_variant["robustness"][key]["winner"]
        for key, row in by_variant["primary"].items()
    )
    robustness = rate(agreement, 96)
    checks["prompt_robustness"] = (
        robustness["rate"] >= GATE_THRESHOLDS["prompt_winner_agreement_min"]
    )
    controls = [r for r in records if r["uid"].startswith("control:")]
    control_data = {}
    for orientation in (0, 1):
        selected = [r for r in controls if r["orientation"] == orientation]
        correct = sum(r["status"] == "valid" and r["winner"] == "relevant" for r in selected)
        control_data[str(orientation)] = rate(correct, 12)
        checks[f"semantic_control_{orientation}"] = (
            len(selected) == 12 and correct / 12 >= GATE_THRESHOLDS["semantic_control_accuracy_min"]
        )
    timings = [r["latency_s"] for r in records if not r["uid"].startswith("control:")]
    estimate = None
    if timings:
        conservative = max(float(np.mean(timings)), float(np.quantile(timings, 0.90))) * 1.5
        estimate = conservative * manifest["main_responses"] + manifest["analysis_reserve_s"]
    checks["resource_runtime"] = (
        estimate is not None and estimate + charged_s <= manifest["max_active_wall_s"]
    )
    checks["gpu_memory"] = (
        runtime["gpu_peak_allocated_bytes"] / runtime["gpu_total_bytes"]
        <= GATE_THRESHOLDS["gpu_peak_fraction_max"]
    )
    checks["development_count"] = len(records) == 240
    return {
        "gate_pass": all(checks.values()),
        "checks": checks,
        "failed_checks": [k for k, passed in checks.items() if not passed],
        "variants": variants,
        "repeatability": repeat_data,
        "prompt_robustness": robustness,
        "semantic_controls": control_data,
        "observed_responses": len(records),
        "evaluation_queries_used": 0,
        "retrieval_utility_computed": False,
        "estimated_remaining_wall_s_with_1_5x_allowance": estimate,
        "latency_mean_s": float(np.mean(timings)) if timings else None,
        "latency_p90_s": float(np.quantile(timings, 0.90)) if timings else None,
        "runtime": runtime,
        "thresholds": GATE_THRESHOLDS,
        "interpretation": "Finite development screen, not a population reliability guarantee",
    }
