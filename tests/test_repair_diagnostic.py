"""Tests for the repair-regime diagnostic study."""

from __future__ import annotations

import networkx as nx
import numpy as np
import pytest

from consistency_ranker.repair_diagnostic.association import (
    compute_feature_associations,
    full_stability_report,
    outcome_group_stats,
    outlier_sensitivity,
)
from consistency_ranker.repair_diagnostic.decision import decide
from consistency_ranker.repair_diagnostic.features import (
    POST_REPAIR_FEATURE_NAMES,
    PRE_REPAIR_FEATURE_NAMES,
    compute_post_repair_features,
    compute_pre_repair_features,
)
from consistency_ranker.repair_diagnostic.outcomes import (
    QueryGraphDiagnostic,
    evaluate_repair_outcome,
)
from consistency_ranker.repair_diagnostic.prediction import (
    baseline_policies,
    evaluate_predictors,
    subgroup_stability,
)


def _diag(dataset, query_id, provider, pool_size, ndcg_preserve, ndcg_repair, **feature_overrides):
    from consistency_ranker.repair_diagnostic.features import PostRepairFeatures, PreRepairFeatures

    defaults = {
        "n_nodes": 6,
        "n_edges": 10,
        "graph_density": 0.4,
        "pool_size": pool_size,
        "n_sccs": 3,
        "n_nontrivial_sccs": 1,
        "largest_scc_size": 3,
        "largest_scc_frac": 0.5,
        "is_cyclic": True,
        "scc_cycle_weight": 2.0,
        "scc_cycle_weight_frac": 0.3,
        "edge_weight_mean": 1.5,
        "edge_weight_std": 0.5,
        "edge_weight_max": 3.0,
        "mean_edge_reliability": 0.8,
        "frac_edges_unanimous": 0.5,
        "provider_disagreement": 0.1,
        "topk_involvement": True,
        "incumbent_topk_margin": 1.0,
    }
    defaults.update(feature_overrides)
    pre = PreRepairFeatures(**defaults)
    post = PostRepairFeatures(
        repair_objective=1.0,
        n_reversed_edges=1,
        weight_reversed_edges=1.0,
        repair_objective_frac=0.2,
    )
    delta = ndcg_repair - ndcg_preserve
    outcome = "improves" if delta > 1e-12 else ("harms" if delta < -1e-12 else "no_change")
    return QueryGraphDiagnostic(
        key=(dataset, query_id, "src", "var", provider),
        dataset=dataset,
        query_id=query_id,
        provider=provider,
        pool_size=pool_size,
        ndcg_preserve=ndcg_preserve,
        ndcg_repair=ndcg_repair,
        delta=delta,
        outcome=outcome,
        pre_repair=pre,
        post_repair=post,
    )


class TestFeatureSeparation:
    def test_pre_and_post_feature_names_disjoint(self):
        assert set(PRE_REPAIR_FEATURE_NAMES).isdisjoint(set(POST_REPAIR_FEATURE_NAMES))

    def test_pre_repair_to_dict_only_pre_repair_names(self):
        from consistency_ranker.repair_diagnostic.features import PreRepairFeatures

        pre = PreRepairFeatures(
            n_nodes=5, n_edges=8, graph_density=0.4, pool_size=6, n_sccs=2, n_nontrivial_sccs=1,
            largest_scc_size=3, largest_scc_frac=0.6, is_cyclic=True, scc_cycle_weight=1.0,
            scc_cycle_weight_frac=0.3, edge_weight_mean=1.0, edge_weight_std=0.2,
            edge_weight_max=2.0, mean_edge_reliability=0.9, frac_edges_unanimous=0.8,
            provider_disagreement=0.05, topk_involvement=False, incumbent_topk_margin=2.0,
        )
        assert set(pre.to_dict()) == set(PRE_REPAIR_FEATURE_NAMES)
        numeric = pre.as_numeric_row()
        assert all(isinstance(v, float) for v in numeric.values())

    def test_post_repair_to_dict_only_post_repair_names(self):
        post = compute_post_repair_features(10.0, [("a", "b", 2.0), ("c", "d", 1.0)])
        assert set(post.to_dict()) == set(POST_REPAIR_FEATURE_NAMES)
        assert post.repair_objective == 3.0
        assert post.n_reversed_edges == 2
        assert post.repair_objective_frac == 0.3


