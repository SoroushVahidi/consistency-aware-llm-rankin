#!/usr/bin/env python
"""
generate_manuscript_tables_and_figures.py
==========================================
Generates the manuscript-facing tables and figures for the negative-result
paper (papers/negative_result_2026/) from ALREADY-EXISTING artifacts only:
reports/repository_scale_headroom_analysis/ (this branch's repository-scale
meta-analysis) and a small number of literal, directly-quoted numbers from
the finalized JDIQ manuscript (papers/JDIQ_2026/manuscript/main.tex) and
its statistical-power table
(reports/final_revision_task2_statistical_power_20260715/).

No new experiments, no new LLM judgments, no network calls, no model
training. Deterministic: re-running produces byte-identical CSVs and
pixel-identical figures (fixed data, fixed matplotlib settings, no
randomness in this script itself -- all upstream bootstrap CIs were
already computed with fixed seeds by run_repository_scale_headroom_analysis.py).

Writes:
  reports/repository_scale_headroom_analysis/manuscript_tables/table_*.csv
  reports/repository_scale_headroom_analysis/manuscript_figures/figure_*.png
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from consistency_ranker.statistical_inference import proportion_interval  # noqa: E402

ANALYSIS_DIR = _REPO_ROOT / "reports/repository_scale_headroom_analysis"
TABLES_DIR = ANALYSIS_DIR / "manuscript_tables"
FIGURES_DIR = ANALYSIS_DIR / "manuscript_figures"

PER_QUERY_EFFECTS_CSV = ANALYSIS_DIR / "per_query_effects.csv"
PER_QUERY_AGG_CSV = ANALYSIS_DIR / "per_query_aggregated_effects.csv"
SUMMARY_JSON = ANALYSIS_DIR / "summary.json"
HEADROOM_BY_REGIME_CSV = ANALYSIS_DIR / "headroom_by_regime.csv"
PREDICTABILITY_JSON = ANALYSIS_DIR / "predictability_upper_bounds.json"

# Literal, directly-quoted numbers from the finalized JDIQ manuscript
# (papers/JDIQ_2026/manuscript/main.tex, verified by grep against the
# source .tex on 2026-07-28) -- NOT recomputed here. Citing rather than
# re-deriving avoids introducing a new, unverified statistic on top of an
# already-published one.
JDIQ_CANONICAL = {
    "median_observed_abs_delta_ndcg_active_larger_pool": 0.0036,
    "mde_nominal_alpha05_power80": 0.0133,
    "mde_holm_adjusted_power80": 0.0207,
    "canonical_active_ms1_holm_significant_cells": "0/20",
    "canonical_full_holm_significant_cells": "0/60",
    "larger_pool_holm_significant_cells": "0/110",
    "exact_repair_canonical_holm_significant_cells": "0/36",
    "exact_repair_larger_pool_holm_significant_cells": "0/56",
    "source": "papers/JDIQ_2026/manuscript/main.tex (finalized 2026-07-15)",
}


def _require(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Required input artifact missing: {path}. This script only reads "
            "already-existing artifacts; run scripts/run_repository_scale_headroom_analysis.py "
            "first if per_query_effects.csv (gitignored, regenerable) is absent."
        )


def _query_by_regime_table(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse pool/pair/protocol variants within the SAME (dataset,
    query_id, regime) into one row -- the "query-by-regime" unit the task
    requires kept separate from the pure query-level unit.
    """
    d = df.copy()
    d["oracle"] = d[["preserve_metric", "repair_metric"]].max(axis=1)
    agg = (
        d.groupby(["dataset", "query_id", "regime"], dropna=False)
        .agg(
            preserve_metric=("preserve_metric", "mean"),
            repair_metric=("repair_metric", "mean"),
            oracle=("oracle", "mean"),
            n_variants=("delta", "count"),
        )
        .reset_index()
    )
    agg["delta"] = agg["repair_metric"] - agg["preserve_metric"]
    return agg


