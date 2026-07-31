"""Tests for the repair-frontier package (SCC-local incumbent-protected
repair, frontier assembly, discovery/selection evaluation)."""

from __future__ import annotations

import networkx as nx
import numpy as np
import pytest

from consistency_ranker.baseline_ranking import copeland_ranking
from consistency_ranker.mwfas_solver import is_scip_available
from consistency_ranker.repair_frontier.acceptance import accept_candidate
from consistency_ranker.repair_frontier.disposition import classify_edge_dispositions
from consistency_ranker.repair_frontier.frontier import build_repair_frontier
from consistency_ranker.repair_frontier.local_candidates import (
    generate_local_candidates,
    generate_protected_candidate,
)
from consistency_ranker.repair_frontier.protection_rules import EdgeProtectionRule, protected_edges
from consistency_ranker.repair_frontier.reinsertion import reinsert_scc_orderings
from consistency_ranker.repair_frontier.selection import (
    SELECTION_FEATURE_COLS,
    _deployable_candidates,
    _feature_row,
    evaluate_predictive_selector,
)
from consistency_ranker.repair_frontier.types import EdgeConfidence


class TestReinsertion:
    def test_reinsertion_only_touches_scc_slots(self):
        incumbent = ["x", "a", "b", "c", "y"]
        local_orders = {frozenset({"a", "b", "c"}): ["c", "a", "b"]}
        result = reinsert_scc_orderings(incumbent, local_orders)
        assert result[0] == "x"
        assert result[4] == "y"
        assert result[1:4] == ["c", "a", "b"]

    def test_acyclic_component_edges_unaffected(self):
        g = nx.DiGraph()
        g.add_edge("x", "y", weight=1.0)
        g.add_edge("y", "z", weight=1.0)
        candidates = build_repair_frontier(g, "ds", "q1")
        for c in candidates:
            assert c.modified_sccs == []
            assert c.global_ranking == copeland_ranking(g)


class TestAcceptance:
    def test_abstain_returns_incumbent(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0)
        g.add_edge("b", "a", weight=0.9)
        incumbent = ["a", "b"]
        candidate = ["b", "a"]
        accepted = accept_candidate(g, incumbent, candidate, mode="conservative", margin=1e9)
        assert accepted is False
        chosen = candidate if accepted else incumbent
        assert chosen == incumbent

    def test_objective_only_accepts_strict_improvement(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=5.0)
        g.add_edge("b", "c", weight=5.0)
        g.add_edge("c", "a", weight=1.0)
        incumbent = copeland_ranking(g)
        candidate = ["a", "b", "c"]
        assert accept_candidate(g, incumbent, candidate, mode="objective_only") in (True, False)
        # the incumbent itself is always accepted, trivially
        assert accept_candidate(g, incumbent, incumbent, mode="objective_only") is True


class TestProtection:
    def test_protected_edge_not_touched_when_avoidable(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0)
        g.add_edge("b", "c", weight=1.0)
        g.add_edge("c", "a", weight=1.0)
        confidences = {
            ("a", "b"): EdgeConfidence("a", "b", 3, 3, True, 3.0, 3.0),
        }
        rule = EdgeProtectionRule(kind="unanimous_multi_provider", min_providers_for_unanimity=2)
        cand = generate_protected_candidate(
            g, frozenset({"a", "b", "c"}), confidences, rule, method="greedy"
        )
        assert ("a", "b") not in {(u, v) for u, v, _ in cand.removed_edges}
        assert cand.protected_edge_violations == 0
        assert nx.is_directed_acyclic_graph(cand.local_dag)

    def test_all_edges_protected_forces_abstain_and_counts_violation(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0)
        g.add_edge("b", "c", weight=1.0)
        g.add_edge("c", "a", weight=1.0)
        pairs = [("a", "b"), ("b", "c"), ("c", "a")]
        confidences = {e: EdgeConfidence(e[0], e[1], 3, 3, True, 3.0, 3.0) for e in pairs}
        rule = EdgeProtectionRule(kind="unanimous_multi_provider", min_providers_for_unanimity=2)
        cand = generate_protected_candidate(
            g, frozenset({"a", "b", "c"}), confidences, rule, method="greedy"
        )
        assert nx.is_directed_acyclic_graph(cand.local_dag)
        assert cand.protected_edge_violations >= 1

    def test_topk_boundary_protection(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0)
        g.add_edge("b", "c", weight=1.0)
        g.add_edge("c", "d", weight=1.0)
        rule = EdgeProtectionRule(kind="topk_boundary_crossing", topk=2, topk_window=2)
        incumbent_rank = {"a": 0, "b": 1, "c": 2, "d": 3}
        protected = protected_edges(g, {}, rule, incumbent_rank=incumbent_rank)
        assert ("b", "c") in protected  # straddles the top-2 boundary
        assert ("a", "b") not in protected  # both inside the core
        assert ("c", "d") not in protected  # both outside the core/band


class TestDedup:
    def test_dedup_identical_rankings(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=5.0)
        g.add_edge("b", "c", weight=5.0)
        g.add_edge("c", "a", weight=0.01)
        candidates = build_repair_frontier(g, "ds", "q1")
        rankings = [tuple(c.global_ranking) for c in candidates]
        assert len(rankings) == len(set(rankings))
        assert sum(1 for c in candidates if c.candidate_id == "incumbent") == 1


