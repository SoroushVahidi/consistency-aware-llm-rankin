from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "reports" / "full_calibrated_core" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from conditional_subsets import classify_query_pair, failure_decomposition_counts  # noqa: E402


def _eval_record(
    *,
    is_cyclic: bool,
    removed_edges: list[tuple[str, str]],
    unrepaired_ranking: list[str],
    repaired_ranking: list[str],
    unrepaired_pw: float,
    repaired_pw: float,
    unrepaired_ndcg: float,
    repaired_ndcg: float,
    relevance_changed_flag: bool | None = None,
) -> dict:
    pairwise_comparisons = {}
    if relevance_changed_flag is not None:
        pairwise_comparisons["unrepaired__vs__repaired"] = {
            "differently_graded_judged_pairs_changed": relevance_changed_flag,
        }
    return {
        "graph_stats": {"is_cyclic": is_cyclic},
        "removed_edges": removed_edges,
        "pairwise_comparisons": pairwise_comparisons,
        "method_outputs": {
            "unrepaired": {
                "ranking": unrepaired_ranking,
                "pairwise_accuracy": unrepaired_pw,
                "ndcg_at_k": unrepaired_ndcg,
            },
            "repaired": {
                "ranking": repaired_ranking,
                "pairwise_accuracy": repaired_pw,
                "ndcg_at_k": repaired_ndcg,
            },
        },
    }


class TestClassifyQueryPair:
    def test_fully_inactive_query(self):
        rec = _eval_record(
            is_cyclic=False,
            removed_edges=[],
            unrepaired_ranking=["a", "b", "c"],
            repaired_ranking=["a", "b", "c"],
            unrepaired_pw=0.5,
            repaired_pw=0.5,
            unrepaired_ndcg=0.7,
            repaired_ndcg=0.7,
        )
        flags = classify_query_pair(
            rec, unrepaired_key="unrepaired", repaired_key="repaired", top_k=2
        )
        assert flags == {
            "has_cycle": False,
            "repair_active": False,
            "ranking_changed": False,
            "topk_changed": False,
            "relevance_order_changed": False,
            "metric_changed": False,
        }

    def test_cycle_and_repair_active_but_ranking_unaffected(self):
        rec = _eval_record(
            is_cyclic=True,
            removed_edges=[("x", "y")],
            unrepaired_ranking=["a", "b", "c"],
            repaired_ranking=["a", "b", "c"],
            unrepaired_pw=0.5,
            repaired_pw=0.5,
            unrepaired_ndcg=0.7,
            repaired_ndcg=0.7,
        )
        flags = classify_query_pair(
            rec, unrepaired_key="unrepaired", repaired_key="repaired", top_k=2
        )
        assert flags["has_cycle"] is True
        assert flags["repair_active"] is True
        assert flags["ranking_changed"] is False
        assert flags["topk_changed"] is False
        assert flags["metric_changed"] is False

    def test_ranking_changed_but_topk_stable(self):
        rec = _eval_record(
            is_cyclic=True,
            removed_edges=[("x", "y")],
            unrepaired_ranking=["a", "b", "c", "d"],
            repaired_ranking=["b", "a", "c", "d"],
            unrepaired_pw=0.5,
            repaired_pw=0.5,
            unrepaired_ndcg=0.7,
            repaired_ndcg=0.7,
        )
        flags = classify_query_pair(
            rec, unrepaired_key="unrepaired", repaired_key="repaired", top_k=2
        )
        assert flags["ranking_changed"] is True
        assert flags["topk_changed"] is False  # {a,b} unchanged as a set

    def test_topk_changed(self):
        rec = _eval_record(
            is_cyclic=True,
            removed_edges=[("x", "y")],
            unrepaired_ranking=["a", "b", "c", "d"],
            repaired_ranking=["c", "a", "b", "d"],
            unrepaired_pw=0.5,
            repaired_pw=0.5,
            unrepaired_ndcg=0.7,
            repaired_ndcg=0.7,
        )
        flags = classify_query_pair(
            rec, unrepaired_key="unrepaired", repaired_key="repaired", top_k=2
        )
        assert flags["topk_changed"] is True  # {a,b} -> {c,a}

    def test_relevance_order_changed_tracks_pairwise_accuracy_delta(self):
        rec = _eval_record(
            is_cyclic=True,
            removed_edges=[("x", "y")],
            unrepaired_ranking=["a", "b"],
            repaired_ranking=["b", "a"],
            unrepaired_pw=0.4,
            repaired_pw=0.6,
            unrepaired_ndcg=0.7,
            repaired_ndcg=0.7,
        )
        flags = classify_query_pair(
            rec, unrepaired_key="unrepaired", repaired_key="repaired", top_k=2
        )
        assert flags["relevance_order_changed"] is True
        assert flags["metric_changed"] is False

    def test_relevance_order_changed_prefers_direct_pair_flag(self):
        rec = _eval_record(
            is_cyclic=True,
            removed_edges=[("x", "y")],
            unrepaired_ranking=["a", "b", "c"],
            repaired_ranking=["b", "a", "c"],
            unrepaired_pw=0.5,
            repaired_pw=0.5,
            unrepaired_ndcg=0.7,
            repaired_ndcg=0.7,
            relevance_changed_flag=True,
        )
        flags = classify_query_pair(
            rec, unrepaired_key="unrepaired", repaired_key="repaired", top_k=2
        )
        assert flags["relevance_order_changed"] is True

    def test_metric_changed_requires_more_than_float_noise(self):
        rec = _eval_record(
            is_cyclic=True,
            removed_edges=[("x", "y")],
            unrepaired_ranking=["a", "b"],
            repaired_ranking=["b", "a"],
            unrepaired_pw=0.5,
            repaired_pw=0.5,
            unrepaired_ndcg=0.700000000001,
            repaired_ndcg=0.700000000002,
        )
        flags = classify_query_pair(
            rec, unrepaired_key="unrepaired", repaired_key="repaired", top_k=2
        )
        assert flags["metric_changed"] is False

    def test_none_metrics_do_not_crash_and_read_as_unchanged(self):
        rec = _eval_record(
            is_cyclic=False,
            removed_edges=[],
            unrepaired_ranking=["a"],
            repaired_ranking=["a"],
            unrepaired_pw=None,
            repaired_pw=None,
            unrepaired_ndcg=None,
            repaired_ndcg=None,
        )
        flags = classify_query_pair(
            rec, unrepaired_key="unrepaired", repaired_key="repaired", top_k=1
        )
        assert flags["relevance_order_changed"] is False
        assert flags["metric_changed"] is False