def _benefit_harm_neutral_with_ci(delta: np.ndarray) -> dict:
    n = len(delta)
    n_benefit = int((delta > 0).sum())
    n_harm = int((delta < 0).sum())
    n_neutral = n - n_benefit - n_harm
    ci_b = proportion_interval(n_benefit, n)
    ci_h = proportion_interval(n_harm, n)
    ci_n = proportion_interval(n_neutral, n)
    return {
        "n": n,
        "n_benefit": n_benefit, "frac_benefit": n_benefit / n,
        "frac_benefit_ci_lower": ci_b.lower, "frac_benefit_ci_upper": ci_b.upper,
        "n_harm": n_harm, "frac_harm": n_harm / n,
        "frac_harm_ci_lower": ci_h.lower, "frac_harm_ci_upper": ci_h.upper,
        "n_neutral": n_neutral, "frac_neutral": n_neutral / n,
        "frac_neutral_ci_lower": ci_n.lower, "frac_neutral_ci_upper": ci_n.upper,
        "mean_delta": float(delta.mean()), "median_delta": float(np.median(delta)),
        "q05_delta": float(np.quantile(delta, 0.05)), "q25_delta": float(np.quantile(delta, 0.25)),
        "q75_delta": float(np.quantile(delta, 0.75)), "q95_delta": float(np.quantile(delta, 0.95)),
        "mean_benefit_magnitude": float(delta[delta > 0].mean()) if n_benefit else None,
        "mean_harm_magnitude": float(delta[delta < 0].mean()) if n_harm else None,
    }


# ---------------------------------------------------------------------------
# Table 1: dataset and regime coverage
# ---------------------------------------------------------------------------


def table_1_coverage(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (dataset,), g in df.groupby(["dataset"]):
        rows.append(
            {
                "dataset": dataset,
                "n_query_regime_rows": len(g),
                "n_distinct_queries": g["query_id"].nunique(),
                "n_regimes_present": g["regime"].nunique(),
                "n_repair_algorithms_present": g["repair_algorithm"].nunique(),
                "n_source_families": g["source_family"].nunique(),
            }
        )
    total = {
        "dataset": "ALL (pooled)",
        "n_query_regime_rows": len(df),
        "n_distinct_queries": df[["dataset", "query_id"]].drop_duplicates().shape[0],
        "n_regimes_present": df["regime"].nunique(),
        "n_repair_algorithms_present": df["repair_algorithm"].nunique(),
        "n_source_families": df["source_family"].nunique(),
    }
    return pd.DataFrame(rows + [total])


# ---------------------------------------------------------------------------
# Table 2: canonical downstream significance results (JDIQ, cited not recomputed)
# ---------------------------------------------------------------------------


def table_2_canonical_significance() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"family": "canonical, active ms1 only", "holm_significant_cells": "0/20",
             "source": JDIQ_CANONICAL["source"]},
            {"family": "canonical, full", "holm_significant_cells": "0/60",
             "source": JDIQ_CANONICAL["source"]},
            {"family": "larger candidate pool (P>k)", "holm_significant_cells": "0/110",
             "source": JDIQ_CANONICAL["source"]},
            {"family": "exact ILP repair, canonical", "holm_significant_cells": "0/36",
             "source": JDIQ_CANONICAL["source"]},
            {"family": "exact ILP repair, larger pool", "holm_significant_cells": "0/56",
             "source": JDIQ_CANONICAL["source"]},
        ]
    )


# ---------------------------------------------------------------------------
# Table 3: repository-scale oracle-headroom results
# ---------------------------------------------------------------------------


