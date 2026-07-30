"""Tests for the bounded extraction-vs-repair study."""

from __future__ import annotations

import networkx as nx
import numpy as np

from consistency_ranker.baseline_ranking import hodge_rank_ranking, hodge_rank_scores
from consistency_ranker.extraction_study.decision import decide
from consistency_ranker.extraction_study.evaluation import (
    QueryGraphResult,
    breakdown_by,
    compute_extractor_stats,
    evaluate_unit_graph,
    full_breakdowns,
    outlier_sensitivity,
)
from consistency_ranker.extraction_study.extractors import EXTRACTORS, extract_all
from consistency_ranker.extraction_study.selection import (
    best_single_fixed_extractor,
    build_predictive_rows,
    evaluate_predictive_selector,
)


def _result(
    dataset, query_id, provider, pool_size, is_cyclic, ndcg_by_extractor, incumbent_ndcg=None
):
    resolved_incumbent_ndcg = (
        incumbent_ndcg if incumbent_ndcg is not None else ndcg_by_extractor["incumbent"]
    )
    return QueryGraphResult(
        key=(dataset, query_id, "src", "var", provider),
        dataset=dataset,
        query_id=query_id,
        provider=provider,
        pool_size=pool_size,
        is_cyclic=is_cyclic,
        n_nodes=5,
        n_edges=8,
        graph_density=0.4,
        ndcg_by_extractor=ndcg_by_extractor,
        incumbent_ndcg=resolved_incumbent_ndcg,
    )


class TestHodgeRank:
    def test_transitive_chain_recovers_exact_potentials(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0)
        g.add_edge("b", "c", weight=1.0)
        scores = hodge_rank_scores(g)
        assert scores["a"] > scores["b"] > scores["c"]
        assert np.isclose(scores["a"] - scores["b"], 1.0, atol=1e-9)
        assert np.isclose(scores["b"] - scores["c"], 1.0, atol=1e-9)
        assert hodge_rank_ranking(g) == ["a", "b", "c"]

    def test_symmetric_cycle_is_perfectly_tied(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0)
        g.add_edge("b", "c", weight=1.0)
        g.add_edge("c", "a", weight=1.0)
        scores = hodge_rank_scores(g)
        vals = list(scores.values())
        assert max(vals) - min(vals) < 1e-9

    def test_single_node_graph_does_not_crash(self):
        g = nx.DiGraph()
        g.add_node("a")
        assert hodge_rank_ranking(g) == ["a"]


class TestExtractorRegistry:
    def test_incumbent_and_copeland_are_identical(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=2.0)
        g.add_edge("b", "c", weight=1.0)
        g.add_edge("c", "a", weight=1.0)
        rankings = extract_all(g)
        assert rankings["incumbent"] == rankings["copeland"]

    def test_extract_all_covers_every_registered_extractor(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=2.0)
        g.add_edge("b", "c", weight=1.0)
        g.add_edge("c", "a", weight=1.0)
        rankings = extract_all(g)
        assert set(rankings) == set(EXTRACTORS)
        for name, ranking in rankings.items():
            assert set(ranking) == {"a", "b", "c"}, name

    def test_evaluate_unit_graph_ndcg_matches_direct_computation(self):
        from consistency_ranker.evaluation import ndcg_at_k

        g = nx.DiGraph()
        g.add_edge("a", "b", weight=2.0)
        g.add_edge("b", "c", weight=1.0)
        relevance = {"a": 2, "b": 1, "c": 0}
        result = evaluate_unit_graph(
            g, relevance, key=("ds", "q1", "s", "v", "p"), dataset="ds", query_id="q1",
            provider="p", pool_size=3,
        )
        assert result is not None
        expected = ndcg_at_k(["a", "b", "c"], relevance, k=10)
        assert result.ndcg_by_extractor["incumbent"] == expected
        assert result.is_cyclic is False


class TestBreakdownsAndStats:
    def test_win_tie_loss_counts(self):
        results = [
            _result("ds", "q1", "p1", 6, False, {"incumbent": 0.5, "borda": 0.6}),
            _result("ds", "q2", "p1", 6, False, {"incumbent": 0.5, "borda": 0.5}),
            _result("ds", "q3", "p1", 6, False, {"incumbent": 0.5, "borda": 0.4}),
        ]
        stats = compute_extractor_stats(results, "borda")
        assert (stats.n_win, stats.n_tie, stats.n_loss) == (1, 1, 1)
        assert stats.n == 3

    def test_breakdown_by_dataset_and_cyclicity(self):
        results = [
            _result("scidocs", "q1", "azure", 6, False, {"incumbent": 0.5, "borda": 0.6}),
            _result("scidocs", "q2", "azure", 6, True, {"incumbent": 0.5, "borda": 0.5}),
            _result("fiqa", "q3", "gemini", 8, False, {"incumbent": 0.5, "borda": 0.4}),
        ]
        by_dataset = breakdown_by(results, "borda", lambda r: r.dataset)
        assert set(by_dataset) == {"scidocs", "fiqa"}
        assert by_dataset["scidocs"]["n"] == 2
        full = full_breakdowns(results, "borda")
        assert set(full) == {"by_dataset", "by_provider", "by_pool_size", "by_cyclicity"}
        assert full["by_cyclicity"]["cyclic"]["n"] == 1
        assert full["by_cyclicity"]["acyclic"]["n"] == 2

    def test_outlier_sensitivity_detects_single_outlier(self):
        results = [
            _result("ds", "q1", "p", 6, False, {"incumbent": 0.5, "borda": 0.9}),  # big win
            _result("ds", "q2", "p", 6, False, {"incumbent": 0.5, "borda": 0.5}),
            _result("ds", "q3", "p", 6, False, {"incumbent": 0.5, "borda": 0.5}),
        ]
        out = outlier_sensitivity(results, "borda", drop_top_n=1)
        assert out["mean_delta_full"] > out["mean_delta_excluding_top_n"]
        assert out["mean_delta_excluding_top_n"] == 0.0


