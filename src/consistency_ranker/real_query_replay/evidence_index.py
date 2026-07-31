"""Canonical index of reusable real-query judgments (local caches only)."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass
class EvidenceSource:
    source_id: str
    dataset: str
    path: str
    sha256: str
    n_records: int
    provider: str | None
    model: str | None
    judgment_mode: str
    has_orientation: bool
    notes: str = ""


@dataclass
class CanonicalQuery:
    dataset: str
    query_id: str
    sources: list[str] = field(default_factory=list)
    n_judgments: int = 0
    providers: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    prompts: list[str] = field(default_factory=list)
    orientations: list[str] = field(default_factory=list)
    judgment_modes: list[str] = field(default_factory=list)
    top_k: int | None = None
    has_qrels: bool = False
    canonical_cache: str | None = None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _qrel_query_ids(dataset: str) -> set[str]:
    candidates = [
        REPO_ROOT / "data" / "processed" / "beir" / dataset / "qrels.jsonl",
        REPO_ROOT / "data" / "processed" / dataset / "qrels.jsonl",
        REPO_ROOT / "data" / "raw" / "beir" / dataset / "qrels.jsonl",
        REPO_ROOT / "data" / "raw" / dataset / "qrels.jsonl",
    ]
    ids: set[str] = set()
    for p in candidates:
        if not p.exists():
            continue
        for row in _iter_jsonl(p):
            qid = str(row.get("query_id") or row.get("qid") or "")
            if qid:
                ids.add(qid)
        break
    return ids


def build_canonical_evidence_index(
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Scan known caches; prefer SciDocs q50 over nested q20/q30 subsets."""
    root = repo_root or REPO_ROOT
    sources: list[EvidenceSource] = []
    duplicates: list[dict[str, Any]] = []
    missing_cells: list[dict[str, Any]] = []
    queries: dict[tuple[str, str], CanonicalQuery] = {}

    # --- SciDocs OpenAI pairwise (canonical = q50; q20/q30 are nested subsets) ---
    q50 = root / "outputs/openai_scidocs_real_pairwise_q50_k15"
    q30 = root / "outputs/openai_scidocs_real_pairwise_q30_k15"
    q20 = root / "outputs/openai_scidocs_real_run_q20_k15"
    hotpot = root / "outputs/openai_hotpotqa_real_run_q20_k15"
    fiqa = root / "outputs/openai_fiqa_real_run_q20_k15"
    multi = root / "reports/multi_provider_llm_robustness_20260725T200000Z"
    fail_v3 = root / "reports/failure_mining_llm_v3"

    scidocs_qrels = _qrel_query_ids("scidocs")
    hotpot_qrels = _qrel_query_ids("hotpotqa")
    fiqa_qrels = _qrel_query_ids("fiqa")
    bright_qrels = _qrel_query_ids("bright")

    def _register_openai_pairwise(dir_path: Path, dataset: str, *, canonical: bool) -> None:
        cache = dir_path / "judgment_cache" / "llm_pairwise_judgments.jsonl"
        cfg_path = dir_path / "config.json"
        if not cache.exists():
            missing_cells.append(
                {
                    "dataset": dataset,
                    "reason": "missing_judgments",
                    "path": str(cache),
                }
            )
            return
        cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
        sha = _sha256_file(cache)
        n = sum(1 for _ in cache.open())
        sid = f"openai_{dataset}_pairwise_{dir_path.name}"
        sources.append(
            EvidenceSource(
                source_id=sid,
                dataset=dataset,
                path=str(cache.relative_to(root)),
                sha256=sha,
                n_records=n,
                provider=str(cfg.get("provider") or "openai"),
                model=str(cfg.get("model") or "gpt-4o-mini"),
                judgment_mode="pairwise",
                has_orientation=bool(cfg.get("debias_position")),
                notes=(
                    "canonical SciDocs pairwise cache"
                    if canonical
                    else "nested subset of SciDocs q50 — do not count as independent"
                ),
            )
        )
        if not canonical and dataset == "scidocs":
            duplicates.append(
                {
                    "kind": "nested_subset",
                    "subset_path": str(cache.relative_to(root)),
                    "subset_sha256": sha,
                    "subset_n": n,
                    "canonical_source": "openai_scidocs_pairwise_openai_scidocs_real_pairwise_q50_k15",
                    "action": "prefer_canonical_q50",
                }
            )
            return
        qrels = {
            "scidocs": scidocs_qrels,
            "hotpotqa": hotpot_qrels,
            "fiqa": fiqa_qrels,
        }.get(dataset, set())
        by_q: dict[str, int] = defaultdict(int)
        for row in _iter_jsonl(cache):
            qid = str(row.get("query_id") or "")
            if not qid:
                continue
            by_q[qid] += 1
        top_k = int(cfg.get("top_k") or 15)
        for qid, nj in by_q.items():
            key = (dataset, qid)
            cq = queries.get(key) or CanonicalQuery(dataset=dataset, query_id=qid)
            cq.sources.append(sid)
            cq.n_judgments = max(cq.n_judgments, nj)
            cq.providers = sorted(set(cq.providers + ["openai"]))
            cq.models = sorted(set(cq.models + [str(cfg.get("model") or "gpt-4o-mini")]))
            cq.prompts = sorted(set(cq.prompts + ["legacy_pairwise"]))
            cq.orientations = sorted(set(cq.orientations + ["none"]))
            cq.judgment_modes = sorted(set(cq.judgment_modes + ["pairwise"]))
            cq.top_k = top_k
            cq.has_qrels = qid in qrels
            cq.canonical_cache = str(cache.relative_to(root))
            queries[key] = cq

    if q50.exists():
        _register_openai_pairwise(q50, "scidocs", canonical=True)
    if q30.exists():
        _register_openai_pairwise(q30, "scidocs", canonical=False)
    if q20.exists():
        _register_openai_pairwise(q20, "scidocs", canonical=False)
    if hotpot.exists():
        _register_openai_pairwise(hotpot, "hotpotqa", canonical=True)
    if fiqa.exists():
        _register_openai_pairwise(fiqa, "fiqa", canonical=True)

    # --- Multi-provider provenance store (2 queries; full orientation) ---
    mp_path = multi / "judgment_records.jsonl"
    if mp_path.exists():
        sha = _sha256_file(mp_path)
        n = sum(1 for _ in mp_path.open())
        sid = "multi_provider_scidocs_pilot"
        sources.append(
            EvidenceSource(
                source_id=sid,
                dataset="scidocs",
                path=str(mp_path.relative_to(root)),
                sha256=sha,
                n_records=n,
                provider="multi",
                model="mixed",
                judgment_mode="pairwise",
                has_orientation=True,
                notes="2-query Stage1+partial Stage3 pilot; within-query factors only",
            )
        )
        by_q: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: {"providers": set(), "models": set(), "prompts": set(), "orients": set()}
        )
        counts: dict[str, int] = defaultdict(int)
        for row in _iter_jsonl(mp_path):
            qid = str(row.get("query_id") or "")
            if not qid:
                continue
            counts[qid] += 1
            by_q[qid]["providers"].add(str(row.get("provider") or ""))
            by_q[qid]["models"].add(str(row.get("model") or ""))
            by_q[qid]["prompts"].add(str(row.get("prompt_version") or ""))
            by_q[qid]["orients"].add(str(row.get("displayed_orientation") or ""))
        for qid, meta in by_q.items():
            key = ("scidocs", qid)
            cq = queries.get(key) or CanonicalQuery(dataset="scidocs", query_id=qid)
            cq.sources.append(sid)
            cq.n_judgments = max(cq.n_judgments, counts[qid])
            cq.providers = sorted(set(cq.providers) | meta["providers"])
            cq.models = sorted(set(cq.models) | meta["models"])
            cq.prompts = sorted(set(cq.prompts) | meta["prompts"])
            cq.orientations = sorted(set(cq.orientations) | meta["orients"])
            cq.judgment_modes = sorted(set(cq.judgment_modes + ["pairwise"]))
            cq.top_k = cq.top_k or 4
            cq.has_qrels = qid in scidocs_qrels
            queries[key] = cq
        # Matched factorial cells still missing for 30–40 query design.
        missing_cells.append(
            {
                "dataset": "scidocs",
                "reason": "matched_factorial_incomplete",
                "detail": "multi-provider pilot has only 2 queries; not 30–40×2×2×orient",
                "n_queries": len(by_q),
            }
        )

    # --- Failure-mining oriented azure+cohere ---
    fm_edges = fail_v3 / "preference_edges_by_query.jsonl"
    fm_metrics = fail_v3 / "query_level_metrics.csv"
    if fm_edges.exists():
        sha = _sha256_file(fm_edges)
        n = sum(1 for _ in fm_edges.open())
        sid = "failure_mining_llm_v3_edges"
        sources.append(
            EvidenceSource(
                source_id=sid,
                dataset="mixed",
                path=str(fm_edges.relative_to(root)),
                sha256=sha,
                n_records=n,
                provider="azure+cohere",
                model="mixed",
                judgment_mode="pairwise",
                has_orientation=True,
                notes="failure-mining graphs; use with query_level_metrics for repair deltas",
            )
        )
        for row in _iter_jsonl(fm_edges):
            dataset = str(row.get("dataset") or "unknown")
            qid = str(row.get("query_id") or "")
            if not qid:
                continue
            key = (dataset, qid)
            cq = queries.get(key) or CanonicalQuery(dataset=dataset, query_id=qid)
            cq.sources.append(sid)
            edges = row.get("edges") or []
            cq.n_judgments = max(cq.n_judgments, len(edges) if isinstance(edges, list) else 0)
            cq.providers = sorted(set(cq.providers + ["azure", "cohere"]))
            cq.orientations = sorted(set(cq.orientations + ["ab", "ba"]))
            cq.judgment_modes = sorted(set(cq.judgment_modes + ["pairwise"]))
            qrels = {
                "scidocs": scidocs_qrels,
                "hotpotqa": hotpot_qrels,
                "fiqa": fiqa_qrels,
                "bright": bright_qrels,
            }.get(dataset, set())
            cq.has_qrels = qid in qrels
            queries[key] = cq
    if fm_metrics.exists():
        sources.append(
            EvidenceSource(
                source_id="failure_mining_llm_v3_metrics",
                dataset="mixed",
                path=str(fm_metrics.relative_to(root)),
                sha256=_sha256_file(fm_metrics),
                n_records=sum(1 for _ in fm_metrics.open()) - 1,
                provider="azure+cohere",
                model="mixed",
                judgment_mode="pairwise",
                has_orientation=True,
                notes="precomputed repair deltas; reconstructible cross-check target",
            )
        )

    inventory = sorted(queries.values(), key=lambda q: (q.dataset, q.query_id))
    return {
        "sources": [asdict(s) for s in sources],
        "queries": [asdict(q) for q in inventory],
        "duplicates": duplicates,
        "missing_cells": missing_cells,
        "summary": {
            "n_sources": len(sources),
            "n_independent_queries": len(inventory),
            "n_queries_with_qrels": sum(1 for q in inventory if q.has_qrels),
            "datasets": sorted({q.dataset for q in inventory}),
            "providers": sorted({p for q in inventory for p in q.providers}),
        },
    }


