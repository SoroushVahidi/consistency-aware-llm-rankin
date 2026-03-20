#!/usr/bin/env python
"""
generate_bm25_scores.py
========================
Generate BM25 score files for fiqa and scidocs in CandidateRanking JSONL format.

Requires: pip install rank-bm25

Output: data/processed/<dataset>/scores/bm25.jsonl

Usage
-----
::

    python scripts/generate_bm25_scores.py --dataset fiqa --top-k 100
    python scripts/generate_bm25_scores.py --dataset scidocs --top-k 100 --max-queries 200

Then run the real experiment with:
    python scripts/run_real_experiment.py --dataset fiqa --preference-source scores --scorer bm25
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from consistency_ranker.data.dataset_registry import get_config
from consistency_ranker.data.unified_loader import load_dataset_splits, save_score_rankings


def _tokenize(text: str) -> list[str]:
    """Simple whitespace tokenizer with lowercasing."""
    return re.sub(r"[^\w\s]", " ", text.lower()).split()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate BM25 scores for fiqa/scidocs in CandidateRanking JSONL format.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        choices=["fiqa", "scidocs"],
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
        "--force",
        action="store_true",
        help="Overwrite existing scores file.",
    )
    args = parser.parse_args()

    try:
        from rank_bm25 import BM25Okapi
        import numpy as np
    except ImportError as exc:
        print(
            "ERROR: rank-bm25 is required. Install with:\n"
            "  pip install rank-bm25 numpy\n"
        )
        sys.exit(1)

    cfg = get_config(args.dataset)
    processed = cfg.processed_path
    scores_dir = processed / "scores"
    out_path = scores_dir / "bm25.jsonl"

    if out_path.exists() and not args.force:
        print(f"[{args.dataset}] Scores file exists: {out_path}. Use --force to overwrite.")
        sys.exit(0)

    # Load dataset
    print(f"[{args.dataset}] Loading queries and documents...")
    queries, documents, _ = load_dataset_splits(args.dataset)

    doc_by_id = {d.doc_id: d for d in documents}
    doc_ids = [d.doc_id for d in documents]
    corpus_texts = [d.text for d in documents]
    tokenized_corpus = [_tokenize(t) for t in corpus_texts]

    print(f"[{args.dataset}] Building BM25 index ({len(documents)} docs)...")
    bm25 = BM25Okapi(tokenized_corpus)

    # Process queries
    query_list = queries[: args.max_queries] if args.max_queries else queries
    rankings: dict[str, list[tuple[str, float]]] = {}

    for i, q in enumerate(query_list):
        if (i + 1) % 50 == 0 or i == 0:
            print(f"  Processing query {i + 1}/{len(query_list)}...")
        tokenized_query = _tokenize(q.text)
        scores = bm25.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][: args.top_k]
        candidates = [
            (doc_ids[idx], float(scores[idx]))
            for idx in top_indices
            if scores[idx] > 0
        ]
        if not candidates:
            candidates = [(doc_ids[i], 0.0) for i in top_indices[: args.top_k]]
        rankings[q.query_id] = candidates

    save_score_rankings(rankings, out_path)
    print(f"[{args.dataset}] Wrote {len(rankings)} queries → {out_path}")
    print(f"\nRun experiment with:")
    print(f"  python scripts/run_real_experiment.py --dataset {args.dataset} --preference-source scores --scorer bm25")


if __name__ == "__main__":
    main()
