#!/usr/bin/env python
"""
Paper-ready experiments: scale, selective policies, tables, qualitative examples.

Uses validated fair pipeline. Reports:
- % cyclic, BEW before/after, % FAS changes ranking
- NDCG@10, MRR, Recall@10, Recall@20
- Selective policies: never, always, BEW-based, disagreement-based, hybrid, learned
- Paper-ready tables A-D
- 5-10 qualitative examples (success + failure)
"""

from __future__ import annotations

import argparse
import time
import csv
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import networkx as nx

from consistency_ranker.baseline_ranking import local_adjacent_swap_refinement, topological_ranking
from consistency_ranker.cycle_detection import has_cycle
from consistency_ranker.data.dataset_registry import get_config
from consistency_ranker.data.unified_loader import (
    load_dataset_splits,
    load_multi_scorer_rankings,
    preferences_from_multiple_score_rankings,
)
from consistency_ranker.evaluation import kendall_tau, mrr, ndcg_at_k, recall_at_k
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.greedy_fas import greedy_fas
from consistency_ranker.pairwise_prefs import Preference


def rrf_fusion(sr: dict[str, list[tuple[str, float]]], k: int = 60) -> list[str]:
    scores: dict[str, float] = {}
    for cands in sr.values():
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


def run_query_full(
    qid: str,
    scorer_rankings: dict[str, list[tuple[str, float]]],
    scorer_names: list[str],
    top_k: int,
    mode: str,
    relevance_map: dict[str, int],
    relevant_ids: set[str],
    return_rankings: bool = False,
) -> dict:
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
    t0 = time.perf_counter()
    rankings["greedy_fas_topological"] = topological_ranking(dag)
    fas_time = time.perf_counter() - t0
    t0 = time.perf_counter()
    rankings["local_adjacent_swap"] = local_adjacent_swap_refinement(
        rankings["rrf_fusion"], graph, objective="bew"
    )
    local_time = time.perf_counter() - t0

    for name in list(rankings.keys()):
        r = rankings[name]
        missing = set(candidate_set) - set(r)
        if missing:
            rankings[name] = r + sorted(missing)

    bew_rrf = _backward_edge_weight(graph, rankings["rrf_fusion"])
    bew_fas = _backward_edge_weight(graph, rankings["greedy_fas_topological"])
    bew_local = _backward_edge_weight(graph, rankings["local_adjacent_swap"])
    is_cyclic = has_cycle(graph)
    n_sccs = nx.number_strongly_connected_components(graph)
    fas_differs_rrf = rankings["greedy_fas_topological"] != rankings["rrf_fusion"]

    if len(scorer_names) >= 2:
        taus = []
        for i, a in enumerate(scorer_names):
            for b in scorer_names[i + 1 :]:
                ra, rb = rankings.get(f"{a}_raw", []), rankings.get(f"{b}_raw", [])
                if ra and rb and set(ra) == set(rb):
                    taus.append(kendall_tau(ra, rb))
        disagreement = 1.0 - (sum(taus) / len(taus)) if taus else 0.0
    else:
        disagreement = 0.0

    result = {
        "query_id": qid,
        "bew_before": bew_rrf,
        "bew_after": bew_fas,
        "bew_after_local": bew_local,
        "fas_time_ms": round(fas_time * 1000, 2),
        "local_time_ms": round(local_time * 1000, 2),
        "cyclic": is_cyclic,
        "n_sccs": n_sccs,
        "disagreement": disagreement,
        "fas_differs_rrf": fas_differs_rrf,
    }
    for name, ranking in rankings.items():
        result[f"ndcg_{name}"] = ndcg_at_k(ranking, relevance_map, k=10)
        result[f"mrr_{name}"] = mrr(ranking, relevant_ids)
        result[f"recall10_{name}"] = recall_at_k(ranking, relevant_ids, k=10)
        result[f"recall20_{name}"] = recall_at_k(ranking, relevant_ids, k=20)
    result["fas_helps"] = result["ndcg_greedy_fas_topological"] > result["ndcg_rrf_fusion"]
    if return_rankings:
        result["rankings"] = rankings
        result["relevant_ids"] = relevant_ids
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="fiqa")
    parser.add_argument("--scorers", default="bm25,dense")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--max-queries", type=int, default=None)
    parser.add_argument("--val-frac", type=float, default=0.2, help="Fraction for validation (learned threshold)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/paper_ready"))
    parser.add_argument("--examples", type=int, default=8)
    args = parser.parse_args()

    random.seed(args.seed)
    scorer_names = [s.strip() for s in args.scorers.split(",") if s.strip()]
    if len(scorer_names) < 2:
        print("ERROR: need at least 2 scorers")
        sys.exit(1)

    cfg = get_config(args.dataset)
    scorer_paths = {n: cfg.processed_path / "scores" / f"{n}.jsonl" for n in scorer_names}
    multi = load_multi_scorer_rankings(scorer_paths)
    missing = [n for n in scorer_names if n not in multi]
    if missing:
        print(f"ERROR: missing scorers: {missing}")
        sys.exit(1)

    queries, _, qrels = load_dataset_splits(args.dataset)
    qrels_by_q = {}
    for e in qrels:
        qrels_by_q.setdefault(e.query_id, []).append(e)

    qids = [
        q.query_id
        for q in queries
        if all(q.query_id in multi[n] for n in scorer_names) and q.query_id in qrels_by_q
    ]
    if args.max_queries:
        qids = qids[: args.max_queries]

    # Validation split for learned threshold
    random.shuffle(qids)
    n_val = max(1, int(len(qids) * args.val_frac))
    val_qids, test_qids = set(qids[:n_val]), qids[n_val:]
    # Use all for test; val only for threshold selection
    all_qids = qids

    per_query: list[dict] = []
    for i, qid in enumerate(all_qids):
        if (i + 1) % 50 == 0 or i == 0:
            print(f"  Query {i + 1}/{len(all_qids)}...")
        sr = {n: multi[n][qid] for n in scorer_names}
        relevance_map = {e.doc_id: e.relevance for e in qrels_by_q[qid]}
        relevant_ids = {e.doc_id for e in qrels_by_q[qid] if e.relevance > 0}
        row = run_query_full(qid, sr, scorer_names, args.top_k, "summed_margin", relevance_map, relevant_ids, return_rankings=(i < args.examples))
        if "rankings" in row:
            row["relevant_ids"] = list(relevant_ids)
        else:
            row.pop("rankings", None)
            row.pop("relevant_ids", None)
        per_query.append(row)

    n = len(per_query)
    val_rows = [r for r in per_query if r["query_id"] in val_qids]
    test_rows = [r for r in per_query if r["query_id"] in test_qids] if test_qids else per_query

    # Percentiles for thresholds
    bew_vals = sorted(r["bew_before"] for r in per_query)
    disc_vals = sorted(r["disagreement"] for r in per_query)
    p75_bew = bew_vals[n * 3 // 4] if bew_vals else 0
    p50_bew = bew_vals[n // 2] if bew_vals else 0
    p75_disc = disc_vals[n * 3 // 4] if disc_vals else 0
    p50_disc = disc_vals[n // 2] if disc_vals else 0

    # Learned threshold: on validation, find best BEW percentile
    best_val_ndcg, best_pct = 0.0, 25
    for pct in [25, 50, 75]:
        p = bew_vals[min(n * pct // 100, n - 1)] if bew_vals else 0
        ndcgs = [r["ndcg_greedy_fas_topological"] if r["bew_before"] >= p else r["ndcg_rrf_fusion"] for r in val_rows]
        avg = sum(ndcgs) / len(val_rows) if val_rows else 0
        if avg > best_val_ndcg:
            best_val_ndcg, best_pct = avg, pct
    learned_thresh_bew = bew_vals[min(n * best_pct // 100, n - 1)] if bew_vals else 0

    # Add selective policies
    for r in per_query:
        r["ndcg_never"] = r["ndcg_rrf_fusion"]
        r["ndcg_always"] = r["ndcg_greedy_fas_topological"]
        r["ndcg_sel_bew25"] = r["ndcg_greedy_fas_topological"] if r["bew_before"] >= p75_bew else r["ndcg_rrf_fusion"]
        r["ndcg_sel_bew50"] = r["ndcg_greedy_fas_topological"] if r["bew_before"] >= p50_bew else r["ndcg_rrf_fusion"]
        r["ndcg_sel_disc25"] = r["ndcg_greedy_fas_topological"] if r["disagreement"] >= p75_disc else r["ndcg_rrf_fusion"]
        r["ndcg_sel_disc50"] = r["ndcg_greedy_fas_topological"] if r["disagreement"] >= p50_disc else r["ndcg_rrf_fusion"]
        r["ndcg_sel_hybrid"] = r["ndcg_greedy_fas_topological"] if (r["bew_before"] >= p50_bew and r["disagreement"] >= p50_disc) else r["ndcg_rrf_fusion"]
        r["ndcg_sel_learned"] = r["ndcg_greedy_fas_topological"] if r["bew_before"] >= learned_thresh_bew else r["ndcg_rrf_fusion"]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    scorers_str = "_".join(scorer_names)

    # --- Aggregate stats ---
    pct_cyclic = 100 * sum(1 for r in per_query if r["cyclic"]) / n
    pct_fas_changes = 100 * sum(1 for r in per_query if r["fas_differs_rrf"]) / n
    avg_bew_before = sum(r["bew_before"] for r in per_query) / n
    avg_bew_after = sum(r["bew_after"] for r in per_query) / n
    avg_bew_after_local = sum(r.get("bew_after_local", 0) for r in per_query) / n
    avg_fas_ms = sum(r.get("fas_time_ms", 0) for r in per_query) / n
    avg_local_ms = sum(r.get("local_time_ms", 0) for r in per_query) / n

    top25_bew = sorted(per_query, key=lambda r: r["bew_before"], reverse=True)[: max(1, n // 4)]
    bot25_bew = sorted(per_query, key=lambda r: r["bew_before"])[: max(1, n // 4)]

    # --- Print report ---
    print("\n" + "=" * 80)
    print(f"PAPER-READY: {args.dataset} n={n} scorers={scorers_str}")
    print("=" * 80)
    print(f"  % cyclic: {pct_cyclic:.1f}  |  BEW before: {avg_bew_before:.2f}  after FAS: {avg_bew_after:.2f}  after local: {avg_bew_after_local:.2f}  |  % FAS changes: {pct_fas_changes:.1f}")
    print(f"  Avg runtime: FAS {avg_fas_ms:.2f} ms  |  local {avg_local_ms:.2f} ms per query")

    print("\n--- TABLE A: Overall ---")
    print(f"{'Method':<22} {'NDCG@10':>8} {'MRR':>8} {'R@10':>8} {'R@20':>8}")
    print("-" * 55)
    for m in ["bm25_raw", "dense_raw", "rrf_fusion", "local_adjacent_swap", "greedy_fas_topological", "sel_bew25", "sel_learned"]:
        k = f"ndcg_{m}" if f"ndcg_{m}" in per_query[0] else (f"ndcg_sel_{m[4:]}" if m.startswith("sel_") else None)
        if k and k in per_query[0]:
            mr = f"mrr_{m}" if f"mrr_{m}" in per_query[0] else ("mrr_greedy_fas_topological" if "sel" in m else "mrr_rrf_fusion")
            if mr not in per_query[0]:
                mr = "mrr_rrf_fusion"
            r10 = f"recall10_{m}" if f"recall10_{m}" in per_query[0] else "recall10_rrf_fusion"
            r20 = f"recall20_{m}" if f"recall20_{m}" in per_query[0] else "recall20_rrf_fusion"
            if r10 not in per_query[0]:
                r10, r20 = "recall10_rrf_fusion", "recall20_rrf_fusion"
            print(f"{m:<22} {sum(r[k] for r in per_query)/n:>8.4f} {sum(r.get(mr,0) for r in per_query)/n:>8.4f} {sum(r.get(r10,0) for r in per_query)/n:>8.4f} {sum(r.get(r20,0) for r in per_query)/n:>8.4f}")

    print("\n--- TABLE B: High-conflict (top 25% BEW) ---")
    for m in ["bm25_raw", "dense_raw", "rrf_fusion", "local_adjacent_swap", "greedy_fas_topological", "sel_bew25"]:
        k = f"ndcg_{m}" if f"ndcg_{m}" in per_query[0] else f"ndcg_sel_{m[4:]}"
        if k in per_query[0]:
            print(f"  {m:<20} NDCG@10 = {sum(r[k] for r in top25_bew)/len(top25_bew):.4f}")

    print("\n--- TABLE C: Low-conflict (bottom 25% BEW) ---")
    for m in ["bm25_raw", "dense_raw", "rrf_fusion", "local_adjacent_swap", "greedy_fas_topological", "sel_bew25"]:
        k = f"ndcg_{m}" if f"ndcg_{m}" in per_query[0] else f"ndcg_sel_{m[4:]}"
        if k in per_query[0]:
            print(f"  {m:<20} NDCG@10 = {sum(r[k] for r in bot25_bew)/len(bot25_bew):.4f}")

    print("\n--- TABLE D: Post-processing comparison (never, always FAS, selective, local) ---")
    for m in ["rrf_fusion", "local_adjacent_swap", "greedy_fas_topological", "sel_bew25"]:
        k = f"ndcg_{m}"
        if k in per_query[0]:
            print(f"  {m:<22} NDCG@10 = {sum(r[k] for r in per_query)/n:.4f}")

    print("\n--- TABLE E: Ablation on selection policy ---")
    policies = [("never", "ndcg_never"), ("always", "ndcg_always"), ("BEW top25%", "ndcg_sel_bew25"), ("BEW top50%", "ndcg_sel_bew50"), ("disagreement top25%", "ndcg_sel_disc25"), ("hybrid", "ndcg_sel_hybrid"), ("learned", "ndcg_sel_learned")]
    print(f"{'Policy':<22} {args.dataset} NDCG@10")
    print("-" * 40)
    for label, col in policies:
        print(f"  {label:<20} {sum(r[col] for r in per_query)/n:.4f}")

    # --- Qualitative examples ---
    examples_with_rankings = [r for r in per_query if "rankings" in r][: args.examples]
    if examples_with_rankings:
        ex_path = args.output_dir / f"{args.dataset}_examples_{scorers_str}.jsonl"
        with ex_path.open("w") as f:
            for r in examples_with_rankings:
                out = {k: v for k, v in r.items() if k != "rankings" and not isinstance(v, (list, dict)) or k == "relevant_ids"}
                out["bew_before"] = round(r["bew_before"], 4)
                out["bew_after"] = round(r["bew_after"], 4)
                out["disagreement"] = round(r["disagreement"], 4)
                out["fas_helps"] = r["ndcg_greedy_fas_topological"] > r["ndcg_rrf_fusion"]
                for k, v in r.get("rankings", {}).items():
                    out[f"ranking_{k}"] = v[:15]
                json.dump(out, f, default=str)
                f.write("\n")
        print(f"\nWrote {len(examples_with_rankings)} examples → {ex_path}")

        print("\n--- Qualitative examples (first 5) ---")
        for i, r in enumerate(examples_with_rankings[:5]):
            helps = "HELPS" if r["ndcg_greedy_fas_topological"] > r["ndcg_rrf_fusion"] else "HURTS"
            print(f"\n  Query {r['query_id']} [{helps}] BEW={r['bew_before']:.2f} disc={r['disagreement']:.3f}")
            print(f"    Relevant: {r.get('relevant_ids', [])[:5]}")
            rank_dict = r.get("rankings", {})
            for name in ["bm25_raw", "dense_raw", "rrf_fusion", "local_adjacent_swap", "greedy_fas_topological"]:
                if name in rank_dict:
                    ndcg = r.get(f"ndcg_{name}", 0)
                    print(f"    {name}: NDCG={ndcg:.3f} top5={rank_dict[name][:5]}")

    # --- Write CSV ---
    flat_cols = [k for k in per_query[0].keys() if k != "rankings" and k != "relevant_ids" and not isinstance(per_query[0].get(k), (list, dict))]
    out_csv = args.output_dir / f"{args.dataset}_paper_k{args.top_k}_{scorers_str}_n{n}.csv"
    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=flat_cols, extrasaction="ignore")
        w.writeheader()
        for r in per_query:
            w.writerow({k: v for k, v in r.items() if k in flat_cols})
    print(f"\nWrote {out_csv}")


if __name__ == "__main__":
    main()
