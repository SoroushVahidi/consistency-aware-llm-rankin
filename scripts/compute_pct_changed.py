#!/usr/bin/env python
"""Compute % queries where FAS ranking differs from raw (BM25) for each config."""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from consistency_ranker.baseline_ranking import topological_ranking
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
    import random
    random.seed(42)

    cfg_fiqa = get_config("fiqa")
    cfg_scidocs = get_config("scidocs")
    multi_fiqa = load_multi_scorer_rankings({
        "bm25": cfg_fiqa.processed_path / "scores" / "bm25.jsonl",
        "synthetic_perturbed": cfg_fiqa.processed_path / "scores" / "synthetic_perturbed.jsonl",
    })
    multi_scidocs = load_multi_scorer_rankings({
        "bm25": cfg_scidocs.processed_path / "scores" / "bm25.jsonl",
        "synthetic_perturbed": cfg_scidocs.processed_path / "scores" / "synthetic_perturbed.jsonl",
    })

    _, _, qrels = load_dataset_splits("fiqa")
    qrels_by_q = {}
    for e in qrels:
        qrels_by_q.setdefault(e.query_id, []).append(e)
    fiqa_qids = sorted(q for q in multi_fiqa["bm25"] if q in multi_fiqa["synthetic_perturbed"] and q in qrels_by_q)
    fiqa_qids = fiqa_qids[:50]

    _, _, qrels_s = load_dataset_splits("scidocs")
    qrels_by_q_s = {}
    for e in qrels_s:
        qrels_by_q_s.setdefault(e.query_id, []).append(e)
    scidocs_qids = sorted(q for q in multi_scidocs["bm25"] if q in multi_scidocs["synthetic_perturbed"] and q in qrels_by_q_s)
    scidocs_qids = scidocs_qids[:50]

    results = {}
    for dataset, multi, qids in [("fiqa", multi_fiqa, fiqa_qids), ("scidocs", multi_scidocs, scidocs_qids)]:
        for top_k in [20, 50]:
            for mode in ["majority_vote", "summed_margin", "vote_plus_margin"]:
                n_changed = 0
                for qid in qids:
                    sr = {
                        "bm25": multi["bm25"][qid][:top_k],
                        "synthetic_perturbed": multi["synthetic_perturbed"][qid][:top_k],
                    }
                    prefs = preferences_from_multiple_score_rankings(qid, sr, weight_mode=mode)
                    if not prefs:
                        continue
                    graph_prefs = [Preference(p.winner_doc_id, p.loser_doc_id, p.weight) for p in prefs]
                    graph = build_graph(graph_prefs)
                    dag, _ = greedy_fas(graph)
                    raw = [d for d, _ in sr["bm25"]]
                    fas = topological_ranking(dag)
                    if raw != fas:
                        n_changed += 1
                key = (dataset, top_k, mode)
                results[key] = 100 * n_changed / len(qids) if qids else 0

    print("Dataset | top_k | mode | %Changed")
    for (ds, k, m), pct in results.items():
        print(f"{ds} | {k} | {m} | {pct:.1f}")


if __name__ == "__main__":
    main()
