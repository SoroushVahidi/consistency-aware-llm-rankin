"""
run_llm_scidocs_pilot_comparison.py
====================================
LLM pairwise baseline pilot on SciDocs with tournament aggregation
and repaired/unrepaired consistency-repair methods.

Runs deterministic mock LLM pairwise judgments (dry-run mode) on 50
SciDocs queries with top-k=20 candidates, then feeds the *same* pairwise
judgments into multiple aggregation strategies for a fair comparison.

Methods compared
----------------
1. **llm_pairwise_copeland** — Copeland aggregation of LLM pairwise judgments
   (the default PRP baseline aggregation).
2. **bt_from_llm** — Bradley-Terry MLE on LLM pairwise judgments.
3. **win_rate_from_llm** — Win-rate ranking on LLM pairwise judgments.
4. **markov_from_llm** — Markov chain (PageRank-style) on LLM judgments.
5. **tournament_sort_from_llm** — Merge-sort with LLM pairwise comparator.
6. **greedy_fas_topological** — Topological sort on FAS-repaired DAG.
7. **greedy_fas_weighted_balance** — Weighted balance on repaired DAG.
8. **greedy_fas_copeland** — Copeland on repaired DAG.
9. **hybrid_rrf_repaired_copeland_a03** — Hybrid: score prior + repaired Copeland.
10. **hybrid_rrf_unrepaired_copeland_a03** — Hybrid: score prior + unrepaired Copeland.
11. **hybrid_rrf_repaired_balance_a03** — Hybrid: score prior + repaired balance.
12. **hybrid_rrf_unrepaired_balance_a03** — Hybrid: score prior + unrepaired balance.

Usage
-----
::

    source /workspace/.venv/bin/activate
    python scripts/run_llm_scidocs_pilot_comparison.py

"""

from __future__ import annotations

import csv
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import networkx as nx

from consistency_ranker.baseline_ranking import score_sum_scores
from consistency_ranker.cycle_detection import has_cycle
from consistency_ranker.data.query_ids import eligible_query_ids, has_usable_eval_labels
from consistency_ranker.data.unified_loader import load_dataset_splits
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.greedy_fas import greedy_fas
from consistency_ranker.pairwise_prefs import Preference
from rerankers.common import write_pairwise_file
from rerankers.llm_pairwise import PairwiseConfig, collect_all_pairs
from rerankers.tournament_agg import aggregate_preferences

DATASET = "scidocs"
MAX_QUERIES = 50
TOP_K = 20
SEED = 42

OUTPUT_DIR = Path("outputs/llm_scidocs_pilot_comparison")


def _ndcg_at_k(ranking: list[str], rel_map: dict[str, int], k: int) -> float | None:
    if not ranking:
        return None
    k_eff = min(k, len(ranking))
    if k_eff <= 0:
        return None

    def _dcg(items):
        total = 0.0
        for i, doc_id in enumerate(items[:k_eff]):
            rel = rel_map.get(doc_id, 0)
            total += (2.0 ** rel - 1.0) / math.log2(i + 2.0)
        return total

    dcg = _dcg(ranking)
    ideal = sorted(ranking, key=lambda d: rel_map.get(d, 0), reverse=True)
    idcg = _dcg(ideal)
    if idcg <= 0.0:
        return 0.0
    return dcg / idcg


def _map_at_k(ranking: list[str], rel_map: dict[str, int], k: int) -> float | None:
    if not ranking:
        return None
    k_eff = min(k, len(ranking))
    total_relevant = sum(1 for d in ranking if rel_map.get(d, 0) > 0)
    if total_relevant == 0:
        return None
    hit_count = 0
    ap_sum = 0.0
    for i, d in enumerate(ranking[:k_eff], start=1):
        if rel_map.get(d, 0) > 0:
            hit_count += 1
            ap_sum += hit_count / i
    denom = min(total_relevant, k_eff)
    return ap_sum / denom if denom > 0 else None


