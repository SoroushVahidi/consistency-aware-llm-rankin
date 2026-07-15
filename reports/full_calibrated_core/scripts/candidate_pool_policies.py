"""Reusable candidate-pool construction policies.

The canonical manuscript pipeline's own pool construction
(`run_phase0_phase1._select_candidates`) selects the top-`top_k` documents
of an RRF-fused ranking over the union of three rankers' native scores.
This module adds alternative, independently-defined pool policies so the
paper's structural/retrieval conclusions can be checked for dependence on
that specific choice (see
reports/candidate_pool_conditional_audit_20260714/AUDIT.md section 1).

Every policy function has the signature
``(ranker_scores: dict[str, dict[str, float]], top_k: int) -> list[str]``,
matching ``_select_candidates`` exactly, so any policy is a drop-in
replacement. All policies are deterministic (no reliance on dict/set
iteration order; every tie is broken by ascending ``doc_id``), take no
qrels, and preserve the identical query set (a policy only changes which
*documents* are eligible per query, never which *queries* are evaluated).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

REPO_ROOT = SCRIPT_DIR.parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from run_phase0_phase1 import _select_candidates as _select_candidates_rrf_union  # noqa: E402

from consistency_ranker.combsum_ranking import combsum_ranking  # noqa: E402

RANKERS = ("bm25", "tfidf", "minilm")

PoolPolicyFn = Callable[[dict, int], list]


def select_candidates_rrf_union(
    ranker_scores: dict[str, dict[str, float]], top_k: int
) -> list[str]:
    """The existing canonical policy, wrapped only for a uniform interface.

    Delegates to the unmodified ``run_phase0_phase1._select_candidates`` so
    this module can never silently diverge from the canonical protocol.
    """
    return _select_candidates_rrf_union(ranker_scores, top_k)


def select_candidates_equal_depth_union(
    ranker_scores: dict[str, dict[str, float]], top_k: int
) -> list[str]:
    """Union of each ranker's own top-``top_k`` documents (policy A).

    Depth is equal per ranker; the resulting pool size varies per query
    (between ``top_k`` and ``3 * top_k``) depending on cross-ranker
    overlap, unlike the RRF-truncated canonical pool, which is always
    exactly ``top_k`` once the union exceeds it. No fusion score is
    computed; membership is decided per-ranker only.
    """
    pool: set[str] = set()
    for ranker in RANKERS:
        scores = ranker_scores.get(ranker, {})
        ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
        pool.update(doc_id for doc_id, _score in ranked[:top_k])
    return sorted(pool)


def select_candidates_round_robin_union(
    ranker_scores: dict[str, dict[str, float]], top_k: int
) -> list[str]:
    """Neutral depth-``top_k`` union independent of RRF (policy B).

    Deterministic round-robin: take rank 1 from bm25, then tfidf, then
    minilm, then rank 2 from each in the same order, and so on, skipping
    documents already added, until exactly ``top_k`` documents are
    collected or every ranker is exhausted. Ranker turn order is fixed
    (alphabetical: bm25, tfidf, minilm) rather than derived from any
    fused score, so no reciprocal-rank-fusion weighting enters pool
    selection at all. Depth matches the canonical pool's depth exactly,
    which the equal-depth-union policy (A) does not, making this the
    directly size-comparable alternative to the canonical RRF pool.
    """
    ranked_by_ranker = {
        ranker: [
            doc_id
            for doc_id, _score in sorted(
                ranker_scores.get(ranker, {}).items(), key=lambda x: (-x[1], x[0])
            )
        ]
        for ranker in RANKERS
    }
    pool: list[str] = []
    seen: set[str] = set()
    depth = 0
    max_depth = max((len(v) for v in ranked_by_ranker.values()), default=0)
    while len(pool) < top_k and depth < max_depth:
        for ranker in RANKERS:
            docs = ranked_by_ranker[ranker]
            if depth < len(docs):
                doc_id = docs[depth]
                if doc_id not in seen:
                    seen.add(doc_id)
                    pool.append(doc_id)
                    if len(pool) >= top_k:
                        break
        depth += 1
    return sorted(pool)


def select_candidates_bm25_only(
    ranker_scores: dict[str, dict[str, float]], top_k: int
) -> list[str]:
    """Single-ranker candidate pool: top-``top_k`` BM25 documents only (policy C).

    Ignores TF-IDF and MiniLM entirely for pool *membership* (they still
    participate in downstream normalization/voting/graph construction for
    whichever documents happen to also be in this BM25-selected pool).
    """
    scores = ranker_scores.get("bm25", {})
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    return sorted(doc_id for doc_id, _score in ranked[:top_k])


def select_candidates_combsum_union(
    ranker_scores: dict[str, dict[str, float]], top_k: int
) -> list[str]:
    """Top-``top_k`` of a CombSUM-fused ranking over the union (policy D).

    Reuses the existing, tested ``consistency_ranker.combsum_ranking.combsum_ranking``
    (per-query/per-ranker min-max normalization, summed across rankers,
    deterministic tie-break by best original rank then doc_id) rather than
    reimplementing fusion logic, so this policy can never silently diverge
    from the CombSUM baseline method used elsewhere in the same pipeline.
    """
    per_system_best_scores = [ranker_scores.get(ranker, {}) for ranker in RANKERS]
    union_docs = sorted({doc_id for scores in per_system_best_scores for doc_id in scores})
    ranked = combsum_ranking(per_system_best_scores, union_docs, normalization="minmax")
    return sorted(ranked[:top_k])


@dataclass(frozen=True)
class PoolSpec:
    pool_id: str
    policy_fn_name: str
    label: str
    kind: str

    _VALID_KINDS = ("canonical", "alternative")

    def __post_init__(self) -> None:
        if self.policy_fn_name not in POOL_POLICY_REGISTRY:
            raise ValueError(
                f"unknown policy_fn_name {self.policy_fn_name!r}; must be one of "
                f"{sorted(POOL_POLICY_REGISTRY)}"
            )
        if self.kind not in self._VALID_KINDS:
            raise ValueError(f"kind must be one of {self._VALID_KINDS}, got {self.kind!r}")
        if not self.pool_id or not self.label:
            raise ValueError("pool_id and label must be non-empty")

    def to_dict(self) -> dict[str, str]:
        return {
            "pool_id": self.pool_id,
            "policy_fn_name": self.policy_fn_name,
            "label": self.label,
            "kind": self.kind,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, str]) -> "PoolSpec":
        return cls(**payload)

    @property
    def policy_fn(self) -> PoolPolicyFn:
        return POOL_POLICY_REGISTRY[self.policy_fn_name]


POOL_POLICY_REGISTRY: dict[str, PoolPolicyFn] = {
    "select_candidates_rrf_union": select_candidates_rrf_union,
    "select_candidates_equal_depth_union": select_candidates_equal_depth_union,
    "select_candidates_round_robin_union": select_candidates_round_robin_union,
    "select_candidates_bm25_only": select_candidates_bm25_only,
    "select_candidates_combsum_union": select_candidates_combsum_union,
}

POOL_SPECS: dict[str, PoolSpec] = {
    "rrf_union_topk": PoolSpec(
        pool_id="rrf_union_topk",
        policy_fn_name="select_candidates_rrf_union",
        label="RRF-fused top-k union (canonical)",
        kind="canonical",
    ),
    "equal_depth_union": PoolSpec(
        pool_id="equal_depth_union",
        policy_fn_name="select_candidates_equal_depth_union",
        label="Equal-depth top-k union across all three rankers",
        kind="alternative",
    ),
    "neutral_round_robin_union": PoolSpec(
        pool_id="neutral_round_robin_union",
        policy_fn_name="select_candidates_round_robin_union",
        label="Neutral round-robin depth-k union (RRF-independent)",
        kind="alternative",
    ),
    "bm25_only": PoolSpec(
        pool_id="bm25_only",
        policy_fn_name="select_candidates_bm25_only",
        label="BM25-only top-k pool",
        kind="alternative",
    ),
    "combsum_union_topk": PoolSpec(
        pool_id="combsum_union_topk",
        policy_fn_name="select_candidates_combsum_union",
        label="CombSUM-fused top-k union",
        kind="alternative",
    ),
}
