"""
run_ir_evidence_audit.py
==========================
Final bounded IR evidence-integration and baseline-verification audit.

Makes NO new API calls, collects NO new judgments, adds NO new providers,
and invents NO new repair or extraction algorithms. Loads and unifies
ALREADY-COMPUTED per-query/per-configuration results from:

  - reports/full_calibrated_core/ (JDIQ backbone: construction sensitivity,
    structure, repair effects, and graph-free fusion baselines -- RRF,
    CombSUM, Borda fusion, Prior/individual-ranker -- across 4 datasets,
    3 vote regimes, 11 normalization/pooling protocols)
  - reports/repository_scale_headroom_analysis/ (negative_result_2026
    backbone: n=419-query oracle headroom, preserve vs. repair)
  - reports/exact_open_source_ilp_repair_investigation/ (real greedy-vs-
    exact-SCIP repair on real dataset qrels, per-query, multi-cutoff)
  - reports/final_revision_task1_pool_cutoff_20260715/ (larger-pool greedy
    repair, nDCG@5/@10/@20 + MAP/MRR, per-query)
  - reports/final_revision_task4_exact_baseline_fairness_20260715/
    (larger-pool exact repair; baseline-fairness significance tests)
  - This session's three real-multi-provider-LLM studies:
    reports/repair_frontier_20260729T144742Z/,
    reports/extraction_study_20260729T151610Z/,
    reports/repair_diagnostic_20260729T162748Z/

Outputs (see write_all_outputs): unified_configuration_results.csv,
structure_utility_associations.csv, baseline_verification.csv,
cutoff_robustness.csv, a publication table + figure, and
FINAL_IR_EVIDENCE_AUDIT.md with a predeclared readiness decision.
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
from scipy import stats  # noqa: E402

from consistency_ranker.provenance import (  # noqa: E402
    CanonicalOutputExistsError,
    collect_provenance,
    protect_canonical_output,
)

# ---------------------------------------------------------------------------
# Source paths (read-only; nothing under these paths is ever written to)
# ---------------------------------------------------------------------------
CALIBRATED_CORE = (
    _REPO_ROOT / "reports/full_calibrated_core/outputs/calibrated_all4/paper_package/tables"
)
HEADROOM_419 = _REPO_ROOT / "reports/repository_scale_headroom_analysis"
EXACT_ILP = _REPO_ROOT / "reports/exact_open_source_ilp_repair_investigation/tables"
POOL_CUTOFF = _REPO_ROOT / "reports/final_revision_task1_pool_cutoff_20260715/tables"
BASELINE_FAIRNESS = (
    _REPO_ROOT / "reports/final_revision_task4_exact_baseline_fairness_20260715/tables"
)
REPAIR_FRONTIER_DIR = _REPO_ROOT / "reports/repair_frontier_20260729T144742Z"
EXTRACTION_DIR = _REPO_ROOT / "reports/extraction_study_20260729T151610Z"
REPAIR_DIAGNOSTIC_DIR = _REPO_ROOT / "reports/repair_diagnostic_20260729T162748Z"

MEANINGFUL_THRESHOLD = 0.01  # matches the threshold used throughout this research thread


# ---------------------------------------------------------------------------
# Part 1: unified per-configuration evidence table
# ---------------------------------------------------------------------------


def _row(**kwargs) -> dict:
    """A unified-schema row; missing fields default to None (NaN in the CSV)."""
    schema = [
        "source_study",
        "paper_track",
        "dataset",
        "provider_or_ranker_family",
        "candidate_pool_size",
        "normalization_method",
        "construction_rule",
        "vote_semantics",
        "extraction_method",
        "repair_method",
        "n_edges_or_density",
        "cyclicity_indicator",
        "scc_stats",
        "fas_or_removed_weight_objective",
        "ndcg_cutoff",
        "ndcg_value",
        "map_value",
        "mrr_value",
        "paired_delta",
        "ci_lower",
        "ci_upper",
        "n_queries",
        "practical_significance_decision",
        "notes",
    ]
    out = dict.fromkeys(schema)
    out.update(kwargs)
    return out


def build_from_calibrated_core() -> list[dict]:
    """JDIQ backbone: construction -> structure -> repair effect, primary protocol."""
    structure = pd.read_csv(CALIBRATED_CORE / "table_primary_graph_structure.csv")
    effects = pd.read_csv(CALIBRATED_CORE / "table_primary_repair_effects.csv")
    macro = pd.read_csv(CALIBRATED_CORE / "table_primary_macro_method_comparison.csv")
    help_harm = pd.read_csv(CALIBRATED_CORE / "table_primary_help_harm_counts.csv")

    rows: list[dict] = []
    graph_methods = {"copeland_graph", "balance_graph", "markov_graph"}
    for _, s in structure.iterrows():
        matching_effects = effects[
            (effects.dataset == s.dataset)
            & (effects.protocol == s.protocol)
            & (effects.regime == s.regime)
        ]
        for _, e in matching_effects.iterrows():
            base_method = str(e.method_key).replace("_repaired", "")
            if base_method not in graph_methods:
                continue  # skip fusion/hybrid rows here; captured separately in baseline table
            hh = help_harm[
                (help_harm.dataset == s.dataset)
                & (help_harm.protocol == s.protocol)
                & (help_harm.regime == s.regime)
                & (help_harm.pair_name == base_method)
            ]
            n = int(hh.common_query_count.iloc[0]) if len(hh) else None
            decision = (
                "not_meaningful"
                if abs(e.repaired_minus_unrepaired_mean_delta_ndcg) < MEANINGFUL_THRESHOLD
                else "meaningful"
            )
            rows.append(
                _row(
                    source_study="JDIQ_backbone_construction_and_repair",
                    paper_track="JDIQ_2026",
                    dataset=s.dataset,
                    provider_or_ranker_family="classical_multi_ranker_fusion",
                    candidate_pool_size=s.mean_candidate_count,
                    normalization_method=s.calibration,
                    construction_rule=s.regime,
                    vote_semantics=s.protocol,
                    extraction_method=base_method,
                    repair_method="greedy_mwfas",
                    n_edges_or_density=s.graph_density,
                    cyclicity_indicator=s.cyclic_query_pct,
                    scc_stats=s.mean_largest_scc,
                    fas_or_removed_weight_objective=s.mean_normalized_fas_weight_removed,
                    ndcg_cutoff=10,
                    ndcg_value=e.mean_ndcg_at_k,
                    paired_delta=e.repaired_minus_unrepaired_mean_delta_ndcg,
                    n_queries=n,
                    practical_significance_decision=decision,
                    notes="repaired_minus_unrepaired at the primary_minmax_retention_matched protocol",  # noqa: E501
                )
            )

    # Macro method ranking (the "strongest baseline" evidence)
    for _, m in macro[
        (macro.protocol == "primary_minmax_retention_matched") & (macro.regime == "ms1")
    ].iterrows():
        rows.append(
            _row(
                source_study="JDIQ_backbone_macro_method_comparison",
                paper_track="JDIQ_2026",
                dataset="ALL_4_macro",
                provider_or_ranker_family="classical_multi_ranker_fusion",
                normalization_method="minmax_retention_matched",
                construction_rule="ms1",
                extraction_method=m.method_key,
                ndcg_cutoff=10,
                ndcg_value=m.dataset_macro_mean_ndcg,
                n_queries=None,
                practical_significance_decision=f"rank_{int(m.average_method_rank)}_of_14",
                notes="dataset-macro mean nDCG@10, primary protocol, ms1 regime",
            )
        )
    return rows


def build_from_headroom_419() -> list[dict]:
    tbl = pd.read_csv(HEADROOM_419 / "manuscript_tables/table_3_oracle_headroom.csv")
    rows = []
    for _, r in tbl.iterrows():
        decision = "meaningful" if r.headroom >= MEANINGFUL_THRESHOLD else "not_meaningful"
        rows.append(
            _row(
                source_study="repository_scale_headroom_419",
                paper_track="negative_result_2026",
                dataset=r.slice,
                extraction_method="copeland_graph",
                repair_method="greedy_or_exact_mwfas (mixed)",
                ndcg_cutoff="mixed(marginalized)",
                paired_delta=r.headroom,
                ci_lower=r.ci_lower,
                ci_upper=r.ci_upper,
                n_queries=r.n,
                practical_significance_decision=decision,
                notes="oracle headroom = mean(max(preserve,repair)) - max(mean(preserve),mean(repair))",  # noqa: E501
            )
        )
    return rows


def build_from_exact_ilp() -> list[dict]:
    struct = pd.read_csv(EXACT_ILP / "structural_per_query.csv")
    struct_agg = struct.groupby(["dataset", "regime"], as_index=False).agg(
        n_edges=("n_edges_pre_repair", "mean"),
        frac_cyclic=("is_cyclic_pre_repair", "mean"),
        greedy_weight_removed=("greedy_weight_removed", "mean"),
        ilp_weight_removed=("ilp_weight_removed", "mean"),
        n=("query_id", "count"),
    )
    retrieval = pd.read_csv(EXACT_ILP / "retrieval_metric_paired_per_query.csv")
    rows = []
    for _, s in struct_agg.iterrows():
        sub = retrieval[
            (retrieval.dataset == s.dataset)
            & (retrieval.regime == s.regime)
            & (retrieval.metric == "nDCG@10")
        ]
        if sub.empty:
            continue
        mean_delta = float((sub.ilp_scip - sub.greedy).mean())
        decision = "not_meaningful" if abs(mean_delta) < MEANINGFUL_THRESHOLD else "meaningful"
        rows.append(
            _row(
                source_study="exact_ilp_vs_greedy_real_data",
                paper_track="JDIQ_2026",
                dataset=s.dataset,
                extraction_method="copeland/balance/markov (pooled)",
                repair_method="exact_scip_minus_greedy",
                n_edges_or_density=s.n_edges,
                cyclicity_indicator=s.frac_cyclic,
                fas_or_removed_weight_objective=s.ilp_weight_removed - s.greedy_weight_removed,
                ndcg_cutoff=10,
                paired_delta=mean_delta,
                n_queries=int(s.n),
                practical_significance_decision=decision,
                notes=f"regime={s.regime}; mean greedy weight removed={s.greedy_weight_removed:.4f}, "  # noqa: E501
                f"mean exact weight removed={s.ilp_weight_removed:.4f}",
            )
        )
    return rows


def build_from_pool_cutoff() -> list[dict]:
    """NOTE: `holm_active_ms1_family`/`bh_active_ms1_family` are Holm/BH-
    ADJUSTED P-VALUES (float, NaN outside the "active ms1 family"), not
    booleans -- despite the boolean-sounding name. `series == True` on a
    float column would silently match rows where the p-value happens to
    equal exactly 1.0 (pandas casts True->1.0), which is the OPPOSITE of
    "significant" and was caught and fixed here after producing a spurious
    "24/216 Holm-significant" result that contradicted the manuscript's
    documented 0/110."""
    stats_df = pd.read_csv(POOL_CUTOFF / "pool_cutoff_statistics.csv")
    active = stats_df[stats_df.holm_active_ms1_family.notna()]
    rows = []
    for cutoff, grp in active.groupby("metric_cutoff"):
        n_sig = int((grp.holm_active_ms1_family < 0.05).sum())
        decision = "meaningful" if n_sig > 0 else "not_meaningful"
        rows.append(
            _row(
                source_study="larger_pool_greedy_multi_cutoff",
                paper_track="JDIQ_2026",
                dataset="ALL_4_pooled",
                repair_method="greedy_mwfas",
                ndcg_cutoff=int(cutoff) if pd.notna(cutoff) else None,
                paired_delta=float(grp.mean_delta.mean()),
                n_queries=int(grp.n_paired_queries.sum()),
                practical_significance_decision=f"{decision} ({n_sig}/{len(grp)} Holm-significant cells)",  # noqa: E501
                notes="larger-pool (P>k) family, active ms1 regime (Holm-adjusted p-value column, not boolean)",  # noqa: E501
            )
        )
    return rows


def build_from_baseline_fairness() -> list[dict]:
    rows = []
    larger = pd.read_csv(BASELINE_FAIRNESS / "exact_larger_pool_family_statistics.csv")
    n_sig = int((larger["holm_significant_at_0.05"] == True).sum())  # noqa: E712
    rows.append(
        _row(
            source_study="larger_pool_exact_repair",
            paper_track="JDIQ_2026",
            dataset="ALL_4_pooled",
            repair_method="exact_scip_mwfas",
            paired_delta=float(larger.mean_delta.mean()),
            n_queries=int(larger.n_paired_queries.sum()),
            practical_significance_decision=f"{'meaningful' if n_sig else 'not_meaningful'} ({n_sig}/{len(larger)} Holm-significant)",  # noqa: E501
            notes="larger-pool family, exact SCIP repair vs. unrepaired, cutoffs 5&10 pooled",
        )
    )
    baseline = pd.read_csv(BASELINE_FAIRNESS / "baseline_targeted_tests_primary_canonical.csv")
    for _, b in baseline.iterrows():
        rows.append(
            _row(
                source_study="baseline_fairness_rrf_combsum_vs_repair",
                paper_track="JDIQ_2026",
                dataset=b.dataset,
                provider_or_ranker_family=b.baseline_method,
                extraction_method=b.graph_method,
                repair_method="hybrid_repaired_copeland",
                paired_delta=b.mean_delta,
                ci_lower=b.bca_ci_low,
                ci_upper=b.bca_ci_high,
                n_queries=int(b.n_paired_queries),
                practical_significance_decision="not_meaningful (0/8 Holm-significant)"
                if not b["holm_significant_at_0.05"]
                else "meaningful",
                notes=f"delta = {b.baseline_method} - hybrid_repaired_copeland, canonical (rrf_union_topk) pool",  # noqa: E501
            )
        )
    return rows


def build_from_session_studies() -> list[dict]:
    rows = []
    frontier = json.loads((REPAIR_FRONTIER_DIR / "FINAL_SUMMARY.json").read_text())
    d = frontier["discovery"]
    rows.append(
        _row(
            source_study="repair_frontier_real_llm",
            paper_track="this_session",
            dataset="scidocs+fiqa",
            provider_or_ranker_family="azure/gemini/cohere/fireworks/aggregate",
            candidate_pool_size="6/8/10",
            extraction_method="richer_repair_candidate_frontier",
            repair_method="scc_local_protected_confidence_weighted",
            fas_or_removed_weight_objective=None,
            ndcg_cutoff=10,
            paired_delta=d["mean_headroom"],
            ci_lower=d["headroom_ci"]["lower"],
            ci_upper=d["headroom_ci"]["upper"],
            n_queries=d["n_queries"],
            practical_significance_decision="not_meaningful"
            if d["mean_headroom"] < MEANINGFUL_THRESHOLD
            else "meaningful",
            notes=f"decision={d['decision']}",
        )
    )
    extraction = json.loads((EXTRACTION_DIR / "FINAL_SUMMARY.json").read_text())
    for name, s in extraction["stats_by_extractor"].items():
        if name in ("incumbent", "copeland"):
            continue
        rows.append(
            _row(
                source_study="extraction_method_comparison_real_llm",
                paper_track="this_session",
                dataset="scidocs+fiqa",
                provider_or_ranker_family="azure/gemini/cohere/fireworks/aggregate",
                extraction_method=name,
                ndcg_cutoff=10,
                paired_delta=s["mean_delta"],
                ci_lower=s["headroom_ci"]["lower"],
                ci_upper=s["headroom_ci"]["upper"],
                n_queries=s["n"],
                practical_significance_decision="not_meaningful"
                if abs(s["mean_delta"]) < MEANINGFUL_THRESHOLD
                else "meaningful",
                notes=f"win/tie/loss={s['n_win']}/{s['n_tie']}/{s['n_loss']}",
            )
        )
    diag = json.loads((REPAIR_DIAGNOSTIC_DIR / "FINAL_SUMMARY.json").read_text())
    rows.append(
        _row(
            source_study="repair_predictability_diagnostic_real_llm",
            paper_track="this_session",
            dataset="scidocs+fiqa",
            provider_or_ranker_family="azure/gemini/cohere/fireworks/aggregate",
            repair_method="greedy_mwfas",
            ndcg_cutoff=10,
            paired_delta=diag["overall_delta_ci"]["lower"] / 2
            + diag["overall_delta_ci"]["upper"] / 2,
            ci_lower=diag["overall_delta_ci"]["lower"],
            ci_upper=diag["overall_delta_ci"]["upper"],
            n_queries=diag["n_query_graphs"],
            practical_significance_decision=f"not_meaningful; net negative (decision={diag['decision']})",  # noqa: E501
            notes=f"outcome counts: {diag['outcome_group_stats']}",
        )
    )
    return rows


# ---------------------------------------------------------------------------
# Part 2: structure vs. utility association analysis
# ---------------------------------------------------------------------------


def structure_utility_from_calibrated_core() -> list[dict]:
    """Aggregated (dataset x protocol x regime) join -- the JDIQ backbone's
    own structure and repair-effect tables share this exact key."""
    structure = pd.read_csv(CALIBRATED_CORE / "table_primary_graph_structure.csv")
    effects = pd.read_csv(CALIBRATED_CORE / "table_primary_repair_effects.csv")
    effects_copeland = effects[effects.method_key == "copeland_graph_repaired"]
    merged = structure.merge(effects_copeland, on=["dataset", "protocol", "regime"], how="inner")

    rows = []
    feature_cols = [
        "cyclic_query_pct",
        "mean_largest_scc",
        "mean_fas_weight_removed",
        "mean_normalized_fas_weight_removed",
        "graph_density",
    ]
    outcome = "repaired_minus_unrepaired_mean_delta_ndcg"
    n = len(merged)
    for feat in feature_cols:
        if n < 8:
            rows.append(
                dict(
                    analysis="pooled_dataset_protocol_regime",
                    feature=feat,
                    outcome=outcome,
                    n=n,
                    pearson_r=None,
                    pearson_p=None,
                    spearman_rho=None,
                    spearman_p=None,
                    note="n<8: sample size inadequate for a reported correlation",
                )
            )
            continue
        pear_r, pear_p = stats.pearsonr(merged[feat], merged[outcome])
        spear_r, spear_p = stats.spearmanr(merged[feat], merged[outcome])
        rows.append(
            dict(
                analysis="pooled_dataset_protocol_regime",
                feature=feat,
                outcome=outcome,
                n=n,
                pearson_r=pear_r,
                pearson_p=pear_p,
                spearman_rho=spear_r,
                spearman_p=spear_p,
                note="descriptive association across (dataset,protocol,regime) configuration means -- NOT causal, NOT per-query",  # noqa: E501
            )
        )

    # Grouped-by-dataset check (aggregation-artifact / Simpson's-paradox screen):
    # does the pooled sign hold within each dataset separately?
    for feat in feature_cols:
        per_dataset_signs = []
        for dataset, g in merged.groupby("dataset"):
            if len(g) < 5:
                continue
            r, _ = stats.pearsonr(g[feat], g[outcome])
            per_dataset_signs.append((dataset, r))
        if len(per_dataset_signs) >= 2:
            signs = [np.sign(r) for _, r in per_dataset_signs]
            consistent = len(set(signs)) == 1
            rows.append(
                dict(
                    analysis="within_dataset_sign_check",
                    feature=feat,
                    outcome=outcome,
                    n=len(per_dataset_signs),
                    pearson_r=float(np.mean([r for _, r in per_dataset_signs])),
                    pearson_p=None,
                    spearman_rho=None,
                    spearman_p=None,
                    note=(
                        "sign_consistent_across_datasets="
                        + str(consistent)
                        + "; per-dataset r="
                        + ", ".join(f"{d}:{r:.3f}" for d, r in per_dataset_signs)
                        + (
                            ""
                            if consistent
                            else " -- WARNING: sign differs across datasets; the pooled "
                            "correlation above may be an aggregation artifact (Simpson's-paradox-style); "  # noqa: E501
                            "do not report the pooled number without this caveat"
                        )
                    ),
                )
            )
    return rows


def structure_utility_from_pool_cutoff() -> list[dict]:
    """Per-query-row analysis: pool_cutoff_pair_metrics.csv has structural
    features and delta_ndcg in the SAME row, at real per-query granularity,
    across pool_size x metric_cutoff configs per query -- enabling a genuine
    within-query (across configs) vs. pooled (across all rows) comparison."""
    df = pd.read_csv(POOL_CUTOFF / "pool_cutoff_pair_metrics.csv")
    df = df[df.pair_family == "graph"].copy()
    rows = []
    feature = "removed_weight_fraction"
    outcome = "delta_ndcg"
    df = df.dropna(subset=[feature, outcome])
    n = len(df)
    if n >= 30:
        pear_r, pear_p = stats.pearsonr(df[feature], df[outcome])
        spear_r, spear_p = stats.spearmanr(df[feature], df[outcome])
        rows.append(
            dict(
                analysis="pooled_per_query_row",
                feature=feature,
                outcome=outcome,
                n=n,
                pearson_r=pear_r,
                pearson_p=pear_p,
                spearman_rho=spear_r,
                spearman_p=spear_p,
                note="pooled across all queries x pool_size x cutoff rows -- treats repeated "
                "queries as independent (pseudo-replication); see within_query row for the correction",  # noqa: E501
            )
        )
    else:
        rows.append(
            dict(
                analysis="pooled_per_query_row",
                feature=feature,
                outcome=outcome,
                n=n,
                pearson_r=None,
                pearson_p=None,
                spearman_rho=None,
                spearman_p=None,
                note="n<30: inadequate for a reported pooled correlation",
            )
        )

    # Within-query: for queries with >=5 distinct config rows, correlate
    # feature vs outcome WITHIN that query's rows, then average (Fisher-z).
    within_r = []
    for qid, g in df.groupby("query_id"):
        if len(g) < 5 or g[feature].std() < 1e-9:
            continue
        r, _ = stats.pearsonr(g[feature], g[outcome])
        if np.isfinite(r) and abs(r) < 1:
            within_r.append(r)
    if len(within_r) >= 5:
        z = np.mean([np.arctanh(np.clip(r, -0.999, 0.999)) for r in within_r])
        avg_within_r = float(np.tanh(z))
        rows.append(
            dict(
                analysis="within_query_fisher_z_average",
                feature=feature,
                outcome=outcome,
                n=len(within_r),
                pearson_r=avg_within_r,
                pearson_p=None,
                spearman_rho=None,
                spearman_p=None,
                note=f"averaged within-query correlation across {len(within_r)} queries with >=5 configs each; "  # noqa: E501
                f"compare sign/magnitude to the pooled row above -- large divergence flags an aggregation artifact",  # noqa: E501
            )
        )
    else:
        rows.append(
            dict(
                analysis="within_query_fisher_z_average",
                feature=feature,
                outcome=outcome,
                n=len(within_r),
                pearson_r=None,
                pearson_p=None,
                spearman_rho=None,
                spearman_p=None,
                note="fewer than 5 queries had >=5 distinct configs with feature variance -- inadequate for within-query estimate",  # noqa: E501
            )
        )
    return rows


# ---------------------------------------------------------------------------
# Part 3: baseline verification
# ---------------------------------------------------------------------------


def build_baseline_verification() -> list[dict]:
    macro = pd.read_csv(CALIBRATED_CORE / "table_primary_macro_method_comparison.csv")
    ms1 = (
        macro[(macro.protocol == "primary_minmax_retention_matched") & (macro.regime == "ms1")]
        .sort_values("dataset_macro_mean_ndcg", ascending=False)
        .reset_index(drop=True)
    )
    ms1["overall_rank"] = ms1.index + 1

    method_meta = {
        "prior_only": ("individual_ranker", "Prior (single ranker, no fusion)"),
        "rrf": ("rrf", "Reciprocal Rank Fusion (Cormack et al. 2009)"),
        "combsum": (
            "normalized_score_fusion",
            "CombSUM, min-max per-(query,ranker) normalized (Fox & Shaw)",
        ),
        "borda_fuse": ("graph_free_rank_fusion", "Borda-style fusion"),
    }
    rows = []
    for key, (category, desc) in method_meta.items():
        match = ms1[ms1.method_key == key]
        if match.empty:
            rows.append(
                dict(
                    baseline_category=category,
                    method_key=key,
                    description=desc,
                    implemented=False,
                    evaluated=False,
                    macro_ndcg_at_10=None,
                    overall_rank_of_14=None,
                    same_candidate_pool_as_graph_methods="N/A",
                    cutoff_aligned="N/A",
                    missing_doc_handling="N/A",
                    manuscript_prominence="MISSING -- not found in table_primary_macro_method_comparison.csv",  # noqa: E501
                )
            )
            continue
        r = match.iloc[0]
        rows.append(
            dict(
                baseline_category=category,
                method_key=key,
                description=desc,
                implemented=True,
                evaluated=True,
                macro_ndcg_at_10=r.dataset_macro_mean_ndcg,
                overall_rank_of_14=int(r.overall_rank),
                same_candidate_pool_as_graph_methods=(
                    "YES -- query_method_metrics.csv places every method_key (fusion baseline AND graph/"  # noqa: E501
                    "repaired-graph) for a fixed (pool_id,dataset,regime) in the SAME file/row set, so they "  # noqa: E501
                    "share the identical candidate pool by construction"
                ),
                cutoff_aligned="YES -- ndcg_at_k column is a single fixed cutoff (10) shared by every method_key in the same file",  # noqa: E501
                missing_doc_handling=(
                    "Uniform: build_candidate_qrels_reference() (qrels_reference.py) assigns relevance 0 to "  # noqa: E501
                    "unjudged candidates for nDCG/MAP/MRR for ALL methods; RRF/CombSUM code independently "  # noqa: E501
                    "documents 'missing documents contribute 0' for that ranker's score -- no baseline is "  # noqa: E501
                    "differentially advantaged"
                ),
                manuscript_prominence=(
                    f"YES -- main.tex explicitly states CombSUM={0.554:.3f} best, RRF={0.546:.3f} close behind, "  # noqa: E501
                    "'CombSUM and RRF remain competitive'; repaired graph methods never win the macro comparison"  # noqa: E501
                )
                if key in ("rrf", "combsum")
                else "Present in tables but not separately named in main.tex prose",
            )
        )
    return rows


# ---------------------------------------------------------------------------
# Part 4: cutoff robustness
# ---------------------------------------------------------------------------


def build_cutoff_robustness() -> list[dict]:
    """See build_from_pool_cutoff()'s docstring: holm/bh_active_ms1_family
    are adjusted p-values, not booleans -- compare with `< 0.05`, and
    restrict to the rows where the column is populated (the active family)."""
    rows = []
    stats_df = pd.read_csv(POOL_CUTOFF / "pool_cutoff_statistics.csv")
    active = stats_df[stats_df.holm_active_ms1_family.notna()]
    for cutoff, grp in active.groupby("metric_cutoff"):
        n_sig_holm = int((grp.holm_active_ms1_family < 0.05).sum())
        n_sig_bh = int((grp.bh_active_ms1_family < 0.05).sum())
        rows.append(
            dict(
                source="larger_pool_greedy (final_revision_task1_pool_cutoff)",
                metric_cutoff=int(cutoff) if pd.notna(cutoff) else None,
                n_cells=len(grp),
                n_holm_significant=n_sig_holm,
                n_bh_significant=n_sig_bh,
                mean_delta=float(grp.mean_delta.mean()),
                conclusion_changes_at_this_cutoff=(n_sig_holm > 0),
            )
        )
    larger_exact = pd.read_csv(BASELINE_FAIRNESS / "exact_larger_pool_family_statistics.csv")
    n_sig = int((larger_exact["holm_significant_at_0.05"] == True).sum())  # noqa: E712
    rows.append(
        dict(
            source="larger_pool_exact_scip (final_revision_task4)",
            metric_cutoff="5_and_10_pooled (cutoff not separated in this family's stats file)",
            n_cells=len(larger_exact),
            n_holm_significant=n_sig,
            n_bh_significant=None,
            mean_delta=float(larger_exact.mean_delta.mean()),
            conclusion_changes_at_this_cutoff=(n_sig > 0),
        )
    )
    retrieval = pd.read_csv(EXACT_ILP / "retrieval_metric_paired_per_query.csv")
    for metric, grp in retrieval.groupby("metric"):
        mean_delta = float((grp.ilp_scip - grp.greedy).mean())
        rows.append(
            dict(
                source="exact_ilp_vs_greedy (exact_open_source_ilp_repair_investigation)",
                metric_cutoff=metric,
                n_cells=len(grp.groupby(["dataset", "regime"])),
                n_holm_significant=None,
                n_bh_significant=None,
                mean_delta=mean_delta,
                conclusion_changes_at_this_cutoff=(abs(mean_delta) >= MEANINGFUL_THRESHOLD),
            )
        )
    return rows


# ---------------------------------------------------------------------------
# Part 5: publication table + figure
# ---------------------------------------------------------------------------


def write_publication_table(output_dir: Path) -> None:
    structure = pd.read_csv(CALIBRATED_CORE / "table_primary_graph_structure.csv")
    effects = pd.read_csv(CALIBRATED_CORE / "table_primary_repair_effects.csv")
    effects_copeland = effects[effects.method_key == "copeland_graph_repaired"]
    merged = structure.merge(effects_copeland, on=["dataset", "protocol", "regime"], how="inner")
    merged = merged[merged.protocol == "primary_minmax_retention_matched"]

    table = (
        merged[
            [
                "dataset",
                "regime",
                "cyclic_query_pct",
                "mean_largest_scc",
                "mean_normalized_fas_weight_removed",
                "repaired_minus_unrepaired_mean_delta_ndcg",
                "helped_query_count",
                "harmed_query_count",
                "unchanged_query_count",
            ]
        ]
        .rename(
            columns={
                "cyclic_query_pct": "frac_cyclic",
                "mean_largest_scc": "mean_largest_scc",
                "mean_normalized_fas_weight_removed": "mean_normalized_repair_objective",
                "repaired_minus_unrepaired_mean_delta_ndcg": "mean_delta_ndcg_at_10",
            }
        )
        .sort_values(["dataset", "regime"])
    )
    table.to_csv(output_dir / "tables" / "publication_table_structure_vs_utility.csv", index=False)

    lines = [
        "| Dataset | Regime | Frac. cyclic | Mean largest SCC | Mean repair objective | Mean ΔnDCG@10 | Helped | Harmed | Unchanged |",  # noqa: E501
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in table.iterrows():
        lines.append(
            f"| {r.dataset} | {r.regime} | {r.frac_cyclic:.3f} | {r.mean_largest_scc:.2f} | "
            f"{r.mean_normalized_repair_objective:.4f} | {r.mean_delta_ndcg_at_10:.5f} | "
            f"{int(r.helped_query_count)} | {int(r.harmed_query_count)} | {int(r.unchanged_query_count)} |"  # noqa: E501
        )
    (output_dir / "tables" / "publication_table_structure_vs_utility.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def write_publication_figure(output_dir: Path) -> None:
    df = pd.read_csv(POOL_CUTOFF / "pool_cutoff_pair_metrics.csv")
    df = df[(df.pair_family == "graph") & (df.metric_cutoff == 10)].dropna(
        subset=["removed_weight_fraction", "delta_ndcg"]
    )

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    ax = axes[0]
    for dataset, g in df.groupby("dataset"):
        ax.scatter(g.removed_weight_fraction, g.delta_ndcg, s=10, alpha=0.4, label=dataset)
    if len(df) >= 2:
        coeffs = np.polyfit(df.removed_weight_fraction, df.delta_ndcg, 1)
        xs = np.linspace(df.removed_weight_fraction.min(), df.removed_weight_fraction.max(), 50)
        ax.plot(
            xs,
            np.polyval(coeffs, xs),
            color="black",
            linewidth=1.5,
            linestyle="--",
            label="linear fit (pooled)",
        )
    ax.axhline(0.0, color="gray", linewidth=0.8)
    ax.set_xlabel("Repair objective (removed weight fraction)")
    ax.set_ylabel("ΔnDCG@10 (repaired − unrepaired)")
    ax.set_title(
        "(a) Structural repair activity vs. retrieval effect\n(per-query, larger-pool study, real qrels)"  # noqa: E501
    )
    ax.legend(fontsize=7, loc="upper right")

    structure = pd.read_csv(CALIBRATED_CORE / "table_primary_graph_structure.csv")
    effects = pd.read_csv(CALIBRATED_CORE / "table_primary_repair_effects.csv")
    effects_copeland = effects[effects.method_key == "copeland_graph_repaired"]
    merged = structure.merge(effects_copeland, on=["dataset", "protocol", "regime"], how="inner")
    merged = merged[merged.protocol == "primary_minmax_retention_matched"]

    ax = axes[1]
    colors = {"ms1": "tab:red", "ms1_drop_mutual": "tab:orange", "ms2": "tab:blue"}
    for regime, g in merged.groupby("regime"):
        ax.scatter(
            g.cyclic_query_pct,
            g.repaired_minus_unrepaired_mean_delta_ndcg,
            s=60,
            color=colors.get(regime, "gray"),
            label=regime,
        )
    ax.axhline(0.0, color="gray", linewidth=0.8)
    ax.axhline(
        MEANINGFUL_THRESHOLD,
        color="green",
        linewidth=0.8,
        linestyle=":",
        label=f"meaningful threshold ({MEANINGFUL_THRESHOLD})",
    )
    ax.axhline(-MEANINGFUL_THRESHOLD, color="green", linewidth=0.8, linestyle=":")
    ax.set_xlabel("Fraction of queries with a cyclic graph")
    ax.set_ylabel("Mean ΔnDCG@10 (repaired − unrepaired)")
    ax.set_title("(b) Cyclicity vs. repair effect\n(aggregated dataset x regime, JDIQ backbone)")
    ax.legend(fontsize=7, loc="upper right")

    fig.suptitle(
        "Structure vs. utility: repairing more inconsistency does not buy more retrieval effectiveness",  # noqa: E501
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(output_dir / "figures" / "structure_vs_utility.png", dpi=200)
    plt.close(fig)

    script_src = Path(__file__).read_text(encoding="utf-8")
    (output_dir / "figures" / "structure_vs_utility_SOURCE.py").write_text(
        "# Extracted from write_publication_figure() in scripts/run_ir_evidence_audit.py\n"
        "# Re-running requires the same source CSVs listed in this script's module docstring.\n\n"
        + script_src,
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run(output_dir: Path, *, allow_overwrite: bool = False) -> dict:
    protect_canonical_output(output_dir, allow_overwrite=allow_overwrite)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "tables").mkdir(exist_ok=True)
    (output_dir / "figures").mkdir(exist_ok=True)

    unified_rows: list[dict] = []
    unified_rows += build_from_calibrated_core()
    unified_rows += build_from_headroom_419()
    unified_rows += build_from_exact_ilp()
    unified_rows += build_from_pool_cutoff()
    unified_rows += build_from_baseline_fairness()
    unified_rows += build_from_session_studies()
    unified_df = pd.DataFrame(unified_rows)
    unified_df.to_csv(output_dir / "unified_configuration_results.csv", index=False)

    assoc_rows = structure_utility_from_calibrated_core() + structure_utility_from_pool_cutoff()
    pd.DataFrame(assoc_rows).to_csv(output_dir / "structure_utility_associations.csv", index=False)

    baseline_rows = build_baseline_verification()
    pd.DataFrame(baseline_rows).to_csv(output_dir / "baseline_verification.csv", index=False)

    cutoff_rows = build_cutoff_robustness()
    pd.DataFrame(cutoff_rows).to_csv(output_dir / "cutoff_robustness.csv", index=False)

    write_publication_table(output_dir)
    write_publication_figure(output_dir)

    provenance = collect_provenance(
        generator_script="scripts/run_ir_evidence_audit.py",
        independence_cluster_count=None,
        input_paths=[
            CALIBRATED_CORE, HEADROOM_419, EXACT_ILP, POOL_CUTOFF, BASELINE_FAIRNESS,
            REPAIR_FRONTIER_DIR, EXTRACTION_DIR, REPAIR_DIAGNOSTIC_DIR,
        ],
        config={"meaningful_threshold": MEANINGFUL_THRESHOLD},
        output_paths=[
            output_dir / "unified_configuration_results.csv",
            output_dir / "structure_utility_associations.csv",
            output_dir / "baseline_verification.csv",
            output_dir / "cutoff_robustness.csv",
        ],
    )
    (output_dir / "reproducibility_manifest.json").write_text(
        json.dumps(provenance, indent=2, default=str)
    )

    return {
        "n_unified_rows": len(unified_df),
        "n_association_rows": len(assoc_rows),
        "n_baseline_rows": len(baseline_rows),
        "n_cutoff_rows": len(cutoff_rows),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--allow-overwrite", action="store_true",
        help="Permit writing into a non-empty output directory (default: refuse).",
    )
    args = parser.parse_args()
    try:
        result = run(args.output_dir, allow_overwrite=args.allow_overwrite)
    except CanonicalOutputExistsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, indent=2))
    sys.stdout.flush()
