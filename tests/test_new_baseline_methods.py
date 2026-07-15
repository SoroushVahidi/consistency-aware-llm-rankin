from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "reports" / "full_calibrated_core" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import full_calibration_utils as fcu  # noqa: E402
import run_full_calibrated_core as rfc  # noqa: E402

NEW_METHOD_KEYS = (
    "pagerank_graph",
    "pagerank_graph_repaired",
    "rank_centrality_graph",
    "rank_centrality_graph_repaired",
    "markov_hybrid_unrepaired",
    "markov_hybrid_repaired",
    "bradley_terry_graph",
    "bradley_terry_graph_repaired",
)


def _one_query_eval_record(dataset: str = "hotpotqa", regime: str = "ms1", index: int = 0):
    evaluator = fcu.CalibrationEvaluator()
    dataset_inputs = rfc._analysis_dataset_inputs(dataset)
    spec = dataset_inputs["spec"]
    baseline = fcu.raw_baseline_statistics(dataset_inputs)
    pair_margins, _zv = rfc._pair_margin_summary(dataset_inputs, "minmax_query_ranker")
    tc = fcu.choose_threshold_config(
        dataset=dataset,
        regime=regime,
        calibration="minmax_query_ranker",
        threshold_mode="retention_matched",
        baseline_vote_rates=baseline[regime]["vote_rates"],
        baseline_edge_count=baseline[regime]["edge_count"],
        calibration_pair_margins=pair_margins,
        per_query_inputs=dataset_inputs["per_query_inputs"],
    )
    item = dataset_inputs["per_query_inputs"][index]
    artifacts = fcu.build_query_vote_artifacts(
        query_id=item["query_id"],
        raw_scores_by_ranker=item["raw_scores_by_ranker"],
        candidate_pool=item["candidate_pool"],
        calibration="minmax_query_ranker",
        threshold_config=tc,
    )
    tuple_maps = rfc._score_maps_as_tuples(item["raw_scores_by_ranker"])
    record = evaluator.evaluate_query(
        dataset=dataset,
        query_id=item["query_id"],
        qrels_for_query=item["qrels_for_query"],
        vote_regime=regime,
        top_k=spec.top_k,
        candidate_pool=item["candidate_pool"],
        vote_rows=artifacts["rows"],
        raw_score_maps_by_ranker=tuple_maps,
    )
    return record, item, evaluator, dataset_inputs, spec, artifacts, tc


class TestNewBaselinesRegistered:
    def test_all_new_methods_in_method_keys(self):
        for key in NEW_METHOD_KEYS:
            assert key in rfc.METHOD_KEYS

    def test_new_pairs_in_pair_specs(self):
        pair_names = {p[0] for p in rfc.PAIR_SPECS}
        for expected in (
            "pagerank_graph",
            "rank_centrality_graph",
            "markov_hybrid",
            "bradley_terry_graph",
        ):
            assert expected in pair_names

    def test_new_baseline_pair_names_excludes_legacy(self):
        assert set(rfc.NEW_BASELINE_PAIR_NAMES).isdisjoint(rfc.LEGACY_PAIR_NAMES)
        assert len(rfc.PAIR_SPECS) == len(rfc.LEGACY_PAIR_NAMES) + len(rfc.NEW_BASELINE_PAIR_NAMES)


class TestNewBaselineFairness:
    def test_all_new_methods_present_for_a_real_query(self):
        record, *_ = _one_query_eval_record()
        for key in NEW_METHOD_KEYS:
            assert key in record["method_outputs"]

    def test_new_methods_only_rank_documents_in_the_candidate_pool(self):
        record, item, *_ = _one_query_eval_record()
        pool = set(item["candidate_pool"])
        for key in NEW_METHOD_KEYS:
            ranking = record["method_outputs"][key]["ranking"]
            assert set(ranking) <= pool, key

    def test_new_methods_use_the_same_candidate_pool_as_legacy_methods(self):
        record, item, *_ = _one_query_eval_record()
        pool = set(item["candidate_pool"])
        legacy_pool = set(record["method_outputs"]["copeland_graph"]["ranking"])
        for key in NEW_METHOD_KEYS:
            new_pool = set(record["method_outputs"][key]["ranking"])
            assert new_pool <= pool
            assert legacy_pool <= pool

    def test_evaluation_is_deterministic(self):
        record1, item, evaluator, dataset_inputs, spec, artifacts, tc = _one_query_eval_record()
        tuple_maps = rfc._score_maps_as_tuples(item["raw_scores_by_ranker"])
        record2 = evaluator.evaluate_query(
            dataset="hotpotqa",
            query_id=item["query_id"],
            qrels_for_query=item["qrels_for_query"],
            vote_regime="ms1",
            top_k=spec.top_k,
            candidate_pool=item["candidate_pool"],
            vote_rows=artifacts["rows"],
            raw_score_maps_by_ranker=tuple_maps,
        )
        for key in NEW_METHOD_KEYS:
            assert (
                record1["method_outputs"][key]["ranking"]
                == record2["method_outputs"][key]["ranking"]
            ), key


class TestBradleyTerryIntegration:
    def test_bradley_terry_repaired_has_no_more_edges_than_unrepaired(self):
        # Repair only removes edges; Bradley-Terry is fit on graph edges, so
        # the repaired-graph fit must never see more preference pairs than
        # the unrepaired fit for the same query.
        record, *_ = _one_query_eval_record()
        raw_edges = record["graph"].number_of_edges()
        repaired_edges = record["repaired_graph"].number_of_edges()
        assert repaired_edges <= raw_edges

    def test_bradley_terry_scores_are_probabilities_summing_near_one(self):
        record, *_ = _one_query_eval_record()
        scores = record["method_outputs"]["bradley_terry_graph"]["scores"]
        if scores:
            total = sum(scores.values())
            assert 0.99 <= total <= 1.01
