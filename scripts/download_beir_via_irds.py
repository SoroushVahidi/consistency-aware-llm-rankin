#!/usr/bin/env python
"""
download_beir_via_irds.py
=========================
Download BEIR datasets (fiqa, scidocs) via ir_datasets when HuggingFace fails.

Usage: pip install ir-datasets && python scripts/download_beir_via_irds.py --dataset fiqa
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from consistency_ranker.data.dataset_registry import get_config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["fiqa", "scidocs"], required=True)
    parser.add_argument("--max-queries", type=int, default=None)
    parser.add_argument("--max-docs", type=int, default=None)
    args = parser.parse_args()

    try:
        import ir_datasets
    except ImportError:
        print("Install: pip install ir-datasets")
        sys.exit(1)

    # scidocs has no test split, fiqa has test
    irds_name = f"beir/{args.dataset}/test" if args.dataset == "fiqa" else f"beir/{args.dataset}"
    cfg = get_config(args.dataset)
    raw_path = cfg.raw_path
    raw_path.mkdir(parents=True, exist_ok=True)

    print(f"Loading {irds_name} via ir_datasets...")
    ds = ir_datasets.load(irds_name)

    queries = []
    for q in ds.queries_iter():
        queries.append({"query_id": str(q.query_id), "text": q.text})
        if args.max_queries and len(queries) >= args.max_queries:
            break

    docs = []
    doc_ids = set()
    for d in ds.docs_iter():
        if d.doc_id in doc_ids:
            continue
        doc_ids.add(d.doc_id)
        docs.append({"doc_id": str(d.doc_id), "text": d.text, "title": getattr(d, "title", "") or ""})
        if args.max_docs and len(docs) >= args.max_docs:
            break

    query_ids = {q["query_id"] for q in queries}
    doc_ids_set = {d["doc_id"] for d in docs}

    qrels = []
    for r in ds.qrels_iter():
        qid, did = str(r.query_id), str(r.doc_id)
        if qid in query_ids and did in doc_ids_set:
            qrels.append({"query_id": qid, "doc_id": did, "relevance": int(r.relevance)})

    def write_jsonl(records, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

    write_jsonl(queries, raw_path / "queries.jsonl")
    write_jsonl(docs, raw_path / "documents.jsonl")
    write_jsonl(qrels, raw_path / "qrels.jsonl")
    print(f"Wrote {len(queries)} queries, {len(docs)} docs, {len(qrels)} qrels → {raw_path}")


if __name__ == "__main__":
    main()
