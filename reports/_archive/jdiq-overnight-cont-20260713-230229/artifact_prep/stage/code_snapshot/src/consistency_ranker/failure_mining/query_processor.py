"""Process a single query and build a full forensic failure-mining record."""

from __future__ import annotations

from typing import Any

import networkx as nx

from consistency_ranker.baseline_ranking import (
    borda_ranking,
    borda_scores,
    local_adjacent_swap_refinement,
    pagerank_ranking,
    rank_centrality_ranking,
    score_sum_ranking,
    score_sum_scores,
    topological_ranking,
)
from consistency_ranker.borda_fuse_ranking import per_query_borda_fuse_ranking_from_score_maps
from consistency_ranker.combsum_ranking import (
    COMBSUM_NORM_MINMAX,
    per_query_combsum_ranking_from_score_maps,
)
from consistency_ranker.failure_mining.analysis import OUR_REPAIRED_METHOD, OUR_UNREPAIRED_METHOD, compute_failure_labels
from consistency_ranker.failure_mining.data_setup import DEFAULT_RANKERS
from consistency_ranker.failure_mining.graph_features import backward_edge_weight, extended_graph_stats
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.greedy_fas import greedy_fas, greedy_fas_total_weight
from consistency_ranker.markov_graph_ranking import DEFAULT_MARKOV_DAMPING, markov_graph_ranking
from consistency_ranker.pairwise_prefs import Preference
from consistency_ranker.rrf_ranking import DEFAULT_RRF_K, per_query_rrf_ranking_from_score_maps
from rerankers.tournament_agg import bradley_terry_ranking

from scripts.run_real_experiment import (
    _average_precision_at_k,
    _kendall_tau,
    _ndcg_at_k,
    _pairwise_accuracy_from_relevance,
    _prior_only_ranking,
    _reference_ranking_for_candidates,
    _rrf_prior_scores_for_query,
    _score_sum_prior_scores,
)


def _mrr_at_k(ranking: list[str], rel_map: dict[str, int], k: int) -> float | None:
    if not ranking:
        return None
    k_eff = min(k, len(ranking))
    for i, doc_id in enumerate(ranking[:k_eff]):
        if rel_map.get(doc_id, 0) > 0:
            return 1.0 / (i + 1)
    return 0.0


def _prefs_to_tuples(prefs: list[Preference]) -> list[tuple[str, str, float]]:
    return [(p.winner, p.loser, float(p.weight)) for p in prefs]


def _ranking_scores_from_list(ranking: list[str]) -> dict[str, float]:
    n = len(ranking)
    return {doc_id: float(n - i) for i, doc_id in enumerate(ranking)}


def _evaluate_ranking(
    ranking: list[str],
    *,
    ref_ranking: list[str],
    rel_map: dict[str, int],
    top_k: int,
    graph: nx.DiGraph,
    prior_ndcg: float | None,
    unrepaired_ndcg: float | None,
    best_external_ndcg: float | None,
) -> dict[str, Any]:
    aligned = [d for d in ranking if d in set(ref_ranking)]
    ndcg = _ndcg_at_k(aligned, rel_map, k=top_k)
    return {
        "ranking": ranking,
        "scores": _ranking_scores_from_list(ranking),
        "ndcg_at_k": ndcg,
        "map_at_k": _average_precision_at_k(aligned, rel_map, k=top_k),
        "mrr_at_k": _mrr_at_k(aligned, rel_map, k=top_k),
        "pairwise_accuracy": _pairwise_accuracy_from_relevance(aligned, rel_map),
        "kendall_tau": _kendall_tau(aligned, ref_ranking),
        "backward_edge_weight": backward_edge_weight(graph, ranking),
        "delta_vs_prior": (ndcg - prior_ndcg) if ndcg is not None and prior_ndcg is not None else None,
        "delta_vs_unrepaired": (
            (ndcg - unrepaired_ndcg) if ndcg is not None and unrepaired_ndcg is not None else None
        ),
        "delta_vs_best_external": (
            (ndcg - best_external_ndcg)
            if ndcg is not None and best_external_ndcg is not None
            else None
        ),
    }


