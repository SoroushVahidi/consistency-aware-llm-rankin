#!/usr/bin/env python
"""
Generate cross-encoder reranking scores for multi-scorer experiments.

Reranks the union of BM25 and dense top-k candidates per query. Uses
cross-encoder/ms-marco-MiniLM-L-6-v2 (stronger than bi-encoder for reranking).

Output: data/processed/beir/<dataset>/scores/cross_encoder.jsonl

Requires: pip install sentence-transformers

Usage
-----
::
    python scripts/generate_cross_encoder_scores.py --dataset fiqa --top-k 50
    python scripts/generate_cross_encoder_scores.py --dataset scidocs --top-k 50 --max-queries 100
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from consistency_ranker.data.dataset_registry import get_config
from consistency_ranker.data.unified_loader import load_dataset_splits, load_multi_scorer_rankings, save_score_rankings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate cross-encoder reranking scores (union of BM25 + dense).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--dataset", type=str, required=True, choices=["fiqa", "scidocs", "hotpotqa"])
    parser.add_argument("--top-k", type=int, default=50, help="Top-k from each base scorer to union")
    parser.add_argument("--max-queries", type=int, default=None)
    parser.add_argument(
        "--model",
        type=str,
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        help="Cross-encoder model (e.g. ms-marco-MiniLM-L-6-v2 or ms-marco-MiniLM-L-2-v2)",
    )
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        from sentence_transformers import CrossEncoder
    except ImportError:
        print("ERROR: sentence-transformers required. pip install sentence-transformers")
        sys.exit(1)

    cfg = get_config(args.dataset)
    scores_dir = cfg.processed_path / "scores"
    scores_dir.mkdir(parents=True, exist_ok=True)
    out_path = scores_dir / "cross_encoder.jsonl"

    if out_path.exists() and not args.force:
        print(f"[{args.dataset}] Scores exist: {out_path}. Use --force to overwrite.")
        sys.exit(0)

    scorer_paths = {
        "bm25": scores_dir / "bm25.jsonl",
        "dense": scores_dir / "dense.jsonl",
    }
    multi = load_multi_scorer_rankings(scorer_paths)
    if "bm25" not in multi or "dense" not in multi:
        print("ERROR: bm25 and dense scores required. Run generate_bm25_scores and generate_dense_scores first.")
        sys.exit(1)

    queries, documents, _ = load_dataset_splits(args.dataset)
    doc_by_id = {d.doc_id: d for d in documents}
    query_by_id = {q.query_id: q for q in queries}

    qids = [
        qid
        for qid in multi["bm25"]
        if qid in multi["dense"] and qid in query_by_id
    ]
    if args.max_queries:
        qids = qids[: args.max_queries]

    print(f"[{args.dataset}] Loading cross-encoder {args.model}...")
    model = CrossEncoder(args.model)

    rankings: dict[str, list[tuple[str, float]]] = {}
    for i, qid in enumerate(qids):
        if (i + 1) % 20 == 0 or i == 0:
            print(f"  Query {i + 1}/{len(qids)}...")
        q = query_by_id[qid]
        bm25_docs = {d for d, _ in multi["bm25"][qid][: args.top_k]}
        dense_docs = {d for d, _ in multi["dense"][qid][: args.top_k]}
        candidate_ids = sorted(bm25_docs | dense_docs)
        if not candidate_ids:
            continue
        pairs = []
        for doc_id in candidate_ids:
            if doc_id not in doc_by_id:
                continue
            text = doc_by_id[doc_id].text
            if len(text) > 512:
                text = text[:512] + "..."
            pairs.append((q.text, text))
        if len(pairs) != len(candidate_ids):
            continue
        scores = model.predict(pairs, batch_size=args.batch_size, show_progress_bar=False)
        order = sorted(range(len(candidate_ids)), key=lambda j: float(scores[j]), reverse=True)
        rankings[qid] = [(candidate_ids[j], float(scores[j])) for j in order]

    save_score_rankings(rankings, out_path)
    print(f"[{args.dataset}] Wrote {len(rankings)} queries → {out_path}")


if __name__ == "__main__":
    main()