class TestFailureDecomposition:
    def test_categories_are_mutually_exclusive_and_exhaustive(self):
        flags_list = [
            {
                "has_cycle": False,
                "repair_active": False,
                "ranking_changed": False,
                "metric_changed": False,
            },
            {
                "has_cycle": True,
                "repair_active": False,
                "ranking_changed": False,
                "metric_changed": False,
            },
            {
                "has_cycle": True,
                "repair_active": True,
                "ranking_changed": False,
                "metric_changed": False,
            },
            {
                "has_cycle": True,
                "repair_active": True,
                "ranking_changed": True,
                "metric_changed": False,
            },
            {
                "has_cycle": True,
                "repair_active": True,
                "ranking_changed": True,
                "metric_changed": True,
            },
        ]
        counts = failure_decomposition_counts(flags_list)
        assert counts["n_queries"] == 5
        assert counts["no_cycle"] == 1
        assert counts["cycle_but_repair_inactive"] == 1
        assert counts["repair_inactive_on_ranking"] == 1
        assert counts["ranking_changed_metric_stable"] == 1
        assert counts["metric_changed"] == 1
        total = (
            counts["no_cycle"]
            + counts["cycle_but_repair_inactive"]
            + counts["repair_inactive_on_ranking"]
            + counts["ranking_changed_metric_stable"]
            + counts["metric_changed"]
        )
        assert total == counts["n_queries"]

    def test_fractions_sum_to_one(self):
        flags_list = [
            {
                "has_cycle": False,
                "repair_active": False,
                "ranking_changed": False,
                "metric_changed": False,
            },
            {
                "has_cycle": True,
                "repair_active": True,
                "ranking_changed": True,
                "metric_changed": True,
            },
        ]
        counts = failure_decomposition_counts(flags_list)
        frac_sum = sum(v for k, v in counts.items() if k.endswith("_fraction"))
        assert abs(frac_sum - 1.0) < 1e-9

    def test_empty_input(self):
        counts = failure_decomposition_counts([])
        assert counts["n_queries"] == 0
        assert "no_cycle_fraction" not in counts
