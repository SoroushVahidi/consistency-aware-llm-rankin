"""
Tests for the modern reranking baseline modules.
"""

from __future__ import annotations

import json

import pytest

from rerankers.common import (
    BudgetTracker,
    JudgmentCache,
    RerankerResult,
    write_pairwise_file,
    write_score_file,
)
from rerankers.cross_encoder import CrossEncoderConfig
from rerankers.llm_listwise import ListwiseConfig
from rerankers.llm_listwise import rerank_query as lw_rerank
from rerankers.llm_pairwise import PairwiseConfig, collect_all_pairs
from rerankers.llm_pairwise import rerank_query as pw_rerank
from rerankers.llm_pointwise import PointwiseConfig
from rerankers.llm_pointwise import rerank_query as pt_rerank
from rerankers.tournament_agg import (
    aggregate_preferences,
    bradley_terry_ranking,
    copeland_ranking,
    markov_chain_ranking,
    tournament_sort_ranking,
    win_rate_ranking,
)


class TestBudgetTracker:
    def test_unlimited_budget(self):
        bt = BudgetTracker()
        assert not bt.budget_exhausted
        bt.record(100, 10)
        assert bt.calls_made == 1
        assert not bt.budget_exhausted

    def test_limited_budget(self):
        bt = BudgetTracker(max_calls=2)
        assert not bt.budget_exhausted
        bt.record()
        bt.record()
        assert bt.budget_exhausted

    def test_summary(self):
        bt = BudgetTracker(max_calls=10)
        bt.record(50, 5)
        s = bt.summary()
        assert s["calls_made"] == 1
        assert s["tokens_in"] == 50
        assert s["tokens_out"] == 5


class TestJudgmentCache:
    def test_put_get(self, tmp_path):
        cache = JudgmentCache(tmp_path, "test")
        cache.put("q1", ["d1", "d2"], {"score": 7.0})
        result = cache.get("q1", ["d1", "d2"])
        assert result is not None
        assert result["score"] == 7.0

    def test_miss(self, tmp_path):
        cache = JudgmentCache(tmp_path, "test")
        assert cache.get("q1", ["d1"]) is None

    def test_persistence(self, tmp_path):
        cache1 = JudgmentCache(tmp_path, "test")
        cache1.put("q1", ["d1"], {"score": 3.0})
        cache2 = JudgmentCache(tmp_path, "test")
        result = cache2.get("q1", ["d1"])
        assert result is not None
        assert result["score"] == 3.0


class TestWriteFiles:
    def test_write_score_file(self, tmp_path):
        results = [
            RerankerResult(
                query_id="q1",
                ranked_doc_ids=["d1", "d2"],
                scores={"d1": 10.0, "d2": 5.0},
            )
        ]
        path = tmp_path / "scores.jsonl"
        write_score_file(results, path)
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2
        first = json.loads(lines[0])
        assert first["query_id"] == "q1"
        assert first["doc_id"] == "d1"

    def test_write_pairwise_file(self, tmp_path):
        prefs = {"q1": [("d1", "d2", 1.0), ("d1", "d3", 0.5)]}
        path = tmp_path / "pairs.jsonl"
        write_pairwise_file(prefs, path)
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2


class TestTournamentAggregation:
    """Test tournament aggregation baselines."""

    PREFS = [
        ("d1", "d2", 1.0),
        ("d1", "d3", 1.0),
        ("d2", "d3", 1.0),
        ("d3", "d4", 1.0),
        ("d2", "d4", 1.0),
        ("d1", "d4", 1.0),
    ]

    def test_copeland(self):
        result = copeland_ranking(self.PREFS)
        assert result.ranked_doc_ids[0] == "d1"
        assert result.ranked_doc_ids[-1] == "d4"

    def test_win_rate(self):
        result = win_rate_ranking(self.PREFS)
        assert result.ranked_doc_ids[0] == "d1"

    def test_bradley_terry(self):
        result = bradley_terry_ranking(self.PREFS)
        assert len(result.ranked_doc_ids) == 4
        assert result.ranked_doc_ids[0] == "d1"

    def test_markov_chain(self):
        result = markov_chain_ranking(self.PREFS)
        assert len(result.ranked_doc_ids) == 4

    def test_tournament_sort(self):
        result = tournament_sort_ranking(self.PREFS)
        assert len(result.ranked_doc_ids) == 4
        assert result.ranked_doc_ids[0] == "d1"

    def test_aggregate_preferences_dispatch(self):
        for method in ("copeland", "win_rate", "bradley_terry", "markov_chain", "tournament_sort"):
            result = aggregate_preferences(method, self.PREFS)
            assert len(result.ranked_doc_ids) == 4

    def test_aggregate_unknown_method(self):
        with pytest.raises(ValueError, match="Unknown"):
            aggregate_preferences("nonexistent", self.PREFS)

    def test_empty_preferences(self):
        result = copeland_ranking([])
        assert result.ranked_doc_ids == []

    def test_with_cycles(self):
        cyclic_prefs = [
            ("d1", "d2", 1.0),
            ("d2", "d3", 1.0),
            ("d3", "d1", 1.0),
        ]
        for method in ("copeland", "win_rate", "bradley_terry", "markov_chain"):
            result = aggregate_preferences(method, cyclic_prefs)
            assert len(result.ranked_doc_ids) == 3


class TestLLMPointwiseDryRun:
    def test_dry_run_produces_ranking(self):
        candidates = [("d1", "doc text 1"), ("d2", "doc text 2"), ("d3", "doc text 3")]
        config = PointwiseConfig(dry_run=True, seed=42)
        result = pt_rerank("q1", "test query", candidates, config=config)
        assert result.query_id == "q1"
        assert len(result.ranked_doc_ids) == 3
        assert set(result.ranked_doc_ids) == {"d1", "d2", "d3"}
        assert result.metadata["dry_run"] is True


class TestLLMPairwiseDryRun:
    def test_dry_run_produces_ranking(self):
        candidates = [("d1", "doc text 1"), ("d2", "doc text 2"), ("d3", "doc text 3")]
        config = PairwiseConfig(dry_run=True, seed=42)
        result = pw_rerank("q1", "test query", candidates, config=config)
        assert result.query_id == "q1"
        assert len(result.ranked_doc_ids) == 3
        assert result.metadata["dry_run"] is True

    def test_collect_all_pairs(self):
        candidates = [("d1", "t1"), ("d2", "t2"), ("d3", "t3")]
        config = PairwiseConfig(dry_run=True, seed=42)
        pairs, meta = collect_all_pairs("q1", "query", candidates, config=config)
        assert len(pairs) == 3
        assert meta["n_pairs"] == 3


class TestLLMListwiseDryRun:
    def test_dry_run_produces_ranking(self):
        candidates = [("d1", "text 1"), ("d2", "text 2"), ("d3", "text 3")]
        config = ListwiseConfig(dry_run=True, seed=42, window_size=5)
        result = lw_rerank("q1", "test query", candidates, config=config)
        assert result.query_id == "q1"
        assert len(result.ranked_doc_ids) == 3
        assert result.metadata["dry_run"] is True

    def test_sliding_window(self):
        candidates = [(f"d{i}", f"text {i}") for i in range(15)]
        config = ListwiseConfig(dry_run=True, seed=42, window_size=5, step_size=3)
        result = lw_rerank("q1", "test query", candidates, config=config)
        assert len(result.ranked_doc_ids) == 15


class TestCrossEncoderConfig:
    def test_default_config(self):
        config = CrossEncoderConfig()
        assert config.model_name == "cross-encoder/ms-marco-MiniLM-L-6-v2"
        assert config.batch_size == 64