def table_3_headroom(summary: dict, headroom_by_regime: pd.DataFrame) -> pd.DataFrame:
    ql = summary["query_level_headroom_RECOMMENDED"]
    overall = pd.DataFrame(
        [
            {
                "slice": "ALL (query-level, recommended)", "n": ql["n_distinct_queries"],
                "headroom": ql["headroom"], "ci_lower": ql["headroom_ci_lower"],
                "ci_upper": ql["headroom_ci_upper"],
            }
        ]
    )
    by_regime = headroom_by_regime[headroom_by_regime["slice_type"] == "by_dataset_and_regime"][
        ["dataset", "regime", "n_queries", "headroom", "headroom_ci_lower", "headroom_ci_upper"]
    ].rename(columns={"n_queries": "n"})
    by_regime["slice"] = by_regime["dataset"] + " / " + by_regime["regime"] + " (row-level)"
    by_regime = by_regime.rename(
        columns={"headroom_ci_lower": "ci_lower", "headroom_ci_upper": "ci_upper"}
    )[["slice", "n", "headroom", "ci_lower", "ci_upper"]]
    return pd.concat([overall, by_regime], ignore_index=True)


# ---------------------------------------------------------------------------
# Table 4: benefit/harm/neutral decomposition (query-level AND query-by-regime, kept separate)
# ---------------------------------------------------------------------------


def table_4_benefit_harm_neutral(df: pd.DataFrame, agg_query: pd.DataFrame) -> pd.DataFrame:
    rows = []

    def _add(label, unit, delta_arr):
        if len(delta_arr) == 0:
            return
        d = _benefit_harm_neutral_with_ci(delta_arr)
        d["slice"] = label
        d["unit"] = unit
        rows.append(d)

    _add("ALL", "query-level", agg_query["delta"].to_numpy(dtype=float))
    for dataset, g in agg_query.groupby("dataset"):
        _add(dataset, "query-level", g["delta"].to_numpy(dtype=float))

    qbr = _query_by_regime_table(df)
    _add("ALL", "query-by-regime", qbr["delta"].to_numpy(dtype=float))
    for (dataset, regime), g in qbr.groupby(["dataset", "regime"]):
        _add(f"{dataset} / {regime}", "query-by-regime", g["delta"].to_numpy(dtype=float))

    for algo, g in df.groupby("repair_algorithm"):
        _add(f"repair_algorithm={algo}", "query-by-regime (not deduped across regimes)",
             g["delta"].to_numpy(dtype=float))

    out = pd.DataFrame(rows)
    cols = ["slice", "unit"] + [c for c in out.columns if c not in ("slice", "unit")]
    return out[cols]


# ---------------------------------------------------------------------------
# Table 5: feature association summary (reformat predictability_upper_bounds.json)
# ---------------------------------------------------------------------------


def table_5_feature_association(predictability: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(predictability)


# ---------------------------------------------------------------------------
# Table 6: previous selector attempts (structured synthesis matching research_decision.md)
# ---------------------------------------------------------------------------


def table_6_selector_attempts() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "attempt": "outputs/learned_selector/",
                "target": "FAS-apply-or-not per query",
                "features": "bew_before, disagreement, n_sccs, cyclic_int (4)",
                "model": "logistic regression, shallow tree",
                "n_queries": 300,
                "n_datasets": 3,
                "negative_controls": "none",
                "result": "fixed threshold (disagreement top-25%) beat both learned models overall",
                "fundamental_or_implementation": (
                    "fundamental (per repository-scale headroom ceiling)"
                ),
            },
            {
                "attempt": "experiments/failure_class_audit_20260711_212157/",
                "target": "harm_label, help_label, any_non_neutral, extraction_insensitivity",
                "features": "undocumented in surviving report",
                "model": "logistic, tree, random forest",
                "n_queries": None,
                "n_datasets": None,
                "negative_controls": "none",
                "result": "ROC-AUC 0.83-0.88, PR-AUC only 0.09-0.33 (imbalance mismatch)",
                "fundamental_or_implementation": "fundamental, compounded by class imbalance",
            },
            {
                "attempt": "src/consistency_ranker/repair_selector_mining/",
                "target": "delta >= {0, 0.0025, 0.005, 0.01} binary + regression",
                "features": (
                    "is_cyclic, largest_scc_frac, n_non_trivial_sccs, "
                    "scc_cycle_burden_frac, n_mutual_pairs_frac, graph_density, "
                    "vote_entropy, fas_removed_weight_frac, prior_top1_margin, "
                    "prior_entropy, ranker_disagreement, greedy_exact_disagreement (12)"
                ),
                "model": "logreg, shallow_tree, tree_depth4, random_forest, "
                         "gradient_boosting, random_forest_calibrated",
                "n_queries": None,
                "n_datasets": None,
                "negative_controls": "designed but not implemented",
                "result": "never executed -- no run outputs found in this repository",
                "fundamental_or_implementation": "not assessable empirically",
            },
            {
                "attempt": "reports/repository_scale_headroom_analysis/ (this analysis)",
                "target": "oracle headroom (diagnostic, not a trained model)",
                "features": "repair_cost, largest_scc_size, graph_density, is_cyclic, "
                             "repair_algorithm, dataset, regime",
                "model": "none -- descriptive/statistical only",
                "n_queries": 419,
                "n_datasets": 4,
                "negative_controls": "not applicable (no model trained)",
                "result": "headroom real but ~8x below the manuscript's own 80%-power MDE; "
                          "negligible univariate association for every available covariate",
                "fundamental_or_implementation": (
                    "explains why 1-2 likely failed: the ceiling itself is tiny"
                ),
            },
        ]
    )


