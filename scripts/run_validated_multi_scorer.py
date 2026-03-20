#!/usr/bin/env python
"""
Validated multi-scorer experiment with FAIR comparison.

All methods use the SAME candidate set = union of bm25[:top_k] and dense[:top_k].
Methods: bm25_raw, dense_raw, rrf_fusion, score_sum (graph no FAS), greedy_fas_topological.

No qrels in preference construction. Dense is BM25-reranked (same candidate pool).
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import networkx as nx

from consistency_ranker.baseline_ranking import score_sum_ranking, topological_ranking
from consistency_ranker.data.dataset_registry import get_config
from consistency_ranker.data.unified_loader import (
    load_dataset_splits,
    load_multi_scorer_rankings,
    preferences_from_multiple_score_rankings,
)
from consistency_ranker.evaluation import mrr, ndcg_at_k, recall_at_k
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.greedy_fas import greedy_fas
from consistency_ranker.pairwise_prefs import Preference


def rrf_fusion(scorer_rankings: dict[str, list[tuple[str, float]]], k: int = 60) -> list[str]:
    """Reciprocal Rank Fusion. RRF_score(d) = sum 1/(k + rank_i)."""
    scores: dict[str, float] = {}
    for cands in scorer_rankings.values():
        for r, (doc_id, _) in enumerate(cands):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + r + 1)
    return sorted(scores, key=lambda d: scores[d], reverse=True)


def _rank_by_scores(candidate_set: list[str], score_map: dict[str, float]) -> list[str]:
    """Rank candidate_set by score_map. Docs not in map get -inf."""
    return sorted(candidate_set, key=lambda d: score_map.get(d, float("-inf")), reverse=True)


def _backward_edge_weight(graph: nx.DiGraph, ranking: list[str]) -> float:
    """Sum of weights of edges that disagree with ranking. Edge u→v is backward if v ranked before u."""
    pos = {n: i for i, n in enumerate(ranking)}
    total = 0.0
    for u, v, data in graph.edges(data=True):
        u_pos, v_pos = pos.get(u), pos.get(v)
        if u_pos is not None and v_pos is not None and v_pos < u_pos:
            total += data.get("weight", 1.0)
    return total


def run_query(
    qid: str,
    scorer_rankings: dict[str, list[tuple[str, float]]],
    top_k: int,
    mode: str,
    relevance_map: dict[str, int],
    relevant_ids: set[str],
    return_rankings: bool = False,
) -> dict | tuple[dict, dict[str, list[str]]]:
    """Run validated pipeline for one query. All methods use same candidate set."""
    # Common candidate set = union of bm25[:top_k] and dense[:top_k]
    bm25_docs = {d for d, _ in scorer_rankings["bm25"][:top_k]}
    dense_docs = {d for d, _ in scorer_rankings["dense"][:top_k]}
    candidate_set = sorted(bm25_docs | dense_docs)

    bm25_scores = {d: s for d, s in scorer_rankings["bm25"]}
    dense_scores = {d: s for d, s in scorer_rankings["dense"]}

    sr_truncated = {
        "bm25": scorer_rankings["bm25"][:top_k],
        "dense": scorer_rankings["dense"][:top_k],
    }
    prefs = preferences_from_multiple_score_rankings(qid, sr_truncated, weight_mode=mode)
    graph_prefs = [Preference(p.winner_doc_id, p.loser_doc_id, p.weight) for p in prefs]
    graph = build_graph(graph_prefs)
    dag, _ = greedy_fas(graph)

    rankings = {}
    rankings["bm25_raw"] = _rank_by_scores(candidate_set, bm25_scores)
    rankings["dense_raw"] = _rank_by_scores(candidate_set, dense_scores)
    rankings["rrf_fusion"] = rrf_fusion(sr_truncated)
    rankings["score_sum"] = score_sum_ranking(graph)
    rankings["greedy_fas_topological"] = topological_ranking(dag)

    # Ensure all rankings cover candidate_set (rrf/score_sum/fas might have different order)
    for name in list(rankings.keys()):
        r = rankings[name]
        missing = set(candidate_set) - set(r)
        if missing:
            rankings[name] = r + sorted(missing)

    results = {}
    for name, ranking in rankings.items():
        results[name] = {
            "ndcg_at_10": ndcg_at_k(ranking, relevance_map, k=10),
            "mrr": mrr(ranking, relevant_ids),
            "recall_at_10": recall_at_k(ranking, relevant_ids, k=10),
            "recall_at_20": recall_at_k(ranking, relevant_ids, k=20),
        }
    # BEW: backward edge weight of ranking on original graph (lower = more consistent)
    bew_bm25 = _backward_edge_weight(graph, rankings["bm25_raw"])
    bew_fas = _backward_edge_weight(graph, rankings["greedy_fas_topological"])
    results["_graph_stats"] = {"bew_bm25_raw": bew_bm25, "bew_fas": bew_fas}
    if return_rankings:
        return results, rankings
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="fiqa")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--max-queries", type=int, default=50)
    parser.add_argument("--mode", default="summed_margin", choices=["majority_vote", "summed_margin", "vote_plus_margin"])
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/validated"))
    parser.add_argument("--examples", type=int, default=0, help="Print N example queries with full rankings")
    args = parser.parse_args()

    cfg = get_config(args.dataset)
    scorer_paths = {
        "bm25": cfg.processed_path / "scores" / "bm25.jsonl",
        "dense": cfg.processed_path / "scores" / "dense.jsonl",
    }
    multi = load_multi_scorer_rankings(scorer_paths)
    if "dense" not in multi:
        print("ERROR: dense scores not found. Run generate_dense_scores.py first.")
        sys.exit(1)

    queries, _, qrels = load_dataset_splits(args.dataset)
    qrels_by_q = {}
    for e in qrels:
        qrels_by_q.setdefault(e.query_id, []).append(e)

    qids = [
        q.query_id
        for q in queries
        if q.query_id in multi["bm25"]
        and q.query_id in multi["dense"]
        and q.query_id in qrels_by_q
    ][: args.max_queries]

    all_rows = []
    for qid in qids:
        sr = {"bm25": multi["bm25"][qid], "dense": multi["dense"][qid]}
        relevance_map = {e.doc_id: e.relevance for e in qrels_by_q[qid]}
        relevant_ids = {e.doc_id for e in qrels_by_q[qid] if e.relevance > 0}
        res = run_query(qid, sr, args.top_k, args.mode, relevance_map, relevant_ids)
        graph_stats = res.pop("_graph_stats", {})
        for method, metrics in res.items():
            row = {
                "dataset": args.dataset,
                "query_id": qid,
                "method": method,
                "ndcg_at_10": round(metrics["ndcg_at_10"], 6),
                "mrr": round(metrics["mrr"], 6),
                "recall_at_10": round(metrics["recall_at_10"], 6),
                "recall_at_20": round(metrics["recall_at_20"], 6),
            }
            if graph_stats:
                row["bew_bm25_raw"] = round(graph_stats["bew_bm25_raw"], 6)
                row["bew_fas"] = round(graph_stats["bew_fas"], 6)
            all_rows.append(row)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_csv = args.output_dir / f"{args.dataset}_validated_k{args.top_k}_{args.mode}.csv"
    if all_rows:
        fieldnames = list(all_rows[0].keys())
        with out_csv.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            w.writerows(all_rows)
        print(f"Wrote {out_csv}")

    # Summary
    from collections import defaultdict
    by_method = defaultdict(list)
    for r in all_rows:
        by_method[r["method"]].append(r)
    print("\n" + "=" * 80)
    print(f"VALIDATED RESULTS: {args.dataset} top_k={args.top_k} mode={args.mode}")
    print("=" * 80)
    print(f"{'Method':<25} {'NDCG@10':>10} {'MRR':>10} {'R@10':>10} {'R@20':>10}")
    print("-" * 80)
    for method in ["bm25_raw", "dense_raw", "rrf_fusion", "score_sum", "greedy_fas_topological"]:
        rows = by_method[method]
        if not rows:
            continue
        n = len(rows)
        ndcg = sum(r["ndcg_at_10"] for r in rows) / n
        mrr_v = sum(r["mrr"] for r in rows) / n
        r10 = sum(r["recall_at_10"] for r in rows) / n
        r20 = sum(r["recall_at_20"] for r in rows) / n
        print(f"{method:<25} {ndcg:>10.4f} {mrr_v:>10.4f} {r10:>10.4f} {r20:>10.4f}")
    # BEW: average per query (one row per method per query; take first row per query)
    if all_rows and "bew_bm25_raw" in all_rows[0]:
        qids_seen: set[str] = set()
        bew_before, bew_after = [], []
        for r in all_rows:
            qid = r["query_id"]
            if qid not in qids_seen:
                qids_seen.add(qid)
                bew_before.append(r["bew_bm25_raw"])
                bew_after.append(r["bew_fas"])
        if bew_before:
            print("-" * 80)
            print(f"BEW: avg before (bm25_raw on graph)={sum(bew_before)/len(bew_before):.4f}, avg after (FAS on graph)={sum(bew_after)/len(bew_after):.4f}")

    # Example queries
    if args.examples > 0:
        print("\n" + "=" * 80)
        print(f"EXAMPLE QUERIES (first {args.examples})")
        print("=" * 80)
        for i, qid in enumerate(qids[: args.examples]):
            sr = {"bm25": multi["bm25"][qid], "dense": multi["dense"][qid]}
            relevance_map = {e.doc_id: e.relevance for e in qrels_by_q[qid]}
            relevant_ids = {e.doc_id for e in qrels_by_q[qid] if e.relevance > 0}
            res, rankings = run_query(qid, sr, args.top_k, args.mode, relevance_map, relevant_ids, return_rankings=True)
            bm25_docs = {d for d, _ in sr["bm25"][: args.top_k]}
            dense_docs = {d for d, _ in sr["dense"][: args.top_k]}
            union_size = len(bm25_docs | dense_docs)
            print(f"\n--- Query {qid} (candidate set size={union_size}) ---")
            print(f"  Relevant: {relevant_ids}")
            for method in ["bm25_raw", "dense_raw", "rrf_fusion", "score_sum", "greedy_fas_topological"]:
                m = res[method]
                rank_list = rankings[method]
                print(f"  {method} NDCG@10={m['ndcg_at_10']:.4f}")
                print(f"    Ranking: {rank_list[:15]}{'...' if len(rank_list) > 15 else ''}")


if __name__ == "__main__":
    main()
