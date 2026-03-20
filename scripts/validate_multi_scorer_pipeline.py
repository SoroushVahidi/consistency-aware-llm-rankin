#!/usr/bin/env python
"""
Validation script for multi-scorer pipeline.
Verifies: input rankings, candidate sets, leakage, BEW, and prints 5 example queries.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from consistency_ranker.baseline_ranking import score_sum_ranking, topological_ranking
from consistency_ranker.data.dataset_registry import get_config
from consistency_ranker.data.unified_loader import (
    load_dataset_splits,
    load_multi_scorer_rankings,
    preferences_from_multiple_score_rankings,
)
from consistency_ranker.evaluation import ndcg_at_k
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.greedy_fas import greedy_fas
from consistency_ranker.pairwise_prefs import Preference


def _backward_edge_weight(graph, ranking):
    pos = {n: i for i, n in enumerate(ranking)}
    total = 0.0
    for u, v, data in graph.edges(data=True):
        if pos.get(v, 999) < pos.get(u, 999):
            total += data.get("weight", 1.0)
    return total


def rrf_fusion(scorer_rankings: dict[str, list[tuple[str, float]]], k: int = 60) -> list[str]:
    """Reciprocal Rank Fusion. RRF_score(d) = sum 1/(k + rank_i)."""
    scores: dict[str, float] = {}
    for name, cands in scorer_rankings.items():
        for r, (doc_id, _) in enumerate(cands):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + r + 1)
    return sorted(scores, key=lambda d: scores[d], reverse=True)


def main():
    cfg = get_config("fiqa")
    scorer_paths = {
        "bm25": cfg.processed_path / "scores" / "bm25.jsonl",
        "dense": cfg.processed_path / "scores" / "dense.jsonl",
    }
    multi = load_multi_scorer_rankings(scorer_paths)
    queries, _, qrels = load_dataset_splits("fiqa")
    qrels_by_q = {}
    for e in qrels:
        qrels_by_q.setdefault(e.query_id, []).append(e)

    top_k = 20
    mode = "summed_margin"

    print("=" * 80)
    print("1. WHAT EACH METHOD USES AS INPUT")
    print("=" * 80)
    print("""
- raw_score (current): first scorer's order = BM25 top-k (dict order: bm25,dense)
- dense_raw: NOT in current pipeline - we need to add it
- simple_fusion: NOT in current pipeline - we need RRF/Borda
- score_sum, borda, pagerank: use COMBINED GRAPH (union of bm25[:k] and dense[:k])
- greedy_fas_topological: use DAG after FAS, topological sort

CRITICAL: The graph uses UNION of bm25[:top_k] and dense[:top_k].
So graph has 20-40 nodes. BM25 raw has only 20 nodes.
=> UNFAIR: graph methods have larger candidate pool!
""")

    print("=" * 80)
    print("2. DENSE RERANKING: BM25 CANDIDATES ONLY?")
    print("=" * 80)
    print("""
generate_dense_scores.py with --rerank-from bm25:
- Loads BM25 top-k per query
- Embeds those docs + query
- Reranks them
=> YES: Dense only sees BM25 candidates. No leakage from full corpus.
""")

    print("=" * 80)
    print("3. QRELS IN PREFERENCE CONSTRUCTION?")
    print("=" * 80)
    print("""
For preference_source=multi_scores:
- preferences_from_multiple_score_rankings(query_id, scorer_rankings, weight_mode)
- scorer_rankings = {bm25: [...], dense: [...]} from score files only
=> NO: Qrels are NOT used in preference construction. Only for evaluation.
""")

    print("=" * 80)
    print("4. BEW COMPUTATION")
    print("=" * 80)
    print("""
_backward_edge_weight(graph, ranking):
- For each edge (u,v) in graph: edge means "u preferred over v"
- If ranking places v before u (v_pos < u_pos), edge is BACKWARD
- BEW = sum of weights of backward edges

BEW before = BEW of raw_score (BM25) ranking on original graph
BEW after  = BEW of greedy_fas_topological ranking on original graph

The topological sort is on the DAG (after FAS). So it has 0 BEW on the DAG.
But we evaluate BEW on the ORIGINAL graph. So BEW after can be > 0 (the removed edges).
""")

    # 5 example queries
    print("=" * 80)
    print("5. FIVE EXAMPLE QUERIES")
    print("=" * 80)

    qids = [q.query_id for q in queries[:50] if q.query_id in multi["bm25"] and q.query_id in multi["dense"]][:5]
    for qid in qids:
        sr = {
            "bm25": multi["bm25"][qid][:top_k],
            "dense": multi["dense"][qid][:top_k],
        }
        prefs = preferences_from_multiple_score_rankings(qid, sr, weight_mode=mode)
        graph_prefs = [Preference(p.winner_doc_id, p.loser_doc_id, p.weight) for p in prefs]
        graph = build_graph(graph_prefs)
        dag, _ = greedy_fas(graph)

        bm25_rank = [d for d, _ in sr["bm25"]]
        dense_rank = [d for d, _ in sr["dense"]]
        rrf_rank = rrf_fusion(sr)
        score_sum_rank = score_sum_ranking(graph)
        fas_rank = topological_ranking(dag)

        relevance_map = {e.doc_id: e.relevance for e in qrels_by_q.get(qid, [])}
        rel_docs = [e.doc_id for e in qrels_by_q.get(qid, []) if e.relevance > 0]

        ndcg_bm25 = ndcg_at_k(bm25_rank, relevance_map, k=10)
        ndcg_dense = ndcg_at_k(dense_rank, relevance_map, k=10)
        ndcg_rrf = ndcg_at_k(rrf_rank, relevance_map, k=10)
        ndcg_score_sum = ndcg_at_k(score_sum_rank, relevance_map, k=10)
        ndcg_fas = ndcg_at_k(fas_rank, relevance_map, k=10)

        bew_bm25 = _backward_edge_weight(graph, bm25_rank)
        bew_fas = _backward_edge_weight(graph, fas_rank)

        print(f"\n--- Query {qid} ---")
        print(f"  Candidate set size: bm25={len(bm25_rank)}, dense={len(dense_rank)}, union={len(set(bm25_rank)|set(dense_rank))}")
        print(f"  BM25 top-10:    {bm25_rank[:10]}")
        print(f"  Dense top-10:   {dense_rank[:10]}")
        print(f"  RRF top-10:    {rrf_rank[:10]}")
        print(f"  Score_sum top-10: {score_sum_rank[:10]}")
        print(f"  FAS top-10:    {fas_rank[:10]}")
        print(f"  Relevant docs: {rel_docs[:10]}")
        print(f"  NDCG@10: bm25={ndcg_bm25:.4f} dense={ndcg_dense:.4f} rrf={ndcg_rrf:.4f} score_sum={ndcg_score_sum:.4f} fas={ndcg_fas:.4f}")
        print(f"  BEW: bm25={bew_bm25:.4f} fas={bew_fas:.4f}")


if __name__ == "__main__":
    main()