# ---------------------------------------------------------------------------
# Table 7: claims and evidence status (load the existing evidence_table.csv)
# ---------------------------------------------------------------------------


def table_7_claims_and_evidence() -> pd.DataFrame:
    return pd.read_csv(ANALYSIS_DIR / "evidence_table.csv")


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------


def _savefig(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / name, dpi=150)
    plt.close(fig)


def figure_1_structural_vs_downstream() -> None:
    # Structural activity (removed-weight fraction range from the manuscript)
    # vs. Holm-significant fraction of cells, by family -- descriptive bar chart.
    families = [
        "canonical\nactive ms1", "canonical\nfull", "larger\npool",
        "exact repair\ncanonical", "exact repair\nlarger pool",
    ]
    # Repair is structurally active (edges removed) in all 5 families (manuscript).
    structural_active = [1.0, 1.0, 1.0, 1.0, 1.0]
    holm_significant_frac = [0 / 20, 0 / 60, 0 / 110, 0 / 36, 0 / 56]
    x = np.arange(len(families))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    width = 0.35
    ax.bar(
        x - width / 2, structural_active, width,
        label="Fraction of graphs with active repair\n(edges removed)",
    )
    ax.bar(
        x + width / 2, holm_significant_frac, width,
        label="Fraction of Holm-significant\nnDCG cells",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(families)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Fraction")
    ax.set_title("Structural repair activity vs. downstream significance (JDIQ manuscript)")
    ax.legend(loc="upper right", fontsize=8)
    _savefig(fig, "figure_1_structural_vs_downstream.png")


def figure_2_delta_distribution(agg_query: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    deltas = agg_query["delta"].to_numpy(dtype=float)
    ax.hist(deltas, bins=60, color="#4C72B0", edgecolor="black", linewidth=0.3)
    ax.axvline(0, color="black", linewidth=1)
    ax.set_xlabel("Per-query repair effect: NDCG(repair) - NDCG(preserve)")
    ax.set_ylabel("Number of queries (n=%d)" % len(deltas))
    ax.set_title("Distribution of query-level repair effects (all 4 datasets)")
    _savefig(fig, "figure_2_delta_distribution.png")


def figure_3_benefit_harm_neutral_by_dataset(agg_query: pd.DataFrame) -> None:
    datasets = sorted(agg_query["dataset"].unique())
    benefit, harm, neutral = [], [], []
    for ds in datasets:
        d = agg_query.loc[agg_query["dataset"] == ds, "delta"].to_numpy(dtype=float)
        n = len(d)
        benefit.append((d > 0).sum() / n)
        harm.append((d < 0).sum() / n)
        neutral.append((d == 0).sum() / n)
    x = np.arange(len(datasets))
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(x, benefit, label="Benefit", color="#55A868")
    ax.bar(x, harm, bottom=benefit, label="Harm", color="#C44E52")
    bottom2 = [b + h for b, h in zip(benefit, harm)]
    ax.bar(x, neutral, bottom=bottom2, label="Neutral (exact 0)", color="#8C8C8C")
    ax.set_xticks(x)
    ax.set_xticklabels(datasets)
    ax.set_ylabel("Fraction of queries (query-level)")
    ax.set_title("Benefit / harm / neutral fractions by dataset")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_ylim(0, 1.0)
    _savefig(fig, "figure_3_benefit_harm_neutral_by_dataset.png")


def figure_4_headroom_by_regime(headroom_by_regime: pd.DataFrame) -> None:
    d = headroom_by_regime[headroom_by_regime["slice_type"] == "by_dataset_and_regime"].copy()
    d = d.sort_values(["dataset", "regime"])
    labels = [f"{r.dataset}\n{r.regime}" for r in d.itertuples()]
    x = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(10, 5))
    yerr_lower = d["headroom"] - d["headroom_ci_lower"]
    yerr_upper = d["headroom_ci_upper"] - d["headroom"]
    ax.bar(x, d["headroom"], yerr=[yerr_lower, yerr_upper], capsize=3, color="#4C72B0")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7, rotation=0)
    ax.set_ylabel("Oracle headroom (row-level; see caption)")
    ax.set_title(
        "Oracle headroom by dataset x vote-construction regime\n"
        "(row-level CIs shown; see Table 3/4 for query-level estimates)"
    )
    _savefig(fig, "figure_4_headroom_by_regime.png")


