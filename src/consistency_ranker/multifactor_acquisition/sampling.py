"""Deterministic 30-query sample from the canonical 80-query OpenAI inventory."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SEED = 20260726
QUOTAS = {"scidocs": 18, "hotpotqa": 8, "fiqa": 4}
TOP_K = 12
MIN_CANDIDATES = 2
MAX_DOC_CHARS = 1200

CACHE_DIRS = {
    "scidocs": "outputs/openai_scidocs_real_pairwise_q50_k15",
    "hotpotqa": "outputs/openai_hotpotqa_real_run_q20_k15",
    "fiqa": "outputs/openai_fiqa_real_run_q20_k15",
}

DOC_PATHS = {
    "scidocs": "data/processed/beir/scidocs/documents.jsonl",
    "hotpotqa": "data/processed/hotpotqa/documents.jsonl",
    "fiqa": "data/processed/beir/fiqa/documents.jsonl",
}

QUERY_PATHS = {
    "scidocs": "data/processed/beir/scidocs/queries.jsonl",
    "hotpotqa": "data/processed/hotpotqa/queries.jsonl",
    "fiqa": "data/processed/beir/fiqa/queries.jsonl",
}


@dataclass
class SampledQuery:
    dataset: str
    query_id: str
    query_text: str
    query_text_hash: str
    doc_ids: list[str]
    doc_text_hashes: dict[str, str]
    prior_scores: dict[str, float]
    features: dict[str, float]
    cache_dir: str
    replacement_of: str | None = None
    effective_depth: int = TOP_K
    requested_top_k: int = TOP_K


def effective_depth(n_usable: int, *, top_k: int = TOP_K) -> int:
    """effective_depth = min(12, number of candidates with usable text)."""
    return int(min(top_k, max(0, n_usable)))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_jsonl_map(path: Path, id_key: str = "id") -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            key = str(
                row.get(id_key)
                or row.get("query_id")
                or row.get("doc_id")
                or row.get("_id")
                or row.get("id")
                or ""
            )
            if key:
                out[key] = row
    return out


def _doc_text(row: dict[str, Any]) -> str:
    text = row.get("text") or row.get("contents") or row.get("title") or ""
    if row.get("title") and row.get("text") and row["title"] not in str(text):
        text = f"{row['title']}. {text}"
    return str(text)[:MAX_DOC_CHARS]


def _query_docs_from_cache(cache_dir: Path) -> dict[str, list[str]]:
    """Preserve first-seen order of doc ids per query from the judgment cache."""
    path = cache_dir / "judgment_cache" / "llm_pairwise_judgments.jsonl"
    order: dict[str, list[str]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            qid = str(row["query_id"])
            for d in row.get("doc_ids") or []:
                ds = str(d)
                if ds not in seen[qid]:
                    seen[qid].add(ds)
                    order[qid].append(ds)
            for key in ("winner", "loser", "winner_doc_id", "loser_doc_id"):
                if row.get(key):
                    ds = str(row[key])
                    if ds not in seen[qid]:
                        seen[qid].add(ds)
                        order[qid].append(ds)
    return dict(order)


def _lexical_prior(query_text: str, doc_texts: dict[str, str]) -> dict[str, float]:
    q_toks = set(query_text.lower().split())
    scores: dict[str, float] = {}
    for did, text in doc_texts.items():
        d_toks = set(text.lower().split())
        if not q_toks or not d_toks:
            scores[did] = 0.0
        else:
            scores[did] = float(len(q_toks & d_toks)) / math.sqrt(len(d_toks))
    # tie-break by doc id for deterministic ranking
    ranked = sorted(scores, key=lambda d: (-scores[d], d))
    # convert to descending rank scores
    n = len(ranked)
    return {d: float(n - i) for i, d in enumerate(ranked)}


def _features(query_text: str, prior: dict[str, float], doc_ids: list[str]) -> dict[str, float]:
    vals = [prior[d] for d in doc_ids]
    spread = (max(vals) - min(vals)) if vals else 0.0
    margin = (vals[0] - vals[1]) if len(vals) >= 2 else 0.0
    # entropy of softmax-ish
    import math as _m

    if vals:
        m = max(vals)
        exps = [_m.exp(v - m) for v in vals]
        z = sum(exps) or 1.0
        ps = [e / z for e in exps]
        ent = -sum(p * _m.log(p + 1e-12) for p in ps)
    else:
        ent = 0.0
    return {
        "query_length": float(len(query_text.split())),
        "prior_score_spread": float(spread),
        "top_score_margin": float(margin),
        "prior_entropy": float(ent),
        "n_candidates": float(len(doc_ids)),
    }


def _stratum_key(feats: dict[str, float]) -> str:
    """Coarse bins for stratification (pre-decision only)."""

    def bin_spread(x: float) -> str:
        if x < 2:
            return "spread_lo"
        if x < 5:
            return "spread_mid"
        return "spread_hi"

    def bin_len(x: float) -> str:
        if x < 8:
            return "qlen_lo"
        if x < 16:
            return "qlen_mid"
        return "qlen_hi"

    return f"{bin_len(feats['query_length'])}|{bin_spread(feats['prior_score_spread'])}"


def build_query_universe(repo: Path) -> list[dict[str, Any]]:
    """All eligible queries from the three OpenAI pairwise caches (top-12 capable)."""
    rows: list[dict[str, Any]] = []
    for dataset, rel in CACHE_DIRS.items():
        cache_dir = repo / rel
        docs = _load_jsonl_map(repo / DOC_PATHS[dataset])
        queries = _load_jsonl_map(repo / QUERY_PATHS[dataset])
        q_docs = _query_docs_from_cache(cache_dir)
        for qid, doc_ids_all in sorted(q_docs.items()):
            if len(doc_ids_all) < MIN_CANDIDATES:
                continue
            qrow = queries.get(qid)
            if not qrow:
                continue
            qtext = str(qrow.get("text") or qrow.get("query") or "")
            # take up to TOP_K in cache order, then re-rank by lexical prior for scores
            cand = doc_ids_all[:TOP_K]
            doc_texts = {}
            for d in cand:
                if d not in docs:
                    continue
                text = _doc_text(docs[d])
                if text and text.strip():
                    doc_texts[d] = text
            # Eligible pool = candidates with usable text; depth may be < TOP_K.
            if len(doc_texts) < MIN_CANDIDATES:
                continue
            ordered_ids = [d for d in cand if d in doc_texts]
            prior = _lexical_prior(qtext, doc_texts)
            # order candidates by prior for acquisition top_k semantics
            ordered = sorted(ordered_ids, key=lambda d: (-prior[d], d))
            depth = effective_depth(len(ordered), top_k=TOP_K)
            ordered = ordered[:depth]
            doc_texts = {d: doc_texts[d] for d in ordered}
            prior = {d: prior[d] for d in ordered}
            feats = _features(qtext, prior, ordered)
            rows.append(
                {
                    "dataset": dataset,
                    "query_id": qid,
                    "query_text": qtext,
                    "query_text_hash": _sha(qtext),
                    "doc_ids": ordered,
                    "doc_texts": doc_texts,
                    "doc_text_hashes": {d: _sha(doc_texts[d]) for d in ordered},
                    "prior_scores": prior,
                    "features": feats,
                    "stratum": _stratum_key(feats),
                    "cache_dir": rel,
                    "n_candidates": len(ordered),
                    "effective_depth": depth,
                    "requested_top_k": TOP_K,
                }
            )
    return rows


def sample_queries(
    repo: Path,
    *,
    seed: int = SEED,
    quotas: dict[str, int] | None = None,
) -> tuple[list[SampledQuery], list[dict[str, Any]]]:
    """Stratified deterministic sample; replacements recorded when a row fails hydration."""
    quotas = quotas or QUOTAS
    universe = build_query_universe(repo)
    by_ds: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in universe:
        by_ds[row["dataset"]].append(row)

    # deterministic shuffle within stratum then dataset using seed
    def sort_key(row: dict[str, Any]) -> tuple:
        h = hashlib.sha256(f"{seed}:{row['dataset']}:{row['query_id']}".encode()).hexdigest()
        return (row["stratum"], h)

    selected: list[SampledQuery] = []
    audit: list[dict[str, Any]] = []
    for ds, need in quotas.items():
        pool = sorted(by_ds.get(ds, []), key=sort_key)
        # round-robin across strata
        by_str: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in pool:
            by_str[r["stratum"]].append(r)
        strata = sorted(by_str)
        picked_ids: set[str] = set()
        out_rows: list[dict[str, Any]] = []
        idx = 0
        while len(out_rows) < need and any(by_str[s] for s in strata):
            s = strata[idx % len(strata)]
            idx += 1
            if not by_str[s]:
                continue
            cand = by_str[s].pop(0)
            if cand["query_id"] in picked_ids:
                continue
            # eligibility already checked in universe; accept
            picked_ids.add(cand["query_id"])
            out_rows.append(cand)
            audit.append(
                {
                    "dataset": ds,
                    "query_id": cand["query_id"],
                    "stratum": cand["stratum"],
                    "status": "selected",
                }
            )
        if len(out_rows) < need:
            raise RuntimeError(
                f"Insufficient eligible queries for {ds}: need {need}, got {len(out_rows)}"
            )
        for cand in out_rows:
            selected.append(
                SampledQuery(
                    dataset=cand["dataset"],
                    query_id=cand["query_id"],
                    query_text=cand["query_text"],
                    query_text_hash=cand["query_text_hash"],
                    doc_ids=list(cand["doc_ids"]),
                    doc_text_hashes=dict(cand["doc_text_hashes"]),
                    prior_scores=dict(cand["prior_scores"]),
                    features=dict(cand["features"]),
                    cache_dir=cand["cache_dir"],
                    effective_depth=int(cand.get("effective_depth") or len(cand["doc_ids"])),
                    requested_top_k=int(cand.get("requested_top_k") or TOP_K),
                )
            )
    # attach doc_texts via rebuild for runtime (not serialized fully in CSV)
    texts_by_q = {
        (r["dataset"], r["query_id"]): r["doc_texts"] for r in universe
    }
    for sq in selected:
        setattr(sq, "doc_texts", texts_by_q[(sq.dataset, sq.query_id)])
    return selected, audit


def load_samples_from_csv(
    repo: Path,
    csv_path: Path,
) -> list[SampledQuery]:
    """Reload the frozen query sample (do not re-draw after seeing results)."""
    import csv

    docs_by_ds = {
        ds: _load_jsonl_map(repo / path) for ds, path in DOC_PATHS.items()
    }
    queries_by_ds = {
        ds: _load_jsonl_map(repo / path) for ds, path in QUERY_PATHS.items()
    }
    samples: list[SampledQuery] = []
    with csv_path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            ds = row["dataset"]
            qid = row["query_id"]
            doc_ids = json.loads(row.get("doc_ids_json") or row.get("doc_ids") or "[]")
            prior = json.loads(row.get("prior_json") or "{}")
            feats = json.loads(row.get("features_json") or "{}")
            hashes = json.loads(row.get("doc_hash_json") or "{}")
            qrow = queries_by_ds[ds].get(qid) or {}
            qtext = str(
                row.get("query_text")
                or qrow.get("text")
                or qrow.get("query")
                or ""
            )
            doc_texts: dict[str, str] = {}
            usable_ids: list[str] = []
            for d in doc_ids:
                d = str(d)
                src = docs_by_ds[ds].get(d)
                if not src:
                    continue
                text = _doc_text(src)
                if text and text.strip():
                    doc_texts[d] = text
                    usable_ids.append(d)
            depth = effective_depth(len(usable_ids), top_k=TOP_K)
            usable_ids = usable_ids[:depth]
            doc_texts = {d: doc_texts[d] for d in usable_ids}
            prior = {d: float(prior.get(d, 0.0)) for d in usable_ids} or _lexical_prior(
                qtext, doc_texts
            )
            sq = SampledQuery(
                dataset=ds,
                query_id=qid,
                query_text=qtext,
                query_text_hash=str(row.get("query_text_hash") or _sha(qtext)),
                doc_ids=usable_ids,
                doc_text_hashes={d: hashes.get(d) or _sha(doc_texts[d]) for d in usable_ids},
                prior_scores=prior,
                features=feats or _features(qtext, prior, usable_ids),
                cache_dir=str(row.get("cache_dir") or CACHE_DIRS[ds]),
                replacement_of=row.get("replacement_of") or None,
                effective_depth=depth,
                requested_top_k=TOP_K,
            )
            setattr(sq, "doc_texts", doc_texts)
            samples.append(sq)
    return samples


def sampled_to_rows(samples: list[SampledQuery]) -> list[dict[str, Any]]:
    rows = []
    for s in samples:
        d = asdict(s)
        d["features_json"] = json.dumps(s.features)
        d["prior_json"] = json.dumps(s.prior_scores)
        d["doc_ids_json"] = json.dumps(s.doc_ids)
        d["doc_hash_json"] = json.dumps(s.doc_text_hashes)
        d["effective_depth"] = s.effective_depth
        d["requested_top_k"] = s.requested_top_k
        rows.append(d)
    return rows
