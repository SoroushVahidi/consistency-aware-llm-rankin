"""Build the frozen initial request plan and compute request identity hashes."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from consistency_ranker.counterfactual_benchmark.models import (
    CandidatePoolRecord,
    PairRecord,
    PlannedRequest,
)


def compute_request_hash(
    *,
    benchmark_version: str,
    dataset: str,
    query_id: str,
    pool_hash: str,
    doc_a_id: str,
    doc_b_id: str,
    text_hash_a: str,
    text_hash_b: str,
    presentation_order: str,
    provider: str,
    model_id: str,
    prompt_sha256: str,
    schema_sha256: str,
    temperature: float,
    seed: int,
    attempt_type: str,
) -> str:
    """Hash every field that identifies (and could change the response of) a request."""
    payload: dict[str, Any] = {
        "benchmark_version": benchmark_version,
        "dataset": dataset,
        "query_id": query_id,
        "pool_hash": pool_hash,
        "doc_a_id": doc_a_id,
        "doc_b_id": doc_b_id,
        "text_hash_a": text_hash_a,
        "text_hash_b": text_hash_b,
        "presentation_order": presentation_order,
        "provider": provider,
        "model_id": model_id,
        "prompt_sha256": prompt_sha256,
        "schema_sha256": schema_sha256,
        "temperature": temperature,
        "seed": seed,
        "attempt_type": attempt_type,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_initial_requests(
    *,
    config: dict[str, Any],
    pools: dict[tuple[str, str], CandidatePoolRecord],
    pairs: dict[tuple[str, str], list[PairRecord]],
) -> list[PlannedRequest]:
    """Build the shared-pair-set initial request plan: query x provider x pair."""
    benchmark_version = str(config["benchmark_version"])
    prompt_hash = str(config["prompt_sha256"])
    schema_hash = str(config["judgment_schema_sha256"])
    temperature = float(config["generation_defaults"]["temperature"])
    seed = int(config["generation_defaults"]["seed"])
    providers = list(config["provider_panel"])

    requests: list[PlannedRequest] = []
    for dataset, meta in config["datasets"].items():
        for qid in meta["query_ids"]:
            key = (dataset, str(qid))
            pool = pools[key]
            for provider_meta in providers:
                provider = str(provider_meta["provider"])
                model_id = str(provider_meta["model_or_deployment"])
                for pair in pairs[key]:
                    request_hash = compute_request_hash(
                        benchmark_version=benchmark_version,
                        dataset=dataset,
                        query_id=str(qid),
                        pool_hash=pool.pool_hash,
                        doc_a_id=pair.doc_a_id,
                        doc_b_id=pair.doc_b_id,
                        text_hash_a=pool.text_hashes[pair.doc_a_id],
                        text_hash_b=pool.text_hashes[pair.doc_b_id],
                        presentation_order=pair.initial_presentation_order,
                        provider=provider,
                        model_id=model_id,
                        prompt_sha256=prompt_hash,
                        schema_sha256=schema_hash,
                        temperature=temperature,
                        seed=seed,
                        attempt_type="initial",
                    )
                    requests.append(
                        PlannedRequest(
                            request_hash=request_hash,
                            benchmark_version=benchmark_version,
                            dataset=dataset,
                            query_id=str(qid),
                            pool_hash=pool.pool_hash,
                            provider=provider,
                            model_id=model_id,
                            doc_a_id=pair.doc_a_id,
                            doc_b_id=pair.doc_b_id,
                            presentation_order=pair.initial_presentation_order,
                            pair_id=pair.pair_id,
                            pair_reason=pair.reason,
                            temperature=temperature,
                            seed=seed,
                            attempt_type="initial",
                        )
                    )
    return requests
