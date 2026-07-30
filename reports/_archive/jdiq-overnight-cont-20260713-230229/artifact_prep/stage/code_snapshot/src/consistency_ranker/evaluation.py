"""
evaluation.py
=============
Evaluation metrics for ranking quality and preference consistency.

Metrics
-------
kendall_tau:
    Kendall τ rank correlation between a predicted ranking and a reference
    ranking.  Returns a value in [-1, +1]; +1 means perfect agreement.

pairwise_inconsistency_count:
    Count the number of pairs (i, j) where the graph edge direction disagrees
    with the ground-truth preference.

ranking_agreement:
    Fraction of pairs where predicted and reference ranking agree.

n_violations:
    Count pairs where the predicted ranking disagrees with the reference.
"""

from __future__ import annotations

import itertools
import math

import networkx as nx


def kendall_tau(ranking: list[str], reference: list[str]) -> float:
    """Compute Kendall τ rank correlation between *ranking* and *reference*.

    Both lists must contain exactly the same items.

    Parameters
    ----------
    ranking:
        Predicted ranking (index 0 = best).
    reference:
        Ground-truth ranking (index 0 = best).

    Returns
    -------
    float
        Kendall τ in ``[-1.0, +1.0]``.  Returns ``0.0`` if fewer than 2 items.

    Raises
    ------
    ValueError
        If *ranking* and *reference* do not contain the same items.
    """
    if set(ranking) != set(reference):
        raise ValueError(
            "ranking and reference must contain the same items. "
            f"Extra in ranking: {set(ranking) - set(reference)}, "
            f"Extra in reference: {set(reference) - set(ranking)}"
        )
    n = len(ranking)
    if n < 2:
        return 0.0

    # Build position lookup
    pos_pred = {item: i for i, item in enumerate(ranking)}
    pos_ref = {item: i for i, item in enumerate(reference)}

    concordant = 0
    discordant = 0
    for a, b in itertools.combinations(ranking, 2):
        pred_order = pos_pred[a] < pos_pred[b]
        ref_order = pos_ref[a] < pos_ref[b]
        if pred_order == ref_order:
            concordant += 1
        else:
            discordant += 1

    total = concordant + discordant
    return (concordant - discordant) / total if total > 0 else 0.0


def ranking_agreement(ranking: list[str], reference: list[str]) -> float:
    """Fraction of pairs where *ranking* agrees with *reference*.

    Parameters
    ----------
    ranking:
        Predicted ranking.
    reference:
        Ground-truth ranking.

    Returns
    -------
    float
        Value in ``[0.0, 1.0]``.
    """
    tau = kendall_tau(ranking, reference)
    return (tau + 1.0) / 2.0


def n_violations(ranking: list[str], reference: list[str]) -> int:
    """Count the number of pairwise order violations.

    A violation occurs for a pair (a, b) where *reference* prefers a over b but
    *ranking* places b before a (or vice versa).

    Parameters
    ----------
    ranking:
        Predicted ranking.
    reference:
        Ground-truth ranking.

    Returns
    -------
    int
        Number of discordant pairs.
    """
    n = len(ranking)
    if n < 2:
        return 0
    pos_pred = {item: i for i, item in enumerate(ranking)}
    pos_ref = {item: i for i, item in enumerate(reference)}
    count = 0
    for a, b in itertools.combinations(reference, 2):
        pred_order = pos_pred[a] < pos_pred[b]
        ref_order = pos_ref[a] < pos_ref[b]
        if pred_order != ref_order:
            count += 1
    return count


def pairwise_inconsistency_count(
    graph: nx.DiGraph,
    reference_ranking: list[str],
) -> int:
    """Count edges in *graph* that disagree with *reference_ranking*.

    An edge u → v is *inconsistent* with the reference if the reference ranks v
    above u (i.e. v is preferred over u in the ground truth).

    Parameters
    ----------
    graph:
        Directed preference graph.
    reference_ranking:
        Ground-truth ranking (index 0 = best).

    Returns
    -------
    int
        Number of inconsistent edges.
    """
    pos = {item: i for i, item in enumerate(reference_ranking)}
    count = 0
    for u, v in graph.edges():
        # Edge u→v says "u preferred over v"
        # Inconsistent if reference says v is better than u (pos[v] < pos[u])
        u_pos = pos.get(u)
        v_pos = pos.get(v)
        if u_pos is not None and v_pos is not None and v_pos < u_pos:
            count += 1
    return count


# ---------------------------------------------------------------------------
# Retrieval metrics (NDCG, MRR, Recall@k)
# ---------------------------------------------------------------------------


def ndcg_at_k(
    ranking: list[str],
    relevance_map: dict[str, int],
    k: int = 10,
) -> float:
    """Compute NDCG@k for a ranking given graded relevance.

    Uses the standard formula: DCG@k = sum_{i=1}^{k} (2^{rel_i} - 1) / log2(i+1).
    IDCG is computed from the ideal ranking (relevant docs sorted by grade).
    NDCG = DCG / IDCG; returns 0.0 if IDCG is 0 (no relevant docs).

    Parameters
    ----------
    ranking:
        Predicted ranking (index 0 = best). Doc ids not in *relevance_map*
        are treated as relevance 0.
    relevance_map:
        doc_id -> relevance grade (0 = not relevant, higher = more relevant).
    k:
        Cut-off position.

    Returns
    -------
    float
        NDCG@k in [0.0, 1.0].
    """
    def dcg(ordered_relevances: list[int], cutoff: int) -> float:
        total = 0.0
        for i in range(min(cutoff, len(ordered_relevances))):
            rel = ordered_relevances[i]
            total += (math.pow(2, rel) - 1) / math.log2(i + 2)
        return total

    relevances = [relevance_map.get(doc_id, 0) for doc_id in ranking[:k]]
    dcg_val = dcg(relevances, k)

    ideal_relevances = sorted(relevance_map.values(), reverse=True)
    idcg_val = dcg(ideal_relevances, k)

    if idcg_val <= 0:
        return 0.0
    return dcg_val / idcg_val


def mrr(
    ranking: list[str],
    relevant_ids: set[str],
) -> float:
    """Compute Reciprocal Rank — 1 / rank of first relevant document.

    Parameters
    ----------
    ranking:
        Predicted ranking (index 0 = best).
    relevant_ids:
        Set of document ids that are considered relevant.

    Returns
    -------
    float
        1/rank of first relevant doc, or 0.0 if no relevant doc in ranking.
    """
    for i, doc_id in enumerate(ranking):
        if doc_id in relevant_ids:
            return 1.0 / (i + 1)
    return 0.0


def recall_at_k(
    ranking: list[str],
    relevant_ids: set[str],
    k: int,
) -> float:
    """Compute Recall@k — fraction of relevant docs in top-k.

    Parameters
    ----------
    ranking:
        Predicted ranking (index 0 = best).
    relevant_ids:
        Set of document ids that are considered relevant.
    k:
        Cut-off position.

    Returns
    -------
    float
        |relevant ∩ ranking[:k]| / |relevant|. Returns 0.0 if no relevant docs.
    """
    if not relevant_ids:
        return 0.0
    top_k = set(ranking[:k])
    hits = len(relevant_ids & top_k)
    return hits / len(relevant_ids)