def write_evidence_tables(index: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "canonical_evidence_manifest.json").write_text(
        json.dumps(index, indent=2, sort_keys=True), encoding="utf-8"
    )
    with (out_dir / "canonical_query_inventory.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "dataset",
                "query_id",
                "n_judgments",
                "providers",
                "models",
                "prompts",
                "orientations",
                "judgment_modes",
                "top_k",
                "has_qrels",
                "canonical_cache",
                "sources",
            ],
        )
        w.writeheader()
        for q in index["queries"]:
            w.writerow(
                {
                    "dataset": q["dataset"],
                    "query_id": q["query_id"],
                    "n_judgments": q["n_judgments"],
                    "providers": "|".join(q["providers"]),
                    "models": "|".join(q["models"]),
                    "prompts": "|".join(q["prompts"]),
                    "orientations": "|".join(q["orientations"]),
                    "judgment_modes": "|".join(q["judgment_modes"]),
                    "top_k": q.get("top_k") or "",
                    "has_qrels": q["has_qrels"],
                    "canonical_cache": q.get("canonical_cache") or "",
                    "sources": "|".join(q["sources"]),
                }
            )
    with (out_dir / "duplicate_evidence_report.csv").open("w", newline="", encoding="utf-8") as f:
        fields = sorted({k for row in index["duplicates"] for k in row})
        w = csv.DictWriter(f, fieldnames=fields or ["kind"])
        w.writeheader()
        for row in index["duplicates"]:
            w.writerow(row)
    with (out_dir / "missing_factor_cells.csv").open("w", newline="", encoding="utf-8") as f:
        fields = sorted({k for row in index["missing_cells"] for k in row})
        w = csv.DictWriter(f, fieldnames=fields or ["reason"])
        w.writeheader()
        for row in index["missing_cells"]:
            w.writerow(row)
