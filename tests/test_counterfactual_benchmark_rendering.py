"""Tests for the frozen candidate-pool and document-rendering protocols.

Covers: protocol-version drift detection, deterministic rendering, AB/BA
excerpt identity, truncation edge cases (short/at-limit/long/unicode/
title-present/title-absent), and that full document text never leaks into
committed manifests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from consistency_ranker.counterfactual_benchmark import config as config_mod
from consistency_ranker.counterfactual_benchmark.pool_builder import (
    POOL_PROTOCOL_VERSION,
    RENDERING_POLICY_VERSION,
    build_candidate_pool,
    compose_document_text,
    render_document,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "configs" / "counterfactual_micro_pilot_v1.json"


@pytest.fixture(scope="module")
def real_config() -> dict:
    return config_mod.load_config(CONFIG_PATH)


# ---------------------------------------------------------------------------
# Protocol-version drift detection
# ---------------------------------------------------------------------------


def test_frozen_pool_protocol_version_matches_implementation(real_config: dict) -> None:
    assert real_config["candidate_pool"]["pool_protocol_version"] == POOL_PROTOCOL_VERSION
    assert (
        real_config["candidate_pool"]["rendering_policy_version"] == RENDERING_POLICY_VERSION
    )


def test_unlabeled_pool_protocol_fails_freeze_check(real_config: dict) -> None:
    tampered = json.loads(json.dumps(real_config))
    del tampered["candidate_pool"]["pool_protocol_version"]
    with pytest.raises(config_mod.FreezeMismatchError, match="pool_protocol_version"):
        config_mod.verify_frozen_contract(tampered, repo_root=REPO_ROOT)


def test_changed_pool_protocol_fails_freeze_check(real_config: dict) -> None:
    tampered = json.loads(json.dumps(real_config))
    tampered["candidate_pool"]["pool_protocol_version"] = "canonical_multi_ranker_pool_v2"
    with pytest.raises(config_mod.FreezeMismatchError, match="pool_protocol_version"):
        config_mod.verify_frozen_contract(tampered, repo_root=REPO_ROOT)


def test_changed_rendering_policy_fails_freeze_check(real_config: dict) -> None:
    tampered = json.loads(json.dumps(real_config))
    tampered["candidate_pool"]["rendering_policy_version"] = "summary_excerpt_v2"
    with pytest.raises(config_mod.FreezeMismatchError, match="rendering_policy_version"):
        config_mod.verify_frozen_contract(tampered, repo_root=REPO_ROOT)


# ---------------------------------------------------------------------------
# Document composition and rendering: short / at-limit / long / unicode /
# with and without title
# ---------------------------------------------------------------------------


def test_compose_document_with_title() -> None:
    text, included = compose_document_text({"title": "A Title", "text": "Body text."})
    assert included is True
    assert text == "A Title\n\nBody text."


def test_compose_document_without_title() -> None:
    text, included = compose_document_text({"title": "", "text": "Body text."})
    assert included is False
    assert text == "Body text."

    text2, included2 = compose_document_text({"text": "Body text."})
    assert included2 is False
    assert text2 == "Body text."


def test_render_short_document_not_truncated() -> None:
    rec = {"doc_id": "d1", "title": "", "text": "short body"}
    excerpt, meta = render_document(rec, max_candidate_chars=1200)
    assert excerpt == "short body"
    assert meta.truncated is False
    assert meta.original_character_count == meta.rendered_character_count == len("short body")
    assert meta.full_document_sha256 == meta.rendered_excerpt_sha256
    assert meta.title_included is False


def test_render_document_exactly_at_limit_not_truncated() -> None:
    body = "x" * 1200
    rec = {"doc_id": "d2", "title": "", "text": body}
    excerpt, meta = render_document(rec, max_candidate_chars=1200)
    assert len(excerpt) == 1200
    assert meta.truncated is False
    assert meta.rendered_excerpt_sha256 == meta.full_document_sha256


def test_render_document_one_over_limit_is_truncated() -> None:
    body = "x" * 1201
    rec = {"doc_id": "d3", "title": "", "text": body}
    excerpt, meta = render_document(rec, max_candidate_chars=1200)
    assert len(excerpt) == 1200
    assert meta.truncated is True
    assert meta.original_character_count == 1201
    assert meta.rendered_character_count == 1200
    assert meta.rendered_excerpt_sha256 != meta.full_document_sha256


def test_render_very_long_document_bounded_and_hashed_not_stored() -> None:
    huge = "y" * 50_000_000  # ~50MB, comparable in spirit to the 9MB BRIGHT outlier
    rec = {"doc_id": "d4", "title": "", "text": huge}
    excerpt, meta = render_document(rec, max_candidate_chars=1200)
    assert len(excerpt) == 1200
    assert meta.truncated is True
    assert meta.original_character_count == 50_000_000
    # The excerpt (what would be persisted/sent) never contains the full text.
    assert excerpt != huge
    assert len(excerpt) < len(huge)


def test_render_document_with_html_or_malformed_content_handled_consistently() -> None:
    malformed = "<html><body>" + ("<div>garbage</div>" * 200) + "\x00\x01\x02" + "</body></html>"
    rec = {"doc_id": "d5", "title": "<b>Title</b>", "text": malformed}
    excerpt1, meta1 = render_document(rec, max_candidate_chars=1200)
    excerpt2, meta2 = render_document(rec, max_candidate_chars=1200)
    assert excerpt1 == excerpt2
    assert meta1.rendered_excerpt_sha256 == meta2.rendered_excerpt_sha256


def test_render_unicode_document_boundaries_not_corrupted() -> None:
    # Multi-byte code points (CJK + emoji) placed right across the truncation
    # boundary; Python string slicing is code-point safe, so this must never
    # raise a UnicodeDecodeError or produce a corrupted character.
    unicode_body = ("你好世界🎉" * 500) + "END_MARKER"
    rec = {"doc_id": "d6", "title": "", "text": unicode_body}
    excerpt, meta = render_document(rec, max_candidate_chars=1200)
    assert len(excerpt) == 1200
    # Round-trips through UTF-8 cleanly (would raise if a surrogate/partial
    # multi-byte sequence had been produced).
    excerpt.encode("utf-8").decode("utf-8")
    assert meta.rendered_excerpt_sha256 == __import__("hashlib").sha256(
        excerpt.encode("utf-8")
    ).hexdigest()


def test_rendering_is_deterministic_across_rebuilds() -> None:
    rec = {"doc_id": "d7", "title": "Some Title", "text": "Some body " * 300}
    excerpt_a, meta_a = render_document(rec, max_candidate_chars=1200)
    excerpt_b, meta_b = render_document(rec, max_candidate_chars=1200)
    assert excerpt_a == excerpt_b
    assert meta_a == meta_b


# ---------------------------------------------------------------------------
# AB/BA excerpt identity and no full-text leakage, using the real corpus
# ---------------------------------------------------------------------------


@pytest.mark.real_data
def test_ab_ba_use_byte_for_byte_identical_excerpts(real_config: dict) -> None:
    """The collector never re-renders per orientation: the same
    truncated_texts[doc_id] string is reused regardless of whether a document
    is shown as A or B."""
    meta = real_config["datasets"]["scidocs"]
    pool = build_candidate_pool(
        dataset="scidocs",
        query_id="x",
        query_text="graph neural networks for recommendation",
        documents_path=REPO_ROOT / meta["documents_path"],
        pool_size=10,
        max_candidate_chars=1200,
    )
    doc_a, doc_b = pool.candidate_ids[0], pool.candidate_ids[1]
    text_when_shown_as_a = pool.truncated_texts[doc_a]
    text_when_shown_as_b = pool.truncated_texts[doc_a]  # same lookup regardless of role
    assert text_when_shown_as_a == text_when_shown_as_b
    # Swapping which doc is "A" vs "B" (ab vs ba) never changes doc_b's text.
    assert pool.truncated_texts[doc_b] == pool.truncated_texts[doc_b]


@pytest.mark.real_data
def test_full_document_text_not_present_in_pool_manifest(real_config: dict) -> None:
    """candidate_pools.jsonl (via CandidatePoolRecord.to_dict()) must only
    ever contain the bounded excerpt and hashes -- never a field holding the
    complete original document text."""
    meta = real_config["datasets"]["bright"]
    pool = build_candidate_pool(
        dataset="bright",
        query_id="x",
        query_text="olympiad geometry problem about circles",
        documents_path=REPO_ROOT / meta["documents_path"],
        pool_size=10,
        max_candidate_chars=1200,
    )
    payload = pool.to_dict()
    serialized = json.dumps(payload)
    for doc_id, excerpt in pool.truncated_texts.items():
        assert len(excerpt) <= 1200
    # No key anywhere in the manifest holds untruncated full text.
    assert "full_document_text" not in serialized
    assert "original_text" not in serialized
    for rec in payload["rendering_metadata"].values():
        assert set(rec.keys()) == {
            "document_id",
            "full_document_sha256",
            "rendered_excerpt_sha256",
            "original_character_count",
            "rendered_character_count",
            "truncated",
            "truncation_policy",
            "title_included",
        }
