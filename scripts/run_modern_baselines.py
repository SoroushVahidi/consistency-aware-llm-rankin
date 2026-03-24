"""
run_modern_baselines.py
=======================
Run modern reranking baselines on the same datasets and candidate pools
used in the consistency-aware ranking paper.

This script produces output files compatible with the existing pipeline:
- Score JSONL files (for cross-encoder and pointwise baselines)
- Pairwise preference JSONL files (for pairwise baselines)
- Per-query CSV and summary CSV (mirroring run_real_experiment.py format)

Usage
-----
::

    # Cross-encoder baseline on SciDocs (fully local, no API needed)
    python scripts/run_modern_baselines.py \\
        --dataset scidocs --baseline cross_encoder --max-queries 50 --top-k 20

    # All graph-aggregation baselines from existing preferences
    python scripts/run_modern_baselines.py \\
        --dataset scidocs --baseline tournament_agg --max-queries 50 --top-k 20

    # LLM baselines in dry-run mode (mock judgments for pipeline validation)
    python scripts/run_modern_baselines.py \\
        --dataset scidocs --baseline llm_pointwise --max-queries 10 --top-k 10 --dry-run

    # All baselines at once
    python scripts/run_modern_baselines.py \\
        --dataset scidocs --baseline all --max-queries 50 --top-k 20

"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


from consistency_ranker.data.query_ids import (
    eligible_query_ids,
    has_usable_eval_labels,
    load_query_ids_file,
)
from consistency_ranker.data.unified_loader import (
    load_dataset_splits,
    preferences_from_qrels,
)
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.pairwise_prefs import Preference

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

BASELINES = (
    "cross_encoder",
    "llm_pointwise",
    "llm_pairwise",
    "llm_listwise",
    "tournament_agg",
)

TOURNAMENT_METHODS = (
    "bt_from_qrels",
    "win_rate_from_qrels",
    "markov_from_qrels",
    "tournament_sort_from_qrels",
)


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


def run_cross_encoder(
    queries_pool, qrels_by_query, documents_by_id, top_k, config_overrides=None
):
    """Run cross-encoder reranking baseline."""
    from rerankers.cross_encoder import CrossEncoderConfig, rerank_query

    config = CrossEncoderConfig(**(config_overrides or {}))

    log.info("Loading cross-encoder model: %s", config.model_name)
    from rerankers.cross_encoder import _get_cross_encoder

    model = _get_cross_encoder(config)

    results = []
    for idx, (qid, query_text, candidate_pool) in enumerate(queries_pool):
        result = rerank_query(
            query_text=query_text,
            candidates=candidate_pool,
            config=config,
            model=model,
        )
        result.query_id = qid
        results.append(result)
        if (idx + 1) % 10 == 0:
            log.info("  Cross-encoder: %d/%d queries", idx + 1, len(queries_pool))

    return results


def run_llm_pointwise(
    queries_pool, qrels_by_query, documents_by_id, top_k, dry_run=True, config_overrides=None
):
    """Run LLM pointwise scoring baseline."""
    from rerankers.llm_pointwise import PointwiseConfig, rerank_query

    cfg = {"dry_run": dry_run, **(config_overrides or {})}
    config = PointwiseConfig(**cfg)

    results = []
    for idx, (qid, query_text, candidate_pool) in enumerate(queries_pool):
        result = rerank_query(qid, query_text, candidate_pool, config=config)
        results.append(result)
        if (idx + 1) % 10 == 0:
            log.info("  LLM pointwise: %d/%d queries", idx + 1, len(queries_pool))

    return results


def run_llm_pairwise(
    queries_pool, qrels_by_query, documents_by_id, top_k, dry_run=True, config_overrides=None
):
    """Run LLM pairwise comparison baseline."""
    from rerankers.llm_pairwise import PairwiseConfig, rerank_query

    cfg = {"dry_run": dry_run, **(config_overrides or {})}
    config = PairwiseConfig(**cfg)

    results = []
    for idx, (qid, query_text, candidate_pool) in enumerate(queries_pool):
        result = rerank_query(qid, query_text, candidate_pool, config=config)
        results.append(result)
        if (idx + 1) % 10 == 0:
            log.info("  LLM pairwise: %d/%d queries", idx + 1, len(queries_pool))

    return results


def run_llm_listwise(
    queries_pool, qrels_by_query, documents_by_id, top_k, dry_run=True, config_overrides=None
):
    """Run LLM listwise (RankGPT-style) reranking baseline."""
    from rerankers.llm_listwise import ListwiseConfig, rerank_query

    cfg = {"dry_run": dry_run, **(config_overrides or {})}
    config = ListwiseConfig(**cfg)

    results = []
    for idx, (qid, query_text, candidate_pool) in enumerate(queries_pool):
        result = rerank_query(qid, query_text, candidate_pool, config=config)
        results.append(result)
        if (idx + 1) % 10 == 0:
            log.info("  LLM listwise: %d/%d queries", idx + 1, len(queries_pool))

    return results


def run_tournament_aggregation(
    queries_pool, qrels_by_query, documents_by_id, top_k, seed=42
):
    """Run tournament aggregation baselines on qrels-derived preferences.

    Uses the same preference source as the main pipeline (qrels) and applies
    different aggregation strategies.
    """
    from consistency_ranker.data.unified_loader import preferences_from_qrels
    from rerankers.tournament_agg import aggregate_preferences

    all_results = {m: [] for m in TOURNAMENT_METHODS}

    for idx, (qid, query_text, candidate_pool) in enumerate(queries_pool):
        qrels = qrels_by_query.get(qid, [])
        if not qrels:
            continue

        schema_prefs = preferences_from_qrels(
            qrels, top_k=top_k, seed=seed, weight_scheme="grade_diff"
        )
        prefs = [
            (p.winner_doc_id, p.loser_doc_id, p.weight) for p in schema_prefs
        ]

        if not prefs:
            continue

        all_ids = [doc_id for doc_id, _ in candidate_pool]

        for method_label, agg_method in [
            ("bt_from_qrels", "bradley_terry"),
            ("win_rate_from_qrels", "win_rate"),
            ("markov_from_qrels", "markov_chain"),
            ("tournament_sort_from_qrels", "tournament_sort"),
        ]:
            extra_kwargs = {}
            if agg_method == "tournament_sort":
                extra_kwargs["seed"] = seed
            result = aggregate_preferences(
                method=agg_method,
                preferences=prefs,
                all_doc_ids=all_ids,
                **extra_kwargs,
            )
            result.query_id = qid
            result.metadata["method"] = method_label
            all_results[method_label].append(result)

        if (idx + 1) % 10 == 0:
            log.info(
                "  Tournament aggregation: %d/%d queries", idx + 1, len(queries_pool)
            )

    return all_results


def evaluate_results(
    results: list,
    method_name: str,
    qrels_by_query: dict,
    graph_cache: dict,
    top_k: int,
    dataset: str,
    preference_source: str,
) -> list[dict]:
    """Evaluate a list of RerankerResults and return per-query metric rows."""
    rows = []
    for result in results:
        qid = result.query_id
        qrels = qrels_by_query.get(qid, [])
        if not qrels:
            continue

        candidate_nodes = set(result.ranked_doc_ids)
        ref_ranking, rel_map = _reference_ranking_for_candidates(qrels, candidate_nodes)

        ranking = result.ranked_doc_ids
        ranking_aligned = [d for d in ranking if d in set(ref_ranking)]

        ndcg = _ndcg_at_k(ranking_aligned, rel_map, k=top_k)
        map_k = _map_at_k(ranking_aligned, rel_map, k=top_k)
        prec_k, rec_k = _precision_recall_at_k(ranking_aligned, rel_map, k=top_k)

        graph = graph_cache.get(qid)
        bew = _backward_edge_weight(graph, ranking) if graph else None
        pic = _pairwise_inconsistency(graph, ranking) if graph else None

        rows.append({
            "dataset": dataset,
            "query_id": qid,
            "method": method_name,
            "preference_source": preference_source,
            "n_candidates": len(ranking),
            "ndcg_at_k": round(ndcg, 6) if ndcg is not None else None,
            "map_at_k": round(map_k, 6) if map_k is not None else None,
            "precision_at_k": round(prec_k, 6) if prec_k is not None else None,
            "recall_at_k": round(rec_k, 6) if rec_k is not None else None,
            "backward_edge_weight": round(bew, 6) if bew is not None else None,
            "pairwise_inconsistency": pic,
        })

    return rows


def build_summary(rows, methods):
    """Aggregate per-query rows into per-method summary."""
    by_method = defaultdict(list)
    for r in rows:
        by_method[r["method"]].append(r)

    summary = []
    for method in methods:
        mrows = by_method.get(method, [])
        if not mrows:
            continue

        def _mean(key):
            vals = [r[key] for r in mrows if r.get(key) is not None]
            return round(sum(vals) / len(vals), 6) if vals else None

        summary.append({
            "method": method,
            "n_queries": len(mrows),
            "ndcg_mean": _mean("ndcg_at_k"),
            "map_mean": _mean("map_at_k"),
            "precision_at_k_mean": _mean("precision_at_k"),
            "recall_at_k_mean": _mean("recall_at_k"),
            "bew_mean": _mean("backward_edge_weight"),
            "pic_mean": _mean("pairwise_inconsistency"),
        })

    return summary


def _write_csv(rows, path):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Run modern reranking baselines.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dataset", default="scidocs",
        help="Dataset: scidocs | fiqa | hotpotqa | bright",
    )
    parser.add_argument(
        "--baseline", default="all",
        help=(
            "Which baseline to run: cross_encoder, llm_pointwise, llm_pairwise, "
            "llm_listwise, tournament_agg, all"
        ),
    )
    parser.add_argument("--max-queries", type=int, default=50)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("outputs/modern_baselines"),
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Use mock LLM judgments (no API key needed).")
    parser.add_argument("--no-llm", action="store_true",
                        help="Skip LLM baselines (pointwise, pairwise, listwise).")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--query-id-file", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    dataset = args.dataset
    output_dir = args.output_dir / dataset
    output_dir.mkdir(parents=True, exist_ok=True)

    baselines_to_run = list(BASELINES) if args.baseline == "all" else [args.baseline]
    if args.no_llm:
        baselines_to_run = [b for b in baselines_to_run if not b.startswith("llm_")]

    print(f"\n{'=' * 65}")
    print(f"  Modern Baselines — {dataset.upper()}")
    print(f"{'=' * 65}")
    print(f"  baselines: {', '.join(baselines_to_run)}")
    print(f"  max_queries: {args.max_queries}")
    print(f"  top_k: {args.top_k}")
    print(f"  dry_run: {args.dry_run}")
    print(f"  output_dir: {output_dir}\n")

    try:
        queries, documents, qrels = load_dataset_splits(dataset)
    except FileNotFoundError as exc:
        log.error("%s\nRun: python scripts/prepare_datasets.py --dataset %s", exc, dataset)
        sys.exit(1)

    qrels_by_query = defaultdict(list)
    for entry in qrels:
        qrels_by_query[entry.query_id].append(entry)

    documents_by_id = {getattr(d, "doc_id", str(i)): d for i, d in enumerate(documents)}

    eligible_qids = eligible_query_ids(qrels)
    if args.query_id_file:
        requested = load_query_ids_file(args.query_id_file)
        sampled_qids = [q for q in requested if q in set(eligible_qids)][:args.max_queries]
    else:
        rng = random.Random(args.seed)
        rng.shuffle(eligible_qids)
        sampled_qids = eligible_qids[:args.max_queries]

    print(f"[1] {len(eligible_qids)} eligible queries; sampled {len(sampled_qids)}")

    query_by_id = {q.query_id: q for q in queries}

    queries_pool = []
    for qid in sampled_qids:
        query = query_by_id.get(qid)
        if query is None:
            continue
        qrels_q = qrels_by_query.get(qid, [])
        if not has_usable_eval_labels(qrels_q):
            continue

        sorted_entries = sorted(qrels_q, key=lambda e: (-e.relevance, e.doc_id))[:args.top_k]
        candidate_pool = []
        for entry in sorted_entries:
            doc = documents_by_id.get(entry.doc_id)
            if doc is None:
                continue
            text = getattr(doc, "text", "") or getattr(doc, "title", "") or str(doc)
            candidate_pool.append((entry.doc_id, text))

        if len(candidate_pool) >= 2:
            query_text = getattr(query, "text", "") or getattr(query, "title", "") or str(query)
            queries_pool.append((qid, query_text, candidate_pool))

    print(f"[2] Built candidate pools for {len(queries_pool)} queries")

    graph_cache = {}
    for qid, _, _ in queries_pool:
        qrels_q = qrels_by_query.get(qid, [])
        schema_prefs = preferences_from_qrels(
            qrels_q, top_k=args.top_k, seed=args.seed, weight_scheme="grade_diff"
        )
        prefs = [
            Preference(winner=p.winner_doc_id, loser=p.loser_doc_id, weight=p.weight)
            for p in schema_prefs
        ]
        if prefs:
            graph_cache[qid] = build_graph(prefs)

    all_rows = []
    all_methods = []

    for baseline in baselines_to_run:
        t0 = time.time()
        print(f"\n--- Running: {baseline} ---")

        if baseline == "cross_encoder":
            results = run_cross_encoder(
                queries_pool, qrels_by_query, documents_by_id, args.top_k
            )
            rows = evaluate_results(
                results, "cross_encoder", qrels_by_query, graph_cache,
                args.top_k, dataset, "cross_encoder",
            )
            all_rows.extend(rows)
            all_methods.append("cross_encoder")

        elif baseline == "llm_pointwise":
            results = run_llm_pointwise(
                queries_pool, qrels_by_query, documents_by_id, args.top_k,
                dry_run=args.dry_run,
            )
            method_label = "llm_pointwise" + ("_mock" if args.dry_run else "")
            rows = evaluate_results(
                results, method_label, qrels_by_query, graph_cache,
                args.top_k, dataset, "llm_pointwise",
            )
            all_rows.extend(rows)
            all_methods.append(method_label)

        elif baseline == "llm_pairwise":
            results = run_llm_pairwise(
                queries_pool, qrels_by_query, documents_by_id, args.top_k,
                dry_run=args.dry_run,
            )
            method_label = "llm_pairwise" + ("_mock" if args.dry_run else "")
            rows = evaluate_results(
                results, method_label, qrels_by_query, graph_cache,
                args.top_k, dataset, "llm_pairwise",
            )
            all_rows.extend(rows)
            all_methods.append(method_label)

        elif baseline == "llm_listwise":
            results = run_llm_listwise(
                queries_pool, qrels_by_query, documents_by_id, args.top_k,
                dry_run=args.dry_run,
            )
            method_label = "llm_listwise" + ("_mock" if args.dry_run else "")
            rows = evaluate_results(
                results, method_label, qrels_by_query, graph_cache,
                args.top_k, dataset, "llm_listwise",
            )
            all_rows.extend(rows)
            all_methods.append(method_label)

        elif baseline == "tournament_agg":
            agg_results = run_tournament_aggregation(
                queries_pool, qrels_by_query, documents_by_id, args.top_k,
                seed=args.seed,
            )
            for method_label, results in agg_results.items():
                rows = evaluate_results(
                    results, method_label, qrels_by_query, graph_cache,
                    args.top_k, dataset, "qrels",
                )
                all_rows.extend(rows)
                all_methods.append(method_label)
        else:
            log.warning("Unknown baseline: %s", baseline)
            continue

        elapsed = time.time() - t0
        print(f"  {baseline} completed in {elapsed:.1f}s")

    if all_rows:
        pq_path = output_dir / f"{dataset}_modern_baselines_per_query.csv"
        _write_csv(all_rows, pq_path)
        print(f"\n[3] Per-query CSV → {pq_path}")

        summary = build_summary(all_rows, all_methods)
        summary_path = output_dir / f"{dataset}_modern_baselines_summary.csv"
        _write_csv(summary, summary_path)
        print(f"[4] Summary CSV → {summary_path}")

        config = {
            "dataset": dataset,
            "baselines": baselines_to_run,
            "max_queries": args.max_queries,
            "top_k": args.top_k,
            "seed": args.seed,
            "dry_run": args.dry_run,
            "n_queries_processed": len(queries_pool),
            "methods": all_methods,
        }
        config_path = output_dir / f"{dataset}_modern_baselines_config.json"
        with config_path.open("w") as fh:
            json.dump(config, fh, indent=2)
        print(f"[5] Config JSON → {config_path}")

        print(f"\n{'=' * 65}")
        print(f"  Summary — {dataset.upper()}")
        print(f"{'=' * 65}")
        for s in summary:
            ndcg = s["ndcg_mean"]
            ndcg_str = f"{ndcg:.4f}" if ndcg is not None else "N/A"
            print(f"  {s['method']:<35} nDCG={ndcg_str}  (n={s['n_queries']})")
        print(f"{'=' * 65}\n")

    else:
        print("\nNo results to report.")


if __name__ == "__main__":
    main()