def figure_5_headroom_vs_mde(summary: dict) -> None:
    ql = summary["query_level_headroom_RECOMMENDED"]
    fig, ax = plt.subplots(figsize=(6, 4.5))
    labels = ["Query-level\noracle headroom", "Holm-adjusted\n80%-power MDE\n(JDIQ manuscript)"]
    values = [ql["headroom"], JDIQ_CANONICAL["mde_holm_adjusted_power80"]]
    errs = [[ql["headroom"] - ql["headroom_ci_lower"]], [0]]
    errs_upper = [[ql["headroom_ci_upper"] - ql["headroom"]], [0]]
    colors = ["#4C72B0", "#C44E52"]
    bars = ax.bar(labels, values, color=colors)
    ax.errorbar(
        [0], [ql["headroom"]], yerr=[[errs[0][0]], [errs_upper[0][0]]],
        fmt="none", ecolor="black", capsize=4,
    )
    ax.set_ylabel("nDCG@10 effect size")
    ratio = ql["headroom"] / JDIQ_CANONICAL["mde_holm_adjusted_power80"]
    ax.set_title(
        f"Oracle headroom vs. established minimum-detectable-effect\n(ratio = {ratio:.3f})"
    )
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.0005, f"{v:.4f}", ha="center", fontsize=9)
    _savefig(fig, "figure_5_headroom_vs_mde.png")


def figure_6_feature_association(predictability: list[dict]) -> None:
    numeric = [p for p in predictability if "pearson_r" in p]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    names = [p["covariate"] for p in numeric]
    r_vals = [abs(p["pearson_r"]) for p in numeric]
    ax.barh(names, r_vals, color="#4C72B0")
    ax.axvline(
        0.1, color="gray", linestyle="--", linewidth=1, label="|r|=0.1 (conventional 'small')"
    )
    ax.set_xlabel("|Pearson r| vs. repair effect")
    ax.set_title(
        "Pre-repair covariate association with repair effect\n"
        "(all far below conventional 'small' effect)"
    )
    ax.set_xlim(0, 0.15)
    ax.legend(fontsize=8)
    _savefig(fig, "figure_6_feature_association.png")


