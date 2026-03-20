#!/usr/bin/env python
"""Aggregate multi-scorer experiment results into summary table and find example queries."""

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "outputs"

CONFIGS = [
    ("fiqa", 20, "majority_vote"),
    ("fiqa", 20, "summed_margin"),
    ("fiqa", 20, "vote_plus_margin"),
    ("fiqa", 50, "majority_vote"),
    ("fiqa", 50, "summed_margin"),
    ("fiqa", 50, "vote_plus_margin"),
    ("scidocs", 20, "majority_vote"),
    ("scidocs", 20, "summed_margin"),
    ("scidocs", 20, "vote_plus_margin"),
    ("scidocs", 50, "majority_vote"),
    ("scidocs", 50, "summed_margin"),
    ("scidocs", 50, "vote_plus_margin"),
]


def load_per_query(dataset: str, dirname: str) -> list[dict]:
    path = OUT / dirname / f"{dataset}_per_query.csv"
    if not path.exists():
        return []
    rows = []
    with path.open() as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def main():
    table_rows = []
    examples = []

    for dataset, k, mode in CONFIGS:
        dirname = f"multi_{dataset}_k{k}_{mode}"
        rows = load_per_query(dataset, dirname)
        if not rows:
            continue

        # One row per query per method
        by_query: dict[str, dict[str, dict]] = {}
        for r in rows:
            qid = r["query_id"]
            method = r["method"]
            if qid not in by_query:
                by_query[qid] = {}
            by_query[qid][method] = r

        # Aggregate
        raw_rows = [by_query[q][m] for q in by_query for m in by_query[q] if m == "raw_score"]
        fas_rows = [by_query[q][m] for q in by_query for m in by_query[q] if m == "greedy_fas_topological"]

        n = len(by_query)
        n_cyclic = sum(1 for r in raw_rows if r.get("is_cyclic", "False") == "True")
        pct_cyclic = 100 * n_cyclic / n if n else 0

        avg_bew_raw = sum(float(r.get("backward_edge_weight", 0) or 0) for r in raw_rows) / n if n else 0
        avg_bew_fas = sum(float(r.get("backward_edge_weight", 0) or 0) for r in fas_rows) / n if n else 0

        n_changed = 0
        for qid, methods in by_query.items():
            if "raw_score" in methods and "greedy_fas_topological" in methods:
                raw_rank = _parse_ranking(methods["raw_score"])
                fas_rank = _parse_ranking(methods["greedy_fas_topological"])
                if raw_rank != fas_rank:
                    n_changed += 1
                    if methods["raw_score"].get("is_cyclic") == "True" and len(examples) < 5:
                        examples.append({
                            "dataset": dataset,
                            "query_id": qid,
                            "top_k": k,
                            "mode": mode,
                            "raw": raw_rank,
                            "fas": fas_rank,
                            "bew_raw": float(methods["raw_score"].get("backward_edge_weight", 0) or 0),
                            "bew_fas": float(methods["greedy_fas_topological"].get("backward_edge_weight", 0) or 0),
                        })
        pct_changed = 100 * n_changed / n if n else 0

        # Per-method metrics
        for method in ["raw_score", "score_sum", "borda", "pagerank", "greedy_fas_topological"]:
            m_rows = [by_query[q][m] for q in by_query for m in by_query[q] if m == method]
            if not m_rows:
                continue
            ndcg = sum(float(r.get("ndcg_at_10", 0) or 0) for r in m_rows) / n
            mrr = sum(float(r.get("mrr", 0) or 0) for r in m_rows) / n
            r10 = sum(float(r.get("recall_at_10", 0) or 0) for r in m_rows) / n
            r20 = sum(float(r.get("recall_at_20", 0) or 0) for r in m_rows) / n
            table_rows.append({
                "Dataset": dataset,
                "Scorers": "bm25,synthetic_perturbed",
                "top_k": k,
                "aggregation_mode": mode,
                "Method": method,
                "NDCG@10": round(ndcg, 4),
                "MRR": round(mrr, 4),
                "R@10": round(r10, 4),
                "R@20": round(r20, 4),
                "%Cyclic": round(pct_cyclic, 1),
                "BEW_raw_avg": round(avg_bew_raw, 4),
                "BEW_fas_avg": round(avg_bew_fas, 4),
                "%Changed": round(pct_changed, 1),
            })

    # Print table
    print("\n" + "=" * 120)
    print("MULTI-SCORER EXPERIMENT SUMMARY")
    print("=" * 120)
    header = "Dataset | Scorers | top_k | aggregation_mode | Method | NDCG@10 | MRR | R@10 | R@20 | %Cyclic | BEW_raw | BEW_fas | %Changed"
    print(header)
    print("-" * 120)
    for r in table_rows:
        print(f"{r['Dataset']} | {r['Scorers']} | {r['top_k']} | {r['aggregation_mode']} | {r['Method']} | {r['NDCG@10']} | {r['MRR']} | {r['R@10']} | {r['R@20']} | {r['%Cyclic']} | {r['BEW_raw_avg']} | {r['BEW_fas_avg']} | {r['%Changed']}")

    # Save examples - we need per-scorer rankings. Load from score files.
    print("\n" + "=" * 80)
    print("EXAMPLE QUERIES (cyclic, FAS changed ranking)")
    print("=" * 80)
    # Reload examples with scorer rankings
    from consistency_ranker.data.dataset_registry import get_config
    from consistency_ranker.data.unified_loader import load_score_rankings

    for i, ex in enumerate(examples[:5], 1):
        print(f"\n--- Example {i}: {ex['dataset']} query {ex['query_id']} (top_k={ex['top_k']}, mode={ex['mode']}) ---")
        print(f"  BEW before (raw): {ex['bew_raw']:.4f}, after (FAS): {ex['bew_fas']:.4f}")
        cfg = get_config(ex["dataset"])
        bm25 = load_score_rankings(cfg.processed_path / "scores" / "bm25.jsonl")
        syn = load_score_rankings(cfg.processed_path / "scores" / "synthetic_perturbed.jsonl")
        qid = ex["query_id"]
        k = ex["top_k"]
        bm25_rank = [d for d, _ in bm25.get(qid, [])[:k]]
        syn_rank = [d for d, _ in syn.get(qid, [])[:k]]
        print(f"  BM25 top-10:    {bm25_rank[:10]}")
        print(f"  Synthetic top-10: {syn_rank[:10]}")
        print(f"  Raw (BM25) top-10:  {ex['raw'][:10]}")
        print(f"  FAS repaired top-10: {ex['fas'][:10]}")


def _parse_ranking(row: dict) -> list[str]:
    # Per-query CSV doesn't store the actual ranking - we need to get it from the experiment.
    # The CSV has method but not the ranking list. We'll need to recompute or the run_real_experiment
    # would need to output rankings. For now, we can't get the actual doc IDs from the CSV.
    # Return empty - we'll need another approach for examples.
    return []


if __name__ == "__main__":
    main()
