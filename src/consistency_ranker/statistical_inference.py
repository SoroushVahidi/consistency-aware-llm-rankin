"""Reusable paired-inference helpers for revision-time manuscript audits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
from scipy.stats import beta as beta_dist
from scipy.stats import norm
from scipy.stats import t as student_t

_ZERO_TOL = 1.0e-15


@dataclass(frozen=True)
class SignFlipResult:
    pvalue: float | None
    method: str
    n: int
    nonzero_count: int
    observed_mean: float | None
    reps: int | None
    seed: int | None


@dataclass(frozen=True)
class BootstrapIntervalResult:
    method: str
    lower: float | None
    upper: float | None
    frac_gt_zero: float | None
    reps: int
    seed: int


@dataclass(frozen=True)
class ProportionIntervalResult:
    method: str
    successes: int
    n: int
    proportion: float | None
    lower: float | None
    upper: float | None
    confidence: float


@dataclass(frozen=True)
class MDEResult:
    power_target: float
    detected_shift: float | None
    achieved_power: float | None
    alpha: float
    test_method: str
    simulation_reps: int
    test_reps: int
    seed: int


@dataclass(frozen=True)
class EquivalenceResult:
    margin: float
    pvalue: float | None
    ci90_low: float | None
    ci90_high: float | None
    equivalent: bool
    n: int
    mean_delta: float | None
    se_delta: float | None


def _as_float_array(values: Iterable[float]) -> np.ndarray:
    arr = np.asarray(list(values), dtype=float)
    if arr.ndim != 1:
        raise ValueError("Expected a one-dimensional sequence of values.")
    return arr


def _nonzero_mask(arr: np.ndarray, tol: float = _ZERO_TOL) -> np.ndarray:
    return np.abs(arr) > tol


def delta_summary(values: Iterable[float]) -> dict[str, float | int | None]:
    arr = _as_float_array(values)
    if arr.size == 0:
        return {
            "n": 0,
            "nonzero_count": 0,
            "nonzero_fraction": None,
            "mean": None,
            "median": None,
            "std": None,
            "se": None,
            "observed_standardized_effect": None,
            "q05": None,
            "q25": None,
            "q75": None,
            "q95": None,
        }
    nonzero = int(np.count_nonzero(_nonzero_mask(arr)))
    std = float(arr.std(ddof=1)) if arr.size > 1 else 0.0
    se = float(std / np.sqrt(arr.size)) if arr.size > 0 else None
    return {
        "n": int(arr.size),
        "nonzero_count": nonzero,
        "nonzero_fraction": float(nonzero / arr.size),
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "std": std,
        "se": se,
        "observed_standardized_effect": (float(arr.mean() / std) if std > _ZERO_TOL else None),
        "q05": float(np.quantile(arr, 0.05)),
        "q25": float(np.quantile(arr, 0.25)),
        "q75": float(np.quantile(arr, 0.75)),
        "q95": float(np.quantile(arr, 0.95)),
    }


def exact_sign_flip_pvalue(
    deltas: Sequence[float],
    *,
    block_size: int = 65536,
) -> SignFlipResult:
    arr = _as_float_array(deltas)
    if arr.size == 0:
        return SignFlipResult(
            pvalue=None,
            method="exact_sign_flip",
            n=0,
            nonzero_count=0,
            observed_mean=None,
            reps=0,
            seed=None,
        )
    mask = _nonzero_mask(arr)
    nonzero = np.abs(arr[mask])
    if nonzero.size == 0:
        return SignFlipResult(
            pvalue=1.0,
            method="exact_sign_flip",
            n=int(arr.size),
            nonzero_count=0,
            observed_mean=float(arr.mean()),
            reps=1,
            seed=None,
        )
    total_sign_patterns = 1 << int(nonzero.size)
    observed = abs(float(arr.mean()))
    thresholds = 0
    feature_ids = np.arange(nonzero.size, dtype=np.uint64)
    for start in range(0, total_sign_patterns, block_size):
        stop = min(total_sign_patterns, start + block_size)
        states = np.arange(start, stop, dtype=np.uint64)[:, None]
        bits = (states >> feature_ids) & 1
        signs = np.where(bits == 0, -1.0, 1.0)
        means = np.abs(signs @ nonzero / float(arr.size))
        thresholds += int(np.count_nonzero(means >= observed - _ZERO_TOL))
    pvalue = float(thresholds / total_sign_patterns)
    return SignFlipResult(
        pvalue=pvalue,
        method="exact_sign_flip",
        n=int(arr.size),
        nonzero_count=int(nonzero.size),
        observed_mean=float(arr.mean()),
        reps=total_sign_patterns,
        seed=None,
    )


def monte_carlo_sign_flip_pvalue(
    deltas: Sequence[float],
    *,
    reps: int = 10_000,
    seed: int = 17,
) -> SignFlipResult:
    arr = _as_float_array(deltas)
    if arr.size == 0:
        return SignFlipResult(
            pvalue=None,
            method="monte_carlo_sign_flip",
            n=0,
            nonzero_count=0,
            observed_mean=None,
            reps=reps,
            seed=seed,
        )
    observed = abs(float(arr.mean()))
    rng = np.random.default_rng(seed)
    flips = rng.choice(np.array([-1.0, 1.0]), size=(reps, arr.size), replace=True)
    perm_means = np.abs((flips * arr).mean(axis=1))
    pvalue = float((np.count_nonzero(perm_means >= observed - _ZERO_TOL) + 1) / (reps + 1))
    return SignFlipResult(
        pvalue=pvalue,
        method="monte_carlo_sign_flip",
        n=int(arr.size),
        nonzero_count=int(np.count_nonzero(_nonzero_mask(arr))),
        observed_mean=float(arr.mean()),
        reps=reps,
        seed=seed,
    )


def sign_flip_pvalue(
    deltas: Sequence[float],
    *,
    exact_max_nonzero: int = 20,
    reps: int = 10_000,
    seed: int = 17,
) -> SignFlipResult:
    arr = _as_float_array(deltas)
    nonzero_count = int(np.count_nonzero(_nonzero_mask(arr)))
    if nonzero_count <= exact_max_nonzero:
        return exact_sign_flip_pvalue(arr)
    return monte_carlo_sign_flip_pvalue(arr, reps=reps, seed=seed)


def _bootstrap_means(
    arr: np.ndarray,
    *,
    reps: int,
    seed: int,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    samples = rng.choice(arr, size=(reps, arr.size), replace=True)
    return samples.mean(axis=1)


def _bootstrap_mean_samples(
    arr: np.ndarray,
    *,
    reps: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    samples = rng.choice(arr, size=(reps, arr.size), replace=True)
    return samples, samples.mean(axis=1)


def bootstrap_mean_interval(
    values: Sequence[float],
    *,
    method: str = "percentile",
    reps: int = 10_000,
    seed: int = 13,
) -> BootstrapIntervalResult:
    arr = _as_float_array(values)
    if arr.size == 0:
        return BootstrapIntervalResult(
            method=method, lower=None, upper=None, frac_gt_zero=None, reps=reps, seed=seed
        )
    theta_hat = float(arr.mean())
    samples, boot_means = _bootstrap_mean_samples(arr, reps=reps, seed=seed)
    frac_gt_zero = float(np.mean(boot_means > 0.0))
    alpha_lo = 0.025
    alpha_hi = 0.975

    if method == "percentile":
        lo, hi = np.quantile(boot_means, [alpha_lo, alpha_hi])
    elif method == "basic":
        q_lo, q_hi = np.quantile(boot_means, [alpha_lo, alpha_hi])
        lo, hi = (2 * theta_hat - q_hi), (2 * theta_hat - q_lo)
    elif method == "bca":
        proportion_less = np.mean(boot_means < theta_hat)
        proportion_less = float(np.clip(proportion_less, 1.0 / (2 * reps), 1.0 - 1.0 / (2 * reps)))
        z0 = float(norm.ppf(proportion_less))
        if arr.size < 2:
            accel = 0.0
        else:
            jackknife = np.array(
                [
                    np.delete(arr, idx).mean() if arr.size > 1 else theta_hat
                    for idx in range(arr.size)
                ],
                dtype=float,
            )
            jack_mean = float(jackknife.mean())
            centered = jack_mean - jackknife
            denom = np.sum(centered**2)
            accel = float(np.sum(centered**3) / (6.0 * denom**1.5)) if denom > _ZERO_TOL else 0.0

        def _adjust(alpha: float) -> float:
            z = float(norm.ppf(alpha))
            numer = z0 + z
            denom = 1.0 - accel * numer
            if abs(denom) <= _ZERO_TOL:
                return alpha
            return float(norm.cdf(z0 + numer / denom))

        adj_lo = np.clip(_adjust(alpha_lo), 0.0, 1.0)
        adj_hi = np.clip(_adjust(alpha_hi), 0.0, 1.0)
        lo, hi = np.quantile(boot_means, [adj_lo, adj_hi])
    elif method == "studentized":
        orig_se = float(arr.std(ddof=1) / np.sqrt(arr.size)) if arr.size > 1 else 0.0
        if orig_se <= _ZERO_TOL:
            lo, hi = theta_hat, theta_hat
        else:
            boot_se = samples.std(axis=1, ddof=1) / np.sqrt(arr.size)
            valid = boot_se > _ZERO_TOL
            if not np.any(valid):
                lo, hi = theta_hat, theta_hat
            else:
                t_stats = (boot_means[valid] - theta_hat) / boot_se[valid]
                q_lo, q_hi = np.quantile(t_stats, [alpha_lo, alpha_hi])
                lo = theta_hat - q_hi * orig_se
                hi = theta_hat - q_lo * orig_se
    else:
        raise ValueError(f"Unsupported bootstrap interval method: {method}")

    return BootstrapIntervalResult(
        method=method,
        lower=float(lo),
        upper=float(hi),
        frac_gt_zero=frac_gt_zero,
        reps=reps,
        seed=seed,
    )


def proportion_interval(
    successes: int,
    n: int,
    *,
    method: str = "wilson",
    confidence: float = 0.95,
) -> ProportionIntervalResult:
    """Confidence interval for a single binomial proportion ``successes / n``.

    Centralized replacement for using ``bootstrap_mean_interval`` on a 0/1
    indicator vector to estimate a rate (e.g. a severe-harm rate or a
    stopped/capped rate). A nonparametric bootstrap of an all-zero or
    all-one sample is degenerate -- every resample is identical to the
    original, so the resulting interval collapses to a single point
    (``[0, 0]`` or ``[1, 1]``) regardless of the true sample size. That
    understates uncertainty precisely in the cases (0 events, or all
    events) where the interval matters most. Wilson and Clopper-Pearson
    intervals both have nonzero width away from the true 0/1 bounds even
    when the observed count is exactly 0 or exactly ``n``.

    Use this for a single group's rate (e.g. "35 severe-harm events out of
    350 walks"). It is not the right tool for the *difference* of two
    paired/correlated proportions (e.g. a per-query paired reduction in
    harm rate between two methods) -- that remains a bootstrap or
    permutation problem over the paired difference vector, handled by
    :func:`bootstrap_mean_interval` / :func:`sign_flip_pvalue`.
    """
    if n < 0 or successes < 0 or successes > n:
        raise ValueError(f"Invalid proportion inputs: successes={successes}, n={n}")
    if not 0.0 < confidence < 1.0:
        raise ValueError(f"confidence must be in (0, 1): got {confidence}")
    if n == 0:
        return ProportionIntervalResult(
            method=method, successes=successes, n=0, proportion=None,
            lower=None, upper=None, confidence=confidence,
        )

    p_hat = successes / n
    alpha = 1.0 - confidence

    if method == "wilson":
        z = float(norm.ppf(1.0 - alpha / 2.0))
        denom = 1.0 + z**2 / n
        center = (p_hat + z**2 / (2 * n)) / denom
        half_width = (z / denom) * np.sqrt(p_hat * (1.0 - p_hat) / n + z**2 / (4 * n**2))
        lower = max(0.0, center - half_width)
        upper = min(1.0, center + half_width)
    elif method == "clopper_pearson":
        if successes == 0:
            lower = 0.0
        else:
            lower = float(beta_dist.ppf(alpha / 2.0, successes, n - successes + 1))
        if successes == n:
            upper = 1.0
        else:
            upper = float(beta_dist.ppf(1.0 - alpha / 2.0, successes + 1, n - successes))
    else:
        raise ValueError(f"Unsupported proportion interval method: {method}")

    return ProportionIntervalResult(
        method=method,
        successes=int(successes),
        n=int(n),
        proportion=float(p_hat),
        lower=float(lower),
        upper=float(upper),
        confidence=confidence,
    )


def holm_adjust(pvalues: Sequence[float | None]) -> list[float | None]:
    pvals = list(pvalues)
    indexed = [(idx, float(p)) for idx, p in enumerate(pvals) if p is not None]
    adjusted: list[float | None] = [None] * len(pvals)
    if not indexed:
        return adjusted
    indexed.sort(key=lambda item: item[1])
    running = 0.0
    total = len(indexed)
    for rank, (idx, pval) in enumerate(indexed, start=1):
        scaled = (total - rank + 1) * pval
        running = max(running, scaled)
        adjusted[idx] = min(1.0, running)
    return adjusted


def bh_adjust(pvalues: Sequence[float | None]) -> list[float | None]:
    pvals = list(pvalues)
    indexed = [(idx, float(p)) for idx, p in enumerate(pvals) if p is not None]
    adjusted: list[float | None] = [None] * len(pvals)
    if not indexed:
        return adjusted
    indexed.sort(key=lambda item: item[1], reverse=True)
    total = len(indexed)
    running = 1.0
    for rev_rank, (idx, pval) in enumerate(indexed, start=1):
        rank = total - rev_rank + 1
        scaled = pval * total / rank
        running = min(running, scaled)
        adjusted[idx] = min(1.0, running)
    return adjusted


def by_adjust(pvalues: Sequence[float | None]) -> list[float | None]:
    pvals = list(pvalues)
    indexed = [(idx, float(p)) for idx, p in enumerate(pvals) if p is not None]
    adjusted: list[float | None] = [None] * len(pvals)
    if not indexed:
        return adjusted
    total = len(indexed)
    harmonic = float(np.sum(1.0 / np.arange(1, total + 1, dtype=float)))
    indexed.sort(key=lambda item: item[1], reverse=True)
    running = 1.0
    for rev_rank, (idx, pval) in enumerate(indexed, start=1):
        rank = total - rev_rank + 1
        scaled = pval * total * harmonic / rank
        running = min(running, scaled)
        adjusted[idx] = min(1.0, running)
    return adjusted


def minimum_detectable_effect_normal(
    *,
    n: int,
    sd: float,
    alpha: float,
    power: float,
) -> float | None:
    if n <= 0 or sd <= _ZERO_TOL:
        return None
    alpha = float(np.clip(alpha, _ZERO_TOL, 1.0 - _ZERO_TOL))
    power = float(np.clip(power, _ZERO_TOL, 1.0 - _ZERO_TOL))
    z_alpha = float(norm.ppf(1.0 - alpha / 2.0))
    z_power = float(norm.ppf(power))
    return float((z_alpha + z_power) * sd / np.sqrt(n))


def _shifted_resample(
    arr: np.ndarray,
    *,
    shift: float,
    rng: np.random.Generator,
) -> np.ndarray:
    sample = rng.choice(arr, size=arr.size, replace=True)
    shifted = sample.copy()
    shifted[_nonzero_mask(shifted)] += shift
    return shifted


def simulate_mde(
    deltas: Sequence[float],
    *,
    alpha: float,
    power_target: float,
    shift_grid: Sequence[float],
    simulation_reps: int = 400,
    test_reps: int = 4096,
    seed: int = 101,
    exact_max_nonzero: int = 18,
) -> MDEResult:
    arr = _as_float_array(deltas)
    if arr.size == 0 or np.count_nonzero(_nonzero_mask(arr)) == 0:
        return MDEResult(
            power_target=power_target,
            detected_shift=None,
            achieved_power=None,
            alpha=alpha,
            test_method="sign_flip",
            simulation_reps=simulation_reps,
            test_reps=test_reps,
            seed=seed,
        )

    rng = np.random.default_rng(seed)
    sorted_grid = [float(value) for value in shift_grid]
    for shift in sorted_grid:
        rejects = 0
        for rep in range(simulation_reps):
            simulated = _shifted_resample(arr, shift=shift, rng=rng)
            result = sign_flip_pvalue(
                simulated,
                exact_max_nonzero=exact_max_nonzero,
                reps=test_reps,
                seed=seed + rep + int(round(shift * 1_000_000)),
            )
            if result.pvalue is not None and result.pvalue <= alpha:
                rejects += 1
        achieved_power = rejects / simulation_reps
        if achieved_power >= power_target:
            return MDEResult(
                power_target=power_target,
                detected_shift=shift,
                achieved_power=float(achieved_power),
                alpha=alpha,
                test_method="sign_flip",
                simulation_reps=simulation_reps,
                test_reps=test_reps,
                seed=seed,
            )
    return MDEResult(
        power_target=power_target,
        detected_shift=None,
        achieved_power=float(achieved_power),
        alpha=alpha,
        test_method="sign_flip",
        simulation_reps=simulation_reps,
        test_reps=test_reps,
        seed=seed,
    )


def paired_tost(
    deltas: Sequence[float],
    *,
    margin: float,
    alpha: float = 0.05,
) -> EquivalenceResult:
    arr = _as_float_array(deltas)
    if arr.size == 0:
        return EquivalenceResult(
            margin=margin,
            pvalue=None,
            ci90_low=None,
            ci90_high=None,
            equivalent=False,
            n=0,
            mean_delta=None,
            se_delta=None,
        )

    mean_delta = float(arr.mean())
    if arr.size == 1:
        se = None
        ci90_low = mean_delta
        ci90_high = mean_delta
        equivalent = -margin <= mean_delta <= margin
        pvalue = 0.0 if equivalent else 1.0
        return EquivalenceResult(
            margin=margin,
            pvalue=pvalue,
            ci90_low=ci90_low,
            ci90_high=ci90_high,
            equivalent=equivalent,
            n=1,
            mean_delta=mean_delta,
            se_delta=se,
        )

    sd = float(arr.std(ddof=1))
    se = float(sd / np.sqrt(arr.size))
    df = arr.size - 1
    t_crit = float(student_t.ppf(1.0 - alpha, df))
    ci90_low = mean_delta - t_crit * se
    ci90_high = mean_delta + t_crit * se

    if se <= _ZERO_TOL:
        equivalent = -margin <= mean_delta <= margin
        pvalue = 0.0 if equivalent else 1.0
        return EquivalenceResult(
            margin=margin,
            pvalue=pvalue,
            ci90_low=ci90_low,
            ci90_high=ci90_high,
            equivalent=equivalent,
            n=int(arr.size),
            mean_delta=mean_delta,
            se_delta=se,
        )

    t_lower = (mean_delta + margin) / se
    t_upper = (mean_delta - margin) / se
    p_lower = 1.0 - float(student_t.cdf(t_lower, df))
    p_upper = float(student_t.cdf(t_upper, df))
    pvalue = max(p_lower, p_upper)
    equivalent = (p_lower <= alpha) and (p_upper <= alpha)
    return EquivalenceResult(
        margin=margin,
        pvalue=float(pvalue),
        ci90_low=float(ci90_low),
        ci90_high=float(ci90_high),
        equivalent=bool(equivalent),
        n=int(arr.size),
        mean_delta=mean_delta,
        se_delta=se,
    )


# ---------------------------------------------------------------------------
# Adjusted-p-value significance helper
#
# Added 2026-07-30 (repo hygiene Stage 1,
# reports/repo_cleanup_stage1_20260730T004010Z/) to centralize and guard
# against a bug caught while building reports/ir_evidence_audit_20260729T182949Z/:
# `pool_cutoff_statistics.csv`'s `holm_active_ms1_family` column is a
# Holm-adjusted p-value (float, NaN outside the active family), despite its
# boolean-sounding name. Comparing it with `series == True` silently matches
# rows where the p-value happens to equal exactly 1.0 (pandas casts
# `True` -> `1.0`) -- the OPPOSITE of "significant" -- which produced a
# spurious "24/216 Holm-significant" result before it was caught. This
# helper makes that specific misuse raise loudly instead of silently
# returning a wrong mask.
#
# This is deliberately NOT applied to genuinely boolean columns such as
# `holm_significant_at_0.05` in `exact_larger_pool_family_statistics.csv` /
# `baseline_targeted_tests_primary_canonical.csv` (verified `dtype == bool`
# there) -- for those, indexing with the column directly (or `== True`) is
# correct; this helper exists for the float-disguised-as-boolean case only,
# and rejects real boolean input specifically so the two cases can never be
# confused for one another.
# ---------------------------------------------------------------------------


def is_significant_pvalue(values: Any, alpha: float = 0.05) -> pd.Series:
    """Return a boolean mask of which (adjusted) p-values are < ``alpha``.

    Treats missing values (``NaN``, ``None``, ``pd.NA``) as not-significant
    rather than raising or silently matching. Raises ``TypeError`` if
    ``values`` is boolean-typed (plain ``bool``, NumPy ``bool_``, or
    pandas' nullable ``BooleanDtype``) -- a real p-value series should never
    be boolean-typed, and the historical bug this helper guards against is
    exactly a float p-value column being mistaken for (or compared as if it
    were) a boolean column. Raises ``ValueError``/``TypeError`` via
    ``pandas.to_numeric(..., errors="raise")`` on genuinely non-numeric
    input (e.g. the strings ``"True"``/``"yes"``) rather than silently
    coercing it.
    """
    s = values if isinstance(values, pd.Series) else pd.Series(values)
    if isinstance(s.dtype, pd.BooleanDtype) or s.dtype == bool:
        raise TypeError(
            "is_significant_pvalue() expects a numeric (adjusted) p-value "
            f"series, but received boolean dtype {s.dtype!r}. This is exactly "
            "the historical bug this helper guards against: a float p-value "
            "column that happens to contain the value 1.0 would silently "
            "match `series == True` (pandas casts True -> 1.0), which is the "
            "OPPOSITE of significant. If this series is genuinely a "
            "precomputed significance flag (e.g. a column already named "
            "`holm_significant_at_<alpha>` with real bool dtype), use it "
            "directly instead of calling this helper."
        )
    numeric = pd.to_numeric(s, errors="raise")
    return numeric.notna() & (numeric < alpha)


def parse_numeric_threshold(value: Any) -> float:
    """Parse ``value`` (a float, int, or numeric string) into a plain float.

    Added alongside :func:`is_significant_pvalue` to centralize numeric
    threshold parsing (e.g. an alpha/significance cutoff read from a config
    file or CLI argument) after a second, unrelated bug was caught in the
    same audit: ``df.holm_significant_at_0.05`` parses as the attribute
    access ``df.holm_significant_at_0`` followed by the float literal
    ``.05`` -- a ``SyntaxError`` at parse time, not a silent runtime bug,
    but a trap for any column name containing a literal ``.`` (always use
    bracket indexing, ``df["holm_significant_at_0.05"]``, for such columns).

    Accepts standard Python float literals/strings, including a leading-dot
    form (``".05"``) and scientific notation (``"5e-2"``), and negative
    values. Rejects booleans explicitly (``True``/``False`` are not valid
    thresholds even though ``float(True) == 1.0`` would otherwise silently
    "succeed"), and rejects malformed strings by letting the underlying
    ``ValueError`` propagate.
    """
    if isinstance(value, bool):
        raise TypeError(
            f"parse_numeric_threshold() rejects bool input ({value!r}); "
            "a significance threshold must be a real number, not a boolean flag."
        )
    return float(value)


# ---------------------------------------------------------------------------
# Cluster-aware inference
#
# Added 2026-07-30 (repo Stage 3, real-LLM clustered re-analysis) to
# centralize the fix for a second, distinct bug family from the same
# research thread: `repair_frontier`/`extraction_study`/`repair_diagnostic`
# each report "n=120" observations, but those 120 rows are 6 real,
# independent underlying queries replicated across ~20 provider/pool
# construction variants apiece. `bootstrap_mean_interval()` (above)
# resamples individual rows i.i.d. -- correct when rows genuinely are
# independent draws, silently wrong (understates uncertainty) when they are
# nested within a much smaller number of true clusters. These two functions
# make "resample the clusters, not the rows" the explicit, only way to get a
# CI for clustered data in this codebase, so a future study cannot
# reintroduce the same mistake by reaching for `bootstrap_mean_interval`
# out of habit.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClusteredMeanResult:
    """Cluster-level summary: one mean per cluster, then the mean of means.

    This is the "query-level aggregation" step several inference methods in
    this module build on: computing statistics over ``cluster_means`` (6
    numbers, one per query) rather than over the raw rows (120 numbers, 20
    per query) is what makes every downstream CI/test honest about the true
    number of independent observations.
    """

    overall_mean: float
    cluster_ids: tuple[Any, ...]
    cluster_means: tuple[float, ...]
    cluster_sizes: tuple[int, ...]
    n_clusters: int
    n_rows: int


def compute_cluster_means(values: Sequence[float], clusters: Sequence[Any]) -> ClusteredMeanResult:
    """Aggregate ``values`` to one mean per distinct value in ``clusters``.

    ``clusters`` must be the same length as ``values`` (one cluster label
    per row); rows sharing a cluster label are averaged together before any
    further inference is performed on them.
    """
    values = list(values)
    clusters = list(clusters)
    if len(values) != len(clusters):
        raise ValueError(
            f"compute_cluster_means: values (n={len(values)}) and clusters "
            f"(n={len(clusters)}) must be the same length"
        )
    if not values:
        return ClusteredMeanResult(
            overall_mean=float("nan"),
            cluster_ids=(),
            cluster_means=(),
            cluster_sizes=(),
            n_clusters=0,
            n_rows=0,
        )
    by_cluster: dict[Any, list[float]] = {}
    order: list[Any] = []
    for v, c in zip(values, clusters):
        if c not in by_cluster:
            by_cluster[c] = []
            order.append(c)
        by_cluster[c].append(float(v))
    cluster_ids = tuple(order)
    cluster_means = tuple(float(np.mean(by_cluster[c])) for c in order)
    cluster_sizes = tuple(len(by_cluster[c]) for c in order)
    overall_mean = float(np.mean(cluster_means))  # mean of cluster means, NOT mean of rows
    return ClusteredMeanResult(
        overall_mean=overall_mean,
        cluster_ids=cluster_ids,
        cluster_means=cluster_means,
        cluster_sizes=cluster_sizes,
        n_clusters=len(cluster_ids),
        n_rows=len(values),
    )


def cluster_bootstrap_mean_interval(
    values: Sequence[float],
    clusters: Sequence[Any],
    *,
    method: str = "percentile",
    reps: int = 10_000,
    seed: int = 13,
    min_clusters: int = 3,
) -> BootstrapIntervalResult:
    """Cluster (block) bootstrap CI for the mean, resampling clusters.

    Each bootstrap replicate draws ``n_clusters`` cluster labels **with
    replacement** from the observed clusters, then averages those clusters'
    *already-aggregated* per-cluster means (see :func:`compute_cluster_means`)
    -- never resamples individual rows. With ``n_clusters`` this small (e.g.
    6), the bootstrap distribution is necessarily coarse (only
    ``comb(2*n_clusters-1, n_clusters)`` distinct resample compositions are
    possible); this is reported honestly via ``reps`` and ``n_clusters`
    rather than dressed up as high-resolution.

    Raises ``ValueError`` if fewer than ``min_clusters`` distinct clusters
    are present -- silently returning a CI computed on 1-2 clusters would be
    worse than refusing, since no percentile interval is meaningful there.
    """
    agg = compute_cluster_means(values, clusters)
    if agg.n_clusters < min_clusters:
        raise ValueError(
            f"cluster_bootstrap_mean_interval requires at least {min_clusters} distinct "
            f"clusters, got {agg.n_clusters}. Refusing to silently compute a CI that would "
            "understate uncertainty (or be undefined) with this few clusters."
        )
    cluster_means_arr = np.asarray(agg.cluster_means, dtype=float)
    n = agg.n_clusters
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(reps, n))
    boot_means = cluster_means_arr[idx].mean(axis=1)
    theta_hat = agg.overall_mean
    frac_gt_zero = float(np.mean(boot_means > 0.0))
    alpha_lo, alpha_hi = 0.025, 0.975

    if method == "percentile":
        lo, hi = np.quantile(boot_means, [alpha_lo, alpha_hi])
    elif method == "basic":
        q_lo, q_hi = np.quantile(boot_means, [alpha_lo, alpha_hi])
        lo, hi = (2 * theta_hat - q_hi), (2 * theta_hat - q_lo)
    else:
        raise ValueError(f"cluster_bootstrap_mean_interval: unknown method {method!r}")

    return BootstrapIntervalResult(
        method=f"cluster_{method}",
        lower=float(lo),
        upper=float(hi),
        frac_gt_zero=frac_gt_zero,
        reps=reps,
        seed=seed,
    )


def cluster_exact_sign_flip_pvalue(
    values: Sequence[float], clusters: Sequence[Any]
) -> SignFlipResult:
    """Exact paired sign-flip test on cluster-level means (query-level
    aggregation followed by an exact permutation test).

    With only a handful of clusters (e.g. 6, so 2**6=64 sign patterns) this
    is enumerated exactly by :func:`exact_sign_flip_pvalue` -- delegating to
    it here (rather than duplicating the enumeration logic) after the
    query-level aggregation step, so the "cluster" version and the
    already-existing row-level version share one tested implementation.
    """
    agg = compute_cluster_means(values, clusters)
    return exact_sign_flip_pvalue(agg.cluster_means)


def cluster_exact_permutation_correlation(
    feature_values: Sequence[float],
    outcome_values: Sequence[float],
    clusters: Sequence[Any],
    *,
    max_exact_n: int = 8,
    mc_reps: int = 10_000,
    seed: int = 19,
) -> dict[str, Any]:
    """Query-clustered feature-outcome association: aggregate both
    ``feature_values`` and ``outcome_values`` to one value per cluster
    (mean; for a 0/1 feature this is the within-cluster fraction), compute
    Pearson r on the resulting (n_clusters) pairs, and get a p-value by
    exact permutation (enumerating all ``n_clusters!`` relabelings when
    ``n_clusters <= max_exact_n`` -- 6! = 720, trivial to enumerate exactly;
    falls back to a seeded Monte Carlo permutation for larger cluster
    counts). This replaces a row-level Pearson correlation computed at
    n=120 (which treats 20 replicates of each of 6 queries as 120
    independent data points) with the honest n=6 test the data can
    actually support -- the scipy/asymptotic p-value at n=6 would rest on a
    t-distribution approximation that is not trustworthy this far from its
    large-sample justification, so this always reports an exact/permutation
    p-value instead, never the asymptotic one.
    """
    import itertools
    import math

    agg_feat = compute_cluster_means(feature_values, clusters)
    agg_out = compute_cluster_means(outcome_values, clusters)
    if agg_feat.cluster_ids != agg_out.cluster_ids:
        raise ValueError(
            "cluster_exact_permutation_correlation: feature and outcome clusters must "
            "appear in the same order -- build both from the same (values, clusters) call order"
        )
    x = np.asarray(agg_feat.cluster_means, dtype=float)
    y = np.asarray(agg_out.cluster_means, dtype=float)
    n = len(x)
    if n < 3:
        return {
            "n_clusters": n,
            "pearson_r": None,
            "pvalue": None,
            "method": "insufficient_clusters",
        }
    if np.std(x) < _ZERO_TOL or np.std(y) < _ZERO_TOL:
        return {
            "n_clusters": n,
            "pearson_r": 0.0,
            "pvalue": 1.0,
            "method": "degenerate_zero_variance",
        }
    observed_r = float(np.corrcoef(x, y)[0, 1])

    if n <= max_exact_n:
        perms = list(itertools.permutations(range(n)))
        count = 0
        for perm in perms:
            r = np.corrcoef(x, np.array(y)[list(perm)])[0, 1]
            if abs(r) >= abs(observed_r) - _ZERO_TOL:
                count += 1
        pvalue = count / len(perms)
        method = f"exact_permutation_{math.factorial(n)}"
        reps = len(perms)
    else:
        rng = np.random.default_rng(seed)
        count = 0
        for _ in range(mc_reps):
            perm_y = rng.permutation(y)
            r = np.corrcoef(x, perm_y)[0, 1]
            if abs(r) >= abs(observed_r) - _ZERO_TOL:
                count += 1
        pvalue = (count + 1) / (mc_reps + 1)
        method = "monte_carlo_permutation"
        reps = mc_reps

    return {
        "n_clusters": n,
        "cluster_ids": agg_feat.cluster_ids,
        "cluster_feature_means": tuple(x.tolist()),
        "cluster_outcome_means": tuple(y.tolist()),
        "pearson_r": observed_r,
        "pvalue": float(pvalue),
        "method": method,
        "reps": reps,
    }