def _precision_recall_at_k(ranking, rel_map, k):
    if not ranking:
        return None, None
    k_eff = min(k, len(ranking))
    top = ranking[:k_eff]
    hits = sum(1 for d in top if rel_map.get(d, 0) > 0)
    precision = hits / k_eff
    total_relevant = sum(1 for d in ranking if rel_map.get(d, 0) > 0)
    recall = (hits / total_relevant) if total_relevant > 0 else None
    return precision, recall


def _backward_edge_weight(graph, ranking):
    pos = {node: i for i, node in enumerate(ranking)}
    total = 0.0
    for u, v, data in graph.edges(data=True):
        u_pos = pos.get(u)
        v_pos = pos.get(v)
        if u_pos is not None and v_pos is not None and v_pos < u_pos:
            total += data.get("weight", 1.0)
    return total


def _pairwise_inconsistency(graph, ranking):
    pos = {node: i for i, node in enumerate(ranking)}
    count = 0
    for u, v in graph.edges():
        u_pos = pos.get(u)
        v_pos = pos.get(v)
        if u_pos is not None and v_pos is not None and v_pos < u_pos:
            count += 1
    return count


def _reference_ranking_for_candidates(qrels_for_query, candidates):
    rel_map = {}
    for e in qrels_for_query:
        rel_map[e.doc_id] = max(rel_map.get(e.doc_id, e.relevance), e.relevance)
    candidate_list = sorted(set(candidates))
    for doc_id in candidate_list:
        rel_map.setdefault(doc_id, 0)
    candidate_list.sort(key=lambda d: (-rel_map[d], d))
    return candidate_list, rel_map