def process_query_record(
    *,
    dataset: str,
    vote_regime: str,
    query_id: str,
    query_text: str | None,
    split: str,
    qrels_for_query: list,
    prefs: list[Preference],
    score_prior_sets: list[dict[str, list[tuple[str, float]]]],
    top_k: int,
    doc_snippets: dict[str, dict[str, str]] | None = None,
    markov_damping: float = DEFAULT_MARKOV_DAMPING,
) -> dict[str, Any] | None:
    """Build a full forensic record for one query × vote regime."""
    if not prefs:
        return None

    graph = build_graph(prefs)
    if graph.number_of_nodes() < 2:
        return None

    ref_ranking, rel_map = _reference_ranking_for_candidates(
        qrels_for_query=qrels_for_query,
        candidates=graph.nodes(),
    )
    candidate_ids = sorted(graph.nodes())
    score_sum_prior = score_sum_scores(graph)
    prior_scores = _rrf_prior_scores_for_query(
        query_id=query_id,
        candidate_nodes=set(graph.nodes()),
        score_prior_sets=score_prior_sets,
        fallback_scores=_score_sum_prior_scores(graph),
    )

    graph_stats = extended_graph_stats(graph, prior_scores=prior_scores, ref_ranking=ref_ranking)

    dag, removed = greedy_fas(graph)
    fas_removed_weight = greedy_fas_total_weight(removed)
    repaired_stats = extended_graph_stats(dag, prior_scores=prior_scores, ref_ranking=ref_ranking)

    removed_edges = [
        {"source": u, "target": v, "weight": float(w)} for u, v, w in removed
    ]
    repaired_edges = [
        {"source": u, "target": v, "weight": float(d.get("weight", 1.0))}
        for u, v, d in dag.edges(data=True)
    ]

    pref_tuples = _prefs_to_tuples(prefs)
    all_docs = list(graph.nodes())

    rankings: dict[str, list[str]] = {
        "score_sum": score_sum_ranking(graph),
        "borda": borda_ranking(graph),
        "pagerank": pagerank_ranking(graph),
        "rank_centrality": rank_centrality_ranking(graph),
        OUR_UNREPAIRED_METHOD: markov_graph_ranking(graph, damping=markov_damping),
        OUR_REPAIRED_METHOD: markov_graph_ranking(dag, damping=markov_damping),
        "greedy_fas_topological": topological_ranking(dag),
        "prior_only": _prior_only_ranking(graph.nodes(), prior_scores),
    }

    if score_prior_sets:
        rankings["rrf"] = per_query_rrf_ranking_from_score_maps(
            query_id, score_prior_sets, graph.nodes(), k=DEFAULT_RRF_K
        )
        rankings["combsum"] = per_query_combsum_ranking_from_score_maps(
            query_id, score_prior_sets, graph.nodes(), normalization=COMBSUM_NORM_MINMAX
        )
        rankings["borda_fuse"] = per_query_borda_fuse_ranking_from_score_maps(
            query_id, score_prior_sets, graph.nodes()
        )

    bt = bradley_terry_ranking(pref_tuples, all_doc_ids=all_docs)
    rankings["bradley_terry"] = bt.ranked_doc_ids

    base_rank = rankings.get("rrf") or rankings.get("prior_only") or rankings[OUR_UNREPAIRED_METHOD]
    rankings["local_kemenization"] = local_adjacent_swap_refinement(base_rank, graph, objective="bew")

    # Pre-compute reference ndcgs for deltas
    prior_rank = rankings["prior_only"]
    prior_aligned = [d for d in prior_rank if d in set(ref_ranking)]
    prior_ndcg = _ndcg_at_k(prior_aligned, rel_map, k=top_k)
    unrepaired_aligned = [d for d in rankings[OUR_UNREPAIRED_METHOD] if d in set(ref_ranking)]
    unrepaired_ndcg = _ndcg_at_k(unrepaired_aligned, rel_map, k=top_k)

    external_ndcgs: list[float] = []
    method_outputs: dict[str, dict] = {}
    for name, ranking in rankings.items():
        aligned = [d for d in ranking if d in set(ref_ranking)]
        ndcg = _ndcg_at_k(aligned, rel_map, k=top_k)
        if name != OUR_REPAIRED_METHOD and ndcg is not None:
            external_ndcgs.append(ndcg)
        best_ext = max(external_ndcgs) if external_ndcgs else None
        method_outputs[name] = _evaluate_ranking(
            ranking,
            ref_ranking=ref_ranking,
            rel_map=rel_map,
            top_k=top_k,
            graph=graph,
            prior_ndcg=prior_ndcg,
            unrepaired_ndcg=unrepaired_ndcg,
            best_external_ndcg=best_ext,
        )

    failure_labels = compute_failure_labels(method_outputs)

    unrepaired_rank = rankings[OUR_UNREPAIRED_METHOD]
    repaired_rank = rankings[OUR_REPAIRED_METHOD]
    repair_changed_ranking = unrepaired_rank != repaired_rank

    qrels_dict = {e.doc_id: int(e.relevance) for e in qrels_for_query}

    candidate_id_set = set(candidate_ids)
    ranker_scores: dict[str, dict[str, float]] = {}
    for ranker_name, score_set in zip(DEFAULT_RANKERS, score_prior_sets):
        per_query = dict(score_set.get(query_id, []))
        ranker_scores[ranker_name] = {
            d: s for d, s in per_query.items() if d in candidate_id_set
        }

    return {
        "query_metadata": {
            "dataset": dataset,
            "vote_regime": vote_regime,
            "query_id": query_id,
            "query_text": query_text,
            "split": split,
            "n_candidates": len(candidate_ids),
            "candidate_doc_ids": candidate_ids,
            "qrels": qrels_dict,
            "doc_snippets": doc_snippets or {},
        },
        "baseline_info": {
            "prior_ranking": rankings["prior_only"],
            "prior_scores": prior_scores,
            "score_sum_scores": score_sum_prior,
            "borda_scores": borda_scores(graph),
            "bm25_scores": ranker_scores.get("bm25", {}),
            "tfidf_scores": ranker_scores.get("tfidf", {}),
            "minilm_scores": ranker_scores.get("minilm", {}),
        },
        "graph_stats": graph_stats,
        "repair_info": {
            "repair_applied": len(removed) > 0,
            "fas_method": "greedy_fas",
            "removed_edges": removed_edges,
            "fas_removed_weight": fas_removed_weight,
            "n_edges_removed": len(removed),
            "repaired_edges": repaired_edges,
            "bew_after_repair": repaired_stats.get("backward_edge_weight_pre_repair"),
            "pic_after_repair": repaired_stats.get("pairwise_inconsistency_pre_repair"),
            "largest_scc_after_repair": repaired_stats.get("largest_scc_size"),
            "is_dag_after_repair": repaired_stats.get("is_dag"),
            "repair_changed_final_ranking": repair_changed_ranking,
        },
        "method_outputs": method_outputs,
        "failure_labels": failure_labels,
    }