def figure_7_selector_attempt_timeline() -> None:
    attempts = [
        ("2026-07-11\nfailure_class_audit", "High ROC-AUC,\nlow PR-AUC"),
        ("2026-07-13\nrepair_selector_mining", "Built,\nnever run"),
        ("2026-07-1x\nlearned_selector", "Fixed threshold\nbeat learned model"),
        ("2026-07-28\nrepository-scale\nGate 0", "Headroom real but\n~8x below MDE"),
    ]
    fig, ax = plt.subplots(figsize=(9, 3))
    x = np.arange(len(attempts))
    ax.plot(x, [1] * len(attempts), "o-", color="#4C72B0", markersize=10)
    for xi, (label, result) in zip(x, attempts):
        ax.annotate(
            label, (xi, 1), textcoords="offset points", xytext=(0, 15),
            ha="center", fontsize=8,
        )
        ax.annotate(
            result, (xi, 1), textcoords="offset points", xytext=(0, -35),
            ha="center", fontsize=8, color="#C44E52",
        )
    ax.set_ylim(0.5, 1.5)
    ax.axis("off")
    ax.set_title("Four independent attempts, one convergent conclusion")
    _savefig(fig, "figure_7_selector_attempt_timeline.png")


def main() -> None:
    _require(PER_QUERY_EFFECTS_CSV)
    _require(PER_QUERY_AGG_CSV)
    _require(SUMMARY_JSON)
    _require(HEADROOM_BY_REGIME_CSV)
    _require(PREDICTABILITY_JSON)

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(PER_QUERY_EFFECTS_CSV, low_memory=False)
    agg_query = pd.read_csv(PER_QUERY_AGG_CSV)
    summary = json.loads(SUMMARY_JSON.read_text())
    headroom_by_regime = pd.read_csv(HEADROOM_BY_REGIME_CSV)
    predictability = json.loads(PREDICTABILITY_JSON.read_text())

    if len(df) != summary["n_total_rows"]:
        raise ValueError(
            f"per_query_effects.csv row count ({len(df)}) does not match "
            f"summary.json's n_total_rows ({summary['n_total_rows']}) -- inputs are "
            "inconsistent, refusing to generate manuscript artifacts from stale data."
        )
    # (dataset, query_id) is the grouping key -- query_id alone may repeat across datasets.
    n_distinct = agg_query[["dataset", "query_id"]].drop_duplicates().shape[0]
    if n_distinct != len(agg_query):
        raise ValueError(
            "per_query_aggregated_effects.csv has duplicate (dataset, query_id) rows"
        )

    table_1_coverage(df).to_csv(TABLES_DIR / "table_1_dataset_regime_coverage.csv", index=False)
    table_2_canonical_significance().to_csv(
        TABLES_DIR / "table_2_canonical_downstream_significance.csv", index=False
    )
    table_3_headroom(summary, headroom_by_regime).to_csv(
        TABLES_DIR / "table_3_oracle_headroom.csv", index=False
    )
    table_4_benefit_harm_neutral(df, agg_query).to_csv(
        TABLES_DIR / "table_4_benefit_harm_neutral_decomposition.csv", index=False
    )
    table_5_feature_association(predictability).to_csv(
        TABLES_DIR / "table_5_feature_association_summary.csv", index=False
    )
    table_6_selector_attempts().to_csv(
        TABLES_DIR / "table_6_previous_selector_attempts.csv", index=False
    )
    table_7_claims_and_evidence().to_csv(
        TABLES_DIR / "table_7_claims_and_evidence_status.csv", index=False
    )

    figure_1_structural_vs_downstream()
    figure_2_delta_distribution(agg_query)
    figure_3_benefit_harm_neutral_by_dataset(agg_query)
    figure_4_headroom_by_regime(headroom_by_regime)
    figure_5_headroom_vs_mde(summary)
    figure_6_feature_association(predictability)
    figure_7_selector_attempt_timeline()

    print(f"Wrote 7 tables to {TABLES_DIR}")
    print(f"Wrote 7 figures to {FIGURES_DIR}")


if __name__ == "__main__":
    main()
