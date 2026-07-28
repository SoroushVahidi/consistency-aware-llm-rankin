"""Tests for the deterministic Cohere-compatible schema projection
(``counterfactual_benchmark.cohere_schema_projection``).

Diagnosed root cause (bounded live confirmation, 2026-07-27): the native
Cohere ClientV2 confirmation was rejected with HTTP 400 before any content
was generated. The canonical judgment schema's ``minimum``/``maximum``
numeric-range constraints on ``confidence`` are the most probable cause --
Cohere's documented structured-output subset does not support them as
generation-time constraints. This module projects them out for the
provider-facing request only; the canonical schema and strict local
validation are never touched.
"""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

from consistency_ranker.counterfactual_benchmark.cohere_schema_projection import (
    CANONICAL_SCHEMA_SHA256,
    SCHEMA_PROJECTION_PROTOCOL_VERSION,
    UnclassifiedSchemaKeywordError,
    _infer_json_schema_type_for_const,
    build_cohere_schema_projection,
    verify_canonical_schema_hash,
)
from consistency_ranker.counterfactual_pilot.schema import load_json_schema


def test_canonical_schema_hash_matches_frozen_constant() -> None:
    assert verify_canonical_schema_hash() == CANONICAL_SCHEMA_SHA256


def test_projection_is_deterministic() -> None:
    _, hash1, _, _ = build_cohere_schema_projection()
    _, hash2, _, _ = build_cohere_schema_projection()
    assert hash1 == hash2


def test_exactly_documented_and_live_evidenced_keywords_are_removed() -> None:
    """v3: minimum/maximum (documented-unsupported constraints) plus $id
    (live-evidenced-unsupported schema-identity metadata, recovered from
    request_hash 41f1de66...'s "unknown field '$id'" rejection). The
    schema_version/type addition (finding 3) is a separate, additive
    category -- see test_missing_type_companion_to_const_is_added below."""
    _, _, removed, _ = build_cohere_schema_projection()
    pointers = {r.json_pointer for r in removed}
    assert pointers == {
        "/properties/confidence/minimum",
        "/properties/confidence/maximum",
        "/$id",
    }
    by_pointer = {r.json_pointer: r.reason for r in removed}
    constraint_reason = "unsupported_by_cohere_structured_outputs"
    assert by_pointer["/properties/confidence/minimum"] == constraint_reason
    assert by_pointer["/properties/confidence/maximum"] == constraint_reason
    assert by_pointer["/$id"] == "unsupported_schema_identity_metadata_live_evidenced"


def test_missing_type_companion_to_const_is_added() -> None:
    """v3 (finding 3): schema_version declares const without type in the
    canonical schema; Cohere's live rejection under request_hash
    be312ecf...  named exactly this ("missing required field 'type'").
    The projection adds type: "string", inferred mechanically from the
    const value's Python type -- never a guess."""
    projected, _, _, added = build_cohere_schema_projection()
    assert len(added) == 1
    annotation = added[0]
    assert annotation.json_pointer == "/properties/schema_version/type"
    assert annotation.keyword == "type"
    assert annotation.inferred_value == "string"
    assert annotation.reason == "missing_required_type_companion_to_const_live_evidenced"
    assert projected["properties"]["schema_version"]["type"] == "string"


def test_canonical_schema_version_has_no_type_today() -> None:
    """Baseline evidence: the addition only fires because the canonical
    schema genuinely lacks 'type' on schema_version today. If this ever
    changes, the addition becomes a no-op, not a conflicting override."""
    canonical = load_json_schema()
    assert "type" not in canonical["properties"]["schema_version"]
    assert canonical["properties"]["schema_version"]["const"] == (
        "counterfactual_pairwise_judgment_v1"
    )


