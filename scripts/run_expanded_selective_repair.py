#!/usr/bin/env python
"""
Expanded selective-repair experiments: more queries, optional third scorer.

Uses validated fair pipeline. Supports 2 or 3 scorers (bm25, dense, cross_encoder).
Evaluates: bm25_raw, dense_raw, [cross_encoder_raw], rrf_fusion, greedy_fas,
selective_repair (BEW thresholds 2, 3, 5).

Usage
-----
::
    python scripts/run_expanded_selective_repair.py --dataset fiqa --max-queries 100
    python scripts/run_expanded_selective_repair.py --dataset scidocs --scorers bm25,dense,cross_encoder --max-queries 100
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import networkx as nx

from consistency_ranker.baseline_ranking import score_sum_ranking, topological_ranking
from consistency_ranker.cycle_detection import has_cycle
from consistency_ranker.data.dataset_registry import get_config
from consistency_ranker.data.unified_loader import (
    load_dataset_splits,
    load_multi_scorer_rankings,
    preferences_from_multiple_score_rankings,
)
from consistency_ranker.evaluation import kendall_tau, ndcg_at_k
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.greedy_fas import greedy_fas
from consistency_ranker.pairwise_prefs import Preference


def rrf_fusion(scorer_rankings: dict[str, list[tuple[str, float]]], k: int = 60) -> list[str]:
    scores: dict[str, float] = {}
    for cands in scorer_rankings.values():
        for r, (doc_id, _) in enumerate(cands):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + r + 1)
    return sorted(scores, key=lambda d: scores[d], reverse=True)


def _rank_by_scores(candidate_set: list[str], score_map: dict[str, float]) -> list[str]:
    return sorted(candidate_set, key=lambda d: score_map.get(d, float("-inf")), reverse=True)


def _backward_edge_weight(graph: nx.DiGraph, ranking: list[str]) -> float:
    pos = {n: i for i, n in enumerate(ranking)}
    total = 0.0
    for u, v, data in graph.edges(data=True):
        u_pos, v_pos = pos.get(u), pos.get(v)
        if u_pos is not None and v_pos is not None and v_pos < u_pos:
            total += data.get("weight", 1.0)
    return total


def run_query_flexible(
    qid: str,
    scorer_rankings: dict[str, list[tuple[str, float]]],
    scorer_names: list[str],
    top_k: int,
    mode: str,
    relevance_map: dict[str, int],
    relevant_ids: set[str],
) -> dict:
    """Run validated pipeline for one query. Candidate set = union of all scorers' top-k."""
    all_docs = set()
    for name in scorer_names:
        all_docs |= {d for d, _ in scorer_rankings[name][:top_k]}
    candidate_set = sorted(all_docs)

    sr_truncated = {n: scorer_rankings[n][:top_k] for n in scorer_names}
    prefs = preferences_from_multiple_score_rankings(qid, sr_truncated, weight_mode=mode)
    graph_prefs = [Preference(p.winner_doc_id, p.loser_doc_id, p.weight) for p in prefs]
    graph = build_graph(graph_prefs)
    dag, _ = greedy_fas(graph)

    rankings = {}
    for name in scorer_names:
        scores = {d: s for d, s in scorer_rankings[name]}
        rankings[f"{name}_raw"] = _rank_by_scores(candidate_set, scores)
    rankings["rrf_fusion"] = rrf_fusion(sr_truncated)
    rankings["greedy_fas_topological"] = topological_ranking(dag)

    for name in list(rankings.keys()):
        r = rankings[name]
        missing = set(candidate_set) - set(r)
        if missing:
            rankings[name] = r + sorted(missing)

    result = {"query_id": qid}
    for name, ranking in rankings.items():
        result[f"ndcg_{name}"] = ndcg_at_k(ranking, relevance_map, k=10)
    bew_rrf = _backward_edge_weight(graph, rankings["rrf_fusion"])
    bew_fas = _backward_edge_weight(graph, rankings["greedy_fas_topological"])
    result["bew_before"] = bew_rrf  # conflict level for selective repair
    result["bew_after"] = bew_fas
    result["cyclic"] = has_cycle(graph)
    result["rankings"] = rankings

    # Disagreement: avg 1-tau across scorer pairs
    if len(scorer_names) >= 2:
        taus = []
        for i, a in enumerate(scorer_names):
            for b in scorer_names[i + 1 :]:
                ra = rankings.get(f"{a}_raw", [])
                rb = rankings.get(f"{b}_raw", [])
                if ra and rb and set(ra) == set(rb):
                    taus.append(kendall_tau(ra, rb))
        result["disagreement"] = 1.0 - (sum(taus) / len(taus)) if taus else 0.0
    else:
        result["disagreement"] = 0.0

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="fiqa")
    parser.add_argument("--scorers", default="bm25,dense", help="Comma-separated: bm25,dense or bm25,dense,cross_encoder")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--max-queries", type=int, default=100)
    parser.add_argument("--mode", default="summed_margin")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/expanded_selective"))
    args = parser.parse_args()

    scorer_names = [s.strip() for s in args.scorers.split(",") if s.strip()]
    if len(scorer_names) < 2:
        print("ERROR: need at least 2 scorers")
        sys.exit(1)

    cfg = get_config(args.dataset)
    scorer_paths = {n: cfg.processed_path / "scores" / f"{n}.jsonl" for n in scorer_names}
    multi = load_multi_scorer_rankings(scorer_paths)
    missing = [n for n in scorer_names if n not in multi]
    if missing:
        print(f"ERROR: missing scorers: {missing}. Generate with scripts first.")
        sys.exit(1)

    queries, _, qrels = load_dataset_splits(args.dataset)
    qrels_by_q = {}
    for e in qrels:
        qrels_by_q.setdefault(e.query_id, []).append(e)

    qids = [
        q.query_id
        for q in queries
        if all(q.query_id in multi[n] for n in scorer_names)
        and q.query_id in qrels_by_q
    ][: args.max_queries]

    per_query: list[dict] = []
    for i, qid in enumerate(qids):
        if (i + 1) % 25 == 0 or i == 0:
            print(f"  Query {i + 1}/{len(qids)}...")
        sr = {n: multi[n][qid] for n in scorer_names}
        relevance_map = {e.doc_id: e.relevance for e in qrels_by_q[qid]}
        relevant_ids = {e.doc_id for e in qrels_by_q[qid] if e.relevance > 0}
        row = run_query_flexible(qid, sr, scorer_names, args.top_k, args.mode, relevance_map, relevant_ids)
        rankings = row.pop("rankings", {})
        per_query.append(row)

    # Selective repair: use BEW percentile thresholds (BEW scale varies by n_scorers/graph)
    bew_vals = sorted(r["bew_before"] for r in per_query)
    p75 = bew_vals[len(bew_vals) * 3 // 4] if bew_vals else 0
    p50 = bew_vals[len(bew_vals) // 2] if bew_vals else 0
    p25 = bew_vals[len(bew_vals) // 4] if bew_vals else 0
    for r in per_query:
        r["ndcg_selective_top25_bew"] = r["ndcg_greedy_fas_topological"] if r["bew_before"] >= p75 else r["ndcg_rrf_fusion"]
        r["ndcg_selective_top50_bew"] = r["ndcg_greedy_fas_topological"] if r["bew_before"] >= p50 else r["ndcg_rrf_fusion"]
        r["ndcg_selective_top75_bew"] = r["ndcg_greedy_fas_topological"] if r["bew_before"] >= p25 else r["ndcg_rrf_fusion"]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    scorers_str = "_".join(scorer_names)
    out_csv = args.output_dir / f"{args.dataset}_k{args.top_k}_{scorers_str}_n{len(qids)}.csv"
    fieldnames = [k for k in per_query[0].keys() if k != "rankings"]
    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(per_query)
    print(f"Wrote {out_csv}")

    n = len(per_query)
    print("\n" + "=" * 80)
    print(f"EXPANDED SELECTIVE REPAIR: {args.dataset} n={n} scorers={scorers_str}")
    print("=" * 80)

    # Overall
    print("\n1. OVERALL RESULTS")
    print("-" * 60)
    methods = [f"ndcg_{n}_raw" for n in scorer_names] + ["ndcg_rrf_fusion", "ndcg_greedy_fas_topological",
                                                         "ndcg_selective_top25_bew", "ndcg_selective_top50_bew", "ndcg_selective_top75_bew"]
    for m in methods:
        if m in per_query[0]:
            avg = sum(r[m] for r in per_query) / n
            print(f"  {m.replace('ndcg_',''):<25} NDCG@10 = {avg:.4f}")

    # High BEW
    sorted_bew = sorted(per_query, key=lambda r: r["bew_before"], reverse=True)
    top25_bew = sorted_bew[: max(1, n // 4)]
    print(f"\n2. HIGH BEW (top 25%, n={len(top25_bew)})")
    print("-" * 60)
    for m in methods:
        if m in per_query[0]:
            avg = sum(r[m] for r in top25_bew) / len(top25_bew)
            print(f"  {m.replace('ndcg_',''):<25} NDCG@10 = {avg:.4f}")

    # High disagreement
    sorted_disc = sorted(per_query, key=lambda r: r["disagreement"], reverse=True)
    top25_disc = sorted_disc[: max(1, n // 4)]
    print(f"\n3. HIGH DISAGREEMENT (top 25%, n={len(top25_disc)})")
    print("-" * 60)
    for m in methods:
        if m in per_query[0]:
            avg = sum(r[m] for r in top25_disc) / len(top25_disc)
            print(f"  {m.replace('ndcg_',''):<25} NDCG@10 = {avg:.4f}")

    # Selective repair summary (percentile-based: FAS for top X% by BEW)
    print("\n4. SELECTIVE REPAIR (RRF base, FAS for top X% by BEW)")
    print("-" * 60)
    for thresh, col, pct in [("top 25% BEW", "ndcg_selective_top25_bew", 25), ("top 50% BEW", "ndcg_selective_top50_bew", 50), ("top 75% BEW", "ndcg_selective_top75_bew", 75)]:
        avg = sum(r[col] for r in per_query) / n
        n_apply = max(1, n * pct // 100)
        print(f"  {thresh:<15} NDCG@10 = {avg:.4f}  (FAS applied to {n_apply} queries)")

    # Markdown table
    print("\n5. CLEAN TABLE (for report)")
    print("-" * 60)
    order = ["bm25_raw", "dense_raw", "cross_encoder_raw", "rrf_fusion", "greedy_fas_topological", "selective_top25_bew", "selective_top50_bew", "selective_top75_bew"]
    actual_cols = [f"ndcg_{o}" for o in order if f"ndcg_{o}" in per_query[0]]
    header = "| Subset | n | " + " | ".join(c.replace("ndcg_", "") for c in actual_cols) + " |"
    print(header)
    print("|" + "-" * (len(header) - 2) + "|")
    for label, rows in [
        ("Overall", per_query),
        ("High BEW", top25_bew),
        ("High disagreement", top25_disc),
    ]:
        m = len(rows)
        vals = [f"{sum(r[c] for r in rows)/m:.3f}" for c in actual_cols]
        print(f"| {label} | {m} | " + " | ".join(vals) + " |")

    summary_path = args.output_dir / f"{args.dataset}_summary_{scorers_str}_n{len(qids)}.csv"
    with summary_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subset", "n"] + [c.replace("ndcg_", "") for c in actual_cols])
        for label, rows in [("overall", per_query), ("high_bew", top25_bew), ("high_disagreement", top25_disc)]:
            m = len(rows)
            w.writerow([label, m] + [round(sum(r[c] for r in rows) / m, 4) for c in actual_cols])
    print(f"\nWrote summary: {summary_path}")


if __name__ == "__main__":
    main()
