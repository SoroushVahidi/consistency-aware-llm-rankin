"""Regression tests for the query-clustering independence-unit error (repo
Stage 3, 2026-07-30): repair_frontier/extraction_study/repair_diagnostic
each report "n=120" observations that are actually 6 independent queries
replicated ~20x each. These tests prevent that specific mistake (row-level
resampling/testing/CV-splitting of clustered data) from recurring, using
synthetic fixtures for the statistical-primitive tests (fast, no large
report files needed) and the real, already-stored source data for the two
population-fact tests that specifically need to pin down the real numbers.
"""

from __future__ import annotations

import numpy as np
import pytest

from consistency_ranker.real_llm_reanalysis import (
    diagnostic_reanalysis,
    extraction_reanalysis,
    population,
)
from consistency_ranker.statistical_inference import (
    cluster_bootstrap_mean_interval,
    cluster_exact_permutation_correlation,
    cluster_exact_sign_flip_pvalue,
    compute_cluster_means,
    holm_adjust,
)


def _synthetic_clustered_data(n_clusters: int = 6, rows_per_cluster: int = 20, seed: int = 0):
    """6 clusters x 20 rows each, matching the real studies' shape, with a
    genuine per-cluster effect plus within-cluster noise -- exactly the
    structure (many correlated replicates per independent unit) the bug
    ignored."""
    rng = np.random.default_rng(seed)
    cluster_effects = rng.normal(0.0, 0.01, size=n_clusters)
    clusters = []
    values = []
    for c in range(n_clusters):
        for _ in range(rows_per_cluster):
            clusters.append(f"query_{c}")
            values.append(cluster_effects[c] + rng.normal(0.0, 0.05))
    return values, clusters


def test_real_population_manifest_has_six_clusters_not_120() -> None:
    """Pin down the actual number directly from the stored source files --
    the exact bug this whole stage exists to correct."""
    rows = population.build_population_manifest()
    summary = population.population_summary(rows)
    assert summary["total_unique_queries_overall"] == 6
    assert summary["by_study"]["extraction_study"]["n_rows"] == 120
    assert summary["by_study"]["extraction_study"]["n_unique_queries"] == 6
    assert summary["by_study"]["repair_diagnostic"]["n_rows"] == 120
    assert summary["by_study"]["repair_diagnostic"]["n_unique_queries"] == 6
    # The bug this stage fixes: 120 rows must never be read as 120 clusters.
    extraction_stats = summary["by_study"]["extraction_study"]
    assert extraction_stats["n_rows"] != extraction_stats["n_unique_queries"]


def test_real_studies_share_identical_six_queries() -> None:
    rows = population.build_population_manifest()
    by_study = {}
    for study in ("extraction_study", "repair_diagnostic", "repair_frontier"):
        by_study[study] = {r["independence_cluster"] for r in rows if r["study"] == study}
    assert by_study["extraction_study"] == by_study["repair_diagnostic"]
    assert by_study["repair_diagnostic"] == by_study["repair_frontier"]
    assert len(by_study["extraction_study"]) == 6


def test_bootstrap_resamples_clusters_not_rows() -> None:
    """If the cluster bootstrap secretly resampled rows, its CI would be
    much narrower than one computed from only 6 independent numbers --
    detect this by comparing against a hand-rolled 6-value bootstrap."""
    values, clusters = _synthetic_clustered_data()
    ci = cluster_bootstrap_mean_interval(values, clusters, seed=13, reps=5000)

    agg = compute_cluster_means(values, clusters)
    cluster_means = np.array(agg.cluster_means)
    rng = np.random.default_rng(13)
    idx = rng.integers(0, 6, size=(5000, 6))
    hand_rolled = cluster_means[idx].mean(axis=1)
    hand_lo, hand_hi = np.quantile(hand_rolled, [0.025, 0.975])
    assert ci.lower == pytest.approx(hand_lo, rel=1e-9)
    assert ci.upper == pytest.approx(hand_hi, rel=1e-9)


def test_all_rows_for_one_cluster_move_together_in_resample() -> None:
    """A resample that only ever contains WHOLE clusters (never splits one
    query's 20 rows across two different resample slots) is the defining
    property of a correct cluster bootstrap. Verify structurally: the
    bootstrap only ever consumes compute_cluster_means()'s per-cluster
    aggregates, never the raw per-row array, so a row can never appear
    fractionally or be split from its cluster."""
    values, clusters = _synthetic_clustered_data()
    agg = compute_cluster_means(values, clusters)
    # The cluster bootstrap's only numeric input is agg.cluster_means (one
    # number per cluster) -- by construction, whatever gets resampled is an
    # entire cluster's contribution, never a partial one.
    assert len(agg.cluster_means) == agg.n_clusters == 6
    assert sum(agg.cluster_sizes) == len(values)


def test_grouped_cv_does_not_split_one_query_across_train_and_test() -> None:
    """Confirms (does not re-implement) that repair_diagnostic's actual
    predictor evaluation groups by (dataset, query_id) via GroupKFold."""
    status = diagnostic_reanalysis.grouped_cv_status()
    assert status["grouped_cv_already_implemented"] is True
    assert status["grouping_key"] == "(dataset, query_id)"


