#!/usr/bin/env python
"""
Prepare HotpotQA distractor dev into the repository's standard processed format.

Reads: data/raw/hotpotqa/hotpot_dev_distractor_v1.json
Writes: data/processed/hotpotqa/{queries.jsonl, documents.jsonl, qrels.jsonl}

Document IDs: <query_id>::<title> (deterministic, unique per query)
Qrels: supporting-fact paragraphs marked relevant (relevance=1)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from consistency_ranker.data.schema import Document, QrelEntry, Query


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare HotpotQA distractor dev to processed format.")
    parser.add_argument("--input", type=Path, default=REPO / "data/raw/hotpotqa/hotpot_dev_distractor_v1.json")
    parser.add_argument("--output-dir", type=Path, default=REPO / "data/processed/hotpotqa")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: Input not found: {args.input}")
        return 1

    with args.input.open(encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, list):
        print("ERROR: Expected JSON array of records")
        return 1

    queries: list[Query] = []
    documents: list[Document] = []
    qrels: list[QrelEntry] = []

    for rec in raw:
        qid = str(rec["_id"])
        question = str(rec["question"])
        ctx = rec.get("context", [])
        sf = rec.get("supporting_facts", [])
        qtype = rec.get("type", "")
        level = rec.get("level", "")

        # Supporting-fact titles (exact match for qrels)
        sf_titles = {str(t) for t, _ in sf}

        queries.append(Query(
            query_id=qid,
            text=question,
            metadata={"type": qtype, "level": level} if (qtype or level) else {},
        ))

        for title, sentences in ctx:
            title = str(title)
            text = " ".join(str(s) for s in sentences) if isinstance(sentences, list) else str(sentences)
            doc_id = f"{qid}::{title}"
            documents.append(Document(
                doc_id=doc_id,
                text=text,
                title=title,
                metadata={"query_id": qid},
            ))
            if title in sf_titles:
                qrels.append(QrelEntry(query_id=qid, doc_id=doc_id, relevance=1))

    args.output_dir.mkdir(parents=True, exist_ok=True)

    out_q = args.output_dir / "queries.jsonl"
    out_d = args.output_dir / "documents.jsonl"
    out_r = args.output_dir / "qrels.jsonl"

    existing_outputs = [path for path in (out_q, out_d, out_r) if path.exists()]
    if existing_outputs and not args.force:
        existing_names = ", ".join(path.name for path in existing_outputs)
        print(f"Output exists ({existing_names}). Use --force to overwrite.")
        return 0

    def write_jsonl(records, path: Path, to_dict):
        with path.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(to_dict(r)) + "\n")

    write_jsonl(queries, out_q, lambda q: q.to_dict())
    write_jsonl(documents, out_d, lambda d: d.to_dict())
    write_jsonl(qrels, out_r, lambda r: r.to_dict())

    n_q = len(queries)
    n_d = len(documents)
    n_r = len(qrels)
    docs_per_q = n_d / n_q if n_q else 0
    rel_per_q = n_r / n_q if n_q else 0

    print(f"Wrote {out_q} ({n_q} queries)")
    print(f"Wrote {out_d} ({n_d} documents)")
    print(f"Wrote {out_r} ({n_r} qrels)")
    print(f"  Avg docs per query: {docs_per_q:.1f}")
    print(f"  Avg relevant docs per query: {rel_per_q:.1f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