class TestPreRepairFeatureComputation:
    def test_cyclic_graph_detected_with_correct_scc_cycle_weight(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0)
        g.add_edge("b", "c", weight=1.0)
        g.add_edge("c", "a", weight=1.0)
        g.add_edge("a", "d", weight=5.0)  # not part of any cycle
        feats = compute_pre_repair_features(g, pool_size=4)
        assert feats.is_cyclic is True
        assert feats.n_nontrivial_sccs == 1
        assert feats.largest_scc_size == 3
        assert feats.scc_cycle_weight == 3.0  # the 3-cycle's edges only
        assert feats.scc_cycle_weight_frac == 3.0 / 8.0

    def test_acyclic_graph_has_zero_scc_cycle_weight(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0)
        g.add_edge("b", "c", weight=1.0)
        feats = compute_pre_repair_features(g, pool_size=3)
        assert feats.is_cyclic is False
        assert feats.n_nontrivial_sccs == 0
        assert feats.scc_cycle_weight == 0.0


class TestOutcomeClassification:
    def test_evaluate_repair_outcome_matches_direct_computation(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=5.0)
        g.add_edge("b", "c", weight=5.0)
        g.add_edge("c", "a", weight=0.1)
        relevance = {"a": 2, "b": 1, "c": 0}
        diag = evaluate_repair_outcome(
            g, relevance, key=("ds", "q1", "s", "v", "p"), dataset="ds", query_id="q1",
            provider="p", pool_size=3,
        )
        assert diag.outcome in ("improves", "harms", "no_change")
        assert abs(diag.delta - (diag.ndcg_repair - diag.ndcg_preserve)) < 1e-12


class TestAssociation:
    def test_outcome_group_stats_groups_correctly(self):
        results = [
            _diag("ds", "q1", "p", 6, 0.5, 0.6),
            _diag("ds", "q2", "p", 6, 0.5, 0.4),
            _diag("ds", "q3", "p", 6, 0.5, 0.5),
        ]
        stats = outcome_group_stats(results)
        assert stats["improves"]["n"] == 1
        assert stats["harms"]["n"] == 1
        assert stats["no_change"]["n"] == 1

    def test_holm_pvalues_never_below_raw(self):
        results = [
            _diag("ds", f"q{i}", "p", 6, 0.5, 0.5 + (0.05 if i % 2 == 0 else -0.05))
            for i in range(10)
        ]
        associations = compute_feature_associations(results, reps=200)
        for a in associations:
            assert a.pvalue_holm is None or a.pvalue_holm >= a.pvalue_raw - 1e-9

    def test_feature_stability_flags_sign_flip(self):
        # Feature perfectly positively correlated with delta in group A,
        # perfectly negatively correlated in group B.
        results = []
        for i in range(5):
            r = _diag("A", f"q{i}", "p", 6, 0.5, 0.5 + 0.01 * i, incumbent_topk_margin=float(i))
            results.append(r)
        for i in range(5):
            r = _diag("B", f"q{i}", "p", 6, 0.5, 0.5 - 0.01 * i, incumbent_topk_margin=float(i))
            results.append(r)
        report = full_stability_report(results, ["incumbent_topk_margin"])
        by_dataset = report["incumbent_topk_margin"]["by_dataset"]
        assert by_dataset["A"]["correlation"] > 0.9
        assert by_dataset["B"]["correlation"] < -0.9

    def test_outlier_sensitivity_detects_single_outlier(self):
        results = [
            _diag("ds", "q1", "p", 6, 0.5, 0.9),
            _diag("ds", "q2", "p", 6, 0.5, 0.5),
            _diag("ds", "q3", "p", 6, 0.5, 0.5),
        ]
        out = outlier_sensitivity(results, drop_top_n=1)
        assert out["mean_delta_full"] > out["mean_delta_excluding_top_n"]
        assert out["mean_delta_excluding_top_n"] == 0.0


