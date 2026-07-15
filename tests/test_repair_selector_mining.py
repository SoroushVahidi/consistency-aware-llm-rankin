"""Tests for repair-selector mining splits, leakage guards, and merging."""

from __future__ import annotations

import json

import pytest

from consistency_ranker.repair_selector_mining.repair_pairs import REPAIR_PAIRS, PRIMARY_REPAIR_PAIR
from consistency_ranker.repair_selector_mining.splits import assign_splits
from consistency_ranker.repair_selector_mining.candidate_selection import mining_priority_score, pre_outcome_features
from consistency_ranker.pairwise_prefs import Preference


def test_repair_pairs_are_matched_components():
    for pair in REPAIR_PAIRS:
        assert pair.repaired != pair.unrepaired
        assert pair.repair_backend
        assert pair.extraction


def test_primary_pair_is_markov_greedy():
    assert PRIMARY_REPAIR_PAIR.repaired == "markov_graph_repaired"
    assert PRIMARY_REPAIR_PAIR.unrepaired == "markov_graph"
    assert PRIMARY_REPAIR_PAIR.repair_backend == "greedy_fas"


def test_splits_no_query_in_multiple_splits():
    candidates = [
        {"dataset": "scidocs", "query_id": f"q{i}", "query_text": f"query text {i}"}
        for i in range(30)
    ]
    candidates += [
        {"dataset": "fiqa", "query_id": f"q{i}", "query_text": f"fiqa query {i}"}
        for i in range(20)
    ]
    assignments = assign_splits(candidates, seed=42)
    by_query: dict[tuple[str, str], str] = {}
    for (ds, qid), split in assignments.items():
        assert (ds, qid) not in by_query or by_query[(ds, qid)] == split
        by_query[(ds, qid)] = split
    splits = set(by_query.values())
    assert "test" in splits
    test_frac = sum(1 for s in by_query.values() if s == "test") / len(by_query)
    assert test_frac >= 0.15


def test_near_duplicate_queries_same_split():
    candidates = [
        {"dataset": "scidocs", "query_id": "q1", "query_text": "What is ML?"},
        {"dataset": "scidocs", "query_id": "q2", "query_text": "what is ml?"},
        {"dataset": "scidocs", "query_id": "q3", "query_text": "Different topic"},
    ]
    assignments = assign_splits(candidates, seed=7)
    assert assignments[("scidocs", "q1")] == assignments[("scidocs", "q2")]


def test_pre_outcome_features_exclude_ndcg():
    prefs = [
        Preference("a", "b", 1.0),
        Preference("b", "c", 0.8),
        Preference("c", "a", 0.6),
    ]
    feats = pre_outcome_features(prefs, prior_scores={"a": 1.0, "b": 0.5, "c": 0.3})
    assert "ndcg" not in json.dumps(feats).lower()
    assert "qrel" not in json.dumps(feats).lower()
    assert feats["is_cyclic"] == 1.0


def test_mining_priority_higher_for_cyclic_graph():
    cyclic = {"is_cyclic": 1.0, "largest_scc_frac": 0.8, "scc_cycle_burden_frac": 0.5,
              "ranker_disagreement": 0.3, "prior_top1_margin": 0.15, "fas_removed_weight_frac": 0.2,
              "greedy_exact_disagreement": 0.1, "graph_density": 0.3, "vote_entropy": 1.0,
              "n_nodes": 10, "n_edges": 20}
    acyclic = {**cyclic, "is_cyclic": 0.0, "largest_scc_frac": 0.1, "scc_cycle_burden_frac": 0.0}
    assert mining_priority_score(cyclic) > mining_priority_score(acyclic)
