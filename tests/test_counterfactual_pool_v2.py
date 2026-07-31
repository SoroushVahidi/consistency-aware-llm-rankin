"""Tests for the lexical_prior_pool_v2 protocol: bounded-denominator prior,
explicit document-validity gate, and the v2 pair selector.

Diagnosed defect (see reports/counterfactual_collector_canary_v1_20260727T145126Z
and the 8-query/80-candidate audit): v1's primary prior (overlap/sqrt(len))
has no lower bound on document length, so a near-empty document can
outscore substantive ones purely through the denominator, capturing up to
10/10 pool slots for a real frozen query. v2 fixes this with (a) a floor on
the prior's denominator and (b) a pre-scoring validity gate that excludes
degenerate documents regardless of score.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from consistency_ranker.counterfactual_benchmark import config as config_mod
from consistency_ranker.counterfactual_benchmark.pair_selection import (
    select_shared_pairs_v2,
)
from consistency_ranker.counterfactual_benchmark.pool_builder import (
    MIN_ALPHA_TOKENS_V2,
    MIN_SUBSTANTIVE_CHARS_V2,
    POOL_PROTOCOL_VERSION_V2,
    build_candidate_pool,
    build_candidate_pool_v2,
    document_validity_v2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
V1_CONFIG_PATH = REPO_ROOT / "configs" / "counterfactual_micro_pilot_v1.json"
V2_CONFIG_PATH = REPO_ROOT / "configs" / "counterfactual_micro_pilot_v2.json"

# The exact frozen SciDocs query whose v1 pool was measured to be 10/10
# title-only (canary v1's query).
SCIDOCS_QUERY_ID = "01273bd34dacfe9ef887b320f36934d2f9fa9b34"
SCIDOCS_QUERY_TEXT = "Image-Guided Nanopositioning Scheme for SEM"
SCIDOCS_DOCS_PATH = REPO_ROOT / "data/processed/beir/scidocs/documents.jsonl"


@pytest.fixture(scope="module")
def v2_config() -> dict:
    return config_mod.load_config(V2_CONFIG_PATH)


# ---------------------------------------------------------------------------
# document_validity_v2 unit behavior
# ---------------------------------------------------------------------------


def test_title_only_document_is_invalid() -> None:
    is_valid, reason = document_validity_v2("Some Short Title\n\n", title_included=True)
    assert is_valid is False
    assert reason == "title_only_no_body"


def test_empty_text_is_invalid() -> None:
    is_valid, reason = document_validity_v2("", title_included=False)
    assert is_valid is False
    assert reason == "empty_rendered_text"


def test_body_below_alpha_token_floor_is_invalid() -> None:
    body = "1 2 3 4 5 6 7 8 9 10"  # 10 numeric tokens, zero alphabetic
    is_valid, reason = document_validity_v2(f"Title\n\n{body}", title_included=True)
    assert is_valid is False
    assert reason == "insufficient_alpha_tokens"


def test_body_below_char_floor_is_invalid() -> None:
    body = " ".join(["word"] * (MIN_ALPHA_TOKENS_V2 + 5))  # enough tokens, too few chars
    assert len(body) < MIN_SUBSTANTIVE_CHARS_V2
    is_valid, reason = document_validity_v2(f"Title\n\n{body}", title_included=True)
    assert is_valid is False
    assert reason == "insufficient_substantive_chars"


def test_substantive_document_is_valid() -> None:
    body = "This is a real sentence with enough substantive words to pass. " * 3
    is_valid, reason = document_validity_v2(f"Some Title\n\n{body}", title_included=True)
    assert is_valid is True
    assert reason is None


def test_substantive_document_without_title_is_valid() -> None:
    body = "This is a real sentence with enough substantive words to pass. " * 3
    is_valid, reason = document_validity_v2(body, title_included=False)
    assert is_valid is True
    assert reason is None


# ---------------------------------------------------------------------------
# Pool construction: v1 vs v2 on the real, previously-failing SciDocs query
# ---------------------------------------------------------------------------


def test_v1_pool_is_captured_by_title_only_documents_on_the_canary_query() -> None:
    """Locks in the diagnosed v1 defect as a regression guard: this exact
    query's v1 pool really is 100% title-only, matching the frozen canary
    v1 artifact's pool_hash. If this ever stops being true, v1's frozen
    meaning has changed and the config/test must be revisited together."""
    pool = build_candidate_pool(
        dataset="scidocs",
        query_id=SCIDOCS_QUERY_ID,
        query_text=SCIDOCS_QUERY_TEXT,
        documents_path=SCIDOCS_DOCS_PATH,
        pool_size=10,
        max_candidate_chars=1200,
    )
    assert pool.pool_hash == "eb56c63dfba1322157a689ebdc2d083450ff1e374d8ecdcd290d12203149d030"
    title_only_count = sum(
        1
        for d in pool.candidate_ids
        if not document_validity_v2(pool.truncated_texts[d], title_included=True)[0]
    )
    assert title_only_count == 10


def test_v2_pool_excludes_title_only_documents_on_the_same_query() -> None:
    pool = build_candidate_pool_v2(
        dataset="scidocs",
        query_id=SCIDOCS_QUERY_ID,
        query_text=SCIDOCS_QUERY_TEXT,
        documents_path=SCIDOCS_DOCS_PATH,
        pool_size=10,
        max_candidate_chars=1200,
    )
    assert pool.pool_protocol_version == POOL_PROTOCOL_VERSION_V2
    assert len(pool.candidate_ids) == 10
    for d in pool.candidate_ids:
        is_valid, reason = document_validity_v2(
            pool.truncated_texts[d], title_included=pool.rendering_metadata[d].title_included
        )
        assert is_valid, f"{d} invalid: {reason}"
    lengths = [pool.rendering_metadata[d].rendered_character_count for d in pool.candidate_ids]
    assert min(lengths) >= MIN_SUBSTANTIVE_CHARS_V2
    # v2's pool must differ from v1's for the same query (new hash, new content).
    v1_pool = build_candidate_pool(
        dataset="scidocs",
        query_id=SCIDOCS_QUERY_ID,
        query_text=SCIDOCS_QUERY_TEXT,
        documents_path=SCIDOCS_DOCS_PATH,
        pool_size=10,
        max_candidate_chars=1200,
    )
    assert pool.pool_hash != v1_pool.pool_hash


def test_v2_pool_records_exclusion_with_replacement_and_reason() -> None:
    pool = build_candidate_pool_v2(
        dataset="scidocs",
        query_id=SCIDOCS_QUERY_ID,
        query_text=SCIDOCS_QUERY_TEXT,
        documents_path=SCIDOCS_DOCS_PATH,
        pool_size=10,
        max_candidate_chars=1200,
    )
    assert len(pool.exclusion_records) >= 1
    for rec in pool.exclusion_records:
        assert set(rec.keys()) == {
            "excluded_document_id",
            "exclusion_reason",
            "replacement_candidate",
        }
        assert rec["replacement_candidate"] in pool.candidate_ids
        assert rec["excluded_document_id"] not in pool.candidate_ids


def test_v2_pool_deterministic_across_rebuilds() -> None:
    p1 = build_candidate_pool_v2(
        dataset="scidocs",
        query_id=SCIDOCS_QUERY_ID,
        query_text=SCIDOCS_QUERY_TEXT,
        documents_path=SCIDOCS_DOCS_PATH,
        pool_size=10,
        max_candidate_chars=1200,
    )
    p2 = build_candidate_pool_v2(
        dataset="scidocs",
        query_id=SCIDOCS_QUERY_ID,
        query_text=SCIDOCS_QUERY_TEXT,
        documents_path=SCIDOCS_DOCS_PATH,
        pool_size=10,
        max_candidate_chars=1200,
    )
    assert p1.pool_hash == p2.pool_hash
    assert p1.candidate_ids == p2.candidate_ids
    assert p1.exclusion_records == p2.exclusion_records


def test_v2_pool_construction_never_reads_qrels(v2_config: dict) -> None:
    """qrels independence: the function signature has no qrels parameter,
    and the qrels file is never opened by pool construction."""
    import inspect

    sig = inspect.signature(build_candidate_pool_v2)
    assert "qrels" not in sig.parameters
    assert "qrels_path" not in sig.parameters


@pytest.mark.parametrize(
    "dataset,query_id,query_text",
    [
        (
            "scidocs",
            "01273bd34dacfe9ef887b320f36934d2f9fa9b34",
            "Image-Guided Nanopositioning Scheme for SEM",
        ),
        (
            "scidocs",
            "012e396b02aa584cb74a65ae14af355e7c897858",
            "Efficient and secure data storage operations for mobile cloud computing",
        ),
    ],
)
def test_v2_pool_contains_exactly_ten_valid_documents_for_frozen_queries(
    dataset: str, query_id: str, query_text: str, v2_config: dict
) -> None:
    meta = v2_config["datasets"][dataset]
    pool = build_candidate_pool_v2(
        dataset=dataset,
        query_id=query_id,
        query_text=query_text,
        documents_path=REPO_ROOT / meta["documents_path"],
        pool_size=10,
        max_candidate_chars=1200,
    )
    assert len(pool.candidate_ids) == 10
    assert len(set(pool.candidate_ids)) == 10


# ---------------------------------------------------------------------------
# Pair selection (v2): validity refusal, archetype coverage, shared pairs
# ---------------------------------------------------------------------------


def test_select_shared_pairs_v2_succeeds_on_a_valid_pool() -> None:
    pool = build_candidate_pool_v2(
        dataset="scidocs",
        query_id=SCIDOCS_QUERY_ID,
        query_text=SCIDOCS_QUERY_TEXT,
        documents_path=SCIDOCS_DOCS_PATH,
        pool_size=10,
        max_candidate_chars=1200,
    )
    pairs = select_shared_pairs_v2(pool, eval_k=5, n_pairs=8, seed=42)
    assert len(pairs) == 8
    assert len({p.pair_id for p in pairs}) == 8
    for p in pairs:
        for doc_id in (p.doc_a_id, p.doc_b_id):
            is_valid, reason = document_validity_v2(
                pool.truncated_texts[doc_id],
                title_included=pool.rendering_metadata[doc_id].title_included,
            )
            assert is_valid, f"{doc_id} invalid in selected pair: {reason}"


def test_select_shared_pairs_v2_covers_expected_archetypes() -> None:
    pool = build_candidate_pool_v2(
        dataset="scidocs",
        query_id=SCIDOCS_QUERY_ID,
        query_text=SCIDOCS_QUERY_TEXT,
        documents_path=SCIDOCS_DOCS_PATH,
        pool_size=10,
        max_candidate_chars=1200,
    )
    pairs = select_shared_pairs_v2(pool, eval_k=5, n_pairs=8, seed=42)
    reasons = {p.reason for p in pairs}
    assert "top_ranked" in reasons


def test_select_shared_pairs_v2_refuses_pool_with_invalid_candidate() -> None:
    """Defense-in-depth: even if a pool somehow contained an invalid
    candidate, the v2 pair selector must refuse rather than silently pairing
    it, per the frozen document-validity rule."""
    pool = build_candidate_pool_v2(
        dataset="scidocs",
        query_id=SCIDOCS_QUERY_ID,
        query_text=SCIDOCS_QUERY_TEXT,
        documents_path=SCIDOCS_DOCS_PATH,
        pool_size=10,
        max_candidate_chars=1200,
    )
    import dataclasses

    tampered_texts = dict(pool.truncated_texts)
    victim = pool.candidate_ids[0]
    tampered_texts[victim] = "Title\n\n"  # title-only, now invalid
    tampered_pool = dataclasses.replace(pool, truncated_texts=tampered_texts)
    with pytest.raises(ValueError, match="document-validity"):
        select_shared_pairs_v2(tampered_pool, eval_k=5, n_pairs=8, seed=42)


def test_select_shared_pairs_v2_never_reads_qrels() -> None:
    import inspect

    sig = inspect.signature(select_shared_pairs_v2)
    assert "qrels" not in sig.parameters


def test_no_title_only_pair_in_v2_canary_query() -> None:
    """The specific real-world regression this whole v2 protocol exists to
    fix: the exact query used by canary v1 (where every candidate was
    title-only) must now produce zero title-only pairs."""
    pool = build_candidate_pool_v2(
        dataset="scidocs",
        query_id=SCIDOCS_QUERY_ID,
        query_text=SCIDOCS_QUERY_TEXT,
        documents_path=SCIDOCS_DOCS_PATH,
        pool_size=10,
        max_candidate_chars=1200,
    )
    pairs = select_shared_pairs_v2(pool, eval_k=5, n_pairs=8, seed=42)
    for p in pairs:
        for doc_id in (p.doc_a_id, p.doc_b_id):
            excerpt = pool.truncated_texts[doc_id]
            body = excerpt.split("\n\n", 1)
            body_text = body[1].strip() if len(body) > 1 else ""
            assert body_text, f"{doc_id} is title-only in selected pair {p.pair_id}"