class TestSelection:
    def test_best_single_fixed_extractor_picks_highest_mean_delta(self):
        results = [
            _result("ds", "q1", "p", 6, False, {"incumbent": 0.5, "borda": 0.9, "pagerank": 0.5}),
            _result("ds", "q2", "p", 6, False, {"incumbent": 0.5, "borda": 0.6, "pagerank": 0.5}),
        ]
        assert best_single_fixed_extractor(results) == "borda"

    def test_group_kfold_no_query_in_both_splits(self):
        import random

        from sklearn.model_selection import GroupKFold

        rng = random.Random(0)
        results = []
        for qi in range(6):
            for gi in range(3):
                ndcg = {"incumbent": 0.5, "borda": 0.5 + (0.1 if rng.random() < 0.5 else -0.1)}
                results.append(
                    _result("ds", f"q{qi}", f"prov{gi}", 6, rng.random() < 0.5, ndcg)
                )
        rows = build_predictive_rows(results)
        groups = np.array([f"{r['dataset']}::{r['query_id']}" for r in rows])
        gkf = GroupKFold(n_splits=4)
        for train_idx, test_idx in gkf.split(np.zeros(len(rows)), None, groups):
            assert not (set(groups[train_idx]) & set(groups[test_idx]))

    def test_predictive_selector_unsupported_on_tiny_data(self):
        results = [
            _result("ds", "q1", "p", 6, False, {"incumbent": 0.5, "borda": 0.6}),
            _result("ds", "q2", "p", 6, False, {"incumbent": 0.5, "borda": 0.5}),
        ]
        rows = build_predictive_rows(results)
        result = evaluate_predictive_selector(rows)
        assert result["status"] == "UNSUPPORTED"

    def test_predictive_rows_exclude_relevance_derived_features(self):
        results = [
            _result("ds", "q1", "p", 6, False, {"incumbent": 0.5, "borda": 0.6}),
        ]
        rows = build_predictive_rows(results)
        forbidden = ("ndcg", "relevance", "label_source")
        for row in rows:
            for key in row:
                if key == "label":
                    continue
                assert not any(f in key.lower() for f in forbidden)


class TestDecision:
    def test_fixed_extractor_meaningful_gain(self):
        result = decide(
            best_fixed_name="borda", best_fixed_mean_delta=0.02, best_fixed_headroom_ci_lower=0.01,
            best_fixed_downside_q05=0.0, selection_status="SUPPORTED", oracle_mean_delta=0.03,
        )
        assert result.decision == "EXTRACTION_IMPROVES_RANKING"

    def test_small_but_consistent_lower_tail_still_counts(self):
        result = decide(
            best_fixed_name="borda",
            best_fixed_mean_delta=0.003,
            best_fixed_headroom_ci_lower=0.001,
            best_fixed_downside_q05=0.0005,
            selection_status="SUPPORTED",
            oracle_mean_delta=0.01,
        )
        assert result.decision == "EXTRACTION_IMPROVES_RANKING"

    def test_selective_extraction_only(self):
        result = decide(
            best_fixed_name="borda",
            best_fixed_mean_delta=0.002,
            best_fixed_headroom_ci_lower=-0.001,
            best_fixed_downside_q05=-0.01,
            selection_status="SUPPORTED",
            oracle_mean_delta=0.02,
        )
        assert result.decision == "SELECTIVE_EXTRACTION_ONLY"

    def test_oracle_only_not_deployable(self):
        result = decide(
            best_fixed_name="borda",
            best_fixed_mean_delta=0.001,
            best_fixed_headroom_ci_lower=-0.005,
            best_fixed_downside_q05=-0.02,
            selection_status="UNSUPPORTED",
            oracle_mean_delta=0.015,
        )
        assert result.decision == "ORACLE_ONLY_NOT_DEPLOYABLE"

    def test_no_meaningful_extraction_gain(self):
        result = decide(
            best_fixed_name="borda",
            best_fixed_mean_delta=0.001,
            best_fixed_headroom_ci_lower=-0.001,
            best_fixed_downside_q05=-0.01,
            selection_status="UNSUPPORTED",
            oracle_mean_delta=0.002,
        )
        assert result.decision == "NO_MEANINGFUL_EXTRACTION_GAIN"
