"""Direct enumeration of the three real-LLM studies' stored observations.

Deliberately does NOT trust any previously-reported summary count (e.g. the
"n=120 query-graphs" language in the original reports/audit) -- every field
below is read straight from the studies' own per-row JSONL files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]

FRONTIER_DIR = _REPO_ROOT / "reports/repair_frontier_20260729T144742Z"
EXTRACTION_DIR = _REPO_ROOT / "reports/extraction_study_20260729T151610Z"
DIAGNOSTIC_DIR = _REPO_ROOT / "reports/repair_diagnostic_20260729T162748Z"

# Model identifiers per provider, read directly from the raw provider-call
# transcripts (reports/multi_provider_repair_pilot_20260729T032348Z/raw_calls/
# *_calls.jsonl, each record's own "model" field) -- not hardcoded from
# memory. See population_manifest() below for the actual read.
_PILOT_DIR = _REPO_ROOT / "reports/multi_provider_repair_pilot_20260729T032348Z/raw_calls"
_RAW_CALL_FILES = {
    "azure": _PILOT_DIR / "azure_calls.jsonl",
    "gemini": _PILOT_DIR / "gemini_calls.jsonl",
    "cohere": _PILOT_DIR / "cohere_calls.jsonl",
    "fireworks": _PILOT_DIR / "fireworks_calls.jsonl",
}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def provider_model_map() -> dict[str, str]:
    """Read the actual model string used by each provider from the raw call
    transcripts (first record of each provider's file). "aggregate" is not
    a raw model call -- it is a derived combination of the four real
    providers' judgments, recorded as such."""
    models = {"aggregate": "derived (unweighted combination of azure/gemini/cohere/fireworks)"}
    for provider, path in _RAW_CALL_FILES.items():
        if not path.exists():
            models[provider] = "UNKNOWN (raw_calls file not found)"
            continue
        with path.open(encoding="utf-8") as f:
            first = json.loads(f.readline())
        models[provider] = first.get("model", "UNKNOWN")
    return models


def _split_unit_key(unit_key: str) -> dict[str, str]:
    """unit_key components appear in different orders across the three
    studies (verified this stage); split generically and classify each part
    by shape rather than assuming a fixed position."""
    parts = unit_key.split("|")
    out = {"dataset": "", "query_id": "", "source": "", "variant": "", "provider": ""}
    providers = {"azure", "gemini", "cohere", "fireworks", "aggregate"}
    datasets = {"scidocs", "fiqa"}
    sources = {"pool6_pilot", "reviewer_concerns_branch_b"}
    for p in parts:
        if p in providers:
            out["provider"] = p
        elif p in datasets:
            out["dataset"] = p
        elif p in sources:
            out["source"] = p
        elif p.startswith("pool") and ("_" in p or p[4:].isdigit() is False):
            out["variant"] = p
        else:
            # remaining part is the query_id (no fixed vocabulary -- BeIR
            # doc/query ids are hashes for scidocs, small ints for fiqa)
            if not out["query_id"]:
                out["query_id"] = p
    return out


def build_population_manifest() -> list[dict[str, Any]]:
    """One row per stored observation across all three studies, each tagged
    with its independence cluster (query_id)."""
    models = provider_model_map()
    rows: list[dict[str, Any]] = []

    for r in _load_jsonl(EXTRACTION_DIR / "extraction_results.jsonl"):
        parts = _split_unit_key(r["unit_key"])
        rows.append(
            {
                "study": "extraction_study",
                "source_file": "extraction_results.jsonl",
                "unit_key": r["unit_key"],
                "independence_cluster": r["query_id"],
                "query_id": r["query_id"],
                "dataset": r["dataset"],
                "provider": r["provider"],
                "model": models.get(r["provider"], "UNKNOWN"),
                "construction_variant": parts["variant"] or parts["source"],
                "pool_size": r["pool_size"],
                "repair_method": "",
                "extractor": "ALL (row holds every extractor's ndcg)",
                "diagnostic_configuration": "",
                "is_cyclic": r.get("is_cyclic"),
                "incumbent_ndcg": r.get("incumbent_ndcg"),
            }
        )

    for r in _load_jsonl(DIAGNOSTIC_DIR / "diagnostic_results.jsonl"):
        parts = _split_unit_key(r["unit_key"])
        rows.append(
            {
                "study": "repair_diagnostic",
                "source_file": "diagnostic_results.jsonl",
                "unit_key": r["unit_key"],
                "independence_cluster": r["query_id"],
                "query_id": r["query_id"],
                "dataset": r["dataset"],
                "provider": r["provider"],
                "model": models.get(r["provider"], "UNKNOWN"),
                "construction_variant": parts["variant"] or parts["source"],
                "pool_size": r["pool_size"],
                "repair_method": "greedy_mwfas",
                "extractor": "",
                "diagnostic_configuration": r["outcome"],
                "is_cyclic": r.get("pre_repair", {}).get("is_cyclic"),
                "incumbent_ndcg": r.get("ndcg_preserve"),
            }
        )

    frontier_rows = _load_jsonl(FRONTIER_DIR / "checkpoint/frontier_results.jsonl")
    for r in frontier_rows:
        parts = _split_unit_key(r["unit_key"])
        rows.append(
            {
                "study": "repair_frontier",
                "source_file": "checkpoint/frontier_results.jsonl",
                "unit_key": r["unit_key"],
                "independence_cluster": r["query_id"],
                "query_id": r["query_id"],
                "dataset": r["dataset"],
                "provider": parts["provider"],
                "model": models.get(parts["provider"], "UNKNOWN"),
                "construction_variant": r.get("variant", ""),
                "pool_size": "",
                "repair_method": r.get("candidate_id", ""),
                "extractor": "",
                "diagnostic_configuration": "",
                "is_cyclic": r.get("graph_features", {}).get("is_cyclic"),
                "incumbent_ndcg": "",
            }
        )

    return rows


def population_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Descriptive counts computed directly from the manifest -- the numbers
    this whole re-analysis stage exists to pin down precisely."""
    by_study: dict[str, dict[str, Any]] = {}
    for study in sorted({r["study"] for r in rows}):
        study_rows = [r for r in rows if r["study"] == study]
        clusters = {r["independence_cluster"] for r in study_rows}
        providers = {r["provider"] for r in study_rows if r["provider"]}
        variants = {r["construction_variant"] for r in study_rows if r["construction_variant"]}
        by_study[study] = {
            "n_rows": len(study_rows),
            "n_unique_queries": len(clusters),
            "n_providers": len(providers),
            "n_construction_variants": len(variants),
            "rows_per_query_min": min(
                sum(1 for r in study_rows if r["independence_cluster"] == c) for c in clusters
            ),
            "rows_per_query_max": max(
                sum(1 for r in study_rows if r["independence_cluster"] == c) for c in clusters
            ),
        }
    all_clusters = [
        set(r["independence_cluster"] for r in rows if r["study"] == s) for s in by_study
    ]
    shared_across_all = all_clusters[0].intersection(*all_clusters[1:]) if all_clusters else set()
    return {
        "by_study": by_study,
        "total_rows": len(rows),
        "total_unique_queries_overall": len({r["independence_cluster"] for r in rows}),
        "queries_shared_across_all_three_studies": sorted(shared_across_all),
        "n_queries_shared_across_all_three_studies": len(shared_across_all),
    }