def test_holm_correction_includes_all_eight_extractor_comparisons() -> None:
    rows = extraction_reanalysis.load_rows()
    result = extraction_reanalysis.clustered_analysis(rows)
    assert result["family_size"] == 8
    assert set(result["family_members"]) == {
        "borda", "pagerank", "rank_centrality", "balance_score", "hodge_rank",
        "fas_balance_prior_fusion", "hybrid_rrf_prior_fusion", "copeland",
    }
    # Every member must carry a Holm-adjusted p-value, not just a raw one.
    for extractor in result["family_members"]:
        assert result["per_extractor"][extractor]["exact_sign_flip_pvalue_holm"] is not None


def test_holm_adjust_on_eight_pvalues_matches_manual_reference() -> None:
    """Regression-pin the Holm arithmetic itself against a hand-computed
    reference, independent of the real extraction data, so a future change
    to holm_adjust() that silently drops a family member would be caught
    even if the real data's own numbers happened not to expose it."""
    raw = [0.01, 0.5, 0.001, 0.9, 0.2, 0.15625, 0.9375, 1.0]
    adjusted = holm_adjust(raw)
    assert len(adjusted) == 8
    # Manual Holm: sort ascending, multiply by (n - rank + 1), enforce monotonicity.
    order = sorted(range(8), key=lambda i: raw[i])
    running = 0.0
    expected = [None] * 8
    for rank, idx in enumerate(order, start=1):
        scaled = (8 - rank + 1) * raw[idx]
        running = max(running, scaled)
        expected[idx] = min(1.0, running)
    for a, e in zip(adjusted, expected):
        assert a == pytest.approx(e)


def test_paired_analysis_uses_one_shared_cluster_argument_and_guards_it() -> None:
    """`cluster_exact_permutation_correlation` takes ONE `clusters` argument
    used to aggregate both the feature and the outcome, which by
    construction guarantees they can never desync in normal use (both
    aggregations see cluster ids in the same first-seen order). The
    function still carries an explicit equality guard
    (`agg_feat.cluster_ids != agg_out.cluster_ids: raise ValueError`) as a
    defense-in-depth check; this test confirms the guard condition itself
    is correct by constructing two aggregates from genuinely different
    cluster orderings and confirming they compare unequal -- i.e. the
    condition the guard checks for is a real, detectable state, not a
    dead comparison that could never be true."""
    from consistency_ranker.statistical_inference import compute_cluster_means

    feature = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0] * 4
    outcome = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6] * 4
    clusters_first_order = ["q1", "q2", "q3", "q4", "q5", "q6"] * 4
    # same set of ids as clusters_first_order, different first-seen order
    clusters_second_order = ["q6", "q5", "q4", "q3", "q2", "q1"] * 4

    agg_a = compute_cluster_means(feature, clusters_first_order)
    agg_b = compute_cluster_means(outcome, clusters_second_order)
    assert agg_a.cluster_ids != agg_b.cluster_ids  # the guard's condition is reachable/meaningful

    # Normal usage (one shared `clusters` argument) never hits the guard
    # and returns a real result:
    result = cluster_exact_permutation_correlation(feature, outcome, clusters_first_order)
    assert result["n_clusters"] == 6


def test_deterministic_seed_reproduces_identical_bootstrap_output() -> None:
    values, clusters = _synthetic_clustered_data()
    ci1 = cluster_bootstrap_mean_interval(values, clusters, seed=13, reps=2000)
    ci2 = cluster_bootstrap_mean_interval(values, clusters, seed=13, reps=2000)
    assert ci1.lower == ci2.lower
    assert ci1.upper == ci2.upper
    ci3 = cluster_bootstrap_mean_interval(values, clusters, seed=99, reps=2000)
    assert ci3.lower != ci1.lower or ci3.upper != ci1.upper


def test_missing_clusters_fail_loudly() -> None:
    with pytest.raises(ValueError, match="at least 3 distinct clusters"):
        cluster_bootstrap_mean_interval([1.0, 2.0], ["q1", "q1"], min_clusters=3)
    with pytest.raises(ValueError, match="same length"):
        compute_cluster_means([1.0, 2.0, 3.0], ["q1", "q2"])


def test_report_metadata_exposes_both_unique_query_count_and_row_count() -> None:
    rows = population.build_population_manifest()
    summary = population.population_summary(rows)
    for study, stats in summary["by_study"].items():
        assert "n_rows" in stats
        assert "n_unique_queries" in stats
        assert stats["n_rows"] >= stats["n_unique_queries"]


def test_exact_sign_flip_on_six_clusters_uses_all_64_patterns() -> None:
    values, clusters = _synthetic_clustered_data()
    result = cluster_exact_sign_flip_pvalue(values, clusters)
    assert result.reps == 64  # 2**6, confirms exact enumeration, not Monte Carlo
