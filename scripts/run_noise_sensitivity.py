"""
run_noise_sensitivity.py
========================
Run controlled noise-sensitivity experiments comparing repaired vs unrepaired
methods and graph aggregation baselines at multiple flip probabilities.

Produces per-noise-level CSV results and a combined summary table.

Usage
-----
::

    python scripts/run_noise_sensitivity.py \\
        --dataset scidocs --max-queries 500 --top-k 20 \\
        --noise-levels 0.0,0.05,0.10,0.15,0.20,0.25,0.30

"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import logging
import math
import random

from consistency_ranker.baseline_ranking import (
    borda_ranking,
    copeland_ranking,
    pagerank_ranking,
    score_sum_ranking,
    topological_ranking,
)
from consistency_ranker.data.query_ids import eligible_query_ids, has_usable_eval_labels
from consistency_ranker.data.unified_loader import load_dataset_splits, preferences_from_qrels
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.greedy_fas import greedy_fas
from consistency_ranker.pairwise_prefs import Preference
from rerankers.tournament_agg import (
    bradley_terry_ranking,
    markov_chain_ranking,
    tournament_sort_ranking,
    win_rate_ranking,
)

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)


def _ndcg_at_k(ranking, rel_map, k):
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
    return dcg / idcg if idcg > 0 else 0.0


def _flip_prefs(prefs, flip_prob, seed, query_id):
    if flip_prob == 0.0:
        return prefs
    rng = random.Random(f"{seed}:{query_id}")
    flipped = []
    for p in prefs:
        if rng.random() < flip_prob:
            flipped.append(Preference(winner=p.loser, loser=p.winner, weight=p.weight))
        else:
            flipped.append(p)
    return flipped


def _ref_ranking_for_candidates(qrels_for_query, candidates):
    rel_map = {}
    for e in qrels_for_query:
        rel_map[e.doc_id] = max(rel_map.get(e.doc_id, e.relevance), e.relevance)
    candidate_list = sorted(set(candidates))
    for doc_id in candidate_list:
        rel_map.setdefault(doc_id, 0)
    candidate_list.sort(key=lambda d: (-rel_map[d], d))
    return candidate_list, rel_map


def _weighted_out_minus_in_ranking(graph):
    scores = {n: 0.0 for n in graph.nodes()}
    for u, v, data in graph.edges(data=True):
        w = data.get("weight", 1.0)
        scores[u] += w
        scores[v] -= w
    return sorted(scores, key=lambda n: (-scores[n], n))


METHODS_TO_RUN = [
    "score_sum",
    "borda",
    "copeland_unrepaired",
    "pagerank",
    "greedy_fas_topological",
    "greedy_fas_weighted_balance",
    "greedy_fas_copeland",
    "bt_aggregation",
    "win_rate_aggregation",
    "markov_aggregation",
    "tournament_sort_aggregation",
]


def run_noise_level(
    dataset, queries_pool, qrels_by_query, flip_prob, top_k, seed
):
    """Run all methods at a single noise level."""
    rows = []

    for qid, _, candidate_pool in queries_pool:
        qrels_q = qrels_by_query.get(qid, [])
        if not qrels_q:
            continue

        schema_prefs = preferences_from_qrels(
            qrels_q, top_k=top_k, seed=seed, weight_scheme="grade_diff"
        )
        base_prefs = [
            Preference(winner=p.winner_doc_id, loser=p.loser_doc_id, weight=p.weight)
            for p in schema_prefs
        ]
        if not base_prefs:
            continue

        prefs = _flip_prefs(base_prefs, flip_prob, seed, qid)
        graph = build_graph(prefs)
        dag, removed = greedy_fas(graph)

        all_ids = [doc_id for doc_id, _ in candidate_pool]
        candidate_set = set(all_ids)
        ref_ranking, rel_map = _ref_ranking_for_candidates(qrels_q, candidate_set)

        pref_tuples = [(p.winner, p.loser, p.weight) for p in prefs]

        rankings = {}
        rankings["score_sum"] = score_sum_ranking(graph)
        rankings["borda"] = borda_ranking(graph)
        rankings["copeland_unrepaired"] = copeland_ranking(graph)
        rankings["pagerank"] = pagerank_ranking(graph)

        try:
            rankings["greedy_fas_topological"] = topological_ranking(dag)
        except Exception:
            rankings["greedy_fas_topological"] = list(dag.nodes())

        rankings["greedy_fas_weighted_balance"] = _weighted_out_minus_in_ranking(dag)

        from consistency_ranker.baseline_ranking import copeland_ranking as bl_copeland
        rankings["greedy_fas_copeland"] = bl_copeland(dag)

        bt_result = bradley_terry_ranking(pref_tuples, all_doc_ids=all_ids)
        rankings["bt_aggregation"] = bt_result.ranked_doc_ids

        wr_result = win_rate_ranking(pref_tuples, all_doc_ids=all_ids)
        rankings["win_rate_aggregation"] = wr_result.ranked_doc_ids

        mc_result = markov_chain_ranking(pref_tuples, all_doc_ids=all_ids)
        rankings["markov_aggregation"] = mc_result.ranked_doc_ids

        ts_result = tournament_sort_ranking(pref_tuples, all_doc_ids=all_ids, seed=seed)
        rankings["tournament_sort_aggregation"] = ts_result.ranked_doc_ids

        for method, ranking in rankings.items():
            aligned = [d for d in ranking if d in candidate_set]
            ndcg = _ndcg_at_k(aligned, rel_map, k=top_k)
            rows.append({
                "dataset": dataset,
                "query_id": qid,
                "flip_prob": flip_prob,
                "method": method,
                "ndcg_at_k": round(ndcg, 6) if ndcg is not None else None,
            })

    return rows


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Noise sensitivity analysis.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--dataset", default="scidocs")
    parser.add_argument("--max-queries", type=int, default=500)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--noise-levels", default="0.00,0.05,0.10,0.15,0.20,0.25,0.30",
        help="Comma-separated flip probabilities.",
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("outputs/noise_sensitivity"),
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    noise_levels = [float(x) for x in args.noise_levels.split(",")]

    output_dir = args.output_dir / args.dataset
    output_dir.mkdir(parents=True, exist_ok=True)

    queries, documents, qrels = load_dataset_splits(args.dataset)

    qrels_by_query = defaultdict(list)
    for e in qrels:
        qrels_by_query[e.query_id].append(e)

    documents_by_id = {getattr(d, "doc_id", str(i)): d for i, d in enumerate(documents)}

    elig = eligible_query_ids(qrels)
    rng = random.Random(args.seed)
    rng.shuffle(elig)
    sampled = elig[:args.max_queries]

    query_by_id = {q.query_id: q for q in queries}
    queries_pool = []
    for qid in sampled:
        query = query_by_id.get(qid)
        if query is None:
            continue
        qrels_q = qrels_by_query.get(qid, [])
        if not has_usable_eval_labels(qrels_q):
            continue
        sorted_entries = sorted(qrels_q, key=lambda e: (-e.relevance, e.doc_id))[:args.top_k]
        pool = []
        for entry in sorted_entries:
            doc = documents_by_id.get(entry.doc_id)
            if doc is None:
                continue
            text = getattr(doc, "text", "") or getattr(doc, "title", "") or str(doc)
            pool.append((entry.doc_id, text))
        if len(pool) >= 2:
            queries_pool.append((qid, getattr(query, "text", "") or str(query), pool))

    print(f"Dataset: {args.dataset}, queries: {len(queries_pool)}, top_k: {args.top_k}")
    print(f"Noise levels: {noise_levels}")

    all_rows = []
    for noise in noise_levels:
        t0 = time.time()
        rows = run_noise_level(
            args.dataset, queries_pool, qrels_by_query, noise, args.top_k, args.seed
        )
        all_rows.extend(rows)
        elapsed = time.time() - t0
        n_q = len(set(r["query_id"] for r in rows))
        print(f"  flip_prob={noise:.2f}: {n_q} queries, {len(rows)} rows, {elapsed:.1f}s")

    pq_path = output_dir / f"{args.dataset}_noise_sensitivity_per_query.csv"
    pq_path.parent.mkdir(parents=True, exist_ok=True)
    with pq_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\nPer-query CSV → {pq_path}")

    summary_rows = []
    grouped = defaultdict(lambda: defaultdict(list))
    for r in all_rows:
        grouped[(r["flip_prob"], r["method"])]["ndcg"].append(r["ndcg_at_k"])

    for (fp, method), vals in sorted(grouped.items()):
        ndcg_vals = [v for v in vals["ndcg"] if v is not None]
        n = len(ndcg_vals)
        mean_ndcg = sum(ndcg_vals) / n if n else None
        summary_rows.append({
            "dataset": args.dataset,
            "flip_prob": fp,
            "method": method,
            "n_queries": n,
            "ndcg_mean": round(mean_ndcg, 6) if mean_ndcg is not None else None,
        })

    summary_path = output_dir / f"{args.dataset}_noise_sensitivity_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"Summary CSV → {summary_path}")

    latex_lines = [
        r"\begin{table}[ht]",
        r"\centering",
        rf"\caption{{Noise sensitivity on {args.dataset.upper()} (nDCG@{args.top_k})}}",
        rf"\label{{tab:noise_sensitivity_{args.dataset}}}",
    ]
    noise_strs = [f"{n:.2f}" for n in noise_levels]
    header = "Method & " + " & ".join(noise_strs) + r" \\"
    latex_lines.append(r"\begin{tabular}{l" + "c" * len(noise_levels) + "}")
    latex_lines.append(r"\toprule")
    latex_lines.append(header)
    latex_lines.append(r"\midrule")

    by_method = defaultdict(dict)
    for r in summary_rows:
        by_method[r["method"]][r["flip_prob"]] = r["ndcg_mean"]

    for method in METHODS_TO_RUN:
        if method not in by_method:
            continue
        vals = []
        for n in noise_levels:
            v = by_method[method].get(n)
            vals.append(f"{v:.4f}" if v is not None else "--")
        m_display = method.replace("_", r"\_")
        latex_lines.append(f"{m_display} & " + " & ".join(vals) + r" \\")

    latex_lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    latex_path = output_dir / f"{args.dataset}_noise_sensitivity.tex"
    latex_path.write_text("\n".join(latex_lines), encoding="utf-8")
    print(f"LaTeX table → {latex_path}")

    md_lines = [f"# Noise Sensitivity — {args.dataset.upper()}\n"]
    md_lines.append("| Method | " + " | ".join(noise_strs) + " |")
    md_lines.append("|--------" + "|------" * len(noise_levels) + "|")
    for method in METHODS_TO_RUN:
        if method not in by_method:
            continue
        vals = []
        for n in noise_levels:
            v = by_method[method].get(n)
            vals.append(f"{v:.4f}" if v is not None else "—")
        md_lines.append(f"| {method} | " + " | ".join(vals) + " |")
    md_lines.append("")
    md_lines.append(f"*{len(queries_pool)} queries, top-k={args.top_k}, seed={args.seed}*")

    md_path = output_dir / f"{args.dataset}_noise_sensitivity.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Markdown summary → {md_path}")

    config = {
        "dataset": args.dataset,
        "max_queries": args.max_queries,
        "top_k": args.top_k,
        "seed": args.seed,
        "noise_levels": noise_levels,
        "n_queries": len(queries_pool),
        "methods": METHODS_TO_RUN,
    }
    config_path = output_dir / f"{args.dataset}_noise_sensitivity_config.json"
    with config_path.open("w") as fh:
        json.dump(config, fh, indent=2)
    print(f"Config → {config_path}")

    print(f"\n{'=' * 70}")
    print(f"  Noise Sensitivity Summary — {args.dataset.upper()}")
    print(f"{'=' * 70}")
    for method in METHODS_TO_RUN:
        if method not in by_method:
            continue
        vals = [by_method[method].get(n) for n in noise_levels]
        val_strs = [f"{v:.4f}" if v is not None else "  --  " for v in vals]
        print(f"  {method:<35} {' '.join(val_strs)}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
