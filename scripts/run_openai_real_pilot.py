"""
run_openai_real_pilot.py
========================
Real OpenAI pairwise pilot — configurable dataset, queries, and top_k.

Makes REAL OpenAI API calls (no mock/dry-run). Judgments are cached to disk
for full resumability. Evaluates 12 aggregation methods on the same judgments.

Usage:
    python scripts/run_openai_real_pilot.py                    # defaults
    DATASET=hotpotqa MAX_QUERIES=10 python scripts/run_openai_real_pilot.py
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


from consistency_ranker.baseline_ranking import score_sum_scores, topological_ranking
from consistency_ranker.cycle_detection import has_cycle
from consistency_ranker.data.query_ids import eligible_query_ids, has_usable_eval_labels
from consistency_ranker.data.unified_loader import load_dataset_splits
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.greedy_fas import greedy_fas
from consistency_ranker.pairwise_prefs import Preference
from rerankers.common import write_pairwise_file
from rerankers.llm_pairwise import LLMCallStats, PairwiseConfig, collect_all_pairs
from rerankers.tournament_agg import aggregate_preferences

DATASET = os.environ.get("DATASET", "scidocs")
MAX_QUERIES = int(os.environ.get("MAX_QUERIES", "20"))
TOP_K = int(os.environ.get("TOP_K", "15"))
SEED = 42
MODEL = "gpt-4o-mini"
PROVIDER = "openai"

OUTPUT_DIR = Path(
    os.environ.get(
        "OUTPUT_DIR",
        f"outputs/openai_{DATASET}_real_run_q{MAX_QUERIES}_k{TOP_K}",
    )
)

GPT4O_MINI_INPUT_COST_PER_M = 0.15
GPT4O_MINI_OUTPUT_COST_PER_M = 0.60

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
        1 for u, v in graph.edges()
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


def _normalize(scores):
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    if hi - lo <= 1e-12:
        return {k: 0.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def _copeland_from_graph(g):
    scores = {n: g.out_degree(n) - g.in_degree(n) for n in g.nodes()}
    return sorted(scores, key=lambda n: (-scores[n], n))


def _balance_from_graph(g):
    scores = {n: 0.0 for n in g.nodes()}
    for u, v, d in g.edges(data=True):
        w = d.get("weight", 1.0)
        scores[u] += w
        scores[v] -= w
    return sorted(scores, key=lambda n: (-scores[n], n))


def _hybrid(g, prior, component, alpha):
    if not g.nodes():
        return []
    if component == "balance":
        raw = {n: 0.0 for n in g.nodes()}
        for u, v, d in g.edges(data=True):
            w = d.get("weight", 1.0)
            raw[u] += w
            raw[v] -= w
    else:
        raw = {n: float(g.out_degree(n) - g.in_degree(n)) for n in g.nodes()}
    pn = _normalize({n: prior.get(n, 0.0) for n in g.nodes()})
    cn = _normalize(raw)
    combo = {n: pn.get(n, 0.0) + alpha * cn.get(n, 0.0) for n in g.nodes()}
    return sorted(combo, key=lambda n: (-combo[n], n))


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set.")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cache_dir = OUTPUT_DIR / "judgment_cache"

    print(f"\n{'='*70}")
    print(f"  REAL OpenAI Pairwise Run — {DATASET}")
    print(f"{'='*70}")
    print(f"  dataset     : {DATASET}")
    print(f"  max_queries : {MAX_QUERIES}")
    print(f"  top_k       : {TOP_K}")
    print(f"  model       : {MODEL}")
    print(f"  provider    : {PROVIDER}")
    print("  mode        : REAL API CALLS")
    print("  debiasing   : DISABLED")
    print(f"  output_dir  : {OUTPUT_DIR}")
    n_pairs = TOP_K * (TOP_K - 1) // 2
    print(f"  est. calls  : {n_pairs * MAX_QUERIES} ({n_pairs} pairs × {MAX_QUERIES} q)")
    print()

    # 1. Load dataset
    queries, documents, qrels = load_dataset_splits(DATASET)
    print(f"[1] Loaded {len(queries)} queries, {len(documents)} docs, {len(qrels)} qrels")

    qrels_by_q = defaultdict(list)
    for e in qrels:
        qrels_by_q[e.query_id].append(e)
    docs_by_id = {getattr(d, "doc_id", str(i)): d for i, d in enumerate(documents)}
    query_by_id = {q.query_id: q for q in queries}

    # 2. Sample queries
    eligible = eligible_query_ids(qrels)
    rng = random.Random(SEED)
    rng.shuffle(eligible)
    sampled = eligible[:MAX_QUERIES]
    print(f"[2] {len(eligible)} eligible; sampled {len(sampled)}")

    # 3. Build candidate pools
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

    # 4. Collect real pairwise judgments
    config = PairwiseConfig(
        model=MODEL,
        provider=PROVIDER,
        dry_run=False,
        seed=SEED,
        cache_dir=cache_dir,
        temperature=0.0,
        max_tokens=4,
        debias_position=False,
    )

    stats = LLMCallStats()
    all_prefs: dict[str, list[tuple[str, str, float]]] = {}
    all_meta: dict[str, dict] = {}

    wall_start = time.time()
    api_error_msg = None
    print("\n[4] Collecting REAL OpenAI pairwise judgments …")
    for idx, (qid, qt, cands) in enumerate(pool):
        t0 = time.time()
        try:
            pairs, meta = collect_all_pairs(qid, qt, cands, config, stats=stats)
        except Exception as exc:
            api_error_msg = str(exc)
            print(f"\n  ERROR at query {idx+1} [{qid}]: {exc}")
            print("  Stopping. Will evaluate collected queries.")
            break
        dt = time.time() - t0
        all_prefs[qid] = pairs
        all_meta[qid] = meta
        print(
            f"  query {idx+1:>3}/{len(pool)} [{qid[:12]}…] "
            f"{len(pairs)} pairs {dt:.1f}s "
            f"(API={stats.api_calls} cache={stats.cache_hits})"
        )
    wall_elapsed = time.time() - wall_start

    if not all_prefs:
        print("\nFATAL: No judgments collected.")
        sys.exit(1)

    pool = [(q, t, c) for q, t, c in pool if q in all_prefs]
    total_pairs = sum(len(p) for p in all_prefs.values())
    ss = stats.summary()

    print(f"\n  Total pairs  : {total_pairs}")
    print(f"  API calls    : {ss['api_calls']}")
    print(f"  Cache hits   : {ss['cache_hits']}")
    print(f"  Prompt tok   : {ss['prompt_tokens']:,}")
    print(f"  Compl tok    : {ss['completion_tokens']:,}")
    print(f"  Total tok    : {ss['total_tokens']:,}")
    print(f"  Errors       : {ss['errors']}")
    print(f"  Wall time    : {wall_elapsed:.1f}s")

    in_cost = ss["prompt_tokens"] / 1e6 * GPT4O_MINI_INPUT_COST_PER_M
    out_cost = ss["completion_tokens"] / 1e6 * GPT4O_MINI_OUTPUT_COST_PER_M
    total_cost = in_cost + out_cost
    print(f"  Est. cost    : ${total_cost:.4f}")

    jf = OUTPUT_DIR / "judgments.jsonl"
    write_pairwise_file(all_prefs, jf)
    print(f"\n  Saved → {jf}")

    # 5. Evaluate
    rows: list[dict] = []
    print(f"\n[5] Evaluating {len(METHOD_LABELS)} methods …")
    for qi, (qid, qt, cands) in enumerate(pool):
        prefs = all_prefs[qid]
        if not prefs:
            continue
        qr = qrels_by_q.get(qid, [])
        ids = [d for d, _ in cands]
        gp = [Preference(winner=w, loser=lo, weight=wt) for w, lo, wt in prefs]
        graph = build_graph(gp)
        dag, removed = greedy_fas(graph)
        cyclic = has_cycle(graph)
        prior = score_sum_scores(graph)
        cn = set(graph.nodes())
        ref, rel = _ref_ranking(qr, cn)
        cs = set(ref)

        rnk: dict[str, list[str]] = {}

        # Copeland
        wins, losses = defaultdict(int), defaultdict(int)
        for w, lo, _ in prefs:
            wins[w] += 1
            losses[lo] += 1
        cop = {d: wins.get(d, 0) - losses.get(d, 0) for d in ids}
        rnk["llm_pairwise_copeland"] = sorted(cop, key=lambda d: (-cop[d], d))

        for ml, am in [
            ("bt_from_llm", "bradley_terry"),
            ("win_rate_from_llm", "win_rate"),
            ("markov_from_llm", "markov_chain"),
            ("tournament_sort_from_llm", "tournament_sort"),
        ]:
            kw = {"seed": SEED} if am == "tournament_sort" else {}
            r = aggregate_preferences(method=am, preferences=prefs, all_doc_ids=ids, **kw)
            rnk[ml] = r.ranked_doc_ids

        rnk["greedy_fas_topological"] = topological_ranking(dag)
        rnk["greedy_fas_weighted_balance"] = _balance_from_graph(dag)
        rnk["greedy_fas_copeland"] = _copeland_from_graph(dag)

        rnk["hybrid_rrf_repaired_copeland_a03"] = _hybrid(dag, prior, "copeland", 0.3)
        rnk["hybrid_rrf_unrepaired_copeland_a03"] = _hybrid(graph, prior, "copeland", 0.3)
        rnk["hybrid_rrf_repaired_balance_a03"] = _hybrid(dag, prior, "balance", 0.3)
        rnk["hybrid_rrf_unrepaired_balance_a03"] = _hybrid(graph, prior, "balance", 0.3)

        for mn in METHOD_LABELS:
            ra = [d for d in rnk[mn] if d in cs]
            ndcg = _ndcg_at_k(ra, rel, TOP_K)
            mapk = _map_at_k(ra, rel, TOP_K)
            pk, rk = _precision_recall_at_k(ra, rel, TOP_K)
            bew = _backward_edge_weight(graph, rnk[mn])
            pic = _pairwise_inconsistency(graph, rnk[mn])
            rows.append({
                "dataset": DATASET, "query_id": qid, "method": mn,
                "n_candidates": len(rnk[mn]), "is_cyclic": cyclic,
                "n_fas_removed": len(removed),
                "ndcg_at_k": round(ndcg, 6) if ndcg is not None else None,
                "map_at_k": round(mapk, 6) if mapk is not None else None,
                "precision_at_k": round(pk, 6) if pk is not None else None,
                "recall_at_k": round(rk, 6) if rk is not None else None,
                "backward_edge_weight": round(bew, 6),
                "pairwise_inconsistency": pic,
            })

        if (qi + 1) % 5 == 0:
            print(f"  … {qi+1}/{len(pool)} queries")

    print(f"  Evaluated {len(pool)} queries × {len(METHOD_LABELS)} methods")

    # 6. Per-query CSV
    pq = OUTPUT_DIR / "openai_per_query.csv"
    if rows:
        with pq.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"\n[6] Per-query CSV → {pq}")

    # 7. Summary
    by_m = defaultdict(list)
    for r in rows:
        by_m[r["method"]].append(r)
    srows = []
    for m in METHOD_LABELS:
        mr = by_m.get(m, [])
        if not mr:
            continue

        def _mn(k, _mr=mr):
            v = [r[k] for r in _mr if r.get(k) is not None]
            return sum(v) / len(v) if v else None

        srows.append({
            "method": m, "n_queries": len(mr),
            "ndcg_mean": round(_mn("ndcg_at_k"), 4) if _mn("ndcg_at_k") is not None else None,
            "map_mean": round(_mn("map_at_k"), 4) if _mn("map_at_k") is not None else None,
            "precision_mean": (
                round(_mn("precision_at_k"), 4) if _mn("precision_at_k") is not None else None
            ),
            "recall_mean": (
                round(_mn("recall_at_k"), 4) if _mn("recall_at_k") is not None else None
            ),
            "bew_mean": round(_mn("backward_edge_weight"), 2),
            "pic_mean": round(_mn("pairwise_inconsistency"), 2),
        })

    sp = OUTPUT_DIR / "openai_summary.csv"
    if srows:
        with sp.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(srows[0].keys()))
            w.writeheader()
            w.writerows(srows)
    print(f"[7] Summary CSV → {sp}")

    # 8. Config
    nq = len(pool)
    partial = api_error_msg is not None
    cfg = {
        "label": f"REAL OPENAI RUN ({nq} queries{', PARTIAL' if partial else ''}) — NOT mock",
        "dataset": DATASET, "max_queries": MAX_QUERIES, "top_k": TOP_K,
        "seed": SEED, "model": MODEL, "provider": PROVIDER,
        "dry_run": False, "debias_position": False, "temperature": 0.0,
        "n_queries_processed": nq, "partial_run": partial,
        "api_error": api_error_msg, "total_pairwise_comparisons": total_pairs,
        "methods": METHOD_LABELS, "cache_dir": str(cache_dir),
        "api_stats": ss, "wall_time_s": round(wall_elapsed, 1),
        "cost_estimate_usd": round(total_cost, 4),
    }
    cp = OUTPUT_DIR / "config.json"
    with cp.open("w") as f:
        json.dump(cfg, f, indent=2)
    print(f"[8] Config → {cp}")

    # 9. Markdown
    by_name = {s["method"]: s for s in srows}
    cyc_cnt = sum(1 for r in rows if r["method"] == "llm_pairwise_copeland" and r["is_cyclic"])
    tot_q = sum(1 for r in rows if r["method"] == "llm_pairwise_copeland")
    avg_fas = (
        sum(r["n_fas_removed"] for r in rows if r["method"] == "llm_pairwise_copeland")
        / tot_q if tot_q else 0
    )
    best_ndcg = max((s["ndcg_mean"] for s in srows if s["ndcg_mean"] is not None), default=0)

    md = [
        f"# Real OpenAI Pairwise Run — {DATASET}", "",
        "**This is a REAL OpenAI run — all judgments from live gpt-4o-mini API calls.**", "",
        "## Configuration", "",
        "| Param | Value |", "|-------|-------|",
        f"| Dataset | {DATASET} |",
        f"| Queries | {nq} |",
        f"| top_k | {TOP_K} |",
        f"| Model | {MODEL} |",
        f"| Provider | {PROVIDER} |",
        "| Mode | **REAL API CALLS** |",
        "| Temperature | 0.0 |", "",
        "## API Usage", "",
        "| Metric | Value |", "|--------|-------|",
        f"| Pairwise comparisons | {total_pairs} |",
        f"| API calls | {ss['api_calls']} |",
        f"| Cache hits | {ss['cache_hits']} |",
        f"| Prompt tokens | {ss['prompt_tokens']:,} |",
        f"| Completion tokens | {ss['completion_tokens']:,} |",
        f"| Wall time | {wall_elapsed:.1f}s |",
        f"| Est. cost | ${total_cost:.4f} |",
        f"| Errors | {ss['errors']} |", "",
    ]
    if partial:
        md += [f"**Partial run** — error: `{api_error_msg}`", ""]

    md += [
        "## Results", "",
        f"| Method | nDCG@{TOP_K} | MAP@{TOP_K} | BEW↓ | PIC↓ |",
        "|--------|---------|---------|------|------|",
    ]
    for s in srows:
        n = f"{s['ndcg_mean']:.4f}" if s["ndcg_mean"] is not None else "—"
        m = f"{s['map_mean']:.4f}" if s["map_mean"] is not None else "—"
        b = f"{s['bew_mean']:.2f}"
        p = f"{s['pic_mean']:.2f}"
        if s["ndcg_mean"] is not None and abs(s["ndcg_mean"] - best_ndcg) < 1e-6:
            n = f"**{n}**"
        md.append(f"| {s['method']} | {n} | {m} | {b} | {p} |")

    md += ["", "## Repaired vs Unrepaired", "",
           "| Component | ΔnDCG | ΔBEW | ΔPIC |",
           "|-----------|-------|------|------|"]
    for comp in ("copeland", "balance"):
        rk = f"hybrid_rrf_repaired_{comp}_a03"
        uk = f"hybrid_rrf_unrepaired_{comp}_a03"
        r, u = by_name.get(rk, {}), by_name.get(uk, {})
        if r and u:
            dn = (r.get("ndcg_mean") or 0) - (u.get("ndcg_mean") or 0)
            db = (u.get("bew_mean") or 0) - (r.get("bew_mean") or 0)
            dp = (u.get("pic_mean") or 0) - (r.get("pic_mean") or 0)
            md.append(f"| {comp} | {dn:+.4f} | {db:+.2f} | {dp:+.2f} |")

    md += ["", "## Graph Stats", ""]
    if tot_q:
        md.append(f"- Cyclic queries: {cyc_cnt}/{tot_q} ({cyc_cnt/tot_q*100:.1f}%)")
    md += [f"- Avg FAS edges removed: {avg_fas:.1f}", "",
           "---",
           f"*Generated from REAL {PROVIDER} API calls, not mock/synthetic.*"]

    mp = OUTPUT_DIR / "OPENAI_RUN_SUMMARY.md"
    mp.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"[9] Summary → {mp}")

    # 10. Console
    print(f"\n{'='*70}")
    hdr = (
        f"{'Method':<42} {'nDCG@'+str(TOP_K):>8} {'MAP@'+str(TOP_K):>8} "
        f"{'BEW':>8} {'PIC':>8}"
    )
    print(hdr)
    print("-" * len(hdr))
    for s in srows:
        n = f"{s['ndcg_mean']:.4f}" if s["ndcg_mean"] is not None else "—"
        m = f"{s['map_mean']:.4f}" if s["map_mean"] is not None else "—"
        b = f"{s['bew_mean']:.2f}"
        p = f"{s['pic_mean']:.2f}"
        print(f"{s['method']:<42} {n:>8} {m:>8} {b:>8} {p:>8}")
    print(f"{'='*70}")
    print()


if __name__ == "__main__":
    main()
