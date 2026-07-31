"""Native Cohere ClientV2 transport for frozen counterfactual judgments.

Distinct from, and never falls back to, Cohere's OpenAI-compatibility
endpoint used by every other provider's shared "openai" family path in
``dispatch.py``/``rerankers.llm_pairwise``. This module never imports the
``openai`` package and never constructs an OpenAI client or points at
``https://api.cohere.ai/compatibility/v1``.

Diagnosed defect this investigates: two bounded live calls through Cohere's
OpenAI-compatibility endpoint (archived at
``archive/cohere-compat-schema-failed-20260727``, commit
``0646fde88a3d529ce4ebd4a4c2d5b6d3b21074a2``) both returned syntactically
valid but schema-invalid JSON (``evidence_strength: "unsupported"``)
regardless of ``response_format``. This module tests whether Cohere's own
native Chat API v2 -- a different wire protocol and a different
``response_format`` convention (the SDK's ``JsonObjectResponseFormatV2``,
whose schema field is named ``json_schema``, not ``schema``) -- can honor
the same frozen judgment schema.

This transport is experimental and is NOT wired into ``dispatch.call_provider``
or the frozen ``counterfactual_provider_panel_v1``: it is invoked only by an
explicit, separate confirmation path until independently validated.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from consistency_ranker.counterfactual_benchmark.cohere_schema_projection import (
    CANONICAL_SCHEMA_SHA256,
    SCHEMA_PROJECTION_PROTOCOL_VERSION,
    build_cohere_schema_projection,
)
from consistency_ranker.counterfactual_pilot.schema import load_json_schema

#: Distinct from the archived compatibility-path constant
#: ``COHERE_STRUCTURED_OUTPUT_PROTOCOL_VERSION = "cohere_json_schema_v1"``
#: (no longer present on this branch; see archive commit above).
COHERE_NATIVE_V2_TRANSPORT_FAMILY = "cohere_native_v2"
COHERE_NATIVE_V2_JSON_SCHEMA_PROTOCOL_VERSION = "cohere_native_v2_json_schema_v1"

#: The only model this transport will call -- matches the frozen panel's
#: Cohere member. A mismatch is a configuration error, not a runtime one.
FROZEN_COHERE_MODEL_ID = "command-r-plus-08-2024"

_NATIVE_ENV_VAR = "COHERE_API_KEY"


class CohereNativeConfigError(ValueError):
    """Raised when the native transport is asked to run outside its frozen contract."""


#: Distinguishes exactly where a request/response stopped, per the
#: reviewed failure taxonomy: a 400 with no generation is
#: request_rejected_before_generation, never failed_after_inference.
FAILURE_STAGES = frozenset(
    {
        "client_configuration_failure",
        "request_serialization_failure",
        "request_rejected_before_generation",
        "provider_generation_failure",
        "response_extraction_failure",
        "schema_validation_failure",
    }
)


@dataclass
class NativeDispatchResult:
    raw_text: str | None
    prompt_tokens: int
    completion_tokens: int
    latency_seconds: float
    error_category: str | None
    error_message: str | None
    response_type: str | None = None
    finish_reason: str | None = None
    content_block_types: tuple[str, ...] = field(default_factory=tuple)
    multiple_text_blocks: bool = False
    thinking_blocks_present: bool = False
    citations_present: bool = False
    tool_calls_present: bool = False
    # Failure-stage / accounting granularity (Part VI): a rejected-before-
    # generation call must never be conflated with an accepted-but-failed
    # generation for billing/ledger purposes.
    failure_stage: str | None = None
    provider_call_attempted: bool = False
    generation_started: bool = False
    billable_tokens: int = 0
    # Schema-projection provenance (never affects local validation, which
    # always uses the canonical schema regardless of these fields).
    canonical_schema_sha256: str | None = None
    provider_schema_sha256: str | None = None
    schema_projection_protocol: str | None = None
    removed_constraints: tuple[dict[str, str], ...] = field(default_factory=tuple)
    added_type_annotations: tuple[dict[str, str], ...] = field(default_factory=tuple)


def native_cohere_ready() -> tuple[bool, str]:
    """Check ``COHERE_API_KEY`` presence only (never read or log the value).

    Deliberately narrower than ``dispatch.preflight_provider_ready("cohere")``,
    which also treats ``COHERE_BASE_URL``/``COHERE_MODEL`` presence as
    "ready" -- those are compatibility-path artifacts and irrelevant (and
    potentially misleading) for the native transport.
    """
    if os.environ.get(_NATIVE_ENV_VAR):
        return True, f"env_present:{_NATIVE_ENV_VAR}"
    return False, f"missing_env:{_NATIVE_ENV_VAR}"


def _classify_cohere_error(exc: BaseException) -> str:
    """Map a raised cohere-SDK exception to a stable error category.

    Mirrors ``failure_mining.llm_runner.classify_llm_error``'s category
    names for consistency, without importing openai's exception hierarchy.
    """
    try:
        import cohere
    except ImportError:
        return "unknown_error"
    if isinstance(exc, (cohere.UnauthorizedError, cohere.InvalidTokenError)):
        return "auth_error"
    if isinstance(exc, cohere.ForbiddenError):
        return "permission_error"
    if isinstance(exc, cohere.NotFoundError):
        return "model_not_found"
    if isinstance(exc, cohere.TooManyRequestsError):
        return "rate_limited"
    if isinstance(exc, (cohere.BadRequestError, cohere.UnprocessableEntityError)):
        return "malformed_request"
    if isinstance(exc, cohere.GatewayTimeoutError):
        return "timeout"
    if isinstance(exc, (cohere.InternalServerError, cohere.ServiceUnavailableError)):
        return "server_error"
    return "unknown_error"


def _sanitized_error_message(exc: BaseException) -> str:
    """Build a diagnostic error message that prioritizes the actual API
    rejection reason.

    Cohere's ``ApiError.__str__`` renders as
    ``"headers: {...}, status_code: ..., body: ..."`` -- the useful part
    (``body``, which carries e.g. "invalid schema: ...") comes *last* and
    was previously lost when the message was blindly truncated with
    ``str(exc)[:500]`` (observed live 2026-07-27: the confirmation call's
    captured error_message was HTTP response headers only, with the actual
    rejection reason truncated away). Response headers here are diagnostic
    metadata (trace IDs, cache-control), never credentials -- but body/
    status_code is what's actually needed to diagnose a failure, so it is
    surfaced explicitly instead of relying on dict-repr field ordering.
    """
    status_code = getattr(exc, "status_code", None)
    body = getattr(exc, "body", None)
    if status_code is not None or body is not None:
        return f"status_code={status_code} body={body}"[:1000]
    return str(exc)[:500]


def call_cohere_native(
    *,
    model_id: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    judgment_schema: dict[str, Any] | None = None,
    chat_fn: Callable[..., Any] | None = None,
) -> NativeDispatchResult:
    """Issue exactly one native ClientV2 call. Never falls back to another
    transport or provider.

    ``judgment_schema`` defaults to the frozen (canonical) schema loaded
    verbatim from ``schemas/counterfactual_pairwise_judgment_v1.json``
    (single source of truth). If a caller passes an explicit schema, it
    must be identical to the frozen one -- this is a fail-closed
    configuration guard, not a feature for using a different schema.

    The **canonical** schema is never sent to Cohere as-is: a deterministic,
    fully-recorded projection (``cohere_schema_projection``) is built from
    it and *that* is what goes on the wire, because Cohere's native
    structured-output validator does not document support for JSON
    Schema's ``minimum``/``maximum`` numeric-range keywords, which the
    canonical schema uses on ``confidence``. Local judgment validation is
    unaffected by this -- it always validates against the full canonical
    schema, regardless of what was sent to the provider.

    ``chat_fn`` (protocol: ``chat_fn(*, model, messages, response_format,
    temperature, max_tokens) -> V2ChatResponse``-shaped object) lets tests
    inject a fake without a real client or network access, mirroring
    ``dispatch.call_provider``'s ``call_fn`` injection pattern.
    """
    if model_id != FROZEN_COHERE_MODEL_ID:
        raise CohereNativeConfigError(
            f"native Cohere transport is frozen to model_id={FROZEN_COHERE_MODEL_ID!r}, "
            f"got {model_id!r}"
        )

    frozen_schema = load_json_schema()
    if judgment_schema is None:
        judgment_schema = frozen_schema
    elif judgment_schema != frozen_schema:
        raise CohereNativeConfigError(
            "judgment_schema does not match the frozen "
            "schemas/counterfactual_pairwise_judgment_v1.json artifact"
        )

    try:
        provider_schema, provider_schema_hash, removed, added = build_cohere_schema_projection(
            judgment_schema
        )
    except Exception as exc:  # noqa: BLE001 - a schema-projection bug is a config error
        return NativeDispatchResult(
            raw_text=None,
            prompt_tokens=0,
            completion_tokens=0,
            latency_seconds=0.0,
            error_category="malformed_request",
            error_message=f"schema projection failed: {exc}"[:500],
            failure_stage="request_serialization_failure",
        )
    # Raw-file-bytes hash, matching the well-known frozen constant used
    # throughout the rest of the codebase (config.py's verify_frozen_contract,
    # all counterfactual_* configs' judgment_schema_sha256) -- NOT a hash of
    # the re-serialized dict, which would silently diverge from that value
    # (observed 2026-07-27: an earlier version of this function did that,
    # producing a provenance hash that didn't match CANONICAL_SCHEMA_SHA256
    # anywhere else in the repo).
    canonical_schema_hash = CANONICAL_SCHEMA_SHA256
    removed_dicts = tuple(r.to_dict() for r in removed)
    added_dicts = tuple(a.to_dict() for a in added)

    ready, reason = native_cohere_ready()
    if not ready:
        return NativeDispatchResult(
            raw_text=None,
            prompt_tokens=0,
            completion_tokens=0,
            latency_seconds=0.0,
            error_category="missing_credentials",
            error_message=reason,
            failure_stage="client_configuration_failure",
            canonical_schema_sha256=canonical_schema_hash,
            provider_schema_sha256=provider_schema_hash,
            schema_projection_protocol=SCHEMA_PROJECTION_PROTOCOL_VERSION,
            removed_constraints=removed_dicts,
            added_type_annotations=added_dicts,
        )

    if chat_fn is None:
        import cohere
        from cohere.types import JsonObjectResponseFormatV2, UserChatMessageV2

        client = cohere.ClientV2(api_key=os.environ[_NATIVE_ENV_VAR])

        def chat_fn(
            *, model: str, messages: list[Any], response_format: Any, temperature: float,
            max_tokens: int,
        ) -> Any:
            return client.chat(
                model=model,
                messages=messages,
                response_format=response_format,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        native_messages: list[Any] = [UserChatMessageV2(content=prompt)]
        native_response_format: Any = JsonObjectResponseFormatV2(json_schema=provider_schema)
    else:
        # Test-injected chat_fn: build the same request-shape dicts a real
        # call would receive, without importing the cohere SDK types, so
        # request-capture tests can assert on plain, inspectable values.
        native_messages = [{"role": "user", "content": prompt}]
        native_response_format = {"type": "json_object", "json_schema": provider_schema}

    t0 = time.perf_counter()
    try:
        response = chat_fn(
            model=model_id,
            messages=native_messages,
            response_format=native_response_format,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:  # noqa: BLE001 - classified below, never re-raised bare
        latency = time.perf_counter() - t0
        # A raised exception here means the SDK/API never returned a
        # response object -- generation never started. This is distinct
        # from an accepted request that failed during/after generation.
        return NativeDispatchResult(
            raw_text=None,
            prompt_tokens=0,
            completion_tokens=0,
            latency_seconds=latency,
            error_category=_classify_cohere_error(exc),
            error_message=_sanitized_error_message(exc),
            failure_stage="request_rejected_before_generation",
            provider_call_attempted=True,
            generation_started=False,
            canonical_schema_sha256=canonical_schema_hash,
            provider_schema_sha256=provider_schema_hash,
            schema_projection_protocol=SCHEMA_PROJECTION_PROTOCOL_VERSION,
            removed_constraints=removed_dicts,
            added_type_annotations=added_dicts,
        )
    latency = time.perf_counter() - t0

    message = response.message
    content_items = list(message.content or [])
    block_types = tuple(getattr(item, "type", "unknown") for item in content_items)
    text_blocks = [
        item.text for item in content_items if getattr(item, "type", None) == "text"
    ]
    thinking_present = any(getattr(item, "type", None) == "thinking" for item in content_items)
    # Only the documented text content block(s) are ever treated as judgment
    # JSON. thinking/citations/tool_calls are recorded for shape visibility
    # but never concatenated into raw_text or parsed as judgment content.
    raw_text = "".join(text_blocks) if text_blocks else None

    usage = getattr(response, "usage", None)
    tokens = getattr(usage, "tokens", None) if usage else None
    prompt_tokens = int(tokens.input_tokens) if tokens and tokens.input_tokens is not None else 0
    completion_tokens = (
        int(tokens.output_tokens) if tokens and tokens.output_tokens is not None else 0
    )

    return NativeDispatchResult(
        raw_text=raw_text,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_seconds=latency,
        error_category=None if raw_text else "malformed_response",
        error_message=None if raw_text else "no text content block in native Cohere response",
        response_type=type(response).__name__,
        finish_reason=getattr(response, "finish_reason", None),
        content_block_types=block_types,
        multiple_text_blocks=len(text_blocks) > 1,
        thinking_blocks_present=thinking_present,
        citations_present=bool(getattr(message, "citations", None)),
        tool_calls_present=bool(getattr(message, "tool_calls", None)),
        failure_stage=None if raw_text else "response_extraction_failure",
        provider_call_attempted=True,
        generation_started=True,
        billable_tokens=prompt_tokens + completion_tokens,
        canonical_schema_sha256=canonical_schema_hash,
        provider_schema_sha256=provider_schema_hash,
        schema_projection_protocol=SCHEMA_PROJECTION_PROTOCOL_VERSION,
        removed_constraints=removed_dicts,
        added_type_annotations=added_dicts,
    )
