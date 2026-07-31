from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "reports" / "full_calibrated_core" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import full_calibration_utils as fcu  # noqa: E402
import run_full_calibrated_core as rfc  # noqa: E402


def _ndcg(ranking: list[str], rel_map: dict[str, int], k: int) -> float:
    aligned = fcu._align_ranking(ranking, rel_map)
    return float(fcu._ndcg_at_k(aligned, rel_map, k=k) or 0.0)


def _one_query_eval_record(*, dataset: str, regime: str, pool_size: int, metric_cutoff: int):
    evaluator = fcu.CalibrationEvaluator()
    dataset_inputs = rfc._analysis_dataset_inputs(dataset, pool_size_override=pool_size)
    baseline = fcu.raw_baseline_statistics(dataset_inputs)
    pair_margins, _zero_var = rfc._pair_margin_summary(dataset_inputs, "minmax_query_ranker")
    threshold_config = fcu.choose_threshold_config(
        dataset=dataset,
        regime=regime,
        calibration="minmax_query_ranker",
        threshold_mode="retention_matched",
        baseline_vote_rates=baseline[regime]["vote_rates"],
        baseline_edge_count=baseline[regime]["edge_count"],
        calibration_pair_margins=pair_margins,
        per_query_inputs=dataset_inputs["per_query_inputs"],
    )
    item = dataset_inputs["per_query_inputs"][0]
    artifacts = fcu.build_query_vote_artifacts(
        query_id=item["query_id"],
        raw_scores_by_ranker=item["raw_scores_by_ranker"],
        candidate_pool=item["candidate_pool"],
        calibration="minmax_query_ranker",
        threshold_config=threshold_config,
    )
    record = evaluator.evaluate_query(
        dataset=dataset,
        query_id=item["query_id"],
        qrels_for_query=item["qrels_for_query"],
        vote_regime=regime,
        top_k=metric_cutoff,
        candidate_pool=item["candidate_pool"],
        vote_rows=artifacts["rows"],
        raw_score_maps_by_ranker={
            ranker: list(score_map.items())
            for ranker, score_map in item["raw_scores_by_ranker"].items()
        },
    )
    assert record is not None
    return dataset_inputs, item, record


class TestPrefixComparisonHelpers:
    def test_p_equals_k_supported(self):
        rel_map = {"d1": 3, "d2": 2, "d3": 0}
        summary = fcu.summarize_prefix_change(
            ["d1", "d2", "d3"],
            ["d2", "d1", "d3"],
            rel_map=rel_map,
            k=3,
        )
        assert summary["top_k_membership_changed"] is False
        assert summary["top_k_order_changed"] is True

    def test_identical_topk_membership_but_changed_order(self):
        rel_map = {"d1": 2, "d2": 2, "d3": 1, "d4": 0}
        summary = fcu.summarize_prefix_change(
            ["d1", "d2", "d3", "d4"],
            ["d2", "d1", "d3", "d4"],
            rel_map=rel_map,
            k=3,
        )
        assert summary["top_k_membership_changed"] is False
        assert summary["top_k_order_changed"] is True
        assert summary["differently_graded_judged_pairs_changed"] is False
        assert summary["relevance_sequence_changed"] is False

    def test_changed_topk_membership_detected(self):
        rel_map = {"d1": 3, "d2": 2, "d3": 1, "d4": 0}
        summary = fcu.summarize_prefix_change(
            ["d1", "d2", "d3", "d4"],
            ["d1", "d2", "d4", "d3"],
            rel_map=rel_map,
            k=3,
        )
        assert summary["top_k_membership_changed"] is True
        assert summary["top_k_order_changed"] is True

    def test_changes_below_k_do_not_change_ndcg(self):
        rel_map = {"d1": 3, "d2": 2, "d3": 1, "d4": 0, "d5": 0}
        raw = ["d1", "d2", "d3", "d4", "d5"]
        repaired = ["d1", "d2", "d3", "d5", "d4"]
        summary = fcu.summarize_prefix_change(raw, repaired, rel_map=rel_map, k=3)
        assert summary["top_k_membership_changed"] is False
        assert summary["top_k_order_changed"] is False
        assert _ndcg(raw, rel_map, 3) == pytest.approx(_ndcg(repaired, rel_map, 3))

    def test_crossing_k_boundary_can_change_ndcg(self):
        rel_map = {"d1": 3, "d2": 2, "d3": 0, "d4": 1}
        raw = ["d1", "d2", "d3", "d4"]
        repaired = ["d1", "d2", "d4", "d3"]
        summary = fcu.summarize_prefix_change(raw, repaired, rel_map=rel_map, k=3)
        assert summary["top_k_membership_changed"] is True
        assert _ndcg(raw, rel_map, 3) != pytest.approx(_ndcg(repaired, rel_map, 3))

    def test_differently_graded_judged_pairs_change_detected(self):
        rel_map = {"d1": 3, "d2": 1, "d3": 2}
        summary = fcu.summarize_prefix_change(
            ["d1", "d2", "d3"],
            ["d3", "d2", "d1"],
            rel_map=rel_map,
            k=3,
        )
        assert summary["differently_graded_judged_pairs_changed"] is True

    def test_cutoff_exceeding_ranking_length_raises(self):
        with pytest.raises(ValueError, match="Requested cutoff exceeds available ranking length"):
            fcu.summarize_prefix_change(["d1", "d2"], ["d1", "d2"], rel_map={"d1": 1}, k=3)

    def test_deterministic_results(self):
        rel_map = {"d1": 3, "d2": 2, "d3": 1, "d4": 0}
        args = (["d1", "d2", "d3", "d4"], ["d2", "d1", "d3", "d4"])
        first = fcu.summarize_prefix_change(*args, rel_map=rel_map, k=3)
        second = fcu.summarize_prefix_change(*args, rel_map=rel_map, k=3)
        assert first == second


class TestPoolSizeOverride:
    @pytest.mark.real_data
    def test_prepare_dataset_inputs_respects_pool_size_override(self):
        default_inputs = rfc._analysis_dataset_inputs("hotpotqa")
        larger_inputs = rfc._analysis_dataset_inputs("hotpotqa", pool_size_override=35)
        assert default_inputs["requested_pool_size"] == 10
        assert larger_inputs["requested_pool_size"] == 35
        assert len(default_inputs["per_query_inputs"][0]["candidate_pool"]) == 10
        assert len(larger_inputs["per_query_inputs"][0]["candidate_pool"]) == 35

    @pytest.mark.real_data
    def test_real_query_records_keep_pool_size_and_metric_cutoff_separate(self):
        _dataset_inputs, item, record = _one_query_eval_record(
            dataset="hotpotqa",
            regime="ms1",
            pool_size=35,
            metric_cutoff=5,
        )
        assert record["candidate_pool_size"] == len(item["candidate_pool"]) == 35
        assert record["metric_cutoff"] == 5
        method = record["method_outputs"]["hybrid_repaired_copeland_a0p3_minmax"]
        assert len(method["ranking"]) == 35
        assert len(method["top_k_prefix"]) == 5
        assert method["mrr_at_k"] is not None

    def test_evaluate_query_raises_when_cutoff_exceeds_pool(self):
        evaluator = fcu.CalibrationEvaluator()
        with pytest.raises(ValueError, match="exceeds candidate pool size 2"):
            evaluator.evaluate_query(
                dataset="toy",
                query_id="q1",
                qrels_for_query=[],
                vote_regime="ms1",
                top_k=3,
                candidate_pool=["d1", "d2"],
                vote_rows=[],
                raw_score_maps_by_ranker={"bm25": [], "tfidf": [], "minilm": []},
            )
