"""
run_openai_real_listwise.py
===========================
Real OpenAI listwise run — configurable dataset, queries, and top_k.

Makes REAL OpenAI API calls (no mock/dry-run). Rankings are cached to disk
for resumability. Evaluates the listwise reranker on the selected queries and
writes a compact evidence package for audit purposes.
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
from rerankers.llm_listwise import ListwiseConfig, rerank_query

DATASET = os.environ.get("DATASET", "scidocs")
MAX_QUERIES = int(os.environ.get("MAX_QUERIES", "20"))
TOP_K = int(os.environ.get("TOP_K", "15"))
SEED = 42
MODEL = os.environ.get("MODEL", "gpt-4o-mini")
TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.0"))
WINDOW_SIZE = int(os.environ.get("WINDOW_SIZE", str(TOP_K)))
STEP_SIZE = int(os.environ.get("STEP_SIZE", str(max(1, TOP_K // 2))))
NUM_PASSES = int(os.environ.get("NUM_PASSES", "1"))
OUTPUT_DIR = Path(
    os.environ.get(
        "OUTPUT_DIR",
        f"outputs/openai_{DATASET}_real_listwise_q{MAX_QUERIES}_k{TOP_K}",
    )
)

GPT4O_MINI_INPUT_COST_PER_M = 0.15
GPT4O_MINI_OUTPUT_COST_PER_M = 0.60


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


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set.")
        sys.exit(1)
    if OUTPUT_DIR.exists():
        print(f"ERROR: Output directory already exists: {OUTPUT_DIR}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    cache_dir = OUTPUT_DIR / "judgment_cache"

    print(f"\n{'=' * 70}")
    print(f"  REAL OpenAI Listwise Run — {DATASET}")
    print(f"{'=' * 70}")
    print(f"  dataset     : {DATASET}")
    print(f"  max_queries : {MAX_QUERIES}")
    print(f"  top_k       : {TOP_K}")
    print(f"  model       : {MODEL}")
    print("  provider    : openai")
    print("  mode        : REAL API CALLS")
    print(f"  temperature : {TEMPERATURE}")
    print(f"  window_size : {WINDOW_SIZE}")
    print(f"  step_size   : {STEP_SIZE}")
    print(f"  num_passes  : {NUM_PASSES}")
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

    config = ListwiseConfig(
        model=MODEL,
        temperature=TEMPERATURE,
        max_tokens=512,
        window_size=WINDOW_SIZE,
        step_size=STEP_SIZE,
        num_passes=NUM_PASSES,
        cache_dir=cache_dir,
        dry_run=False,
        seed=SEED,
        strict_parsing=True,
    )

    rows: list[dict] = []
    completed = 0
    api_error_msg = None
    parse_issue_count = 0
    parse_issue_examples: list[str] = []
    wall_start = time.time()
    print("\n[4] Running REAL OpenAI listwise reranking …")
    for idx, (qid, qt, cands) in enumerate(pool):
        t0 = time.time()
        try:
            result = rerank_query(qid, qt, cands, config=config)
        except Exception as exc:
            api_error_msg = str(exc)
            print(f"\n  ERROR at query {idx + 1} [{qid}]: {exc}")
            print("  Stopping. Will summarize collected queries.")
            break

        dt = time.time() - t0
        completed += 1
        meta = result.metadata
        stats = meta.get("api_stats", {})
        parse_issue_count += int(stats.get("parse_failures", 0))
        qr = qrels_by_q.get(qid, [])
        ids = [d for d, _ in cands]
        rel_ids, rel = _ref_ranking(qr, ids)
        graph = build_graph(
            [
                Preference(winner=p.winner_doc_id, loser=p.loser_doc_id, weight=p.weight)
                for p in []
            ]
        )
        schema_prefs = []
        for i, winner in enumerate(rel_ids):
            for loser in rel_ids[i + 1 :]:
                if rel.get(winner, 0) > rel.get(loser, 0):
                    schema_prefs.append(Preference(winner=winner, loser=loser, weight=1.0))
        if schema_prefs:
            graph = build_graph(schema_prefs)

        ranking = result.ranked_doc_ids
        ndcg = _ndcg_at_k(ranking, rel, TOP_K)
        mapk = _map_at_k(ranking, rel, TOP_K)
        pk, rk = _precision_recall_at_k(ranking, rel, TOP_K)
        bew = _backward_edge_weight(graph, ranking) if graph.number_of_edges() else None
        pic = _pairwise_inconsistency(graph, ranking) if graph.number_of_edges() else None
        rows.append(
            {
                "dataset": DATASET,
                "query_id": qid,
                "method": "llm_listwise",
                "n_candidates": len(ranking),
                "ndcg_at_k": round(ndcg, 6) if ndcg is not None else None,
                "map_at_k": round(mapk, 6) if mapk is not None else None,
                "precision_at_k": round(pk, 6) if pk is not None else None,
                "recall_at_k": round(rk, 6) if rk is not None else None,
                "backward_edge_weight": round(bew, 6) if bew is not None else None,
                "pairwise_inconsistency": pic,
                "api_calls": stats.get("api_calls", 0),
                "cache_hits": stats.get("cache_hits", 0),
                "prompt_tokens": stats.get("prompt_tokens", 0),
                "completion_tokens": stats.get("completion_tokens", 0),
                "total_tokens": stats.get("total_tokens", 0),
                "parse_failures": stats.get("parse_failures", 0),
            }
        )
        if stats.get("parse_failures", 0) and not parse_issue_examples:
            parse_issue_examples.extend(meta.get("parse_error_details", [])[:3])
        print(
            f"  query {idx + 1:>3}/{len(pool)} [{qid[:12]}…] "
            f"{dt:.1f}s (API={stats.get('api_calls', 0)} cache={stats.get('cache_hits', 0)})"
        )

    wall_elapsed = time.time() - wall_start
    if not rows:
        print("\nFATAL: No listwise results collected.")
        sys.exit(1)

    total_api_calls = sum(r["api_calls"] for r in rows)
    total_cache_hits = sum(r["cache_hits"] for r in rows)
    total_prompt_tokens = sum(r["prompt_tokens"] for r in rows)
    total_completion_tokens = sum(r["completion_tokens"] for r in rows)
    total_tokens = sum(r["total_tokens"] for r in rows)
    total_cost = (
        total_prompt_tokens / 1e6 * GPT4O_MINI_INPUT_COST_PER_M
        + total_completion_tokens / 1e6 * GPT4O_MINI_OUTPUT_COST_PER_M
    )

    pq = OUTPUT_DIR / "listwise_per_query.csv"
    with pq.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n[5] Per-query CSV → {pq}")

    def _mn(key):
        vals = [r[key] for r in rows if r.get(key) is not None]
        return sum(vals) / len(vals) if vals else None

    summary = {
        "method": "llm_listwise",
        "n_queries": len(rows),
        "ndcg_mean": round(_mn("ndcg_at_k"), 4) if _mn("ndcg_at_k") is not None else None,
        "map_mean": round(_mn("map_at_k"), 4) if _mn("map_at_k") is not None else None,
        "precision_mean": (
            round(_mn("precision_at_k"), 4) if _mn("precision_at_k") is not None else None
        ),
        "recall_mean": (
            round(_mn("recall_at_k"), 4) if _mn("recall_at_k") is not None else None
        ),
        "bew_mean": round(_mn("backward_edge_weight"), 2)
        if _mn("backward_edge_weight") is not None
        else None,
        "pic_mean": round(_mn("pairwise_inconsistency"), 2)
        if _mn("pairwise_inconsistency") is not None
        else None,
    }

    sp = OUTPUT_DIR / "listwise_summary.csv"
    with sp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary.keys()))
        w.writeheader()
        w.writerow(summary)
    print(f"[6] Summary CSV → {sp}")

    cfg = {
        "label": (
            f"REAL OPENAI LISTWISE RUN ({completed} queries"
            f"{', PARTIAL' if api_error_msg else ''}) — NOT mock"
        ),
        "dataset": DATASET,
        "max_queries": MAX_QUERIES,
        "top_k": TOP_K,
        "seed": SEED,
        "model": MODEL,
        "provider": "openai",
        "dry_run": False,
        "temperature": TEMPERATURE,
        "window_size": WINDOW_SIZE,
        "step_size": STEP_SIZE,
        "num_passes": NUM_PASSES,
        "n_queries_processed": completed,
        "partial_run": api_error_msg is not None,
        "api_error": api_error_msg,
        "cache_dir": str(cache_dir),
        "api_stats": {
            "api_calls": total_api_calls,
            "cache_hits": total_cache_hits,
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "parse_failures": parse_issue_count,
        },
        "wall_time_s": round(wall_elapsed, 1),
        "cost_estimate_usd": round(total_cost, 4),
    }
    cp = OUTPUT_DIR / "config.json"
    with cp.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    print(f"[7] Config → {cp}")

    md = [
        f"# Real OpenAI Listwise Run — {DATASET}",
        "",
        "**This is a REAL OpenAI run — rankings come from live gpt-4o-mini API calls.**",
        "",
        "## Configuration",
        "",
        "| Param | Value |",
        "|-------|-------|",
        f"| Dataset | {DATASET} |",
        f"| Queries | {completed} |",
        f"| top_k | {TOP_K} |",
        f"| Model | {MODEL} |",
        "| Provider | openai |",
        "| Mode | **REAL API CALLS** |",
        f"| Temperature | {TEMPERATURE} |",
        f"| Window size | {WINDOW_SIZE} |",
        f"| Step size | {STEP_SIZE} |",
        f"| Num passes | {NUM_PASSES} |",
        "",
        "## API Usage",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| API calls | {total_api_calls} |",
        f"| Cache hits | {total_cache_hits} |",
        f"| Prompt tokens | {total_prompt_tokens:,} |",
        f"| Completion tokens | {total_completion_tokens:,} |",
        f"| Total tokens | {total_tokens:,} |",
        f"| Wall time | {wall_elapsed:.1f}s |",
        f"| Est. cost | ${total_cost:.4f} |",
        f"| Parse failures | {parse_issue_count} |",
        "",
        "## Results",
        "",
        f"| Method | nDCG@{TOP_K} | MAP@{TOP_K} | BEW↓ | PIC↓ |",
        "|--------|---------|---------|------|------|",
        (
            f"| llm_listwise | "
            f"{summary['ndcg_mean'] if summary['ndcg_mean'] is not None else '—'} | "
            f"{summary['map_mean'] if summary['map_mean'] is not None else '—'} | "
            f"{summary['bew_mean'] if summary['bew_mean'] is not None else '—'} | "
            f"{summary['pic_mean'] if summary['pic_mean'] is not None else '—'} |"
        ),
        "",
    ]
    if api_error_msg:
        md += [f"**Partial run** — error: `{api_error_msg}`", ""]
    if parse_issue_examples:
        md += ["## Parse issues", ""]
        for item in parse_issue_examples:
            md.append(f"- `{item}`")
        md.append("")
    md += [
        "---",
        "*Generated from REAL openai API calls, not mock/synthetic.*",
    ]
    mp = OUTPUT_DIR / "LISTWISE_RUN_SUMMARY.md"
    mp.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"[8] Summary → {mp}")


if __name__ == "__main__":
    main()
