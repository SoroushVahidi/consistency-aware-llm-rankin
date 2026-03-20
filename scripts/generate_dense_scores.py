#!/usr/bin/env python
"""
generate_dense_scores.py
========================
Generate dense retriever score files using sentence-transformers.

Uses all-MiniLM-L6-v2 (~80MB), a lightweight embedding model. Output format
matches CandidateRanking JSONL (same as bm25.jsonl).

Requires: pip install sentence-transformers

Output: data/processed/beir/<dataset>/scores/dense.jsonl

Usage
-----
::

    python scripts/generate_dense_scores.py --dataset fiqa --top-k 100
    python scripts/generate_dense_scores.py --dataset scidocs --top-k 100 --max-queries 200
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from consistency_ranker.data.dataset_registry import get_config
from consistency_ranker.data.unified_loader import load_dataset_splits, save_score_rankings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate dense retriever scores for fiqa/scidocs using sentence-transformers.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        choices=["fiqa", "scidocs", "hotpotqa"],
        help="Dataset to score.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=100,
        help="Number of top candidates per query to write.",
    )
    parser.add_argument(
        "--max-queries",
        type=int,
        default=None,
        help="Limit number of queries (for quick testing).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Sentence-transformers model name.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Batch size for encoding (lower if OOM).",
    )
    parser.add_argument(
        "--rerank-from",
        type=str,
        default=None,
        help="If set (e.g. bm25), rerank that scorer's top-k instead of full corpus. Much faster.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing scores file.",
    )
    args = parser.parse_args()

    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
    except ImportError:
        print(
            "ERROR: sentence-transformers is required. Install with:\n"
            "  pip install sentence-transformers\n"
        )
        sys.exit(1)

    cfg = get_config(args.dataset)
    scores_dir = cfg.processed_path / "scores"
    scores_dir.mkdir(parents=True, exist_ok=True)
    out_path = scores_dir / "dense.jsonl"

    if out_path.exists() and not args.force:
        print(f"[{args.dataset}] Scores file exists: {out_path}. Use --force to overwrite.")
        sys.exit(0)

    print(f"[{args.dataset}] Loading queries and documents...")
    queries, documents, _ = load_dataset_splits(args.dataset)
    doc_by_id = {d.doc_id: d for d in documents}
    query_list = queries[: args.max_queries] if args.max_queries else queries
    query_ids = [q.query_id for q in query_list]

    # HotpotQA: documents are per-query; always use per-query scoring (no global corpus)
    if args.dataset == "hotpotqa":
        args.rerank_from = None  # Ignore rerank_from; we score per-query docs

    # Option: rerank from BM25 (fast) vs full corpus (slow)
    if args.rerank_from:
        from consistency_ranker.data.unified_loader import load_score_rankings
        base_path = scores_dir / f"{args.rerank_from}.jsonl"
        if not base_path.exists():
            print(f"ERROR: {base_path} not found. Run generate_bm25_scores first.")
            sys.exit(1)
        base_rankings = load_score_rankings(base_path)
        print(f"[{args.dataset}] Reranking from {args.rerank_from} (top-{args.top_k} per query)...")
    else:
        base_rankings = None

    print(f"[{args.dataset}] Loading model {args.model}...")
    model = SentenceTransformer(args.model)

    rankings: dict[str, list[tuple[str, float]]] = {}

    if base_rankings:
        # Rerank: for each query, embed query + candidate docs, score, sort
        for i, q in enumerate(query_list):
            if (i + 1) % 20 == 0 or i == 0:
                print(f"  Query {i + 1}/{len(query_list)}...")
            if q.query_id not in base_rankings:
                continue
            candidates = base_rankings[q.query_id][: args.top_k]
            if not candidates:
                continue
            doc_ids = [d for d, _ in candidates]
            doc_texts = []
            for d in doc_ids:
                if d not in doc_by_id:
                    break
                t = doc_by_id[d].text
                # Truncate long docs (sentence-transformers has 512 token limit)
                if len(t) > 4000:
                    t = t[:4000] + "..."
                doc_texts.append(t)
            if len(doc_texts) != len(doc_ids):
                continue
            query_emb = model.encode([q.text], convert_to_tensor=False)[0]
            doc_embs = model.encode(doc_texts, batch_size=min(32, len(doc_texts)), convert_to_tensor=False)
            qn = query_emb / (np.linalg.norm(query_emb) + 1e-9)
            dn = doc_embs / (np.linalg.norm(doc_embs, axis=1, keepdims=True) + 1e-9)
            scores = np.dot(dn, qn)
            order = np.argsort(scores)[::-1]
            rankings[q.query_id] = [(doc_ids[j], float(scores[j])) for j in order]
    elif args.dataset == "hotpotqa":
        # HotpotQA: per-query documents (10 per query). Score each query against its docs.
        from collections import defaultdict

        docs_by_query: dict[str, list] = defaultdict(list)
        for d in documents:
            qid = d.metadata.get("query_id")
            if qid:
                docs_by_query[qid].append(d)

        for i, q in enumerate(query_list):
            if (i + 1) % 50 == 0 or i == 0:
                print(f"  Query {i + 1}/{len(query_list)}...")
            qdocs = docs_by_query.get(q.query_id, [])
            if not qdocs:
                continue
            doc_ids = [d.doc_id for d in qdocs]
            doc_texts = [d.text[:4000] + "..." if len(d.text) > 4000 else d.text for d in qdocs]
            query_emb = model.encode([q.text], convert_to_tensor=False)[0]
            doc_embs = model.encode(doc_texts, batch_size=min(32, len(doc_texts)), convert_to_tensor=False)
            qn = query_emb / (np.linalg.norm(query_emb) + 1e-9)
            dn = doc_embs / (np.linalg.norm(doc_embs, axis=1, keepdims=True) + 1e-9)
            scores = np.dot(dn, qn)
            order = np.argsort(scores)[::-1][: args.top_k]
            rankings[q.query_id] = [(doc_ids[j], float(scores[j])) for j in order]
    else:
        # Full corpus retrieval (BEIR-style)
        doc_ids = [d.doc_id for d in documents]
        corpus_texts = [d.text for d in documents]
        query_texts = [q.text for q in query_list]
        print(f"[{args.dataset}] Encoding corpus ({len(corpus_texts)} docs)...")
        corpus_embeddings = model.encode(
            corpus_texts, batch_size=args.batch_size, show_progress_bar=True, convert_to_tensor=False
        )
        print(f"[{args.dataset}] Encoding queries ({len(query_texts)} queries)...")
        query_embeddings = model.encode(
            query_texts, batch_size=args.batch_size, show_progress_bar=True, convert_to_tensor=False
        )
        corpus_norm = corpus_embeddings / (np.linalg.norm(corpus_embeddings, axis=1, keepdims=True) + 1e-9)
        query_norm = query_embeddings / (np.linalg.norm(query_embeddings, axis=1, keepdims=True) + 1e-9)
        sim_matrix = np.dot(query_norm, corpus_norm.T)
        for i, q in enumerate(query_list):
            scores = sim_matrix[i]
            top_indices = np.argsort(scores)[::-1][: args.top_k]
            rankings[q.query_id] = [(doc_ids[idx], float(scores[idx])) for idx in top_indices]

    save_score_rankings(rankings, out_path)
    print(f"[{args.dataset}] Wrote {len(rankings)} queries → {out_path}")
    print(f"\nRun multi-scorer experiment with:")
    print(f"  python scripts/run_real_experiment.py --dataset {args.dataset} --preference-source multi_scores \\")
    print(f"    --scorers bm25,dense --multi-score-weight-mode summed_margin --max-queries 50")


if __name__ == "__main__":
    main()