class TestPrediction:
    def test_baseline_policies_computed_correctly(self):
        results = [
            _diag("ds", "q1", "p", 6, 0.6, 0.8),
            _diag("ds", "q2", "p", 6, 0.4, 0.2),
        ]
        baselines = baseline_policies(results)
        assert baselines["never_repair"] == 0.5
        assert baselines["always_repair"] == 0.5
        assert baselines["random_selection"] == 0.5
        # mean(max(0.6,0.8), max(0.4,0.2)) = mean(0.8,0.4)
        assert baselines["oracle_selection"] == pytest.approx(0.6)

    def test_group_kfold_no_query_in_both_splits(self):
        import random

        from sklearn.model_selection import GroupKFold

        rng = random.Random(0)
        results = []
        for qi in range(6):
            for gi in range(3):
                delta = 0.05 if rng.random() < 0.5 else -0.05
                results.append(
                    _diag("ds", f"q{qi}", f"prov{gi}", 6, 0.5, 0.5 + delta)
                )
        groups = np.array([f"{r.dataset}::{r.query_id}" for r in results])
        gkf = GroupKFold(n_splits=4)
        for train_idx, test_idx in gkf.split(np.zeros(len(results)), None, groups):
            assert not (set(groups[train_idx]) & set(groups[test_idx]))

    def test_predictors_unsupported_on_tiny_data(self):
        results = [_diag("ds", "q1", "p", 6, 0.5, 0.6), _diag("ds", "q2", "p", 6, 0.5, 0.5)]
        result = evaluate_predictors(results)
        assert result["status"] == "UNSUPPORTED"

    def test_predictors_unsupported_on_extreme_class_imbalance(self):
        # Enough query groups to pass the group-count gate, but only a
        # single "improves" row overall -- must not silently produce a
        # trivially "perfect" balanced accuracy from folds with zero
        # positive test examples (see prediction.py's class-balance gate).
        results = [_diag("ds", "q0", "p", 6, 0.5, 0.6)]
        for qi in range(1, 6):
            for gi in range(3):
                results.append(_diag("ds", f"q{qi}", f"prov{gi}", 6, 0.5, 0.5))
        result = evaluate_predictors(results)
        assert result["status"] == "UNSUPPORTED"
        assert result["class_balance"]["positive"] == 1

    def test_subgroup_stability_fraction(self):
        row_a = {
            "dataset": "A", "provider": "p", "pool_size": 6,
            "policy_ndcg": 0.9, "ndcg_preserve": 0.5,
        }
        row_b = {
            "dataset": "B", "provider": "p", "pool_size": 6,
            "policy_ndcg": 0.3, "ndcg_preserve": 0.5,
        }
        model_result = {"oof_rows": [row_a, dict(row_a), row_b]}
        result = subgroup_stability(model_result, key_name="dataset")
        assert result["detail"]["A"]["passes"] is True
        assert result["detail"]["B"]["passes"] is False
        assert result["fraction_passing"] == 0.5


class TestDecision:
    _base_models = {
        "majority_class": {"mean_balanced_accuracy": 0.5},
        "single_feature_threshold": {"mean_balanced_accuracy": 0.55, "policy_mean_ndcg": 0.61},
        "shallow_decision_tree": {"mean_balanced_accuracy": 0.7, "policy_mean_ndcg": 0.63},
        "regularized_logistic_regression": {
            "mean_balanced_accuracy": 0.6,
            "policy_mean_ndcg": 0.60,
        },
        "control_shuffled_labels_logreg": {"mean_balanced_accuracy": 0.5},
        "control_random_features_logreg": {"mean_balanced_accuracy": 0.5},
    }

    def test_stable_regime_found_when_all_conditions_hold(self):
        result = decide(
            headroom_gate_decision="PROCEED_TO_LABELING",
            oracle_headroom_mean=0.03,
            predictor_status="EVALUATED",
            models=self._base_models,
            never_repair_ndcg=0.60,
            stability_pass_fraction=0.8,
        )
        assert result.decision == "STABLE_REPAIR_REGIME_FOUND"
        assert all(result.conditions.values())

    def test_weak_descriptive_pattern_when_not_stable(self):
        result = decide(
            headroom_gate_decision="AMBIGUOUS_NEED_MORE_DATA",
            oracle_headroom_mean=0.03,
            predictor_status="EVALUATED",
            models=self._base_models,
            never_repair_ndcg=0.60,
            stability_pass_fraction=0.2,  # fails stability
        )
        assert result.decision == "WEAK_DESCRIPTIVE_PATTERN_ONLY"

    def test_oracle_only_not_predictable(self):
        no_skill_models = {
            "majority_class": {"mean_balanced_accuracy": 0.5},
            "single_feature_threshold": {"mean_balanced_accuracy": 0.5, "policy_mean_ndcg": 0.5},
            "shallow_decision_tree": {"mean_balanced_accuracy": 0.5, "policy_mean_ndcg": 0.5},
            "regularized_logistic_regression": {
                "mean_balanced_accuracy": 0.5,
                "policy_mean_ndcg": 0.5,
            },
            "control_shuffled_labels_logreg": {"mean_balanced_accuracy": 0.5},
            "control_random_features_logreg": {"mean_balanced_accuracy": 0.5},
        }
        result = decide(
            headroom_gate_decision="PROCEED_TO_LABELING",
            oracle_headroom_mean=0.03,
            predictor_status="EVALUATED",
            models=no_skill_models,
            never_repair_ndcg=0.60,
            stability_pass_fraction=0.0,
        )
        assert result.decision == "ORACLE_ONLY_NOT_PREDICTABLE"

    def test_no_identifiable_regime_when_no_headroom(self):
        result = decide(
            headroom_gate_decision="NO_HEADROOM_DO_NOT_LEARN",
            oracle_headroom_mean=0.001,
            predictor_status="UNSUPPORTED",
            models={},
            never_repair_ndcg=0.60,
            stability_pass_fraction=0.0,
        )
        assert result.decision == "NO_IDENTIFIABLE_REPAIR_REGIME"