def test_infer_json_schema_type_for_const_covers_json_types() -> None:
    assert _infer_json_schema_type_for_const("x", pointer="/p") == "string"
    assert _infer_json_schema_type_for_const(1, pointer="/p") == "integer"
    assert _infer_json_schema_type_for_const(1.5, pointer="/p") == "number"
    assert _infer_json_schema_type_for_const(True, pointer="/p") == "boolean"
    assert _infer_json_schema_type_for_const(None, pointer="/p") == "null"
    assert _infer_json_schema_type_for_const({}, pointer="/p") == "object"
    assert _infer_json_schema_type_for_const([], pointer="/p") == "array"


def test_infer_json_schema_type_for_const_fails_closed_on_unmappable_type() -> None:
    with pytest.raises(UnclassifiedSchemaKeywordError, match="cannot infer"):
        _infer_json_schema_type_for_const(object(), pointer="/nowhere")


def test_type_is_not_added_when_already_present() -> None:
    """A property with both const and an explicit type must not get a
    second, conflicting type addition recorded."""
    canonical = load_json_schema()
    tampered = copy.deepcopy(canonical)
    tampered["properties"]["schema_version"]["type"] = "string"
    _, _, _, added = build_cohere_schema_projection(tampered)
    assert added == ()


def test_schema_remains_untouched() -> None:
    """$schema is only suspected, not live-evidenced -- it must remain in
    the projection, unlike $id."""
    projected, _, removed, _ = build_cohere_schema_projection()
    assert "$schema" in projected
    assert projected["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert not any(r.keyword == "$schema" for r in removed)


def test_removal_records_have_correct_keyword_names() -> None:
    _, _, removed, _ = build_cohere_schema_projection()
    by_pointer = {r.json_pointer: r.keyword for r in removed}
    assert by_pointer["/properties/confidence/minimum"] == "minimum"
    assert by_pointer["/properties/confidence/maximum"] == "maximum"
    assert by_pointer["/$id"] == "$id"


def test_enums_are_preserved() -> None:
    projected, _, _, _ = build_cohere_schema_projection()
    assert projected["properties"]["preference"]["enum"] == ["A", "B", "TIE", "ABSTAIN"]
    assert projected["properties"]["evidence_strength"]["enum"] == [
        "weak",
        "moderate",
        "strong",
    ]
    assert projected["properties"]["reason_code"]["enum"] == [
        "direct_relevance",
        "partial_answer",
        "unsupported",
        "ambiguous",
        "other",
    ]


def test_const_is_preserved() -> None:
    projected, _, _, _ = build_cohere_schema_projection()
    assert projected["properties"]["schema_version"]["const"] == (
        "counterfactual_pairwise_judgment_v1"
    )


def test_required_fields_are_preserved() -> None:
    projected, _, _, _ = build_cohere_schema_projection()
    assert projected["required"] == [
        "schema_version",
        "preference",
        "confidence",
        "evidence_strength",
        "reason_code",
    ]


def test_additional_properties_is_preserved() -> None:
    projected, _, _, _ = build_cohere_schema_projection()
    assert projected["additionalProperties"] is False


def test_unknown_constraint_keyword_fails_closed() -> None:
    canonical = load_json_schema()
    tampered = copy.deepcopy(canonical)
    tampered["properties"]["confidence"]["exclusiveMinimum"] = 0.0
    with pytest.raises(UnclassifiedSchemaKeywordError, match="exclusiveMinimum"):
        build_cohere_schema_projection(tampered)


def test_canonical_schema_is_never_mutated_in_memory() -> None:
    canonical = load_json_schema()
    before = copy.deepcopy(canonical)
    build_cohere_schema_projection(canonical)
    assert canonical == before  # unchanged after projection


def test_canonical_schema_file_remains_byte_identical_on_disk() -> None:
    """The projection must never write to
    schemas/counterfactual_pairwise_judgment_v1.json -- verified by hashing
    the file's raw bytes before and after building the projection."""
    from pathlib import Path

    schema_path = (
        Path(__file__).resolve().parents[1]
        / "schemas"
        / "counterfactual_pairwise_judgment_v1.json"
    )
    before_bytes = schema_path.read_bytes()
    build_cohere_schema_projection()
    after_bytes = schema_path.read_bytes()
    assert before_bytes == after_bytes
    assert hashlib.sha256(after_bytes).hexdigest() == CANONICAL_SCHEMA_SHA256


def test_no_unrelated_canonical_field_is_removed_or_modified() -> None:
    """Only /$id, /properties/confidence/minimum, and
    /properties/confidence/maximum may be removed, and only
    /properties/schema_version/type may be added -- every other
    field/value must be identical to canonical."""
    canonical = load_json_schema()
    projected, _, removed, added = build_cohere_schema_projection()
    removed_pointers = {r.json_pointer for r in removed}
    assert removed_pointers == {
        "/$id",
        "/properties/confidence/minimum",
        "/properties/confidence/maximum",
    }
    assert {a.json_pointer for a in added} == {"/properties/schema_version/type"}

    # Reconstruct what canonical minus exactly the removed keys, plus
    # exactly the added key, should look like, and assert it equals the
    # projection exactly.
    expected = copy.deepcopy(canonical)
    del expected["$id"]
    del expected["properties"]["confidence"]["minimum"]
    del expected["properties"]["confidence"]["maximum"]
    expected["properties"]["schema_version"]["type"] = "string"
    assert projected == expected


def test_module_level_frozen_schema_object_is_never_mutated() -> None:
    before = json.dumps(load_json_schema(), sort_keys=True)
    build_cohere_schema_projection()  # uses load_json_schema() internally
    after = json.dumps(load_json_schema(), sort_keys=True)
    assert before == after


def test_projection_receives_a_distinct_hash_from_canonical() -> None:
    canonical = load_json_schema()
    canonical_hash = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    projected, projected_hash, _, _ = build_cohere_schema_projection()
    assert projected != canonical
    assert projected_hash != canonical_hash


def test_verify_canonical_schema_hash_detects_drift(tmp_path) -> None:
    tampered_path = tmp_path / "schemas" / "counterfactual_pairwise_judgment_v1.json"
    tampered_path.parent.mkdir(parents=True)
    tampered = load_json_schema()
    tampered["properties"]["evidence_strength"]["enum"].append("unsupported")
    tampered_path.write_text(json.dumps(tampered))
    with pytest.raises(ValueError, match="canonical judgment schema drift"):
        verify_canonical_schema_hash(repo_root=tmp_path)


def test_projection_protocol_version_is_stable_string() -> None:
    assert SCHEMA_PROJECTION_PROTOCOL_VERSION == "cohere_native_v2_schema_projection_v3"


def test_v1_protocol_identity_preserved_as_historical_reference() -> None:
    """v1's identity must remain importable and distinct from v3's, since a
    real live call (request_hash 41f1de66...) was persisted under it."""
    from consistency_ranker.counterfactual_benchmark.cohere_schema_projection import (
        SCHEMA_PROJECTION_PROTOCOL_VERSION_V1,
    )

    assert SCHEMA_PROJECTION_PROTOCOL_VERSION_V1 == "cohere_native_v2_schema_projection_v1"
    assert SCHEMA_PROJECTION_PROTOCOL_VERSION_V1 != SCHEMA_PROJECTION_PROTOCOL_VERSION


def test_v2_protocol_identity_preserved_as_historical_reference() -> None:
    """v2's identity must remain importable and distinct from v3's, since a
    real live call (request_hash be312ecf...) was persisted under it."""
    from consistency_ranker.counterfactual_benchmark.cohere_schema_projection import (
        SCHEMA_PROJECTION_PROTOCOL_VERSION_V2,
    )

    assert SCHEMA_PROJECTION_PROTOCOL_VERSION_V2 == "cohere_native_v2_schema_projection_v2"
    assert SCHEMA_PROJECTION_PROTOCOL_VERSION_V2 != SCHEMA_PROJECTION_PROTOCOL_VERSION
