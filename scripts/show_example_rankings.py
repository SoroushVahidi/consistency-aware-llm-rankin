#!/usr/bin/env python
"""Show per-scorer and repaired rankings for example cyclic queries."""

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
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.greedy_fas import greedy_fas
from consistency_ranker.pairwise_prefs import Preference


def main():
    cfg = get_config("fiqa")
    scorer_paths = {
        "bm25": cfg.processed_path / "scores" / "bm25.jsonl",
        "synthetic_perturbed": cfg.processed_path / "scores" / "synthetic_perturbed.jsonl",
    }
    multi = load_multi_scorer_rankings(scorer_paths)
    top_k = 20
    mode = "summed_margin"

    cyclic_qids = ["2376", "4946", "620", "7911", "932"]
    queries, _, qrels = load_dataset_splits("fiqa")
    qrels_by_q = {}
    for e in qrels:
        qrels_by_q.setdefault(e.query_id, []).append(e)

    print("\n" + "=" * 80)
    print("5 EXAMPLE QUERIES: Cyclic multi-scorer graph, FAS changed ranking")
    print("Dataset: fiqa | Scorers: bm25, synthetic_perturbed | top_k=20 | mode=summed_margin")
    print("=" * 80)

    for qid in cyclic_qids:
        if qid not in multi["bm25"] or qid not in multi["synthetic_perturbed"]:
            continue
        scorer_rankings = {
            "bm25": multi["bm25"][qid][:top_k],
            "synthetic_perturbed": multi["synthetic_perturbed"][qid][:top_k],
        }
        prefs = preferences_from_multiple_score_rankings(
            qid, scorer_rankings, weight_mode=mode
        )
        graph_prefs = [Preference(p.winner_doc_id, p.loser_doc_id, p.weight) for p in prefs]
        graph = build_graph(graph_prefs)
        dag, _ = greedy_fas(graph)

        bm25_rank = [d for d, _ in scorer_rankings["bm25"]]
        syn_rank = [d for d, _ in scorer_rankings["synthetic_perturbed"]]
        raw_rank = bm25_rank
        fas_rank = topological_ranking(dag)

        if raw_rank == fas_rank:
            continue

        print(f"\n--- Query {qid} ---")
        print(f"  BM25 top-10:           {bm25_rank[:10]}")
        print(f"  Synthetic top-10:      {syn_rank[:10]}")
        print(f"  Raw (BM25) top-10:    {raw_rank[:10]}")
        print(f"  FAS repaired top-10:   {fas_rank[:10]}")


if __name__ == "__main__":
    main()
