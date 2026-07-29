#!/usr/bin/env python
"""
run_repository_scale_headroom_analysis.py
==========================================
Repository-scale meta-analysis of preserve-vs-repair evidence, to determine
whether the "predict per-query repair effect" research direction
(docs/research/RESEARCH_TRAJECTORY.md) should continue at all.

Reads ONLY already-existing, already-committed (or already-local, in the
case of a few JDIQ-era working directories) per-query outcome tables --
NO new experiments, NO new LLM judgments, NO network calls, NO model
training. Unifies them into one per-query table with full provenance,
computes oracle headroom at repository scale (pooled and sliced many
ways, with bootstrap CIs), characterizes heterogeneity descriptively, and
runs simple information-theoretic/statistical predictability-upper-bound
checks (mutual information, correlation, ANOVA) on whatever pre-repair
covariates each source already provides -- no new feature engineering.

Writes reports/repository_scale_headroom_analysis/.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats as scipy_stats  # noqa: E402
from sklearn.feature_selection import mutual_info_regression  # noqa: E402

from consistency_ranker.statistical_inference import (  # noqa: E402
    bootstrap_mean_interval,
    proportion_interval,
)

OUT_DIR = _REPO_ROOT / "reports/repository_scale_headroom_analysis"

UNIFIED_COLUMNS = [
    "source_family", "source_file", "source_file_sha256",
    "dataset", "regime", "pool_id_or_config", "pool_size", "metric_cutoff",
    "protocol", "pair_name", "pair_family", "repair_algorithm",
    "judge_or_provider", "parsing_policy",
    "query_id", "preserve_metric", "repair_metric", "delta",
    "repair_cost", "is_cyclic", "largest_scc_size", "graph_density",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _row(source_family, path, **kwargs):
    base = {c: None for c in UNIFIED_COLUMNS}
    base["source_family"] = source_family
    base["source_file"] = str(path.relative_to(_REPO_ROOT))
    base.update(kwargs)
    return base


def _clean_float(v):
    try:
        f = float(v)
        return f if np.isfinite(f) else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Per-family loaders. Each returns a list of dicts in UNIFIED_COLUMNS shape.
# ---------------------------------------------------------------------------


def load_paired_deltas_style(path: Path, family: str, repair_algorithm: str) -> list[dict]:
    df = pd.read_csv(path)
    sha = _sha256(path)
    rows = []
    for rec in df.to_dict("records"):
        u, r = _clean_float(rec.get("unrepaired_ndcg")), _clean_float(rec.get("repaired_ndcg"))
        if u is None or r is None:
            continue
        rows.append(
            _row(
                family, path, source_file_sha256=sha,
                dataset=rec.get("dataset"), regime=rec.get("regime"),
                pool_id_or_config=rec.get("pool_id"),
                protocol=rec.get("protocol"),
                pair_name=rec.get("pair_name"), pair_family=rec.get("pair_family"),
                repair_algorithm=repair_algorithm,
                query_id=str(rec.get("query_id")),
                preserve_metric=u, repair_metric=r, delta=r - u,
            )
        )
    return rows


def load_exact_task4_style(path: Path) -> list[dict]:
    df = pd.read_csv(path)
    sha = _sha256(path)
    rows = []
    for rec in df.to_dict("records"):
        u, r = _clean_float(rec.get("unrepaired_ndcg")), _clean_float(rec.get("repaired_ndcg"))
        if u is None or r is None:
            continue
        rows.append(
            _row(
                "exact_ilp_task4", path, source_file_sha256=sha,
                dataset=rec.get("dataset"), regime=rec.get("regime"),
                pool_id_or_config=rec.get("config_id"), pool_size=rec.get("pool_size"),
                metric_cutoff=rec.get("metric_cutoff"),
                protocol=rec.get("family"),
                pair_name=rec.get("pair_name"), pair_family=rec.get("pair_family"),
                repair_algorithm="exact_ilp",
                query_id=str(rec.get("query_id")),
                preserve_metric=u, repair_metric=r, delta=r - u,
                repair_cost=_clean_float(rec.get("removed_weight")),
                is_cyclic=rec.get("graph_is_cyclic"),
            )
        )
    return rows


def load_pool_cutoff_style(path: Path, repair_algorithm: str) -> list[dict]:
    df = pd.read_csv(path)
    sha = _sha256(path)
    rows = []
    for rec in df.to_dict("records"):
        u, r = _clean_float(rec.get("unrepaired_ndcg")), _clean_float(rec.get("repaired_ndcg"))
        if u is None or r is None:
            continue
        scc = rec.get("largest_scc_size_pre")
        density = rec.get("graph_density_pre")
        cost = rec.get("removed_weight_fraction")
        if cost is None:
            cost = rec.get("removed_weight")
        rows.append(
            _row(
                f"pool_cutoff_{repair_algorithm}", path, source_file_sha256=sha,
                dataset=rec.get("dataset"), regime=rec.get("regime"),
                pool_id_or_config=rec.get("config_id"), pool_size=rec.get("pool_size"),
                metric_cutoff=rec.get("metric_cutoff"),
                pair_name=rec.get("pair_name"), pair_family=rec.get("pair_family"),
                repair_algorithm=repair_algorithm,
                query_id=str(rec.get("query_id")),
                preserve_metric=u, repair_metric=r, delta=r - u,
                repair_cost=_clean_float(cost),
                is_cyclic=rec.get("graph_is_cyclic"),
                largest_scc_size=_clean_float(scc),
                graph_density=_clean_float(density),
            )
        )
    return rows


def load_policy_sensitivity_style(path: Path) -> list[dict]:
    df = pd.read_csv(path)
    sha = _sha256(path)
    rows = []
    for rec in df.to_dict("records"):
        if rec.get("usable") in (False, "False", 0, "0"):
            continue
        u, r = _clean_float(rec.get("unrepaired_ndcg")), _clean_float(rec.get("repaired_ndcg"))
        if u is None or r is None:
            continue
        rows.append(
            _row(
                "real_llm_integrity_policy_sensitivity", path, source_file_sha256=sha,
                dataset=rec.get("dataset"), regime=rec.get("vote_regime"),
                repair_algorithm="greedy",
                judge_or_provider=rec.get("provider"), parsing_policy=rec.get("policy"),
                query_id=str(rec.get("query_id")),
                preserve_metric=u, repair_metric=r, delta=r - u,
                is_cyclic=rec.get("is_cyclic"),
                largest_scc_size=_clean_float(rec.get("largest_scc_size")),
            )
        )
    return rows


def load_cycle_type_style(path: Path) -> list[dict]:
    df = pd.read_csv(path)
    sha = _sha256(path)
    rows = []
    for rec in df.to_dict("records"):
        u = _clean_float(rec.get("ndcg_unrepaired_markov_graph"))
        r = _clean_float(rec.get("ndcg_repaired_markov_graph_repaired"))
        if u is None or r is None:
            continue
        rows.append(
            _row(
                "cycle_type_diagnostic", path, source_file_sha256=sha,
                dataset=rec.get("dataset"), regime=rec.get("regime"),
                pair_name="markov_graph_repaired", pair_family="graph",
                repair_algorithm="greedy",
                query_id=str(rec.get("query_id")),
                preserve_metric=u, repair_metric=r, delta=r - u,
                repair_cost=_clean_float(rec.get("fas_weight_removed_before")),
                is_cyclic=rec.get("is_cyclic_before"),
                largest_scc_size=_clean_float(rec.get("largest_scc_before")),
            )
        )
    return rows


def build_unified_table() -> tuple[pd.DataFrame, list[dict]]:
    all_rows: list[dict] = []
    coverage: list[dict] = []

    def _track(family, path, n):
        coverage.append(
            {"source_family": family, "path": str(path.relative_to(_REPO_ROOT)), "n_rows": n}
        )

    simple_sources = [
        ("pool_robustness_greedy",
         "reports/candidate_pool_conditional_audit_20260714/tables/pool_robustness_paired_deltas.csv",
         "greedy"),
        ("new_baseline_greedy",
         "reports/candidate_pool_conditional_audit_20260714/tables/new_baseline_paired_deltas.csv",
         "greedy"),
        ("full_calibrated_core_greedy",
         "reports/full_calibrated_core/tables/full_paired_deltas.csv",
         "greedy"),
    ]
    for family, rel, algo in simple_sources:
        path = _REPO_ROOT / rel
        if not path.exists():
            continue
        rows = load_paired_deltas_style(path, family, algo)
        all_rows.extend(rows)
        _track(family, path, len(rows))

    exact_task4_path = (
        _REPO_ROOT
        / "reports/final_revision_task4_exact_baseline_fairness_20260715"
        / "tables/exact_repaired_vs_unrepaired_pair_metrics.csv"
    )
    if exact_task4_path.exists():
        rows = load_exact_task4_style(exact_task4_path)
        all_rows.extend(rows)
        _track("exact_ilp_task4", exact_task4_path, len(rows))

    for algo, subdir in (("greedy", "greedy_pool_cutoff"), ("exact_ilp", "exact_pool_cutoff")):
        base = _REPO_ROOT / f"reports/final_revision_task1_pool_cutoff_20260715/outputs/{subdir}"
        if not base.exists():
            continue
        for path in sorted(base.rglob("query_pair_metrics.csv")):
            rows = load_pool_cutoff_style(path, algo)
            all_rows.extend(rows)
            _track(f"pool_cutoff_{algo}", path, len(rows))

    policy_sens_path = (
        _REPO_ROOT
        / "experiments/real_llm_integrity_audit_20260713_034713"
        / "policy_sensitivity_full.csv"
    )
    if policy_sens_path.exists():
        rows = load_policy_sensitivity_style(policy_sens_path)
        all_rows.extend(rows)
        _track("real_llm_integrity_policy_sensitivity", policy_sens_path, len(rows))

    cycle_type_path = (
        _REPO_ROOT
        / "reports/blocking_issues_investigation/tables"
        / "query_cycle_type_and_repair_effect.csv"
    )
    if cycle_type_path.exists():
        rows = load_cycle_type_style(cycle_type_path)
        all_rows.extend(rows)
        _track("cycle_type_diagnostic", cycle_type_path, len(rows))

    df = pd.DataFrame(all_rows, columns=UNIFIED_COLUMNS)
    return df, coverage


# ---------------------------------------------------------------------------
# Phase 2: oracle headroom (pooled + sliced), with bootstrap CIs.
# ---------------------------------------------------------------------------


def _headroom_for_group(g: pd.DataFrame) -> dict:
    preserve = g["preserve_metric"].to_numpy(dtype=float)
    repair = g["repair_metric"].to_numpy(dtype=float)
    oracle = np.maximum(preserve, repair)
    mean_preserve, mean_repair, mean_oracle = preserve.mean(), repair.mean(), oracle.mean()
    regret_preserve = oracle - preserve
    regret_repair = oracle - repair
    stronger_regret = regret_preserve if mean_preserve >= mean_repair else regret_repair
    ci = bootstrap_mean_interval(stronger_regret.tolist(), reps=5000, seed=13)
    delta = repair - preserve
    return {
        "n_queries": int(len(g)),
        "mean_preserve": float(mean_preserve),
        "mean_repair": float(mean_repair),
        "mean_oracle": float(mean_oracle),
        "headroom": float(mean_oracle - max(mean_preserve, mean_repair)),
        "headroom_ci_lower": ci.lower,
        "headroom_ci_upper": ci.upper,
        "frac_benefit": float((delta > 0).mean()),
        "frac_harm": float((delta < 0).mean()),
        "frac_neutral": float((delta == 0).mean()),
        "mean_delta": float(delta.mean()),
        "median_delta": float(np.median(delta)),
        "std_delta": float(delta.std(ddof=1)) if len(delta) > 1 else 0.0,
    }


def run_headroom_by(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    records = []
    for keys, g in df.groupby(by, dropna=False):
        if len(g) < 5:
            continue
        keys = keys if isinstance(keys, tuple) else (keys,)
        rec = dict(zip(by, keys))
        rec.update(_headroom_for_group(g))
        records.append(rec)
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Phase 5: predictability upper bounds on existing numeric covariates.
# ---------------------------------------------------------------------------


def predictability_upper_bounds(df: pd.DataFrame) -> list[dict]:
    numeric_covariates = ["repair_cost", "largest_scc_size", "graph_density"]
    results = []
    for col in numeric_covariates:
        sub = df[[col, "delta"]].dropna()
        if len(sub) < 30:
            results.append(
                {"covariate": col, "n": len(sub), "note": "insufficient non-null n (<30)"}
            )
            continue
        x = sub[col].to_numpy(dtype=float).reshape(-1, 1)
        y = sub["delta"].to_numpy(dtype=float)
        pear_r, pear_p = scipy_stats.pearsonr(x.ravel(), y)
        spear_r, spear_p = scipy_stats.spearmanr(x.ravel(), y)
        mi = mutual_info_regression(x, y, random_state=0)[0]
        results.append(
            {
                "covariate": col, "n": int(len(sub)),
                "pearson_r": float(pear_r), "pearson_p": float(pear_p),
                "spearman_r": float(spear_r), "spearman_p": float(spear_p),
                "mutual_info": float(mi),
            }
        )

    if "is_cyclic" in df.columns:
        sub = df[["is_cyclic", "delta"]].dropna()
        sub = sub[sub["is_cyclic"].isin([True, False, "True", "False", 1, 0, 1.0, 0.0])]
        if len(sub) >= 30:
            cyclic_mask = sub["is_cyclic"].isin([True, "True", 1, 1.0])
            cyc = sub.loc[cyclic_mask, "delta"].to_numpy(dtype=float)
            acyc = sub.loc[~cyclic_mask, "delta"].to_numpy(dtype=float)
            if len(cyc) >= 5 and len(acyc) >= 5:
                f_stat, anova_p = scipy_stats.f_oneway(cyc, acyc)
                pooled_std = np.sqrt(((cyc.std(ddof=1) ** 2) + (acyc.std(ddof=1) ** 2)) / 2)
                cohens_d = (cyc.mean() - acyc.mean()) / pooled_std if pooled_std > 1e-12 else None
                results.append(
                    {
                        "covariate": "is_cyclic (ANOVA cyclic vs acyclic)",
                        "n": int(len(sub)),
                        "n_cyclic": int(len(cyc)),
                        "n_acyclic": int(len(acyc)),
                        "mean_delta_cyclic": float(cyc.mean()),
                        "mean_delta_acyclic": float(acyc.mean()),
                        "f_stat": float(f_stat),
                        "anova_p": float(anova_p),
                        "cohens_d": float(cohens_d) if cohens_d is not None else None,
                    }
                )

    if "repair_algorithm" in df.columns:
        groups = [
            g["delta"].dropna().to_numpy(dtype=float)
            for _, g in df.groupby("repair_algorithm")
            if len(g) >= 5
        ]
        if len(groups) >= 2:
            f_stat, anova_p = scipy_stats.f_oneway(*groups)
            results.append(
                {
                    "covariate": "repair_algorithm (ANOVA across algorithms)",
                    "n": int(sum(len(g) for g in groups)),
                    "f_stat": float(f_stat),
                    "anova_p": float(anova_p),
                }
            )

    if "dataset" in df.columns:
        groups = [
            g["delta"].dropna().to_numpy(dtype=float)
            for _, g in df.groupby("dataset")
            if len(g) >= 5
        ]
        if len(groups) >= 2:
            f_stat, anova_p = scipy_stats.f_oneway(*groups)
            results.append(
                {
                    "covariate": "dataset (ANOVA across datasets)",
                    "n": int(sum(len(g) for g in groups)),
                    "f_stat": float(f_stat),
                    "anova_p": float(anova_p),
                }
            )

    return results


def query_level_headroom(df: pd.DataFrame) -> dict:
    """Headroom computed at the correct, non-pseudo-replicated unit of
    analysis: one row per distinct (dataset, query_id), averaging across
    every regime/pool/pair/protocol variant of that query first. The
    row-pooled ``_headroom_for_group(df)`` treats 122k+ rows as
    independent when only ~419 distinct queries exist (each query repeats
    across many experimental regimes) -- its CI is therefore too narrow.
    This function is the honest, conservative cross-check.
    """
    d = df.copy()
    d["oracle"] = d[["preserve_metric", "repair_metric"]].max(axis=1)
    agg = d.groupby(["dataset", "query_id"]).agg(
        preserve_metric=("preserve_metric", "mean"),
        repair_metric=("repair_metric", "mean"),
        oracle=("oracle", "mean"),
        n_regimes=("delta", "count"),
    ).reset_index()
    agg["delta"] = agg["repair_metric"] - agg["preserve_metric"]

    mean_preserve, mean_repair, mean_oracle = (
        agg["preserve_metric"].mean(), agg["repair_metric"].mean(), agg["oracle"].mean()
    )
    regret_preserve = agg["oracle"] - agg["preserve_metric"]
    regret_repair = agg["oracle"] - agg["repair_metric"]
    stronger = regret_preserve if mean_preserve >= mean_repair else regret_repair
    ci = bootstrap_mean_interval(stronger.tolist(), reps=10000, seed=13)
    delta = agg["delta"].to_numpy(dtype=float)
    return {
        "n_distinct_queries": int(len(agg)),
        "mean_n_regimes_per_query": float(agg["n_regimes"].mean()),
        "mean_preserve": float(mean_preserve),
        "mean_repair": float(mean_repair),
        "mean_oracle": float(mean_oracle),
        "headroom": float(mean_oracle - max(mean_preserve, mean_repair)),
        "headroom_ci_lower": ci.lower,
        "headroom_ci_upper": ci.upper,
        "frac_benefit": float((delta > 0).mean()),
        "frac_harm": float((delta < 0).mean()),
        "frac_neutral_exact": float((delta == 0).mean()),
        "mean_delta": float(delta.mean()),
        "median_delta": float(np.median(delta)),
        "std_delta": float(delta.std(ddof=1)),
    }, agg


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    df, coverage = build_unified_table()
    df.to_csv(OUT_DIR / "per_query_effects.csv", index=False)
    print(f"Unified table: {len(df)} rows across {len(coverage)} source files")

    pooled = _headroom_for_group(df)
    query_level, query_level_agg_df = query_level_headroom(df)
    query_level_agg_df.to_csv(OUT_DIR / "per_query_aggregated_effects.csv", index=False)
    by_dataset = run_headroom_by(df, ["dataset"])
    by_repair_algo = run_headroom_by(df, ["repair_algorithm"])
    by_dataset_algo = run_headroom_by(df, ["dataset", "repair_algorithm"])
    by_regime = run_headroom_by(df, ["dataset", "regime"])
    by_pair_family = run_headroom_by(df, ["pair_family"])
    by_source_family = run_headroom_by(df, ["source_family"])

    headroom_by_regime_combined = pd.concat(
        [
            by_dataset.assign(slice_type="by_dataset"),
            by_repair_algo.assign(slice_type="by_repair_algorithm"),
            by_dataset_algo.assign(slice_type="by_dataset_and_repair_algorithm"),
            by_regime.assign(slice_type="by_dataset_and_regime"),
            by_pair_family.assign(slice_type="by_pair_family"),
            by_source_family.assign(slice_type="by_source_family"),
        ],
        ignore_index=True,
    )
    headroom_by_regime_combined.to_csv(OUT_DIR / "headroom_by_regime.csv", index=False)

    predictability = predictability_upper_bounds(df)
    (OUT_DIR / "predictability_upper_bounds.json").write_text(
        json.dumps(predictability, indent=2, default=str)
    )

    n_all, n_benefit = len(df), int((df["delta"] > 0).sum())
    n_harm = int((df["delta"] < 0).sum())
    frac_benefit_ci = proportion_interval(n_benefit, n_all)
    frac_harm_ci = proportion_interval(n_harm, n_all)

    summary = {
        "n_total_rows": n_all,
        "n_source_families": int(df["source_family"].nunique()),
        "n_source_files": len(coverage),
        "n_distinct_datasets": int(df["dataset"].nunique()),
        "n_distinct_query_dataset_pairs": int(
            df[["dataset", "query_id"]].drop_duplicates().shape[0]
        ),
        "datasets": sorted(df["dataset"].dropna().unique().tolist()),
        "repair_algorithms": sorted(df["repair_algorithm"].dropna().unique().tolist()),
        "pooled_headroom_row_level_CAUTION_pseudoreplicated": pooled,
        "query_level_headroom_RECOMMENDED": query_level,
        "pseudoreplication_note": (
            "The row-level pooled statistic treats every (dataset, query_id, "
            "regime, pool, pair) combination as an independent observation -- "
            "it is NOT: only n_distinct_query_dataset_pairs queries actually "
            "exist, each repeated across many regimes. Its CI is too narrow "
            "and should not be quoted as the headline number. "
            "query_level_headroom_RECOMMENDED aggregates to one row per "
            "distinct query first (averaging across regimes) before "
            "bootstrapping, which is the statistically defensible number."
        ),
        "pooled_frac_benefit_ci95": {
            "lower": frac_benefit_ci.lower, "upper": frac_benefit_ci.upper
        },
        "pooled_frac_harm_ci95": {"lower": frac_harm_ci.lower, "upper": frac_harm_ci.upper},
        "delta_distribution": {
            "mean": float(df["delta"].mean()),
            "median": float(df["delta"].median()),
            "std": float(df["delta"].std(ddof=1)),
            "q05": float(df["delta"].quantile(0.05)),
            "q25": float(df["delta"].quantile(0.25)),
            "q75": float(df["delta"].quantile(0.75)),
            "q95": float(df["delta"].quantile(0.95)),
            "min": float(df["delta"].min()),
            "max": float(df["delta"].max()),
        },
        "source_coverage": coverage,
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, default=str))

    printable = {k: v for k, v in summary.items() if k != "source_coverage"}
    print(json.dumps(printable, indent=2, default=str))


if __name__ == "__main__":
    main()