def _normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    if hi - lo <= 1e-12:
        return {k: 0.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def _copeland_ranking_from_graph(graph: nx.DiGraph) -> list[str]:
    scores = {n: graph.out_degree(n) - graph.in_degree(n) for n in graph.nodes()}
    return sorted(scores, key=lambda n: (-scores[n], n))


def _weighted_balance_ranking(graph: nx.DiGraph) -> list[str]:
    scores: dict[str, float] = {n: 0.0 for n in graph.nodes()}
    for u, v, data in graph.edges(data=True):
        w = data.get("weight", 1.0)
        scores[u] += w
        scores[v] -= w
    return sorted(scores, key=lambda n: (-scores[n], n))


def _hybrid_component_ranking(
    graph: nx.DiGraph,
    prior_scores: dict[str, float],
    component: str,
    alpha: float,
) -> list[str]:
    if not graph.nodes():
        return []
    if component == "balance":
        comp_raw: dict[str, float] = {n: 0.0 for n in graph.nodes()}
        for u, v, data in graph.edges(data=True):
            w = data.get("weight", 1.0)
            comp_raw[u] += w
            comp_raw[v] -= w
    elif component == "copeland":
        comp_raw = {n: float(graph.out_degree(n) - graph.in_degree(n)) for n in graph.nodes()}
    else:
        raise ValueError(f"Unknown component: {component!r}")
    prior_n = _normalize_scores({n: prior_scores.get(n, 0.0) for n in graph.nodes()})
    comp_n = _normalize_scores(comp_raw)
    combo = {n: prior_n.get(n, 0.0) + alpha * comp_n.get(n, 0.0) for n in graph.nodes()}
    return sorted(combo, key=lambda n: (-combo[n], n))


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 70}")
    print("  LLM Pairwise Pilot Comparison — SciDocs")
    print(f"{'=' * 70}")
    print(f"  dataset     : {DATASET}")
    print(f"  max_queries : {MAX_QUERIES}")
    print(f"  top_k       : {TOP_K}")
    print(f"  seed        : {SEED}")
    print("  mode        : dry_run (deterministic mock LLM judgments)")
    print("  caching     : enabled (disk-backed)")
    print(f"  output_dir  : {OUTPUT_DIR}\n")

    # ------------------------------------------------------------------
    # 1. Load dataset
    # ------------------------------------------------------------------
    queries, documents, qrels = load_dataset_splits(DATASET)
    print(f"[1] Loaded {len(queries)} queries, {len(documents)} docs, {len(qrels)} qrels")

    qrels_by_query: dict[str, list] = defaultdict(list)
    for entry in qrels:
        qrels_by_query[entry.query_id].append(entry)

    documents_by_id = {getattr(d, "doc_id", str(i)): d for i, d in enumerate(documents)}
    query_by_id = {q.query_id: q for q in queries}

    # ------------------------------------------------------------------
    # 2. Sample queries
    # ------------------------------------------------------------------
    eligible_qids = eligible_query_ids(qrels)
    rng = random.Random(SEED)
    rng.shuffle(eligible_qids)
    sampled_qids = eligible_qids[:MAX_QUERIES]
    print(f"[2] {len(eligible_qids)} eligible queries; sampled {len(sampled_qids)}")

    # ------------------------------------------------------------------
    # 3. Build candidate pools and collect LLM pairwise judgments
    # ------------------------------------------------------------------
    cache_dir = OUTPUT_DIR / "judgment_cache"
    config = PairwiseConfig(
        dry_run=True,
        seed=SEED,
        cache_dir=cache_dir,
        temperature=0.0,
    )

    all_llm_preferences: dict[str, list[tuple[str, str, float]]] = {}
    queries_pool: list[tuple[str, str, list[tuple[str, str]]]] = []

    print("[3] Collecting LLM pairwise judgments …")
    for idx, qid in enumerate(sampled_qids):
        query = query_by_id.get(qid)
        if query is None:
            continue
        qrels_q = qrels_by_query.get(qid, [])
        if not has_usable_eval_labels(qrels_q):
            continue

        sorted_entries = sorted(qrels_q, key=lambda e: (-e.relevance, e.doc_id))[:TOP_K]
        candidate_pool = []
        for entry in sorted_entries:
            doc = documents_by_id.get(entry.doc_id)
            if doc is None:
                continue
            text = getattr(doc, "text", "") or getattr(doc, "title", "") or str(doc)
            candidate_pool.append((entry.doc_id, text))

        if len(candidate_pool) < 2:
            continue

        query_text = getattr(query, "text", "") or getattr(query, "title", "") or str(query)
        queries_pool.append((qid, query_text, candidate_pool))

        pairs, metadata = collect_all_pairs(qid, query_text, candidate_pool, config)
        all_llm_preferences[qid] = pairs

        if (idx + 1) % 10 == 0:
            print(f"  … {idx + 1}/{len(sampled_qids)} queries")

    print(f"  Collected judgments for {len(queries_pool)} queries")
    total_pairs = sum(len(p) for p in all_llm_preferences.values())
    print(f"  Total pairwise comparisons: {total_pairs}")

    # Save LLM pairwise judgments to disk
    pairwise_file = OUTPUT_DIR / "llm_pairwise_judgments.jsonl"
    write_pairwise_file(all_llm_preferences, pairwise_file)
    print(f"  Saved → {pairwise_file}")

    # ------------------------------------------------------------------
    # 4. Run all methods on the same judgments
    # ------------------------------------------------------------------
    METHOD_LABELS = [
        "llm_pairwise_copeland",
        "bt_from_llm",
        "win_rate_from_llm",
        "markov_from_llm",
        "tournament_sort_from_llm",
        "greedy_fas_topological",
        "greedy_fas_weighted_balance",
        "greedy_fas_copeland",
        "hybrid_rrf_repaired_copeland_a03",
        "hybrid_rrf_unrepaired_copeland_a03",
        "hybrid_rrf_repaired_balance_a03",
        "hybrid_rrf_unrepaired_balance_a03",
    ]

    all_rows: list[dict] = []

    print("\n[4] Running aggregation methods …")
    for q_idx, (qid, query_text, candidate_pool) in enumerate(queries_pool):
        prefs_tuples = all_llm_preferences[qid]
        if not prefs_tuples:
            continue

        qrels_q = qrels_by_query.get(qid, [])
        all_ids = [doc_id for doc_id, _ in candidate_pool]

        # Build graph from LLM pairwise judgments
        graph_prefs = [
            Preference(winner=w, loser=lo, weight=wt) for w, lo, wt in prefs_tuples
        ]
        graph = build_graph(graph_prefs)

        # Greedy FAS repair
        dag, removed_edges = greedy_fas(graph)
        is_cyclic = has_cycle(graph)

        # Score-sum prior from original graph (for hybrid methods)
        prior_scores = score_sum_scores(graph)

        # Reference ranking from qrels
        candidate_nodes = set(graph.nodes())
        ref_ranking, rel_map = _reference_ranking_for_candidates(qrels_q, candidate_nodes)
        candidate_set = set(ref_ranking)

        rankings: dict[str, list[str]] = {}

        # --- Method 1: LLM pairwise Copeland (default PRP aggregation) ---
        wins: dict[str, int] = defaultdict(int)
        losses: dict[str, int] = defaultdict(int)
        for winner, loser, _ in prefs_tuples:
            wins[winner] += 1
            losses[loser] += 1
        copeland_scores = {d: wins.get(d, 0) - losses.get(d, 0) for d in all_ids}
        rankings["llm_pairwise_copeland"] = sorted(
            copeland_scores, key=lambda d: (-copeland_scores[d], d)
        )

        # --- Methods 2-5: Tournament aggregation methods ---
        for method_label, agg_method in [
            ("bt_from_llm", "bradley_terry"),
            ("win_rate_from_llm", "win_rate"),
            ("markov_from_llm", "markov_chain"),
            ("tournament_sort_from_llm", "tournament_sort"),
        ]:
            extra_kwargs = {}
            if agg_method == "tournament_sort":
                extra_kwargs["seed"] = SEED
            result = aggregate_preferences(
                method=agg_method,
                preferences=prefs_tuples,
                all_doc_ids=all_ids,
                **extra_kwargs,
            )
            rankings[method_label] = result.ranked_doc_ids

        # --- Methods 6-8: FAS-repaired graph methods ---
        from consistency_ranker.baseline_ranking import topological_ranking

        rankings["greedy_fas_topological"] = topological_ranking(dag)
        rankings["greedy_fas_weighted_balance"] = _weighted_balance_ranking(dag)
        rankings["greedy_fas_copeland"] = _copeland_ranking_from_graph(dag)

        # --- Methods 9-12: Hybrid repaired/unrepaired ---
        rankings["hybrid_rrf_repaired_copeland_a03"] = _hybrid_component_ranking(
            dag, prior_scores, component="copeland", alpha=0.3,
        )
        rankings["hybrid_rrf_unrepaired_copeland_a03"] = _hybrid_component_ranking(
            graph, prior_scores, component="copeland", alpha=0.3,
        )
        rankings["hybrid_rrf_repaired_balance_a03"] = _hybrid_component_ranking(
            dag, prior_scores, component="balance", alpha=0.3,
        )
        rankings["hybrid_rrf_unrepaired_balance_a03"] = _hybrid_component_ranking(
            graph, prior_scores, component="balance", alpha=0.3,
        )

        # --- Evaluate all methods ---
        for method_name in METHOD_LABELS:
            ranking = rankings[method_name]
            ranking_aligned = [d for d in ranking if d in candidate_set]

            ndcg = _ndcg_at_k(ranking_aligned, rel_map, k=TOP_K)
            map_k = _map_at_k(ranking_aligned, rel_map, k=TOP_K)
            prec_k, rec_k = _precision_recall_at_k(ranking_aligned, rel_map, k=TOP_K)
            bew = _backward_edge_weight(graph, ranking)
            pic = _pairwise_inconsistency(graph, ranking)

            all_rows.append({
                "dataset": DATASET,
                "query_id": qid,
                "method": method_name,
                "n_candidates": len(ranking),
                "is_cyclic": is_cyclic,
                "n_fas_removed": len(removed_edges),
                "ndcg_at_k": round(ndcg, 6) if ndcg is not None else None,
                "map_at_k": round(map_k, 6) if map_k is not None else None,
                "precision_at_k": round(prec_k, 6) if prec_k is not None else None,
                "recall_at_k": round(rec_k, 6) if rec_k is not None else None,
                "backward_edge_weight": round(bew, 6),
                "pairwise_inconsistency": pic,
            })

        if (q_idx + 1) % 10 == 0:
            print(f"  … {q_idx + 1}/{len(queries_pool)} queries evaluated")

    print(f"  Evaluated {len(queries_pool)} queries × {len(METHOD_LABELS)} methods")

    # ------------------------------------------------------------------
    # 5. Write per-query CSV
    # ------------------------------------------------------------------
    pq_path = OUTPUT_DIR / "pilot_per_query.csv"
    if all_rows:
        pq_path.parent.mkdir(parents=True, exist_ok=True)
        with pq_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(all_rows[0].keys()))
            writer.writeheader()
            writer.writerows(all_rows)
    print(f"\n[5] Per-query CSV → {pq_path}")

    # ------------------------------------------------------------------
    # 6. Build summary and comparison table
    # ------------------------------------------------------------------
    by_method: dict[str, list[dict]] = defaultdict(list)
    for r in all_rows:
        by_method[r["method"]].append(r)

    summary_rows = []
    for method in METHOD_LABELS:
        mrows = by_method.get(method, [])
        if not mrows:
            continue

        def _mean(key):
            vals = [r[key] for r in mrows if r.get(key) is not None]
            return sum(vals) / len(vals) if vals else None

        summary_rows.append({
            "method": method,
            "n_queries": len(mrows),
            "ndcg_mean": round(_mean("ndcg_at_k"), 4) if _mean("ndcg_at_k") is not None else None,
            "map_mean": round(_mean("map_at_k"), 4) if _mean("map_at_k") is not None else None,
            "precision_mean": (
                round(_mean("precision_at_k"), 4)
                if _mean("precision_at_k") is not None
                else None
            ),
            "recall_mean": (
                round(_mean("recall_at_k"), 4) if _mean("recall_at_k") is not None else None
            ),
            "bew_mean": round(_mean("backward_edge_weight"), 2),
            "pic_mean": round(_mean("pairwise_inconsistency"), 2),
        })

    summary_path = OUTPUT_DIR / "pilot_summary.csv"
    if summary_rows:
        with summary_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(summary_rows[0].keys()))
            writer.writeheader()
            writer.writerows(summary_rows)
    print(f"[6] Summary CSV → {summary_path}")

    # ------------------------------------------------------------------
    # 7. Generate Markdown comparison table
    # ------------------------------------------------------------------
    md_lines = [
        "# LLM Pairwise Pilot Comparison — SciDocs",
        "",
        "## Experiment Configuration",
        "",
        f"- **Dataset**: {DATASET}",
        f"- **Queries**: {len(queries_pool)} (sampled from {len(eligible_qids)} eligible)",
        f"- **Top-k candidates**: {TOP_K}",
        f"- **Seed**: {SEED}",
        "- **LLM mode**: dry_run (deterministic mock judgments via MD5 hashing)",
        "- **Position debiasing**: disabled",
        f"- **Judgment caching**: disk-backed ({cache_dir})",
        f"- **Total pairwise comparisons**: {total_pairs}",
        "",
        "## Method Categories",
        "",
        "| Category | Methods |",
        "|----------|---------|",
        "| LLM Pairwise Baseline | llm_pairwise_copeland |",
        "| Tournament Aggregation | bt_from_llm, win_rate_from_llm, markov_from_llm, "
        "tournament_sort_from_llm |",
        "| FAS-Repaired Graph | greedy_fas_topological, greedy_fas_weighted_balance, "
        "greedy_fas_copeland |",
        "| Hybrid Repaired | hybrid_rrf_repaired_copeland_a03, "
        "hybrid_rrf_repaired_balance_a03 |",
        "| Hybrid Unrepaired | hybrid_rrf_unrepaired_copeland_a03, "
        "hybrid_rrf_unrepaired_balance_a03 |",
        "",
        "## Pilot Comparison Table",
        "",
        "All methods consume the **same LLM pairwise judgments** (deterministic mock, "
        f"seed={SEED}).",
        "",
        "| Method | nDCG@{k} | MAP@{k} | P@{k} | R@{k} | BEW↓ | PIC↓ |".format(
            k=TOP_K
        ),
        "|--------|---------|---------|-------|-------|------|------|",
    ]

    best_ndcg = max(
        (s["ndcg_mean"] for s in summary_rows if s["ndcg_mean"] is not None), default=0
    )

    for s in summary_rows:
        ndcg_str = f"{s['ndcg_mean']:.4f}" if s["ndcg_mean"] is not None else "—"
        map_str = f"{s['map_mean']:.4f}" if s["map_mean"] is not None else "—"
        prec_str = f"{s['precision_mean']:.4f}" if s["precision_mean"] is not None else "—"
        rec_str = f"{s['recall_mean']:.4f}" if s["recall_mean"] is not None else "—"
        bew_str = f"{s['bew_mean']:.2f}"
        pic_str = f"{s['pic_mean']:.2f}"

        if s["ndcg_mean"] is not None and abs(s["ndcg_mean"] - best_ndcg) < 1e-6:
            ndcg_str = f"**{ndcg_str}**"

        md_lines.append(
            f"| {s['method']} | {ndcg_str} | {map_str} | {prec_str} | "
            f"{rec_str} | {bew_str} | {pic_str} |"
        )

    # Repaired vs unrepaired delta section
    md_lines.extend([
        "",
        "## Repaired vs Unrepaired Deltas",
        "",
        "Positive Δ means repaired is *better* (higher nDCG / lower BEW).",
        "",
        "| Component | nDCG Δ | BEW Δ | PIC Δ |",
        "|-----------|--------|-------|-------|",
    ])

    by_name = {s["method"]: s for s in summary_rows}
    for component in ("copeland", "balance"):
        rep_key = f"hybrid_rrf_repaired_{component}_a03"
        unrep_key = f"hybrid_rrf_unrepaired_{component}_a03"
        rep = by_name.get(rep_key, {})
        unrep = by_name.get(unrep_key, {})
        if rep and unrep:
            d_ndcg = (rep.get("ndcg_mean") or 0) - (unrep.get("ndcg_mean") or 0)
            d_bew = (unrep.get("bew_mean") or 0) - (rep.get("bew_mean") or 0)
            d_pic = (unrep.get("pic_mean") or 0) - (rep.get("pic_mean") or 0)
            md_lines.append(
                f"| {component} | {d_ndcg:+.4f} | {d_bew:+.2f} | {d_pic:+.2f} |"
            )

    # Graph repair statistics
    cyclic_count = sum(
        1 for r in all_rows if r["method"] == "llm_pairwise_copeland" and r["is_cyclic"]
    )
    total_q = sum(1 for r in all_rows if r["method"] == "llm_pairwise_copeland")
    avg_fas = (
        sum(
            r["n_fas_removed"]
            for r in all_rows
            if r["method"] == "llm_pairwise_copeland"
        )
        / total_q
        if total_q
        else 0
    )

    md_lines.extend([
        "",
        "## Graph Repair Statistics",
        "",
        f"- Cyclic preference graphs: {cyclic_count}/{total_q} "
        f"({cyclic_count / total_q * 100:.1f}%)" if total_q else "",
        f"- Average FAS edges removed: {avg_fas:.1f}",
        "",
        "## Files",
        "",
        f"- Per-query results: `{pq_path}`",
        f"- Summary CSV: `{summary_path}`",
        f"- LLM pairwise judgments: `{pairwise_file}`",
        f"- Judgment cache: `{cache_dir}`",
    ])

    md_path = OUTPUT_DIR / "PILOT_COMPARISON.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"[7] Comparison table → {md_path}")

    # Save config
    config_data = {
        "dataset": DATASET,
        "max_queries": MAX_QUERIES,
        "top_k": TOP_K,
        "seed": SEED,
        "dry_run": True,
        "n_queries_processed": len(queries_pool),
        "total_pairwise_comparisons": total_pairs,
        "methods": METHOD_LABELS,
        "cache_dir": str(cache_dir),
    }
    config_path = OUTPUT_DIR / "pilot_config.json"
    with config_path.open("w") as fh:
        json.dump(config_data, fh, indent=2)
    print(f"[8] Config → {config_path}")

    # ------------------------------------------------------------------
    # 8. Print comparison table to stdout
    # ------------------------------------------------------------------
    print(f"\n{'=' * 70}")
    print("  PILOT COMPARISON TABLE — SciDocs")
    print(f"  {len(queries_pool)} queries, top-k={TOP_K}, seed={SEED}, "
          f"dry_run (deterministic mock)")
    print(f"{'=' * 70}")
    print()
    header = (
        f"{'Method':<42} {'nDCG@' + str(TOP_K):>8} {'MAP@' + str(TOP_K):>8} "
        f"{'P@' + str(TOP_K):>8} {'R@' + str(TOP_K):>8} {'BEW':>8} {'PIC':>8}"
    )
    print(header)
    print("-" * len(header))
    for s in summary_rows:
        ndcg_str = f"{s['ndcg_mean']:.4f}" if s["ndcg_mean"] is not None else "—"
        map_str = f"{s['map_mean']:.4f}" if s["map_mean"] is not None else "—"
        prec_str = f"{s['precision_mean']:.4f}" if s["precision_mean"] is not None else "—"
        rec_str = f"{s['recall_mean']:.4f}" if s["recall_mean"] is not None else "—"
        bew_str = f"{s['bew_mean']:.2f}"
        pic_str = f"{s['pic_mean']:.2f}"
        print(
            f"{s['method']:<42} {ndcg_str:>8} {map_str:>8} "
            f"{prec_str:>8} {rec_str:>8} {bew_str:>8} {pic_str:>8}"
        )
    print(f"{'=' * 70}")

    # Print deltas
    print("\nRepaired vs Unrepaired Deltas:")
    print(f"  {'Component':<12} {'ΔNDCG':>8} {'ΔBEW':>8} {'ΔPIC':>8}")
    print(f"  {'-'*12} {'-'*8} {'-'*8} {'-'*8}")
    for component in ("copeland", "balance"):
        rep = by_name.get(f"hybrid_rrf_repaired_{component}_a03", {})
        unrep = by_name.get(f"hybrid_rrf_unrepaired_{component}_a03", {})
        if rep and unrep:
            d_ndcg = (rep.get("ndcg_mean") or 0) - (unrep.get("ndcg_mean") or 0)
            d_bew = (unrep.get("bew_mean") or 0) - (rep.get("bew_mean") or 0)
            d_pic = (unrep.get("pic_mean") or 0) - (rep.get("pic_mean") or 0)
            print(f"  {component:<12} {d_ndcg:>+8.4f} {d_bew:>+8.2f} {d_pic:>+8.2f}")

    print(f"\nGraph stats: {cyclic_count}/{total_q} cyclic, "
          f"avg {avg_fas:.1f} edges removed by FAS")
    print()


if __name__ == "__main__":
    main()
