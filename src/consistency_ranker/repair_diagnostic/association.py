"""Descriptive/associational analysis: which pre- and post-repair features
associate with repair outcome, with multiple-testing correction and
subgroup stability checks.

Reuses :func:`consistency_ranker.statistical_inference.holm_adjust` for
family-wise multiple-testing correction (the same correction used
throughout this repository's other experiment scripts) and
:func:`consistency_ranker.statistical_inference.bootstrap_mean_interval`
for effect-size uncertainty on the overall delta.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from consistency_ranker.statistical_inference import (
    BootstrapIntervalResult,
    bootstrap_mean_interval,
    holm_adjust,
)

from .features import POST_REPAIR_FEATURE_NAMES, PRE_REPAIR_FEATURE_NAMES
from .outcomes import QueryGraphDiagnostic

ALL_FEATURE_NAMES = [(n, "pre_repair") for n in PRE_REPAIR_FEATURE_NAMES] + [
    (n, "post_repair") for n in POST_REPAIR_FEATURE_NAMES
]


def _feature_value(d: QueryGraphDiagnostic, name: str) -> float:
    if name in PRE_REPAIR_FEATURE_NAMES:
        row = d.pre_repair.as_numeric_row()
    else:
        row = {k: float(v) for k, v in d.post_repair.to_dict().items()}
    return row[name]


def outcome_group_stats(results: list[QueryGraphDiagnostic]) -> dict:
    """Requirement 4: descriptive comparisons for improved/harmed/unchanged cases."""
    groups: dict[str, list[QueryGraphDiagnostic]] = defaultdict(list)
    for d in results:
        groups[d.outcome].append(d)
    out = {}
    for outcome in ("improves", "harms", "no_change"):
        members = groups.get(outcome, [])
        deltas = [m.delta for m in members]
        preserve_vals = [m.ndcg_preserve for m in members]
        repair_vals = [m.ndcg_repair for m in members]
        out[outcome] = {
            "n": len(members),
            "mean_delta": float(np.mean(deltas)) if deltas else 0.0,
            "mean_ndcg_preserve": float(np.mean(preserve_vals)) if preserve_vals else 0.0,
            "mean_ndcg_repair": float(np.mean(repair_vals)) if repair_vals else 0.0,
        }
    return out


def overall_delta_ci(results: list[QueryGraphDiagnostic]) -> BootstrapIntervalResult:
    deltas = [d.delta for d in results]
    return bootstrap_mean_interval(deltas) if deltas else bootstrap_mean_interval([])


@dataclass(frozen=True)
class FeatureAssociation:
    feature: str
    family: str
    correlation: float
    pvalue_raw: float
    pvalue_holm: float | None
    n: int

    def to_dict(self) -> dict:
        return {
            "feature": self.feature,
            "family": self.family,
            "correlation": self.correlation,
            "pvalue_raw": self.pvalue_raw,
            "pvalue_holm": self.pvalue_holm,
            "n": self.n,
        }


def _permutation_correlation_pvalue(
    x: np.ndarray, y: np.ndarray, *, reps: int = 10_000, seed: int = 23
) -> tuple[float, float]:
    """Two-sided permutation test for the Pearson correlation between *x*
    and *y* -- simple and nonparametric, appropriate for small-n, heavily-
    tied delta distributions where a parametric correlation p-value would
    be unreliable."""
    if np.std(x) < 1e-12 or np.std(y) < 1e-12:
        return 0.0, 1.0
    observed = float(np.corrcoef(x, y)[0, 1])
    rng = np.random.default_rng(seed)
    count = 0
    for _ in range(reps):
        perm_y = rng.permutation(y)
        r = np.corrcoef(x, perm_y)[0, 1]
        if abs(r) >= abs(observed) - 1e-12:
            count += 1
    pvalue = (count + 1) / (reps + 1)
    return observed, float(pvalue)


def compute_feature_associations(
    results: list[QueryGraphDiagnostic], *, reps: int = 10_000, seed: int = 23
) -> list[FeatureAssociation]:
    """Requirement 2/4: effect size (Pearson r) + Holm-adjusted permutation
    significance for every candidate feature, pre- and post-repair (clearly
    tagged by family so the caller never conflates the two)."""
    deltas = np.array([d.delta for d in results])
    prelim = []
    raw_pvalues = []
    for name, family in ALL_FEATURE_NAMES:
        x = np.array([_feature_value(d, name) for d in results])
        r, p = _permutation_correlation_pvalue(x, deltas, reps=reps, seed=seed)
        prelim.append((name, family, r, p))
        raw_pvalues.append(p)
    holm_ps = holm_adjust(raw_pvalues)
    n = len(results)
    return [
        FeatureAssociation(
            feature=name, family=family, correlation=r, pvalue_raw=p, pvalue_holm=hp, n=n
        )
        for (name, family, r, p), hp in zip(prelim, holm_ps)
    ]


def feature_stability_by_subgroup(
    results: list[QueryGraphDiagnostic], feature_name: str, *, key_fn
) -> dict:
    """Whether a feature's correlation with delta is consistent in SIGN
    across major subgroups (dataset/provider/pool_size) -- a feature whose
    correlation flips sign across subgroups is not a stable regime signal."""
    groups: dict = defaultdict(list)
    for d in results:
        groups[key_fn(d)].append(d)
    out = {}
    for k, members in groups.items():
        if len(members) < 4:
            out[str(k)] = {
                "n": len(members),
                "correlation": None,
                "note": "too few for correlation",
            }
            continue
        x = np.array([_feature_value(m, feature_name) for m in members])
        y = np.array([m.delta for m in members])
        if np.std(x) < 1e-12 or np.std(y) < 1e-12:
            out[str(k)] = {"n": len(members), "correlation": None, "note": "no variance"}
            continue
        out[str(k)] = {"n": len(members), "correlation": float(np.corrcoef(x, y)[0, 1])}
    return out


def full_stability_report(results: list[QueryGraphDiagnostic], feature_names: list[str]) -> dict:
    """Requirement 4: feature stability across datasets, providers, pool sizes."""
    report = {}
    for name in feature_names:
        report[name] = {
            "by_dataset": feature_stability_by_subgroup(
                results, name, key_fn=lambda d: d.dataset
            ),
            "by_provider": feature_stability_by_subgroup(
                results, name, key_fn=lambda d: d.provider
            ),
            "by_pool_size": feature_stability_by_subgroup(
                results, name, key_fn=lambda d: d.pool_size
            ),
        }
    return report


def outlier_sensitivity(results: list[QueryGraphDiagnostic], *, drop_top_n: int = 1) -> dict:
    """Requirement 4: outlier sensitivity of the overall mean delta."""
    deltas = sorted((d.delta for d in results), reverse=True)
    if not deltas:
        return {
            "mean_delta_full": 0.0,
            "mean_delta_excluding_top_n": None,
            "drop_top_n": drop_top_n,
        }
    full_mean = float(np.mean(deltas))
    if len(deltas) <= drop_top_n:
        return {
            "mean_delta_full": full_mean,
            "mean_delta_excluding_top_n": None,
            "drop_top_n": drop_top_n,
        }
    excl_mean = float(np.mean(deltas[drop_top_n:]))
    frac = ((full_mean - excl_mean) / full_mean) if abs(full_mean) > 1e-12 else None
    return {
        "mean_delta_full": full_mean,
        "mean_delta_excluding_top_n": excl_mean,
        "drop_top_n": drop_top_n,
        "fraction_of_mean_from_top_n": frac,
    }


__all__ = [
    "ALL_FEATURE_NAMES",
    "outcome_group_stats",
    "overall_delta_ci",
    "FeatureAssociation",
    "compute_feature_associations",
    "feature_stability_by_subgroup",
    "full_stability_report",
    "outlier_sensitivity",
]
