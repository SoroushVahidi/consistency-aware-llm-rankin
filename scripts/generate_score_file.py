"""
generate_score_file.py
======================
Generate external score JSONL files for real-signal ranking experiments.

Output schema (one row per query-document score):
{"query_id":"...","doc_id":"...","score":1.23,"ranker":"bm25"}
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

# Allow running as `python scripts/generate_score_file.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from consistency_ranker.data.query_ids import (  # noqa: E402
    eligible_query_ids,
    load_query_ids_file,
    sample_query_ids,
    save_query_ids_file,
)
from consistency_ranker.data.dataset_registry import DATASET_NAMES  # noqa: E402
from consistency_ranker.data.unified_loader import load_dataset_splits  # noqa: E402

TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _document_text(doc) -> str:
    if doc.title:
        return f"{doc.title}\n{doc.text}"
    return doc.text


class _LexicalIndex:
    def __init__(self, documents: list) -> None:
        self.doc_ids: list[str] = []
        self.doc_lengths: list[int] = []
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        self.df: dict[str, int] = {}
        self.sorted_doc_indices = []

        for idx, doc in enumerate(documents):
            self.doc_ids.append(doc.doc_id)
            counts = Counter(_tokenize(_document_text(doc)))
            doc_len = sum(counts.values())
            self.doc_lengths.append(doc_len)
            for term, tf in counts.items():
                self.postings[term].append((idx, tf))

        self.n_docs = len(self.doc_ids)
        self.avgdl = (
            sum(self.doc_lengths) / self.n_docs
            if self.n_docs > 0 else 0.0
        )
        self.df = {term: len(rows) for term, rows in self.postings.items()}
        self.sorted_doc_indices = sorted(range(self.n_docs), key=lambda i: self.doc_ids[i])

    def _top_with_fallback(
        self,
        scores: dict[int, float],
        top_n: int,
    ) -> list[tuple[str, float]]:
        ranked = sorted(scores.items(), key=lambda x: (-x[1], self.doc_ids[x[0]]))
        out = [(self.doc_ids[i], float(s)) for i, s in ranked[:top_n]]
        if len(out) >= top_n:
            return out
        seen = {doc_id for doc_id, _ in out}
        for i in self.sorted_doc_indices:
            doc_id = self.doc_ids[i]
            if doc_id in seen:
                continue
            out.append((doc_id, 0.0))
            if len(out) >= top_n:
                break
        return out


class BM25Ranker:
    def __init__(self, documents: list, k1: float = 1.5, b: float = 0.75) -> None:
        self.index = _LexicalIndex(documents)
        self.k1 = k1
        self.b = b

    def top_docs(self, query_text: str, top_n: int) -> list[tuple[str, float]]:
        q_counts = Counter(_tokenize(query_text))
        if not q_counts:
            return self.index._top_with_fallback({}, top_n)

        scores: dict[int, float] = defaultdict(float)
        for term, qtf in q_counts.items():
            postings = self.index.postings.get(term)
            if not postings:
                continue
            df = self.index.df[term]
            idf = math.log((self.index.n_docs - df + 0.5) / (df + 0.5) + 1.0)
            for doc_idx, tf in postings:
                dl = self.index.doc_lengths[doc_idx]
                denom = tf + self.k1 * (1.0 - self.b + self.b * dl / max(self.index.avgdl, 1e-9))
                scores[doc_idx] += idf * (tf * (self.k1 + 1.0) / denom) * qtf
        return self.index._top_with_fallback(scores, top_n)


class TfidfRanker:
    def __init__(self, documents: list) -> None:
        self.index = _LexicalIndex(documents)
        self.idf: dict[str, float] = {
            term: math.log((self.index.n_docs + 1.0) / (df + 1.0)) + 1.0
            for term, df in self.index.df.items()
        }
        self.doc_norms = self._build_doc_norms()

    def _build_doc_norms(self) -> list[float]:
        sq = [0.0 for _ in range(self.index.n_docs)]
        for term, postings in self.index.postings.items():
            idf = self.idf[term]
            for doc_idx, tf in postings:
                w = (1.0 + math.log(tf)) * idf
                sq[doc_idx] += w * w
        return [math.sqrt(v) if v > 0 else 1.0 for v in sq]

    def top_docs(self, query_text: str, top_n: int) -> list[tuple[str, float]]:
        q_counts = Counter(_tokenize(query_text))
        if not q_counts:
            return self.index._top_with_fallback({}, top_n)

        q_weights: dict[str, float] = {}
        q_sq = 0.0
        for term, qtf in q_counts.items():
            idf = self.idf.get(term)
            if idf is None:
                continue
            wq = (1.0 + math.log(qtf)) * idf
            q_weights[term] = wq
            q_sq += wq * wq
        q_norm = math.sqrt(q_sq) if q_sq > 0 else 1.0

        scores: dict[int, float] = defaultdict(float)
        for term, wq in q_weights.items():
            for doc_idx, tf in self.index.postings.get(term, []):
                wd = (1.0 + math.log(tf)) * self.idf[term]
                scores[doc_idx] += wq * wd

        for doc_idx in list(scores.keys()):
            scores[doc_idx] /= (self.doc_norms[doc_idx] * q_norm)

        return self.index._top_with_fallback(scores, top_n)


class MiniLMRanker:
    def __init__(self, documents: list) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "MiniLM ranker requires sentence-transformers. "
                "Install with: python3 -m pip install sentence-transformers"
            ) from exc

        self.doc_ids = [doc.doc_id for doc in documents]
        texts = [_document_text(doc) for doc in documents]
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        emb = self.model.encode(
            texts,
            batch_size=64,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        self.doc_embeddings = np.asarray(emb, dtype=np.float32)

    def top_docs(self, query_text: str, top_n: int) -> list[tuple[str, float]]:
        if not self.doc_ids:
            return []
        q_emb = self.model.encode(
            [query_text],
            show_progress_bar=False,
            normalize_embeddings=True,
        )[0]
        q_emb = np.asarray(q_emb, dtype=np.float32)
        scores = self.doc_embeddings @ q_emb
        k = min(top_n, len(self.doc_ids))
        if k <= 0:
            return []
        if k == len(self.doc_ids):
            top_idx = np.arange(len(self.doc_ids))
        else:
            top_idx = np.argpartition(-scores, k - 1)[:k]
        ordered = sorted(top_idx.tolist(), key=lambda i: (-float(scores[i]), self.doc_ids[i]))
        return [(self.doc_ids[i], float(scores[i])) for i in ordered]


def _build_ranker(name: str, documents: list):
    if name == "bm25":
        return BM25Ranker(documents)
    if name == "tfidf":
        return TfidfRanker(documents)
    if name == "minilm":
        return MiniLMRanker(documents)
    raise ValueError(f"Unknown ranker {name!r}")


def _resolve_query_ids(
    *,
    qrels: list,
    max_queries: int,
    seed: int,
    query_id_file: Path | None,
) -> tuple[list[str], int]:
    eligible = eligible_query_ids(qrels)
    eligible_set = set(eligible)

    if query_id_file is None:
        return sample_query_ids(eligible, max_queries=max_queries, seed=seed), len(eligible)

    if query_id_file.exists():
        requested = load_query_ids_file(query_id_file)
        selected = [qid for qid in requested if qid in eligible_set][:max_queries]
        return selected, len(eligible)

    selected = sample_query_ids(eligible, max_queries=max_queries, seed=seed)
    save_query_ids_file(selected, query_id_file)
    return selected, len(eligible)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate external score JSONL for real preference-source experiments.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        choices=sorted(DATASET_NAMES),
        help="Registered dataset id (see dataset_registry).",
    )
    parser.add_argument(
        "--ranker",
        type=str,
        required=True,
        choices=["bm25", "tfidf", "minilm"],
    )
    parser.add_argument("--max-queries", type=int, default=50)
    parser.add_argument("--top-n", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--query-id-file",
        type=Path,
        default=None,
        help=(
            "Optional TXT/JSONL query-id file. If it exists, query ids are read "
            "from it. If it does not exist, sampled ids are written to it."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    queries, documents, qrels = load_dataset_splits(args.dataset)
    query_by_id = {q.query_id: q for q in queries}

    sampled_qids, n_eligible = _resolve_query_ids(
        qrels=qrels,
        max_queries=args.max_queries,
        seed=args.seed,
        query_id_file=args.query_id_file,
    )

    ranker = _build_ranker(args.ranker, documents)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    with args.output.open("w", encoding="utf-8") as fh:
        for qid in sampled_qids:
            query = query_by_id.get(qid)
            if query is None:
                continue
            for doc_id, score in ranker.top_docs(query.text, top_n=args.top_n):
                row = {
                    "query_id": qid,
                    "doc_id": doc_id,
                    "score": float(score),
                    "ranker": args.ranker,
                }
                fh.write(json.dumps(row) + "\n")
                n_rows += 1

    print(f"[generate_score_file] dataset={args.dataset}")
    print(f"[generate_score_file] ranker={args.ranker}")
    print(f"[generate_score_file] eligible_queries={n_eligible}")
    print(f"[generate_score_file] sampled_queries={len(sampled_qids)}")
    print(f"[generate_score_file] wrote_rows={n_rows}")
    print(f"[generate_score_file] output={args.output}")
    if args.query_id_file is not None:
        print(f"[generate_score_file] query_id_file={args.query_id_file}")


if __name__ == "__main__":
    main()
