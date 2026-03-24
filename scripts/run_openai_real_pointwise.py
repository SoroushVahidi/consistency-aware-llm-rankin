"""
run_openai_real_pointwise.py
============================
Bounded real OpenAI pointwise run with explicit reporting artifacts.

Makes REAL OpenAI API calls (no mock/dry-run), writes:
  - config.json
  - pointwise_per_query.csv
  - pointwise_summary.csv
  - POINTWISE_RUN_SUMMARY.md
  - pointwise_scores.jsonl
  - judgment_cache/llm_pointwise_judgments.jsonl
"""

from __future__ import annotations

import csv
import json
import math
import os
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


from consistency_ranker.data.query_ids import eligible_query_ids, has_usable_eval_labels
from consistency_ranker.data.unified_loader import load_dataset_splits
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.pairwise_prefs import Preference
from rerankers.common import write_score_file
from rerankers.llm_pointwise import PointwiseConfig, rerank_query

DATASET = os.environ.get("DATASET", "scidocs")
MAX_QUERIES = int(os.environ.get("MAX_QUERIES", "20"))
TOP_K = int(os.environ.get("TOP_K", "15"))
SEED = 42
MODEL = os.environ.get("MODEL", "gpt-4o-mini")
TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.0"))
OUTPUT_DIR = Path(
    os.environ.get(
        "OUTPUT_DIR",
        f"outputs/openai_{DATASET}_real_pointwise_q{MAX_QUERIES}_k{TOP_K}",
    )
)

GPT4O_MINI_INPUT_COST_PER_M = 0.15
GPT4O_MINI_OUTPUT_COST_PER_M = 0.60
METHOD_LABEL = "llm_pointwise"


def _ndcg_at_k(ranking, rel_map, k):
    if not ranking:
        return None
    k_eff = min(k, len(ranking))
    if k_eff <= 0:
        return None

    def _dcg(items):
        return sum(
            (2.0 ** rel_map.get(d, 0) - 1.0) / math.log2(i + 2.0)
            for i, d in enumerate(items[:k_eff])
        )

    dcg = _dcg(ranking)
    ideal = sorted(ranking, key=lambda d: rel_map.get(d, 0), reverse=True)
    idcg = _dcg(ideal)
    return dcg / idcg if idcg > 0 else 0.0


def _map_at_k(ranking, rel_map, k):
    if not ranking:
        return None
    k_eff = min(k, len(ranking))
    total_relevant = sum(1 for d in ranking if rel_map.get(d, 0) > 0)
    if total_relevant == 0:
        return None
    hit = 0
    ap = 0.0
    for i, d in enumerate(ranking[:k_eff], 1):
        if rel_map.get(d, 0) > 0:
            hit += 1
            ap += hit / i
    denom = min(total_relevant, k_eff)
    return ap / denom if denom > 0 else None


def _precision_recall_at_k(ranking, rel_map, k):
    if not ranking:
        return None, None
    k_eff = min(k, len(ranking))
    top = ranking[:k_eff]
    hits = sum(1 for d in top if rel_map.get(d, 0) > 0)
    prec = hits / k_eff
    total_rel = sum(1 for d in ranking if rel_map.get(d, 0) > 0)
    rec = (hits / total_rel) if total_rel > 0 else None
    return prec, rec


def _backward_edge_weight(graph, ranking):
    pos = {n: i for i, n in enumerate(ranking)}
    return sum(
        d.get("weight", 1.0)
        for u, v, d in graph.edges(data=True)
        if pos.get(u) is not None and pos.get(v) is not None and pos[v] < pos[u]
    )


def _pairwise_inconsistency(graph, ranking):
    pos = {n: i for i, n in enumerate(ranking)}
    return sum(
        1
        for u, v in graph.edges()
        if pos.get(u) is not None and pos.get(v) is not None and pos[v] < pos[u]
    )


def _ref_ranking(qrels_q, candidates):
    rel = {}
    for e in qrels_q:
        rel[e.doc_id] = max(rel.get(e.doc_id, e.relevance), e.relevance)
    cl = sorted(set(candidates))
    for d in cl:
        rel.setdefault(d, 0)
    cl.sort(key=lambda d: (-rel[d], d))
    return cl, rel


