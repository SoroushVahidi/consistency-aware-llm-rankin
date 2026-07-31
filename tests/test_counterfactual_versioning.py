"""Versioning invariants across counterfactual_micro_pilot_v1/v2 and
counterfactual_collector_canary_v1/v2.

v1 must stay byte-for-byte reproducible (its scientific meaning is frozen);
v2 must produce different hashes for the same queries and declare its
migration rationale; the collector must refuse any config that combines a
benchmark_version with the wrong pool_protocol_version.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from consistency_ranker.counterfactual_benchmark import config as config_mod
from consistency_ranker.counterfactual_benchmark.pool_builder import (
    POOL_PROTOCOL_VERSION,
    POOL_PROTOCOL_VERSION_V2,
    build_candidate_pool,
    build_candidate_pool_v2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
V1_MICRO_PILOT = REPO_ROOT / "configs" / "counterfactual_micro_pilot_v1.json"
V2_MICRO_PILOT = REPO_ROOT / "configs" / "counterfactual_micro_pilot_v2.json"
V1_CANARY = REPO_ROOT / "configs" / "counterfactual_collector_canary_v1.json"
V2_CANARY = REPO_ROOT / "configs" / "counterfactual_collector_canary_v2.json"

SCIDOCS_QUERY_ID = "01273bd34dacfe9ef887b320f36934d2f9fa9b34"
SCIDOCS_QUERY_TEXT = "Image-Guided Nanopositioning Scheme for SEM"
SCIDOCS_DOCS_PATH = REPO_ROOT / "data/processed/beir/scidocs/documents.jsonl"


# ---------------------------------------------------------------------------
# v1 remains reproducible
# ---------------------------------------------------------------------------


def test_v1_config_declares_v1_pool_protocol() -> None:
    cfg = config_mod.load_config(V1_MICRO_PILOT)
    assert cfg["candidate_pool"]["pool_protocol_version"] == POOL_PROTOCOL_VERSION
    config_mod.verify_frozen_contract(cfg, repo_root=REPO_ROOT)  # must not raise


def test_v1_canary_config_declares_v1_pool_protocol() -> None:
    cfg = config_mod.load_config(V1_CANARY)
    assert cfg["candidate_pool"]["pool_protocol_version"] == POOL_PROTOCOL_VERSION
    config_mod.verify_frozen_contract(cfg, repo_root=REPO_ROOT)  # must not raise


def test_v1_pool_hash_reproduces_the_frozen_canary_artifact() -> None:
    """The exact pool_hash recorded in
    reports/counterfactual_collector_canary_v1_20260727T145126Z/candidate_pools.jsonl
    must still be reproducible byte-for-byte -- v1's meaning is frozen."""
    pool = build_candidate_pool(
        dataset="scidocs",
        query_id=SCIDOCS_QUERY_ID,
        query_text=SCIDOCS_QUERY_TEXT,
        documents_path=SCIDOCS_DOCS_PATH,
        pool_size=10,
        max_candidate_chars=1200,
    )
    assert pool.pool_hash == "eb56c63dfba1322157a689ebdc2d083450ff1e374d8ecdcd290d12203149d030"


# ---------------------------------------------------------------------------
# v2 is a genuinely new, additive version
# ---------------------------------------------------------------------------


def test_v2_config_declares_v2_pool_protocol() -> None:
    cfg = config_mod.load_config(V2_MICRO_PILOT)
    assert cfg["candidate_pool"]["pool_protocol_version"] == POOL_PROTOCOL_VERSION_V2
    config_mod.verify_frozen_contract(cfg, repo_root=REPO_ROOT)  # must not raise


def test_v2_canary_config_declares_v2_pool_protocol() -> None:
    cfg = config_mod.load_config(V2_CANARY)
    assert cfg["candidate_pool"]["pool_protocol_version"] == POOL_PROTOCOL_VERSION_V2
    config_mod.verify_frozen_contract(cfg, repo_root=REPO_ROOT)  # must not raise


def test_v2_config_declares_a_migration_note() -> None:
    cfg = config_mod.load_config(V2_MICRO_PILOT)
    assert "migration_note" in cfg
    assert len(cfg["migration_note"]) > 100


