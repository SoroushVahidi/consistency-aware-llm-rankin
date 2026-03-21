#!/usr/bin/env python
"""
generate_proxy_datasets.py
==========================
Generate realistic proxy datasets for SciDocs, FiQA, HotpotQA, and BRIGHT
when the real HuggingFace datasets are not accessible (e.g., offline/sandboxed
environments).

Each dataset is generated to faithfully reflect the published characteristics
of the real dataset:

- **SciDocs**: citation-recommendation benchmark.  ~500 queries, ~25 K-document
  corpus, binary (0/1) relevance, ~3–5 relevant docs per query.
- **FiQA-2018**: financial question answering.  ~648 queries, ~57 K-document
  corpus, graded (0–3) relevance, ~5–10 relevant docs per query.
- **HotpotQA**: multi-hop question answering.  ~7 400 validation examples
  (limited here to ``--max-queries``), exactly 10 supporting-paragraph
  candidates per query, binary relevance, 2–3 supporting docs per query.
- **BRIGHT**: reasoning-intensive retrieval.  ~100 queries, graded (0–2)
  relevance, 3–8 relevant docs per query.

Outputs (matching the structure expected by ``prepare_datasets.py``):

    data/raw/<dataset>/queries.jsonl
    data/raw/<dataset>/documents.jsonl
    data/raw/<dataset>/qrels.jsonl

Usage
-----
::

    # Generate all datasets (defaults)
    python scripts/generate_proxy_datasets.py

    # Generate a single dataset
    python scripts/generate_proxy_datasets.py --dataset scidocs

    # Increase size for a more thorough run
    python scripts/generate_proxy_datasets.py --dataset fiqa --max-queries 648

Options
-------
--dataset       Dataset to generate (scidocs | fiqa | hotpotqa | bright | all)
--max-queries   Override the default number of queries
--seed          Random seed (default: 42)
--force         Overwrite existing files
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from consistency_ranker.data.dataset_registry import DATASET_NAMES, get_config

# ---------------------------------------------------------------------------
# Topic/vocabulary pools for text generation
# ---------------------------------------------------------------------------

_SCIDOCS_TOPICS = [
    "neural network architecture", "knowledge graph embedding", "information retrieval",
    "natural language processing", "graph neural networks", "transformer models",
    "question answering systems", "document summarisation", "named entity recognition",
    "relation extraction", "semantic similarity", "text classification",
    "machine translation", "dialogue systems", "coreference resolution",
    "dependency parsing", "word embeddings", "language model pretraining",
    "few-shot learning", "zero-shot transfer",
]

_FIQA_TOPICS = [
    "portfolio diversification", "stock market volatility", "bond yield curve",
    "dividend reinvestment", "index fund strategy", "tax-loss harvesting",
    "retirement planning", "risk-adjusted returns", "asset allocation",
    "options trading strategy", "currency hedging", "inflation protection",
    "real estate investment", "corporate debt", "central bank policy",
    "earnings per share", "capital gains tax", "mutual fund fees",
    "exchange-traded fund", "short selling mechanics",
]

_HOTPOTQA_TOPICS = [
    "historical event", "scientific discovery", "cultural landmark",
    "literary work", "political movement", "geographical feature",
    "technological invention", "biographical fact", "economic concept",
    "philosophical idea",
]

_BRIGHT_TOPICS = [
    "causal mechanism", "empirical evidence", "theoretical framework",
    "experimental design", "statistical inference", "counterfactual reasoning",
    "analogical reasoning", "deductive argument", "inductive generalisation",
    "abductive hypothesis",
]

_VERBS = ["describes", "analyses", "investigates", "proposes", "evaluates",
          "reviews", "studies", "extends", "applies", "introduces"]
_ADJECTIVES = ["novel", "improved", "efficient", "scalable", "robust",
               "systematic", "comprehensive", "unified", "adaptive", "deep"]
_NOUNS = ["approach", "framework", "method", "model", "system",
          "technique", "algorithm", "architecture", "benchmark", "dataset"]


def _rng_text(rng: random.Random, n_sentences: int, pool: list[str]) -> str:
    """Generate placeholder text with topic-specific vocabulary."""
    sentences = []
    for _ in range(n_sentences):
        topic = rng.choice(pool)
        verb = rng.choice(_VERBS)
        adj = rng.choice(_ADJECTIVES)
        noun = rng.choice(_NOUNS)
        sentences.append(
            f"This work {verb} a {adj} {noun} for {topic}."
        )
    return " ".join(sentences)


def _stable_id(prefix: str, idx: int) -> str:
    """Generate a short stable identifier."""
    return f"{prefix}_{idx:06d}"


def _write_jsonl(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    print(f"    Wrote {len(records):,} records → {path}")


# ---------------------------------------------------------------------------
# Dataset-specific generators
# ---------------------------------------------------------------------------


@dataclass
class _GenSpec:
    """Parameters that control the size and characteristics of one dataset."""
    name: str
    raw_path_key: str  # the key used in dataset_registry (raw_path)
    n_queries: int
    n_corpus: int
    n_relevant_range: tuple[int, int]   # (min, max) relevant docs per query
    relevance_max: int                  # maximum relevance grade (1 = binary)
    n_candidates_per_query: int | None  # if set, exactly this many candidates
    topic_pool: list[str]
    query_prefix: str
    doc_prefix: str


_SPECS: dict[str, _GenSpec] = {
    "scidocs": _GenSpec(
        name="scidocs",
        raw_path_key="scidocs",
        n_queries=500,
        n_corpus=25_000,
        n_relevant_range=(3, 5),
        relevance_max=1,
        n_candidates_per_query=None,
        topic_pool=_SCIDOCS_TOPICS,
        query_prefix="q_sci",
        doc_prefix="d_sci",
    ),
    "fiqa": _GenSpec(
        name="fiqa",
        raw_path_key="fiqa",
        n_queries=648,
        n_corpus=57_000,
        n_relevant_range=(5, 10),
        relevance_max=3,
        n_candidates_per_query=None,
        topic_pool=_FIQA_TOPICS,
        query_prefix="q_fiqa",
        doc_prefix="d_fiqa",
    ),
    "hotpotqa": _GenSpec(
        name="hotpotqa",
        raw_path_key="hotpotqa",
        n_queries=500,
        n_corpus=0,   # corpus is query-local for HotpotQA
        n_relevant_range=(2, 3),
        relevance_max=1,
        n_candidates_per_query=10,
        topic_pool=_HOTPOTQA_TOPICS,
        query_prefix="q_hop",
        doc_prefix="d_hop",
    ),
    "bright": _GenSpec(
        name="bright",
        raw_path_key="bright",
        n_queries=100,
        n_corpus=5_000,
        n_relevant_range=(3, 8),
        relevance_max=2,
        n_candidates_per_query=None,
        topic_pool=_BRIGHT_TOPICS,
        query_prefix="q_bright",
        doc_prefix="d_bright",
    ),
}


def _generate_dataset(
    spec: _GenSpec,
    raw_path: Path,
    max_queries: int | None,
    seed: int,
    force: bool,
) -> None:
    """Generate proxy JSONL files for one dataset."""
    n_queries = min(spec.n_queries, max_queries) if max_queries else spec.n_queries
    rng = random.Random(seed)

    queries_path = raw_path / "queries.jsonl"
    docs_path = raw_path / "documents.jsonl"
    qrels_path = raw_path / "qrels.jsonl"

    if queries_path.exists() and docs_path.exists() and qrels_path.exists() and not force:
        print(
            f"[{spec.name}] Files already exist in {raw_path}. "
            "Skipping (use --force to regenerate)."
        )
        return

    raw_path.mkdir(parents=True, exist_ok=True)
    print(f"[{spec.name}] Generating proxy data ({n_queries} queries) …")

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    queries: list[dict] = []
    for i in range(n_queries):
        topic = rng.choice(spec.topic_pool)
        qid = _stable_id(spec.query_prefix, i)
        text = f"What are the key aspects of {topic}?"
        queries.append({"query_id": qid, "text": text, "metadata": {}})

    # ------------------------------------------------------------------
    # Documents (corpus or per-query for HotpotQA)
    # ------------------------------------------------------------------
    documents: list[dict] = []
    qrels: list[dict] = []

    if spec.n_candidates_per_query is not None:
        # HotpotQA-style: each query has its own pool of candidates
        n_cands = spec.n_candidates_per_query
        n_relevant_min, n_relevant_max = spec.n_relevant_range

        for q_idx, q in enumerate(queries):
            qid = q["query_id"]
            # Create n_cands documents for this query
            cand_docs = []
            for c in range(n_cands):
                did = _stable_id(spec.doc_prefix, q_idx * n_cands + c)
                text = _rng_text(rng, rng.randint(2, 5), spec.topic_pool)
                documents.append({"doc_id": did, "text": text, "title": f"Doc {did}", "metadata": {}})
                cand_docs.append(did)

            n_rel = rng.randint(n_relevant_min, min(n_relevant_max, n_cands - 1))
            relevant = rng.sample(cand_docs, n_rel)
            relevant_set = set(relevant)

            for did in cand_docs:
                relevance = spec.relevance_max if did in relevant_set else 0
                qrels.append({
                    "query_id": qid,
                    "doc_id": did,
                    "relevance": relevance,
                })

    else:
        # Standard BEIR-style: shared corpus with per-query relevance
        n_corpus = spec.n_corpus
        n_relevant_min, n_relevant_max = spec.n_relevant_range

        print(f"[{spec.name}]   Building corpus ({n_corpus:,} docs) …")
        for d in range(n_corpus):
            did = _stable_id(spec.doc_prefix, d)
            text = _rng_text(rng, rng.randint(3, 8), spec.topic_pool)
            title = f"{rng.choice(_ADJECTIVES).title()} {rng.choice(_NOUNS).title()} on {rng.choice(spec.topic_pool)}"
            documents.append({"doc_id": did, "text": text, "title": title, "metadata": {}})

        doc_ids = [d["doc_id"] for d in documents]

        print(f"[{spec.name}]   Assigning relevance for {n_queries} queries …")
        for q in queries:
            qid = q["query_id"]
            n_rel = rng.randint(n_relevant_min, n_relevant_max)

            # Assign a pool of ~50 candidate docs per query; some are relevant
            pool_size = min(50, n_corpus)
            pool = rng.sample(doc_ids, pool_size)
            relevant = rng.sample(pool, min(n_rel, pool_size))
            relevant_set = set(relevant)

            for did in pool:
                if did in relevant_set:
                    # For multi-grade datasets, assign varied grades
                    if spec.relevance_max > 1:
                        relevance = rng.randint(1, spec.relevance_max)
                    else:
                        relevance = 1
                else:
                    relevance = 0
                qrels.append({
                    "query_id": qid,
                    "doc_id": did,
                    "relevance": relevance,
                })

    # ------------------------------------------------------------------
    # Write JSONL
    # ------------------------------------------------------------------
    _write_jsonl(queries, queries_path)
    _write_jsonl(documents, docs_path)
    _write_jsonl(qrels, qrels_path)

    n_rel_total = sum(1 for q in qrels if q["relevance"] > 0)
    print(
        f"[{spec.name}] Done. "
        f"{len(queries)} queries, {len(documents):,} docs, "
        f"{len(qrels):,} qrel entries ({n_rel_total:,} relevant)"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate realistic proxy datasets for offline/sandboxed experiments.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dataset",
        choices=DATASET_NAMES + ["all"],
        default="all",
        help="Dataset to generate (default: all)",
    )
    parser.add_argument(
        "--max-queries",
        type=int,
        default=None,
        help="Override the default number of queries per dataset",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files",
    )
    args = parser.parse_args(argv)

    targets = DATASET_NAMES if args.dataset == "all" else [args.dataset]

    for name in targets:
        print(f"\n{'='*60}")
        print(f"  Generating proxy dataset: {name}")
        print(f"{'='*60}")
        spec = _SPECS[name]
        cfg = get_config(name)
        _generate_dataset(
            spec=spec,
            raw_path=cfg.raw_path,
            max_queries=args.max_queries,
            seed=args.seed,
            force=args.force,
        )

    print("\nAll requested proxy datasets generated.")


if __name__ == "__main__":
    main()
