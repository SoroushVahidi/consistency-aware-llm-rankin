"""Extended query processing with matched repair pairs and variants."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import networkx as nx

from consistency_ranker.baseline_ranking import (
    borda_scores,
    copeland_ranking,
    topological_ranking,
    weighted_out_minus_in_ranking,
)
from consistency_ranker.failure_mining.query_processor import process_query_record
from consistency_ranker.greedy_fas import greedy_fas
from consistency_ranker.markov_graph_ranking import DEFAULT_MARKOV_DAMPING, markov_graph_ranking
from consistency_ranker.metric_aware_repair import metric_aware_edge_weights
from consistency_ranker.pairwise_prefs import Preference
from consistency_ranker.repair_selector_mining.repair_pairs import REPAIR_PAIRS

from scripts.run_real_experiment import _ndcg_at_k, _reference_ranking_for_candidates

ILP_MAX_NODES = 20
EXACT_DP_MAX_NODES = 16


def _ranking_scores(ranking: list[str]) -> dict[str, float]:
    n = len(ranking)
    return {doc_id: float(n - i) for i, doc_id in enumerate(ranking)}


def _eval_ranking(
    ranking: list[str],
    *,
    ref_ranking: list[str],
    rel_map: dict[str, int],
    top_k: int,
) -> dict[str, Any]:
    aligned = [d for d in ranking if d in set(ref_ranking)]
    ndcg = _ndcg_at_k(aligned, rel_map, k=top_k)
    return {"ranking": ranking, "scores": _ranking_scores(ranking), "ndcg_at_k": ndcg}


def _build_repair_dags(graph: nx.DiGraph) -> dict[str, nx.DiGraph]:
    dags: dict[str, nx.DiGraph] = {}
    dag_greedy, _ = greedy_fas(graph)
    dags["greedy_fas"] = dag_greedy
    n = graph.number_of_nodes()
    if n <= ILP_MAX_NODES:
        try:
            from consistency_ranker.mwfas_solver import solve

            dag_ilp, _ = solve(graph, method="ilp")
            dags["ilp"] = dag_ilp
        except Exception:
            pass
    if n <= EXACT_DP_MAX_NODES:
        try:
            import importlib.util

            caar_solver = Path("/home/soroush/consistency-aware-llm-rankin-caar/src/consistency_ranker/mwfas_solver.py")
            if caar_solver.exists():
                spec = importlib.util.spec_from_file_location("caar_mwfas", caar_solver)
                mod = importlib.util.module_from_spec(spec)
                assert spec.loader is not None
                spec.loader.exec_module(mod)
                dag_dp, _ = mod.solve(graph, method="exact_dp")
                dags["exact_dp"] = dag_dp
        except Exception:
            pass
    return dags


def _topological_or_markov_fallback(graph: nx.DiGraph) -> list[str]:
    if nx.is_directed_acyclic_graph(graph):
        return topological_ranking(graph)
    from consistency_ranker.markov_graph_ranking import markov_graph_ranking

    return markov_graph_ranking(graph)


def _extra_rankings(
    graph: nx.DiGraph,
    dags: dict[str, nx.DiGraph],
    *,
    score_sum_prior: dict[str, float],
    damping: float = DEFAULT_MARKOV_DAMPING,
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {
        "copeland": copeland_ranking(graph),
        "balance": weighted_out_minus_in_ranking(graph),
        "topological_unrepaired": _topological_or_markov_fallback(graph),
    }
    dag = dags.get("greedy_fas", graph)
    out["copeland_repaired"] = copeland_ranking(dag)
    out["balance_repaired"] = weighted_out_minus_in_ranking(dag)
    out["greedy_fas_topological"] = topological_ranking(dag)
    if "ilp" in dags:
        out["markov_graph_ilp_repaired"] = markov_graph_ranking(dags["ilp"], damping=damping)
    if "exact_dp" in dags:
        out["markov_graph_exact_dp_repaired"] = markov_graph_ranking(dags["exact_dp"], damping=damping)
    return out


def _metric_aware_variant(
    graph: nx.DiGraph,
    *,
    prior_scores: dict[str, float],
    damping: float = DEFAULT_MARKOV_DAMPING,
) -> dict[str, Any] | None:
    """Metric-aware repair kept separate from standard MWFAS label."""
    try:
        weights = metric_aware_edge_weights(graph, prior_scores=prior_scores)
        weighted = nx.DiGraph()
        for u, v, data in graph.edges(data=True):
            w = float(weights.get((u, v), data.get("weight", 1.0)))
            weighted.add_edge(u, v, weight=w, margin=data.get("margin", w))
        dag, removed = greedy_fas(weighted)
        ranking = markov_graph_ranking(dag, damping=damping)
        return {
            "ranking": ranking,
            "n_edges_removed": len(removed),
            "repair_backend": "metric_aware_greedy_fas",
        }
    except Exception:
        return None


def process_repair_query(
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
    """Build full record with matched repair pairs and variant metadata."""
    base = process_query_record(
        dataset=dataset,
        vote_regime=vote_regime,
        query_id=query_id,
        query_text=query_text,
        split=split,
        qrels_for_query=qrels_for_query,
        prefs=prefs,
        score_prior_sets=score_prior_sets,
        top_k=top_k,
        doc_snippets=doc_snippets,
        markov_damping=markov_damping,
    )
    if base is None:
        return None

    from consistency_ranker.graph_construction import build_graph

    graph = build_graph(prefs)
    ref_ranking, rel_map = _reference_ranking_for_candidates(
        qrels_for_query=qrels_for_query,
        candidates=graph.nodes(),
    )
    score_sum_prior = base["baseline_info"].get("score_sum_scores", {})
    dags = _build_repair_dags(graph)
    extra = _extra_rankings(graph, dags, score_sum_prior=score_sum_prior, damping=markov_damping)

    method_outputs = dict(base["method_outputs"])
    for name, ranking in extra.items():
        if name not in method_outputs:
            method_outputs[name] = _eval_ranking(
                ranking, ref_ranking=ref_ranking, rel_map=rel_map, top_k=top_k
            )

    metric_variant = _metric_aware_variant(graph, prior_scores=score_sum_prior, damping=markov_damping)
    if metric_variant:
        base["metric_aware_repair"] = {
            **metric_variant,
            "ndcg_at_k": _eval_ranking(
                metric_variant["ranking"],
                ref_ranking=ref_ranking,
                rel_map=rel_map,
                top_k=top_k,
            )["ndcg_at_k"],
        }

    repair_pair_results: list[dict[str, Any]] = []
    for pair in REPAIR_PAIRS:
        rep = method_outputs.get(pair.repaired, {}).get("ndcg_at_k")
        unrep = method_outputs.get(pair.unrepaired, {}).get("ndcg_at_k")
        if rep is None or unrep is None:
            continue
        gain = float(rep) - float(unrep)
        repair_pair_results.append(
            {
                "dataset": dataset,
                "vote_regime": vote_regime,
                "query_id": query_id,
                "repaired_method": pair.repaired,
                "unrepaired_method": pair.unrepaired,
                "repair_backend": pair.repair_backend,
                "extraction": pair.extraction,
                "ndcg_repaired": rep,
                "ndcg_unrepaired": unrep,
                "repair_gain": gain,
                "split": split,
            }
        )

    base["method_outputs"] = method_outputs
    base["repair_pair_results"] = repair_pair_results
    base["query_metadata"]["split"] = split
    base["split_assignment"] = split
    return base


def repair_gain(record: dict, *, repaired: str, unrepaired: str) -> float | None:
    rep = record.get("method_outputs", {}).get(repaired, {}).get("ndcg_at_k")
    unrep = record.get("method_outputs", {}).get(unrepaired, {}).get("ndcg_at_k")
    if rep is None or unrep is None:
        return None
    return float(rep) - float(unrep)