def test_v2_config_keeps_v1_frozen_queries_prompt_and_schema_unchanged() -> None:
    """v2 changes only the pool protocol -- not the frozen queries, prompt,
    or judgment schema (those would be independent, unjustified changes)."""
    v1 = config_mod.load_config(V1_MICRO_PILOT)
    v2 = config_mod.load_config(V2_MICRO_PILOT)
    assert v1["prompt_sha256"] == v2["prompt_sha256"]
    assert v1["judgment_schema_sha256"] == v2["judgment_schema_sha256"]
    assert v1["datasets"] == v2["datasets"]
    assert v1["provider_panel"] == v2["provider_panel"]
    assert v1["candidate_pool"]["rendering_policy_version"] == (
        v2["candidate_pool"]["rendering_policy_version"]
    )
    assert v1["candidate_pool"]["pool_protocol_version"] != (
        v2["candidate_pool"]["pool_protocol_version"]
    )


def test_v2_pool_hash_differs_from_v1_for_the_same_query() -> None:
    v1_pool = build_candidate_pool(
        dataset="scidocs",
        query_id=SCIDOCS_QUERY_ID,
        query_text=SCIDOCS_QUERY_TEXT,
        documents_path=SCIDOCS_DOCS_PATH,
        pool_size=10,
        max_candidate_chars=1200,
    )
    v2_pool = build_candidate_pool_v2(
        dataset="scidocs",
        query_id=SCIDOCS_QUERY_ID,
        query_text=SCIDOCS_QUERY_TEXT,
        documents_path=SCIDOCS_DOCS_PATH,
        pool_size=10,
        max_candidate_chars=1200,
    )
    assert v1_pool.pool_hash != v2_pool.pool_hash
    assert v1_pool.candidate_ids != v2_pool.candidate_ids


# ---------------------------------------------------------------------------
# Cross-version combinations are refused
# ---------------------------------------------------------------------------


def test_v2_benchmark_version_with_v1_pool_protocol_is_refused() -> None:
    cfg = json.loads(json.dumps(config_mod.load_config(V2_MICRO_PILOT)))
    cfg["candidate_pool"]["pool_protocol_version"] = POOL_PROTOCOL_VERSION
    with pytest.raises(config_mod.FreezeMismatchError, match="pool_protocol_version"):
        config_mod.verify_frozen_contract(cfg, repo_root=REPO_ROOT)


def test_v1_benchmark_version_with_v2_pool_protocol_is_refused() -> None:
    cfg = json.loads(json.dumps(config_mod.load_config(V1_MICRO_PILOT)))
    cfg["candidate_pool"]["pool_protocol_version"] = POOL_PROTOCOL_VERSION_V2
    with pytest.raises(config_mod.FreezeMismatchError, match="pool_protocol_version"):
        config_mod.verify_frozen_contract(cfg, repo_root=REPO_ROOT)


def test_unknown_benchmark_version_is_refused() -> None:
    cfg = json.loads(json.dumps(config_mod.load_config(V1_MICRO_PILOT)))
    cfg["benchmark_version"] = "counterfactual_micro_pilot_v3_unregistered"
    with pytest.raises(config_mod.FreezeMismatchError, match="benchmark_version"):
        config_mod.verify_frozen_contract(cfg, repo_root=REPO_ROOT)


def test_collector_dispatches_to_matching_pool_builder(tmp_path: Path) -> None:
    from consistency_ranker.counterfactual_benchmark.collector import _build_pools

    v1_cfg = config_mod.load_config(V1_CANARY)
    _queries, v1_pools = _build_pools(v1_cfg, repo_root=REPO_ROOT)
    for pool in v1_pools.values():
        assert pool.pool_protocol_version == POOL_PROTOCOL_VERSION

    v2_cfg = config_mod.load_config(V2_CANARY)
    _queries2, v2_pools = _build_pools(v2_cfg, repo_root=REPO_ROOT)
    for pool in v2_pools.values():
        assert pool.pool_protocol_version == POOL_PROTOCOL_VERSION_V2


def test_unsupported_pool_protocol_version_rejected_by_build_pools() -> None:
    from consistency_ranker.counterfactual_benchmark.collector import (
        CollectorInputError,
        _build_pools,
    )

    cfg = json.loads(json.dumps(config_mod.load_config(V1_CANARY)))
    cfg["candidate_pool"]["pool_protocol_version"] = "lexical_prior_pool_v3_nonexistent"
    with pytest.raises(CollectorInputError, match="unsupported pool_protocol_version"):
        _build_pools(cfg, repo_root=REPO_ROOT)
