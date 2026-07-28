"""Deterministic Cohere-compatible projection of the frozen judgment schema.

Diagnosed root cause, in two stages, from two bounded live confirmations:

1. (request_hash ``d6ba44eb9fc254a2bdd9cbae2c3005f56e4c849f6b35788998031fb88c8338fe``)
   the native Cohere ClientV2 call was rejected with HTTP 400 *before
   generating any content*. The frozen canonical judgment schema was the
   only input that changed relative to a syntactically-valid request, and
   it contains ``minimum``/``maximum`` numeric-range constraints on
   ``confidence``. Projection v1 (``cohere_native_v2_schema_projection_v1``)
   removed those two keywords.
2. (request_hash ``41f1de66736d8bb70410eefe0a59ad378b68fbc87c44bc00078fb71a5d19b302``,
   sent with v1's projection applied) rejected again with HTTP 400 -- but
   this time the (separately fixed) error capture recovered the *exact*
   reason for the first time: ``"unknown field '$id' in \\`object\\` type"``.
   ``minimum``/``maximum`` were confirmed *not* the sole cause. Projection
   v2 (``cohere_native_v2_schema_projection_v2``) additionally removed the
   top-level ``$id`` keyword -- a distinct category from the numeric
   constraints above: provider-unsupported *schema-identity metadata*, not
   a generation-time constraint. ``$schema`` was left untouched: only
   ``$id`` was named in the returned error.
3. (request_hash ``be312ecf7ba089348ffa2e0a93d1e0f2155940f6721175d63f9de14e26aa6c78``,
   sent with v2's projection applied) rejected a *third* time with HTTP
   400, but the error moved to a new, different field entirely --
   confirming ``$id`` removal was necessary but not sufficient:
   ``"error at 'properties.schema_version': missing required field
   'type'"``. The canonical schema's ``schema_version`` property is
   ``{"const": "counterfactual_pairwise_judgment_v1"}`` with no ``type``
   key -- valid JSON Schema (a ``const`` value unambiguously implies its
   own type), but Cohere's structured-output validator requires ``type``
   to be given explicitly alongside ``const``. Projection v3
   (``cohere_native_v2_schema_projection_v3``, this version) adds this
   missing companion field: a third category, distinct from both removal
   categories above, that *adds* rather than removes a keyword. It fires
   only where a property schema has ``const`` and no ``type`` (today, only
   ``schema_version``); the inferred value is mechanically derived from the
   Python type of the ``const`` value itself, so it is never a guess about
   Cohere's requirements -- it is a JSON-Schema-faithful annotation of
   information already implied by the (reviewed, evidenced) ``const``
   keyword's value. ``$schema`` remains untouched: no live rejection has
   named it. No live call has yet confirmed that this addition resolves
   the rejection; this is an evidence-motivated attempt, not a confirmed
   fix.

This module produces a **projection**, never a redefinition, of the
canonical schema:

- The canonical schema (``load_json_schema()``, sha256
  ``f8332b7eadcbe92e1c4aed5299a0e3b1214c6d53a68aff3c826fe86147366de7``)
  remains the single frozen contract used for freeze identity, local
  validation, benchmark semantics, and cross-provider equivalence. This
  module never mutates it and never writes to
  ``schemas/counterfactual_pairwise_judgment_v1.json``.
- The projection is a provider-facing *view*: only explicitly-classified,
  documented- or live-evidenced-unsupported keywords are removed (in two
  distinct, separately-named categories: numeric generation-time
  constraints, and schema-identity metadata), and only one explicitly
  reviewed, evidence-motivated addition is made (a ``type`` companion
  field for ``const``-only properties). Every removal and addition is
  recorded with its exact JSON pointer, and any keyword this module has
  not explicitly reviewed and classified causes projection to fail closed
  (``UnclassifiedSchemaKeywordError``) rather than being silently dropped
  or silently passed through. This is deliberately *not* a generic
  recursive "strip all ``$``-prefixed keys" mechanism: each removed or
  added keyword is named individually, with its own evidence and reason
  string.
- Local validation (``counterfactual_pilot.schema.validate_judgment``) is
  never relaxed by this module and continues to enforce the full canonical
  contract, including ``confidence`` in ``[0, 1]``, regardless of what the
  provider-facing projection permits.

The protocol version was incremented at each transformation-semantics
change (v1 -> v2 -> v3) because a live call was already made and its
evidence persisted under each prior identity, so a later version's
*different* projection output must never be mistaken for -- or share a
request/cache identity with -- an earlier version's.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from consistency_ranker.counterfactual_pilot.schema import load_json_schema

SCHEMA_PROJECTION_PROTOCOL_VERSION = "cohere_native_v2_schema_projection_v3"

#: Superseded identities, kept only as documented historical references for
#: the requests/evidence persisted under them. Do not use for new requests.
#: v1: reports/cohere_native_v2_schema_projection_confirmation_20260728T000000Z/
#: v2: reports/cohere_native_v2_schema_projection_v2_confirmation_20260728T010224Z/
SCHEMA_PROJECTION_PROTOCOL_VERSION_V1 = "cohere_native_v2_schema_projection_v1"
SCHEMA_PROJECTION_PROTOCOL_VERSION_V2 = "cohere_native_v2_schema_projection_v2"

#: Raw-file sha256 of schemas/counterfactual_pairwise_judgment_v1.json --
#: verified against the actual file at import-adjacent call time, never
#: trusted blindly. Matches the value used throughout the frozen contract
#: (config.py's verify_frozen_contract, all counterfactual_* configs).
CANONICAL_SCHEMA_SHA256 = "f8332b7eadcbe92e1c4aed5299a0e3b1214c6d53a68aff3c826fe86147366de7"

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "schemas" / "counterfactual_pairwise_judgment_v1.json"
)

# Keywords Cohere's documented structured-output subset does NOT support as
# generation-time constraints. Removed during projection; every removal is
# recorded. This registry should only ever grow after reviewing Cohere's
# published structured-output documentation for the removed keyword.
UNSUPPORTED_CONSTRAINT_KEYWORDS = frozenset(
    {
        "minimum",
        "maximum",
        "minItems",
        "maxItems",
        "minLength",
        "maxLength",
        "allOf",
        "oneOf",
        "not",
    }
)

# Schema-identity metadata keywords Cohere's native structured-output
# validator has been *live-evidenced* (not merely suspected) to reject.
# Distinct category from UNSUPPORTED_CONSTRAINT_KEYWORDS above: these are
# not generation-time value constraints, they are meta-fields describing
# the schema document itself. Each entry here must be backed by an actual
# recovered API rejection naming that exact keyword -- this is not a
# generic "strip all $-prefixed keys" list. Only "$id" qualifies today
# (recovered 2026-07-27, request_hash
# 41f1de66736d8bb70410eefe0a59ad378b68fbc87c44bc00078fb71a5d19b302:
# "unknown field '$id' in `object` type"). "$schema" is NOT included here:
# it is the same category of metadata and a reasonable suspect, but no live
# rejection has named it, so removing it would be an unreviewed guess --
# exactly what this module's fail-closed design exists to prevent. It stays
# in _PASSTHROUGH_KEYWORDS below until equivalent evidence exists.
UNSUPPORTED_SCHEMA_IDENTITY_METADATA_KEYWORDS = frozenset({"$id"})

# Keywords passed through unchanged: remaining schema-identity/metadata
# (not generation-time constraints, not live-evidenced as rejected) plus
# the core structural keywords Cohere documents as supported. Anything
# outside this set, UNSUPPORTED_CONSTRAINT_KEYWORDS, and
# UNSUPPORTED_SCHEMA_IDENTITY_METADATA_KEYWORDS fails projection closed.
_PASSTHROUGH_KEYWORDS = frozenset(
    {
        "$schema",
        "title",
        "description",
        "type",
        "properties",
        "required",
        "additionalProperties",
        "const",
        "enum",
        "items",
        "$ref",
        "$defs",
        "$def",
        "anyOf",
        "pattern",
        "format",
    }
)


class UnclassifiedSchemaKeywordError(ValueError):
    """Raised when the canonical schema contains a JSON Schema keyword this
    projector has not explicitly reviewed and classified as either
    supported (passthrough) or unsupported (removed). Fail closed rather
    than silently drop or silently forward an unreviewed keyword."""


@dataclass(frozen=True)
class RemovedConstraint:
    json_pointer: str
    keyword: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "json_pointer": self.json_pointer,
            "keyword": self.keyword,
            "reason": self.reason,
        }


# Maps the Python type of a JSON Schema ``const`` value to the JSON Schema
# ``type`` name it unambiguously implies. bool is checked before int
# (bool is a subclass of int in Python); this mapping is only ever
# consulted for a ``const`` value already present in the reviewed,
# frozen canonical schema, never for arbitrary input.
_JSON_SCHEMA_TYPE_BY_PYTHON_TYPE: tuple[tuple[type, str], ...] = (
    (bool, "boolean"),
    (str, "string"),
    (int, "integer"),
    (float, "number"),
    (type(None), "null"),
    (dict, "object"),
    (list, "array"),
)


def _infer_json_schema_type_for_const(value: Any, *, pointer: str) -> str:
    for python_type, json_schema_type in _JSON_SCHEMA_TYPE_BY_PYTHON_TYPE:
        if isinstance(value, python_type):
            return json_schema_type
    raise UnclassifiedSchemaKeywordError(
        f"cannot infer a JSON Schema type for 'const' value of Python type "
        f"{type(value)!r} at {pointer!r}"
    )


@dataclass(frozen=True)
class AddedTypeAnnotation:
    """Records a ``type`` keyword this module added to a property schema
    that declared ``const`` without ``type`` -- see the module docstring's
    finding 3. Distinct from ``RemovedConstraint``: this is an addition,
    not a removal."""

    json_pointer: str
    keyword: str
    inferred_value: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "json_pointer": self.json_pointer,
            "keyword": self.keyword,
            "inferred_value": self.inferred_value,
            "reason": self.reason,
        }


def verify_canonical_schema_hash(repo_root: Path | None = None) -> str:
    """Return the actual raw-file sha256, raising if it disagrees with the
    frozen constant -- never trust CANONICAL_SCHEMA_SHA256 without checking."""
    path = (
        repo_root / "schemas" / "counterfactual_pairwise_judgment_v1.json"
        if repo_root
        else _SCHEMA_PATH
    )
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != CANONICAL_SCHEMA_SHA256:
        raise ValueError(
            f"canonical judgment schema drift detected: expected sha256 "
            f"{CANONICAL_SCHEMA_SHA256!r}, file {path} actually hashes to {actual!r}"
        )
    return actual


def _project_schema_node(
    node: dict[str, Any],
    pointer: str,
    removed: list[RemovedConstraint],
    added: list[AddedTypeAnnotation],
) -> dict[str, Any]:
    """Project one JSON Schema *schema object* dict.

    Schema-structure-aware, not a blind recursive walk: ``properties`` is
    the one keyword whose value is a map of *user-defined property names* to
    nested schema objects, so its keys are never checked against the
    keyword registries -- only recursed into as schema objects in their own
    right. Every other passthrough keyword's value (``required``/``enum``:
    list of plain strings; ``const``/``type``/``description``/``title``/
    ``$schema``: plain scalars; ``additionalProperties``: bool) is passed
    through unchanged with no further schema-keyword interpretation, which
    is correct for this schema's actual shape (``$id`` is no longer
    passthrough -- see ``UNSUPPORTED_SCHEMA_IDENTITY_METADATA_KEYWORDS``
    above). A future schema using
    ``items``/``$ref``/``anyOf`` with nested schema objects would need this
    function extended before relying on it -- it does not recurse into
    those today.

    After a node's own keywords are projected, if it declares ``const``
    without ``type``, a ``type`` keyword is added (see
    ``AddedTypeAnnotation`` / finding 3 in the module docstring) -- this
    check runs on every node, but only ever fires on a property schema that
    actually has that exact shape (currently only ``schema_version``); it
    is a no-op everywhere else, including the top-level document, which
    already declares ``type`` explicitly.
    """
    out: dict[str, Any] = {}
    for key, value in node.items():
        child_pointer = f"{pointer}/{key}"
        if key in UNSUPPORTED_CONSTRAINT_KEYWORDS:
            removed.append(
                RemovedConstraint(
                    json_pointer=child_pointer,
                    keyword=key,
                    reason="unsupported_by_cohere_structured_outputs",
                )
            )
            continue
        if key in UNSUPPORTED_SCHEMA_IDENTITY_METADATA_KEYWORDS:
            removed.append(
                RemovedConstraint(
                    json_pointer=child_pointer,
                    keyword=key,
                    reason="unsupported_schema_identity_metadata_live_evidenced",
                )
            )
            continue
        if key == "properties":
            if not isinstance(value, dict):
                raise UnclassifiedSchemaKeywordError(
                    f"expected 'properties' at {child_pointer!r} to be an object"
                )
            out[key] = {
                prop_name: _project_schema_node(
                    prop_schema, f"{child_pointer}/{prop_name}", removed, added
                )
                for prop_name, prop_schema in value.items()
            }
            continue
        if key not in _PASSTHROUGH_KEYWORDS:
            raise UnclassifiedSchemaKeywordError(
                f"unclassified JSON Schema keyword {key!r} at {child_pointer!r}: "
                "add it to _PASSTHROUGH_KEYWORDS or UNSUPPORTED_CONSTRAINT_KEYWORDS "
                "in cohere_schema_projection.py only after reviewing Cohere's "
                "documented structured-output support for this keyword"
            )
        out[key] = value

    if "const" in out and "type" not in out:
        inferred = _infer_json_schema_type_for_const(out["const"], pointer=pointer)
        out["type"] = inferred
        added.append(
            AddedTypeAnnotation(
                json_pointer=f"{pointer}/type",
                keyword="type",
                inferred_value=inferred,
                reason="missing_required_type_companion_to_const_live_evidenced",
            )
        )
    return out


def build_cohere_schema_projection(
    canonical_schema: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str, tuple[RemovedConstraint, ...], tuple[AddedTypeAnnotation, ...]]:
    """Return (projected_schema, projected_schema_sha256, removed_constraints,
    added_annotations).

    Never mutates ``canonical_schema`` (or the module-level frozen schema
    loaded via ``load_json_schema()``). Fails closed
    (``UnclassifiedSchemaKeywordError``) if the schema contains any keyword
    not explicitly reviewed and classified above.
    """
    verify_canonical_schema_hash()
    if canonical_schema is None:
        canonical_schema = load_json_schema()
    removed: list[RemovedConstraint] = []
    added: list[AddedTypeAnnotation] = []
    # json.loads(json.dumps(...)) is a cheap, dependency-free deep copy that
    # also guarantees the input is never mutated in place.
    frozen_copy = json.loads(json.dumps(canonical_schema))
    projected = _project_schema_node(frozen_copy, "", removed, added)
    projected_hash = hashlib.sha256(
        json.dumps(projected, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return projected, projected_hash, tuple(removed), tuple(added)
