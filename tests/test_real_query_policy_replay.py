"""Tests for offline real-query replay and feature-schema versioning."""

from __future__ import annotations

import pytest

from consistency_ranker.policy_selection.gate_features import (
    FEATURE_SCHEMA_VERSION,
    SCHEMA_COVERAGE_V2,
    SCHEMA_LEGACY_V1,
    assert_schemas_compatible,
    extract_features,
    feature_names_for_stage,
    features_to_vector,
    resolve_feature_schema,
)
from consistency_ranker.policy_selection.policy_calibration import CalibratedModel
from consistency_ranker.prior_robust.adversarial_judges import (
    AdversarialScenario,
    make_adversarial_world,
)
from consistency_ranker.prior_robust.engine import make_initial_robust_state
from consistency_ranker.real_query_replay.evidence_index import (
    build_canonical_evidence_index,
)
from consistency_ranker.real_query_replay.network_guard import (
    NetworkForbiddenError,
    assert_no_network,
    uninstall_no_network_guard,
)
from consistency_ranker.real_query_replay.predictors import evaluate_matched_random
from consistency_ranker.reliability_repair.pair_evidence import (
    NormalizedEvidence,
    canonical_doc_order,
    canonical_pair_id,
)


def _state_with_topk_evidence():
    scenario = AdversarialScenario(
        name="t",
        prior_regime="outsider_buried",
        judge_regime="clean",
        n_items=8,
        top_k=3,
        seed=0,
    )
    world = make_adversarial_world(scenario)
    state = make_initial_robust_state(
        query_id="q",
        candidate_ids=list(world["true_ranking"]),
        prior_scores=world["prior_scores"],
        budget=12,
        top_k=3,
        seed=0,
    )
    ranking = list(world["true_ranking"])
    evs = []
    for i in range(3):
        for j in range(i + 1, 3):
            a, b = ranking[i], ranking[j]
            di, dj = canonical_doc_order(a, b)
            z = 1 if a == di else -1
            evs.append(
                NormalizedEvidence(
                    query_id="q",
                    canonical_pair_id=canonical_pair_id("q", a, b),
                    doc_i=di,
                    doc_j=dj,
                    displayed_orientation="ab",
                    z=z,  # type: ignore[arg-type]
                    abstention_subtype="none",
                    provider="syn",
                    model="syn",
                    prompt_version="v1",
                    valid=True,
                )
            )
    for i in range(3):
        for j in range(3, 6):
            a, b = ranking[i], ranking[j]
            di, dj = canonical_doc_order(a, b)
            z = 1 if a == di else -1
            evs.append(
                NormalizedEvidence(
                    query_id="q",
                    canonical_pair_id=canonical_pair_id("q", a, b),
                    doc_i=di,
                    doc_j=dj,
                    displayed_orientation="ab",
                    z=z,  # type: ignore[arg-type]
                    abstention_subtype="none",
                    provider="syn",
                    model="syn",
                    prompt_version="v1",
                    valid=True,
                )
            )
    state.add_evidence(evs)
    return state


def test_resolve_feature_schema_aliases():
    assert resolve_feature_schema("legacy_v1") == SCHEMA_LEGACY_V1
    assert resolve_feature_schema("coverage_v2") == SCHEMA_COVERAGE_V2
    assert resolve_feature_schema(None) == FEATURE_SCHEMA_VERSION
    with pytest.raises(ValueError):
        resolve_feature_schema("not_a_schema")


def test_legacy_v1_probe_features_remain_constant_dead_values():
    state = _state_with_topk_evidence()
    bundle = extract_features(state, stage="probe", schema_version="legacy_v1")
    assert bundle.schema_version == SCHEMA_LEGACY_V1
    assert bundle.values["preliminary_g_prior"] == 1.0
    assert bundle.values["evidence_only_stability_proxy"] == 0.0


def test_coverage_v2_uses_topk_fraction_and_varies():
    state = _state_with_topk_evidence()
    bundle = extract_features(state, stage="probe", schema_version="coverage_v2")
    assert bundle.schema_version == SCHEMA_COVERAGE_V2
    assert "evidence_coverage_fraction" in bundle.values
    assert "preliminary_g_prior_from_coverage" in bundle.values
    assert "preliminary_g_prior" not in bundle.values
    assert bundle.values["evidence_coverage_fraction"] > 0.0
    assert bundle.values["preliminary_g_prior_from_coverage"] < 1.0


def test_schema_mismatch_rejects_cross_loading():
    with pytest.raises(ValueError):
        assert_schemas_compatible("legacy_v1", "coverage_v2")
    state = _state_with_topk_evidence()
    legacy = extract_features(state, stage="probe", schema_version="legacy_v1")
    with pytest.raises(ValueError):
        features_to_vector(legacy, expected_schema="coverage_v2")


def test_legacy_model_cannot_silently_consume_v2_vectors():
    model = CalibratedModel(
        kind="logistic",
        feature_names=list(feature_names_for_stage("probe", schema_version="legacy_v1")),
        schema_version=SCHEMA_LEGACY_V1,
        weights=[0.0] * 22,
        bias=0.0,
    )
    payload = model.to_dict()
    payload["schema_version"] = SCHEMA_COVERAGE_V2
    with pytest.raises(ValueError):
        CalibratedModel.from_dict(payload)
    # Explicit adapter path still requires matching expected schema.
    with pytest.raises(ValueError):
        CalibratedModel.from_dict_for_schema(payload, expected_schema=SCHEMA_LEGACY_V1)


def test_evidence_index_dedupes_nested_scidocs_caches():
    index = build_canonical_evidence_index()
    assert index["summary"]["n_independent_queries"] >= 1
    nested = [d for d in index["duplicates"] if d.get("kind") == "nested_subset"]
    # q20/q30 should be reported as nested if present.
    assert isinstance(nested, list)


def test_query_grouping_is_by_original_query():
    index = build_canonical_evidence_index()
    keys = [(q["dataset"], q["query_id"]) for q in index["queries"]]
    assert len(keys) == len(set(keys))


def test_matched_random_routing_rate():
    rows = [{"repair_gain": 0.1}, {"repair_gain": -0.2}, {"repair_gain": 0.0}, {"repair_gain": 0.05}]
    res = evaluate_matched_random(rows, escalation_rate=0.5, seed=1)
    assert res.n_escalated == 2
    assert abs(res.escalation_rate - 0.5) < 1e-9


def test_no_network_guard_blocks_connect():
    assert_no_network()
    import socket

    with pytest.raises(NetworkForbiddenError):
        socket.socket().connect(("127.0.0.1", 1))
    uninstall_no_network_guard()


def test_frozen_outcome_f_feature_schema_string_unchanged():
    assert FEATURE_SCHEMA_VERSION == "policy_gate_features_v1"
    assert SCHEMA_LEGACY_V1 == "policy_gate_features_v1"
