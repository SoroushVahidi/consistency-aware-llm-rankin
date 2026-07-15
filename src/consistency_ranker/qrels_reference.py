"""Helpers for candidate-aligned qrels evaluation and judged-pair diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import networkx as nx


@dataclass(frozen=True)
class CandidateQrelsReference:
    """Candidate-aligned qrels view with separate metric and judged-pair maps."""

    candidate_ranking: list[str]
    eval_rel_map: dict[str, int]
    judged_rel_map: dict[str, int]


def _dedup_highest_relevance(qrels_for_query: Iterable[object]) -> dict[str, int]:
    judged_rel_map: dict[str, int] = {}
    for entry in qrels_for_query:
        doc_id = str(entry.doc_id)
        relevance = int(entry.relevance)
        judged_rel_map[doc_id] = max(judged_rel_map.get(doc_id, relevance), relevance)
    return judged_rel_map


def build_candidate_qrels_reference(
    qrels_for_query: Iterable[object],
    candidates: Iterable[str],
) -> CandidateQrelsReference:
    """Build candidate-aligned qrels data without manufacturing judged pairs.

    ``eval_rel_map`` contains every candidate document, assigning 0 to
    unjudged candidates so ranking metrics continue to treat them as
    non-relevant. ``judged_rel_map`` contains only explicit qrels and is the
    sole source for judged-pair diagnostics such as BEW, PIC, and pairwise
    relevance accuracy.
    """

    judged_rel_map = _dedup_highest_relevance(qrels_for_query)
    candidate_ranking = sorted({str(doc_id) for doc_id in candidates})
    eval_rel_map = {doc_id: int(judged_rel_map.get(doc_id, 0)) for doc_id in candidate_ranking}
    candidate_ranking.sort(key=lambda doc_id: (-eval_rel_map[doc_id], doc_id))
    return CandidateQrelsReference(
        candidate_ranking=candidate_ranking,
        eval_rel_map=eval_rel_map,
        judged_rel_map=judged_rel_map,
    )


def judged_pair_preference(
    doc_a: str,
    doc_b: str,
    judged_rel_map: dict[str, int],
) -> int | None:
    """Return the explicit judged preference for a pair, or ``None``.

    The pair is comparable only when both documents have explicit qrels and
    their relevance grades differ. Equal-grade pairs and any pair containing
    an unjudged document are intentionally incomparable.
    """

    rel_a = judged_rel_map.get(doc_a)
    rel_b = judged_rel_map.get(doc_b)
    if rel_a is None or rel_b is None or rel_a == rel_b:
        return None
    return 1 if rel_a > rel_b else -1


def pairwise_accuracy_for_judged_pairs(
    ranking: list[str],
    judged_rel_map: dict[str, int],
) -> float | None:
    if len(ranking) < 2:
        return None
    pos = {doc_id: idx for idx, doc_id in enumerate(ranking)}
    docs = list(ranking)
    correct = 0
    total = 0
    for idx, left in enumerate(docs):
        for right in docs[idx + 1 :]:
            preference = judged_pair_preference(left, right, judged_rel_map)
            if preference is None:
                continue
            total += 1
            if (preference > 0 and pos[left] < pos[right]) or (
                preference < 0 and pos[right] < pos[left]
            ):
                correct += 1
    return (correct / total) if total > 0 else None


def judged_pair_order_changed(
    ranking_a: list[str],
    ranking_b: list[str],
    judged_rel_map: dict[str, int],
    *,
    docs: Iterable[str] | None = None,
) -> bool:
    """Whether two rankings disagree on any explicit different-grade pair."""

    if docs is None:
        candidate_docs = list({*ranking_a, *ranking_b})
    else:
        candidate_docs = [str(doc_id) for doc_id in docs]
    pos_a = {doc_id: idx for idx, doc_id in enumerate(ranking_a)}
    pos_b = {doc_id: idx for idx, doc_id in enumerate(ranking_b)}
    available_docs = [doc_id for doc_id in candidate_docs if doc_id in pos_a and doc_id in pos_b]
    for idx, left in enumerate(available_docs):
        for right in available_docs[idx + 1 :]:
            if judged_pair_preference(left, right, judged_rel_map) is None:
                continue
            if (pos_a[left] < pos_a[right]) != (pos_b[left] < pos_b[right]):
                return True
    return False


def qrels_pairwise_inconsistency(
    graph: nx.DiGraph,
    judged_rel_map: dict[str, int],
) -> int:
    count = 0
    for winner, loser in graph.edges():
        preference = judged_pair_preference(winner, loser, judged_rel_map)
        if preference is not None and preference < 0:
            count += 1
    return count


def qrels_backward_edge_weight(
    graph: nx.DiGraph,
    judged_rel_map: dict[str, int],
) -> float:
    total = 0.0
    for winner, loser, data in graph.edges(data=True):
        preference = judged_pair_preference(winner, loser, judged_rel_map)
        if preference is not None and preference < 0:
            total += float(data.get("weight", 1.0))
    return total
