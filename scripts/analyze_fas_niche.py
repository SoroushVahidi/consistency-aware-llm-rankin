#!/usr/bin/env python
"""
Per-query and grouped analysis for FAS niche: when does consistency-aware repair help?

Uses the validated fair pipeline. Computes:
- Per-query: NDCG@10 for each method, BEW before/after, cyclic, n_sccs
- BM25 vs dense disagreement (1 - Kendall tau)
- Whether FAS improved over RRF and over dense
- Grouped analysis by conflict level
- Selective repair: apply FAS only when conflict exceeds threshold
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from consistency_ranker.data.dataset_registry import get_config
from consistency_ranker.data.unified_loader import load_dataset_splits, load_multi_scorer_rankings
from consistency_ranker.evaluation import kendall_tau

from run_validated_multi_scorer import run_query  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="fiqa")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--max-queries", type=int, default=50)
    parser.add_argument("--mode", default="summed_margin")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/fas_niche"))
    parser.add_argument("--bew-buckets", default="0,1,5,999", help="BEW-before bucket edges (low,med,high)")
    args = parser.parse_args()

    cfg = get_config(args.dataset)
    scorer_paths = {
        "bm25": cfg.processed_path / "scores" / "bm25.jsonl",
        "dense": cfg.processed_path / "scores" / "dense.jsonl",
    }
    multi = load_multi_scorer_rankings(scorer_paths)
    if "dense" not in multi:
        print("ERROR: dense scores not found. Run generate_dense_scores.py first.")
        sys.exit(1)

    queries, _, qrels = load_dataset_splits(args.dataset)
    qrels_by_q = {}
    for e in qrels:
        qrels_by_q.setdefault(e.query_id, []).append(e)

    qids = [
        q.query_id
        for q in queries
        if q.query_id in multi["bm25"]
        and q.query_id in multi["dense"]
        and q.query_id in qrels_by_q
    ][: args.max_queries]

    # Per-query analysis
    per_query: list[dict] = []
    for qid in qids:
        sr = {"bm25": multi["bm25"][qid], "dense": multi["dense"][qid]}
        relevance_map = {e.doc_id: e.relevance for e in qrels_by_q[qid]}
        relevant_ids = {e.doc_id for e in qrels_by_q[qid] if e.relevance > 0}
        res, rankings = run_query(qid, sr, args.top_k, args.mode, relevance_map, relevant_ids, return_rankings=True)
        graph_stats = res.pop("_graph_stats", {})

        ndcg_bm25 = res["bm25_raw"]["ndcg_at_10"]
        ndcg_dense = res["dense_raw"]["ndcg_at_10"]
        ndcg_rrf = res["rrf_fusion"]["ndcg_at_10"]
        ndcg_fas = res["greedy_fas_topological"]["ndcg_at_10"]

        bew_before = graph_stats.get("bew_bm25_raw", 0)
        bew_after = graph_stats.get("bew_fas", 0)
        cyclic = graph_stats.get("cyclic", False)
        n_sccs = graph_stats.get("n_sccs", 0)

        bm25_rank = rankings["bm25_raw"]
        dense_rank = rankings["dense_raw"]
        tau = kendall_tau(bm25_rank, dense_rank)
        disagreement = 1.0 - tau  # higher = more disagreement

        fas_beat_rrf = ndcg_fas > ndcg_rrf
        fas_beat_dense = ndcg_fas > ndcg_dense

        per_query.append({
            "query_id": qid,
            "ndcg_bm25_raw": round(ndcg_bm25, 6),
            "ndcg_dense_raw": round(ndcg_dense, 6),
            "ndcg_rrf_fusion": round(ndcg_rrf, 6),
            "ndcg_greedy_fas": round(ndcg_fas, 6),
            "bew_before": round(bew_before, 6),
            "bew_after": round(bew_after, 6),
            "cyclic": cyclic,
            "n_sccs": n_sccs,
            "disagreement_bm25_dense": round(disagreement, 6),
            "fas_improved_over_rrf": fas_beat_rrf,
            "fas_improved_over_dense": fas_beat_dense,
        })

    # Write per-query CSV
    args.output_dir.mkdir(parents=True, exist_ok=True)
    per_query_path = args.output_dir / f"{args.dataset}_per_query_k{args.top_k}_{args.mode}.csv"
    if per_query:
        with per_query_path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=per_query[0].keys())
            w.writeheader()
            w.writerows(per_query)
        print(f"Wrote per-query: {per_query_path}")

    # Parse BEW buckets
    bew_edges = [float(x) for x in args.bew_buckets.split(",")]
    bucket_names = []
    for i in range(len(bew_edges) - 1):
        lo, hi = bew_edges[i], bew_edges[i + 1]
        if hi >= 999:
            bucket_names.append((f"BEW>={lo:.0f}", lambda b: b >= lo))
        else:
            bucket_names.append((f"{lo:.0f}<=BEW<{hi:.0f}", lambda b, l=lo, h=hi: l <= b < h))

    def bucket_by_bew(bew: float) -> str:
        for name, pred in bucket_names:
            if pred(bew):
                return name
        return "other"

    # Add BEW bucket to each row
    for row in per_query:
        row["bew_bucket"] = bucket_by_bew(row["bew_before"])

    # --- Table 1: Overall results ---
    n = len(per_query)
    print("\n" + "=" * 80)
    print("1. OVERALL RESULTS")
    print("=" * 80)
    print(f"Dataset={args.dataset} top_k={args.top_k} mode={args.mode} n={n}")
    print("-" * 60)
    for method, col in [
        ("bm25_raw", "ndcg_bm25_raw"),
        ("dense_raw", "ndcg_dense_raw"),
        ("rrf_fusion", "ndcg_rrf_fusion"),
        ("greedy_fas", "ndcg_greedy_fas"),
    ]:
        avg = sum(r[col] for r in per_query) / n
        print(f"  {method:<20} NDCG@10 = {avg:.4f}")
    pct_fas_beat_rrf = 100 * sum(1 for r in per_query if r["fas_improved_over_rrf"]) / n
    pct_fas_beat_dense = 100 * sum(1 for r in per_query if r["fas_improved_over_dense"]) / n
    pct_cyclic = 100 * sum(1 for r in per_query if r["cyclic"]) / n
    print(f"  FAS beat RRF: {pct_fas_beat_rrf:.1f}% of queries")
    print(f"  FAS beat dense: {pct_fas_beat_dense:.1f}% of queries")
    print(f"  Cyclic graphs: {pct_cyclic:.1f}%")

    # --- Table 2: By BEW bucket ---
    print("\n" + "=" * 80)
    print("2. GROUPED BY CONFLICT LEVEL (BEW before)")
    print("=" * 80)
    buckets_seen: set[str] = set()
    for row in per_query:
        buckets_seen.add(row["bew_bucket"])
    for bucket in sorted(buckets_seen):
        rows = [r for r in per_query if r["bew_bucket"] == bucket]
        if not rows:
            continue
        m = len(rows)
        print(f"\n  {bucket} (n={m})")
        print("  " + "-" * 50)
        for method, col in [
            ("bm25_raw", "ndcg_bm25_raw"),
            ("dense_raw", "ndcg_dense_raw"),
            ("rrf_fusion", "ndcg_rrf_fusion"),
            ("greedy_fas", "ndcg_greedy_fas"),
        ]:
            avg = sum(r[col] for r in rows) / m
            print(f"    {method:<18} NDCG@10 = {avg:.4f}")
        pct_fas_rrf = 100 * sum(1 for r in rows if r["fas_improved_over_rrf"]) / m
        print(f"    FAS beat RRF: {pct_fas_rrf:.1f}%")

    # --- Table 3: Cyclic vs acyclic ---
    print("\n" + "=" * 80)
    print("3. CYCLIC vs ACYCLIC")
    print("=" * 80)
    for label, pred in [("Cyclic", lambda r: r["cyclic"]), ("Acyclic", lambda r: not r["cyclic"])]:
        rows = [r for r in per_query if pred(r)]
        if not rows:
            continue
        m = len(rows)
        print(f"\n  {label} (n={m})")
        print("  " + "-" * 50)
        for method, col in [
            ("bm25_raw", "ndcg_bm25_raw"),
            ("dense_raw", "ndcg_dense_raw"),
            ("rrf_fusion", "ndcg_rrf_fusion"),
            ("greedy_fas", "ndcg_greedy_fas"),
        ]:
            avg = sum(r[col] for r in rows) / m
            print(f"    {method:<18} NDCG@10 = {avg:.4f}")
        pct_fas_rrf = 100 * sum(1 for r in rows if r["fas_improved_over_rrf"]) / m
        print(f"    FAS beat RRF: {pct_fas_rrf:.1f}%")

    # --- Table 4: Hardest queries ---
    print("\n" + "=" * 80)
    print("4. FAS ON HARDEST QUERIES")
    print("=" * 80)

    # 4a: Top 25% by BEW
    sorted_by_bew = sorted(per_query, key=lambda r: r["bew_before"], reverse=True)
    top25_bew = sorted_by_bew[: max(1, len(sorted_by_bew) // 4)]
    print(f"\n  Top 25% by BEW (n={len(top25_bew)}, BEW>={min(r['bew_before'] for r in top25_bew):.2f})")
    for method, col in [
        ("bm25_raw", "ndcg_bm25_raw"),
        ("dense_raw", "ndcg_dense_raw"),
        ("rrf_fusion", "ndcg_rrf_fusion"),
        ("greedy_fas", "ndcg_greedy_fas"),
    ]:
        avg = sum(r[col] for r in top25_bew) / len(top25_bew)
        print(f"    {method:<18} NDCG@10 = {avg:.4f}")
    pct = 100 * sum(1 for r in top25_bew if r["fas_improved_over_rrf"]) / len(top25_bew)
    print(f"    FAS beat RRF: {pct:.1f}%")

    # 4b: Cyclic only
    cyclic_rows = [r for r in per_query if r["cyclic"]]
    if cyclic_rows:
        print(f"\n  Cyclic only (n={len(cyclic_rows)})")
        for method, col in [
            ("bm25_raw", "ndcg_bm25_raw"),
            ("dense_raw", "ndcg_dense_raw"),
            ("rrf_fusion", "ndcg_rrf_fusion"),
            ("greedy_fas", "ndcg_greedy_fas"),
        ]:
            avg = sum(r[col] for r in cyclic_rows) / len(cyclic_rows)
            print(f"    {method:<18} NDCG@10 = {avg:.4f}")
        pct = 100 * sum(1 for r in cyclic_rows if r["fas_improved_over_rrf"]) / len(cyclic_rows)
        print(f"    FAS beat RRF: {pct:.1f}%")

    # 4c: Top 25% by BM25-dense disagreement
    sorted_by_disc = sorted(per_query, key=lambda r: r["disagreement_bm25_dense"], reverse=True)
    top25_disc = sorted_by_disc[: max(1, len(sorted_by_disc) // 4)]
    print(f"\n  Top 25% by BM25-dense disagreement (n={len(top25_disc)})")
    for method, col in [
        ("bm25_raw", "ndcg_bm25_raw"),
        ("dense_raw", "ndcg_dense_raw"),
        ("rrf_fusion", "ndcg_rrf_fusion"),
        ("greedy_fas", "ndcg_greedy_fas"),
    ]:
        avg = sum(r[col] for r in top25_disc) / len(top25_disc)
        print(f"    {method:<18} NDCG@10 = {avg:.4f}")
    pct = 100 * sum(1 for r in top25_disc if r["fas_improved_over_rrf"]) / len(top25_disc)
    print(f"    FAS beat RRF: {pct:.1f}%")

    # 4d: Queries where RRF performs poorly (bottom 25% by RRF NDCG)
    sorted_by_rrf = sorted(per_query, key=lambda r: r["ndcg_rrf_fusion"])
    bottom25_rrf = sorted_by_rrf[: max(1, len(sorted_by_rrf) // 4)]
    print(f"\n  Bottom 25% by RRF NDCG (n={len(bottom25_rrf)}, RRF<={max(r['ndcg_rrf_fusion'] for r in bottom25_rrf):.4f})")
    for method, col in [
        ("bm25_raw", "ndcg_bm25_raw"),
        ("dense_raw", "ndcg_dense_raw"),
        ("rrf_fusion", "ndcg_rrf_fusion"),
        ("greedy_fas", "ndcg_greedy_fas"),
    ]:
        avg = sum(r[col] for r in bottom25_rrf) / len(bottom25_rrf)
        print(f"    {method:<18} NDCG@10 = {avg:.4f}")
    pct = 100 * sum(1 for r in bottom25_rrf if r["fas_improved_over_rrf"]) / len(bottom25_rrf)
    print(f"    FAS beat RRF: {pct:.1f}%")

    # --- Table 5: Selective repair ---
    print("\n" + "=" * 80)
    print("5. SELECTIVE REPAIR")
    print("=" * 80)
    print("  Base = RRF. Apply FAS only when conflict exceeds threshold.")
    print("-" * 60)

    # Thresholds: BEW-based and cyclic-based (never = baseline, always = full FAS)
    thresholds = [
        ("never (baseline)", lambda r: False),
        ("bew>=5", lambda r: r["bew_before"] >= 5),
        ("bew>=3", lambda r: r["bew_before"] >= 3),
        ("bew>=2", lambda r: r["bew_before"] >= 2),
        ("bew>=1", lambda r: r["bew_before"] >= 1),
        ("cyclic_only", lambda r: r["cyclic"]),
        ("always", lambda r: True),
    ]

    selective_results = []
    for name, pred in thresholds:
        rows_apply = [r for r in per_query if pred(r)]
        # For each query: use FAS if in rows_apply else RRF
        ndcgs = []
        for r in per_query:
            if pred(r):
                ndcgs.append(r["ndcg_greedy_fas"])
            else:
                ndcgs.append(r["ndcg_rrf_fusion"])
        avg_ndcg = sum(ndcgs) / n
        n_apply = len(rows_apply)
        selective_results.append((name, avg_ndcg, n_apply))

    for name, avg_ndcg, n_apply in selective_results:
        print(f"  {name:<20} NDCG@10={avg_ndcg:.4f}  (FAS applied to {n_apply} queries)")

    # Also: selective repair with dense as base
    print("\n  Base = dense_raw. Apply FAS only when conflict exceeds threshold.")
    print("-" * 60)
    for name, pred in thresholds:
        ndcgs = []
        for r in per_query:
            if pred(r):
                ndcgs.append(r["ndcg_greedy_fas"])
            else:
                ndcgs.append(r["ndcg_dense_raw"])
        avg_ndcg = sum(ndcgs) / n
        n_apply = sum(1 for r in per_query if pred(r))
        print(f"  {name:<20} NDCG@10={avg_ndcg:.4f}  (FAS applied to {n_apply} queries)")

    # --- Table 6: Summary table for report ---
    print("\n" + "=" * 80)
    print("6. CLEAN SUMMARY TABLE (for report)")
    print("=" * 80)
    print(f"\n| Subset | n | bm25_raw | dense_raw | rrf_fusion | greedy_fas | FAS beat RRF |")
    print("|-------|---|----------|-----------|------------|------------|--------------|")

    def row_str(rows: list, label: str) -> str:
        if not rows:
            return ""
        m = len(rows)
        a = sum(r["ndcg_bm25_raw"] for r in rows) / m
        b = sum(r["ndcg_dense_raw"] for r in rows) / m
        c = sum(r["ndcg_rrf_fusion"] for r in rows) / m
        d = sum(r["ndcg_greedy_fas"] for r in rows) / m
        pct = 100 * sum(1 for r in rows if r["fas_improved_over_rrf"]) / m
        return f"| {label} | {m} | {a:.3f} | {b:.3f} | {c:.3f} | {d:.3f} | {pct:.0f}% |"

    print(row_str(per_query, "Overall"))
    print(row_str(cyclic_rows, "Cyclic only"))
    print(row_str(top25_bew, "High BEW (top 25%)"))
    print(row_str(bottom25_rrf, "Low RRF (bottom 25%)"))

    # Write summary CSV
    summary_path = args.output_dir / f"{args.dataset}_fas_niche_summary_k{args.top_k}_{args.mode}.csv"
    with summary_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subset", "n", "ndcg_bm25", "ndcg_dense", "ndcg_rrf", "ndcg_fas", "pct_fas_beat_rrf"])
        for label, rows in [
            ("overall", per_query),
            ("cyclic_only", cyclic_rows),
            ("high_bew_top25", top25_bew),
            ("low_rrf_bottom25", bottom25_rrf),
        ]:
            if rows:
                m = len(rows)
                w.writerow([
                    label, m,
                    round(sum(r["ndcg_bm25_raw"] for r in rows) / m, 4),
                    round(sum(r["ndcg_dense_raw"] for r in rows) / m, 4),
                    round(sum(r["ndcg_rrf_fusion"] for r in rows) / m, 4),
                    round(sum(r["ndcg_greedy_fas"] for r in rows) / m, 4),
                    round(100 * sum(1 for r in rows if r["fas_improved_over_rrf"]) / m, 1),
                ])
    print(f"\nWrote summary: {summary_path}")

    # --- Strict judgment ---
    print("\n" + "=" * 80)
    print("7. STRICT JUDGMENT")
    print("=" * 80)
    avg_rrf = sum(r["ndcg_rrf_fusion"] for r in per_query) / n
    avg_fas = sum(r["ndcg_greedy_fas"] for r in per_query) / n
    avg_dense = sum(r["ndcg_dense_raw"] for r in per_query) / n
    fas_beat_rrf_overall = avg_fas > avg_rrf
    fas_beat_dense_overall = avg_fas > avg_dense

    print(f"""
  - Overall: FAS ({avg_fas:.4f}) {'beats' if fas_beat_rrf_overall else 'does not beat'} RRF ({avg_rrf:.4f})
  - Overall: FAS ({avg_fas:.4f}) {'beats' if fas_beat_dense_overall else 'does not beat'} dense ({avg_dense:.4f})

  - FAS has a niche: On high-BEW and cyclic queries, FAS sometimes beats RRF.
    Check "FAS beat RRF" % in Tables 2-4. If >50% in a subset, FAS is competitive there.

  - Selective repair: Compare "always" vs "cyclic_only" / "bew>=N".
    If selective yields higher NDCG than "always", selective is stronger.

  - Framing: The story is better as *analysis/repair* — when do multi-scorer
    disagreements create cycles, and does consistency-aware repair help on those
    hard queries? — rather than as a new best reranker that beats RRF/dense globally.
""")


if __name__ == "__main__":
    main()
