"""Offline pairwise-oracle loading for the active-acquisition pilot.

Loads the exhaustive, already-collected real OpenAI (gpt-4o-mini) pairwise
judgments for SciDocs from ``outputs/openai_scidocs_real_pairwise_q50_k15/``
(a frozen, pre-existing artifact — not modified or regenerated here) and
exposes, per query:

* a fixed candidate pool;
* the exhaustive win/loss oracle (revealed only on request by the simulator);
* a cheap, offline, qrels-free initial ranking score (in-pool BM25);
* qrels relevance, kept separate and used only by the evaluation module —
  never passed to any acquisition-scoring function.

No live provider or API calls are made anywhere in this module.
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from consistency_ranker.data.unified_loader import load_dataset_splits

_TOKEN_RE = re.compile(r"[^\w\s]")

DEFAULT_JUDGMENTS_PATH = "outputs/openai_scidocs_real_pairwise_q50_k15/judgments.jsonl"


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.sub(" ", text.lower()).split()


@dataclass(frozen=True)
class QueryOracle:
    """Everything needed to simulate acquisition for one query."""

    query_id: str
    candidates: tuple[str, ...]
    oracle: dict[frozenset, str]
    bm25_scores: dict[str, float]
    relevance: dict[str, int]

    def all_pairs(self) -> list[tuple[str, str]]:
        """All unordered candidate pairs, in a fixed deterministic order."""
        cands = self.candidates
        return [(cands[a], cands[b]) for a in range(len(cands)) for b in range(a + 1, len(cands))]

    def reveal(self, i: str, j: str) -> tuple[str, str]:
        """Reveal the cached judgment for pair (i, j) as (winner, loser)."""
        key = frozenset((i, j))
        winner = self.oracle[key]
        loser = j if winner == i else i
        return winner, loser


def bm25_scores(
    query_text: str, doc_text: dict[str, str], *, k1: float = 1.5, b: float = 0.75
) -> dict[str, float]:
    """Deterministic, offline, in-pool Okapi BM25.

    Computed only from the (already-cached) query text and candidate document
    text supplied by the caller — no qrels, no judgments, no network access.
    Serves as the pilot's "inexpensive initial ranking" (Phase 2, step 1).
    """
    q_terms = _tokenize(query_text)
    doc_terms = {d: _tokenize(t) for d, t in doc_text.items()}
    doc_len = {d: len(toks) for d, toks in doc_terms.items()}
    avgdl = (sum(doc_len.values()) / len(doc_len)) if doc_len else 0.0
    n_docs = max(len(doc_terms), 1)
    df: dict[str, int] = defaultdict(int)
    for toks in doc_terms.values():
        for term in set(toks):
            df[term] += 1
    scores: dict[str, float] = {}
    for d, toks in doc_terms.items():
        tf: dict[str, int] = defaultdict(int)
        for term in toks:
            tf[term] += 1
        score = 0.0
        dl = doc_len[d] or 1
        # sorted(), not bare set() iteration: dict/set iteration order is not
        # guaranteed stable across PYTHONHASHSEED values, and `score +=` is a
        # floating-point accumulation, so an unsorted set iteration here
        # produced tiny (~1e-15) run-to-run differences in bm25_scores that
        # the regularized-aggregation optimizer (regularized_aggregation.py)
        # is sensitive enough to amplify into visibly different rankings.
        # This was invisible to the Copeland-extraction pilot (ties at that
        # scale essentially never flip a sort order) but violates the
        # determinism this module now needs to guarantee.
        for term in sorted(set(q_terms)):
            if term not in tf:
                continue
            n_q = df.get(term, 0)
            idf = math.log(1.0 + (n_docs - n_q + 0.5) / (n_q + 0.5))
            freq = tf[term]
            denom = freq + k1 * (1 - b + b * dl / (avgdl or 1.0))
            score += idf * (freq * (k1 + 1)) / (denom or 1e-9)
        scores[d] = score
    return scores


def load_scidocs_pairwise_oracle(
    judgments_path: Path | str = DEFAULT_JUDGMENTS_PATH,
) -> dict[str, QueryOracle]:
    """Load the exhaustive cached pairwise-judgment oracle, one entry per query.

    Raises if any query's cached judgments are not exhaustive over its
    candidate pool (``C(n, 2)`` pairs) — this pilot requires an exhaustive
    offline oracle so any acquired-budget subset can be evaluated fairly
    against the same "ground truth" exhaustive result.
    """
    judgments_path = Path(judgments_path)
    raw_by_query: dict[str, list[dict]] = defaultdict(list)
    with judgments_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            raw_by_query[row["query_id"]].append(row)

    queries, documents, qrels = load_dataset_splits("scidocs")
    query_text_by_id = {q.query_id: q.text for q in queries}
    doc_text_by_id = {d.doc_id: f"{d.title} {d.text}".strip() for d in documents}
    qrels_by_query: dict[str, dict[str, int]] = defaultdict(dict)
    for e in qrels:
        prev = qrels_by_query[e.query_id].get(e.doc_id, e.relevance)
        qrels_by_query[e.query_id][e.doc_id] = max(prev, e.relevance)

    result: dict[str, QueryOracle] = {}
    for qid, rows in raw_by_query.items():
        cand_set: set[str] = set()
        oracle: dict[frozenset, str] = {}
        for row in rows:
            w, loser = row["winner_doc_id"], row["loser_doc_id"]
            cand_set.add(w)
            cand_set.add(loser)
            oracle[frozenset((w, loser))] = w
        candidates = tuple(sorted(cand_set))
        n_expected = len(candidates) * (len(candidates) - 1) // 2
        if len(oracle) != n_expected:
            raise ValueError(
                f"query {qid}: expected exhaustive {n_expected} pairs for "
                f"{len(candidates)} candidates, found {len(oracle)} — this "
                "dataset does not satisfy the exhaustive-oracle precondition."
            )
        q_text = query_text_by_id.get(qid, "")
        doc_text = {d: doc_text_by_id.get(d, "") for d in candidates}
        scores = bm25_scores(q_text, doc_text)
        relevance = {d: qrels_by_query.get(qid, {}).get(d, 0) for d in candidates}
        result[qid] = QueryOracle(
            query_id=qid,
            candidates=candidates,
            oracle=oracle,
            bm25_scores=scores,
            relevance=relevance,
        )
    return result


__all__ = ["QueryOracle", "bm25_scores", "load_scidocs_pairwise_oracle", "DEFAULT_JUDGMENTS_PATH"]