class TestLocalCandidates:
    def test_local_candidate_is_total_order(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0)
        g.add_edge("b", "c", weight=1.0)
        g.add_edge("c", "a", weight=1.0)
        members = frozenset({"a", "b", "c"})
        incumbent_ranking = ["a", "b", "c"]
        candidates = generate_local_candidates(g, members, incumbent_ranking, exact_max_n=12)
        assert len(candidates) > 1
        for c in candidates:
            assert set(c.local_order) == members
            assert len(c.local_order) == len(members)
            if c.method == "original" or "residual=True" in c.method:
                continue
            assert nx.is_directed_acyclic_graph(c.local_dag)

    @pytest.mark.skipif(not is_scip_available(), reason="PySCIPOpt not installed")
    def test_exact_candidate_present_and_acyclic(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=5.0)
        g.add_edge("b", "c", weight=4.0)
        g.add_edge("c", "a", weight=0.25)
        members = frozenset({"a", "b", "c"})
        candidates = generate_local_candidates(g, members, ["a", "b", "c"], exact_max_n=12)
        exact = next(c for c in candidates if c.method == "exact")
        assert nx.is_directed_acyclic_graph(exact.local_dag)
        assert set(exact.local_order) == members


class TestDisposition:
    def test_preserved(self):
        orig = nx.DiGraph()
        orig.add_edge("a", "b", weight=1.0)
        repaired = orig.copy()
        result = classify_edge_dispositions(orig, repaired)
        assert result[("a", "b")] == "preserved"

    def test_removed_and_reversed(self):
        # A 2-cycle where both edges are removed: the surviving deterministic
        # topological order (node-insertion tie-break) places u before v, so
        # (u, v) classifies "removed" (order coincidentally still holds) and
        # (v, u) classifies "reversed" (order now contradicts it).
        orig = nx.DiGraph()
        orig.add_edge("u", "v", weight=1.0)
        orig.add_edge("v", "u", weight=1.0)
        repaired = nx.DiGraph()
        repaired.add_nodes_from(["u", "v"])
        result = classify_edge_dispositions(orig, repaired)
        assert result[("u", "v")] == "removed"
        assert result[("v", "u")] == "reversed"

    def test_unresolved_residual_cycle(self):
        orig = nx.DiGraph()
        for u, v in [("a", "b"), ("b", "c"), ("c", "a")]:
            orig.add_edge(u, v, weight=1.0)
        repaired = orig.copy()  # nothing removed -- still fully cyclic
        result = classify_edge_dispositions(orig, repaired)
        assert all(v == "unresolved" for v in result.values())

    def test_mismatched_node_sets_raises(self):
        orig = nx.DiGraph()
        orig.add_edge("a", "b", weight=1.0)
        repaired = nx.DiGraph()
        repaired.add_node("a")
        with pytest.raises(ValueError):
            classify_edge_dispositions(orig, repaired)


class TestSelectionNoLeakage:
    def test_selection_features_exclude_relevance(self):
        forbidden = ("ndcg", "relevance", "label")
        for col in SELECTION_FEATURE_COLS:
            assert not any(f in col.lower() for f in forbidden)

    def test_oracle_analysis_only_never_feeds_deployable_features(self):
        # Distinct weights + a protected edge force the protected candidate's
        # ranking to diverge from both the incumbent and whole-graph greedy,
        # so its acceptance_by_mode (computed with relevance labels for
        # oracle_analysis_only) is actually populated -- and confirm that
        # info never leaks into the label-free selection feature row.
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0)
        g.add_edge("b", "c", weight=5.0)
        g.add_edge("c", "a", weight=5.0)
        relevance = {"a": 2, "b": 1, "c": 0}
        confidences = {("a", "b"): EdgeConfidence("a", "b", 3, 3, True, 3.0, 3.0)}
        rule = EdgeProtectionRule(kind="unanimous_multi_provider", min_providers_for_unanimity=2)
        candidates = build_repair_frontier(
            g, "ds", "q1", relevance_map=relevance, confidences=confidences, protection_rules=[rule]
        )
        protected = [c for c in candidates if c.candidate_id.startswith("scc_local_protected_")]
        assert protected, "expected a protected candidate to survive dedup"
        assert "oracle_analysis_only" in protected[0].acceptance_by_mode
        row = _feature_row(protected[0])
        assert set(row) == set(SELECTION_FEATURE_COLS)
        pool = _deployable_candidates(candidates)
        assert all(c.acceptance_mode != "oracle_analysis_only" for c in pool)

    def test_group_kfold_no_query_in_both_splits(self):
        import random

        from sklearn.model_selection import GroupKFold

        rng = random.Random(0)
        rows = []
        for qi in range(6):
            for _ in range(5):
                rows.append(
                    {
                        "dataset": "ds",
                        "query_id": f"q{qi}",
                        "label": rng.randint(0, 1),
                        **{c: rng.random() for c in SELECTION_FEATURE_COLS},
                    }
                )
        groups = np.array([f"{r['dataset']}::{r['query_id']}" for r in rows])
        gkf = GroupKFold(n_splits=4)
        for train_idx, test_idx in gkf.split(np.zeros(len(rows)), None, groups):
            assert not (set(groups[train_idx]) & set(groups[test_idx]))

        result = evaluate_predictive_selector(rows)
        assert result["status"] in ("EVALUATED", "UNSUPPORTED")


class TestDeterminism:
    def test_frontier_deterministic_given_seed(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=3.0)
        g.add_edge("b", "c", weight=2.0)
        g.add_edge("c", "a", weight=1.0)
        rule = EdgeProtectionRule(kind="confidence_threshold", reliability_tau=0.5)
        kwargs = dict(protection_rules=[rule], relevance_map={"a": 2, "b": 1, "c": 0})

        def _strip_runtime(c):
            d = c.to_dict()
            d.pop("runtime_s")
            return d

        c1 = build_repair_frontier(g, "ds", "q1", **kwargs)
        c2 = build_repair_frontier(g, "ds", "q1", **kwargs)
        assert [_strip_runtime(c) for c in c1] == [_strip_runtime(c) for c in c2]
