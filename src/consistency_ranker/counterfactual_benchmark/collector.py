"""Orchestrates the fail-closed counterfactual micro-pilot collector.

Three execution modes, exactly one required per run:

* ``dry_run``    -- plans everything, calls no provider, writes the plan.
* ``cache_only`` -- resolves every planned request from an existing cache;
  missing entries are explicit failures, never silent substitutions.
* ``live``       -- resolves missing requests via real provider calls, under
  a hard-capped, resumable ledger.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Literal, cast

from consistency_ranker.counterfactual_benchmark import config as config_mod
from consistency_ranker.counterfactual_benchmark import pool_builder
from consistency_ranker.counterfactual_benchmark.cache_store import JudgmentCacheStore
from consistency_ranker.counterfactual_benchmark.dispatch import (
    call_provider,
    estimate_request_tokens,
)
from consistency_ranker.counterfactual_benchmark.evaluation import (
    compute_terminal_outcomes,
    load_qrels,
)
from consistency_ranker.counterfactual_benchmark.models import (
    CandidatePoolRecord,
    NormalizedJudgment,
    PairRecord,
    PlannedRequest,
)
from consistency_ranker.counterfactual_benchmark.pair_selection import (
    select_shared_pairs,
    select_shared_pairs_v2,
)
from consistency_ranker.counterfactual_benchmark.prompt_renderer import render_request_prompt
from consistency_ranker.counterfactual_benchmark.query_selection import load_frozen_queries
from consistency_ranker.counterfactual_benchmark.report import (
    status_label,
    write_final_report,
    write_json,
    write_jsonl,
)
from consistency_ranker.counterfactual_benchmark.reserve import (
    build_reserve_request,
    derive_reserve_decisions,
)
from consistency_ranker.counterfactual_benchmark.validation import assert_no_qrels_anywhere
from consistency_ranker.counterfactual_pilot.presentation import (
    map_displayed_preference_to_document,
)
from consistency_ranker.counterfactual_pilot.schema import extract_json_payload, validate_judgment
from consistency_ranker.counterfactual_pilot.trajectory import validate_step_record
from consistency_ranker.experiment_cli import (
    ensure_output_dir,
    file_sha256,
    write_run_manifest,
)
from consistency_ranker.provider_capability.ledger import LiveCallCapExceeded, LiveCallLedger
from consistency_ranker.provider_capability.sanitize import response_hash, sanitize_mapping

VALID_MODES = ("dry_run", "cache_only", "live")


class CollectorInputError(ValueError):
    pass


_POOL_BUILDERS = {
    pool_builder.POOL_PROTOCOL_VERSION: pool_builder.build_candidate_pool,
    pool_builder.POOL_PROTOCOL_VERSION_V2: pool_builder.build_candidate_pool_v2,
}


def _build_pools(
    config: dict[str, Any], *, repo_root: Path
) -> tuple[list, dict[tuple[str, str], CandidatePoolRecord]]:
    frozen_queries = load_frozen_queries(config, repo_root=repo_root)
    pool_size = int(config["candidate_pool"]["pool_size"])
    max_chars = int(config["candidate_pool"]["max_candidate_chars"])
    protocol = config["candidate_pool"]["pool_protocol_version"]
    builder_fn = _POOL_BUILDERS.get(protocol)
    if builder_fn is None:
        raise CollectorInputError(f"unsupported pool_protocol_version: {protocol!r}")
    pools: dict[tuple[str, str], CandidatePoolRecord] = {}
    for fq in frozen_queries:
        documents_path = repo_root / config["datasets"][fq.dataset]["documents_path"]
        pool = builder_fn(
            dataset=fq.dataset,
            query_id=fq.query_id,
            query_text=fq.query_text,
            documents_path=documents_path,
            pool_size=pool_size,
            max_candidate_chars=max_chars,
        )
        assert_no_qrels_anywhere(pool.to_dict())
        pools[(fq.dataset, fq.query_id)] = pool
    return frozen_queries, pools


def _plan_summary(
    config: dict[str, Any],
    pools: dict[tuple[str, str], CandidatePoolRecord],
) -> dict[str, Any]:
    return {
        "prompt_sha256": config["prompt_sha256"],
        "judgment_schema_sha256": config["judgment_schema_sha256"],
        "panel_version": config["panel_version"],
        "model_ids": sorted(m["model_or_deployment"] for m in config["provider_panel"]),
        "temperature": config["generation_defaults"]["temperature"],
        "max_output_tokens": config["generation_defaults"]["max_output_tokens"],
        "pool_hashes": sorted(p.pool_hash for p in pools.values()),
        "query_ids": sorted(f"{ds}:{qid}" for (ds, qid) in pools),
        "policies": sorted(config["policies"]),
        "eval_k": config["candidate_pool"]["eval_k"],
        "hard_max_live_calls": config["call_budget"]["hard_max_live_calls"],
    }


def _step_record(
    *,
    config: dict[str, Any],
    pool: CandidatePoolRecord,
    request: PlannedRequest,
    judgment: NormalizedJudgment,
) -> dict[str, Any]:
    rec = {
        "benchmark_version": config["benchmark_version"],
        "dataset": request.dataset,
        "query_id": request.query_id,
        "candidate_pool_id": pool.pool_hash,
        "candidate_ids": list(pool.candidate_ids),
        "policy": "judgment_collection_only",
        "budget": config["acquisition"]["initial_selected_pairs_per_query"],
        "provider": request.provider,
        "model_id": request.model_id,
        "step": 0,
        "available_action_count": len(pool.candidate_ids),
        "selected_pair": [request.doc_a_id, request.doc_b_id],
        "presentation_order": request.presentation_order,
        "request_hash": request.request_hash,
        "judgment": {
            "preference": judgment.preference,
            "confidence": judgment.confidence,
            "evidence_strength": judgment.evidence_strength,
            "reason_code": judgment.reason_code,
        },
        "normalized_document_preference": judgment.normalized_document_preference,
        "confidence": judgment.confidence,
        "remaining_budget": None,
        "graph_state_summary": {},
        "ranking_after_step": [],
        "stop_reason": None if judgment.success else judgment.error_category,
        "calls_used": 1,
        "tokens_used": {
            "prompt": judgment.prompt_tokens or 0,
            "completion": judgment.completion_tokens or 0,
        },
        "latency": judgment.latency_seconds or 0.0,
    }
    validate_step_record(rec)
    return rec


def _resolve_cache_only(
    request_hash: str, cache: JudgmentCacheStore
) -> NormalizedJudgment | None:
    hit = cache.get(request_hash)
    if hit is None:
        return None
    fields = {k: v for k, v in hit.items() if k != "from_cache"}
    return NormalizedJudgment(**fields, from_cache=True)


def _resolve_live(
    *,
    request: PlannedRequest,
    query_text: str,
    pool: CandidatePoolRecord,
    config: dict[str, Any],
    repo_root: Path,
    ledger: LiveCallLedger,
    cache: JudgmentCacheStore,
    call_fn: Callable[..., tuple[str, object]] | None,
) -> NormalizedJudgment:
    cached = cache.get(request.request_hash)
    if cached is not None:
        return NormalizedJudgment(
            **{k: v for k, v in cached.items() if k != "from_cache"}, from_cache=True
        )

    doc_a_text = pool.truncated_texts[request.doc_a_id]
    doc_b_text = pool.truncated_texts[request.doc_b_id]
    if request.presentation_order == "ab":
        shown_a, shown_b = doc_a_text, doc_b_text
    else:
        shown_a, shown_b = doc_b_text, doc_a_text
    prompt = render_request_prompt(
        repo_root=repo_root,
        query_text=query_text,
        candidate_a_text=shown_a,
        candidate_b_text=shown_b,
        max_candidate_chars=int(config["candidate_pool"]["max_candidate_chars"]),
    )
    est_in, est_out = estimate_request_tokens(
        prompt, max_output_tokens=int(config["generation_defaults"]["max_output_tokens"])
    )

    try:
        ledger.begin_request(
            provider=request.provider,
            purpose=f"{request.dataset}:{request.query_id}:{request.pair_id}",
            request_hash=request.request_hash,
            estimated_input_tokens=est_in,
            max_output_tokens=est_out,
            is_retry=request.attempt_type == "reserve",
        )
    except LiveCallCapExceeded as exc:
        judgment = NormalizedJudgment(
            request_hash=request.request_hash,
            dataset=request.dataset,
            query_id=request.query_id,
            provider=request.provider,
            model_id=request.model_id,
            doc_a_id=request.doc_a_id,
            doc_b_id=request.doc_b_id,
            pair_id=request.pair_id,
            presentation_order=request.presentation_order,
            attempt_type=request.attempt_type,
            success=False,
            inference_attempted=False,
            error_category="cap_exceeded",
            error_message=str(exc),
        )
        return judgment

    result = call_provider(
        provider=request.provider,
        model_id=request.model_id,
        prompt=prompt,
        temperature=request.temperature,
        max_tokens=int(config["generation_defaults"]["max_output_tokens"]),
        call_fn=call_fn,
    )

    preference = confidence = evidence_strength = reason_code = None
    normalized_pref = None
    parse_failed = False
    wrapper_extraction_used = False
    success = result.error_category is None
    if success:
        candidate_text, unwrapped = extract_json_payload(result.raw_response)
        try:
            obj = json.loads(candidate_text)
            validated = validate_judgment(obj)
        except (json.JSONDecodeError, ValueError, TypeError):
            parse_failed = True
            success = False
        else:
            wrapper_extraction_used = unwrapped
            preference = validated["preference"]
            confidence = validated["confidence"]
            evidence_strength = validated["evidence_strength"]
            reason_code = validated["reason_code"]
            normalized_pref = map_displayed_preference_to_document(
                preference,
                orientation=cast(Literal["ab", "ba"], request.presentation_order),
                doc_a_id=request.doc_a_id,
                doc_b_id=request.doc_b_id,
            )

    ledger.finish_request(
        provider=request.provider,
        purpose=f"{request.dataset}:{request.query_id}:{request.pair_id}",
        request_hash=request.request_hash,
        success=success,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        latency_seconds=result.latency_seconds,
        parse_status="parse_failed" if parse_failed else ("ok" if success else "error"),
        raw_response=result.raw_response,
        error=result.error_message,
        is_retry=request.attempt_type == "reserve",
    )

    judgment = NormalizedJudgment(
        request_hash=request.request_hash,
        dataset=request.dataset,
        query_id=request.query_id,
        provider=request.provider,
        model_id=request.model_id,
        doc_a_id=request.doc_a_id,
        doc_b_id=request.doc_b_id,
        pair_id=request.pair_id,
        presentation_order=request.presentation_order,
        attempt_type=request.attempt_type,
        success=success,
        preference=preference,
        normalized_document_preference=normalized_pref,
        confidence=confidence,
        evidence_strength=evidence_strength,
        reason_code=reason_code,
        raw_response_hash=response_hash(result.raw_response),
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        latency_seconds=result.latency_seconds,
        from_cache=False,
        parse_failed=parse_failed,
        wrapper_extraction_used=wrapper_extraction_used,
        inference_attempted=result.error_category != "missing_credentials",
        error_category=result.error_category if not success and not parse_failed else (
            "parse_failure" if parse_failed else None
        ),
        error_message=result.error_message,
    )
    cache.put(sanitize_mapping(judgment.to_dict()))
    return judgment


def run_collection(
    *,
    config_path: Path,
    output_dir: Path,
    mode: str,
    repo_root: Path,
    is_canary: bool = False,
    overwrite: bool = False,
    cache_dir: Path | None = None,
    call_fn: Callable[..., tuple[str, object]] | None = None,
) -> dict[str, Any]:
    if mode not in VALID_MODES:
        raise CollectorInputError(f"mode must be one of {VALID_MODES}, got {mode!r}")

    config = config_mod.load_config(config_path)
    config_mod.verify_frozen_contract(config, repo_root=repo_root)

    output_dir = ensure_output_dir(output_dir, overwrite=overwrite)
    write_run_manifest(
        output_dir,
        script="scripts/run_counterfactual_micro_pilot.py",
        config=config,
        repo_root=repo_root,
        input_hashes={
            "config": file_sha256(config_path),
            "prompt": config["prompt_sha256"],
            "schema": config["judgment_schema_sha256"],
        },
        extra={"mode": mode, "is_canary": is_canary},
    )

    frozen_queries, pools = _build_pools(config, repo_root=repo_root)

    eval_k = int(config["candidate_pool"]["eval_k"])
    n_pairs = int(config["acquisition"]["initial_selected_pairs_per_query"])
    seed = int(config["generation_defaults"]["seed"])
    pairs: dict[tuple[str, str], list[PairRecord]] = {}
    for key, pool in pools.items():
        if pool.pool_protocol_version == pool_builder.POOL_PROTOCOL_VERSION_V2:
            pairs[key] = select_shared_pairs_v2(pool, eval_k=eval_k, n_pairs=n_pairs, seed=seed)
        else:
            pairs[key] = select_shared_pairs(pool, eval_k=eval_k, n_pairs=n_pairs, seed=seed)

    from consistency_ranker.counterfactual_benchmark.request_plan import build_initial_requests

    initial_requests = build_initial_requests(config=config, pools=pools, pairs=pairs)
    expected_initial = int(config["call_budget"]["initial_live_calls"])
    if len(initial_requests) != expected_initial:
        raise CollectorInputError(
            f"planned {len(initial_requests)} initial requests, "
            f"config declares {expected_initial}"
        )
    for r in initial_requests:
        assert_no_qrels_anywhere(r.to_dict())

    query_text_by_key = {(fq.dataset, fq.query_id): fq.query_text for fq in frozen_queries}

    # Token estimate over the frozen plan (dry-run and pre-flight for all modes).
    max_in_per_req = int(config["call_budget"]["max_input_tokens_per_request"])
    max_out_per_req = int(config["call_budget"]["max_output_tokens_per_request"])
    max_cum_in = int(config["call_budget"]["max_total_input_tokens"])
    max_cum_out = int(config["call_budget"]["max_total_output_tokens"])
    cum_in = cum_out = 0
    per_request_violations: list[str] = []
    for r in initial_requests:
        pool = pools[(r.dataset, r.query_id)]
        prompt = render_request_prompt(
            repo_root=repo_root,
            query_text=query_text_by_key[(r.dataset, r.query_id)],
            candidate_a_text=pool.truncated_texts[r.doc_a_id],
            candidate_b_text=pool.truncated_texts[r.doc_b_id],
            max_candidate_chars=int(config["candidate_pool"]["max_candidate_chars"]),
        )
        est_in, est_out = estimate_request_tokens(
            prompt, max_output_tokens=int(config["generation_defaults"]["max_output_tokens"])
        )
        if est_in > max_in_per_req:
            per_request_violations.append(r.request_hash)
        cum_in += est_in
        cum_out += est_out
    if per_request_violations:
        raise CollectorInputError(
            f"{len(per_request_violations)} planned request(s) exceed "
            f"max_input_tokens_per_request={max_in_per_req}"
        )
    reserve_cap = int(config["call_budget"]["reserved_followup_calls"])
    cum_in_with_reserve_estimate = cum_in + reserve_cap * (cum_in // max(len(initial_requests), 1))
    cum_out_with_reserve_estimate = cum_out + reserve_cap * max_out_per_req
    if cum_in_with_reserve_estimate > max_cum_in or cum_out_with_reserve_estimate > max_cum_out:
        raise CollectorInputError(
            "estimated cumulative tokens (including reserve headroom) exceed frozen caps: "
            f"input={cum_in_with_reserve_estimate}/{max_cum_in} "
            f"output={cum_out_with_reserve_estimate}/{max_cum_out}"
        )

    plan_summary = _plan_summary(config, pools)
    plan_path = output_dir / "collection_plan.json"
    if plan_path.exists():
        previous = json.loads(plan_path.read_text(encoding="utf-8"))
        config_mod.validate_against_previous_plan(plan_summary, previous.get("summary", {}))
    write_json(
        plan_path,
        {
            "summary": plan_summary,
            "initial_request_count": len(initial_requests),
            "reserved_followup_calls": reserve_cap,
            "hard_max_live_calls": config["call_budget"]["hard_max_live_calls"],
            "estimated_input_tokens_initial": cum_in,
            "estimated_output_tokens_initial": cum_out,
            "planned_requests": [r.to_dict() for r in initial_requests],
        },
    )
    write_jsonl(
        output_dir / "candidate_pools.jsonl", [p.to_dict() for p in pools.values()]
    )

    if mode == "dry_run":
        write_jsonl(output_dir / "request_ledger.jsonl", [])
        write_jsonl(output_dir / "normalized_judgments.jsonl", [])
        write_jsonl(output_dir / "trajectory_events.jsonl", [])
        write_jsonl(output_dir / "terminal_outcomes.jsonl", [])
        summary = {
            "mode": mode,
            "queries_loaded": len(frozen_queries),
            "pool_sizes": {f"{k[0]}:{k[1]}": len(p.candidate_ids) for k, p in pools.items()},
            "initial_request_count": len(initial_requests),
            "reserved_followup_calls": reserve_cap,
            "hard_max_live_calls": config["call_budget"]["hard_max_live_calls"],
            "estimated_input_tokens_initial": cum_in,
            "estimated_output_tokens_initial": cum_out,
            "paid_api_calls": 0,
            "failures": 0,
        }
        write_json(output_dir / "validation_report.json", {"mode": mode, "problems": []})
        label = status_label(mode=mode, is_canary=is_canary)
        write_final_report(output_dir, label=label, mode=mode, is_canary=is_canary, summary=summary)
        return summary

    # cache_only / live share the same request-resolution + reserve loop.
    cache_path = (cache_dir or output_dir) / "normalized_judgments.jsonl"
    cache = JudgmentCacheStore(cache_path)

    ledger: LiveCallLedger | None = None
    if mode == "live":
        cb = config["call_budget"]
        ledger = LiveCallLedger(
            max_total_live_calls=int(cb["hard_max_live_calls"]),
            max_live_calls_per_provider=int(cb["max_live_calls_per_provider"]),
            max_total_input_tokens=int(cb["max_total_input_tokens"]),
            max_total_output_tokens=int(cb["max_total_output_tokens"]),
            max_retries_per_request=int(cb["max_retries_per_request"]),
            max_estimated_cost_usd=None,
            path=output_dir / "request_ledger.jsonl",
        )
        ledger.load()

    initial_judgments: list[NormalizedJudgment] = []
    step_records: list[dict[str, Any]] = []
    missing_cells: list[dict[str, Any]] = []

    for r in initial_requests:
        if mode == "cache_only":
            judgment = _resolve_cache_only(r.request_hash, cache)
            if judgment is None:
                judgment = NormalizedJudgment(
                    request_hash=r.request_hash,
                    dataset=r.dataset,
                    query_id=r.query_id,
                    provider=r.provider,
                    model_id=r.model_id,
                    doc_a_id=r.doc_a_id,
                    doc_b_id=r.doc_b_id,
                    pair_id=r.pair_id,
                    presentation_order=r.presentation_order,
                    attempt_type=r.attempt_type,
                    success=False,
                    inference_attempted=False,
                    error_category="missing_cache_entry",
                    error_message=f"no cached judgment for request_hash={r.request_hash}",
                )
                missing_cells.append(
                    {"request_hash": r.request_hash, "reason": "missing_cache_entry"}
                )
        else:
            assert ledger is not None
            judgment = _resolve_live(
                request=r,
                query_text=query_text_by_key[(r.dataset, r.query_id)],
                pool=pools[(r.dataset, r.query_id)],
                config=config,
                repo_root=repo_root,
                ledger=ledger,
                cache=cache,
                call_fn=call_fn,
            )
            if not judgment.success:
                missing_cells.append(
                    {"request_hash": r.request_hash, "reason": judgment.error_category}
                )
        initial_judgments.append(judgment)
        step_records.append(
            _step_record(
                config=config,
                pool=pools[(r.dataset, r.query_id)],
                request=r,
                judgment=judgment,
            )
        )

    reserve_decisions = derive_reserve_decisions(
        initial_judgments=initial_judgments, pairs_by_query=pairs, max_reserve=reserve_cap
    )
    reserve_judgments: list[NormalizedJudgment] = []
    for decision in reserve_decisions:
        if not decision.scheduled:
            continue
        pool = pools[(decision.dataset, decision.query_id)]
        original_pair = next(
            p for p in pairs[(decision.dataset, decision.query_id)] if p.pair_id == decision.pair_id
        )
        model_id = next(
            m["model_or_deployment"]
            for m in config["provider_panel"]
            if m["provider"] == decision.provider
        )
        request_hash, presentation_order = build_reserve_request(
            decision=decision,
            original_pair=original_pair,
            config=config,
            pool_hash=pool.pool_hash,
            text_hash_a=pool.text_hashes[original_pair.doc_a_id],
            text_hash_b=pool.text_hashes[original_pair.doc_b_id],
            model_id=model_id,
        )
        reserve_request = PlannedRequest(
            request_hash=request_hash,
            benchmark_version=config["benchmark_version"],
            dataset=decision.dataset,
            query_id=decision.query_id,
            pool_hash=pool.pool_hash,
            provider=decision.provider,
            model_id=model_id,
            doc_a_id=original_pair.doc_a_id,
            doc_b_id=original_pair.doc_b_id,
            presentation_order=presentation_order,
            pair_id=original_pair.pair_id,
            pair_reason=original_pair.reason,
            temperature=float(config["generation_defaults"]["temperature"]),
            seed=int(config["generation_defaults"]["seed"]),
            attempt_type="reserve",
            reserve_trigger=decision.trigger,
            reserve_priority=decision.priority,
        )
        assert_no_qrels_anywhere(reserve_request.to_dict())
        if mode == "cache_only":
            judgment = _resolve_cache_only(request_hash, cache)
            if judgment is None:
                judgment = NormalizedJudgment(
                    request_hash=request_hash,
                    dataset=decision.dataset,
                    query_id=decision.query_id,
                    provider=decision.provider,
                    model_id=model_id,
                    doc_a_id=original_pair.doc_a_id,
                    doc_b_id=original_pair.doc_b_id,
                    pair_id=original_pair.pair_id,
                    presentation_order=presentation_order,
                    attempt_type="reserve",
                    success=False,
                    inference_attempted=False,
                    error_category="missing_cache_entry",
                    error_message=f"no cached judgment for request_hash={request_hash}",
                )
                missing_cells.append(
                    {"request_hash": request_hash, "reason": "missing_cache_entry"}
                )
        else:
            assert ledger is not None
            judgment = _resolve_live(
                request=reserve_request,
                query_text=query_text_by_key[(decision.dataset, decision.query_id)],
                pool=pool,
                config=config,
                repo_root=repo_root,
                ledger=ledger,
                cache=cache,
                call_fn=call_fn,
            )
            if not judgment.success:
                missing_cells.append(
                    {"request_hash": request_hash, "reason": judgment.error_category}
                )
        reserve_judgments.append(judgment)
        step_records.append(
            _step_record(config=config, pool=pool, request=reserve_request, judgment=judgment)
        )

    all_judgments = initial_judgments + reserve_judgments

    qrels_by_dataset = {
        ds: load_qrels(repo_root / meta["qrels_path"]) for ds, meta in config["datasets"].items()
    }
    terminal_outcomes = compute_terminal_outcomes(
        judgments=all_judgments, pools=pools, qrels_by_dataset=qrels_by_dataset, eval_k=eval_k
    )

    write_jsonl(output_dir / "normalized_judgments.jsonl", [j.to_dict() for j in all_judgments])
    write_jsonl(output_dir / "trajectory_events.jsonl", step_records)
    write_jsonl(output_dir / "terminal_outcomes.jsonl", [o.to_dict() for o in terminal_outcomes])
    write_jsonl(
        output_dir / "reserve_decisions.jsonl", [d.to_dict() for d in reserve_decisions]
    )
    if mode == "live":
        assert ledger is not None
        write_json(output_dir / "ledger_summary.json", ledger.summary())
        paid_api_calls = ledger.total_live_calls
    else:
        paid_api_calls = 0

    validation_problems: list[str] = []
    write_json(
        output_dir / "validation_report.json", {"mode": mode, "problems": validation_problems}
    )

    successful = sum(1 for j in all_judgments if j.success)
    failed_after_inference = sum(
        1 for j in all_judgments if not j.success and j.inference_attempted
    )
    failed_before_inference = sum(
        1 for j in all_judgments if not j.success and not j.inference_attempted
    )
    summary = {
        "mode": mode,
        "queries_loaded": len(frozen_queries),
        "pool_sizes": {f"{k[0]}:{k[1]}": len(p.candidate_ids) for k, p in pools.items()},
        "initial_request_count": len(initial_requests),
        "reserved_followup_calls": reserve_cap,
        "reserve_scheduled": sum(1 for d in reserve_decisions if d.scheduled),
        "reserve_skipped": sum(1 for d in reserve_decisions if not d.scheduled),
        "hard_max_live_calls": config["call_budget"]["hard_max_live_calls"],
        "paid_api_calls": paid_api_calls,
        "successful": successful,
        "failed_after_inference": failed_after_inference,
        "failed_before_inference": failed_before_inference,
        "call_accounting_note": (
            "successful + failed_after_inference == total inference attempts "
            "(calls that reached, or tried to reach, a provider). "
            "failed_before_inference (missing credentials, or blocked by an "
            "already-exhausted cap) is the documented exception: those cells "
            "never attempted a provider call and, in live mode, do not "
            "consume network/billing exposure."
        ),
        "failures": len(missing_cells),
        "missing_cells": missing_cells,
    }
    label = status_label(mode=mode, is_canary=is_canary)
    write_final_report(output_dir, label=label, mode=mode, is_canary=is_canary, summary=summary)
    return summary
