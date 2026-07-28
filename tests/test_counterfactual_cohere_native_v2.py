"""Offline tests for the native Cohere ClientV2 transport
(``counterfactual_benchmark.cohere_native``).

Context: two bounded live calls through Cohere's OpenAI-compatibility
endpoint (archived at archive/cohere-compat-schema-failed-20260727, commit
0646fde88a3d529ce4ebd4a4c2d5b6d3b21074a2) both returned syntactically valid
but schema-invalid JSON. This module implements and tests a genuinely
different transport (Cohere's native Chat API v2) before spending the one
authorized live confirmation call. All tests here use dependency injection
(``chat_fn``) -- no network, no real credentials required.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

import pytest

from consistency_ranker.counterfactual_benchmark.cache_store import JudgmentCacheStore
from consistency_ranker.counterfactual_benchmark.cohere_native import (
    COHERE_NATIVE_V2_JSON_SCHEMA_PROTOCOL_VERSION,
    COHERE_NATIVE_V2_TRANSPORT_FAMILY,
    FROZEN_COHERE_MODEL_ID,
    CohereNativeConfigError,
    call_cohere_native,
    native_cohere_ready,
)
from consistency_ranker.counterfactual_benchmark.cohere_schema_projection import (
    SCHEMA_PROJECTION_PROTOCOL_VERSION,
    build_cohere_schema_projection,
)
from consistency_ranker.counterfactual_pilot.schema import (
    extract_json_payload,
    load_json_schema,
    validate_judgment,
)

FROZEN_SCHEMA = load_json_schema()
VALID_JUDGMENT = {
    "schema_version": "counterfactual_pairwise_judgment_v1",
    "preference": "ABSTAIN",
    "confidence": 0.8,
    "evidence_strength": "strong",
    "reason_code": "unsupported",
}


@pytest.fixture(autouse=True)
def _fake_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COHERE_API_KEY", "fake-key-not-real")


# --- fake native response scaffolding (duck-typed, no cohere SDK import) --


@dataclass
class _FakeContentItem:
    type: str
    text: str | None = None
    thinking: str | None = None


@dataclass
class _FakeMessage:
    content: list[_FakeContentItem] = field(default_factory=list)
    citations: list[Any] | None = None
    tool_calls: list[Any] | None = None


@dataclass
class _FakeTokens:
    input_tokens: float | None = None
    output_tokens: float | None = None


@dataclass
class _FakeUsage:
    tokens: _FakeTokens | None = None


@dataclass
class _FakeV2ChatResponse:
    message: _FakeMessage
    finish_reason: str = "COMPLETE"
    usage: _FakeUsage | None = None


def _text_response(text: str, *, prompt_tokens: int = 100, completion_tokens: int = 20):
    return _FakeV2ChatResponse(
        message=_FakeMessage(content=[_FakeContentItem(type="text", text=text)]),
        usage=_FakeUsage(
            tokens=_FakeTokens(input_tokens=prompt_tokens, output_tokens=completion_tokens)
        ),
    )


# ---------------------------------------------------------------------------
# Request-capture tests
# ---------------------------------------------------------------------------


def test_native_request_uses_frozen_model_and_projected_schema() -> None:
    """The wire schema is the deterministic Cohere-compatible *projection*,
    not the canonical schema verbatim -- confidence's minimum/maximum are
    Cohere-unsupported generation-time constraints and must not be sent."""
    captured: dict[str, Any] = {}

    def fake_chat(**kwargs: Any):
        captured.update(kwargs)
        return _text_response(json.dumps(VALID_JUDGMENT))

    call_cohere_native(
        model_id=FROZEN_COHERE_MODEL_ID,
        prompt="hello",
        temperature=0.0,
        max_tokens=128,
        chat_fn=fake_chat,
    )
    assert captured["model"] == FROZEN_COHERE_MODEL_ID
    assert captured["temperature"] == 0.0
    assert captured["max_tokens"] == 128
    rf = captured["response_format"]
    assert rf["type"] == "json_object"
    schema = rf["json_schema"]
    assert schema != FROZEN_SCHEMA  # projected, not canonical, is sent
    assert schema["required"] == [
        "schema_version",
        "preference",
        "confidence",
        "evidence_strength",
        "reason_code",
    ]
    assert schema["properties"]["preference"]["enum"] == ["A", "B", "TIE", "ABSTAIN"]
    assert schema["properties"]["evidence_strength"]["enum"] == ["weak", "moderate", "strong"]
    assert schema["properties"]["schema_version"]["const"] == (
        "counterfactual_pairwise_judgment_v1"
    )
    assert schema["properties"]["schema_version"]["type"] == "string"
    assert "minimum" not in schema["properties"]["confidence"]
    assert "maximum" not in schema["properties"]["confidence"]
    assert schema["additionalProperties"] is False
    assert captured["messages"] == [{"role": "user", "content": "hello"}]


def test_projection_provenance_recorded_on_every_result() -> None:
    result = _run(lambda **kw: _text_response(json.dumps(VALID_JUDGMENT)))
    assert result.canonical_schema_sha256 is not None
    assert result.provider_schema_sha256 is not None
    assert result.canonical_schema_sha256 != result.provider_schema_sha256
    assert result.schema_projection_protocol == "cohere_native_v2_schema_projection_v3"
    pointers = {c["json_pointer"] for c in result.removed_constraints}
    assert pointers == {
        "/properties/confidence/minimum",
        "/properties/confidence/maximum",
        "/$id",
    }
    added_pointers = {a["json_pointer"] for a in result.added_type_annotations}
    assert added_pointers == {"/properties/schema_version/type"}
    assert result.added_type_annotations[0]["inferred_value"] == "string"


def test_recorded_canonical_hash_matches_the_well_known_frozen_constant() -> None:
    """Regression: an earlier version hashed the re-serialized dict, which
    silently diverged from CANONICAL_SCHEMA_SHA256 (the raw-file-bytes hash
    used everywhere else in the repo, e.g. config.py's
    verify_frozen_contract and every counterfactual_* config's
    judgment_schema_sha256). The provenance record must use the same
    well-known value, not a locally-recomputed one."""
    from consistency_ranker.counterfactual_benchmark.cohere_schema_projection import (
        CANONICAL_SCHEMA_SHA256,
    )

    result = _run(lambda **kw: _text_response(json.dumps(VALID_JUDGMENT)))
    assert result.canonical_schema_sha256 == CANONICAL_SCHEMA_SHA256
    assert result.canonical_schema_sha256 == (
        "f8332b7eadcbe92e1c4aed5299a0e3b1214c6d53a68aff3c826fe86147366de7"
    )


def test_failure_stage_for_rejection_before_generation() -> None:
    def fake_chat(**kw: Any):
        import cohere

        raise cohere.BadRequestError(body={"message": "bad schema"}, headers={})

    result = _run(fake_chat)
    assert result.failure_stage == "request_rejected_before_generation"
    assert result.provider_call_attempted is True
    assert result.generation_started is False
    assert result.billable_tokens == 0


def test_failure_stage_for_missing_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COHERE_API_KEY", raising=False)
    result = _run(lambda **kw: (_ for _ in ()).throw(AssertionError("unreachable")))
    assert result.failure_stage == "client_configuration_failure"
    assert result.provider_call_attempted is False
    assert result.generation_started is False


def test_generation_started_and_billable_tokens_on_success() -> None:
    result = _run(
        lambda **kw: _text_response(
            json.dumps(VALID_JUDGMENT), prompt_tokens=50, completion_tokens=10
        )
    )
    assert result.generation_started is True
    assert result.provider_call_attempted is True
    assert result.failure_stage is None
    assert result.billable_tokens == 60


def test_native_request_rejects_wrong_model_id() -> None:
    with pytest.raises(CohereNativeConfigError, match="frozen to model_id"):
        call_cohere_native(
            model_id="command-r-plus-04-2024",
            prompt="hello",
            temperature=0.0,
            max_tokens=128,
            chat_fn=lambda **kw: _text_response(json.dumps(VALID_JUDGMENT)),
        )


def test_native_request_rejects_mismatched_schema() -> None:
    tampered = json.loads(json.dumps(FROZEN_SCHEMA))
    tampered["properties"]["evidence_strength"]["enum"].append("unsupported")
    with pytest.raises(CohereNativeConfigError, match="does not match the frozen"):
        call_cohere_native(
            model_id=FROZEN_COHERE_MODEL_ID,
            prompt="hello",
            temperature=0.0,
            max_tokens=128,
            judgment_schema=tampered,
            chat_fn=lambda **kw: _text_response(json.dumps(VALID_JUDGMENT)),
        )


def test_native_ready_check_is_narrower_than_compat_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COHERE_API_KEY", raising=False)
    monkeypatch.setenv("COHERE_BASE_URL", "https://api.cohere.ai/compatibility/v1")
    ready, reason = native_cohere_ready()
    assert ready is False
    assert "missing_env" in reason


def test_missing_credentials_never_reaches_chat_fn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COHERE_API_KEY", raising=False)

    def boom(**kwargs: Any):
        raise AssertionError("must never dispatch when credentials are missing")

    result = call_cohere_native(
        model_id=FROZEN_COHERE_MODEL_ID,
        prompt="hello",
        temperature=0.0,
        max_tokens=128,
        chat_fn=boom,
    )
    assert result.error_category == "missing_credentials"
    assert result.raw_text is None


# ---------------------------------------------------------------------------
# Response-shape tests (16 cases from the task spec)
# ---------------------------------------------------------------------------


def _run(chat_fn):
    return call_cohere_native(
        model_id=FROZEN_COHERE_MODEL_ID,
        prompt="hello",
        temperature=0.0,
        max_tokens=128,
        chat_fn=chat_fn,
    )


def _parse(result) -> tuple[bool, str | None]:
    """(parse_failed, error) using the real production parse path."""
    if result.raw_text is None:
        return True, "no_text"
    text, _unwrapped = extract_json_payload(result.raw_text)
    try:
        validate_judgment(json.loads(text))
        return False, None
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        return True, str(exc)


def test_case1_valid_bare_json() -> None:
    result = _run(lambda **kw: _text_response(json.dumps(VALID_JUDGMENT)))
    parse_failed, _ = _parse(result)
    assert result.error_category is None
    assert parse_failed is False


def test_case2_valid_bare_json_text_identical_to_case1() -> None:
    # "valid native parsed JSON object" vs "valid bare JSON text" collapse to
    # the same representation once extracted: this transport always yields a
    # text block (json_schema mode does not return a pre-parsed object).
    result = _run(lambda **kw: _text_response(json.dumps(VALID_JUDGMENT)))
    assert result.raw_text == json.dumps(VALID_JUDGMENT)


def test_case3_valid_single_fenced_json_block() -> None:
    fenced = f"```json\n{json.dumps(VALID_JUDGMENT)}\n```"
    result = _run(lambda **kw: _text_response(fenced))
    text, unwrapped = extract_json_payload(result.raw_text)
    assert unwrapped is True
    validate_judgment(json.loads(text))  # must not raise


def test_case4_invalid_evidence_strength() -> None:
    bad = {**VALID_JUDGMENT, "evidence_strength": "unsupported"}
    result = _run(lambda **kw: _text_response(json.dumps(bad)))
    parse_failed, err = _parse(result)
    assert parse_failed is True
    assert err is not None and "evidence_strength" in err


def test_case5_invalid_reason_code() -> None:
    bad = {**VALID_JUDGMENT, "reason_code": "strong"}
    result = _run(lambda **kw: _text_response(json.dumps(bad)))
    parse_failed, err = _parse(result)
    assert parse_failed is True
    assert err is not None and "reason_code" in err


def test_case6_missing_required_field() -> None:
    bad = {k: v for k, v in VALID_JUDGMENT.items() if k != "reason_code"}
    result = _run(lambda **kw: _text_response(json.dumps(bad)))
    parse_failed, _ = _parse(result)
    assert parse_failed is True


def test_case7_wrong_schema_version() -> None:
    bad = {**VALID_JUDGMENT, "schema_version": "counterfactual_pairwise_judgment_v2"}
    result = _run(lambda **kw: _text_response(json.dumps(bad)))
    parse_failed, err = _parse(result)
    assert parse_failed is True
    assert err is not None and "schema_version" in err


def test_case8_confidence_as_string() -> None:
    bad = {**VALID_JUDGMENT, "confidence": "high"}
    result = _run(lambda **kw: _text_response(json.dumps(bad)))
    parse_failed, _ = _parse(result)
    assert parse_failed is True


def test_case9_confidence_out_of_range() -> None:
    bad = {**VALID_JUDGMENT, "confidence": 1.5}
    result = _run(lambda **kw: _text_response(json.dumps(bad)))
    parse_failed, _ = _parse(result)
    assert parse_failed is True


def test_case10_malformed_json() -> None:
    result = _run(lambda **kw: _text_response("{not valid json"))
    parse_failed, _ = _parse(result)
    assert parse_failed is True


def test_case11_prose_around_json() -> None:
    text = f"Sure, here is the judgment:\n{json.dumps(VALID_JUDGMENT)}\nHope that helps!"
    result = _run(lambda **kw: _text_response(text))
    parse_failed, _ = _parse(result)
    assert parse_failed is True  # prose-wrapped JSON is never heuristically extracted


def test_case12_multiple_text_blocks_are_flagged_not_silently_merged() -> None:
    def fake_chat(**kw: Any):
        return _FakeV2ChatResponse(
            message=_FakeMessage(
                content=[
                    _FakeContentItem(type="text", text='{"a":'),
                    _FakeContentItem(type="text", text='1}'),
                ]
            ),
        )

    result = _run(fake_chat)
    assert result.multiple_text_blocks is True
    assert result.content_block_types == ("text", "text")


def test_case13_no_text_content_only_thinking_block() -> None:
    def fake_chat(**kw: Any):
        return _FakeV2ChatResponse(
            message=_FakeMessage(
                content=[_FakeContentItem(type="thinking", thinking="pondering...")]
            ),
        )

    result = _run(fake_chat)
    assert result.raw_text is None
    assert result.error_category == "malformed_response"
    assert result.thinking_blocks_present is True


def test_case14_citations_present_without_text_content() -> None:
    def fake_chat(**kw: Any):
        return _FakeV2ChatResponse(
            message=_FakeMessage(content=[], citations=[{"start": 0, "end": 1}]),
        )

    result = _run(fake_chat)
    assert result.raw_text is None
    assert result.citations_present is True
    assert result.error_category == "malformed_response"


def test_case15_sdk_exception_before_inference_is_missing_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COHERE_API_KEY", raising=False)
    result = _run(lambda **kw: (_ for _ in ()).throw(AssertionError("unreachable")))
    assert result.error_category == "missing_credentials"


def test_case16_sdk_exception_after_provider_acceptance_is_classified() -> None:
    class _FakeUnauthorized(Exception):
        pass

    def fake_chat(**kw: Any):
        raise _FakeUnauthorized("bad token")

    result = _run(fake_chat)
    assert result.error_category in {"unknown_error", "auth_error"}
    assert result.raw_text is None
    assert "bad token" in (result.error_message or "")


def test_api_error_message_surfaces_body_not_just_headers() -> None:
    """Regression for the live confirmation (2026-07-27): a bare
    str(exc)[:500] truncated a real cohere.BadRequestError down to HTTP
    response headers only, losing the actual rejection reason (body)."""
    import cohere

    huge_headers = {f"x-header-{i}": "v" * 40 for i in range(20)}  # > 500 chars alone

    def fake_chat(**kw: Any):
        raise cohere.BadRequestError(
            body={"message": "invalid json_schema: unsupported keyword '$schema'"},
            headers=huge_headers,
        )

    result = _run(fake_chat)
    assert result.error_category == "malformed_request"
    assert result.error_message is not None
    assert "invalid json_schema" in result.error_message
    assert "status_code=400" in result.error_message


# ---------------------------------------------------------------------------
# Isolation tests
# ---------------------------------------------------------------------------


def test_dispatch_module_is_untouched_by_native_transport() -> None:
    """The compatibility-path dispatch.call_provider must be byte-for-byte
    unaffected by the existence of this module -- it must not import
    cohere_native, and cohere_native must not import dispatch or openai."""
    import ast
    from pathlib import Path

    dispatch_src = (
        Path(__file__).resolve().parents[1]
        / "src/consistency_ranker/counterfactual_benchmark/dispatch.py"
    ).read_text()
    assert "cohere_native" not in dispatch_src

    native_src = (
        Path(__file__).resolve().parents[1]
        / "src/consistency_ranker/counterfactual_benchmark/cohere_native.py"
    ).read_text()
    tree = ast.parse(native_src)
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
    assert not any(m == "openai" or m.startswith("openai.") for m in imported_modules)
    assert "counterfactual_benchmark.dispatch" not in native_src
    # The compatibility-path URL is only ever mentioned in prose (module
    # docstring, explaining what this transport deliberately avoids) --
    # never as a functional argument to ClientV2(...).
    assert "base_url" not in native_src


def test_other_providers_dispatch_still_use_openai_compatible_path() -> None:
    """Azure/Fireworks/Vertex/Cohere-compat all still go through the
    unmodified, pre-existing dispatch.call_provider -- no accidental
    routing changes from adding this module."""
    from consistency_ranker.counterfactual_benchmark.dispatch import call_provider

    captured: dict[str, Any] = {}

    def fake_call_fn(prompt: str, config: Any) -> tuple[str, object]:
        captured["provider_family"] = config.provider
        captured["base_url"] = config.base_url
        return json.dumps(VALID_JUDGMENT), None

    import pytest as _pytest

    mp = _pytest.MonkeyPatch()
    mp.setenv("AZURE_OPENAI_API_KEY", "fake")
    mp.setenv("AZURE_OPENAI_ENDPOINT", "https://fake.example.invalid")
    try:
        call_provider(
            provider="azure",
            model_id="gpt-4.1-mini",
            prompt="hello",
            temperature=0.0,
            max_tokens=128,
            call_fn=fake_call_fn,
        )
    finally:
        mp.undo()
    assert captured["provider_family"] == "openai"


# ---------------------------------------------------------------------------
# Request identity, cache, and resume
# ---------------------------------------------------------------------------


def _native_identity_hash(**overrides: Any) -> str:
    _, provider_schema_hash, _, _ = build_cohere_schema_projection()
    base = dict(
        provider="cohere",
        model_id=FROZEN_COHERE_MODEL_ID,
        transport_family=COHERE_NATIVE_V2_TRANSPORT_FAMILY,
        structured_output_protocol=COHERE_NATIVE_V2_JSON_SCHEMA_PROTOCOL_VERSION,
        schema_projection_protocol=SCHEMA_PROJECTION_PROTOCOL_VERSION,
        canonical_schema_hash="f8332b7eadcbe92e1c4aed5299a0e3b1214c6d53a68aff3c826fe86147366de7",
        provider_schema_projection_hash=provider_schema_hash,
        prompt_sha256="6e8038363393bb3e6c70edb61619107a29253fda60b35295c040c3925661fcf0",
        schema_sha256="f8332b7eadcbe92e1c4aed5299a0e3b1214c6d53a68aff3c826fe86147366de7",
        query_id="01273bd34dacfe9ef887b320f36934d2f9fa9b34",
        candidate_pool_hash="a1eb6b3f452632bb90c276adba3fca0e6e0793da9145101f758831bade591620",
        doc_a_id="161a4ba80d447f9f60fd1246e51b360ec78c13de",
        doc_b_id="219563417819f1129cdfcfa8a75c03d074577be1",
        text_hash_a="3937724a69b5d0e652eb3f62ca98b7c99c236221f44f1754360135ff1e50d842",
        text_hash_b="d4f93e98294ac52987cf8d275b94dabc5634c4ea8831cffeb4cbfc1e5b7d117e",
        presentation_order="ba",
        temperature=0.0,
        max_output_tokens=128,
        attempt_type="initial",
    )
    base.update(overrides)
    blob = json.dumps(base, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# Known historical hashes for the *same* query/pair/pool/prompt/schema under
# earlier protocols -- the projected-schema native identity hash must never
# collide with any of them.
_OLD_JSON_OBJECT_ONLY_HASH = "8075b96f1a6c8271d8e4fd56a272a2dcc412656599fc04440fef63447fa6f494"
_OLD_COMPAT_JSON_SCHEMA_HASH = "a8d368d37bcc918a3684805e0869ce52fe53c39781419b4d44ec19ff57ee3df9"
_OLD_NATIVE_UNPROJECTED_HASH = "d6ba44eb9fc254a2bdd9cbae2c3005f56e4c849f6b35788998031fb88c8338fe"
_OLD_NATIVE_V1_PROJECTION_HASH = "41f1de66736d8bb70410eefe0a59ad378b68fbc87c44bc00078fb71a5d19b302"
_OLD_NATIVE_V2_PROJECTION_HASH = "be312ecf7ba089348ffa2e0a93d1e0f2155940f6721175d63f9de14e26aa6c78"


def test_native_request_identity_differs_from_all_prior_hashes() -> None:
    native_hash = _native_identity_hash()
    assert native_hash != _OLD_JSON_OBJECT_ONLY_HASH
    assert native_hash != _OLD_COMPAT_JSON_SCHEMA_HASH
    assert native_hash != _OLD_NATIVE_UNPROJECTED_HASH
    assert native_hash != _OLD_NATIVE_V1_PROJECTION_HASH
    assert native_hash != _OLD_NATIVE_V2_PROJECTION_HASH


def test_native_request_identity_is_deterministic() -> None:
    assert _native_identity_hash() == _native_identity_hash()


def test_native_request_identity_changes_with_projection_protocol() -> None:
    base_hash = _native_identity_hash()
    changed_hash = _native_identity_hash(
        schema_projection_protocol="cohere_native_v2_schema_projection_v4_hypothetical"
    )
    assert base_hash != changed_hash


def test_v3_request_identity_differs_from_v1_and_v2_confirmation_hashes() -> None:
    """The v3-projection (with the schema_version/type addition) confirmation
    must not collide with either prior real confirmation already persisted:
    v1 (request_hash 41f1de66...) or v2 (request_hash be312ecf...)."""
    v3_hash = _native_identity_hash()  # uses current (v3) SCHEMA_PROJECTION_PROTOCOL_VERSION
    assert v3_hash != _OLD_NATIVE_V1_PROJECTION_HASH
    assert v3_hash != _OLD_NATIVE_V2_PROJECTION_HASH


def test_stale_compat_cache_entry_does_not_satisfy_native_request(tmp_path) -> None:
    cache_path = tmp_path / "normalized_judgments.jsonl"
    cache = JudgmentCacheStore(cache_path)
    cache.put(
        {
            "request_hash": _OLD_COMPAT_JSON_SCHEMA_HASH,
            "provider": "cohere",
            "success": False,
            "error_category": "parse_failure",
        }
    )
    native_hash = _native_identity_hash()
    cache2 = JudgmentCacheStore(cache_path)
    assert cache2.get(_OLD_COMPAT_JSON_SCHEMA_HASH) is not None  # old failure still visible
    assert cache2.get(native_hash) is None  # but does not satisfy the new identity


def test_cache_resume_never_duplicates_native_record(tmp_path) -> None:
    cache_path = tmp_path / "normalized_judgments.jsonl"
    cache = JudgmentCacheStore(cache_path)
    native_hash = _native_identity_hash()
    record = {"request_hash": native_hash, "provider": "cohere", "success": True}
    cache.put(record)
    cache.put(record)  # duplicate write must be a no-op
    lines = cache_path.read_text().strip().splitlines()
    assert len(lines) == 1

    cache2 = JudgmentCacheStore(cache_path)
    assert cache2.get(native_hash) == record
