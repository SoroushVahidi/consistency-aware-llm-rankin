"""Qrels-blind candidate-pool construction and document rendering.

Two frozen, versioned protocols are recorded on every pool so results can
never be silently attributed to a different pipeline:

* ``POOL_PROTOCOL_VERSION`` (candidate selection): no canonical multi-ranker
  fusion pool exists in this repo for these four datasets (verified by
  search before this module was written). This builds a deterministic
  fallback pool from two independent lexical-prior signals over the full
  document corpus, computed purely from query and document text -- qrels
  are never read here. This pool is valid for the operational micro-pilot
  only; it is NOT automatically identical to a canonical multi-ranker/RRF
  pool a later scientific benchmark might use. Changing this protocol
  requires a new benchmark version or an explicit pool-robustness audit.

* ``RENDERING_POLICY_VERSION`` (document -> prompt text): deterministic
  title+text composition followed by a plain prefix truncation. Rendering
  policy is itself an experimental factor; a later benchmark should compare
  at least one alternative rendering policy before broad scientific claims.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from consistency_ranker.counterfactual_benchmark.models import (
    CandidatePoolRecord,
    RenderedDocumentRecord,
)

POOL_PROTOCOL_VERSION = "lexical_prior_pool_v1"
RENDERING_POLICY_VERSION = "title_plus_prefix_truncate_v1"

# Backward-compatible alias (previous name for POOL_PROTOCOL_VERSION).
CONSTRUCTION_METHOD = POOL_PROTOCOL_VERSION

# --- v2: qrels-blind pool protocol with bounded-denominator prior and an
# explicit, pre-scoring document-validity gate ---------------------------
#
# Audit finding (reports/counterfactual_collector_canary_v1_20260727T145126Z
# plus an 8-query / 80-candidate / 64-pair frozen-pool audit): the v1 primary
# prior (token_overlap / sqrt(doc_token_count)) has no lower bound on
# doc_token_count, so a near-empty document (e.g. a SciDocs record with an
# empty "text" field, leaving only the title) can score higher than any
# substantive document merely because its denominator is tiny. This captured
# 10/10 pool slots for one frozen SciDocs query and 7/10 for another, even
# though only 1.34% of the SciDocs corpus has an empty text field -- the
# formula, not the corpus, is what concentrates the pool on empty documents.
# Plain Jaccard and an RRF fusion of the two v1 priors were measured to be
# equally or more biased toward short/empty documents (tested qrels-blind,
# operational properties only -- see PART III/IV audit); a bounded-denominator
# variant of the same overlap formula removed the effect (title-only pool
# share dropped from 21.2% to 1.2% across the 8 frozen queries) without
# introducing a new dependency or changing the rendering policy.
POOL_PROTOCOL_VERSION_V2 = "lexical_prior_pool_v2"

# Floor for the primary-prior denominator: no document is treated as shorter
# than this many tokens for scoring purposes, which caps the maximum
# achievable score for very short/empty documents instead of letting it grow
# without bound as token count shrinks toward zero.
BOUNDED_PRIOR_MIN_DENOMINATOR_TOKENS = 25

# Document-validity thresholds, derived from the observed corpus distribution
# across all four frozen datasets' *nonempty*-text documents (computed
# 2026-07-27): the 1st-percentile alphabetic-token count ranged 15 (hotpotqa)
# to 38 (scidocs), and the 1st-percentile nonempty-body character count
# ranged 103 (hotpotqa) to 280 (scidocs). MIN_ALPHA_TOKENS/MIN_SUBSTANTIVE_CHARS
# are set at the tightest (hotpotqa) percentile rounded down slightly, so the
# gate excludes only genuinely degenerate documents (empty, title-only, or
# markup/number-only bodies) and not the shortest *real* content in any of
# the four corpora.
MIN_ALPHA_TOKENS_V2 = 15
MIN_SUBSTANTIVE_CHARS_V2 = 100


def _tokenize(text: str) -> set[str]:
    return set(text.lower().split())


def _doc_title(rec: dict) -> str:
    return str(rec.get("title") or "").strip()


def _doc_text(rec: dict) -> str:
    return str(rec.get("text") or rec.get("contents") or rec.get("body") or "")


def _doc_id(rec: dict) -> str:
    return str(rec.get("doc_id") or rec.get("id") or rec.get("_id"))


def compose_document_text(rec: dict) -> tuple[str, bool]:
    """Deterministically compose the full document text used for both
    retrieval-prior scoring and prompt rendering: title (if present) plus a
    blank line plus body text. Returns (composed_text, title_included)."""
    title = _doc_title(rec)
    text = _doc_text(rec)
    if title:
        return f"{title}\n\n{text}", True
    return text, False


def _prior_overlap(query_tokens: set[str], doc_tokens: set[str]) -> float:
    """Primary prior: token-overlap count normalized by sqrt(doc length)."""
    if not query_tokens or not doc_tokens:
        return 0.0
    return len(query_tokens & doc_tokens) / math.sqrt(len(doc_tokens))


def _prior_jaccard(query_tokens: set[str], doc_tokens: set[str]) -> float:
    """Secondary prior: plain Jaccard overlap (independent scoring formula)."""
    if not query_tokens or not doc_tokens:
        return 0.0
    union = len(query_tokens | doc_tokens)
    return (len(query_tokens & doc_tokens) / union) if union else 0.0


def _alpha_token_count(text: str) -> int:
    return sum(1 for tok in text.split() if any(ch.isalpha() for ch in tok))


def document_validity_v2(composed_text: str, *, title_included: bool) -> tuple[bool, str | None]:
    """Text-integrity-only eligibility gate (never uses relevance/qrels).

    Returns (is_valid, exclusion_reason). Rejects: empty rendered text;
    title-present-but-empty-body (the exact shape of the canary v1 failure);
    and bodies below the corpus-derived substantive-content floor (guards
    against markup/number-only or otherwise degenerate nonempty bodies).
    Safe to call on either the full composed text (pool construction) or a
    truncated excerpt (pair-selection recheck): the validity floors are far
    below the 1,200-char truncation cap, so truncation of an already-valid
    document never flips it to invalid.
    """
    stripped = composed_text.strip()
    if not stripped:
        return False, "empty_rendered_text"
    if title_included:
        body = composed_text.split("\n\n", 1)
        body_text = body[1].strip() if len(body) > 1 else ""
        if not body_text:
            return False, "title_only_no_body"
        check_text = body_text
    else:
        check_text = stripped
    if _alpha_token_count(check_text) < MIN_ALPHA_TOKENS_V2:
        return False, "insufficient_alpha_tokens"
    if len(check_text) < MIN_SUBSTANTIVE_CHARS_V2:
        return False, "insufficient_substantive_chars"
    return True, None


def _prior_overlap_bounded(query_tokens: set[str], doc_tokens: set[str]) -> float:
    """v2 primary prior: same overlap/sqrt(len) shape as v1, but the
    denominator is floored at BOUNDED_PRIOR_MIN_DENOMINATOR_TOKENS so a
    near-empty document can no longer receive an unboundedly large score."""
    if not query_tokens or not doc_tokens:
        return 0.0
    denom = math.sqrt(max(len(doc_tokens), BOUNDED_PRIOR_MIN_DENOMINATOR_TOKENS))
    return len(query_tokens & doc_tokens) / denom


def truncate_text(text: str, max_chars: int) -> str:
    """Deterministic prefix truncation. Python string slicing operates on
    Unicode code points, so this never splits a multi-byte UTF-8 sequence."""
    return text[:max_chars]


def render_document(rec: dict, *, max_candidate_chars: int) -> tuple[str, RenderedDocumentRecord]:
    """Render one document record to its frozen excerpt plus provenance.

    The excerpt is what is ever sent to a provider or written to disk; the
    full composed text is hashed but never persisted, so a 9-million-
    character document (observed in BRIGHT) cannot leak into a manifest or
    a live prompt.
    """
    did = _doc_id(rec)
    composed, title_included = compose_document_text(rec)
    excerpt = truncate_text(composed, max_candidate_chars)
    record = RenderedDocumentRecord(
        document_id=did,
        full_document_sha256=hashlib.sha256(composed.encode("utf-8")).hexdigest(),
        rendered_excerpt_sha256=hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
        original_character_count=len(composed),
        rendered_character_count=len(excerpt),
        truncated=len(composed) > len(excerpt),
        truncation_policy=RENDERING_POLICY_VERSION,
        title_included=title_included,
    )
    return excerpt, record


def build_candidate_pool(
    *,
    dataset: str,
    query_id: str,
    query_text: str,
    documents_path: Path,
    pool_size: int,
    max_candidate_chars: int,
) -> CandidatePoolRecord:
    """Build a deterministic, qrels-blind pool of *pool_size* candidates.

    Reads the full document corpus once. Ranks by the primary lexical-overlap
    prior (ties broken by doc id for determinism) and keeps the top
    *pool_size*. A second, independently-formulated prior (plain Jaccard) is
    also recorded so pair selection can use cross-prior disagreement without
    ever consulting qrels. Priors are scored over the same title+text
    composition that gets rendered, so retrieval signal and rendered content
    describe the same notion of "the document".
    """
    q_tokens = _tokenize(query_text)
    primary: dict[str, float] = {}
    secondary: dict[str, float] = {}
    composed_by_id: dict[str, dict] = {}
    with documents_path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            did = _doc_id(rec)
            composed, _title_included = compose_document_text(rec)
            if not did or not composed:
                continue
            d_tokens = _tokenize(composed)
            primary[did] = _prior_overlap(q_tokens, d_tokens)
            secondary[did] = _prior_jaccard(q_tokens, d_tokens)
            composed_by_id[did] = rec

    if len(primary) < pool_size:
        raise ValueError(
            f"{dataset}/{query_id}: only {len(primary)} candidate documents "
            f"available, need pool_size={pool_size}"
        )

    ranked = sorted(primary, key=lambda d: (-primary[d], d))
    pool_ids = tuple(ranked[:pool_size])

    truncated: dict[str, str] = {}
    rendering_metadata: dict[str, RenderedDocumentRecord] = {}
    for d in pool_ids:
        excerpt, record = render_document(
            composed_by_id[d], max_candidate_chars=max_candidate_chars
        )
        truncated[d] = excerpt
        rendering_metadata[d] = record

    text_hashes = {d: rendering_metadata[d].rendered_excerpt_sha256 for d in pool_ids}
    pool_hash = hashlib.sha256(
        json.dumps(list(pool_ids), sort_keys=False).encode("utf-8")
    ).hexdigest()

    return CandidatePoolRecord(
        dataset=dataset,
        query_id=query_id,
        candidate_ids=pool_ids,
        pool_hash=pool_hash,
        text_hashes=text_hashes,
        construction_method=POOL_PROTOCOL_VERSION,
        pool_protocol_version=POOL_PROTOCOL_VERSION,
        rendering_policy_version=RENDERING_POLICY_VERSION,
        prior_scores_primary={d: primary[d] for d in pool_ids},
        prior_scores_secondary={d: secondary[d] for d in pool_ids},
        truncated_texts=truncated,
        rendering_metadata=rendering_metadata,
    )


def build_candidate_pool_v2(
    *,
    dataset: str,
    query_id: str,
    query_text: str,
    documents_path: Path,
    pool_size: int,
    max_candidate_chars: int,
) -> CandidatePoolRecord:
    """v2: same qrels-blind, deterministic construction as v1, plus an
    explicit pre-scoring document-validity gate and a bounded-denominator
    primary prior (see module docstring and ``document_validity_v2`` /
    ``_prior_overlap_bounded`` for the audited rationale). Documents that
    fail validity are never scored into the pool even if lexically
    relevant; each exclusion is recorded with the valid candidate that
    filled its slot, so the process is fully auditable.
    """
    q_tokens = _tokenize(query_text)
    primary: dict[str, float] = {}
    secondary: dict[str, float] = {}
    composed_by_id: dict[str, dict] = {}
    validity: dict[str, tuple[bool, str | None]] = {}
    with documents_path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            did = _doc_id(rec)
            composed, title_included = compose_document_text(rec)
            if not did or not composed:
                continue
            d_tokens = _tokenize(composed)
            primary[did] = _prior_overlap_bounded(q_tokens, d_tokens)
            secondary[did] = _prior_jaccard(q_tokens, d_tokens)
            composed_by_id[did] = rec
            validity[did] = document_validity_v2(composed, title_included=title_included)

    n_valid = sum(1 for is_valid, _ in validity.values() if is_valid)
    if n_valid < pool_size:
        raise ValueError(
            f"{dataset}/{query_id}: only {n_valid} document-valid candidates "
            f"available, need pool_size={pool_size}"
        )

    ranked_all = sorted(primary, key=lambda d: (-primary[d], d))
    pool_ids_list: list[str] = []
    exclusion_records: list[dict[str, Any]] = []
    pending_exclusions: list[tuple[str, str | None]] = []
    for d in ranked_all:
        if len(pool_ids_list) >= pool_size:
            break
        is_valid, reason = validity[d]
        if is_valid:
            for excluded_id, excluded_reason in pending_exclusions:
                exclusion_records.append(
                    {
                        "excluded_document_id": excluded_id,
                        "exclusion_reason": excluded_reason,
                        "replacement_candidate": d,
                    }
                )
            pending_exclusions = []
            pool_ids_list.append(d)
        else:
            pending_exclusions.append((d, reason))
    pool_ids = tuple(pool_ids_list)

    truncated: dict[str, str] = {}
    rendering_metadata: dict[str, RenderedDocumentRecord] = {}
    for d in pool_ids:
        excerpt, record = render_document(
            composed_by_id[d], max_candidate_chars=max_candidate_chars
        )
        truncated[d] = excerpt
        rendering_metadata[d] = record

    text_hashes = {d: rendering_metadata[d].rendered_excerpt_sha256 for d in pool_ids}
    pool_hash = hashlib.sha256(
        json.dumps(list(pool_ids), sort_keys=False).encode("utf-8")
    ).hexdigest()

    return CandidatePoolRecord(
        dataset=dataset,
        query_id=query_id,
        candidate_ids=pool_ids,
        pool_hash=pool_hash,
        text_hashes=text_hashes,
        construction_method=POOL_PROTOCOL_VERSION_V2,
        pool_protocol_version=POOL_PROTOCOL_VERSION_V2,
        rendering_policy_version=RENDERING_POLICY_VERSION,
        prior_scores_primary={d: primary[d] for d in pool_ids},
        prior_scores_secondary={d: secondary[d] for d in pool_ids},
        truncated_texts=truncated,
        rendering_metadata=rendering_metadata,
        exclusion_records=tuple(exclusion_records),
    )