def _mean(rows, key):
    vals = [r[key] for r in rows if r.get(key) is not None]
    return sum(vals) / len(vals) if vals else None


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set.")
        sys.exit(1)

    if OUTPUT_DIR.exists():
        print(f"ERROR: Refusing to overwrite existing output directory: {OUTPUT_DIR}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    cache_dir = OUTPUT_DIR / "judgment_cache"

    print(f"\n{'='*70}")
    print(f"  REAL OpenAI Pointwise Run — {DATASET}")
    print(f"{'='*70}")
    print(f"  dataset     : {DATASET}")
    print(f"  max_queries : {MAX_QUERIES}")
    print(f"  top_k       : {TOP_K}")
    print(f"  model       : {MODEL}")
    print("  provider    : openai")
    print("  mode        : REAL API CALLS")
    print(f"  output_dir  : {OUTPUT_DIR}")
    print()

    queries, documents, qrels = load_dataset_splits(DATASET)
    print(f"[1] Loaded {len(queries)} queries, {len(documents)} docs, {len(qrels)} qrels")

    qrels_by_q = defaultdict(list)
    for e in qrels:
        qrels_by_q[e.query_id].append(e)
    docs_by_id = {getattr(d, "doc_id", str(i)): d for i, d in enumerate(documents)}
    query_by_id = {q.query_id: q for q in queries}

    eligible = eligible_query_ids(qrels)
    rng = random.Random(SEED)
    rng.shuffle(eligible)
    sampled = eligible[:MAX_QUERIES]
    print(f"[2] {len(eligible)} eligible; sampled {len(sampled)}")

    pool: list[tuple[str, str, list[tuple[str, str]]]] = []
    for qid in sampled:
        q = query_by_id.get(qid)
        if q is None:
            continue
        qr = qrels_by_q.get(qid, [])
        if not has_usable_eval_labels(qr):
            continue
        entries = sorted(qr, key=lambda e: (-e.relevance, e.doc_id))[:TOP_K]
        cands = []
        for e in entries:
            doc = docs_by_id.get(e.doc_id)
            if doc is None:
                continue
            txt = getattr(doc, "text", "") or getattr(doc, "title", "") or str(doc)
            cands.append((e.doc_id, txt))
        if len(cands) >= 2:
            qt = getattr(q, "text", "") or getattr(q, "title", "") or str(q)
            pool.append((qid, qt, cands))
    print(f"[3] Candidate pools for {len(pool)} queries")

    config = PointwiseConfig(
        model=MODEL,
        dry_run=False,
        seed=SEED,
        cache_dir=cache_dir,
        temperature=TEMPERATURE,
        max_tokens=8,
        strict_parsing=True,
    )

    results = []
    api_error_msg = None
    wall_start = time.time()
    print("\n[4] Collecting REAL OpenAI pointwise judgments …")
    for idx, (qid, qt, cands) in enumerate(pool):
        t0 = time.time()
        try:
            result = rerank_query(qid, qt, cands, config=config)
        except Exception as exc:
            api_error_msg = str(exc)
            print(f"\n  ERROR at query {idx+1} [{qid}]: {exc}")
            print("  Stopping. Will evaluate collected queries.")
            break
        dt = time.time() - t0
        results.append(result)
        api_stats = result.metadata.get("api_stats", {})
        print(
            f"  query {idx+1:>3}/{len(pool)} [{qid[:12]}…] "
            f"{len(cands)} docs {dt:.1f}s "
            f"(API={api_stats.get('api_calls', 0)} cache={api_stats.get('cache_hits', 0)})"
        )
    wall_elapsed = time.time() - wall_start

    if not results:
        print("\nFATAL: No pointwise results collected.")
        sys.exit(1)

    result_by_qid = {r.query_id: r for r in results}
    pool = [(q, t, c) for q, t, c in pool if q in result_by_qid]

    agg_stats = {
        "api_calls": sum(r.metadata.get("api_stats", {}).get("api_calls", 0) for r in results),
        "cache_hits": sum(r.metadata.get("api_stats", {}).get("cache_hits", 0) for r in results),
        "prompt_tokens": sum(
            r.metadata.get("api_stats", {}).get("prompt_tokens", 0) for r in results
        ),
        "completion_tokens": sum(
            r.metadata.get("api_stats", {}).get("completion_tokens", 0) for r in results
        ),
        "total_tokens": sum(
            r.metadata.get("api_stats", {}).get("total_tokens", 0) for r in results
        ),
        "parse_failures": sum(
            r.metadata.get("api_stats", {}).get("parse_failures", 0) for r in results
        ),
    }
    in_cost = agg_stats["prompt_tokens"] / 1e6 * GPT4O_MINI_INPUT_COST_PER_M
    out_cost = agg_stats["completion_tokens"] / 1e6 * GPT4O_MINI_OUTPUT_COST_PER_M
    total_cost = in_cost + out_cost

    print(f"\n  API calls    : {agg_stats['api_calls']}")
    print(f"  Cache hits   : {agg_stats['cache_hits']}")
    print(f"  Prompt tok   : {agg_stats['prompt_tokens']:,}")
    print(f"  Compl tok    : {agg_stats['completion_tokens']:,}")
    print(f"  Total tok    : {agg_stats['total_tokens']:,}")
    print(f"  Parse fails  : {agg_stats['parse_failures']}")
    print(f"  Wall time    : {wall_elapsed:.1f}s")
    print(f"  Est. cost    : ${total_cost:.4f}")

    score_path = OUTPUT_DIR / "pointwise_scores.jsonl"
    write_score_file(results, score_path)
    print(f"\n  Saved → {score_path}")

    rows = []
    for qid, _, cands in pool:
        result = result_by_qid[qid]
        qr = qrels_by_q.get(qid, [])
        ids = [d for d, _ in cands]
        gp = []
        rel_lookup = {}
        for e in qr:
            rel_lookup[e.doc_id] = max(rel_lookup.get(e.doc_id, e.relevance), e.relevance)
        for i, di in enumerate(ids):
            for dj in ids[i + 1:]:
                ri = rel_lookup.get(di, 0)
                rj = rel_lookup.get(dj, 0)
                if ri > rj:
                    gp.append(Preference(winner=di, loser=dj, weight=float(ri - rj)))
                elif rj > ri:
                    gp.append(Preference(winner=dj, loser=di, weight=float(rj - ri)))
        graph = build_graph(gp) if gp else None
        ref, rel = _ref_ranking(qr, ids)
        ra = [d for d in result.ranked_doc_ids if d in set(ref)]
        ndcg = _ndcg_at_k(ra, rel, TOP_K)
        mapk = _map_at_k(ra, rel, TOP_K)
        pk, rk = _precision_recall_at_k(ra, rel, TOP_K)
        bew = _backward_edge_weight(graph, result.ranked_doc_ids) if graph is not None else None
        pic = _pairwise_inconsistency(graph, result.ranked_doc_ids) if graph is not None else None
        rows.append({
            "dataset": DATASET,
            "query_id": qid,
            "method": METHOD_LABEL,
            "n_candidates": len(result.ranked_doc_ids),
            "ndcg_at_k": round(ndcg, 6) if ndcg is not None else None,
            "map_at_k": round(mapk, 6) if mapk is not None else None,
            "precision_at_k": round(pk, 6) if pk is not None else None,
            "recall_at_k": round(rk, 6) if rk is not None else None,
            "backward_edge_weight": round(bew, 6) if bew is not None else None,
            "pairwise_inconsistency": pic,
            "api_calls": result.metadata.get("api_stats", {}).get("api_calls", 0),
            "cache_hits": result.metadata.get("api_stats", {}).get("cache_hits", 0),
            "prompt_tokens": result.metadata.get("api_stats", {}).get("prompt_tokens", 0),
            "completion_tokens": result.metadata.get("api_stats", {}).get("completion_tokens", 0),
            "total_tokens": result.metadata.get("api_stats", {}).get("total_tokens", 0),
            "parse_failures": result.metadata.get("api_stats", {}).get("parse_failures", 0),
        })

    pq = OUTPUT_DIR / "pointwise_per_query.csv"
    with pq.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"[5] Per-query CSV → {pq}")

    summary_row = {
        "method": METHOD_LABEL,
        "n_queries": len(rows),
        "ndcg_mean": round(_mean(rows, "ndcg_at_k"), 4) if _mean(rows, "ndcg_at_k") is not None else None,
        "map_mean": round(_mean(rows, "map_at_k"), 4) if _mean(rows, "map_at_k") is not None else None,
        "precision_mean": (
            round(_mean(rows, "precision_at_k"), 4)
            if _mean(rows, "precision_at_k") is not None
            else None
        ),
        "recall_mean": (
            round(_mean(rows, "recall_at_k"), 4)
            if _mean(rows, "recall_at_k") is not None
            else None
        ),
        "bew_mean": round(_mean(rows, "backward_edge_weight"), 2)
        if _mean(rows, "backward_edge_weight") is not None
        else None,
        "pic_mean": round(_mean(rows, "pairwise_inconsistency"), 2)
        if _mean(rows, "pairwise_inconsistency") is not None
        else None,
    }
    sp = OUTPUT_DIR / "pointwise_summary.csv"
    with sp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_row.keys()))
        w.writeheader()
        w.writerow(summary_row)
    print(f"[6] Summary CSV → {sp}")

    partial = api_error_msg is not None
    cfg = {
        "label": f"REAL OPENAI POINTWISE RUN ({len(results)} queries{', PARTIAL' if partial else ''}) — NOT mock",
        "dataset": DATASET,
        "baseline": METHOD_LABEL,
        "provider": "openai",
        "max_queries": MAX_QUERIES,
        "top_k": TOP_K,
        "seed": SEED,
        "model": MODEL,
        "temperature": TEMPERATURE,
        "dry_run": False,
        "n_queries_processed": len(results),
        "partial_run": partial,
        "api_error": api_error_msg,
        "cache_dir": str(cache_dir),
        "api_stats": agg_stats,
        "wall_time_s": round(wall_elapsed, 1),
        "cost_estimate_usd": round(total_cost, 4),
        "score_file": str(score_path),
        "per_query_csv": str(pq),
        "summary_csv": str(sp),
    }
    cp = OUTPUT_DIR / "config.json"
    with cp.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    print(f"[7] Config → {cp}")

    md = [
        f"# Real OpenAI Pointwise Run — {DATASET}",
        "",
        "**This is a REAL OpenAI run — all scores from live gpt-4o-mini API calls.**",
        "",
        "## Configuration",
        "",
        "| Param | Value |",
        "|-------|-------|",
        f"| Dataset | {DATASET} |",
        f"| Queries | {len(results)} |",
        f"| top_k | {TOP_K} |",
        f"| Model | {MODEL} |",
        "| Provider | openai |",
        "| Mode | **REAL API CALLS** |",
        f"| Temperature | {TEMPERATURE} |",
        "",
        "## API Usage",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| API calls | {agg_stats['api_calls']} |",
        f"| Cache hits | {agg_stats['cache_hits']} |",
        f"| Prompt tokens | {agg_stats['prompt_tokens']:,} |",
        f"| Completion tokens | {agg_stats['completion_tokens']:,} |",
        f"| Total tokens | {agg_stats['total_tokens']:,} |",
        f"| Parse failures | {agg_stats['parse_failures']} |",
        f"| Wall time | {wall_elapsed:.1f}s |",
        f"| Est. cost | ${total_cost:.4f} |",
        "",
        "## Results",
        "",
        f"| Method | nDCG@{TOP_K} | MAP@{TOP_K} | BEW↓ | PIC↓ |",
        "|--------|---------|---------|------|------|",
        (
            f"| {METHOD_LABEL} | {summary_row['ndcg_mean']:.4f} | {summary_row['map_mean']:.4f} | "
            f"{summary_row['bew_mean'] if summary_row['bew_mean'] is not None else '—'} | "
            f"{summary_row['pic_mean'] if summary_row['pic_mean'] is not None else '—'} |"
        ),
        "",
    ]
    if partial:
        md += [f"**Partial run** — error: `{api_error_msg}`", ""]
    md += [
        "## Files",
        "",
        f"- Per-query results: `{pq}`",
        f"- Summary CSV: `{sp}`",
        f"- Score file: `{score_path}`",
        f"- Judgment cache: `{cache_dir}`",
        "",
        "---",
        "*Generated from REAL OpenAI API calls, not mock/synthetic.*",
    ]
    mp = OUTPUT_DIR / "POINTWISE_RUN_SUMMARY.md"
    mp.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"[8] Summary → {mp}")


if __name__ == "__main__":
    main()
